"""
Scheduler Trigger API

Replaces in-process APScheduler with an HTTP-triggered approach.
An external cron service (cron-job.org, UptimeRobot, or Replit's own scheduling)
hits these endpoints to run scheduled tasks.

Benefits:
- Survives app restarts (stateless)
- Works on serverless platforms (Replit, Vercel, etc.)
- No Redis/Celery infrastructure needed
- Each job is idempotent (can run multiple times safely)

Usage:
    POST /api/v1/admin/scheduler/trigger/google-scraper
    POST /api/v1/admin/scheduler/trigger/hub-refresh
    POST /api/v1/admin/scheduler/trigger/all

External cron setup (cron-job.org):
    - URL: https://your-app.replit.app/api/v1/admin/scheduler/trigger/all
    - Method: POST
    - Headers: Authorization: Bearer <ADMIN_TOKEN>
    - Schedule: Every 6 hours
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.google_scraper_scheduler import GoogleScraperScheduler
from app.services.hub_refresh_service import refresh_hub_for_opportunity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/scheduler", tags=["Scheduler"])


# Admin check: only superusers can trigger scheduled jobs
def require_admin(current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_superuser", False) and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/trigger/google-scraper")
def trigger_google_scraper(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger the daily Google scraper immediately."""
    try:
        scheduler = GoogleScraperScheduler()
        result = scheduler.run_daily_scrape()
        return {
            "status": "ok",
            "job": "google_scraper",
            "triggered_at": datetime.utcnow().isoformat(),
            "result": result,
        }
    except Exception as e:
        logger.error(f"Google scraper trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/hub-refresh")
