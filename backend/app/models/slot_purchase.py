from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.sql import func

from app.db.database import Base


class SlotPurchase(Base):
    """
    Idempotency table for slot purchase webhook fulfillments.

    Keyed on the Stripe checkout session id so that Stripe webhook retries
    cannot double-credit a user's slot balance.
    """

    __tablename__ = "slot_purchases"

    id = Column(Integer, primary_key=True, index=True)
    stripe_session_id = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slots = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
