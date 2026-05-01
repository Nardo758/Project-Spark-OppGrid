"""
Report Generation Schemas - Request/Response models for report API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ReportGenerationRequest(BaseModel):
    """Base request for report generation"""
    request_id: str = Field(..., description="Unique request identifier")
    force_regenerate: bool = Field(default=False, description="Force regenerate even if cached")


class IdentifyLocationReportRequest(ReportGenerationRequest):
    """Request for Identify Location PDF report"""
    identify_location_result: Dict[str, Any] = Field(
        ...,
        description="IdentifyLocationResponse data"
    )


class CloneSuccessReportRequest(ReportGenerationRequest):
    """Request for Clone Success PDF report"""
    clone_success_response: Dict[str, Any] = Field(
        ...,
        description="CloneSuccessResponse data"
    )


class PDFReportResponse(BaseModel):
    """Response for PDF report generation"""
    success: bool
    report_id: Optional[str] = None
    filename: str = Field(..., description="PDF filename")
    size_bytes: Optional[int] = Field(None, description="PDF file size in bytes")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    from_cache: bool = Field(default=False, description="Whether report was served from cache")
    generation_time_ms: Optional[int] = Field(None, description="Time taken to generate in ms")
    download_url: Optional[str] = Field(None, description="URL to download report")
    error: Optional[str] = None
    

class ReportStatusResponse(BaseModel):
    """Response for report status check"""
    report_id: str
    report_type: str
    status: str  # 'cached', 'expired', 'not_found'
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    access_count: Optional[int] = None
    last_accessed_at: Optional[datetime] = None
    is_valid: bool = True


class GeneratedReportInfo(BaseModel):
    """Information about a generated report"""
    report_id: str
    request_id: str
    report_type: str
    pdf_filename: str
    size_bytes: int
    generated_at: datetime
    access_count: int
    last_accessed_at: Optional[datetime] = None
    from_cache: bool = False
