"""
Backfill HubMarketByGeography total_businesses from GoogleScrapeJob counts.

This script updates existing HubMarketByGeography rows to set total_businesses
and total_opportunities from actual GoogleScrapeJob data, fixing the zero
values created by the original populate_hub_tables.py.

Usage on Replit:
    cd backend
    python scripts/backfill_hub_market_businesses.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_db
from app.models.data_hub import HubMarketByGeography
from app.models.google_scraping import LocationCatalog, GoogleScrapeJob
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

db = next(get_db())

print("=" * 60)
print("Backfill HubMarketByGeography total_businesses")
print("=" * 60)

# Get all parent locations
parent_locs = db.query(LocationCatalog).filter(
    LocationCatalog.parent_location_id.is_(None)
).all()

print(f"Parent locations: {len(parent_locs)}")

updated = 0
skipped = 0
for loc in parent_locs:
    # Count GoogleScrapeJob for this location
    job_count = (
        db.query(func.count(GoogleScrapeJob.id))
        .filter(GoogleScrapeJob.location_id == loc.id)
        .scalar()
    ) or 0

    if not job_count:
        skipped += 1
        continue

    # Find matching HubMarketByGeography row(s)
    # Try exact match first, then fuzzy
    market = db.query(HubMarketByGeography).filter(
        HubMarketByGeography.city == loc.name
    ).first()

    if not market:
        # Parse city name from loc.name (e.g., "Austin, TX" -> "Austin")
        city_name = loc.name.split(", ")[0] if ", " in loc.name else loc.name
        market = db.query(HubMarketByGeography).filter(
            HubMarketByGeography.city.ilike(f"%{city_name}%")
        ).first()

    if not market:
        # Try matching by city name part
        market = db.query(HubMarketByGeography).filter(
            HubMarketByGeography.city.ilike(f"%{city_name}")
        ).first()

    if market:
        market.total_businesses = job_count
        market.total_opportunities = max(market.total_opportunities or 0, job_count)
        db.add(market)
        updated += 1
        logger.info(f"Updated {loc.name}: total_businesses={job_count}, total_opportunities={market.total_opportunities}")
    else:
        logger.warning(f"No HubMarketByGeography match for {loc.name} (city_name={city_name})")
        skipped += 1

db.commit()
print(f"\n{'=' * 60}")
print(f"Updated: {updated} rows")
print(f"Skipped: {skipped} rows")
print(f"{'=' * 60}")

# Verify
print("\n--- Verification (top 10) ---")
for row in db.query(HubMarketByGeography).filter(
    HubMarketByGeography.total_businesses > 0
).order_by(HubMarketByGeography.total_businesses.desc()).limit(10).all():
    print(f"  {row.city}, {row.state} — total_businesses={row.total_businesses}, total_opportunities={row.total_opportunities}")

db.close()
print("Backfill complete.")
