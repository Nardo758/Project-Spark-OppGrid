"""
Agent API Endpoints — AI Agent access to opportunities data with Phase 3 Intelligence Layer.

Endpoints with AI Intelligence:
  GET  /api/v1/agents/opportunities/search - Search opportunities with intelligent ranking
  GET  /api/v1/agents/opportunities/{id} - Get opportunity detail with predictive analysis
  POST /api/v1/agents/opportunities/batch-analyze - Batch analyze opportunities with risk/momentum
  GET  /api/v1/agents/trends/{vertical} - Analyze trend momentum and acceleration
  GET  /api/v1/agents/markets/{vertical}/{city}/insights - Market health and saturation analysis

All endpoints include:
- Confidence intervals (how sure are we?)
- Data freshness (how old is the data?)
- Predictive insights (what's likely to succeed RIGHT NOW?)
- Risk profiles (what could go wrong?)
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
from app.services.intelligence_engine import IntelligenceEngine

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
    summary="Search opportunities with intelligent ranking",
    tags=["Agent API"],
)
def search_opportunities(
    vertical: Optional[str] = Query(None, description="Category/vertical filter"),
    city: Optional[str] = Query(None, description="City filter"),
    min_market_size: Optional[int] = Query(None, ge=0, description="Minimum market size in millions"),
    max_competition: Optional[str] = Query(None, description="Maximum competition level (low|medium|high)"),
    sort_by: Optional[str] = Query("success_probability", description="Sort field: created_at|score|success_probability"),
    limit: int = Query(50, ge=1, le=500, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> OpportunitiesSearchResponse:
    """
    Search opportunities with intelligent ranking by predicted success probability.
    
    Results are ranked by "How likely is this to succeed RIGHT NOW?" using Phase 3 AI Intelligence.
    
    Query Parameters:
    - vertical: Filter by category (e.g., "SaaS", "E-Commerce")
    - city: Filter by city name
    - min_market_size: Minimum market size in millions USD
    - max_competition: Maximum competition level (low|medium|high)
    - sort_by: Sort field (created_at, score, success_probability) - default is success_probability
    - limit: Results per page (1-500, default 50)
    - offset: Pagination offset (default 0)
    
    Returns: Opportunities ranked by predicted success with:
    - success_probability: Likelihood to succeed RIGHT NOW (0-100)
    - confidence_interval: How confident are we? (0-100)
    - data_freshness_hours: Age of underlying data (hours)
    - trend_momentum: Is this trend accelerating, decelerating, or stable?
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
        
        # Get total count before pagination
        total_count = query.count()
        
        # Get all matching opportunities (we'll sort them intelligently)
        opportunities = query.all()
        
        # Use intelligence engine for ranking
        intelligence = IntelligenceEngine(db)
        ranked = intelligence.rank_opportunities(opportunities)
        
        # Sort by specified field
        if sort_by == "created_at":
            ranked.sort(key=lambda x: x[0].created_at, reverse=True)
        elif sort_by == "score":
            ranked.sort(key=lambda x: x[0].ai_opportunity_score or 0, reverse=True)
        else:  # success_probability (default)
            ranked.sort(key=lambda x: x[1].score, reverse=True)
        
        # Paginate after sorting
        paginated = ranked[offset:offset + limit]
        
        # Build response with intelligence insights
        data = []
        for opp, intelligence_score in paginated:
            momentum = intelligence.trend_analyzer.analyze_momentum(opp)
            
            data.append(OpportunitySummary(
                id=opp.id,
                title=opp.title,
                category=opp.category,
                city=opp.city,
                state=opp.region,
                market_size=opp.ai_market_size_estimate or opp.market_size,
                competition_level=opp.ai_competition_level or "unknown",
                demand_signals=_get_demand_signals(opp),
                confidence_score=_calculate_confidence_score(opp),
                success_probability=intelligence_score.score,
                confidence_interval=intelligence_score.confidence,
                data_freshness_hours=intelligence_score.data_freshness_hours,
                trend_momentum=momentum.direction,
                created_at=opp.created_at,
            ))
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return OpportunitiesSearchResponse(
            data=data,
            metadata=_build_api_metadata(execution_time, total_count),
        )
    
    except Exception as e:
        logger.error(f"Search opportunities error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search opportunities",
        )


