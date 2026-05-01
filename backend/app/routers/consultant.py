"""
Consultant Studio API Router
Three-path validation system: Validate Idea, Search Ideas, Identify Location
Enhanced with Tier A/B location identification system
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import asyncio

from app.db.database import get_db
from app.services.consultant_studio import ConsultantStudioService
from app.services.success_profile.identify_location_service import IdentifyLocationService
from app.models.consultant_activity import ConsultantActivity
from app.models.user import User
from app.schemas.identify_location import (
    IdentifyLocationRequest, IdentifyLocationResult,
    CandidateDetailResponse, PromoteCandidateRequest, PromoteCandidateResponse,
    TargetMarket, UserTier
)

router = APIRouter(prefix="/consultant", tags=["Consultant Studio"])


class ValidateIdeaRequest(BaseModel):
    idea_description: str = Field(..., min_length=10, max_length=5000)
    business_context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class ValidateIdeaResponse(BaseModel):
    success: bool
    idea_description: Optional[str] = None
    recommendation: Optional[str] = None
    online_score: Optional[int] = None
    physical_score: Optional[int] = None
    pattern_analysis: Optional[Dict[str, Any]] = None
    viability_report: Optional[Dict[str, Any]] = None
    similar_opportunities: Optional[List[Dict[str, Any]]] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    # Enriched fields from ReportDataService
    confidence_score: Optional[int] = None
    verdict_summary: Optional[str] = None
    verdict_detail: Optional[str] = None
    market_intelligence: Optional[Dict[str, Any]] = None
    advantages: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    four_ps_scores: Optional[Dict[str, Any]] = None
    feasibility_preview: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, Any]] = None
    # Intelligence card fields
    intel_verdict: Optional[Dict[str, Any]] = None
    intel_metrics: Optional[List[Dict[str, Any]]] = None
    intel_insights: Optional[List[Dict[str, Any]]] = None
    intel_tags: Optional[List[str]] = None
    intel_cta: Optional[Dict[str, Any]] = None
    # Canonical top-level fields
    narrative_verdict: Optional[str] = None
    validation_score: Optional[int] = None
    market_signals_count: Optional[int] = None
    proceed_recommendation: Optional[str] = None
    competition_level: Optional[str] = None
    inferred_category: Optional[str] = None
    demand_signal_quote: Optional[str] = None
    key_competitors: Optional[List[str]] = None
    market_heat_sources: Optional[List[str]] = None


class SearchIdeasRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    min_score: Optional[int] = None
    time_range: Optional[str] = None
    quality_filter: Optional[str] = None
    session_id: Optional[str] = None


class SearchIdeasResponse(BaseModel):
    success: bool
    opportunities: Optional[List[Dict[str, Any]]] = None
    trends: Optional[List[Dict[str, Any]]] = None
    synthesis: Optional[Dict[str, Any]] = None
    total_count: Optional[int] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    # Enriched fields
    ai_synthesis: Optional[str] = None
    opportunity_four_ps: Optional[Dict[str, Any]] = None
    # Intelligence card fields
    intel_verdict: Optional[Dict[str, Any]] = None
    intel_metrics: Optional[List[Dict[str, Any]]] = None
    intel_top_signals: Optional[List[Dict[str, Any]]] = None
    intel_tags: Optional[List[str]] = None
    intel_cta: Optional[Dict[str, Any]] = None
    # Canonical top-level fields
    narrative_summary: Optional[str] = None
    narrative_verdict: Optional[str] = None
    signal_surge_pct: Optional[int] = None
    avg_viability_score: Optional[int] = None
    top_signals_this_week: Optional[List[Dict[str, Any]]] = None
    # Gating fields for preview vs full data
    is_preview_mode: bool = False
    preview_cta: Optional[Dict[str, Any]] = None


class IdentifyLocationRequest(BaseModel):
    city: str = Field(..., min_length=2, max_length=255)
    business_description: str = Field(..., min_length=3, max_length=500)
    additional_params: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class IdentifyLocationResponse(BaseModel):
    success: bool
    city: Optional[str] = None
    business_description: Optional[str] = None
    inferred_category: Optional[str] = None
    geo_analysis: Optional[Dict[str, Any]] = None
    market_report: Optional[Dict[str, Any]] = None
    site_recommendations: Optional[List[Dict[str, Any]]] = None
    map_data: Optional[Dict[str, Any]] = None
    from_cache: Optional[bool] = None
    cache_hit_count: Optional[int] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    # Enriched fields
    four_ps_scores: Optional[Dict[str, Any]] = None
    four_ps_details: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, Any]] = None
    # Intelligence card fields
    intel_verdict: Optional[Dict[str, Any]] = None
    intel_metrics: Optional[List[Dict[str, Any]]] = None
    intel_demographics: Optional[Dict[str, Any]] = None
    intel_micro_markets: Optional[List[Dict[str, Any]]] = None
    intel_tags: Optional[List[str]] = None
    intel_cta: Optional[Dict[str, Any]] = None
    # Canonical top-level fields
    narrative_summary: Optional[str] = None
    proceed_recommendation: Optional[str] = None
    avg_rating: Optional[float] = None
    foot_traffic_growth: Optional[float] = None
    density_per_residents: Optional[str] = None
    demographic_snapshot: Optional[Dict[str, Any]] = None
    micro_markets: Optional[List[Dict[str, Any]]] = None


class CloneSuccessRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    business_address: str = Field(..., min_length=5, max_length=500)
    target_city: Optional[str] = Field(default=None, max_length=255, description="Target city to search for similar locations")
    target_state: Optional[str] = Field(default=None, max_length=2, description="Target state abbreviation (e.g., FL, TX)")
    radius_miles: int = Field(default=3, ge=1, le=10)
    session_id: Optional[str] = None


class MatchingLocation(BaseModel):
    """A matching location with coordinates for map display"""
    name: str
    city: str
    state: str
    lat: float
    lng: float
    similarity_score: int
    demographics_match: int
    competition_match: int
    population: Optional[int] = None
    median_income: Optional[int] = None
    competition_count: Optional[int] = None
    key_factors: List[str] = []


class CloneSuccessResponse(BaseModel):
    success: bool
    source_business: Optional[Dict[str, Any]] = None
    matching_locations: Optional[List[MatchingLocation]] = None
    analysis_radius_miles: int = 3
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    # Enriched fields
    target_four_ps: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, Any]] = None
    # Intelligence card fields
    intel_verdict: Optional[Dict[str, Any]] = None
    intel_metrics: Optional[List[Dict[str, Any]]] = None
    intel_why_it_works: Optional[List[str]] = None
    intel_insights: Optional[List[Dict[str, Any]]] = None
    intel_tags: Optional[List[str]] = None
    intel_cta: Optional[Dict[str, Any]] = None
    # Canonical top-level fields
    narrative_summary: Optional[str] = None
    replicability_label: Optional[str] = None
    est_startup_cost: Optional[str] = None
    market_gap_pct: Optional[int] = None
    why_it_works: Optional[List[str]] = None
    differentiation_needed: Optional[str] = None


class DeepCloneRequest(BaseModel):
    source_business_name: str = Field(..., min_length=2, max_length=255)
    source_business_address: str = Field(..., min_length=5, max_length=500)
    target_city: str = Field(..., min_length=2, max_length=255)
    session_id: Optional[str] = None


class DeepCloneResponse(BaseModel):
    success: bool
    source_business: Optional[Dict[str, Any]] = None
    target_city: Optional[str] = None
    three_mile_analysis: Optional[Dict[str, Any]] = None
    five_mile_analysis: Optional[Dict[str, Any]] = None
    match_score: Optional[int] = None
    key_factors: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
    requires_payment: Optional[bool] = None
    error: Optional[str] = None


class ActivityLogResponse(BaseModel):
    id: int
    path: str
    action: str
    result_summary: Optional[str] = None
    ai_model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: str


@router.post("/validate-idea", response_model=ValidateIdeaResponse)
async def validate_idea(
    request: ValidateIdeaRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    Path 1: Validate Idea - Online vs Physical decision engine
    
    Analyzes a business idea and recommends whether it should be:
    - ONLINE: Digital/remote business model
    - PHYSICAL: Location-based business model
    - HYBRID: Combination of both
    
    AI GENERATION WORKFLOW (Two-Step Process):
    
    Step 1: DeepSeek Draft (8-15 seconds)
    - Generates initial content for all 6 report sections
    - Analytical, data-driven approach
    - Sections: Executive Summary, Market Opportunity, Business Model,
              Financial Viability, Risk Assessment, Next Steps
    - Calls run in parallel for speed
    
    Step 2: Claude Opus Polish (5-10 seconds)
    - Refines and polishes all sections from DeepSeek
    - Improves clarity, tone, and actionability
    - Ensures institutional, professional quality
    - Single sequential call with all sections
    
    Total Generation Time: ~15-25 seconds
    
    Data Sources:
    - report_data_service: Market data, financial benchmarks
    - detected_trends: Market trends and signals
    - market_growth_trajectories: Growth metrics
    - Similar opportunities lookup: Proof-of-concept examples
    
    Response includes 6 comprehensive report sections plus scores/metrics.
    """
    import asyncio
    service = ConsultantStudioService(db)
    
    try:
        result = await asyncio.wait_for(
            service.validate_idea(
                user_id=user_id,
                idea_description=request.idea_description,
                business_context=request.business_context,
                session_id=request.session_id,
            ),
            timeout=65.0  # Increased from 40s to 65s (AI timeout is 60s + 5s buffer)
        )
        return ValidateIdeaResponse(**result)
    except asyncio.TimeoutError:
        return ValidateIdeaResponse(
            success=False,
            error="Analysis timed out after 65 seconds. Please try a simpler question or try again later.",
            idea_description=request.idea_description,
            recommendation="hybrid",
            online_score=50,
            physical_score=50,
        )
    except Exception as e:
        return ValidateIdeaResponse(
            success=False,
            error=f"Analysis failed: {str(e)}",
            idea_description=request.idea_description,
            recommendation="hybrid",
            online_score=50,
            physical_score=50,
        )