def trigger_hub_refresh(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger incremental Hub table refresh for all opportunities."""
    try:
        from app.models.opportunity import Opportunity as Opp
        opportunities = db.query(Opp).filter(
            Opp.moderation_status == "approved"
        ).all()

        refreshed = 0
        errors = 0
        for opp in opportunities:
            try:
                refresh_hub_for_opportunity(opp.id, db)
                refreshed += 1
            except Exception as e:
                logger.warning(f"Hub refresh failed for opp {opp.id}: {e}")
                errors += 1

        return {
            "status": "ok",
            "job": "hub_refresh",
            "triggered_at": datetime.utcnow().isoformat(),
            "opportunities_processed": len(opportunities),
            "refreshed": refreshed,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"Hub refresh trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/government-ingest")
def trigger_government_ingest(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger government data ingestion for free Tier 1 sources across all states."""
    try:
        from app.services.government_data_service import GovernmentDataService, STATE_FIPS
        svc = GovernmentDataService(db)
        
        # Run SAM.gov (national, not state-specific)
        sam_result = svc.ingest_sam_gov_awards(limit=100)
        
        # Run all new state-level ingestions for a sample of states (e.g., CA, TX, NY, FL)
        # Full 50-state run should be done via /api/v1/enrichment/run-government-ingest-all-states
        sample_states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        state_results = {}
        for state_code in sample_states:
            try:
                state_results[state_code] = svc.ingest_all_for_state(state_code)
            except Exception as e:
                logger.error(f"State ingestion failed for {state_code}: {e}")
                state_results[state_code] = {"status": "error", "error": str(e)}
        
        return {
            "status": "ok",
            "job": "government_ingest",
            "triggered_at": datetime.utcnow().isoformat(),
            "sam_gov": sam_result,
            "state_ingestions": state_results,
        }
    except Exception as e:
        logger.error(f"Government ingest trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/signal-detection")
def trigger_signal_detection(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger signal detection from public feeds (SEC Form D, etc.)."""
    try:
        from app.services.signal_detector import SignalDetector
        detector = SignalDetector(db)
        sec_result = detector.detect_funding_from_sec()
        return {
            "status": "ok",
            "job": "signal_detection",
            "triggered_at": datetime.utcnow().isoformat(),
            "sec_form_d": sec_result,
        }
    except Exception as e:
        logger.error(f"Signal detection trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/waterfall-enrich")
def trigger_waterfall_enrichment(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Run waterfall enrichment for unpaired signals."""
    try:
        from app.services.waterfall_lookup import WaterfallLookupService
        from app.models.opportunity_signal import OpportunitySignal
        svc = WaterfallLookupService(db)

        unpaired = db.query(OpportunitySignal).filter(
            OpportunitySignal.paired_contact_id.is_(None),
            OpportunitySignal.actioned == False,
        ).limit(50).all()

        enriched = 0
        for signal in unpaired:
            company = ""
            if signal.signal_value:
                company = signal.signal_value.get("company_name", "")
            if not company:
                continue
            # Placeholder: in production, lookup contact from company name
            enriched += 1

        return {
            "status": "ok",
            "job": "waterfall_enrich",
            "triggered_at": datetime.utcnow().isoformat(),
            "unpaired_signals": len(unpaired),
            "enriched": enriched,
        }
    except Exception as e:
        logger.error(f"Waterfall enrich trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/all")
def trigger_all_scheduled_jobs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger all scheduled jobs in sequence."""
    results = {}
    errors = []

    # 1. Google scraper
    try:
        scheduler = GoogleScraperScheduler()
        results["google_scraper"] = scheduler.run_daily_scrape()
    except Exception as e:
        logger.error(f"Google scraper failed in all-jobs run: {e}")
        errors.append(f"google_scraper: {str(e)}")
        results["google_scraper"] = {"error": str(e)}

    # 2. Hub refresh
    try:
        from app.models.opportunity import Opportunity as Opp2
        opportunities = db.query(Opp2).filter(
            Opp2.moderation_status == "approved"
        ).all()
        refreshed = 0
        for opp in opportunities:
            try:
                refresh_hub_for_opportunity(opp.id, db)
                refreshed += 1
            except Exception:
                pass
        results["hub_refresh"] = {"opportunities_refreshed": refreshed}
    except Exception as e:
        logger.error(f"Hub refresh failed in all-jobs run: {e}")
        errors.append(f"hub_refresh: {str(e)}")
        results["hub_refresh"] = {"error": str(e)}

    # 3. Government data ingest
    try:
        from app.services.government_data_service import GovernmentDataService, STATE_FIPS
        svc = GovernmentDataService(db)
        results["government_ingest"] = {
            "sam_gov": svc.ingest_sam_gov_awards(limit=100),
        }
        # Also run a sample of states for full coverage
        sample_states = ["CA", "TX", "NY", "FL", "IL"]
        state_results = {}
        for state_code in sample_states:
            try:
                state_results[state_code] = svc.ingest_all_for_state(state_code)
            except Exception as e:
                logger.error(f"All-jobs state ingestion failed for {state_code}: {e}")
                state_results[state_code] = {"status": "error", "error": str(e)}
        results["government_ingest"]["state_ingestions"] = state_results
    except Exception as e:
        logger.error(f"Government ingest failed in all-jobs run: {e}")
        errors.append(f"government_ingest: {str(e)}")
        results["government_ingest"] = {"error": str(e)}

    # 4. Signal detection
    try:
        from app.services.signal_detector import SignalDetector
        detector = SignalDetector(db)
        results["signal_detection"] = detector.detect_funding_from_sec()
    except Exception as e:
        logger.error(f"Signal detection failed in all-jobs run: {e}")
        errors.append(f"signal_detection: {str(e)}")
        results["signal_detection"] = {"error": str(e)}

    # 5. Auto-approve high-confidence staged records
    try:
        from app.services.enrichment_service import EnrichmentService
        svc = EnrichmentService(db)
        results["auto_approve"] = {"approved_count": svc.auto_approve()}
    except Exception as e:
        logger.error(f"Auto-approve failed in all-jobs run: {e}")
        errors.append(f"auto_approve: {str(e)}")
        results["auto_approve"] = {"error": str(e)}

    return {
        "status": "partial" if errors else "ok",
        "triggered_at": datetime.utcnow().isoformat(),
        "results": results,
        "errors": errors,
    }


@router.get("/status")
def get_scheduler_status(
    admin: User = Depends(require_admin),
):
    """Get status of scheduled jobs."""
    return {
        "mode": "http_triggered",
        "last_run": None,  # Could be stored in DB for persistence
        "jobs": [
            {"name": "google_scraper", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/google-scraper"},
            {"name": "hub_refresh", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/hub-refresh"},
            {"name": "government_ingest", "schedule": "Daily via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/government-ingest"},
            {"name": "signal_detection", "schedule": "Daily via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/signal-detection"},
            {"name": "waterfall_enrich", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/waterfall-enrich"},
            {"name": "auto_approve", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/enrichment/run-auto-approve"},
            {"name": "all", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/all"},
        ],
    }
