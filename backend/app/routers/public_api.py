"""
OppGrid Public API v1 — Sub-application

Mounted at /v1 by the main FastAPI app.
Swagger UI: /v1/docs
Auth: X-API-Key header (og_live_… or og_test_…)

Rate limits by tier (Spec v2.1):
  builder / api_starter:      10 rpm /  250 req/day   — opportunities > 31 days old
  scaler  / api_professional: 50 rpm /  1 250 req/day — opportunities > 8 days old
  enterprise / api_enterprise: 500 rpm / 10 000 req/day — all opportunities

Monthly opportunity caps (hard caps with $30/opp overage):
  builder / api_starter:       3 opps / month
  scaler  / api_professional: 15 opps / month
  enterprise / api_enterprise: 75 opps / month
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.db.database import get_db
from app.models.api_key import APIKey
from app.models.api_usage import APIUsage
from app.models.opportunity import Opportunity
from app.models.detected_trend import DetectedTrend
from app.models.tier_config import TierConfig
from app.middleware.api_auth import get_authenticated_key, require_scope, APIAuthError
from app.middleware.usage_tracking import UsageTrackingMiddleware
from app.services import api_key_service
from app.services.opportunity_access_service import OpportunityAccessService
from app.schemas.v1_public import (
    ApiOpportunityResponse,
    PaginatedOpportunities,
    ApiTrendResponse,
    PaginatedTrends,
    ApiMarketResponse,
    PaginatedMarkets,
    UsageStatsResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# slowapi limiter — per-API-key rate limiting
# ---------------------------------------------------------------------------

def _key_identifier(request: Request) -> str:
    """
    Unique identifier for the slowapi bucket.

    Uses the API key ID *and* its rpm limit encoded as "{uuid}:{rpm}" so that
    ``dynamic_rate_limit`` can parse the limit without needing a DB look-up.
    Falls back to the client IP address for unauthenticated requests.
    """
    api_key: Optional[APIKey] = getattr(request.state, "api_key", None)
    if api_key is not None:
        # Encode the rpm into the key so dynamic_rate_limit can read it.
        return f"{api_key.id}:{api_key.rate_limit_rpm}"
    return get_remote_address(request)


def dynamic_rate_limit(key: str) -> str:
    """
    Return the per-endpoint rate-limit string based on the API key tier.

    slowapi calls this with the return value of ``_key_identifier`` when the
    callable has a parameter named exactly ``key``.  We encode the rpm into
    the bucket key string so we can recover it here without a DB look-up.
    """
    if ":" in key:
        try:
            _uuid, rpm = key.rsplit(":", 1)
            return f"{int(rpm)}/minute"
        except (ValueError, AttributeError):
            pass
    return "60/minute"


# key_func identifies *who* is making the request (bucket key).
# dynamic_rate_limit determines *how many* requests they may make.
limiter = Limiter(key_func=_key_identifier, default_limits=[])


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

### Rate Limits (v2.1)
| Tier                | RPM | Daily  |
|---------------------|-----|--------|
| builder / api_starter      | 10  | 250    |
| scaler / api_professional  | 50  | 1,250  |
| enterprise / api_enterprise | 500 | 10,000 |

Rate limit headers are included in every response:
- `X-RateLimit-Limit` — RPM ceiling
- `X-RateLimit-Remaining` — RPM window remaining
- `X-Daily-Limit` — daily ceiling
- `X-Daily-Remaining` — daily quota remaining

### Monthly Opportunity Allowance (Hard Caps)
| Tier                | Included / Month | Overage |
|---------------------|-----------------|---------|
| explorer            | 0               | $30/opp |
| builder / api_starter      | 3               | $30/opp |
| scaler / api_professional  | 15              | $30/opp |
| enterprise / api_enterprise | 75              | $30/opp |

Accessing `GET /v1/opportunities/{id}` consumes one slot.
Re-access in the same billing month is **free**.
When allowance is exhausted, pass `?confirm_overage=true` to proceed ($30 charged).

Monthly usage headers on every response:
- `X-Monthly-Included` / `X-Monthly-Used` / `X-Monthly-Remaining`
- `X-Monthly-Overage` / `X-Monthly-Overage-Cost` / `X-Overage-Rate`
- `X-Billing-Month` / `X-Billing-Resets`

### Data Freshness
- **Explorer**: opportunities older than 91 days
- **Builder / API Starter**: opportunities older than 31 days
- **Scaler / API Professional**: opportunities older than 8 days
- **Enterprise / API Enterprise**: real-time access to all opportunities

### Pagination
All list endpoints accept `page` (1-indexed, default 1) and `limit`
(1–100, default 20) query parameters.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Attach slowapi limiter to v1_app state
v1_app.state.limiter = limiter

# CORS
v1_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Async usage tracking (dedicated module)
v1_app.add_middleware(UsageTrackingMiddleware)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

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


@v1_app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Convert slowapi RateLimitExceeded into canonical {"error": ..., "detail": ...} shape."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Rate limit exceeded. Slow down and retry after the window resets.",
        },
        headers={"Retry-After": "60"},
    )


# ---------------------------------------------------------------------------
# Helper: build tier-based freshness filter
# ---------------------------------------------------------------------------

def _freshness_filter(tier: str):
    """
    Return a SQLAlchemy filter expression for data freshness based on tier.

    Uses TierConfig.freshness_days (Spec v2.1):
      explorer:             91+ days old
      builder / api_starter: 31+ days old
      scaler / api_professional: 8+ days old
      enterprise / api_enterprise: real-time (no filter)

    Legacy tier names are mapped to their v2.1 equivalents.
    """
    freshness_days = TierConfig.get_freshness_days(tier)
    if freshness_days == 0:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=freshness_days)
    return Opportunity.created_at <= cutoff


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

@v1_app.get(
    "/opportunities",
    response_model=PaginatedOpportunities,
    tags=["Opportunities"],
    summary="List business opportunities",
)
@limiter.limit(dynamic_rate_limit)
def list_opportunities(
    request: Request,
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
    summary="Get a single opportunity (consumes monthly allowance)",
)
@limiter.limit(dynamic_rate_limit)
def get_opportunity(
    request: Request,
    opportunity_id: int,
    confirm_overage: bool = Query(
        False,
        description=(
            "Set to true to confirm a $30 overage charge when monthly "
            "allowance is exhausted."
        ),
    ),
    api_key: APIKey = Depends(require_scope("read:opportunities")),
    db: Session = Depends(get_db),
):
    """
    Retrieve a single approved opportunity by its integer ID.

    **Consumes 1 from your monthly opportunity allowance.**
    Re-accessing the same opportunity in the same billing month is free.
    When your allowance is exhausted, a `402 Payment Required` response is
    returned. Pass `?confirm_overage=true` to proceed and be charged $30.

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

    # --- Monthly allowance check + access recording ----------------------
    svc = OpportunityAccessService()

    # Try to get Stripe customer ID for overage billing
    stripe_customer_id = None
    try:
        from app.models.subscription import Subscription
        sub = db.query(Subscription).filter(
            Subscription.user_id == api_key.user_id
        ).first()
        if sub:
            stripe_customer_id = sub.stripe_customer_id
    except Exception:
        pass

    result = svc.check_and_record_access(
        db=db,
        user_id=api_key.user_id,
        tier=api_key.tier,
        opportunity_id=opportunity_id,
        api_key_id=str(api_key.id),
        access_type="api",
        confirm_overage=confirm_overage,
        stripe_customer_id=stripe_customer_id,
    )

    if result.get("requires_overage_confirmation"):
        usage = result["usage"]
        cap = TierConfig.get_monthly_cap(api_key.tier)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "overage_confirmation_required",
                "message": (
                    f"You've used all {cap} included opportunities this month."
                ),
                "overage_cost": result["overage_cost"],
                "usage": usage,
                "options": {
                    "confirm": {
                        "url": f"/v1/opportunities/{opportunity_id}?confirm_overage=true",
                        "cost": result["overage_cost"],
                    },
                    "upgrade": {
                        "url": "https://oppgrid.com/upgrade",
                    },
                },
            },
        )

    # Stash access result for the response middleware (monthly headers)
    request.state.monthly_usage = svc.get_usage(
        db, api_key.user_id, api_key.tier
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
@limiter.limit(dynamic_rate_limit)
def list_trends(
    request: Request,
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
@limiter.limit(dynamic_rate_limit)
def list_markets(
    request: Request,
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
@limiter.limit(dynamic_rate_limit)
def get_market_by_region(
    request: Request,
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
@limiter.limit(dynamic_rate_limit)
def get_usage_stats(
    request: Request,
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
@limiter.limit(dynamic_rate_limit)
def v1_root(
    request: Request,
    api_key: APIKey = Depends(get_authenticated_key),
):
    return {
        "api": "OppGrid Public API",
        "version": "1.0.0",
        "docs": "/v1/docs",
        "tier": api_key.tier,
        "scopes": api_key.scopes or [],
    }
