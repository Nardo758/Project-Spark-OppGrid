"""
OppGrid Public API v1 — Sub-application

Mounted at /v1 by the main FastAPI app.
Swagger UI: /v1/docs
Auth: X-API-Key header (og_live_… or og_test_…)

Rate limits by tier:
  starter:      10 rpm /  1 000 req/day  — opportunities > 30 days old
  professional: 100 rpm / 10 000 req/day  — opportunities > 7 days old
  enterprise:   1 000 rpm / 100 000 req/day — all opportunities
"""
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.db.database import get_db, SessionLocal
from app.models.api_key import APIKey
from app.models.api_usage import APIUsage
from app.models.opportunity import Opportunity
from app.models.detected_trend import DetectedTrend
from app.middleware.api_auth import get_authenticated_key, require_scope, APIAuthError
from app.services import api_key_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sub-application
# ---------------------------------------------------------------------------

v1_app = FastAPI(
    title="OppGrid Public API",
    version="1.0.0",
    description="""
## OppGrid Public API v1

Access business intelligence data programmatically.

### Authentication
Include your API key in every request header:
```
X-API-Key: og_live_your_key_here
```
Keys are created from your OppGrid account settings.

### Rate Limits
| Tier         | Requests / min | Requests / day |
|--------------|---------------|----------------|
| starter      | 10            | 1,000          |
| professional | 100           | 10,000         |
| enterprise   | 1,000         | 100,000        |

Rate limit headers are included in every response:
- `X-RateLimit-Remaining` — RPM window remaining
- `X-RateLimit-Remaining-Daily` — daily quota remaining

### Data Freshness
- **Starter**: opportunities older than 30 days
- **Professional**: opportunities older than 7 days
- **Enterprise**: real-time access to all opportunities

### Pagination
All list endpoints accept `page` (1-indexed, default 1) and `limit`
(1–100, default 20) query parameters.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

v1_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@v1_app.exception_handler(APIAuthError)
async def api_auth_error_handler(request: Request, exc: APIAuthError):
    """Convert APIAuthError into the canonical public API error shape: {"error": ..., "detail": ...}."""
    headers = {"Content-Type": "application/json"}
    headers.update(exc.extra_headers)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "detail": exc.detail},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Response-side middleware: rate-limit headers + usage recording
# ---------------------------------------------------------------------------

@v1_app.middleware("http")
async def response_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

    if hasattr(request.state, "rpm_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rpm_remaining)
    if hasattr(request.state, "daily_remaining"):
        response.headers["X-RateLimit-Remaining-Daily"] = str(
            request.state.daily_remaining
        )

    # Record usage for all v1 requests (authenticated or not).
    # api_key_id is None for unauthenticated requests (still recorded for audit).
    # Uses a dedicated SessionLocal so we never touch the request's session
    # after the response has already been sent.
    api_key: Optional[APIKey] = getattr(request.state, "api_key", None)
    db = SessionLocal()
    try:
        api_key_service.record_usage(
            api_key_id=api_key.id if api_key is not None else None,
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            db=db,
        )
    finally:
        db.close()

    return response


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helper: build tier-based freshness filter
# ---------------------------------------------------------------------------

def _freshness_filter(tier: str):
    """Return a SQLAlchemy filter expression for data freshness based on tier."""
    if tier == "starter":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return Opportunity.created_at <= cutoff
    if tier == "professional":
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        return Opportunity.created_at <= cutoff
    # enterprise: no date restriction
    return None


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

@v1_app.get(
    "/opportunities",
    response_model=PaginatedOpportunities,
    tags=["Opportunities"],
    summary="List business opportunities",
)
def list_opportunities(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    category: Optional[str] = Query(None, description="Filter by category (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    region: Optional[str] = Query(None, description="Filter by region / state (partial match)"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum AI opportunity score"),
    api_key: APIKey = Depends(require_scope("read:opportunities")),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of approved business opportunities.

    Results are ordered by AI opportunity score (descending), then by
    creation date. Data freshness depends on your API key tier.

    **Requires scope:** `read:opportunities`
    """
    filters = [
        Opportunity.status == "active",
        Opportunity.moderation_status == "approved",
    ]

    freshness = _freshness_filter(api_key.tier)
    if freshness is not None:
        filters.append(freshness)

    if category:
        filters.append(Opportunity.category.ilike(f"%{category}%"))
    if city:
        filters.append(Opportunity.city.ilike(f"%{city}%"))
    if region:
        filters.append(Opportunity.region.ilike(f"%{region}%"))
    if min_score is not None:
        filters.append(Opportunity.ai_opportunity_score >= min_score)

    query = db.query(Opportunity).filter(*filters)
    total = query.count()
    offset = (page - 1) * limit

    opportunities = (
        query.order_by(
            Opportunity.ai_opportunity_score.desc().nullslast(),
            Opportunity.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedOpportunities(
        data=[
            ApiOpportunityResponse(
                id=o.id,
                title=o.title,
                description=o.description[:500] if o.description else None,
                category=o.category,
                city=o.city,
                region=o.region,
                ai_opportunity_score=o.ai_opportunity_score,
                ai_market_size_estimate=o.ai_market_size_estimate,
                ai_target_audience=o.ai_target_audience,
                ai_competition_level=o.ai_competition_level,
                growth_rate=o.growth_rate,
                created_at=o.created_at,
            )
            for o in opportunities
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=(offset + limit) < total,
    )


@v1_app.get(
    "/opportunities/{opportunity_id}",
    response_model=ApiOpportunityResponse,
    tags=["Opportunities"],
    summary="Get a single opportunity",
)
def get_opportunity(
    opportunity_id: int,
    api_key: APIKey = Depends(require_scope("read:opportunities")),
    db: Session = Depends(get_db),
):
    """
    Retrieve a single approved opportunity by its integer ID.

    **Requires scope:** `read:opportunities`
    """
    filters = [
        Opportunity.id == opportunity_id,
        Opportunity.status == "active",
        Opportunity.moderation_status == "approved",
    ]

    freshness = _freshness_filter(api_key.tier)
    if freshness is not None:
        filters.append(freshness)

    opportunity = db.query(Opportunity).filter(*filters).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    return ApiOpportunityResponse(
        id=opportunity.id,
        title=opportunity.title,
        description=opportunity.description,
        category=opportunity.category,
        city=opportunity.city,
        region=opportunity.region,
        ai_opportunity_score=opportunity.ai_opportunity_score,
        ai_market_size_estimate=opportunity.ai_market_size_estimate,
        ai_target_audience=opportunity.ai_target_audience,
        ai_competition_level=opportunity.ai_competition_level,
        growth_rate=opportunity.growth_rate,
        created_at=opportunity.created_at,
    )


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

@v1_app.get(
    "/trends",
    response_model=PaginatedTrends,
    tags=["Trends"],
    summary="List detected market trends",
)
def list_trends(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_strength: Optional[int] = Query(None, ge=0, le=100, description="Minimum trend strength (0–100)"),
    api_key: APIKey = Depends(require_scope("read:trends")),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of AI-detected market trends, ordered by
    trend strength (descending).

    **Requires scope:** `read:trends`
    """
    filters = []
    if category:
        filters.append(DetectedTrend.category.ilike(f"%{category}%"))
    if min_strength is not None:
        filters.append(DetectedTrend.trend_strength >= min_strength)

    query = db.query(DetectedTrend).filter(*filters)
    total = query.count()
    offset = (page - 1) * limit

    trends = (
        query.order_by(
            DetectedTrend.trend_strength.desc(),
            DetectedTrend.detected_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedTrends(
        data=[
            ApiTrendResponse(
                id=t.id,
                trend_name=t.trend_name,
                trend_strength=t.trend_strength,
                category=t.category,
                opportunities_count=t.opportunities_count,
                growth_rate=t.growth_rate,
                detected_at=t.detected_at,
            )
            for t in trends
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

@v1_app.get(
    "/markets",
    response_model=PaginatedMarkets,
    tags=["Markets"],
    summary="List market intelligence by category",
)
def list_markets(
    api_key: APIKey = Depends(require_scope("read:markets")),
    db: Session = Depends(get_db),
):
    """
    Return aggregated opportunity counts, average AI scores, and top
    regions for each market category.

    **Requires scope:** `read:markets`
    """
    base_filters = [
        Opportunity.status == "active",
        Opportunity.moderation_status == "approved",
        Opportunity.category.isnot(None),
    ]

    freshness = _freshness_filter(api_key.tier)
    if freshness is not None:
        base_filters.append(freshness)

    rows = (
        db.query(
            Opportunity.category,
            sqlfunc.count(Opportunity.id).label("total_opportunities"),
            sqlfunc.avg(Opportunity.ai_opportunity_score).label("avg_score"),
        )
        .filter(*base_filters)
        .group_by(Opportunity.category)
        .order_by(sqlfunc.count(Opportunity.id).desc())
        .all()
    )

    markets: List[ApiMarketResponse] = []
    for row in rows:
        region_rows = (
            db.query(Opportunity.region)
            .filter(
                *base_filters,
                Opportunity.category == row.category,
                Opportunity.region.isnot(None),
            )
            .group_by(Opportunity.region)
            .order_by(sqlfunc.count(Opportunity.id).desc())
            .limit(3)
            .all()
        )
        markets.append(
            ApiMarketResponse(
                category=row.category,
                total_opportunities=row.total_opportunities,
                avg_score=(
                    round(float(row.avg_score), 1) if row.avg_score else None
                ),
                top_regions=[r[0] for r in region_rows if r[0]],
            )
        )

    return PaginatedMarkets(data=markets, total=len(markets))


@v1_app.get(
    "/markets/{region}",
    response_model=PaginatedMarkets,
    tags=["Markets"],
    summary="List market intelligence for a specific region",
)
def get_market_by_region(
    region: str,
    api_key: APIKey = Depends(require_scope("read:markets")),
    db: Session = Depends(get_db),
):
    """
    Return aggregated opportunity counts, average AI scores, and top
    categories for a specific region.

    **Requires scope:** `read:markets`
    """
    base_filters = [
        Opportunity.status == "active",
        Opportunity.moderation_status == "approved",
        Opportunity.category.isnot(None),
        Opportunity.region.ilike(f"%{region}%"),
    ]

    freshness = _freshness_filter(api_key.tier)
    if freshness is not None:
        base_filters.append(freshness)

    rows = (
        db.query(
            Opportunity.category,
            sqlfunc.count(Opportunity.id).label("total_opportunities"),
            sqlfunc.avg(Opportunity.ai_opportunity_score).label("avg_score"),
        )
        .filter(*base_filters)
        .group_by(Opportunity.category)
        .order_by(sqlfunc.count(Opportunity.id).desc())
        .all()
    )

    markets: List[ApiMarketResponse] = []
    for row in rows:
        region_rows = (
            db.query(Opportunity.region)
            .filter(
                *base_filters,
                Opportunity.category == row.category,
                Opportunity.region.isnot(None),
            )
            .group_by(Opportunity.region)
            .order_by(sqlfunc.count(Opportunity.id).desc())
            .limit(3)
            .all()
        )
        markets.append(
            ApiMarketResponse(
                category=row.category,
                total_opportunities=row.total_opportunities,
                avg_score=(
                    round(float(row.avg_score), 1) if row.avg_score else None
                ),
                top_regions=[r[0] for r in region_rows if r[0]],
            )
        )

    return PaginatedMarkets(data=markets, total=len(markets))


# ---------------------------------------------------------------------------
# Usage stats
# ---------------------------------------------------------------------------

@v1_app.get(
    "/usage/stats",
    response_model=UsageStatsResponse,
    tags=["Usage"],
    summary="Get API key usage statistics",
)
def get_usage_stats(
    api_key: APIKey = Depends(get_authenticated_key),
    db: Session = Depends(get_db),
):
    """
    Return today's request count, remaining daily quota, tier limits,
    and the scopes assigned to the authenticated API key.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    usage_today = (
        db.query(sqlfunc.count(APIUsage.id))
        .filter(
            APIUsage.api_key_id == api_key.id,
            APIUsage.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    return UsageStatsResponse(
        api_key_name=api_key.name,
        tier=api_key.tier,
        rate_limit_rpm=api_key.rate_limit_rpm,
        daily_limit=api_key.daily_limit,
        usage_today=usage_today,
        usage_remaining_today=max(0, api_key.daily_limit - usage_today),
        scopes=api_key.scopes or [],
    )


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@v1_app.get("/", include_in_schema=False)
def v1_root():
    return {
        "api": "OppGrid Public API",
        "version": "1.0.0",
        "docs": "/v1/docs",
    }