@router.post("/search-ideas", response_model=SearchIdeasResponse)
async def search_ideas(
    request: SearchIdeasRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    Path 2: Search Ideas - Database exploration with trend detection
    
    Searches validated opportunities with AI-powered trend detection.
    Returns opportunities, detected trends, and AI synthesis.
    
    GATING LOGIC:
    - FREE/GUEST users: See trends + top 2-3 opportunity previews (title, category, score only) + intelligence card + CTA
    - AUTHENTICATED PAID users: See all trends + full opportunity data (descriptions, all opportunities, competition analysis)
    """
    import asyncio
    from app.models import User
    
    service = ConsultantStudioService(db)
    
    # Check user subscription status
    user = db.query(User).filter(User.id == user_id).first()
    
    # Determine if user has paid access
    has_paid_access = False
    if user and user.subscription:
        paid_tiers = [
            'BUILDER', 'SCALER', 'ENTERPRISE',
            'STARTER', 'GROWTH', 'PRO', 'TEAM', 'BUSINESS',  # Legacy tiers
            'API_STARTER', 'API_PROFESSIONAL', 'API_ENTERPRISE'  # API tiers
        ]
        if user.subscription.tier and user.subscription.tier.upper() in paid_tiers:
            # Also verify subscription is active
            active_statuses = ['ACTIVE', 'TRIALING']
            if user.subscription.status.upper() in active_statuses:
                has_paid_access = True
    
    filters = {
        "query": request.query,
        "category": request.category,
        "min_score": request.min_score,
        "time_range": request.time_range,
        "quality_filter": request.quality_filter,
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}
    
    try:
        result = await asyncio.wait_for(
            service.search_ideas(
                user_id=user_id,
                filters=filters,
                session_id=request.session_id,
                is_paid_user=has_paid_access,
            ),
            timeout=65.0  # Increased from 15s to 65s for AI synthesis
        )
        return SearchIdeasResponse(**result)
    except asyncio.TimeoutError:
        return SearchIdeasResponse(
            success=False,
            error="Search timed out after 65 seconds. Please try a simpler query.",
        )
    except Exception as e:
        return SearchIdeasResponse(
            success=False,
            error=f"Search failed: {str(e)}",
        )


@router.post("/identify-location", response_model=IdentifyLocationResponse)
async def identify_location(
    request: IdentifyLocationRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    Path 3: Identify Location - Geographic intelligence
    
    Analyzes a location for business viability based on a natural language
    description of the business (e.g., "coffee shop with drive-thru").
    AI automatically categorizes the business type.
    
    Results are cached for 30 days.
    """
    import asyncio
    service = ConsultantStudioService(db)
    
    try:
        result = await asyncio.wait_for(
            service.identify_location(
                user_id=user_id,
                city=request.city,
                business_description=request.business_description,
                additional_params=request.additional_params,
                session_id=request.session_id,
            ),
            timeout=65.0  # Increased from 25s to 65s for geo analysis + AI
        )
        return IdentifyLocationResponse(**result)
    except asyncio.TimeoutError:
        return IdentifyLocationResponse(
            success=False,
            error="Analysis timed out after 65 seconds. Please try again with a simpler query.",
            city=request.city,
            business_type=request.business_description,
        )
    except Exception as e:
        return IdentifyLocationResponse(
            success=False,
            error=f"Analysis failed: {str(e)}",
            city=request.city,
            business_type=request.business_description,
        )


@router.post("/clone-success", response_model=CloneSuccessResponse)
async def clone_success(
    request: CloneSuccessRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    Path 4: Clone Success - Replicate successful business models
    
    Analyzes a successful business's location, demographics, and success factors,
    then finds similar markets where the model could be replicated.
    Uses configurable radius (3 or 5 miles) for trade area analysis.
    """
    import asyncio
    service = ConsultantStudioService(db)
    
    try:
        result = await asyncio.wait_for(
            service.clone_success(
                user_id=user_id,
                business_name=request.business_name,
                business_address=request.business_address,
                target_city=request.target_city,
                target_state=request.target_state,
                radius_miles=request.radius_miles,
                session_id=request.session_id,
            ),
            timeout=65.0  # Increased from 25s to 65s for location matching
        )
        return CloneSuccessResponse(**result)
    except asyncio.TimeoutError:
        return CloneSuccessResponse(
            success=False,
            error="Analysis timed out after 65 seconds. Please try again with a different business.",
            analysis_radius_miles=request.radius_miles,
        )
    except Exception as e:
        return CloneSuccessResponse(
            success=False,
            error=f"Analysis failed: {str(e)}",
            analysis_radius_miles=request.radius_miles,
        )


@router.post("/deep-clone", response_model=DeepCloneResponse)
async def deep_clone_analysis(
    request: DeepCloneRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
    paid: bool = False,
):
    """
    Premium: Deep Clone Analysis - Detailed 3mi and 5mi radius analysis for a specific target city.
    
    Requires payment or premium subscription. Analyzes:
    - Source business success factors
    - Target city demographics at 3-mile and 5-mile radius
    - Competition comparison
    - Match score and key factors
    """
    from app.models import User
    
    user = db.query(User).filter(User.id == user_id).first()
    has_premium_access = False
    
    if user and user.subscription:
        has_premium_access = user.subscription.tier in ['growth', 'pro', 'team', 'business', 'enterprise']
    
    if not has_premium_access and not paid:
        return DeepCloneResponse(
            success=False,
            requires_payment=True,
            error="This premium feature requires payment or a Builder+ subscription"
        )
    
    service = ConsultantStudioService(db)
    
    result = await service.deep_clone_analysis(
        user_id=user_id,
        source_business_name=request.source_business_name,
        source_business_address=request.source_business_address,
        target_city=request.target_city,
        session_id=request.session_id,
    )
    
    return DeepCloneResponse(**result)


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_activity_log(
    limit: int = 20,
    path: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """Get user's consultant activity history"""
    query = db.query(ConsultantActivity).filter(
        ConsultantActivity.user_id == user_id
    )
    
    if path:
        query = query.filter(ConsultantActivity.path == path)
    
    activities = query.order_by(
        ConsultantActivity.created_at.desc()
    ).limit(limit).all()
    
    return [
        ActivityLogResponse(
            id=a.id,
            path=a.path,
            action=a.action,
            result_summary=a.result_summary,
            ai_model_used=a.ai_model_used,
            processing_time_ms=a.processing_time_ms,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in activities
    ]


@router.get("/stats")
async def get_consultant_stats(
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """Get consultant studio usage statistics"""
    from sqlalchemy import func
    from app.models.detected_trend import DetectedTrend
    from app.models.location_analysis_cache import LocationAnalysisCache
    
    total_activities = db.query(func.count(ConsultantActivity.id)).filter(
        ConsultantActivity.user_id == user_id
    ).scalar() or 0
    
    path_counts = db.query(
        ConsultantActivity.path,
        func.count(ConsultantActivity.id)
    ).filter(
        ConsultantActivity.user_id == user_id
    ).group_by(ConsultantActivity.path).all()
    
    total_trends = db.query(func.count(DetectedTrend.id)).scalar() or 0
    cached_locations = db.query(func.count(LocationAnalysisCache.id)).scalar() or 0
    
    return {
        "total_activities": total_activities,
        "activities_by_path": {path: count for path, count in path_counts},
        "total_trends_detected": total_trends,
        "cached_locations": cached_locations,
    }


@router.get("/admin/analytics")
async def get_consultant_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    Admin analytics for Consultant Studio usage.
    Provides insights for trend analysis, lead generation, and content strategy.
    """
    from sqlalchemy import func, desc, text
    from datetime import datetime, timedelta
    from app.models.detected_trend import DetectedTrend
    from app.models.location_analysis_cache import LocationAnalysisCache
    from app.models.user import User
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    total_activities = db.query(func.count(ConsultantActivity.id)).filter(
        ConsultantActivity.created_at >= cutoff
    ).scalar() or 0
    
    unique_users = db.query(func.count(func.distinct(ConsultantActivity.user_id))).filter(
        ConsultantActivity.created_at >= cutoff
    ).scalar() or 0
    
    path_breakdown = db.query(
        ConsultantActivity.path,
        func.count(ConsultantActivity.id).label('count')
    ).filter(
        ConsultantActivity.created_at >= cutoff
    ).group_by(ConsultantActivity.path).all()
    
    top_ideas = db.execute(text("""
        SELECT 
            payload->>'idea' as idea,
            result_summary,
            COUNT(*) as search_count,
            MAX(created_at) as last_searched
        FROM consultant_activity
        WHERE path = 'validate_idea' 
        AND created_at >= :cutoff
        AND payload->>'idea' IS NOT NULL
        GROUP BY payload->>'idea', result_summary
        ORDER BY search_count DESC, last_searched DESC
        LIMIT 10
    """), {"cutoff": cutoff}).fetchall()
    
    top_locations = db.execute(text("""
        SELECT 
            payload->>'city' as city,
            payload->>'business_type' as business_type,
            COUNT(*) as search_count,
            MAX(created_at) as last_searched
        FROM consultant_activity
        WHERE path = 'identify_location'
        AND created_at >= :cutoff
        AND payload->>'city' IS NOT NULL
        GROUP BY payload->>'city', payload->>'business_type'
        ORDER BY search_count DESC
        LIMIT 10
    """), {"cutoff": cutoff}).fetchall()
    
    daily_activity = db.execute(text("""
        SELECT 
            DATE(created_at) as date,
            path,
            COUNT(*) as count
        FROM consultant_activity
        WHERE created_at >= :cutoff
        GROUP BY DATE(created_at), path
        ORDER BY date DESC
    """), {"cutoff": cutoff}).fetchall()
    
    recent_activities = db.query(ConsultantActivity).filter(
        ConsultantActivity.created_at >= cutoff
    ).order_by(desc(ConsultantActivity.created_at)).limit(20).all()
    
    avg_processing_time = db.query(
        ConsultantActivity.path,
        func.avg(ConsultantActivity.processing_time_ms).label('avg_time')
    ).filter(
        ConsultantActivity.created_at >= cutoff,
        ConsultantActivity.processing_time_ms.isnot(None)
    ).group_by(ConsultantActivity.path).all()
    
    potential_leads = db.execute(text("""
        SELECT 
            ca.user_id,
            u.email,
            u.name,
            COUNT(*) as activity_count,
            MAX(ca.created_at) as last_activity,
            STRING_AGG(DISTINCT ca.path, ', ') as paths_used
        FROM consultant_activity ca
        JOIN users u ON ca.user_id = u.id
        WHERE ca.created_at >= :cutoff
        GROUP BY ca.user_id, u.email, u.name
        HAVING COUNT(*) >= 2
        ORDER BY activity_count DESC
        LIMIT 20
    """), {"cutoff": cutoff}).fetchall()
    
    return {
        "summary": {
            "total_activities": total_activities,
            "unique_users": unique_users,
            "period_days": days,
        },
        "path_breakdown": [
            {"path": p, "count": c} for p, c in path_breakdown
        ],
        "top_ideas_validated": [
            {
                "idea": row.idea[:100] if row.idea else None,
                "result": row.result_summary,
                "count": row.search_count,
                "last_searched": row.last_searched.isoformat() if row.last_searched else None
            }
            for row in top_ideas
        ],
        "top_locations_searched": [
            {
                "city": row.city,
                "business_type": row.business_type,
                "count": row.search_count,
                "last_searched": row.last_searched.isoformat() if row.last_searched else None
            }
            for row in top_locations
        ],
        "daily_activity": [
            {"date": str(row.date), "path": row.path, "count": row.count}
            for row in daily_activity
        ],
        "avg_processing_time_ms": {
            path: int(avg) for path, avg in avg_processing_time if avg
        },
        "recent_activities": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "path": a.path,
                "action": a.action,
                "result_summary": a.result_summary,
                "processing_time_ms": a.processing_time_ms,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "payload_preview": str(a.payload)[:200] if a.payload else None
            }
            for a in recent_activities
        ],
        "potential_leads": [
            {
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "activity_count": row.activity_count,
                "last_activity": row.last_activity.isoformat() if row.last_activity else None,
                "paths_used": row.paths_used
            }
            for row in potential_leads
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Identify Location Service (Enhanced Tier A/B System)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/identify-location/search", response_model=IdentifyLocationResult)
async def identify_location_search(
    request: IdentifyLocationRequest,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    POST /api/consultant-studio/identify-location/search
    
    Main endpoint for location identification with Tier A (named markets) + Tier B (gap discovery).
    
    Request includes:
    - category: Business category (e.g., "coffee_shop_premium")
    - target_market: Market specification (metro, city, or point+radius)
    - market_boundary: Optional filters (ZIP codes, neighborhoods)
    - archetype_preference: Filter to specific archetypes
    - include_gap_discovery: Enable Tier B gap discovery
    
    Response includes:
    - Candidates grouped by archetype (pioneer, mainstream, specialist, anchor, experimental)
    - GeoJSON map data
    - Tier-based limits enforced
    - 7-day caching enabled
    
    Performance: <12s for typical metro + gap discovery enabled
    
    Tier Limits:
    - FREE: 1/month, named only (top 3 per archetype)
    - BUILDER: 5/month, with gaps (top 5 per archetype)
    - SCALER: 25/month, with gaps (unlimited)
    - ENTERPRISE: Unlimited with gaps
    """
    import time
    start_time = time.time()
    
    try:
        # Determine user tier (would normally fetch from user subscription)
        user_tier = UserTier.FREE  # Default to FREE
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj and user_obj.subscription:
            tier_mapping = {
                'BUILDER': UserTier.BUILDER,
                'SCALER': UserTier.SCALER,
                'ENTERPRISE': UserTier.ENTERPRISE,
            }
            user_tier = tier_mapping.get(user_obj.subscription.tier, UserTier.FREE)
        
        service = IdentifyLocationService(db)
        
        result = await asyncio.wait_for(
            asyncio.to_thread(
                service.identify_location,
                category=request.category,
                target_market=request.target_market,
                business_description=request.business_description,
                market_boundary=request.market_boundary,
                archetype_preference=request.archetype_preference,
                include_gap_discovery=request.include_gap_discovery,
                user_tier=user_tier,
                user_id=user_id,
            ),
            timeout=12.0
        )
        
        return result
    
    except asyncio.TimeoutError:
        return IdentifyLocationResult(
            request_id="timeout",
            category=request.category,
            target_market=request.target_market,
            candidates_by_archetype=[],
            total_candidates=0,
            tier=user_tier,
            candidates_shown=0,
            candidates_limited=False,
            map_data={},
            processing_time_ms=12000,
            named_markets_included=False,
            gap_markets_included=False,
        )
    
    except Exception as e:
        logger.error(f"Error in identify_location_search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/identify-location/{request_id}", response_model=IdentifyLocationResult)
async def get_identify_location_result(
    request_id: str = Path(..., description="Request ID from initial search"),
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    GET /api/consultant-studio/identify-location/{request_id}
    
    Retrieve cached identify location result.
    Results are cached for 7 days.
    """
    try:
        service = IdentifyLocationService(db)
        
        # Try to retrieve from cache
        cached = db.query(IdentifyLocationCache).filter(
            IdentifyLocationCache.request_id == request_id
        ).first()
        
        if not cached:
            raise HTTPException(status_code=404, detail="Request not found")
        
        result_dict = cached.result
        result = IdentifyLocationResult(**result_dict)
        result.from_cache = True
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving identify location result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/identify-location/{request_id}/candidate/{candidate_id}")
async def get_candidate_detail(
    request_id: str = Path(..., description="Request ID"),
    candidate_id: str = Path(..., description="Candidate ID"),
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    GET /api/consultant-studio/identify-location/{request_id}/candidate/{candidate_id}
    
    Get detailed view of a single candidate location.
    Includes demographics, competition analysis, foot traffic trends, risk assessment.
    """
    try:
        service = IdentifyLocationService(db)
        candidate_dict = service.get_candidate_detail(request_id, candidate_id)
        
        if not candidate_dict:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return {
            "candidate": candidate_dict,
            "demographics": None,  # TODO: Enrich with demographics API
            "local_competition": None,  # TODO: Enrich with business data
            "foot_traffic_trend": None,  # TODO: Enrich with foot traffic API
            "risk_summary": "Additional enrichment data would be loaded from APIs",
            "created_at": datetime.utcnow()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/identify-location/{request_id}/promote/{candidate_id}", response_model=PromoteCandidateResponse)
async def promote_candidate(
    request_id: str = Path(..., description="Request ID"),
    candidate_id: str = Path(..., description="Candidate ID"),
    promote_request: PromoteCandidateRequest = None,
    db: Session = Depends(get_db),
    user_id: int = 1,
):
    """
    POST /api/consultant-studio/identify-location/{request_id}/promote/{candidate_id}
    
    Convert a candidate location to a SuccessProfile.
    Creates a new record that user can track and build strategies around.
    
    Optional request body:
    {
        "notes": "Optional notes about why this location was chosen"
    }
    """
    try:
        if promote_request is None:
            promote_request = PromoteCandidateRequest()
        
        service = IdentifyLocationService(db)
        result = service.promote_candidate(
            request_id=request_id,
            candidate_id=candidate_id,
            user_id=user_id,
            user_notes=promote_request.notes if promote_request else None
        )
        
        return PromoteCandidateResponse(**result)
    
    except Exception as e:
        logger.error(f"Error promoting candidate: {e}")
        return PromoteCandidateResponse(
            success=False,
            error=str(e)
        )


# Import needed for imports at top of file
from app.models.micro_market import IdentifyLocationCache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
