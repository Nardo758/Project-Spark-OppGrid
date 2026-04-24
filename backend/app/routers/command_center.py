"""
Command Center API
Centralized management for data sources, patterns, jobs, and system metrics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, and_, text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json

from app.db.database import get_db
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.data_source import DataSource, ValidationPattern, SystemMetric, ScrapeJob
from app.models.scraped_source import ScrapedSource, SourceType
from app.models.job_run import JobRun
from app.core.dependencies import get_current_admin_user
from app.services.serpapi_service import serpapi_service

router = APIRouter()


class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    base_weight: float = 1.0
    rate_limit_per_minute: int = 60
    config: dict = {}
    is_active: bool = True


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    base_weight: Optional[float] = None
    rate_limit_per_minute: Optional[int] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class PatternCreate(BaseModel):
    name: str
    regex_pattern: str
    category: str
    confidence: float = 0.8
    validation_level: str = "validated"
    source_specific: dict = {}
    is_active: bool = True


class PatternUpdate(BaseModel):
    name: Optional[str] = None
    regex_pattern: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    validation_level: Optional[str] = None
    source_specific: Optional[dict] = None
    is_active: Optional[bool] = None


class JobCreate(BaseModel):
    source_name: str
    job_type: str = "manual"
    priority: int = 5
    config: dict = {}


@router.get("/dashboard")
async def get_dashboard(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get Command Center dashboard overview"""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    sources = db.query(DataSource).all()
    source_stats = {
        "total": len(sources),
        "active": sum(1 for s in sources if s.is_active and s.status == "active"),
        "paused": sum(1 for s in sources if s.status == "paused"),
        "error": sum(1 for s in sources if s.status == "error"),
    }
    
    total_opps = db.query(Opportunity).count()
    opps_24h = db.query(Opportunity).filter(Opportunity.created_at >= last_24h).count()
    opps_7d = db.query(Opportunity).filter(Opportunity.created_at >= last_7d).count()
    
    scraped_24h = db.query(ScrapedSource).filter(ScrapedSource.received_at >= last_24h).count()
    scraped_7d = db.query(ScrapedSource).filter(ScrapedSource.received_at >= last_7d).count()
    
    processed = db.query(ScrapedSource).filter(ScrapedSource.processed == 1).count()
    unprocessed = db.query(ScrapedSource).filter(ScrapedSource.processed == 0).count()
    errors = db.query(ScrapedSource).filter(ScrapedSource.error_message.isnot(None)).count()
    
    jobs = db.query(ScrapeJob).order_by(desc(ScrapeJob.created_at)).limit(10).all()
    recent_jobs = []
    for job in jobs:
        recent_jobs.append({
            "id": job.id,
            "source_name": job.source_name,
            "status": job.status,
            "job_type": job.job_type,
            "items_processed": job.items_processed,
            "items_accepted": job.items_accepted,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        })
    
    source_breakdown = db.query(
        ScrapedSource.source_type,
        func.count(ScrapedSource.id).label("count")
    ).group_by(ScrapedSource.source_type).all()
    
    by_source = {row.source_type: row.count for row in source_breakdown}
    
    patterns = db.query(ValidationPattern).filter(ValidationPattern.is_active == True).all()
    pattern_stats = {
        "total": len(patterns),
        "total_hits": sum(p.hit_count for p in patterns),
        "avg_confidence": round(sum(p.confidence for p in patterns) / len(patterns), 2) if patterns else 0,
    }
    
    tier_breakdown = db.query(
        Opportunity.status,
        func.count(Opportunity.id).label("count")
    ).group_by(Opportunity.status).all()
    
    tiers = {row.status: row.count for row in tier_breakdown}
    
    return {
        "sources": source_stats,
        "opportunities": {
            "total": total_opps,
            "last_24h": opps_24h,
            "last_7d": opps_7d,
        },
        "scraping": {
            "last_24h": scraped_24h,
            "last_7d": scraped_7d,
            "processed": processed,
            "pending": unprocessed,
            "errors": errors,
            "by_source": by_source,
        },
        "patterns": pattern_stats,
        "tiers": tiers,
        "recent_jobs": recent_jobs,
    }


