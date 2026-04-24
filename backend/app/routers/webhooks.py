from fastapi import APIRouter, Request, Header, HTTPException, Depends, BackgroundTasks
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
import logging
import os

from app.db.database import get_db
from app.services.webhook_gateway import WebhookGateway, WebhookValidationError, RateLimitExceededError
from app.services.geographic_extractor import GeographicExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
apify_router = APIRouter(prefix="/webhook", tags=["apify-webhook"])


def is_webhook_dev_mode():
    """
    Check if webhook dev mode is enabled.
    Dev mode only works in development environment (not production).
    """
    dev_mode = os.getenv("WEBHOOK_DEV_MODE", "0") == "1"
    is_development = os.getenv("REPLIT_DEPLOYMENT", "") != "1"
    
    if dev_mode and not is_development:
        logger.warning("WEBHOOK_DEV_MODE is set but ignored in production environment")
        return False
    
    return dev_mode and is_development


class WebhookPayload(BaseModel):
    data: Dict[str, Any]
    scrape_id: Optional[str] = None


class BatchWebhookPayload(BaseModel):
    items: List[Dict[str, Any]]
    scrape_id: Optional[str] = None


@router.post("/{source}")
async def receive_webhook(
    source: str,
    payload: WebhookPayload,
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Receive webhook from external scrapers.
    Supports HMAC-SHA256 authentication via X-Hub-Signature-256 or X-Webhook-Signature headers.
    In development mode (WEBHOOK_DEV_MODE=1), HMAC verification can be skipped.
    Dev mode is automatically disabled in production.
    """
    gateway = WebhookGateway(db)
    
    signature = x_hub_signature_256 or x_webhook_signature
    
    body = await request.body()
    
    skip_hmac = is_webhook_dev_mode()
    
    try:
        result = await gateway.process_webhook(
            source=source,
            payload=body,
            data=payload.data,
            signature=signature,
            scrape_id=payload.scrape_id,
            skip_hmac=skip_hmac,
        )
        return result
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    except WebhookValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{source}/batch")
async def receive_batch_webhook(
    source: str,
    payload: BatchWebhookPayload,
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Receive batch webhook with multiple items from a single source.
    Useful for bulk imports from scraping jobs.
    Requires HMAC-SHA256 authentication in production.
    Dev mode is automatically disabled in production.
    """
    skip_hmac = is_webhook_dev_mode()
    
    if not skip_hmac:
        signature = x_hub_signature_256 or x_webhook_signature
        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature header")
        
        body = await request.body()
        gateway = WebhookGateway(db)
        if not gateway.verify_hmac_signature(body, signature, source):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    gateway = WebhookGateway(db)
    
    try:
        result = await gateway.process_batch(
            source=source,
            items=payload.items,
            scrape_id=payload.scrape_id,
            pre_authenticated=True,
        )
        return result
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    except WebhookValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/queue/process")
async def process_pending_sources(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Process pending scraped sources and extract geographic features.
    This is typically called by a background worker.
    """
    extractor = GeographicExtractor(db)
    result = await extractor.process_pending_sources(limit=limit)
    return result


@router.post("/opportunities/process")
async def process_opportunities(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Process pending scraped sources into opportunities using Claude AI.
    This analyzes raw data, identifies valid opportunities, and rewrites content professionally.
    """
    from app.services.opportunity_processor import get_opportunity_processor
    
    processor = get_opportunity_processor(db)
    result = await processor.process_pending_sources(limit=limit)
    return result


@router.get("/sources/pending")
async def get_pending_sources(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get list of unprocessed scraped sources"""
    gateway = WebhookGateway(db)
    sources = gateway.get_unprocessed_sources(limit=limit)
    return {
        "count": len(sources),
        "sources": [
            {
                "id": s.id,
                "source_type": s.source_type,
                "external_id": s.external_id,
                "received_at": s.received_at.isoformat() if s.received_at else None,
            }
            for s in sources
        ],
    }


@router.get("/calendar")
async def get_calendar_data(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    Get webhook run data grouped by date and source for calendar display.
    Returns counts per day per source type for the last N days.
    """
    from sqlalchemy import func, text
    from datetime import datetime, timedelta
    from app.models.scraped_source import ScrapedSource
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        func.date(ScrapedSource.received_at).label("run_date"),
        ScrapedSource.source_type,
        func.count().label("count")
    ).filter(
        ScrapedSource.received_at >= cutoff_date
    ).group_by(
        func.date(ScrapedSource.received_at),
        ScrapedSource.source_type
    ).order_by(
        func.date(ScrapedSource.received_at).desc()
    ).all()
    
    calendar_data = {}
    source_totals = {}
    
    for row in results:
        date_str = row.run_date.isoformat() if row.run_date else None
        if date_str:
            if date_str not in calendar_data:
                calendar_data[date_str] = {}
            calendar_data[date_str][row.source_type] = row.count
            source_totals[row.source_type] = source_totals.get(row.source_type, 0) + row.count
    
    total_sources = db.query(func.count()).select_from(ScrapedSource).filter(
        ScrapedSource.received_at >= cutoff_date
    ).scalar()
    
    return {
        "days": days,
        "calendar": calendar_data,
        "source_totals": source_totals,
        "total_items": total_sources or 0,
        "sources": list(source_totals.keys())
    }


async def _background_process_opportunities(limit: int = 50):
    """Background task to process newly imported scraped sources."""
    import asyncio
    import traceback
    from app.db.database import SessionLocal
    from app.services.opportunity_processor import OpportunityProcessor
    
    await asyncio.sleep(2)
    
    db = None
    try:
        db = SessionLocal()
        processor = OpportunityProcessor(db)
        
        total_processed = 0
        total_created = 0
        
        while total_processed < limit:
            batch_limit = min(20, limit - total_processed)
            result = await processor.process_pending_sources(limit=batch_limit)
            
            if result.get("processed", 0) == 0:
                break
                
            total_processed += result.get("processed", 0)
            total_created += result.get("opportunities_created", 0)
            logger.info(f"Background processing: {total_processed} processed, {total_created} created")
        
        logger.info(f"Background processing complete: {total_processed} total processed, {total_created} opportunities created")
    except Exception as e:
        logger.error(f"Background processing error: {e}\n{traceback.format_exc()}")
    finally:
        if db:
            db.close()


@apify_router.post("/apify")
async def receive_apify_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_apify_webhook_secret: Optional[str] = Header(None, alias="X-Apify-Webhook-Secret"),
):
    """
    Receive webhook from Apify when an actor run completes.
    Apify sends run metadata with dataset URL - we fetch the data and process it.
    
    Authentication: Requires X-Apify-Webhook-Secret header matching APIFY_WEBHOOK_SECRET env var.
    In dev mode (WEBHOOK_DEV_MODE=1), authentication is skipped.
    In production, APIFY_WEBHOOK_SECRET must be configured.
    """
    apify_secret = os.getenv("APIFY_WEBHOOK_SECRET", "")
    
    if not is_webhook_dev_mode():
        if not apify_secret:
            logger.error("APIFY_WEBHOOK_SECRET not configured - rejecting webhook in production")
            raise HTTPException(
                status_code=500,
                detail="Apify webhook secret not configured. This is a server configuration error."
            )
        if x_apify_webhook_secret != apify_secret:
            logger.warning("Invalid Apify webhook secret received")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        body = await request.json()
        logger.info(f"Received Apify webhook: {body.get('eventType', 'unknown')}")

        # Support both our flat payload template and the nested resource format.
        # Flat (current): {"runId": "...", "actId": "...", "datasetId": "...", "status": "..."}
        # Nested (legacy): {"resource": {"id": "...", "actId": "...", "defaultDatasetId": "..."}}
        resource = body.get("resource", {})
        dataset_id = body.get("datasetId") or resource.get("defaultDatasetId")
        actor_id = body.get("actId", "") or resource.get("actId", "")
        run_id = body.get("runId") or resource.get("id", "")

        if not dataset_id:
            logger.warning(f"No dataset ID in Apify webhook. Body: {body}")
            raise HTTPException(status_code=400, detail="No datasetId provided")

        # Guard against un-interpolated template payloads (old retries before
        # shouldInterpolateStrings was enabled). Return 400 so Apify stops retrying.
        if "{" in str(dataset_id):
            logger.warning(
                "Apify webhook payload not interpolated (legacy retry) — ignoring. "
                f"datasetId={dataset_id}"
            )
            return {"status": "ignored", "reason": "un-interpolated payload (legacy retry)"}

        # Detect source type from actor ID.
        # Check the known actor-ID map first (Apify sends internal hash IDs, not slugs).
        # Fall back to keyword matching for any actors added later.
        from app.services.apify_service import ACTOR_ID_SOURCE_TYPE_MAP
        if actor_id in ACTOR_ID_SOURCE_TYPE_MAP:
            source_type = ACTOR_ID_SOURCE_TYPE_MAP[actor_id]
        else:
            source_type = "custom"
            actor_lower = actor_id.lower()
            if "twitter" in actor_lower or "tweet" in actor_lower:
                source_type = "twitter"
            elif "reddit" in actor_lower:
                source_type = "reddit"
            elif "yelp" in actor_lower:
                source_type = "yelp"
            elif "google" in actor_lower or "maps" in actor_lower:
                source_type = "google_maps"
            elif "craigslist" in actor_lower or "classifieds" in actor_lower:
                source_type = "craigslist"

        logger.info(f"Detected source type: {source_type} from actor: {actor_id}, run: {run_id}")

        apify_token = os.getenv("APIFY_API_TOKEN", "")
        if not apify_token:
            logger.error("APIFY_API_TOKEN not configured — cannot fetch dataset items")
            raise HTTPException(
                status_code=500,
                detail="APIFY_API_TOKEN not configured. Cannot fetch dataset items."
            )

        dataset_url = (
            f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            f"?format=json&clean=true&limit=1000&token={apify_token}"
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(dataset_url)
            if response.status_code == 401:
                logger.error("Apify dataset fetch unauthorised — check APIFY_API_TOKEN")
                raise HTTPException(status_code=500, detail="Apify dataset fetch unauthorised")
            response.raise_for_status()
            items = response.json()
        
        logger.info(f"Fetched {len(items)} items from Apify dataset {dataset_id}")
        
        if not items:
            return {"status": "success", "message": "No items in dataset", "count": 0}
        
        gateway = WebhookGateway(db)
        stats = {"accepted": 0, "duplicates": 0, "errors": 0}
        
        for item in items:
            try:
                result = await gateway.process_webhook(
                    source=source_type,
                    payload=b"{}",
                    data=item,
                    signature=None,
                    scrape_id=run_id,
                    skip_hmac=True,
                )
                if result.get("status") == "accepted":
                    stats["accepted"] += 1
                elif result.get("status") == "duplicate":
                    stats["duplicates"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                stats["errors"] += 1
        
        logger.info(f"Apify import complete: {stats}")
        
        if stats["accepted"] > 0:
            background_tasks.add_task(_background_process_opportunities, limit=min(stats["accepted"], 100))
            stats["auto_processing"] = "started"
            stats["message"] = f"Processing up to {min(stats['accepted'], 100)} items in background"
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "source_type": source_type,
            **stats
        }
        
    except Exception as e:
        logger.error(f"Apify webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_pipeline_metrics(db: Session = Depends(get_db)):
    """
    Get pipeline health metrics including:
    - Opportunity processing statistics
    - Quality thresholds
    - Recent processing activity
    """
    from app.models.opportunity import Opportunity
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    total_opportunities = db.query(func.count(Opportunity.id)).scalar() or 0
    
    opportunities_24h = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= last_24h
    ).scalar() or 0
    
    opportunities_7d = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= last_7d
    ).scalar() or 0
    
    avg_score = db.query(func.avg(Opportunity.ai_opportunity_score)).filter(
        Opportunity.ai_opportunity_score.isnot(None)
    ).scalar() or 0
    
    high_quality_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.ai_opportunity_score >= 70
    ).scalar() or 0
    
    above_threshold_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.ai_opportunity_score >= 50
    ).scalar() or 0
    
    pending_moderation = db.query(func.count(Opportunity.id)).filter(
        Opportunity.moderation_status == "pending_review"
    ).scalar() or 0
    
    approved_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.moderation_status == "approved"
    ).scalar() or 0
    
    return {
        "status": "healthy",
        "timestamp": now.isoformat(),
        "quality_threshold": {
            "min_opportunity_score": 50,
            "description": "Opportunities below this score are filtered out during processing"
        },
        "totals": {
            "opportunities": total_opportunities,
            "high_quality": high_quality_count,
            "above_threshold": above_threshold_count,
        },
        "activity": {
            "opportunities_last_24h": opportunities_24h,
            "opportunities_last_7d": opportunities_7d,
        },
        "quality_metrics": {
            "average_score": round(float(avg_score), 2) if avg_score else 0,
            "high_quality_percentage": round(high_quality_count / total_opportunities * 100, 2) if total_opportunities > 0 else 0,
            "above_threshold_percentage": round(above_threshold_count / total_opportunities * 100, 2) if total_opportunities > 0 else 0,
        },
        "moderation": {
            "pending_review": pending_moderation,
            "approved": approved_count,
        }
    }
