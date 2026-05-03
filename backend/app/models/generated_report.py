"""
Generated Report Model - Storage of generated reports (text and PDF)
"""

from sqlalchemy import Column, Integer, String, Text, LargeBinary, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from datetime import datetime, timedelta
import enum


class ReportType(str, enum.Enum):
    """Types of reports that can be generated"""
    LAYER_1_OVERVIEW = "layer_1_overview"
    LAYER_2_DEEP_DIVE = "layer_2_deep_dive"
    LAYER_3_EXECUTION = "layer_3_execution"
    identify_location = "identify_location"
    clone_success = "clone_success"
    FEASIBILITY_STUDY = "feasibility_study"
    MARKET_ANALYSIS = "market_analysis"
    STRATEGIC_ASSESSMENT = "strategic_assessment"
    PROGRESS_REPORT = "progress_report"
    PRICING_STRATEGY = "pricing_strategy"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    CUSTOMER_INTERVIEW = "customer_interview"
    BUSINESS_PLAN = "business_plan"
    FINANCIAL_MODEL = "financial_model"
    PESTLE_ANALYSIS = "pestle_analysis"
    PITCH_DECK = "pitch_deck"
    LOCATION_ANALYSIS = "location_analysis"


class ReportStatus(str, enum.Enum):
    """Status of a generated report"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GeneratedReport(Base):
    """
    Storage for generated reports — supports both text-based and PDF-based reports.
    """
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)

    # User and request tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)

    # New PDF-cache columns (may be NULL for older text-based reports)
    request_id = Column(String(100), nullable=True, unique=True, index=True)
    source_analysis_id = Column(String(100), nullable=True, index=True)
    source_request_id = Column(String(100), nullable=True, index=True)
    source_data = Column(JSONB, nullable=True)

    # Report metadata
    report_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)

    # Text-based report content (legacy / Consultant Studio)
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    economic_snapshot = Column(Text, nullable=True)

    # Workspace / template linkage (Consultant Studio)
    workspace_id = Column(Integer, nullable=True)
    template_id = Column(Integer, nullable=True)

    # PDF report content
    pdf_content = Column(LargeBinary, nullable=True)
    pdf_filename = Column(String(255), nullable=True)
    pdf_size_bytes = Column(Integer, nullable=True)

    # Generation metadata
    generation_time_ms = Column(Integer, nullable=True)
    ai_model_used = Column(String(50), nullable=True)
    generator_version = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Tracking
    access_count = Column(Integer, default=0)
    retry_count = Column(Integer, nullable=True, default=0)

    # Error tracking
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Validity flag (1 = valid, 0 = invalidated)
    is_valid = Column(Integer, default=1)

    # Relationships
    user = relationship("User", back_populates="generated_reports")
    opportunity = relationship("Opportunity", back_populates="generated_reports")

    def is_expired(self) -> bool:
        """Check if report cache has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def update_access(self) -> None:
        """Update access tracking"""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed_at = datetime.utcnow()
