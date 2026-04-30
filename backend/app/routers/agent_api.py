"""
Agent API Endpoints — AI Agent access to opportunities data.

Three endpoints for searching, fetching details, and batch analyzing opportunities.
All endpoints require X-Agent-Key header for authentication and are rate-limited to 1000 qpm.

Endpoints:
  GET  /api/v1/agents/opportunities/search - Search opportunities with filters
  GET  /api/v1/agents/opportunities/{id} - Get opportunity detail
  POST /api/v1/agents/opportunities/batch-analyze - Batch analyze opportunities
"""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.models.api_key import APIKey
from app.core.agent_auth import get_agent_api_key_with_rate_limit
from app.services.rate_limiter import get_remaining_requests
from app.schemas.agent_opportunities import (
    OpportunitiesSearchResponse,
    OpportunityDetailResponse,
    OpportunitiesBatchAnalyzeResponse,
    OpportunitySummary,
    OpportunityDetail,
    BatchAnalysisResponse,
    BatchAnalysisItem,
    ApiMetadata,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_api_metadata(execution_time_ms: int, total_count: int = 0) -> ApiMetadata:
    """Build standard API metadata response"""
    return ApiMetadata(
        total_count=total_count,
        execution_time_ms=execution_time_ms,
        api_version="v1",
        timestamp=datetime.now(timezone.utc),
    )


def _get_demand_signals(opportunity: Opportunity) -> List[str]:
    """Extract demand signals from opportunity data"""
    signals = []
    
    if opportunity.validation_count and opportunity.validation_count > 5:
        signals.append("high_validation_count")
    
    if opportunity.growth_rate and opportunity.growth_rate > 10:
        signals.append("high_growth_rate")
    
    if opportunity.ai_urgency_level and opportunity.ai_urgency_level == "critical":
        signals.append("urgent_demand")
    
    if opportunity.ai_competition_level and opportunity.ai_competition_level == "low":
        signals.append("low_competition")
    
    if opportunity.market_size and ("M" in opportunity.market_size or "B" in opportunity.market_size):
        signals.append("substantial_market")
    
    return signals


def _calculate_confidence_score(opportunity: Opportunity) -> float:
    """Calculate confidence score (0-100) based on available data"""
    score = 50.0  # Base score
    
    # AI score contribution
    if opportunity.ai_opportunity_score:
        score += (opportunity.ai_opportunity_score / 100) * 20
    
    # Validation contribution
    if opportunity.validation_count:
        score += min(opportunity.validation_count * 2, 15)
    
    # Growth rate contribution
    if opportunity.growth_rate:
        if opportunity.growth_rate > 20:
            score += 10
        elif opportunity.growth_rate > 10:
            score += 5
    
    # Cap at 100
    return min(score, 100.0)


def _calculate_risk_score(opportunity: Opportunity) -> float:
    """Calculate risk score (0-100) based on competition and other factors"""
    score = 50.0  # Base score
    
    # Competition impact
    if opportunity.ai_competition_level == "high":
        score += 20
    elif opportunity.ai_competition_level == "medium":
        score += 10
    
    # Urgency impact (inverse risk)
    if opportunity.ai_urgency_level == "low":
        score += 15
    
    # Pain intensity impact
    if opportunity.ai_pain_intensity:
        score -= (opportunity.ai_pain_intensity * 2)  # Higher pain = lower risk
    
    return max(0.0, min(score, 100.0))


def _get_trend_direction(opportunity: Opportunity) -> str:
    """Determine trend direction (up, down, neutral)"""
    if opportunity.growth_rate is None or opportunity.growth_rate == 0:
        return "neutral"
    
    if opportunity.growth_rate > 5:
        return "up"
    elif opportunity.growth_rate < -5:
        return "down"
    else:
        return "neutral"


@router.get(
    "/api/v1/agents/opportunities/search",
    response_model=OpportunitiesSearchResponse,
    summary="Search opportunities with filters",
    tags=["Agent API"],
)
def search_opportunities(
    vertical: Optional[str] = Query(None, description="Category/vertical filter"),
    city: Optional[str] = Query(None, description="City filter"),
    min_market_size: Optional[int] = Query(None, ge=0, description="Minimum market size in millions"),
    max_competition: Optional[str] = Query(None, description="Maximum competition level (low|medium|high)"),
    sort_by: Optional[str] = Query("created_at", description="Sort field: created_at|score|validation_count"),
    limit: int = Query(50, ge=1, le=500, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> OpportunitiesSearchResponse:
    """
    Search opportunities with optional filters.
    
    Query Parameters:
    - vertical: Filter by category (e.g., "SaaS", "E-Commerce")
    - city: Filter by city name
    - min_market_size: Minimum market size in millions USD
    - max_competition: Maximum competition level (low|medium|high)
    - sort_by: Sort field (created_at, score, validation_count)
    - limit: Results per page (1-500, default 50)
    - offset: Pagination offset (default 0)
    
    Returns: List of opportunities matching filters with confidence scores.
    """
    start_time = time.time()
    
    try:
        # Build query
        query = db.query(Opportunity).filter(
            Opportunity.status == "active",
            Opportunity.moderation_status == "approved"
        )
        
        # Apply filters
        if vertical:
            query = query.filter(Opportunity.category.ilike(f"%{vertical}%"))
        
        if city:
            query = query.filter(Opportunity.city.ilike(f"%{city}%"))
        
        if max_competition:
            if max_competition.lower() == "low":
                query = query.filter(
                    or_(
                        Opportunity.ai_competition_level == "low",
                        Opportunity.ai_competition_level == None
                    )
                )
            elif max_competition.lower() == "medium":
                query = query.filter(
                    Opportunity.ai_competition_level.in_(["low", "medium", None])
                )
            # "high" would include all
        
        # Sort
        if sort_by == "score":
            query = query.order_by(Opportunity.ai_opportunity_score.desc())
        elif sort_by == "validation_count":
            query = query.order_by(Opportunity.validation_count.desc())
        else:  # created_at (default)
            query = query.order_by(Opportunity.created_at.desc())
        
        # Get total count before pagination
        total_count = query.count()
        
        # Paginate
        opportunities = query.limit(limit).offset(offset).all()
        
        # Build response
        data = [
            OpportunitySummary(
                id=opp.id,
                title=opp.title,
                category=opp.category,
                city=opp.city,
                state=opp.region,
                market_size=opp.ai_market_size_estimate or opp.market_size,
                competition_level=opp.ai_competition_level or "unknown",
                demand_signals=_get_demand_signals(opp),
                confidence_score=_calculate_confidence_score(opp),
                created_at=opp.created_at,
            )
            for opp in opportunities
        ]
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return OpportunitiesSearchResponse(
            data=data,
            metadata=_build_api_metadata(execution_time, total_count),
        )
    
    except Exception as e:
        logger.error(f"Search opportunities error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search opportunities",
        )


@router.get(
    "/api/v1/agents/opportunities/{opportunity_id}",
    response_model=OpportunityDetailResponse,
    summary="Get opportunity detail",
    tags=["Agent API"],
)
def get_opportunity_detail(
    opportunity_id: int,
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> OpportunityDetailResponse:
    """
    Get full opportunity detail with metrics, signals, risk score, and trends.
    
    Path Parameters:
    - opportunity_id: The opportunity ID
    
    Returns: Detailed opportunity data with historical trends.
    """
    start_time = time.time()
    
    try:
        opportunity = db.query(Opportunity).filter(
            Opportunity.id == opportunity_id,
            Opportunity.status == "active",
            Opportunity.moderation_status == "approved"
        ).first()
        
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity {opportunity_id} not found",
            )
        
        # Build historical data (simulate 30/60/90 day trends)
        historical_data = {
            "trend_30_days": _get_trend_direction(opportunity),
            "growth_rate_percent": opportunity.growth_rate or 0,
            "validation_count_total": opportunity.validation_count or 0,
            "ai_score_latest": opportunity.ai_opportunity_score or 0,
        }
        
        data = OpportunityDetail(
            id=opportunity.id,
            title=opportunity.title,
            description=opportunity.description,
            category=opportunity.category,
            subcategory=opportunity.subcategory,
            city=opportunity.city,
            state=opportunity.region,
            country=opportunity.country,
            ai_opportunity_score=opportunity.ai_opportunity_score,
            ai_competition_level=opportunity.ai_competition_level,
            ai_urgency_level=opportunity.ai_urgency_level,
            ai_market_size_estimate=opportunity.ai_market_size_estimate,
            ai_pain_intensity=opportunity.ai_pain_intensity,
            market_size=opportunity.market_size,
            growth_rate=opportunity.growth_rate,
            validation_count=opportunity.validation_count or 0,
            risk_score=_calculate_risk_score(opportunity),
            trend_direction=_get_trend_direction(opportunity),
            historical_data=historical_data,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return OpportunityDetailResponse(
            data=data,
            metadata=_build_api_metadata(execution_time, 1),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get opportunity detail error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch opportunity detail",
        )


class BatchAnalyzeRequest(BaseModel):
    """Request body for batch analyze endpoint"""
    opportunity_ids: List[int] = Field(..., description="List of opportunity IDs to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "opportunity_ids": [1, 2, 3, 4, 5]
            }
        }


@router.post(
    "/api/v1/agents/opportunities/batch-analyze",
    response_model=OpportunitiesBatchAnalyzeResponse,
    summary="Batch analyze opportunities",
    tags=["Agent API"],
)
def batch_analyze_opportunities(
    request: BatchAnalyzeRequest,
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> OpportunitiesBatchAnalyzeResponse:
    """
    Batch analyze multiple opportunities with scores, trends, and comparisons.
    
    Request Body:
    - opportunity_ids: List of opportunity IDs (max 100)
    
    Returns: Batch analysis with individual scores, trends, and comparative data.
    """
    start_time = time.time()
    
    try:
        # Validate input
        if not request.opportunity_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="opportunity_ids must not be empty",
            )
        
        if len(request.opportunity_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 opportunities per batch request",
            )
        
        # Fetch opportunities
        opportunities = db.query(Opportunity).filter(
            Opportunity.id.in_(request.opportunity_ids),
            Opportunity.status == "active",
            Opportunity.moderation_status == "approved"
        ).all()
        
        if not opportunities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No opportunities found for provided IDs",
            )
        
        # Build batch items
        items = []
        scores = []
        risk_levels = []
        
        for opp in opportunities:
            confidence = _calculate_confidence_score(opp)
            risk = _calculate_risk_score(opp)
            scores.append(confidence)
            
            # Categorize risk level
            if risk > 75:
                risk_level = "critical"
            elif risk > 50:
                risk_level = "high"
            elif risk > 25:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            risk_levels.append(risk_level)
            
            item = BatchAnalysisItem(
                id=opp.id,
                title=opp.title,
                score=confidence,
                trend=_get_trend_direction(opp),
                confidence=confidence,
                risk_level=risk_level,
            )
            items.append(item)
        
        # Calculate comparisons
        average_score = sum(scores) / len(scores) if scores else 0
        top_item = max(items, key=lambda x: x.score) if items else None
        
        comparison = {
            "average_score": round(average_score, 2),
            "highest_score": round(max(scores), 2) if scores else 0,
            "lowest_score": round(min(scores), 2) if scores else 0,
            "total_analyzed": len(items),
            "high_risk_count": len([r for r in risk_levels if r in ("high", "critical")]),
            "low_risk_count": len([r for r in risk_levels if r == "low"]),
        }
        
        data = BatchAnalysisResponse(
            items=items,
            comparison=comparison,
            top_opportunity_id=top_item.id if top_item else None,
            average_score=round(average_score, 2),
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return OpportunitiesBatchAnalyzeResponse(
            data=data,
            metadata=_build_api_metadata(execution_time, len(items)),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analyze opportunities error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch analyze opportunities",
        )
