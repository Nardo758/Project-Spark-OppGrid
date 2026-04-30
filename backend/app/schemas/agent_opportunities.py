"""
Agent Opportunities API Response Schemas — Pydantic models for agent opportunities endpoints.

Structured responses with metadata for opportunities search, detail, and batch analysis.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OpportunitySummary(BaseModel):
    """Minimal opportunity data for search results"""
    id: int
    title: str
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    market_size: Optional[str] = None
    competition_level: Optional[str] = None
    demand_signals: Optional[List[str]] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=100)
    created_at: datetime

    class Config:
        from_attributes = True


class OpportunityDetail(BaseModel):
    """Full opportunity data with metrics and trends"""
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    
    # AI Analysis
    ai_opportunity_score: Optional[int] = None
    ai_competition_level: Optional[str] = None
    ai_urgency_level: Optional[str] = None
    ai_market_size_estimate: Optional[str] = None
    ai_pain_intensity: Optional[int] = None
    
    # Metrics
    market_size: Optional[str] = None
    growth_rate: Optional[float] = None
    validation_count: int = 0
    
    # Risk & Trend
    risk_score: float = Field(ge=0, le=100)
    trend_direction: str = Field(default="neutral", pattern="^(up|down|neutral)$")
    
    # Historical data (30/60/90 day trends)
    historical_data: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchAnalysisItem(BaseModel):
    """Single item in batch analysis response"""
    id: int
    title: str
    score: float = Field(ge=0, le=100)
    trend: str = Field(pattern="^(up|down|neutral)$")
    confidence: float = Field(ge=0, le=100)
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")

    class Config:
        from_attributes = True


class BatchAnalysisResponse(BaseModel):
    """Batch analysis response with multiple opportunities"""
    items: List[BatchAnalysisItem]
    comparison: Dict[str, Any] = Field(default_factory=dict)
    top_opportunity_id: Optional[int] = None
    average_score: float = Field(ge=0, le=100)

    class Config:
        from_attributes = True


class ApiMetadata(BaseModel):
    """Standard API response metadata"""
    total_count: int
    execution_time_ms: int
    api_version: str = "v1"
    timestamp: datetime


class OpportunitiesSearchResponse(BaseModel):
    """Response for opportunities search endpoint"""
    data: List[OpportunitySummary]
    metadata: ApiMetadata

    class Config:
        from_attributes = True


class OpportunityDetailResponse(BaseModel):
    """Response for opportunity detail endpoint"""
    data: OpportunityDetail
    metadata: ApiMetadata

    class Config:
        from_attributes = True


class OpportunitiesBatchAnalyzeResponse(BaseModel):
    """Response for batch analyze endpoint"""
    data: BatchAnalysisResponse
    metadata: ApiMetadata

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: datetime
