"""
Consultant Studio API Router
Three-path validation system: Validate Idea, Search Ideas, Identify Location
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.consultant_studio import ConsultantStudioService
from app.models.consultant_activity import ConsultantActivity

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
    
    Uses DeepSeek for pattern analysis and Claude for viability reports.
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
    """
    import asyncio
    service = ConsultantStudioService(db)
    
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
