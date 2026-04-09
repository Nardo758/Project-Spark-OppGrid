"""
OppGrid Opportunity Access Model — v2.1

Tracks each user's access to individual opportunities within a billing month.
One row per (user_id, opportunity_id, billing_month) — re-access within the
same month is free (access_count incremented, not a new row).

Linked to the spec's `opportunity_access` table definition.
"""
import uuid
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric,
    ForeignKey, UniqueConstraint, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class OpportunityAccess(Base):
    __tablename__ = "opportunity_access"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )

    access_type = Column(
        String(20),
        nullable=False,
        default="api",
        comment="api | dashboard | report",
    )

    billing_month = Column(
        Date,
        nullable=False,
        comment="First day of the billing month (YYYY-MM-01)",
    )

    is_included = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if within monthly allowance; False = overage",
    )
    overage_charged = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="USD charged for this access event (0 if included)",
    )
    stripe_invoice_item_id = Column(
        String(100),
        nullable=True,
        comment="Stripe InvoiceItem ID for overage charge",
    )

    first_accessed_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    last_accessed_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    access_count = Column(Integer, nullable=False, default=1)

    # -----------------------------------------------------------------------
    # Constraints & indexes
    # -----------------------------------------------------------------------
    __table_args__ = (
        UniqueConstraint(
            "user_id", "opportunity_id", "billing_month",
            name="uq_opp_access_user_opp_month",
        ),
        Index("idx_opp_access_user_month", "user_id", "billing_month"),
        Index("idx_opp_access_overage", "user_id", "is_included"),
    )

    # -----------------------------------------------------------------------
    # Relationships (optional, not strictly required for service usage)
    # -----------------------------------------------------------------------
    user = relationship("User", backref="opportunity_accesses", lazy="select")
    opportunity = relationship("Opportunity", backref="access_records", lazy="select")
