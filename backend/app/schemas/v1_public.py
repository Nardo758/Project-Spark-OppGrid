"""
Pydantic schemas for the OppGrid Public API v1 endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ApiOpportunityResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    ai_opportunity_score: Optional[int] = None
    ai_market_size_estimate: Optional[str] = None
    ai_target_audience: Optional[str] = None
    ai_competition_level: Optional[str] = None
    growth_rate: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedOpportunities(BaseModel):
    data: List[ApiOpportunityResponse]
    total: int
    page: int
    limit: int
    has_next: bool


class ApiTrendResponse(BaseModel):
    id: int
    trend_name: str
    trend_strength: int
    category: Optional[str] = None
    opportunities_count: int = 0
    growth_rate: Optional[float] = None
    detected_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedTrends(BaseModel):
    data: List[ApiTrendResponse]
    total: int
    page: int
    limit: int
    has_next: bool


class ApiMarketResponse(BaseModel):
    category: str
    total_opportunities: int
    avg_score: Optional[float] = None
    top_regions: List[str] = Field(default_factory=list)


class PaginatedMarkets(BaseModel):
    data: List[ApiMarketResponse]
    total: int


class UsageStatsResponse(BaseModel):
    api_key_name: str
    tier: str
    rate_limit_rpm: int
    daily_limit: int
    usage_today: int
    usage_remaining_today: int
    scopes: List[str]


class ApiErrorResponse(BaseModel):
    error: str
    detail: str
