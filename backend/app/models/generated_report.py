"""
Generated Report Model - Caching and storage of generated PDF reports
"""

from sqlalchemy import Column, Integer, String, Text, LargeBinary, ForeignKey, DateTime, Enum
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


class ReportStatus(str, enum.Enum):
    """Status of a generated report"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GeneratedReport(Base):
    """
    Cache for generated PDF reports
    Stores reports with metadata for quick retrieval and regeneration
    """
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # User and request tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="generated_reports")
    
    # Report metadata
    report_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Source data for regeneration
    source_analysis_id = Column(String(100), nullable=True, index=True)
    source_request_id = Column(String(100), nullable=True, index=True)
    source_data = Column(JSONB, nullable=True)  # Store minimal input data for regeneration
    
    # Report content
    pdf_content = Column(LargeBinary, nullable=True)
    pdf_filename = Column(String(255), nullable=False)
    pdf_size_bytes = Column(Integer, nullable=True)
    
    # Generation metadata
    generation_time_ms = Column(Integer, nullable=True)
    ai_model_used = Column(String(50), nullable=True)
    generator_version = Column(String(20), nullable=True)
    
    # Caching and lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quality and tracking
    is_valid = Column(Integer, default=1)  # Boolean as int for SQLAlchemy compat
    error_message = Column(Text, nullable=True)
    
    def is_expired(self) -> bool:
        """Check if report cache has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def update_access(self) -> None:
        """Update access tracking"""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed_at = datetime.utcnow()
