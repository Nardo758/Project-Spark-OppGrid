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
            {"name": "all", "schedule": "Every 6 hours via external cron", "endpoint": "/api/v1/admin/scheduler/trigger/all"},
        ],
    }
