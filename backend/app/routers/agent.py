"""
OppGrid Agent API

Endpoints for Clawdbot integration:
- Scraper orchestration
- Coverage monitoring
- Data gap detection
- Status reporting
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import logging
import json

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.models.google_scraping import GoogleScrapeJob, GoogleMapsBusiness
from app.models.census_demographics import MarketGrowthTrajectory, CensusPopulationEstimate
from app.models.detected_trend import DetectedTrend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

# Agent authentication
AGENT_API_KEY = os.environ.get("OPPGRID_AGENT_KEY", "oppgrid-agent-secret-key")


def verify_agent_key(x_agent_key: str = Header(None, alias="X-Agent-Key")):
    """Verify the agent API key."""
    if not x_agent_key or x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent key")
    return True


# --- Pydantic Models ---

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    database: str
    services: Dict[str, str]


class CoverageStats(BaseModel):
    total_cities: int
    total_states: int
    total_opportunities: int
    total_businesses: int
    last_scrape: Optional[str]
    coverage_by_state: Dict[str, int]


class DataGap(BaseModel):
    city: str
    state: str
    gap_type: str  # 'no_opportunities', 'stale_data', 'no_competitors', 'no_census'
    priority: str  # 'high', 'medium', 'low'
    last_updated: Optional[str]
    recommendation: str


class ScraperCommand(BaseModel):
    action: str  # 'run', 'pause', 'resume', 'status'
    scraper_type: Optional[str] = None  # 'google_maps', 'census', 'trends', 'all'
    target_cities: Optional[List[str]] = None
    target_states: Optional[List[str]] = None
    business_types: Optional[List[str]] = None
    priority: Optional[str] = "normal"


class ScraperStatus(BaseModel):
    scraper_type: str
    status: str  # 'running', 'idle', 'paused', 'error'
    jobs_pending: int
    jobs_completed_today: int
    last_run: Optional[str]
    next_run: Optional[str]


class AgentCommandResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# --- Health & Status ---

@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Agent health check endpoint."""
    try:
        # Check database
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="operational",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        database=db_status,
        services={
            "scrapers": "available",
            "ai": "available",
            "stripe": "available"
        }
    )


@router.get("/status", response_model=Dict[str, Any])
async def get_platform_status(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get comprehensive platform status for agent monitoring."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    
    # Opportunity stats
    total_opps = db.query(func.count(Opportunity.id)).scalar() or 0
    active_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == 'active'
    ).scalar() or 0
    new_opps_today = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= today
    ).scalar() or 0
    new_opps_week = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= week_ago
    ).scalar() or 0
    
    # Business/competitor stats
    total_businesses = db.query(func.count(GoogleMapsBusiness.id)).scalar() or 0
    active_businesses = db.query(func.count(GoogleMapsBusiness.id)).filter(
        GoogleMapsBusiness.is_active == True
    ).scalar() or 0
    
    # Scraping job stats
    pending_jobs = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'pending'
    ).scalar() or 0
    running_jobs = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'running'
    ).scalar() or 0
    completed_today = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'completed',
        GoogleScrapeJob.completed_at >= today
    ).scalar() or 0
    
    # Coverage
    states_covered = db.query(func.count(distinct(Opportunity.region))).filter(
        Opportunity.region.isnot(None)
    ).scalar() or 0
    cities_covered = db.query(func.count(distinct(Opportunity.city))).filter(
        Opportunity.city.isnot(None)
    ).scalar() or 0
    
    return {
        "timestamp": now.isoformat(),
        "opportunities": {
            "total": total_opps,
            "active": active_opps,
            "new_today": new_opps_today,
            "new_this_week": new_opps_week
        },
        "businesses": {
            "total": total_businesses,
            "active": active_businesses
        },
        "scraping": {
            "jobs_pending": pending_jobs,
            "jobs_running": running_jobs,
            "completed_today": completed_today
        },
        "coverage": {
            "states": states_covered,
            "cities": cities_covered
        }
    }


# --- Coverage Monitoring ---