@router.get("/sources")
async def list_sources(
    active_only: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all data sources with their status and metrics"""
    query = db.query(DataSource)
    if active_only:
        query = query.filter(DataSource.is_active == True)
    
    sources = query.order_by(DataSource.name).all()
    
    result = []
    for source in sources:
        scraped_count = db.query(ScrapedSource).filter(
            ScrapedSource.source_type == source.source_type
        ).count()
        
        result.append({
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "status": source.status,
            "is_active": source.is_active,
            "base_weight": source.base_weight,
            "rate_limit_per_minute": source.rate_limit_per_minute,
            "config": source.config,
            "total_scrapes": source.total_scrapes or scraped_count,
            "valid_opportunities": source.valid_opportunities,
            "failed_scrapes": source.failed_scrapes,
            "average_score": source.average_score,
            "last_scraped_at": source.last_scraped_at.isoformat() if source.last_scraped_at else None,
            "last_error": source.last_error,
            "last_error_at": source.last_error_at.isoformat() if source.last_error_at else None,
            "created_at": source.created_at.isoformat() if source.created_at else None,
        })
    
    return {"sources": result}


@router.post("/sources")
async def create_source(
    source: DataSourceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new data source"""
    existing = db.query(DataSource).filter(DataSource.name == source.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Source with this name already exists")
    
    new_source = DataSource(
        name=source.name,
        source_type=source.source_type,
        base_weight=source.base_weight,
        rate_limit_per_minute=source.rate_limit_per_minute,
        config=source.config,
        is_active=source.is_active,
        status="active" if source.is_active else "disabled",
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    return {"id": new_source.id, "message": "Source created successfully"}


@router.put("/sources/{source_id}")
async def update_source(
    source_id: int,
    update: DataSourceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update a data source"""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)
    
    db.commit()
    return {"message": "Source updated successfully"}


@router.post("/sources/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Toggle a data source active/inactive"""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source.is_active = not source.is_active
    source.status = "active" if source.is_active else "disabled"
    db.commit()
    
    return {"id": source.id, "is_active": source.is_active, "status": source.status}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a data source"""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()
    return {"message": "Source deleted successfully"}


@router.get("/patterns")
async def list_patterns(
    category: Optional[str] = None,
    active_only: bool = True,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List validation patterns"""
    query = db.query(ValidationPattern)
    
    if active_only:
        query = query.filter(ValidationPattern.is_active == True)
    if category:
        query = query.filter(ValidationPattern.category == category)
    
    total = query.count()
    patterns = query.order_by(desc(ValidationPattern.confidence)).offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for p in patterns:
        result.append({
            "id": p.id,
            "name": p.name,
            "regex_pattern": p.regex_pattern,
            "category": p.category,
            "confidence": p.confidence,
            "validation_level": p.validation_level,
            "source_specific": p.source_specific,
            "hit_count": p.hit_count,
            "false_positive_count": p.false_positive_count,
            "last_matched_at": p.last_matched_at.isoformat() if p.last_matched_at else None,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    
    categories = db.query(ValidationPattern.category).distinct().all()
    
    return {
        "patterns": result,
        "total": total,
        "page": page,
        "limit": limit,
        "categories": [c[0] for c in categories],
    }


@router.post("/patterns")
async def create_pattern(
    pattern: PatternCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new validation pattern"""
    new_pattern = ValidationPattern(
        name=pattern.name,
        regex_pattern=pattern.regex_pattern,
        category=pattern.category,
        confidence=pattern.confidence,
        validation_level=pattern.validation_level,
        source_specific=pattern.source_specific,
        is_active=pattern.is_active,
    )
    db.add(new_pattern)
    db.commit()
    db.refresh(new_pattern)
    
    return {"id": new_pattern.id, "message": "Pattern created successfully"}


@router.put("/patterns/{pattern_id}")
async def update_pattern(
    pattern_id: int,
    update: PatternUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update a validation pattern"""
    pattern = db.query(ValidationPattern).filter(ValidationPattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pattern, key, value)
    
    db.commit()
    return {"message": "Pattern updated successfully"}


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a validation pattern"""
    pattern = db.query(ValidationPattern).filter(ValidationPattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    db.delete(pattern)
    db.commit()
    return {"message": "Pattern deleted successfully"}


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    source_name: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List scrape jobs"""
    query = db.query(ScrapeJob)
    
    if status:
        query = query.filter(ScrapeJob.status == status)
    if source_name:
        query = query.filter(ScrapeJob.source_name == source_name)
    
    jobs = query.order_by(desc(ScrapeJob.created_at)).limit(limit).all()
    
    result = []
    for job in jobs:
        result.append({
            "id": job.id,
            "source_name": job.source_name,
            "job_type": job.job_type,
            "status": job.status,
            "priority": job.priority,
            "items_processed": job.items_processed,
            "items_accepted": job.items_accepted,
            "items_rejected": job.items_rejected,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        })
    
    return {"jobs": result}


@router.post("/jobs")
async def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a manual scrape job"""
    source = db.query(DataSource).filter(DataSource.name == job.source_name).first()
    
    new_job = ScrapeJob(
        source_id=source.id if source else None,
        source_name=job.source_name,
        job_type=job.job_type,
        priority=job.priority,
        config=job.config,
        status="pending",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return {"id": new_job.id, "message": "Job created successfully"}


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Retry a failed job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.retry_count >= job.max_retries:
        raise HTTPException(status_code=400, detail="Max retries exceeded")
    
    job.status = "pending"
    job.retry_count += 1
    job.error_message = None
    db.commit()
    
    return {"message": "Job queued for retry"}


@router.get("/metrics")
async def get_metrics(
    metric_type: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get system metrics"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(SystemMetric).filter(SystemMetric.recorded_at >= since)
    
    if metric_type:
        query = query.filter(SystemMetric.metric_type == metric_type)
    
    metrics = query.order_by(desc(SystemMetric.recorded_at)).limit(1000).all()
    
    result = []
    for m in metrics:
        result.append({
            "id": m.id,
            "metric_type": m.metric_type,
            "metric_name": m.metric_name,
            "value": m.value,
            "extra_data": m.extra_data,
            "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
        })
    
    return {"metrics": result, "hours": hours}


@router.get("/scrapes")
async def list_scrapes(
    source_type: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List recent scraped items"""
    query = db.query(ScrapedSource)
    
    if source_type:
        query = query.filter(ScrapedSource.source_type == source_type)
    if processed is not None:
        query = query.filter(ScrapedSource.processed == (1 if processed else 0))
    
    scrapes = query.order_by(desc(ScrapedSource.received_at)).limit(limit).all()
    
    result = []
    for s in scrapes:
        result.append({
            "id": s.id,
            "external_id": s.external_id,
            "source_type": s.source_type,
            "scrape_id": s.scrape_id,
            "processed": s.processed == 1,
            "error_message": s.error_message,
            "received_at": s.received_at.isoformat() if s.received_at else None,
            "processed_at": s.processed_at.isoformat() if s.processed_at else None,
            "raw_data_preview": str(s.raw_data)[:200] if s.raw_data else None,
        })
    
    return {"scrapes": result}


@router.get("/pipeline-stats")
async def get_pipeline_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get detailed pipeline processing statistics"""
    now = datetime.utcnow()
    
    hourly_stats = []
    for i in range(24):
        hour_start = now - timedelta(hours=i+1)
        hour_end = now - timedelta(hours=i)
        
        received = db.query(ScrapedSource).filter(
            and_(ScrapedSource.received_at >= hour_start, ScrapedSource.received_at < hour_end)
        ).count()
        
        processed = db.query(ScrapedSource).filter(
            and_(ScrapedSource.processed_at >= hour_start, ScrapedSource.processed_at < hour_end)
        ).count()
        
        opportunities = db.query(Opportunity).filter(
            and_(Opportunity.created_at >= hour_start, Opportunity.created_at < hour_end)
        ).count()
        
        hourly_stats.append({
            "hour": hour_start.strftime("%Y-%m-%d %H:00"),
            "received": received,
            "processed": processed,
            "opportunities": opportunities,
        })
    
    category_breakdown = db.query(
        Opportunity.category,
        func.count(Opportunity.id).label("count")
    ).group_by(Opportunity.category).order_by(desc("count")).limit(10).all()
    
    categories = [{"category": c.category, "count": c.count} for c in category_breakdown]
    
    source_performance = db.query(
        ScrapedSource.source_type,
        func.count(ScrapedSource.id).label("total"),
        func.sum(ScrapedSource.processed).label("processed"),
    ).group_by(ScrapedSource.source_type).all()
    
    performance = []
    for sp in source_performance:
        success_rate = (sp.processed / sp.total * 100) if sp.total > 0 else 0
        performance.append({
            "source_type": sp.source_type,
            "total": sp.total,
            "processed": sp.processed or 0,
            "success_rate": round(success_rate, 1),
        })
    
    return {
        "hourly_stats": hourly_stats[::-1],
        "category_breakdown": categories,
        "source_performance": performance,
    }


@router.post("/seed-default-sources")
async def seed_default_sources(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Seed default data sources if they don't exist"""
    default_sources = [
        {"name": "Reddit", "source_type": "reddit", "base_weight": 1.0},
        {"name": "Google Maps", "source_type": "google_maps", "base_weight": 0.9},
        {"name": "Yelp", "source_type": "yelp", "base_weight": 0.85},
        {"name": "Twitter/X", "source_type": "twitter", "base_weight": 0.8},
        {"name": "Nextdoor", "source_type": "nextdoor", "base_weight": 0.75},
        {"name": "Custom Webhook", "source_type": "custom", "base_weight": 0.7},
    ]
    
    created = 0
    for src in default_sources:
        existing = db.query(DataSource).filter(DataSource.source_type == src["source_type"]).first()
        if not existing:
            new_source = DataSource(**src, status="active", is_active=True)
            db.add(new_source)
            created += 1
    
    db.commit()
    return {"message": f"Seeded {created} default sources"}


# ===== APIFY INTEGRATION ENDPOINTS =====

from app.services.apify_service import apify_service


class ApifyScheduleCreate(BaseModel):
    name: str
    cron_expression: str
    actor_id: str
    input_data: dict = {}
    timezone: str = "UTC"
    is_enabled: bool = True


class ApifyScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_enabled: Optional[bool] = None
    timezone: Optional[str] = None


@router.get("/apify/status")
async def get_apify_status(
    admin: User = Depends(get_current_admin_user)
):
    """Check if Apify is configured"""
    return {
        "configured": apify_service.is_configured(),
        "message": "Apify API token configured" if apify_service.is_configured() else "APIFY_API_TOKEN not set"
    }


@router.get("/apify/actors")
async def get_apify_actors(
    limit: int = Query(default=100, le=500),
    admin: User = Depends(get_current_admin_user)
):
    """Get list of Apify actors"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    actors = apify_service.get_actors(limit=limit)
    return {"actors": actors, "count": len(actors)}


@router.get("/apify/actors/{actor_id}")
async def get_apify_actor(
    actor_id: str,
    admin: User = Depends(get_current_admin_user)
):
    """Get specific Apify actor details"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    actor = apify_service.get_actor(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/apify/actors/{actor_id}/run")
async def run_apify_actor(
    actor_id: str,
    input_data: dict = None,
    admin: User = Depends(get_current_admin_user)
):
    """Start an Apify actor run"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    try:
        run_info = apify_service.start_actor(actor_id, input_data)
        return {"message": "Actor started", "run": run_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RedditRunRequest(BaseModel):
    subreddits: Optional[List[str]] = None
    max_items: int = 200


@router.post("/apify/reddit/run")
async def run_reddit_scraper(
    req: Optional[RedditRunRequest] = None,
    admin: User = Depends(get_current_admin_user)
):
    """
    Trigger a Reddit scraper run using the trudax/reddit-scraper-lite actor.
    Uses DEFAULT_REDDIT_SUBREDDITS and DEFAULT_REDDIT_ACTOR_INPUT when no
    custom configuration is provided.

    Apify will fire POST /api/v1/webhook/apify when the run completes.
    Register that URL (with APIFY_WEBHOOK_SECRET) in your Apify actor webhook settings.
    """
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="APIFY_API_TOKEN is not configured")

    from app.services.apify_service import DEFAULT_REDDIT_SUBREDDITS, REDDIT_ACTOR_ID

    subreddits = (req.subreddits if req else None) or DEFAULT_REDDIT_SUBREDDITS
    max_items = req.max_items if req else 200

    try:
        run_info = apify_service.run_reddit_scraper(subreddits=subreddits, max_items=max_items)
        return {
            "message": "Reddit scraper run triggered",
            "actor_id": REDDIT_ACTOR_ID,
            "subreddits": subreddits,
            "max_items": max_items,
            "run": run_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/apify/runs")
async def get_apify_runs(
    actor_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    admin: User = Depends(get_current_admin_user)
):
    """Get list of Apify runs"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    runs = apify_service.get_runs(actor_id=actor_id, limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/apify/runs/{run_id}")
async def get_apify_run(
    run_id: str,
    admin: User = Depends(get_current_admin_user)
):
    """Get specific Apify run details"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    run = apify_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/apify/runs/{run_id}/abort")
async def abort_apify_run(
    run_id: str,
    admin: User = Depends(get_current_admin_user)
):
    """Abort an Apify run"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    success = apify_service.abort_run(run_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to abort run")
    return {"message": "Run aborted"}


@router.get("/apify/runs/{run_id}/dataset")
async def get_apify_run_dataset(
    run_id: str,
    limit: int = Query(default=100, le=1000),
    admin: User = Depends(get_current_admin_user)
):
    """Get dataset items from an Apify run"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    run = apify_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise HTTPException(status_code=404, detail="No dataset found for this run")
    
    items = apify_service.get_dataset_items(dataset_id, limit=limit)
    return {"items": items, "count": len(items), "dataset_id": dataset_id}


@router.get("/apify/schedules")
async def get_apify_schedules(
    limit: int = Query(default=100, le=500),
    admin: User = Depends(get_current_admin_user)
):
    """Get list of Apify schedules"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    schedules = apify_service.get_schedules(limit=limit)
    return {"schedules": schedules, "count": len(schedules)}


@router.get("/apify/schedules/{schedule_id}")
async def get_apify_schedule(
    schedule_id: str,
    admin: User = Depends(get_current_admin_user)
):
    """Get specific Apify schedule details"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    schedule = apify_service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/apify/schedules")
async def create_apify_schedule(
    data: ApifyScheduleCreate,
    admin: User = Depends(get_current_admin_user)
):
    """Create a new Apify schedule"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    try:
        schedule = apify_service.create_schedule(
            name=data.name,
            cron_expression=data.cron_expression,
            actor_id=data.actor_id,
            input_data=data.input_data,
            timezone=data.timezone,
            is_enabled=data.is_enabled
        )
        return {"message": "Schedule created", "schedule": schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/apify/schedules/{schedule_id}")
async def update_apify_schedule(
    schedule_id: str,
    data: ApifyScheduleUpdate,
    admin: User = Depends(get_current_admin_user)
):
    """Update an Apify schedule"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    try:
        schedule = apify_service.update_schedule(
            schedule_id=schedule_id,
            name=data.name,
            cron_expression=data.cron_expression,
            is_enabled=data.is_enabled,
            timezone=data.timezone
        )
        return {"message": "Schedule updated", "schedule": schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/apify/schedules/{schedule_id}")
async def delete_apify_schedule(
    schedule_id: str,
    admin: User = Depends(get_current_admin_user)
):
    """Delete an Apify schedule"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    success = apify_service.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete schedule")
    return {"message": "Schedule deleted"}


class ApifyGoogleMapsSearchRequest(BaseModel):
    search_terms: list
    location: str
    max_results: int = 100
    max_reviews: int = 20


@router.post("/apify/google-maps/search")
async def apify_google_maps_search(
    data: ApifyGoogleMapsSearchRequest,
    admin: User = Depends(get_current_admin_user)
):
    """Start a Google Maps search via Apify"""
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    try:
        run_info = apify_service.run_google_maps_search(
            search_terms=data.search_terms,
            location=data.location,
            max_results=data.max_results,
            max_reviews=data.max_reviews
        )
        return {"message": "Google Maps search started", "run": run_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apify/runs/{run_id}/import")
async def import_apify_run(
    run_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Import results from an Apify run into the database"""
    import traceback
    
    if not apify_service.is_configured():
        raise HTTPException(status_code=400, detail="Apify not configured")
    
    try:
        print(f"Starting import for run_id: {run_id}")
        import_result = apify_service.import_existing_run(run_id)
        print(f"Import result status: {import_result.get('status')}, total: {import_result.get('total_results', 0)}")
        
        if import_result["status"] not in ["SUCCEEDED", "ABORTED"]:
            return import_result
        
        results = import_result.get("results", [])
        
        places_count = 0
        reviews_count = 0
        
        for place in results:
            place_data = {
                "source": "apify_google_maps",
                "source_id": place.get("placeId"),
                "content_type": "business",
                "title": place.get("title"),
                "content": f"Category: {place.get('categoryName', 'Unknown')}\nRating: {place.get('totalScore', 'N/A')}\nReviews: {place.get('reviewsCount', 0)}",
                "url": place.get("url"),
                "author": None,
                "location": place.get("city") or place.get("address"),
                "latitude": place.get("location", {}).get("lat") if place.get("location") else None,
                "longitude": place.get("location", {}).get("lng") if place.get("location") else None,
                "metadata": {
                    "category": place.get("categoryName"),
                    "rating": place.get("totalScore"),
                    "reviews_count": place.get("reviewsCount"),
                    "phone": place.get("phone"),
                    "website": place.get("website"),
                    "street": place.get("street"),
                    "city": place.get("city"),
                    "state": place.get("state"),
                    "postal_code": place.get("postalCode"),
                }
            }
            
            stmt = text("""
                INSERT INTO scraped_data (source, source_id, content_type, title, content, url, author, location, latitude, longitude, metadata, scraped_at)
                VALUES (:source, :source_id, :content_type, :title, :content, :url, :author, :location, :latitude, :longitude, :metadata, NOW())
                ON CONFLICT (source, source_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    scraped_at = NOW()
                RETURNING id
            """)
            
            result = db.execute(stmt, {
                **place_data,
                "metadata": json.dumps(place_data["metadata"])
            })
            place_db_id = result.scalar()
            places_count += 1
            
            reviews = place.get("reviews", [])
            for review in reviews:
                review_text = review.get("text") or review.get("snippet") or ""
                if not review_text:
                    continue
                    
                review_data = {
                    "source": "apify_google_maps_review",
                    "source_id": f"{place.get('placeId')}_{review.get('reviewerId', '')}_{review.get('publishedAtDate', '')}",
                    "content_type": "review",
                    "title": f"Review of {place.get('title', 'Unknown')}",
                    "content": review_text,
                    "url": place.get("url"),
                    "author": review.get("name"),
                    "location": place.get("city") or place.get("address"),
                    "metadata": {
                        "rating": review.get("stars"),
                        "likes_count": review.get("likesCount", 0),
                        "response_from_owner": review.get("responseFromOwnerText"),
                        "business_name": place.get("title"),
                        "business_category": place.get("categoryName"),
                        "published_at": review.get("publishedAtDate"),
                    }
                }
                
                stmt = text("""
                    INSERT INTO scraped_data (source, source_id, content_type, title, content, url, author, location, metadata, scraped_at)
                    VALUES (:source, :source_id, :content_type, :title, :content, :url, :author, :location, :metadata, NOW())
                    ON CONFLICT (source, source_id) DO NOTHING
                """)
                
                db.execute(stmt, {
                    **review_data,
                    "metadata": json.dumps(review_data["metadata"])
                })
                reviews_count += 1
        
        db.commit()
        
        return {
            "status": "imported",
            "run_id": run_id,
            "places_imported": places_count,
            "reviews_imported": reviews_count,
            "total_results": len(results)
        }
        
    except Exception as e:
        print(f"Import error: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


class SerpAPISearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    num: int = 10
    gl: str = "us"
    hl: str = "en"


class SerpAPIMapsSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    ll: Optional[str] = None
    hl: str = "en"


class SerpAPIReviewsRequest(BaseModel):
    data_id: str
    sort_by: str = "qualityScore"
    hl: str = "en"
    next_page_token: Optional[str] = None


class SerpAPIPlacesWithReviewsRequest(BaseModel):
    query: str
    location: Optional[str] = None
    ll: Optional[str] = None
    max_places: int = 5
    reviews_per_place: int = 10


@router.get("/serpapi/status")
async def get_serpapi_status(
    admin: User = Depends(get_current_admin_user)
):
    """Check SerpAPI configuration status and account info"""
    return serpapi_service.get_account_info()


@router.post("/serpapi/google-search")
async def serpapi_google_search(
    data: SerpAPISearchRequest,
    admin: User = Depends(get_current_admin_user)
):
    """Execute a Google Search via SerpAPI"""
    if not serpapi_service.is_configured:
        raise HTTPException(status_code=400, detail="SERPAPI_KEY not configured")
    
    try:
        results = serpapi_service.google_search(
            query=data.query,
            location=data.location,
            num=data.num,
            gl=data.gl,
            hl=data.hl
        )
        return {
            "query": data.query,
            "organic_results": results.get("organic_results", []),
            "knowledge_graph": results.get("knowledge_graph"),
            "answer_box": results.get("answer_box"),
            "related_searches": results.get("related_searches", []),
            "total_results": results.get("search_information", {}).get("total_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/serpapi/google-maps")
async def serpapi_google_maps_search(
    data: SerpAPIMapsSearchRequest,
    admin: User = Depends(get_current_admin_user)
):
    """Search Google Maps via SerpAPI"""
    if not serpapi_service.is_configured:
        raise HTTPException(status_code=400, detail="SERPAPI_KEY not configured")
    
    try:
        results = serpapi_service.google_maps_search(
            query=data.query,
            location=data.location,
            ll=data.ll,
            hl=data.hl
        )
        return {
            "query": data.query,
            "local_results": results.get("local_results", []),
            "place_results": results.get("place_results"),
            "count": len(results.get("local_results", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/serpapi/google-maps-reviews")
async def serpapi_google_maps_reviews(
    data: SerpAPIReviewsRequest,
    admin: User = Depends(get_current_admin_user)
):
    """Get reviews for a Google Maps place via SerpAPI"""
    if not serpapi_service.is_configured:
        raise HTTPException(status_code=400, detail="SERPAPI_KEY not configured")
    
    try:
        results = serpapi_service.google_maps_reviews(
            data_id=data.data_id,
            sort_by=data.sort_by,
            hl=data.hl,
            next_page_token=data.next_page_token
        )
        return {
            "data_id": data.data_id,
            "reviews": results.get("reviews", []),
            "place_info": results.get("place_info"),
            "topics": results.get("topics", []),
            "rating": results.get("rating"),
            "total_reviews": results.get("total_reviews"),
            "next_page_token": results.get("serpapi_pagination", {}).get("next_page_token"),
            "count": len(results.get("reviews", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/serpapi/places-with-reviews")
async def serpapi_places_with_reviews(
    data: SerpAPIPlacesWithReviewsRequest,
    admin: User = Depends(get_current_admin_user)
):
    """Search for places and fetch their reviews in one call"""
    if not serpapi_service.is_configured:
        raise HTTPException(status_code=400, detail="SERPAPI_KEY not configured")
    
    try:
        results = serpapi_service.search_places_with_reviews(
            query=data.query,
            location=data.location,
            ll=data.ll,
            max_places=data.max_places,
            reviews_per_place=data.reviews_per_place
        )
        return {
            "query": data.query,
            "places": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/process")
async def process_signals_to_opportunities(
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """
    Process scraped_data signals into validated business opportunities.
    Uses the Signal-to-Opportunity conversion algorithm.
    """
    from app.services.signal_to_opportunity import get_signal_processor
    
    try:
        processor = get_signal_processor(db)
        results = processor.process_scraped_data(limit=limit)
        
        return {
            "success": True,
            "summary": {
                "total_signals": results['total_signals'],
                "passed_quality_filter": results['passed_quality_filter'],
                "clusters_formed": results['clusters_formed'],
                "opportunities_created": results['opportunities_created'],
                "duplicates_merged": results['duplicates_merged']
            },
            "opportunities": results['opportunities']
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/stats")
async def get_signal_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get statistics about scraped_data signals"""
    try:
        total_query = text("SELECT COUNT(*) FROM scraped_data")
        total = db.execute(total_query).scalar()
        
        by_source_query = text("""
            SELECT source, COUNT(*) as count 
            FROM scraped_data 
            GROUP BY source 
            ORDER BY count DESC
        """)
        by_source = [{"source": row[0], "count": row[1]} for row in db.execute(by_source_query)]
        
        by_location_query = text("""
            SELECT location, COUNT(*) as count 
            FROM scraped_data 
            WHERE location IS NOT NULL
            GROUP BY location 
            ORDER BY count DESC
            LIMIT 10
        """)
        by_location = [{"location": row[0], "count": row[1]} for row in db.execute(by_location_query)]
        
        return {
            "total_signals": total,
            "by_source": by_source,
            "top_locations": by_location
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
