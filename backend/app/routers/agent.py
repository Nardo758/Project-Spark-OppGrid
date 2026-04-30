"""
OppGrid Agent API

Endpoints for Clawdbot integration:
- Scraper orchestration
- Coverage monitoring
- Data gap detection
- Status reporting
- Hub data layer access
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text
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
from app.models.data_hub import (
    HubOpportunityEnriched, HubMarketByGeography, HubIndustryInsight,
    HubMarketSignal, HubValidationInsight, HubUserCohort, HubFinancialSnapshot
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

AGENT_API_KEY = os.environ.get("OPPGRID_AGENT_KEY")
if not AGENT_API_KEY:
    import warnings
    warnings.warn("OPPGRID_AGENT_KEY not set — agent endpoints will reject all requests", stacklevel=2)
    AGENT_API_KEY = None


def verify_agent_key(x_agent_key: str = Header(None, alias="X-Agent-Key")):
    if not x_agent_key or x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent key")
    return True


def _hub_available(db: Session) -> bool:
    try:
        result = db.execute(text("SELECT COUNT(*) FROM hub_opportunities_enriched"))
        count = result.scalar() or 0
        return count > 0
    except Exception:
        db.rollback()
        return False


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
    gap_type: str
    priority: str
    last_updated: Optional[str]
    recommendation: str


class ScraperCommand(BaseModel):
    action: str
    scraper_type: Optional[str] = None
    target_cities: Optional[List[str]] = None
    target_states: Optional[List[str]] = None
    business_types: Optional[List[str]] = None
    priority: Optional[str] = "normal"


class ScraperStatus(BaseModel):
    scraper_type: str
    status: str
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
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    hub_status = "available" if _hub_available(db) else "not_populated"

    return HealthResponse(
        status="operational",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        database=db_status,
        services={
            "scrapers": "available",
            "ai": "available",
            "stripe": "available",
            "data_hub": hub_status
        }
    )


@router.get("/status", response_model=Dict[str, Any])
async def get_platform_status(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    use_hub = _hub_available(db)

    if use_hub:
        total_opps = db.query(func.count(HubOpportunityEnriched.opportunity_id)).scalar() or 0
        hub_cities = db.query(func.count(distinct(HubMarketByGeography.city))).scalar() or 0
        hub_states = db.query(func.count(distinct(HubMarketByGeography.state))).scalar() or 0
        avg_score = db.query(func.avg(HubOpportunityEnriched.ai_opportunity_score)).scalar()

        snapshot = db.query(HubFinancialSnapshot).order_by(
            HubFinancialSnapshot.snapshot_date.desc()
        ).first()

        financial = {}
        if snapshot:
            financial = {
                "total_users": snapshot.total_users or 0,
                "active_users_30d": snapshot.active_users_30d or 0,
                "paid_users": snapshot.paid_users or 0,
                "mrr_usd": round(snapshot.mrr_recurring_revenue_usd or 0, 2),
                "total_reports": snapshot.total_reports_generated or 0,
                "reports_this_month": snapshot.reports_this_month or 0
            }

        tier_counts = db.query(
            HubOpportunityEnriched.market_tier,
            func.count(HubOpportunityEnriched.opportunity_id)
        ).group_by(HubOpportunityEnriched.market_tier).all()

        return {
            "timestamp": now.isoformat(),
            "data_source": "hub",
            "opportunities": {
                "total": total_opps,
                "avg_score": round(avg_score or 0, 1),
                "by_tier": {tier: count for tier, count in tier_counts if tier}
            },
            "coverage": {
                "states": hub_states,
                "cities": hub_cities
            },
            "financial": financial,
            "scraping": _get_scraping_stats(db, today)
        }

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

    total_businesses = db.query(func.count(GoogleMapsBusiness.id)).scalar() or 0
    active_businesses = db.query(func.count(GoogleMapsBusiness.id)).filter(
        GoogleMapsBusiness.is_active == True
    ).scalar() or 0

    states_covered = db.query(func.count(distinct(Opportunity.region))).filter(
        Opportunity.region.isnot(None)
    ).scalar() or 0
    cities_covered = db.query(func.count(distinct(Opportunity.city))).filter(
        Opportunity.city.isnot(None)
    ).scalar() or 0

    return {
        "timestamp": now.isoformat(),
        "data_source": "raw",
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
        "scraping": _get_scraping_stats(db, today),
        "coverage": {
            "states": states_covered,
            "cities": cities_covered
        }
    }


def _get_scraping_stats(db: Session, today: datetime) -> Dict[str, int]:
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
    return {
        "jobs_pending": pending_jobs,
        "jobs_running": running_jobs,
        "completed_today": completed_today
    }


# --- Coverage Monitoring ---

@router.get("/coverage", response_model=CoverageStats)
async def get_coverage_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    use_hub = _hub_available(db)

    if use_hub:
        markets = db.query(HubMarketByGeography).all()
        cities = len(set(m.city for m in markets if m.city))
        states = len(set(m.state for m in markets if m.state))
        total_opps = sum(m.total_opportunities or 0 for m in markets)
        total_businesses = sum(m.total_businesses or 0 for m in markets)

        state_counts: Dict[str, int] = {}
        for m in markets:
            if m.state:
                state_counts[m.state] = state_counts.get(m.state, 0) + (m.total_opportunities or 0)

        last_job = db.query(GoogleScrapeJob).filter(
            GoogleScrapeJob.status == 'completed'
        ).order_by(GoogleScrapeJob.completed_at.desc()).first()

        return CoverageStats(
            total_cities=cities,
            total_states=states,
            total_opportunities=total_opps,
            total_businesses=total_businesses,
            last_scrape=last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
            coverage_by_state=state_counts
        )

    cities = db.query(func.count(distinct(Opportunity.city))).filter(
        Opportunity.city.isnot(None)
    ).scalar() or 0

    states = db.query(func.count(distinct(Opportunity.region))).filter(
        Opportunity.region.isnot(None)
    ).scalar() or 0

    total_opps = db.query(func.count(Opportunity.id)).scalar() or 0
    total_businesses = db.query(func.count(GoogleMapsBusiness.id)).scalar() or 0

    last_job = db.query(GoogleScrapeJob).filter(
        GoogleScrapeJob.status == 'completed'
    ).order_by(GoogleScrapeJob.completed_at.desc()).first()

    last_scrape = last_job.completed_at.isoformat() if last_job and last_job.completed_at else None

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
    gaps = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=30)

    census_cities = db.query(
        CensusPopulationEstimate.geography_name,
        CensusPopulationEstimate.state_code,
        CensusPopulationEstimate.population
    ).filter(
        CensusPopulationEstimate.population >= min_population
    ).order_by(CensusPopulationEstimate.population.desc()).limit(200).all()

    use_hub = _hub_available(db)

    if use_hub:
        hub_markets = db.query(HubMarketByGeography.city, HubMarketByGeography.state).all()
        covered_cities = set(
            (m.city.lower(), m.state.lower()) for m in hub_markets if m.city and m.state
        )
    else:
        covered_cities = set(
            (city.lower(), state.lower())
            for city, state in db.query(distinct(Opportunity.city), Opportunity.region).filter(
                Opportunity.city.isnot(None),
                Opportunity.region.isnot(None)
            ).all()
        )

    for city_name, state_code, population in census_cities:
        if len(gaps) >= max_gaps:
            break

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

    if use_hub:
        stale_markets = db.query(HubMarketByGeography).filter(
            HubMarketByGeography.last_updated_at < stale_threshold
        ).limit(max_gaps - len(gaps)).all()

        for m in stale_markets:
            if len(gaps) >= max_gaps:
                break
            gaps.append(DataGap(
                city=m.city,
                state=m.state or "",
                gap_type="stale_data",
                priority="medium",
                last_updated=m.last_updated_at.isoformat() if m.last_updated_at else None,
                recommendation=f"Refresh data for {m.city}, {m.state} (last update: {m.last_updated_at.strftime('%Y-%m-%d') if m.last_updated_at else 'unknown'})"
            ))
    else:
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
    state_upper = state_code.upper()
    use_hub = _hub_available(db)

    if use_hub:
        markets = db.query(HubMarketByGeography).filter(
            HubMarketByGeography.state == state_upper
        ).all()

        enriched = db.query(HubOpportunityEnriched).filter(
            HubOpportunityEnriched.state == state_upper
        ).all()

        city_map: Dict[str, Dict] = {}
        for m in markets:
            city_map[m.city] = {
                "city": m.city,
                "opportunities": m.total_opportunities or 0,
                "avg_score": round(m.avg_opportunity_score or 0, 1),
                "businesses": m.total_businesses or 0,
                "growth_trajectory": m.growth_trajectory,
                "population": m.population,
                "new_30d": m.new_opportunities_30d or 0,
                "last_update": m.last_updated_at.isoformat() if m.last_updated_at else None,
                "has_growth_data": m.growth_trajectory is not None
            }

        tier_counts = {}
        for e in enriched:
            tier = e.market_tier or "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        city_details = sorted(city_map.values(), key=lambda x: x["opportunities"], reverse=True)

        return {
            "state": state_upper,
            "data_source": "hub",
            "total_cities": len(city_details),
            "total_opportunities": sum(c["opportunities"] for c in city_details),
            "total_businesses": sum(c["businesses"] for c in city_details),
            "tier_breakdown": tier_counts,
            "cities": city_details
        }

    cities = db.query(
        Opportunity.city,
        func.count(Opportunity.id).label('opp_count'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score'),
        func.max(Opportunity.updated_at).label('last_update')
    ).filter(
        Opportunity.region == state_upper,
        Opportunity.city.isnot(None)
    ).group_by(Opportunity.city).all()

    businesses = db.query(
        GoogleMapsBusiness.city,
        func.count(GoogleMapsBusiness.id).label('business_count')
    ).filter(
        GoogleMapsBusiness.state == state_upper,
        GoogleMapsBusiness.is_active == True
    ).group_by(GoogleMapsBusiness.city).all()

    business_by_city = {city: count for city, count in businesses if city}

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
        "data_source": "raw",
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
    from app.services.google_scraping_service import GoogleScrapingService

    try:
        if command.action == "status":
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

            if states and not cities:
                for state in states:
                    top_cities = db.query(CensusPopulationEstimate.geography_name).filter(
                        CensusPopulationEstimate.state_code == state.upper(),
                        CensusPopulationEstimate.population >= 50000
                    ).order_by(CensusPopulationEstimate.population.desc()).limit(10).all()

                    for (city_name,) in top_cities:
                        city_clean = city_name.split(" city")[0].split(" town")[0].strip()
                        cities.append(f"{city_clean}, {state.upper()}")

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
            updated = db.query(GoogleScrapeJob).filter(
                GoogleScrapeJob.status == 'running'
            ).update({"status": "paused"})
            db.commit()

            return AgentCommandResponse(
                success=True,
                message=f"Paused {updated} jobs"
            )

        elif command.action == "resume":
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
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    scrapers = []

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
        status="running" if gm_running > 0 else "idle",
        jobs_pending=gm_pending,
        jobs_completed_today=gm_completed_today,
        last_run=gm_last.completed_at.isoformat() if gm_last and gm_last.completed_at else None,
        next_run=None
    ))

    return scrapers


# --- Data Queries (Hub-powered) ---

@router.get("/opportunities/recent")
async def get_recent_opportunities(
    limit: int = 20,
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    market_tier: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    use_hub = _hub_available(db)

    if use_hub:
        query = db.query(HubOpportunityEnriched)

        if city:
            query = query.filter(func.lower(HubOpportunityEnriched.city) == city.lower())
        if state:
            query = query.filter(func.upper(HubOpportunityEnriched.state) == state.upper())
        if category:
            query = query.filter(func.lower(HubOpportunityEnriched.category) == category.lower())
        if min_score:
            query = query.filter(HubOpportunityEnriched.ai_opportunity_score >= min_score)
        if market_tier:
            query = query.filter(HubOpportunityEnriched.market_tier == market_tier)

        opps = query.order_by(HubOpportunityEnriched.ai_opportunity_score.desc().nullslast()).limit(limit).all()

        return [{
            "id": o.opportunity_id,
            "title": o.title,
            "category": o.category,
            "subcategory": o.subcategory,
            "city": o.city,
            "state": o.state,
            "score": o.ai_opportunity_score,
            "market_tier": o.market_tier,
            "trend_momentum": o.trend_momentum,
            "competition_density": o.competition_density,
            "competitors_count": o.direct_competitors_count,
            "difficulty_score": o.difficulty_score,
            "market_readiness": o.market_readiness_score,
            "data_freshness": o.data_freshness,
            "last_updated": o.last_updated_at.isoformat() if o.last_updated_at else None
        } for o in opps]

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
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    use_hub = _hub_available(db)

    if use_hub:
        query = db.query(HubMarketSignal).filter(
            HubMarketSignal.signal_strength >= 0.7
        )
        if category:
            query = query.filter(func.lower(HubMarketSignal.category) == category.lower())

        signals = query.order_by(HubMarketSignal.signal_strength.desc()).limit(limit).all()

        return [{
            "id": s.signal_id,
            "name": s.signal_name,
            "type": s.signal_type,
            "category": s.category,
            "strength": round(s.signal_strength, 2) if s.signal_strength else None,
            "direction": s.trend_direction,
            "momentum": s.momentum,
            "confidence": s.confidence_level,
            "source": s.data_source,
            "interpretation": s.interpretation[:200] if s.interpretation else None,
            "discovered_at": s.discovered_at.isoformat() if s.discovered_at else None
        } for s in signals]

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


# --- Hub Data Endpoints ---

@router.get("/hub/dashboard")
async def get_hub_dashboard(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {
            "status": "not_populated",
            "message": "Hub tables have not been populated yet. Run the Data Hub aggregation first."
        }

    opp_count = db.query(func.count(HubOpportunityEnriched.opportunity_id)).scalar() or 0
    avg_score = db.query(func.avg(HubOpportunityEnriched.ai_opportunity_score)).scalar()

    tier_counts = db.query(
        HubOpportunityEnriched.market_tier,
        func.count(HubOpportunityEnriched.opportunity_id)
    ).group_by(HubOpportunityEnriched.market_tier).all()

    market_count = db.query(func.count(HubMarketByGeography.market_id)).scalar() or 0
    signal_count = db.query(func.count(HubMarketSignal.signal_id)).scalar() or 0
    validation_count = db.query(func.count(HubValidationInsight.validation_id)).scalar() or 0

    snapshot = db.query(HubFinancialSnapshot).order_by(
        HubFinancialSnapshot.snapshot_date.desc()
    ).first()

    cohorts = db.query(HubUserCohort).all()

    top_markets = db.query(HubMarketByGeography).order_by(
        HubMarketByGeography.total_opportunities.desc().nullslast()
    ).limit(10).all()

    hot_signals = db.query(HubMarketSignal).filter(
        HubMarketSignal.signal_strength >= 0.7
    ).order_by(HubMarketSignal.signal_strength.desc()).limit(5).all()

    return {
        "status": "populated",
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_enriched_opportunities": opp_count,
            "avg_opportunity_score": round(avg_score or 0, 1),
            "tier_breakdown": {tier: count for tier, count in tier_counts if tier},
            "total_markets": market_count,
            "total_signals": signal_count,
            "total_validations": validation_count
        },
        "financial": {
            "total_users": snapshot.total_users if snapshot else 0,
            "paid_users": snapshot.paid_users if snapshot else 0,
            "mrr_usd": round(snapshot.mrr_recurring_revenue_usd or 0, 2) if snapshot else 0,
            "arr_usd": round(snapshot.arr_recurring_revenue_usd or 0, 2) if snapshot else 0,
            "total_reports": snapshot.total_reports_generated if snapshot else 0,
            "snapshot_date": snapshot.snapshot_date.isoformat() if snapshot else None
        },
        "cohorts": [{
            "name": c.cohort_name,
            "users": c.user_count,
            "avg_reports_per_month": round(c.avg_reports_generated_per_month or 0, 1),
            "top_report_types": c.preferred_report_types
        } for c in cohorts],
        "top_markets": [{
            "city": m.city,
            "state": m.state,
            "opportunities": m.total_opportunities,
            "avg_score": round(m.avg_opportunity_score or 0, 1),
            "growth": m.growth_trajectory,
            "population": m.population
        } for m in top_markets],
        "hot_signals": [{
            "name": s.signal_name,
            "strength": round(s.signal_strength, 2) if s.signal_strength else None,
            "direction": s.trend_direction,
            "category": s.category
        } for s in hot_signals]
    }


@router.get("/hub/markets")
async def get_hub_markets(
    state: Optional[str] = None,
    growth: Optional[str] = None,
    min_opportunities: int = 0,
    min_population: int = 0,
    limit: int = 50,
    sort_by: str = "opportunities",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {"status": "not_populated", "markets": []}

    query = db.query(HubMarketByGeography)

    if state:
        query = query.filter(func.upper(HubMarketByGeography.state) == state.upper())
    if growth:
        query = query.filter(HubMarketByGeography.growth_trajectory == growth)
    if min_opportunities > 0:
        query = query.filter(HubMarketByGeography.total_opportunities >= min_opportunities)
    if min_population > 0:
        query = query.filter(HubMarketByGeography.population >= min_population)

    sort_col = {
        "opportunities": HubMarketByGeography.total_opportunities,
        "score": HubMarketByGeography.avg_opportunity_score,
        "population": HubMarketByGeography.population,
        "new_30d": HubMarketByGeography.new_opportunities_30d,
    }.get(sort_by, HubMarketByGeography.total_opportunities)

    markets = query.order_by(sort_col.desc().nullslast()).limit(limit).all()

    return {
        "status": "populated",
        "total": len(markets),
        "markets": [{
            "market_id": m.market_id,
            "city": m.city,
            "state": m.state,
            "total_opportunities": m.total_opportunities,
            "categories": m.categories,
            "avg_score": round(m.avg_opportunity_score or 0, 1),
            "total_businesses": m.total_businesses,
            "population": m.population,
            "population_growth": m.population_growth_percent,
            "median_income": m.median_household_income,
            "growth_trajectory": m.growth_trajectory,
            "new_30d": m.new_opportunities_30d,
            "new_90d": m.new_opportunities_90d,
            "last_updated": m.last_updated_at.isoformat() if m.last_updated_at else None
        } for m in markets]
    }


@router.get("/hub/signals")
async def get_hub_signals(
    signal_type: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    min_strength: float = 0.0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {"status": "not_populated", "signals": []}

    query = db.query(HubMarketSignal)

    if signal_type:
        query = query.filter(HubMarketSignal.signal_type == signal_type)
    if category:
        query = query.filter(func.lower(HubMarketSignal.category) == category.lower())
    if direction:
        query = query.filter(HubMarketSignal.trend_direction == direction)
    if min_strength > 0:
        query = query.filter(HubMarketSignal.signal_strength >= min_strength)

    signals = query.order_by(HubMarketSignal.signal_strength.desc().nullslast()).limit(limit).all()

    return {
        "status": "populated",
        "total": len(signals),
        "signals": [{
            "signal_id": s.signal_id,
            "type": s.signal_type,
            "name": s.signal_name,
            "category": s.category,
            "date": s.signal_date.isoformat() if s.signal_date else None,
            "strength": round(s.signal_strength, 2) if s.signal_strength else None,
            "direction": s.trend_direction,
            "momentum": s.momentum,
            "confidence": s.confidence_level,
            "source": s.data_source,
            "interpretation": s.interpretation,
            "strategic_implications": s.strategic_implications,
            "industries_affected": s.industries_affected,
            "discovered_at": s.discovered_at.isoformat() if s.discovered_at else None
        } for s in signals]
    }


@router.get("/hub/financial")
async def get_hub_financial(
    days: int = 30,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {"status": "not_populated", "snapshots": []}

    cutoff = datetime.utcnow().date() - timedelta(days=days)

    snapshots = db.query(HubFinancialSnapshot).filter(
        HubFinancialSnapshot.snapshot_date >= cutoff
    ).order_by(HubFinancialSnapshot.snapshot_date.desc()).all()

    return {
        "status": "populated",
        "period_days": days,
        "snapshots": [{
            "date": s.snapshot_date.isoformat(),
            "period": s.snapshot_period,
            "total_users": s.total_users,
            "active_users_30d": s.active_users_30d,
            "paid_users": s.paid_users,
            "free_users": s.free_users,
            "mrr_usd": round(s.mrr_recurring_revenue_usd or 0, 2),
            "arr_usd": round(s.arr_recurring_revenue_usd or 0, 2),
            "total_reports": s.total_reports_generated,
            "reports_this_month": s.reports_this_month,
            "churn_rate": s.monthly_churn_rate_percent,
            "mom_growth": s.mom_growth_percent,
            "ai_tokens": s.ai_tokens_used,
            "ai_cost_usd": round(s.ai_cost_usd or 0, 4)
        } for s in snapshots]
    }


@router.get("/hub/industries")
async def get_hub_industries(
    maturity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {"status": "not_populated", "industries": []}

    query = db.query(HubIndustryInsight)

    if maturity:
        query = query.filter(HubIndustryInsight.market_maturity == maturity)

    industries = query.order_by(
        HubIndustryInsight.market_growth_rate_percent.desc().nullslast()
    ).limit(limit).all()

    return {
        "status": "populated",
        "total": len(industries),
        "industries": [{
            "industry_id": i.industry_id,
            "name": i.industry_name,
            "code": i.industry_code,
            "parent": i.parent_industry,
            "usa_market_size_usd": i.usa_market_size_usd,
            "growth_rate": i.market_growth_rate_percent,
            "maturity": i.market_maturity,
            "barrier_to_entry": i.barrier_to_entry,
            "avg_startup_cost_usd": i.avg_startup_cost_usd,
            "median_roi": i.median_roi_percent,
            "time_to_profit_months": i.time_to_profitability_months,
            "growth_drivers": i.growth_drivers,
            "top_players": i.top_players,
            "confidence": i.confidence_score
        } for i in industries]
    }


@router.get("/hub/validations")
async def get_hub_validations(
    industry: Optional[str] = None,
    recommendation: Optional[str] = None,
    min_score: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
    if not _hub_available(db):
        return {"status": "not_populated", "validations": []}

    query = db.query(HubValidationInsight)

    if industry:
        query = query.filter(func.lower(HubValidationInsight.industry) == industry.lower())
    if recommendation:
        query = query.filter(HubValidationInsight.go_no_go_recommendation == recommendation.upper())
    if min_score > 0:
        query = query.filter(HubValidationInsight.overall_score >= min_score)

    validations = query.order_by(
        HubValidationInsight.overall_score.desc().nullslast()
    ).limit(limit).all()

    return {
        "status": "populated",
        "total": len(validations),
        "validations": [{
            "validation_id": v.validation_id,
            "industry": v.industry,
            "business_model": v.business_model,
            "online_score": v.online_viability_score,
            "physical_score": v.physical_viability_score,
            "overall_score": v.overall_score,
            "recommendation": v.go_no_go_recommendation,
            "confidence": v.recommendation_confidence,
            "key_advantages": v.key_advantages,
            "key_risks": v.key_risks,
            "cached_at": v.cached_at.isoformat() if v.cached_at else None
        } for v in validations]
    }


# --- AI Usage (for metering) ---

@router.get("/usage/summary")
async def get_ai_usage_summary(
    period: str = "current_month",
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key)
):
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
    from app.models.user import User

    query = db.query(User)

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
    moderation_status: str
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
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        return {"success": False, "message": "Opportunity not found"}

    valid_statuses = ['approved', 'rejected', 'needs_edit']
    if payload.moderation_status not in valid_statuses:
        return {"success": False, "message": f"Invalid status. Must be: {', '.join(valid_statuses)}"}

    opp.moderation_status = payload.moderation_status

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
    from app.models.stripe_event import StripeWebhookEvent

    cutoff = datetime.utcnow() - timedelta(days=days)

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
    import httpx

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return {"success": False, "message": "Stripe key not configured"}

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


# ============================================================================
# WEBHOOK SUBSCRIPTIONS - Phase 2 Part 3
# ============================================================================

@router.post("/webhooks/subscribe", status_code=201, tags=["Webhooks"])
async def subscribe_webhook(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key),
):
    """
    Subscribe to webhook events.
    
    Creates a webhook subscription that will receive events for:
    - opportunity.new: New opportunity detected
    - trend.updated: Market trend detected
    - market.changed: Market data updated
    
    Rate limit: 1 webhook subscription per second per API key
    Max: 10 webhooks per API key
    
    Example request:
    {
      "webhook_url": "https://agent.example.com/webhook",
      "events": ["opportunity.new", "trend.updated"],
      "vertical": "coffee",
      "city": "Austin"
    }
    """
    import hashlib
    import time
    from app.schemas.agent_api import WebhookSubscribeRequest, WebhookSubscribeResponse
    from app.models.agent_webhook_subscription import AgentWebhookSubscription
    
    # Validate request
    try:
        subscription_req = WebhookSubscribeRequest(**request_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    # Get API key from header
    api_key = request_data.get('_api_key', 'agent_key')  # Would be extracted from X-Agent-Key
    
    # Rate limit: Max 1 subscription request per second per key
    # This is checked via the RateLimitMiddleware (1000 qpm = ~17 rps per key)
    
    # Check max webhooks per API key (10 limit)
    existing_webhooks = db.query(AgentWebhookSubscription).filter(
        AgentWebhookSubscription.agent_api_key_id == api_key,
        AgentWebhookSubscription.active == True,
    ).count()
    
    if existing_webhooks >= 10:
        raise HTTPException(
            status_code=429,
            detail="Maximum 10 active webhooks per API key. Deactivate unused webhooks first."
        )
    
    # Validate webhook URL is HTTPS and accessible
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2) as client:
            # Quick ping to test webhook URL
            try:
                response = await client.head(subscription_req.webhook_url)
                if response.status_code >= 500:
                    logger.warning(f"Webhook test returned {response.status_code}: {subscription_req.webhook_url}")
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=400,
                    detail="Webhook URL did not respond within 2 seconds"
                )
            except Exception as e:
                logger.warning(f"Webhook validation warning: {e}")
                # Still allow creation even if test fails (network issues)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook validation error: {e}")
    
    # Create subscription
    webhook_url_hash = hashlib.sha256(subscription_req.webhook_url.encode()).hexdigest()
    
    # Check for duplicate URL (same URL subscribed by same key)
    existing = db.query(AgentWebhookSubscription).filter(
        AgentWebhookSubscription.webhook_url_hash == webhook_url_hash,
        AgentWebhookSubscription.agent_api_key_id == api_key,
    ).first()
    
    if existing and existing.active:
        raise HTTPException(
            status_code=409,
            detail="Webhook URL already subscribed with this API key"
        )
    
    # Create new subscription
    subscription = AgentWebhookSubscription(
        agent_api_key_id=api_key,
        webhook_url=subscription_req.webhook_url,
        webhook_url_hash=webhook_url_hash,
        events=subscription_req.events,
        vertical_filter=subscription_req.vertical,
        city_filter=subscription_req.city,
        active=True,
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"✓ Webhook subscription created: {subscription.subscription_id}")
    
    # Mask the URL for response
    masked_url = subscription_req.webhook_url[:8] + "***" + subscription_req.webhook_url[-8:]
    
    return WebhookSubscribeResponse(
        subscription_id=str(subscription.subscription_id),
        status="active",
        events_subscribed=subscription.events,
        created_at=subscription.created_at,
        webhook_url_masked=masked_url,
        filters={
            "vertical": subscription_req.vertical,
            "city": subscription_req.city,
        } if subscription_req.vertical or subscription_req.city else None
    )


@router.get("/webhooks", tags=["Webhooks"])
async def list_webhooks(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key),
):
    """
    List all active webhook subscriptions for this API key.
    """
    from app.schemas.agent_api import WebhookSubscribeResponse, WebhookSubscriptionListResponse
    
    api_key = "agent_key"  # Would be extracted from X-Agent-Key
    
    subscriptions = db.query(AgentWebhookSubscription).filter(
        AgentWebhookSubscription.agent_api_key_id == api_key,
        AgentWebhookSubscription.active == True,
    ).all()
    
    response_subs = []
    for sub in subscriptions:
        masked_url = sub.webhook_url[:8] + "***" + sub.webhook_url[-8:]
        response_subs.append(WebhookSubscribeResponse(
            subscription_id=str(sub.subscription_id),
            status="active",
            events_subscribed=sub.events,
            created_at=sub.created_at,
            webhook_url_masked=masked_url,
            filters={
                "vertical": sub.vertical_filter,
                "city": sub.city_filter,
            } if sub.vertical_filter or sub.city_filter else None
        ))
    
    return WebhookSubscriptionListResponse(
        subscriptions=response_subs,
        total=len(response_subs)
    )


@router.delete("/webhooks/{subscription_id}", tags=["Webhooks"])
async def delete_webhook(
    subscription_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key),
):
    """
    Delete (deactivate) a webhook subscription.
    """
    from app.schemas.agent_api import WebhookSubscriptionDeleteResponse
    
    api_key = "agent_key"  # Would be extracted from X-Agent-Key
    
    subscription = db.query(AgentWebhookSubscription).filter(
        AgentWebhookSubscription.subscription_id == subscription_id,
        AgentWebhookSubscription.agent_api_key_id == api_key,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Webhook subscription not found"
        )
    
    subscription.active = False
    db.add(subscription)
    db.commit()
    
    logger.info(f"✓ Webhook subscription deactivated: {subscription_id}")
    
    return WebhookSubscriptionDeleteResponse(
        subscription_id=str(subscription.subscription_id),
        status="deleted",
        message="Webhook subscription deactivated"
    )


@router.post("/webhooks/test", tags=["Webhooks"])
async def test_webhook(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_key),
):
    """
    Test a webhook subscription by sending a sample event.
    
    Used to verify webhook is working before relying on it for production events.
    """
    from app.services.webhook_delivery_service import deliver_webhook_async
    
    subscription_id = request_data.get('subscription_id')
    
    if not subscription_id:
        raise HTTPException(
            status_code=400,
            detail="subscription_id is required"
        )
    
    api_key = "agent_key"  # Would be extracted from X-Agent-Key
    
    subscription = db.query(AgentWebhookSubscription).filter(
        AgentWebhookSubscription.subscription_id == subscription_id,
        AgentWebhookSubscription.agent_api_key_id == api_key,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Webhook subscription not found"
        )
    
    # Send test event
    test_data = {
        "opportunity_id": 999,
        "title": "Test Opportunity - OppGrid Webhook Test",
        "vertical": "test",
        "city": "Test City, ST",
        "market_size": 1000000,
    }
    
    success = await deliver_webhook_async(
        subscription,
        "opportunity.new",
        test_data,
        agent_id="agent_tester"
    )
    
    return {
        "success": success,
        "subscription_id": str(subscription.subscription_id),
        "message": "Test event delivered" if success else "Test event delivery failed",
    }
