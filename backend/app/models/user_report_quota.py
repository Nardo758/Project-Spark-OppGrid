"""User report quota tracking model for subscription-based report allocation."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserReportQuota(Base):
    """
    Tracks monthly report generation quota for each user by report tier.
    
    Quota Model:
    - Free Members: No allocation (pay-per-report)
    - Pro Members: 5 Layer1, 2 Layer2, 0 Layer3 per month
    - Business Members: 15 Layer1, 8 Layer2, 3 Layer3 per month
    
    Quota resets on the billing date each month.
    """
    __tablename__ = "user_report_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Report tier: "layer_1", "layer_2", "layer_3"
    report_tier = Column(String(20), nullable=False, index=True)
    
    # Allocated reports for this month
    allocated = Column(Integer, default=0)
    
    # Number of reports generated this month
    used = Column(Integer, default=0)
    
    # When this quota resets (billing date)
    reset_date = Column(DateTime, nullable=False)
    
    # Subscription tier at time of allocation
    subscription_tier = Column(String(50), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint: one quota per user+tier per billing cycle
    __table_args__ = (
        UniqueConstraint('user_id', 'report_tier', 'reset_date', 
                        name='unique_user_tier_period'),
    )
    
    # Relationships
    user = relationship("User", back_populates="report_quotas")
    
    def remaining(self) -> int:
        """Get remaining quota for this tier."""
        return max(0, self.allocated - self.used)
    
    def is_exhausted(self) -> bool:
        """Check if quota is fully used."""
        return self.used >= self.allocated
    
    def can_generate_free(self) -> bool:
        """Check if user can generate report without charge."""
        return self.remaining() > 0
    
    def decrement(self) -> bool:
        """Decrement quota by 1. Returns True if successful."""
        if self.is_exhausted():
            return False
        self.used += 1
        self.updated_at = datetime.utcnow()
        return True


class ReportPurchaseLog(Base):
    """
    Track individual report purchases for auditing and analytics.
    
    Supports both registered users and guest checkouts:
    - user_id: If registered user (non-null)
    - guest_email: If guest checkout (will convert to account later)
    """
    __tablename__ = "report_purchase_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Null for guest
    guest_email = Column(String(255), nullable=True, index=True)  # For guest checkouts
    opportunity_id = Column(Integer, nullable=True)
    
    # "layer_1", "layer_2", "layer_3"
    report_tier = Column(String(20), nullable=False)
    
    # How it was paid: "quota" (free, from allocation), "stripe" (paid), "free" (promo)
    payment_type = Column(String(20), default="stripe")
    
    # Amount charged in cents (0 if quota)
    amount_cents = Column(Integer, default=0)
    
    # Stripe charge ID if applicable
    stripe_charge_id = Column(String(255), nullable=True)
    
    # Report generation ID
    report_id = Column(Integer, nullable=True)
    
    # Track if guest later created account
    guest_converted_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", foreign_keys=[user_id])
