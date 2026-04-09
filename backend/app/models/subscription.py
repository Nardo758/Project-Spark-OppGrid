from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels - v2.1 unified access model (Apr 2026)"""
    # -------- v2.1 Platform tiers (dashboard + optional API) --------
    EXPLORER = "EXPLORER"           # $0/mo   — 0 opps, dashboard only
    BUILDER = "BUILDER"             # $99/mo  — 3 opps, 10 RPM, 250/day
    SCALER = "SCALER"               # $499/mo — 15 opps, 50 RPM, 1250/day
    # ENTERPRISE reused below (value unchanged, limits updated)

    # -------- v2.1 API-only tiers (no dashboard) --------------------
    API_STARTER = "API_STARTER"           # $99/mo  — 3 opps, 10 RPM, 250/day
    API_PROFESSIONAL = "API_PROFESSIONAL" # $499/mo — 15 opps, 50 RPM, 1250/day
    API_ENTERPRISE = "API_ENTERPRISE"     # $2500/mo — 75 opps, 500 RPM, 10000/day

    # -------- Shared across v2.1 platform + API ----------------------
    ENTERPRISE = "ENTERPRISE"  # $2500/mo — 75 opps, 500 RPM, 10000/day

    # -------- Legacy tiers (Jan 2026 model — kept for compat) --------
    STARTER = "STARTER"      # maps to BUILDER equivalent
    GROWTH = "GROWTH"        # maps to BUILDER equivalent
    PRO = "PRO"              # maps to SCALER equivalent
    TEAM = "TEAM"            # maps to BUILDER equivalent
    BUSINESS = "BUSINESS"    # maps to SCALER equivalent

    # Legacy free tier (deprecated)
    FREE = "FREE"            # Deprecated - map to blocked access


class SubscriptionStatus(str, enum.Enum):
    """Subscription status"""
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"
    TRIALING = "TRIALING"
    INCOMPLETE = "INCOMPLETE"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Subscription details
    tier = Column(
        Enum(SubscriptionTier, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    status = Column(
        Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )

    # Stripe details
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Billing cycle
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscription")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Usage tracking
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # View counts
    opportunity_views = Column(Integer, default=0)
    unlocked_opportunities = Column(Integer, default=0)

    # Export counts
    csv_exports = Column(Integer, default=0)
    ideas_exported = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="usage_records")


class UnlockMethod(str, enum.Enum):
    """How the opportunity was unlocked"""
    SUBSCRIPTION = "subscription"  # Auto-unlocked by subscription tier
    PAY_PER_UNLOCK = "pay_per_unlock"  # Paid $15 one-time (Archive Layer 1)
    FAST_PASS = "fast_pass"  # Paid $99 one-time (HOT 0-7 days access)
    DEEP_DIVE = "deep_dive"  # Paid $49 one-time (Layer 2 add-on for Pro tier)
    SLOT_CLAIM = "slot_claim"  # Used monthly slot to claim opportunity


class UserSlotBalance(Base):
    """Track user's monthly slot credits for claiming opportunities"""
    __tablename__ = "user_slot_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Monthly slot allocation (based on subscription tier)
    monthly_slots = Column(Integer, default=0)
    slots_used = Column(Integer, default=0)
    
    # Extra purchased slots (carry over until used)
    purchased_slots = Column(Integer, default=0)
    
    # Period tracking
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="slot_balance")
    
    @property
    def available_slots(self) -> int:
        """Total available slots (monthly + purchased - used)"""
        monthly_remaining = max(0, self.monthly_slots - self.slots_used)
        return monthly_remaining + self.purchased_slots


class OpportunityClaimLimit(Base):
    """Track exclusivity limits per opportunity (3-10 users max)"""
    __tablename__ = "opportunity_claim_limits"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Exclusivity limits
    claim_limit = Column(Integer, default=10)  # Max users who can claim (3-10)
    claimed_count = Column(Integer, default=0)  # Current claim count
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    opportunity = relationship("Opportunity", back_populates="claim_limit_record")
    
    @property
    def slots_remaining(self) -> int:
        """Slots remaining for this opportunity"""
        return max(0, self.claim_limit - self.claimed_count)
    
    @property
    def is_available(self) -> bool:
        """Check if opportunity can still be claimed"""
        return self.claimed_count < self.claim_limit


class UnlockedOpportunity(Base):
    __tablename__ = "unlocked_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)

    # Unlock details
    unlock_method = Column(Enum(UnlockMethod), default=UnlockMethod.SUBSCRIPTION, nullable=False)
    amount_paid = Column(Integer, default=0)  # Amount in cents (for pay-per-unlock)
    stripe_payment_intent_id = Column(String(255), nullable=True)

    # Deep Dive (Layer 2) access - separate from base unlock
    has_deep_dive = Column(Boolean, default=False)  # Paid $49 for Layer 2 access
    deep_dive_payment_intent_id = Column(String(255), nullable=True)
    deep_dive_unlocked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamp
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For pay-per-unlock (30 days)

    # Relationships
    user = relationship("User")
    opportunity = relationship("Opportunity")

    # Unique constraint - user can only unlock each opportunity once
    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_unlocked_opportunity_user_opportunity"),
        {"sqlite_autoincrement": True},
    )