@router.get(
    "/api/v1/agents/opportunities/{opportunity_id}",
    response_model=OpportunityDetailResponse,
    summary="Get opportunity detail with predictive intelligence",
    tags=["Agent API"],
)
def get_opportunity_detail(
    opportunity_id: int,
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> OpportunityDetailResponse:
    """
    Get full opportunity detail with intelligence insights.
    
    Includes:
    - Historical trajectory and growth patterns
    - Predictive success probability
    - Momentum metrics (is trend accelerating?)
    - Market health (saturation, demand signals)
    - Risk profile (execution, seasonal, trend fatigue)
    - Confidence intervals and data freshness
    
    Path Parameters:
    - opportunity_id: The opportunity ID
    
    Returns: Detailed opportunity data with predictive intelligence.
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
        
        # Use intelligence engine for comprehensive analysis
        intelligence = IntelligenceEngine(db)
        intelligence_data = intelligence.analyze_opportunity(opportunity)
        
        success_score = intelligence_data.get("success_score", {})
        momentum = intelligence_data.get("momentum", {})
        market_health = intelligence_data.get("market_health", {})
        risk_profile = intelligence_data.get("risk_profile", {})
        
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
            success_probability=success_score.get("score", 50.0),
            confidence_interval=success_score.get("confidence", 70.0),
            data_freshness_hours=success_score.get("data_freshness_hours", 24),
            momentum_metrics=momentum,
            market_health=market_health,
            risk_profile=risk_profile,
            reasoning=success_score.get("reasoning", ""),
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
        logger.error(f"Get opportunity detail error: {e}", exc_info=True)
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


@router.get(
    "/api/v1/agents/trends/{vertical}",
    summary="Analyze trend momentum and acceleration",
    tags=["Agent API"],
)
def analyze_trends(
    vertical: str,
    city: Optional[str] = Query(None, description="Optional city filter"),
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Analyze trend momentum for a vertical.
    
    Returns:
    - Momentum metrics (7-day, 30-day, 90-day growth rates)
    - Acceleration factor (how fast is this trend moving?)
    - Direction (accelerating, decelerating, stable)
    - Average growth rate across all opportunities in trend
    
    Path Parameters:
    - vertical: The vertical/category to analyze (e.g., "coffee", "dropshipping")
    
    Query Parameters:
    - city: Optional city filter to narrow analysis
    
    Returns: Trend analysis with momentum metrics and confidence intervals.
    """
    start_time = time.time()
    
    try:
        # Query opportunities in this vertical
        query = db.query(Opportunity).filter(
            Opportunity.category.ilike(f"%{vertical}%"),
            Opportunity.status == "active",
            Opportunity.moderation_status == "approved"
        )
        
        if city:
            query = query.filter(Opportunity.city.ilike(f"%{city}%"))
        
        opportunities = query.all()
        
        if not opportunities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No opportunities found for vertical '{vertical}'",
            )
        
        # Use intelligence engine
        intelligence = IntelligenceEngine(db)
        trend_analysis = intelligence.analyze_trends(opportunities)
        
        # Add metadata
        trend_analysis["vertical"] = vertical
        trend_analysis["city_filter"] = city
        trend_analysis["opportunity_count"] = len(opportunities)
        trend_analysis["execution_time_ms"] = int((time.time() - start_time) * 1000)
        trend_analysis["api_version"] = "v1"
        trend_analysis["timestamp"] = datetime.now(timezone.utc)
        
        return trend_analysis
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze trends error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze trends",
        )


@router.get(
    "/api/v1/agents/markets/{vertical}/{city}/insights",
    summary="Get market health and saturation insights",
    tags=["Agent API"],
)
def get_market_insights(
    vertical: str,
    city: str,
    api_key: APIKey = Depends(get_agent_api_key_with_rate_limit),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Analyze market health and saturation for a vertical in a city.
    
    Returns:
    - Market health score (0-100, 100 = hot market)
    - Saturation level (emerging, growing, mature, saturated)
    - Demand vs supply (bullish, neutral, bearish)
    - Business count in market
    - Confidence interval
    
    Signals:
    - "Market is entering saturation zone (80+ businesses)" - WARNING
    - "Demand is growing faster than supply (bullish)" - OPPORTUNITY
    - "Competition rising but demand plateauing (bearish)" - CAUTION
    
    Path Parameters:
    - vertical: The vertical/category (e.g., "coffee", "dropshipping")
    - city: The city to analyze (e.g., "Austin")
    
    Returns: Market health snapshot with saturation and demand signals.
    """
    start_time = time.time()
    
    try:
        # Query opportunities in this market
        query = db.query(Opportunity).filter(
            Opportunity.category.ilike(f"%{vertical}%"),
            Opportunity.city.ilike(f"%{city}%"),
            Opportunity.status == "active",
            Opportunity.moderation_status == "approved"
        )
        
        opportunities = query.all()
        
        if not opportunities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No opportunities found for {vertical} in {city}",
            )
        
        # Use intelligence engine
        intelligence = IntelligenceEngine(db)
        market_analysis = intelligence.analyze_market(opportunities)
        
        # Generate market warnings/signals
        warnings = []
        opportunities_obj = market_analysis.get("market_health_data", [])
        
        if opportunities_obj:
            first = opportunities_obj[0]
            business_count = first.get("business_count", 0)
            demand_supply = first.get("demand_vs_supply", "neutral")
            saturation = first.get("saturation_level", "growing")
            
            if business_count >= 150:
                warnings.append(f"Market is SATURATED ({business_count}+ businesses competing)")
            elif business_count >= 80:
                warnings.append(f"Market is entering saturation zone ({business_count} businesses)")
            
            if demand_supply == "bullish":
                warnings.append("Demand is growing faster than supply (strong opportunity)")
            elif demand_supply == "bearish":
                warnings.append("Competition rising but demand plateauing (caution)")
        
        # Add metadata
        market_analysis["vertical"] = vertical
        market_analysis["city"] = city
        market_analysis["market_warnings"] = warnings
        market_analysis["opportunity_count"] = len(opportunities)
        market_analysis["execution_time_ms"] = int((time.time() - start_time) * 1000)
        market_analysis["api_version"] = "v1"
        market_analysis["timestamp"] = datetime.now(timezone.utc)
        
        return market_analysis
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get market insights error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market insights",
        )
