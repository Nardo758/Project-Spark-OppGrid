"""
Async usage tracking middleware for the OppGrid Public API v1.

Logs every request to the api_usage table using a dedicated DB session.
Attached to the v1_app sub-application; does not run on the main app.

Injects spec v2.1 response headers on every authenticated response:
  Rate limiting:  X-RateLimit-Limit, X-RateLimit-Remaining,
                  X-Daily-Limit, X-Daily-Remaining
  Monthly caps:   X-Monthly-Included, X-Monthly-Used, X-Monthly-Remaining,
                  X-Monthly-Overage, X-Monthly-Overage-Cost, X-Overage-Rate
  Billing period: X-Billing-Month, X-Billing-Resets
  Timing:         X-Response-Time-Ms
"""
import time
import logging
from datetime import date
from typing import Optional

from sqlalchemy import func
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.database import SessionLocal
from app.services import api_key_service
from app.models.tier_config import TierConfig

logger = logging.getLogger(__name__)


def _next_billing_reset(billing_month: date) -> date:
    """Return the first day of the month after *billing_month*."""
    if billing_month.month == 12:
        return date(billing_month.year + 1, 1, 1)
    return date(billing_month.year, billing_month.month + 1, 1)


def _query_monthly_usage(api_key_id, user_id: int, tier: str, db) -> dict:
    """
    Perform a lightweight DB query to get real monthly usage numbers.
    Returns a dict matching the spec usage object shape.
    Falls back to zeroes on any failure (usage headers must never block response).
    """
    try:
        from app.models.opportunity_access import OpportunityAccess

        today = date.today()
        billing_month = date(today.year, today.month, 1)
        cap = TierConfig.get_monthly_cap(tier)
        overage_rate = TierConfig.get_overage_rate(tier)

        total = (
            db.query(func.count(OpportunityAccess.id))
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.billing_month == billing_month,
            )
            .scalar()
        ) or 0

        included_used = (
            db.query(func.count(OpportunityAccess.id))
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.billing_month == billing_month,
                OpportunityAccess.is_included == True,
            )
            .scalar()
        ) or 0

        overage_count = total - included_used

        return {
            "billing_month": billing_month.isoformat(),
            "included_cap": cap,
            "included_used": included_used,
            "included_remaining": max(0, cap - included_used),
            "overage_count": overage_count,
            "overage_cost": float(overage_count * 30.00),
            "total_accessed": total,
        }
    except Exception as exc:
        logger.warning("UsageTrackingMiddleware: monthly usage query failed: %s", exc)
        today = date.today()
        bm = date(today.year, today.month, 1)
        cap = TierConfig.get_monthly_cap(tier)
        return {
            "billing_month": bm.isoformat(),
            "included_cap": cap,
            "included_used": 0,
            "included_remaining": cap,
            "overage_count": 0,
            "overage_cost": 0.0,
            "total_accessed": 0,
        }


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Asynchronous middleware that records every /v1/ request to api_usage
    and injects spec-compliant response headers.

    - api_key_id is taken from request.state.api_key (set by get_authenticated_key).
    - For unauthenticated requests, api_key_id is None (still recorded for audit).
    - Uses a fresh SessionLocal for each request so the main request session
      is never blocked waiting for the write.
    - Failures are logged but never block the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # ---- Timing ---------------------------------------------------------
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        api_key = getattr(request.state, "api_key", None)

        # ---- Per-request DB session for headers + usage write ---------------
        db = SessionLocal()
        try:
            if api_key is not None:
                rpm = api_key.rate_limit_rpm
                daily = api_key.daily_limit
                tier = api_key.tier

                rpm_remaining = getattr(request.state, "rpm_remaining", rpm)
                daily_remaining = getattr(request.state, "daily_remaining", daily)

                # Rate-limit headers
                response.headers["X-RateLimit-Limit"] = str(rpm)
                response.headers["X-RateLimit-Remaining"] = str(rpm_remaining)
                response.headers["X-Daily-Limit"] = str(daily)
                response.headers["X-Daily-Remaining"] = str(daily_remaining)
                # Backward-compat alias
                response.headers["X-RateLimit-Remaining-Daily"] = str(daily_remaining)

                # Monthly allowance headers — use pre-computed state if the
                # opportunity detail endpoint set it; otherwise query DB now.
                monthly = getattr(request.state, "monthly_usage", None)
                if monthly is None:
                    monthly = _query_monthly_usage(
                        api_key_id=api_key.id,
                        user_id=api_key.user_id,
                        tier=tier,
                        db=db,
                    )

                cap = TierConfig.get_monthly_cap(tier)
                overage_rate = TierConfig.get_overage_rate(tier)

                included_used = monthly.get("included_used", 0)
                included_remaining = monthly.get("included_remaining", cap)
                overage_count = monthly.get("overage_count", 0)
                overage_cost = monthly.get("overage_cost", 0.0)
                billing_month_str = monthly.get("billing_month", "")

                try:
                    bm = date.fromisoformat(billing_month_str)
                except (ValueError, TypeError):
                    today = date.today()
                    bm = date(today.year, today.month, 1)

                response.headers["X-Monthly-Included"] = str(cap)
                response.headers["X-Monthly-Used"] = str(included_used)
                response.headers["X-Monthly-Remaining"] = str(included_remaining)
                response.headers["X-Monthly-Overage"] = str(overage_count)
                response.headers["X-Monthly-Overage-Cost"] = f"{overage_cost:.2f}"
                response.headers["X-Overage-Rate"] = f"{overage_rate:.2f}"
                response.headers["X-Billing-Month"] = bm.isoformat()
                response.headers["X-Billing-Resets"] = _next_billing_reset(bm).isoformat()
            else:
                # Unauthenticated — propagate rate-limit info if stashed
                if hasattr(request.state, "rpm_remaining"):
                    response.headers["X-RateLimit-Remaining"] = str(
                        request.state.rpm_remaining
                    )
                if hasattr(request.state, "daily_remaining"):
                    response.headers["X-RateLimit-Remaining-Daily"] = str(
                        request.state.daily_remaining
                    )

            # ---- Async usage write ------------------------------------------
            api_key_id = api_key.id if api_key is not None else None
            api_key_service.record_usage(
                api_key_id=api_key_id,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                db=db,
            )
        except Exception as exc:
            logger.warning("UsageTrackingMiddleware: error in response hook: %s", exc)
        finally:
            db.close()

        return response
