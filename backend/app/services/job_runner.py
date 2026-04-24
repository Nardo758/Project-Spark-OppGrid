from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.job_run import JobRun
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from app.models.transaction import Transaction, TransactionStatus, TransactionType

logger = logging.getLogger(__name__)

_started = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_json_loads(s: str | None) -> dict:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def _safe_json_dumps(obj: Any) -> str | None:
    try:
        return json.dumps(obj)
    except Exception:
        return None


def _start_run(db: Session, job_name: str) -> JobRun:
    run = JobRun(job_name=job_name, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _finish_run(db: Session, run: JobRun, *, status: str, details: Any | None = None, error: str | None = None) -> None:
    run.status = status
    run.finished_at = _utcnow()
    run.details_json = _safe_json_dumps(details) if details is not None else None
    run.error = error
    db.add(run)
    db.commit()


async def _run_job(job_name: str, coro: Callable[[Session], Awaitable[dict]]) -> None:
    db = SessionLocal()
    run = None
    try:
        run = _start_run(db, job_name)
        details = await coro(db)
        _finish_run(db, run, status="succeeded", details=details)
    except Exception as e:
        logger.exception("Job %s failed", job_name)
        if run is not None:
            try:
                _finish_run(db, run, status="failed", error=str(e))
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
    finally:
        db.close()


async def _escrow_release_job(db: Session) -> dict:
    """
    Release escrow-held SUCCESS_FEE transactions when their escrow_release_date has passed.

    Current behavior: mark escrow transaction status from PENDING -> SUCCEEDED and stamp released_at in metadata.
    (Actual Stripe Connect payouts are a future upgrade.)
    """
    now = _utcnow()
    q = db.query(Transaction).filter(
        Transaction.type == TransactionType.SUCCESS_FEE,
        Transaction.status == TransactionStatus.PENDING,
    )
    candidates = q.order_by(Transaction.created_at.asc()).limit(500).all()

    released = 0
    skipped = 0
    checked = 0

    for tx in candidates:
        checked += 1
        meta = _safe_json_loads(tx.metadata_json)
        if meta.get("split_type") != "escrow_share":
            skipped += 1
            continue

        release_at_raw = meta.get("escrow_release_date")
        if not release_at_raw:
            skipped += 1
            continue

        try:
            release_at = datetime.fromisoformat(release_at_raw.replace("Z", "+00:00"))
            if release_at.tzinfo is None:
                release_at = release_at.replace(tzinfo=timezone.utc)
        except Exception:
            skipped += 1
            continue

        if release_at > now:
            continue

        tx.status = TransactionStatus.SUCCEEDED
        meta["released_at"] = now.isoformat()
        tx.metadata_json = _safe_json_dumps(meta) or tx.metadata_json
        db.add(tx)
        released += 1

    if released:
        db.commit()

    return {"checked": checked, "released": released, "skipped": skipped}


async def _apify_import_and_analyze_job(db: Session) -> dict:
    """
    Trigger a new Reddit actor run via Apify.

    Apify will send a webhook (POST /api/v1/webhook/apify) when the run
    completes; that handler fetches the dataset and passes items through
    the OpportunityProcessor pipeline automatically.
    """
    from app.services.apify_service import apify_service

    if not apify_service.is_configured():
        logger.warning("Apify not configured — skipping reddit import job")
        return {"skipped": True, "reason": "APIFY_API_TOKEN not set"}

    try:
        run_info = apify_service.run_reddit_scraper()
        run_id = run_info.get("id", "unknown")
        logger.info("Daily Reddit actor run triggered: run_id=%s", run_id)
        return {"triggered": True, "run_id": run_id, "status": run_info.get("status")}
    except Exception as exc:
        logger.error("Failed to trigger Reddit actor run: %s", exc)
        return {"triggered": False, "error": str(exc)}


def _stripe_status_to_local(status: str | None) -> SubscriptionStatus:
    s = (status or "").lower()
    if s in ("active", "trialing"):
        return SubscriptionStatus.ACTIVE
    if s == "past_due":
        return SubscriptionStatus.PAST_DUE
    if s == "canceled":
        return SubscriptionStatus.CANCELED
    return SubscriptionStatus.INCOMPLETE


def _epoch_to_dt(ts: int | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


async def _stripe_subscription_reconcile_job(db: Session) -> dict:
    """
    Defense-in-depth: periodically reconcile Stripe subscription truth with our DB.

    This catches cases where a webhook was missed/delayed and prevents entitlement drift.
    """
    from app.services.stripe_service import stripe_service, get_stripe_client

    try:
        client = get_stripe_client()
    except Exception as e:
        return {"enabled": False, "error": f"Stripe not configured: {e}"}

    q = db.query(Subscription).filter(Subscription.stripe_subscription_id.isnot(None))
    subs = q.order_by(Subscription.updated_at.asc().nullsfirst(), Subscription.id.asc()).limit(500).all()

    checked = 0
    updated = 0
    errors: list[dict] = []

    pro_price = stripe_service.STRIPE_PRICES.get(SubscriptionTier.PRO)
    business_price = stripe_service.STRIPE_PRICES.get(SubscriptionTier.BUSINESS)

    for s in subs:
        checked += 1
        try:
            stripe_sub = client.Subscription.retrieve(s.stripe_subscription_id)
            local_status = _stripe_status_to_local(getattr(stripe_sub, "status", None))

            # Period + cancel flags
            s.current_period_start = _epoch_to_dt(getattr(stripe_sub, "current_period_start", None)) or s.current_period_start
            s.current_period_end = _epoch_to_dt(getattr(stripe_sub, "current_period_end", None)) or s.current_period_end
            s.cancel_at_period_end = bool(getattr(stripe_sub, "cancel_at_period_end", False))
            s.status = local_status

            # Tier mapping via current subscription item price_id
            try:
                items = getattr(getattr(stripe_sub, "items", None), "data", None) or []
                price_id = None
                if items:
                    price = getattr(items[0], "price", None)
                    price_id = getattr(price, "id", None)
                if price_id:
                    s.stripe_price_id = price_id
                    if pro_price and price_id == pro_price:
                        s.tier = SubscriptionTier.PRO
                    elif business_price and price_id == business_price:
                        s.tier = SubscriptionTier.BUSINESS
            except Exception:
                # Ignore tier mapping errors; keep status reconciliation.
                pass

            db.add(s)
            updated += 1
        except Exception as e:
            errors.append({"subscription_id": s.id, "stripe_subscription_id": s.stripe_subscription_id, "error": str(e)})

    if updated:
        db.commit()

    return {"enabled": True, "checked": checked, "updated": updated, "errors": errors[:25]}


async def _loop(job_name: str, interval_seconds: int, fn: Callable[[Session], Awaitable[dict]]) -> None:
    # Stagger initial run slightly so startup can settle.
    await asyncio.sleep(3)
    while True:
        await _run_job(job_name, fn)
        await asyncio.sleep(max(5, int(interval_seconds)))


def start_background_jobs() -> None:
    """
    Called at app startup. Spawns asyncio tasks for enabled jobs.
    """
    global _started
    if _started:
        return
    _started = True

    if not settings.JOBS_ENABLED:
        logger.info("Background jobs disabled via JOBS_ENABLED=false")
        return

    loop = asyncio.get_event_loop()

    if settings.ESCROW_RELEASE_JOB_ENABLED:
        loop.create_task(_loop("escrow_release", settings.ESCROW_RELEASE_JOB_INTERVAL_SECONDS, _escrow_release_job))
        logger.info("Started job: escrow_release")

    import os as _os
    apify_job_enabled = settings.APIFY_IMPORT_JOB_ENABLED or bool(_os.getenv("APIFY_API_TOKEN"))
    if apify_job_enabled:
        loop.create_task(_loop("apify_import_and_analyze", settings.APIFY_IMPORT_JOB_INTERVAL_SECONDS, _apify_import_and_analyze_job))
        logger.info("Started job: apify_import_and_analyze")

    if settings.STRIPE_RECONCILE_JOB_ENABLED:
        loop.create_task(_loop("stripe_subscription_reconcile", settings.STRIPE_RECONCILE_JOB_INTERVAL_SECONDS, _stripe_subscription_reconcile_job))
        logger.info("Started job: stripe_subscription_reconcile")

