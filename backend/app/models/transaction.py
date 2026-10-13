from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class TransactionType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    MICRO_PAYMENT = "micro_payment"
    PROJECT_PAYMENT = "project_payment"
    SUCCESS_FEE = "success_fee"
    REVENUE_SHARE = "revenue_share"
    PAY_PER_UNLOCK = "pay_per_unlock"
    DEEP_CLONE = "deep_clone"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Transaction(Base):
    """
    Transaction DB: unified ledger for payments and success-based agreements.

    Note: stored as a separate table so we can expand payment flows without
    touching existing `Subscription` / `UnlockedOpportunity` tables.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    expert_id = Column(Integer, ForeignKey("experts.id", ondelete="SET NULL"), nullable=True, index=True)

    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)

    currency = Column(String(10), default="usd")
    amount_cents = Column(Integer, nullable=True)  # primary amount in cents, when applicable
    revenue_amount = Column(Numeric(14, 2), nullable=True)  # for revenue share tracking (future)

    # Stripe identifiers when applicable
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_invoice_id = Column(String(255), nullable=True, unique=True)
    stripe_charge_id = Column(String(255), nullable=True, unique=True)

    # Free-form metadata (JSON-in-Text)
    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    opportunity = relationship("Opportunity")
    expert = relationship("Expert")

