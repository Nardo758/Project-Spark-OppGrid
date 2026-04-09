"""
Report Usage Service
Tracks and manages monthly report usage per user tier
"""
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

from app.models.monthly_report_usage import MonthlyReportUsage
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionTier
from app.core.report_pricing import get_tier_free_reports, get_tier_report_discount, calculate_discounted_price


def get_current_year_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_user_tier(user: User, db: Session) -> str:
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not subscription:
        return "free"
    tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    return tier.lower()


def get_or_create_usage(user_id: int, year_month: str, db: Session) -> MonthlyReportUsage:
    usage = db.query(MonthlyReportUsage).filter(
        MonthlyReportUsage.user_id == user_id,
        MonthlyReportUsage.year_month == year_month
    ).first()
    
    if not usage:
        usage = MonthlyReportUsage(
            user_id=user_id,
            year_month=year_month,
            reports_used=0
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    
    return usage


def get_report_usage_status(user: User, db: Session) -> dict:
    tier = get_user_tier(user, db)
    year_month = get_current_year_month()
    usage = get_or_create_usage(user.id, year_month, db)
    
    free_reports_allocation = get_tier_free_reports(tier)
    is_unlimited = free_reports_allocation == -1
    
    if is_unlimited:
        free_remaining = -1
    else:
        free_remaining = max(0, free_reports_allocation - usage.reports_used)
    
    discount_percent = get_tier_report_discount(tier)
    
    return {
        "tier": tier,
        "year_month": year_month,
        "reports_used": usage.reports_used,
        "free_reports_allocation": free_reports_allocation,
        "free_remaining": free_remaining,
        "is_unlimited": is_unlimited,
        "discount_percent": discount_percent,
        "has_free_reports_available": is_unlimited or free_remaining > 0,
    }


def increment_report_usage(user_id: int, db: Session) -> MonthlyReportUsage:
    year_month = get_current_year_month()
    usage = get_or_create_usage(user_id, year_month, db)
    usage.reports_used += 1
    db.commit()
    db.refresh(usage)
    return usage


def check_free_report_available(user: User, db: Session) -> dict:
    status = get_report_usage_status(user, db)
    
    if status["is_unlimited"]:
        return {
            "is_free": True,
            "reason": "unlimited",
            "discount_percent": status["discount_percent"],
        }
    
    if status["free_remaining"] > 0:
        return {
            "is_free": True,
            "reason": "within_allocation",
            "free_remaining": status["free_remaining"],
            "discount_percent": status["discount_percent"],
        }
    
    return {
        "is_free": False,
        "reason": "allocation_exceeded",
        "discount_percent": status["discount_percent"],
    }


def atomic_reserve_free_report(user: User, db: Session) -> dict:
    """
    Atomically check and reserve a free report credit using SELECT FOR UPDATE.

    Uses a PostgreSQL upsert to ensure the usage row exists, then locks it
    with FOR UPDATE before incrementing. This prevents two simultaneous
    requests from both passing the credit check (TOCTOU race condition).

    Returns {"is_free": True, "reserved": True}  when a credit is consumed.
    Returns {"is_free": True, "reserved": False} for unlimited-tier users.
    Returns {"is_free": False} when the allocation is exhausted.

    If the downstream AI generation fails, call release_free_report_reservation
    to undo the credit deduction.
    """
    tier = get_user_tier(user, db)
    free_reports_allocation = get_tier_free_reports(tier)

    if free_reports_allocation == -1:
        return {"reserved": False, "reason": "unlimited", "is_free": True}

    year_month = get_current_year_month()

    db.execute(
        text(
            "INSERT INTO monthly_report_usage (user_id, year_month, reports_used) "
            "VALUES (:user_id, :year_month, 0) "
            "ON CONFLICT (user_id, year_month) DO NOTHING"
        ),
        {"user_id": user.id, "year_month": year_month},
    )

    usage = (
        db.query(MonthlyReportUsage)
        .filter(
            MonthlyReportUsage.user_id == user.id,
            MonthlyReportUsage.year_month == year_month,
        )
        .with_for_update()
        .first()
    )

    if not usage or usage.reports_used >= free_reports_allocation:
        return {"reserved": False, "reason": "allocation_exceeded", "is_free": False}

    usage.reports_used += 1
    db.commit()

    return {"reserved": True, "reason": "within_allocation", "is_free": True}


def release_free_report_reservation(user_id: int, db: Session) -> None:
    """
    Undo a credit previously reserved by atomic_reserve_free_report.

    Called in the exception handler of generate_free_report when AI generation
    fails after the credit was already incremented.  Idempotent — safe to call
    even if the usage counter is already at zero.
    """
    year_month = get_current_year_month()
    usage = (
        db.query(MonthlyReportUsage)
        .filter(
            MonthlyReportUsage.user_id == user_id,
            MonthlyReportUsage.year_month == year_month,
        )
        .with_for_update()
        .first()
    )
    if usage and usage.reports_used > 0:
        usage.reports_used -= 1


def get_effective_price(base_price_cents: int, user: Optional[User], db: Session) -> dict:
    if not user:
        return {
            "is_free": False,
            "original_price": base_price_cents,
            "final_price": base_price_cents,
            "discount_percent": 0,
            "reason": "guest_user",
        }
    
    free_check = check_free_report_available(user, db)
    
    if free_check["is_free"]:
        return {
            "is_free": True,
            "original_price": base_price_cents,
            "final_price": 0,
            "discount_percent": 100,
            "reason": free_check["reason"],
            "free_remaining": free_check.get("free_remaining"),
        }
    
    discount_percent = free_check["discount_percent"]
    final_price = calculate_discounted_price(base_price_cents, get_user_tier(user, db))
    
    return {
        "is_free": False,
        "original_price": base_price_cents,
        "final_price": final_price,
        "discount_percent": discount_percent,
        "reason": "paid_with_discount" if discount_percent > 0 else "paid_full_price",
    }


report_usage_service = type('ReportUsageService', (), {
    'get_usage_status': staticmethod(get_report_usage_status),
    'increment_usage': staticmethod(increment_report_usage),
    'check_free_available': staticmethod(check_free_report_available),
    'atomic_reserve_free_report': staticmethod(atomic_reserve_free_report),
    'release_free_report_reservation': staticmethod(release_free_report_reservation),
    'get_effective_price': staticmethod(get_effective_price),
    'get_user_tier': staticmethod(get_user_tier),
})()
