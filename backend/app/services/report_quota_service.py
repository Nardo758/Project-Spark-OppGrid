"""Report quota management service for subscription-based allocation."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from app.models.user import User
from app.models.user_report_quota import UserReportQuota, ReportPurchaseLog

logger = logging.getLogger(__name__)


class ReportQuotaService:
    """
    Manages report generation quotas for users based on subscription tier.
    
    Pricing Model:
    - Free Members: Pay-per-report (no allocation)
    - Pro Members: 5/2/0 free + overage discounts
    - Business Members: 15/8/3 free + overage discounts
    """
    
    # Monthly allocation per subscription tier
    TIER_ALLOCATIONS = {
        "free": {"layer_1": 0, "layer_2": 0, "layer_3": 0},
        "pro": {"layer_1": 5, "layer_2": 2, "layer_3": 0},
        "business": {"layer_1": 15, "layer_2": 8, "layer_3": 3},
        "enterprise": {"layer_1": 50, "layer_2": 25, "layer_3": 10},
    }
    
    # Per-report pricing in cents for non-subscribed users
    BASE_PRICES = {
        "layer_1": 1500,  # $15
        "layer_2": 2500,  # $25
        "layer_3": 3500,  # $35
    }
    
    # Overage pricing (discounted from base) by tier
    OVERAGE_PRICES = {
        "free": {"layer_1": 1500, "layer_2": 2500, "layer_3": 3500},  # Full price
        "pro": {"layer_1": 1000, "layer_2": 1800, "layer_3": 2500},   # 33% discount
        "business": {"layer_1": 800, "layer_2": 1500, "layer_3": 2000},  # 47% discount
        "enterprise": {"layer_1": 500, "layer_2": 1000, "layer_3": 1500},  # 66% discount
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_tier(self, user: User) -> str:
        """Get effective subscription tier for user."""
        if not user or not user.subscription:
            return "free"
        
        tier = user.subscription.tier
        if isinstance(tier, str):
            return tier.lower()
        # If it's an enum
        return tier.value.lower() if hasattr(tier, 'value') else str(tier).lower()
    
    def get_billing_date(self, user: User) -> datetime:
        """Get user's subscription billing date."""
        if user.subscription and user.subscription.current_period_end:
            return user.subscription.current_period_end
        return datetime.utcnow() + timedelta(days=30)
    
    def get_or_create_quota(self, user: User, report_tier: str) -> UserReportQuota:
        """Get or create quota record for user+tier."""
        if not user.id:
            raise ValueError("User must be saved before quota operations")
        
        tier = self.get_user_tier(user)
        billing_date = self.get_billing_date(user)
        
        # Normalize billing date to month end (reset on that date)
        reset_date = billing_date.replace(day=1) + timedelta(days=32)
        reset_date = reset_date.replace(day=1) - timedelta(days=1)
        
        # Check if quota exists and is still valid
        quota = self.db.query(UserReportQuota).filter(
            UserReportQuota.user_id == user.id,
            UserReportQuota.report_tier == report_tier,
            UserReportQuota.reset_date >= datetime.utcnow(),
        ).first()
        
        if quota:
            return quota
        
        # Create new quota
        allocated = self.TIER_ALLOCATIONS.get(tier, {}).get(report_tier, 0)
        quota = UserReportQuota(
            user_id=user.id,
            report_tier=report_tier,
            allocated=allocated,
            used=0,
            reset_date=reset_date,
            subscription_tier=tier,
        )
        self.db.add(quota)
        self.db.commit()
        self.db.refresh(quota)
        
        logger.info(f"Created quota for user {user.id}: {report_tier} tier={tier} allocated={allocated}")
        return quota
    
    def get_remaining_quota(self, user: User, report_tier: str) -> int:
        """Get remaining quota for user+tier."""
        if not user.id:
            return 0
        
        quota = self.get_or_create_quota(user, report_tier)
        return quota.remaining()
    
    def can_generate_free(self, user: User, report_tier: str) -> bool:
        """Check if user can generate report without charge."""
        if not user or not user.id:
            return False
        
        # Free tier members never get free reports
        tier = self.get_user_tier(user)
        if tier == "free":
            return False
        
        quota = self.get_or_create_quota(user, report_tier)
        return quota.can_generate_free()
    
    def get_price_for_user(self, user: User, report_tier: str) -> int:
        """
        Get price for report in cents.
        Returns 0 if user has quota allocation remaining.
        Returns overage price if quota exhausted.
        """
        if not user or not user.id:
            return self.BASE_PRICES.get(report_tier, 0)
        
        tier = self.get_user_tier(user)
        
        # Check if user has free allocation
        quota = self.get_or_create_quota(user, report_tier)
        if quota.can_generate_free():
            return 0  # Free from allocation
        
        # Return overage price based on tier
        return self.OVERAGE_PRICES.get(tier, {}).get(report_tier, self.BASE_PRICES.get(report_tier, 0))
    
    def decrement_quota(self, user: User, report_tier: str) -> bool:
        """
        Decrement quota by 1 (when user generates free report).
        Returns True if successful, False if quota exhausted.
        """
        if not user or not user.id:
            return False
        
        quota = self.get_or_create_quota(user, report_tier)
        success = quota.decrement()
        
        if success:
            self.db.commit()
            logger.info(f"Decremented quota for user {user.id}: {report_tier} remaining={quota.remaining()}")
        else:
            logger.warning(f"Quota exhausted for user {user.id}: {report_tier}")
        
        return success
    
    def log_purchase(
        self,
        user: User,
        report_tier: str,
        payment_type: str = "quota",
        amount_cents: int = 0,
        stripe_charge_id: Optional[str] = None,
        report_id: Optional[int] = None,
        opportunity_id: Optional[int] = None,
    ) -> ReportPurchaseLog:
        """Log a report purchase for auditing."""
        log = ReportPurchaseLog(
            user_id=user.id,
            report_tier=report_tier,
            payment_type=payment_type,
            amount_cents=amount_cents,
            stripe_charge_id=stripe_charge_id,
            report_id=report_id,
            opportunity_id=opportunity_id,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        logger.info(f"Logged purchase: user={user.id} tier={report_tier} type={payment_type} amount={amount_cents}¢")
        return log
    
    def get_usage_summary(self, user: User) -> Dict[str, Dict[str, int]]:
        """Get quota usage summary for user across all tiers."""
        if not user or not user.id:
            return {}
        
        summary = {}
        for tier in ["layer_1", "layer_2", "layer_3"]:
            quota = self.get_or_create_quota(user, tier)
            summary[tier] = {
                "allocated": quota.allocated,
                "used": quota.used,
                "remaining": quota.remaining(),
                "exhausted": quota.is_exhausted(),
                "reset_date": quota.reset_date.isoformat(),
            }
        
        return summary
    
    def check_access(self, user: Optional[User], report_tier: str) -> Tuple[bool, str, int]:
        """
        Check if user can generate report and what they'll be charged.
        
        Returns: (can_generate, message, price_cents)
        """
        if not user or not user.id:
            return False, "Must sign up to generate reports", 0
        
        tier = self.get_user_tier(user)
        
        # Check if free tier
        if tier == "free":
            price = self.BASE_PRICES.get(report_tier, 0)
            return True, f"Generate report for ${price/100:.2f}", price
        
        # Check quota
        if self.can_generate_free(user, report_tier):
            remaining = self.get_remaining_quota(user, report_tier)
            return True, f"Generate free ({remaining} remaining this month)", 0
        
        # Overage
        price = self.OVERAGE_PRICES.get(tier, {}).get(report_tier, self.BASE_PRICES.get(report_tier, 0))
        return True, f"Generate report for ${price/100:.2f} (quota exhausted)", price
