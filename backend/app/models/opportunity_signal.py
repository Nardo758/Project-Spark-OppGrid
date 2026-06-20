from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class OpportunitySignal(Base):
    __tablename__ = "opportunity_signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=True, index=True)
    opportunity_id = Column(
        Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )

    signal_type = Column(String(50), nullable=False, index=True)
    signal_value = Column(JSON, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source_url = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)

    paired_contact_id = Column(
        Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    paired_at = Column(DateTime(timezone=True), nullable=True)
    contact_lookup_source = Column(String(50), nullable=True)

    actioned = Column(Boolean, default=False, index=True)
    actioned_by_user_id = Column(Integer, nullable=True)
    actioned_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    opportunity = relationship("Opportunity", back_populates="signals")
    paired_contact = relationship("Lead", back_populates="signals")

    __table_args__ = (
        Index("idx_signal_unpaired", "actioned", "paired_contact_id"),
        Index("idx_signal_type_detected", "signal_type", "detected_at"),
    )
