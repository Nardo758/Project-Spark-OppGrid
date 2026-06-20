from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Index
from sqlalchemy.sql import func
from app.db.database import Base


class DataQualityAudit(Base):
    __tablename__ = "data_quality_audits"

    id = Column(Integer, primary_key=True, index=True)
    dataset = Column(String(50), nullable=False, index=True)
    check_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_records = Column(Integer, default=0)
    stale_records = Column(Integer, default=0)
    missing_records = Column(Integer, default=0)
    accuracy_score = Column(Float, default=0.0)
    freshness_score = Column(Float, default=0.0)
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_dqa_dataset_published", "dataset", "published"),
    )