@router.get("/coverage", response_model=CoverageStats)
async def get_coverage_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get data coverage statistics."""
    # Count unique cities and states
    cities = db.query(func.count(distinct(Opportunity.city))).filter(
        Opportunity.city.isnot(None)
    ).scalar() or 0
    
    states = db.query(func.count(distinct(Opportunity.region))).filter(
        Opportunity.region.isnot(None)
    ).scalar() or 0
    
    total_opps = db.query(func.count(Opportunity.id)).scalar() or 0
    total_businesses = db.query(func.count(GoogleMapsBusiness.id)).scalar() or 0
    
    # Last scrape time
    last_job = db.query(GoogleScrapeJob).filter(
        GoogleScrapeJob.status == 'completed'
    ).order_by(GoogleScrapeJob.completed_at.desc()).first()
    
    last_scrape = last_job.completed_at.isoformat() if last_job and last_job.completed_at else None
    
    # Coverage by state
    state_counts = db.query(
        Opportunity.region,
        func.count(Opportunity.id)
    ).filter(
        Opportunity.region.isnot(None)
    ).group_by(Opportunity.region).all()
    
    coverage_by_state = {state: count for state, count in state_counts if state}
    
    return CoverageStats(
        total_cities=cities,
        total_states=states,
        total_opportunities=total_opps,
        total_businesses=total_businesses,
        last_scrape=last_scrape,
        coverage_by_state=coverage_by_state
    )


@router.get("/coverage/gaps", response_model=List[DataGap])
async def detect_data_gaps(
    min_population: int = 50000,
    max_gaps: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """
    Detect data gaps - cities/states that need more scraping.
    
    Returns prioritized list of locations needing attention.
    """
    gaps = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=30)
    
    # Get all cities from census data with population > min_population
    census_cities = db.query(
        CensusPopulationEstimate.geography_name,
        CensusPopulationEstimate.state_code,
        CensusPopulationEstimate.population
    ).filter(
        CensusPopulationEstimate.population >= min_population
    ).order_by(CensusPopulationEstimate.population.desc()).limit(200).all()
    
    # Get cities we have opportunity data for
    covered_cities = set(
        (city.lower(), state.lower()) 
        for city, state in db.query(distinct(Opportunity.city), Opportunity.region).filter(
            Opportunity.city.isnot(None),
            Opportunity.region.isnot(None)
        ).all()
    )
    
    # Find cities without opportunity data
    for city_name, state_code, population in census_cities:
        if len(gaps) >= max_gaps:
            break
        
        # Parse city name (e.g., "Atlanta city, Georgia" -> "Atlanta")
        city_clean = city_name.split(" city")[0].split(" town")[0].strip()
        
        key = (city_clean.lower(), state_code.lower() if state_code else "")
        
        if key not in covered_cities:
            priority = "high" if population >= 200000 else "medium" if population >= 100000 else "low"
            gaps.append(DataGap(
                city=city_clean,
                state=state_code or "",
                gap_type="no_opportunities",
                priority=priority,
                last_updated=None,
                recommendation=f"Run Google Maps scraper for {city_clean}, {state_code} (pop: {population:,})"
            ))
    
    # Check for stale data in existing cities
    stale_opps = db.query(
        Opportunity.city,
        Opportunity.region,
        func.max(Opportunity.updated_at).label('last_update')
    ).filter(
        Opportunity.city.isnot(None)
    ).group_by(
        Opportunity.city,
        Opportunity.region
    ).having(
        func.max(Opportunity.updated_at) < stale_threshold
    ).limit(max_gaps - len(gaps)).all()
    
    for city, state, last_update in stale_opps:
        if len(gaps) >= max_gaps:
            break
        
        gaps.append(DataGap(
            city=city,
            state=state or "",
            gap_type="stale_data",
            priority="medium",
            last_updated=last_update.isoformat() if last_update else None,
            recommendation=f"Refresh data for {city}, {state} (last update: {last_update.strftime('%Y-%m-%d') if last_update else 'unknown'})"
        ))
    
    return gaps


@router.get("/coverage/state/{state_code}")
async def get_state_coverage(
    state_code: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get detailed coverage for a specific state."""
    state_upper = state_code.upper()
    
    # Cities with opportunities
    cities = db.query(
        Opportunity.city,
        func.count(Opportunity.id).label('opp_count'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score'),
        func.max(Opportunity.updated_at).label('last_update')
    ).filter(
        Opportunity.region == state_upper,
        Opportunity.city.isnot(None)
    ).group_by(Opportunity.city).all()
    
    # Businesses by city
    businesses = db.query(
        GoogleMapsBusiness.city,
        func.count(GoogleMapsBusiness.id).label('business_count')
    ).filter(
        GoogleMapsBusiness.state == state_upper,
        GoogleMapsBusiness.is_active == True
    ).group_by(GoogleMapsBusiness.city).all()
    
    business_by_city = {city: count for city, count in businesses if city}
    
    # Growth trajectories
    trajectories = db.query(MarketGrowthTrajectory).filter(
        MarketGrowthTrajectory.state == state_upper
    ).all()
    
    city_details = []
    for city, opp_count, avg_score, last_update in cities:
        city_details.append({
            "city": city,
            "opportunities": opp_count,
            "avg_score": round(avg_score or 0, 1),
            "businesses": business_by_city.get(city, 0),
            "last_update": last_update.isoformat() if last_update else None,
            "has_growth_data": any(t.city.lower() == city.lower() for t in trajectories)
        })
    
    return {
        "state": state_upper,
        "total_cities": len(cities),
        "total_opportunities": sum(c["opportunities"] for c in city_details),
        "total_businesses": sum(c["businesses"] for c in city_details),
        "cities": sorted(city_details, key=lambda x: x["opportunities"], reverse=True)
    }


# --- Scraper Control ---

@router.post("/scrapers/command", response_model=AgentCommandResponse)
async def execute_scraper_command(
    command: ScraperCommand,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """
    Execute scraper commands.
    
    Actions:
    - run: Start scraping jobs for specified targets
    - pause: Pause running jobs
    - resume: Resume paused jobs
    - status: Get scraper status
    """
    from app.services.google_scraping_service import GoogleScrapingService
    
    try:
        if command.action == "status":
            # Return scraper status
            pending = db.query(func.count(GoogleScrapeJob.id)).filter(
                GoogleScrapeJob.status == 'pending'
            ).scalar() or 0
            running = db.query(func.count(GoogleScrapeJob.id)).filter(
                GoogleScrapeJob.status == 'running'
            ).scalar() or 0
            
            return AgentCommandResponse(
                success=True,
                message="Scraper status retrieved",
                data={
                    "pending_jobs": pending,
                    "running_jobs": running,
                    "scraper_type": command.scraper_type or "all"
                }
            )
        
        elif command.action == "run":
            # Create scraping jobs
            if not command.target_cities and not command.target_states:
                return AgentCommandResponse(
                    success=False,
                    message="Must specify target_cities or target_states"
                )
            
            scraping_service = GoogleScrapingService(db)
            jobs_created = 0
            
            cities = command.target_cities or []
            states = command.target_states or []
            business_types = command.business_types or ["restaurant", "retail", "service"]
            
            # If states specified without cities, get major cities
            if states and not cities:
                for state in states:
                    # Get top cities by population from census
                    top_cities = db.query(CensusPopulationEstimate.geography_name).filter(
                        CensusPopulationEstimate.state_code == state.upper(),
                        CensusPopulationEstimate.population >= 50000
                    ).order_by(CensusPopulationEstimate.population.desc()).limit(10).all()
                    
                    for (city_name,) in top_cities:
                        city_clean = city_name.split(" city")[0].split(" town")[0].strip()
                        cities.append(f"{city_clean}, {state.upper()}")
            
            # Create jobs for each city/business_type combination
            for city_state in cities:
                if ", " in city_state:
                    city, state = city_state.rsplit(", ", 1)
                else:
                    city = city_state
                    state = ""
                
                for biz_type in business_types:
                    job = GoogleScrapeJob(
                        job_type="google_maps_search",
                        search_query=f"{biz_type} in {city}, {state}",
                        location=f"{city}, {state}",
                        status="pending",
                        priority=1 if command.priority == "high" else 2 if command.priority == "normal" else 3
                    )
                    db.add(job)
                    jobs_created += 1
            
            db.commit()
            
            return AgentCommandResponse(
                success=True,
                message=f"Created {jobs_created} scraping jobs",
                data={
                    "jobs_created": jobs_created,
                    "cities": len(cities),
                    "business_types": business_types
                }
            )
        
        elif command.action == "pause":
            # Pause running jobs
            updated = db.query(GoogleScrapeJob).filter(
                GoogleScrapeJob.status == 'running'
            ).update({"status": "paused"})
            db.commit()
            
            return AgentCommandResponse(
                success=True,
                message=f"Paused {updated} jobs"
            )
        
        elif command.action == "resume":
            # Resume paused jobs
            updated = db.query(GoogleScrapeJob).filter(
                GoogleScrapeJob.status == 'paused'
            ).update({"status": "pending"})
            db.commit()
            
            return AgentCommandResponse(
                success=True,
                message=f"Resumed {updated} jobs"
            )
        
        else:
            return AgentCommandResponse(
                success=False,
                message=f"Unknown action: {command.action}"
            )
    
    except Exception as e:
        logger.error(f"Scraper command failed: {e}")
        return AgentCommandResponse(
            success=False,
            message=str(e)
        )


@router.get("/scrapers/status", response_model=List[ScraperStatus])
async def get_all_scraper_status(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get status of all scrapers."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    scrapers = []
    
    # Google Maps scraper
    gm_pending = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'pending',
        GoogleScrapeJob.job_type == 'google_maps_search'
    ).scalar() or 0
    
    gm_running = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'running',
        GoogleScrapeJob.job_type == 'google_maps_search'
    ).scalar() or 0
    
    gm_completed_today = db.query(func.count(GoogleScrapeJob.id)).filter(
        GoogleScrapeJob.status == 'completed',
        GoogleScrapeJob.job_type == 'google_maps_search',
        GoogleScrapeJob.completed_at >= today
    ).scalar() or 0
    
    gm_last = db.query(GoogleScrapeJob).filter(
        GoogleScrapeJob.status == 'completed',
        GoogleScrapeJob.job_type == 'google_maps_search'
    ).order_by(GoogleScrapeJob.completed_at.desc()).first()
    
    scrapers.append(ScraperStatus(
        scraper_type="google_maps",
        status="running" if gm_running > 0 else "idle" if gm_pending > 0 else "idle",
        jobs_pending=gm_pending,
        jobs_completed_today=gm_completed_today,
        last_run=gm_last.completed_at.isoformat() if gm_last and gm_last.completed_at else None,
        next_run=None  # Would need scheduler integration
    ))
    
    # Could add more scraper types here (census, trends, etc.)
    
    return scrapers


# --- Data Queries ---

@router.get("/opportunities/recent")
async def get_recent_opportunities(
    limit: int = 20,
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get recent opportunities with optional filters."""
    query = db.query(Opportunity).filter(Opportunity.status == 'active')
    
    if city:
        query = query.filter(func.lower(Opportunity.city) == city.lower())
    if state:
        query = query.filter(func.upper(Opportunity.region) == state.upper())
    if category:
        query = query.filter(func.lower(Opportunity.category) == category.lower())
    
    opps = query.order_by(Opportunity.created_at.desc()).limit(limit).all()
    
    return [{
        "id": o.id,
        "title": o.title,
        "category": o.category,
        "city": o.city,
        "state": o.region,
        "score": o.ai_opportunity_score,
        "created_at": o.created_at.isoformat() if o.created_at else None
    } for o in opps]


@router.get("/trends/hot")
async def get_hot_trends(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get currently hot/trending market signals."""
    trends = db.query(DetectedTrend).filter(
        DetectedTrend.trend_strength >= 70
    ).order_by(DetectedTrend.trend_strength.desc()).limit(limit).all()
    
    return [{
        "id": t.id,
        "name": t.trend_name,
        "category": t.category,
        "strength": t.trend_strength,
        "confidence": t.confidence_score,
        "opportunities_count": t.opportunities_count,
        "description": t.description[:200] if t.description else None
    } for t in trends]


# --- AI Usage (for metering) ---

@router.get("/usage/summary")
async def get_ai_usage_summary(
    period: str = "current_month",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get platform-wide AI usage summary."""
    from app.models.ai_usage import UserAIUsage
    
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "current_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = datetime(2020, 1, 1)
    
    try:
        usage = db.query(
            func.count(UserAIUsage.id).label('total_requests'),
            func.sum(UserAIUsage.total_tokens).label('total_tokens'),
            func.sum(UserAIUsage.cost_usd).label('total_cost'),
            func.sum(UserAIUsage.billed_amount_usd).label('total_billed')
        ).filter(
            UserAIUsage.created_at >= start_date
        ).first()
        
        return {
            "period": period,
            "period_start": start_date.isoformat(),
            "total_requests": usage.total_requests or 0,
            "total_tokens": usage.total_tokens or 0,
            "total_cost_usd": round(usage.total_cost or 0, 4),
            "total_billed_usd": round(usage.total_billed or 0, 4)
        }
    except Exception as e:
        logger.warning(f"AI usage query failed (table may not exist): {e}")
        return {
            "period": period,
            "error": "usage_table_not_initialized"
        }


# --- Moderation & User Management ---

@router.get("/users/flagged")
async def get_flagged_users(
    reason: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get users flagged for review (banned, suspicious, etc)."""
    from app.models.user import User
    
    query = db.query(User)
    
    # Banned users
    if reason is None or reason == "banned":
        banned = query.filter(User.is_banned == True).all()
        return {
            "users": [{
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "status": "banned",
                "reason": u.ban_reason or "No reason provided",
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None
            } for u in banned[:limit]],
            "total_flagged": len(banned),
            "reason_filter": "banned"
        }
    
    # Inactive users (no activity in 90 days)
    if reason == "inactive":
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        inactive = query.filter(
            User.is_active == True,
            User.updated_at < ninety_days_ago
        ).all()
        return {
            "users": [{
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "status": "inactive",
                "reason": f"No activity since {u.updated_at.strftime('%Y-%m-%d')}",
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None
            } for u in inactive[:limit]],
            "total_flagged": len(inactive),
            "reason_filter": "inactive"
        }
    
    # Recently created (possible spam)
    if reason == "new_suspicious":
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        new_users = query.filter(User.created_at >= one_day_ago).all()
        return {
            "users": [{
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "status": "new_account",
                "reason": "Created in last 24 hours - monitor for spam",
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None
            } for u in new_users[:limit]],
            "total_flagged": len(new_users),
            "reason_filter": "new_suspicious"
        }
    
    return {"users": [], "total_flagged": 0, "reason_filter": reason}


@router.post("/users/{user_id}/ban")
async def ban_user_by_agent(
    user_id: int,
    reason: str = "Flagged by automated agent",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Ban a user account (automated moderation)."""
    from app.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}
    
    if user.is_admin:
        return {"success": False, "message": "Cannot ban admin users"}
    
    user.is_banned = True
    user.ban_reason = reason
    user.is_active = False
    db.commit()
    
    logger.info(f"Agent banned user {user_id}: {reason}")
    
    return {
        "success": True,
        "message": f"User {user.email} banned",
        "user_id": user_id,
        "email": user.email,
        "ban_reason": reason
    }


class ModerationUpdatePayload(BaseModel):
    moderation_status: str  # 'approved', 'rejected', 'needs_edit'
    edit_title: Optional[str] = None
    edit_description: Optional[str] = None
    edit_category: Optional[str] = None
    mod_notes: Optional[str] = None


@router.post("/opportunities/{opportunity_id}/moderate")
async def moderate_opportunity_by_agent(
    opportunity_id: int,
    payload: ModerationUpdatePayload,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Moderate (approve/reject/edit) an opportunity."""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        return {"success": False, "message": "Opportunity not found"}
    
    valid_statuses = ['approved', 'rejected', 'needs_edit']
    if payload.moderation_status not in valid_statuses:
        return {"success": False, "message": f"Invalid status. Must be: {', '.join(valid_statuses)}"}
    
    # Update status
    opp.moderation_status = payload.moderation_status
    
    # Apply edits if provided
    if payload.edit_title:
        opp.title = payload.edit_title[:500]
    if payload.edit_description:
        opp.description = payload.edit_description[:5000]
    if payload.edit_category:
        opp.category = payload.edit_category[:100]
    
    opp.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Agent moderated opportunity {opportunity_id}: {payload.moderation_status}")
    
    return {
        "success": True,
        "message": f"Opportunity {opportunity_id} marked as {payload.moderation_status}",
        "opportunity_id": opportunity_id,
        "title": opp.title,
        "new_status": payload.moderation_status,
        "edited_fields": [
            f for f in ['title', 'description', 'category']
            if getattr(payload, f'edit_{f}', None)
        ]
    }


@router.get("/payments/failed")
async def get_failed_payments(
    days: int = 7,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Get failed payment attempts (charges, subscription renewals, etc)."""
    from app.models.stripe_event import StripeWebhookEvent
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Query failed charge events
    failed_charges = db.query(StripeWebhookEvent).filter(
        StripeWebhookEvent.event_type.in_(['charge.failed', 'invoice.payment_failed']),
        StripeWebhookEvent.received_at >= cutoff
    ).order_by(StripeWebhookEvent.received_at.desc()).limit(limit).all()
    
    failures = []
    for event in failed_charges:
        try:
            data = json.loads(event.event_data) if isinstance(event.event_data, str) else event.event_data or {}
            failure_dict = {
                "event_id": event.stripe_event_id,
                "event_type": event.event_type,
                "received_at": event.received_at.isoformat() if event.received_at else None,
                "livemode": event.livemode,
                "amount_cents": data.get('data', {}).get('object', {}).get('amount', 0),
                "currency": data.get('data', {}).get('object', {}).get('currency', 'usd'),
                "customer_id": data.get('data', {}).get('object', {}).get('customer', ''),
                "description": data.get('data', {}).get('object', {}).get('description', ''),
                "failure_reason": data.get('data', {}).get('object', {}).get('failure_message', 'Unknown')
            }
            failures.append(failure_dict)
        except Exception as e:
            logger.error(f"Error parsing failure event {event.id}: {e}")
    
    return {
        "failed_payments": failures,
        "total_failures": len(failures),
        "days_lookback": days,
        "recommendation": "Review these failures and contact customers if needed"
    }


@router.post("/payments/{stripe_event_id}/refund")
async def issue_refund_by_agent(
    stripe_event_id: str,
    reason: str = "Issued by automated agent",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    """Issue a refund for a failed payment (creates Stripe refund request)."""
    import os
    import httpx
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return {"success": False, "message": "Stripe key not configured"}
    
    # Look up the event
    from app.models.stripe_event import StripeWebhookEvent
    event = db.query(StripeWebhookEvent).filter(
        StripeWebhookEvent.stripe_event_id == stripe_event_id
    ).first()
    
    if not event:
        return {"success": False, "message": "Event not found"}
    
    try:
        event_data = json.loads(event.event_data) if isinstance(event.event_data, str) else event.event_data or {}
        charge_id = event_data.get('data', {}).get('object', {}).get('id', '')
        amount_cents = event_data.get('data', {}).get('object', {}).get('amount', 0)
        
        if not charge_id:
            return {"success": False, "message": "No charge ID found in event"}
        
        # Create refund via Stripe API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.stripe.com/v1/charges/{charge_id}/refunds",
                auth=("Bearer", stripe_key),
                data={"reason": reason}
            )
        
        if response.status_code in [200, 201]:
            refund_data = response.json()
            logger.info(f"Refund issued: {refund_data.get('id')}")
            return {
                "success": True,
                "message": f"Refund issued for charge {charge_id}",
                "refund_id": refund_data.get('id'),
                "amount_cents": amount_cents,
                "reason": reason
            }
        else:
            return {
                "success": False,
                "message": f"Stripe API error: {response.text}"
            }
    
    except Exception as e:
        logger.error(f"Refund failed for event {stripe_event_id}: {e}")
        return {
            "success": False,
            "message": str(e)
        }
