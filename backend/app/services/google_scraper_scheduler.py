"""
Google Scraper Daily Scheduler
Runs Google scraper jobs daily at 2 AM UTC for top 20 US cities
Monitors scraper health and logs results
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.google_scraping import LocationCatalog, KeywordGroup, GoogleScrapeJob
from app.services.google_scraping_service import GoogleScrapingService

logger = logging.getLogger(__name__)

# Top 20 US markets for daily scraping
TOP_20_MARKETS = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Austin, TX",
    "Miami, FL",
    "Denver, CO",
    "San Francisco, CA",
    "Boston, MA",
    "Seattle, WA",
    "Portland, OR",
    "Nashville, TN",
    "Phoenix, AZ",
    "Atlanta, GA",
    "Dallas, TX",
    "Houston, TX",
    "Portland, ME",
    "Bend, OR",
    "Boise, ID",
    "Salt Lake City, UT",
    "Philadelphia, PA",
]

# Default pain-point keywords
DEFAULT_SCRAPE_KEYWORDS = [
    "best pizza restaurants",
    "top gyms",
    "coworking spaces",
    "best coffee shops",
    "yoga studios",
    "pet-friendly businesses",
    "nightlife venues",
    "fine dining",
    "startup offices",
    "boutique fitness",
]


class GoogleScraperScheduler:
    """Manages daily Google Scraper execution with APScheduler"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.job_id = "google_scraper_daily"
        self.scrape_results = {}
        self.last_scrape_timestamp = None
        self.consecutive_failures = 0
        self.setup_daily_job()

    def setup_daily_job(self):
        """Setup the daily Google scraper job at 2 AM UTC"""
        try:
            # Remove existing job if any
            if self.scheduler.get_job(self.job_id):
                self.scheduler.remove_job(self.job_id)

            # Schedule for 2 AM UTC daily
            self.scheduler.add_job(
                self.run_daily_scrape,
                CronTrigger(hour=2, minute=0, timezone="UTC"),
                id=self.job_id,
                name="Daily Google Scraper",
                misfire_grace_time=600,  # 10 minute grace period
                replace_existing=True,
            )
            logger.info(f"✓ Google Scraper scheduled for 2 AM UTC daily")
        except Exception as e:
            logger.error(f"✗ Failed to setup daily job: {e}")

    def run_daily_scrape(self):
        """Execute daily scrape for all top 20 markets"""
        db = SessionLocal()
        try:
            logger.info("=" * 60)
            logger.info(f"GOOGLE SCRAPER DAILY SYNC - {datetime.utcnow()}")
            logger.info("=" * 60)

            service = GoogleScrapingService(db)
            self.last_scrape_timestamp = datetime.utcnow()
            scrape_stats = {
                "started_at": self.last_scrape_timestamp,
                "markets": {},
                "total_businesses_found": 0,
                "total_signals_written": 0,
                "failed_markets": [],
                "errors": {},
            }

            # Get or seed keyword group for daily scraping
            keyword_group = self._get_or_create_daily_keywords(db, service)

            # Scrape each market
            for market_name in TOP_20_MARKETS:
                try:
                    logger.info(f"Scraping {market_name}...")
                    location = self._get_or_create_location(db, service, market_name)

                    if not location:
                        logger.warning(f"Could not create location for {market_name}")
                        scrape_stats["failed_markets"].append(market_name)
                        continue

                    # Create and run scrape job
                    job_data = {
                        "name": f"Daily Scrape - {market_name}",
                        "location_id": location.id,
                        "keyword_group_id": keyword_group.id if keyword_group else None,
                        "source_type": "google_maps_reviews",
                        "depth": 50,
                        "radius_km": 15,
                        "language": "en-US",
                        "sort_by": "relevance",
                    }

                    job = service.create_job(job_data, user_id=None)

                    # Run the job
                    result = service.run_job(job.id)

                    if result.get("success"):
                        businesses = result.get("total_found", 0)
                        signals = result.get("signals_written", 0)
                        scrape_stats["markets"][market_name] = {
                            "status": "completed",
                            "businesses_found": businesses,
                            "signals_written": signals,
                            "job_id": job.id,
                        }
                        scrape_stats["total_businesses_found"] += businesses
                        scrape_stats["total_signals_written"] += signals
                        logger.info(f"  ✓ {market_name}: {businesses} businesses, {signals} signals")
                        self.consecutive_failures = 0
                    else:
                        error = result.get("error", "Unknown error")
                        scrape_stats["markets"][market_name] = {
                            "status": "failed",
                            "error": error,
                            "job_id": job.id,
                        }
                        scrape_stats["failed_markets"].append(market_name)
                        scrape_stats["errors"][market_name] = error
                        logger.error(f"  ✗ {market_name}: {error}")

                except Exception as e:
                    logger.error(f"  ✗ {market_name}: {str(e)}")
                    scrape_stats["failed_markets"].append(market_name)
                    scrape_stats["errors"][market_name] = str(e)
                    self.consecutive_failures += 1

            # Check for alert condition (2+ days of failures)
            if len(scrape_stats["failed_markets"]) >= len(TOP_20_MARKETS) * 0.5:  # >50% failure
                self.consecutive_failures += 1
                if self.consecutive_failures >= 2:
                    logger.error(
                        f"⚠️  ALERT: Google Scraper failed for {self.consecutive_failures} consecutive days! "
                        f"Failed markets: {scrape_stats['failed_markets']}"
                    )
            else:
                self.consecutive_failures = 0

            scrape_stats["completed_at"] = datetime.utcnow()
            scrape_stats["duration_seconds"] = (
                scrape_stats["completed_at"] - scrape_stats["started_at"]
            ).total_seconds()

            # Store results
            self.scrape_results = scrape_stats

            logger.info("=" * 60)
            logger.info(
                f"SCRAPE COMPLETE: {scrape_stats['total_businesses_found']} businesses, "
                f"{scrape_stats['total_signals_written']} signals, "
                f"{len(scrape_stats['failed_markets'])} failed markets"
            )
            logger.info(f"Duration: {scrape_stats['duration_seconds']:.1f} seconds")
            logger.info("=" * 60)

            return scrape_stats

        except Exception as e:
            logger.error(f"✗ Daily scrape failed: {e}", exc_info=True)
            self.consecutive_failures += 1
            if self.consecutive_failures >= 2:
                logger.error(f"⚠️  ALERT: Google Scraper failed for {self.consecutive_failures} consecutive days!")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def _get_or_create_daily_keywords(self, db: Session, service: GoogleScrapingService) -> Optional[KeywordGroup]:
        """Get or create the daily keywords group"""
        try:
            # Check if "Daily Scrape Keywords" group exists
            groups = service.get_keyword_groups(0, 100, "Daily Scrape", None)
            if groups:
                return groups[0]

            # Create new group
            group_data = {
                "name": "Daily Scrape Keywords",
                "category": "daily_discovery",
                "keywords": DEFAULT_SCRAPE_KEYWORDS,
                "description": "Daily keywords for market scraping",
                "match_type": "phrase",
            }
            group = service.create_keyword_group(group_data, user_id=None)
            return group
        except Exception as e:
            logger.warning(f"Could not get/create keyword group: {e}")
            return None

    def _get_or_create_location(self, db: Session, service: GoogleScrapingService, location_name: str) -> Optional[LocationCatalog]:
        """Get or create a location by name"""
        try:
            # Check if location exists
            locations = service.get_locations(0, 1, location_name, "city")
            if locations:
                return locations[0]

            # Create location (using seed data if available)
            location_coords = {
                "New York, NY": (40.7128, -74.0060),
                "Los Angeles, CA": (34.0522, -118.2437),
                "Chicago, IL": (41.8781, -87.6298),
                "Austin, TX": (30.2672, -97.7431),
                "Miami, FL": (25.7617, -80.1918),
                "Denver, CO": (39.7392, -104.9903),
                "San Francisco, CA": (37.7749, -122.4194),
                "Boston, MA": (42.3601, -71.0589),
                "Seattle, WA": (47.6062, -122.3321),
                "Portland, OR": (45.5152, -122.6784),
                "Nashville, TN": (36.1627, -86.7816),
                "Phoenix, AZ": (33.4484, -112.0742),
                "Atlanta, GA": (33.7490, -84.3880),
                "Dallas, TX": (32.7767, -96.7970),
                "Houston, TX": (29.7604, -95.3698),
                "Portland, ME": (43.6591, -70.2568),
                "Bend, OR": (44.0521, -121.3153),
                "Boise, ID": (43.6150, -116.2023),
                "Salt Lake City, UT": (40.7608, -111.8910),
                "Philadelphia, PA": (39.9526, -75.1652),
            }

            coords = location_coords.get(location_name, (0, 0))
            location_data = {
                "name": location_name,
                "location_type": "city",
                "latitude": coords[0],
                "longitude": coords[1],
                "radius_km": 15,
                "is_active": True,
            }

            location = service.create_location(location_data)
            return location

        except Exception as e:
            logger.warning(f"Could not get/create location {location_name}: {e}")
            return None

    def trigger_manual_scrape(self) -> Dict:
        """Manual trigger for scraping (for testing)"""
        try:
            logger.info("Manual scrape triggered via API")
            result = self.run_daily_scrape()
            return result
        except Exception as e:
            logger.error(f"Manual scrape failed: {e}")
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict:
        """Get current scheduler status and last scrape results"""
        job = self.scheduler.get_job(self.job_id)
        return {
            "scheduler_running": self.scheduler.running,
            "job_configured": job is not None,
            "job_next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "last_scrape_timestamp": self.last_scrape_timestamp.isoformat() if self.last_scrape_timestamp else None,
            "consecutive_failures": self.consecutive_failures,
            "last_scrape_results": self.scrape_results,
            "markets_count": len(TOP_20_MARKETS),
        }

    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Google Scraper Scheduler shutdown")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> GoogleScraperScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = GoogleScraperScheduler()
    return _scheduler_instance


def initialize_scheduler():
    """Initialize the scheduler on app startup"""
    try:
        scheduler = get_scheduler()
        logger.info("Google Scraper Scheduler initialized")
        return scheduler
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
        return None
