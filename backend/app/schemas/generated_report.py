from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ReportTypeEnum(str, Enum):
    FEASIBILITY_STUDY = "feasibility_study"
    MARKET_ANALYSIS = "market_analysis"
    STRATEGIC_ASSESSMENT = "strategic_assessment"
    PROGRESS_REPORT = "progress_report"


class ReportStatusEnum(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GeneratedReportCreate(BaseModel):
    opportunity_id: Optional[int] = None
    report_type: ReportTypeEnum
    title: Optional[str] = None


class GeneratedReportUpdate(BaseModel):
    status: Optional[ReportStatusEnum] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    confidence_score: Optional[int] = None
    generation_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None


class GeneratedReportResponse(BaseModel):
    id: int
    user_id: int
    opportunity_id: Optional[int] = None
    report_type: str
    status: str
    title: Optional[str] = None
    summary: Optional[str] = None
    confidence_score: Optional[int] = None
    generation_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GeneratedReportDetail(GeneratedReportResponse):
    content: Optional[str] = None
    economic_snapshot: Optional[dict] = None

    @field_validator('economic_snapshot', mode='before')
    @classmethod
    def parse_economic_snapshot(cls, v):
        """Accept a JSON string (as stored in the DB Text column) or a dict."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @classmethod
    def from_orm_with_snapshot(cls, obj):
        """Convenience wrapper — field_validator handles JSON parsing automatically."""
        return cls.model_validate(obj)


class GeneratedReportList(BaseModel):
    reports: List[GeneratedReportResponse]
    total: int
    page: int
    page_size: int


class ReportStats(BaseModel):
    total_reports: int
    reports_today: int
    reports_this_week: int
    reports_this_month: int
    by_type: dict
    by_status: dict
    avg_generation_time_ms: Optional[float] = None
    avg_confidence_score: Optional[float] = None


class UserReportStats(BaseModel):
    total_reports: int
    reports_this_month: int
    by_type: dict
