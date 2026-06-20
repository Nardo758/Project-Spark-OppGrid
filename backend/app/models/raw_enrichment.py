from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"


class RawEnrichment(Base):
    __tablename__ = "raw_enrichment"

    id = Column(Integer, primary_key=True, index=True)
    target_entity = Column(String(50), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    field_name = Column(String(100), nullable=False, index=True)
    raw_value = Column(Text, nullable=True)
    parsed_value = Column(JSONB, nullable=True)
    confidence_score = Column(Float, default=0.0)
    enriched_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(20), default=EnrichmentStatus.PENDING.value, nullable=False, index=True
    )

    promoted_at = Column(DateTime(timezone=True), nullable=True)
    promoted_by = Column(String(50), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_raw_enrichment_target", "target_entity", "target_id"),
        Index("idx_raw_enrichment_status_expires", "status", "expires_at"),
    )
