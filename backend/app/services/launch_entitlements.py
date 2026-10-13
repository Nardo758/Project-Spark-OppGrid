"""Launch entitlements for OppGrid Monthly and the $49 Deep Clone report.

Legacy tiers stay in the database so current subscribers keep working.
Only MONTHLY can be purchased. Its Stripe price id is STRIPE_PRICE_MONTHLY.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_optional, get_db
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.services.report_quota_service import (
    MONTHLY_DEEP_CLONE_ALLOCATION,
    ReportQuotaService,
)
from app.services.stripe_service import StripeService

MONTHLY_DISPLAY_NAME = "OppGrid Monthly"
MONTHLY_PRICE_CENTS = 3900
DEEP_CLONE_PRICE_CENTS = 4900
DEEP_CLONE_PRICE_LABEL = "$49"
DEEP_CLONE_CHECKOUT_PATH = "/api/v1/subscriptions/deep-clone-checkout"
REPORTS_PER_PERIOD = MONTHLY_DEEP_CLONE_ALLOCATION

LEGACY_PURCHASE_TIERS = frozenset(
    {
        SubscriptionTier.STARTER,
        SubscriptionTier.GROWTH,
        SubscriptionTier.PRO,
        SubscriptionTier.TEAM,
        SubscriptionTier.BUSINESS,
        SubscriptionTier.ENTERPRISE,
    }
)

PREMIUM_TIERS = frozenset(
    {
        SubscriptionTier.GROWTH,
        SubscriptionTier.PRO,
        SubscriptionTier.TEAM,
        SubscriptionTier.BUSINESS,
        SubscriptionTier.ENTERPRISE,
        SubscriptionTier.MONTHLY,
    }
)

# Monthly does not include these. Every other stored tier keeps today's access.
LOCKED_FEATURES = frozenset(
    {
        "expert_marketplace",
        "workhub",
        "datasets",
        "alerts",
    }
)

NEW_PURCHASE_REFUSAL = "This plan is not available for new purchases."


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def coerce_tier(tier) -> SubscriptionTier | None:
    if tier is None:
        return None
    if isinstance(tier, SubscriptionTier):
        return tier
    raw = getattr(tier, "value", tier)
    key = str(raw).strip().upper()
    if not key:
        return None
    try:
        return SubscriptionTier[key]
    except KeyError:
        try:
            return SubscriptionTier(key)
        except ValueError:
            return None


def is_premium_tier(tier) -> bool:
    parsed = coerce_tier(tier)
    return parsed in PREMIUM_TIERS


def is_available_for_new_purchase(tier) -> bool:
    return coerce_tier(tier) == SubscriptionTier.MONTHLY


def tier_unlocks_feature(tier, feature: str) -> bool:
    """Whether a stored tier includes a launch feature.

    MONTHLY includes the feed, included reports, and the premium check.
    It does not include the expert marketplace, WorkHub, datasets, or alerts.
    """
    parsed = coerce_tier(tier)
    if feature == "premium":
        return is_premium_tier(parsed)
    if feature == "feed":
        return parsed == SubscriptionTier.MONTHLY or parsed in LEGACY_PURCHASE_TIERS
    if feature == "reports":
        return parsed == SubscriptionTier.MONTHLY
    if feature in LOCKED_FEATURES:
        return parsed != SubscriptionTier.MONTHLY
    return False


def stripe_price_id_for_tier(tier: SubscriptionTier) -> str | None:
    """Resolve a checkout price id. MONTHLY is read from the environment each call."""
    import os

    if tier == SubscriptionTier.MONTHLY:
        price_id = os.getenv("STRIPE_PRICE_MONTHLY")
        return price_id or None
    return StripeService.STRIPE_PRICES.get(tier)


def entitled_subscription_tier(subscription: Subscription | None, now: datetime | None = None) -> SubscriptionTier:
    """Tier that still has access, including cancel-at-period-end until period end."""
    now = now or datetime.now(timezone.utc)
    if subscription is None:
        return SubscriptionTier.FREE
    tier = coerce_tier(subscription.tier) or SubscriptionTier.FREE
    end = as_utc(subscription.current_period_end)
    if end is not None and now >= end:
        return SubscriptionTier.FREE
    status = subscription.status
    if status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        return tier
    if subscription.cancel_at_period_end and status == SubscriptionStatus.CANCELED:
        return tier
    return SubscriptionTier.FREE


def monthly_period_is_open(subscription: Subscription | None, now: datetime | None = None) -> bool:
    """True while a Monthly subscriber is inside the already-paid Stripe period."""
    if subscription is None or coerce_tier(subscription.tier) != SubscriptionTier.MONTHLY:
        return False
    now = now or datetime.now(timezone.utc)
    start = as_utc(subscription.current_period_start)
    end = as_utc(subscription.current_period_end)
    if end is None or now >= end:
        return False
    if start is not None and now < start:
        return False
    status = subscription.status
    if status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        return True
    return bool(subscription.cancel_at_period_end and status == SubscriptionStatus.CANCELED)


def _deep_clone_purchase_in_period(row: Transaction, start: datetime | None, end: datetime) -> bool:
    if row.status != TransactionStatus.SUCCEEDED:
        return False
    is_deep_clone = row.type == TransactionType.DEEP_CLONE
    if not is_deep_clone and row.metadata_json:
        import json

        try:
            meta = json.loads(row.metadata_json)
        except (TypeError, ValueError):
            meta = {}
        if isinstance(meta, dict):
            payment_type = meta.get("payment_type") or meta.get("type")
            is_deep_clone = payment_type == "deep_clone"
    if not is_deep_clone:
        return False
    created = as_utc(row.created_at) or end
    if start is not None and created < start:
        return False
    return created < end


def paid_deep_clone_reports_in_period(db: Session, user: User, subscription: Subscription) -> int:
    start = as_utc(subscription.current_period_start)
    end = as_utc(subscription.current_period_end)
    if end is None:
        return 0
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.status == TransactionStatus.SUCCEEDED)
        .all()
    )
    return sum(1 for row in rows if _deep_clone_purchase_in_period(row, start, end))


def monthly_report_decision(db: Session, user: User, now: datetime | None = None) -> dict[str, Any] | None:
    """Decide a Deep Clone request for a Monthly subscriber.

    Returns None when the user is not on MONTHLY, so legacy premium and
    one-time unlocks keep their existing path.

    Included reports: 2 per Stripe period (current_period_start/end), stored on
    UserReportQuota and reset by opening a new period row. Unused reports do
    not roll over. A succeeded $49 Deep Clone purchase inside the same period
    adds one report. The next request past that cap offers the $49 checkout.
    """
    subscription = user.subscription
    if subscription is None or coerce_tier(subscription.tier) != SubscriptionTier.MONTHLY:
        return None
    if not monthly_period_is_open(subscription, now=now):
        return {"status": "inactive"}

    quota_service = ReportQuotaService(db)
    quota = quota_service.get_monthly_deep_clone_quota(user, subscription.current_period_end)
    purchased = paid_deep_clone_reports_in_period(db, user, subscription)
    allowance = REPORTS_PER_PERIOD + purchased
    if quota.used >= allowance:
        return {
            "status": "over_quota",
            "error": (
                "OppGrid Monthly includes 2 reports per billing period. "
                "This request is past that limit. Buy the $49 Deep Clone report to continue."
            ),
            "offer_single_report": True,
            "offer_amount_cents": DEEP_CLONE_PRICE_CENTS,
            "offer_amount_label": DEEP_CLONE_PRICE_LABEL,
            "offer_checkout_path": DEEP_CLONE_CHECKOUT_PATH,
            "reports_used": quota.used,
            "reports_limit": REPORTS_PER_PERIOD,
        }
    return {
        "status": "allowed",
        "period_end": subscription.current_period_end,
        "reports_used": quota.used,
        "reports_limit": REPORTS_PER_PERIOD,
    }


def notification_prefs_enable_alerts(prefs: Optional[dict]) -> bool:
    if not isinstance(prefs, dict):
        return False
    return bool(prefs.get("email") or prefs.get("push") or prefs.get("slack"))


def reject_monthly_alerts(db: Session, user: User, prefs: Optional[dict]) -> None:
    if not notification_prefs_enable_alerts(prefs):
        return
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user.id).first()
    )
    if subscription is not None and coerce_tier(subscription.tier) == SubscriptionTier.MONTHLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OppGrid Monthly does not include alerts",
        )


def monthly_feature_lock(feature: str):
    """Refuse the feature for an authenticated Monthly subscriber. Guests pass through."""

    async def _lock(
        current_user: User | None = Depends(get_current_user_optional),
        db: Session = Depends(get_db),
    ) -> None:
        if current_user is None or feature not in LOCKED_FEATURES:
            return
        subscription = (
            db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
        )
        if subscription is not None and coerce_tier(subscription.tier) == SubscriptionTier.MONTHLY:
            label = feature.replace("_", " ")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"OppGrid Monthly does not include {label}",
            )

    return _lock
