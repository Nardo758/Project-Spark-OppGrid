"""
Seed dataset catalog — V2: parent-level only (no duplicate cities)
Creates 14 city datasets + 3 national datasets from Hub tables.
Idempotent: skips if exists.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.data_hub import HubOpportunityEnriched, HubMarketByGeography, HubIndustryInsight, HubMarketSignal
from app.models.google_scraping import LocationCatalog, GoogleScrapeJob, KeywordGroup
from sqlalchemy import func, or_
import uuid
from datetime import datetime

db = next(get_db())

print("=" * 60)
print("Dataset Catalog Seeder v2 (parent-level only)")
print("=" * 60)

# ── Check available data ───────────────────────────────────────
opp_count = db.query(HubOpportunityEnriched).count()
geo_count = db.query(HubMarketByGeography).count()
insight_count = db.query(HubIndustryInsight).count()
scrape_count = db.query(GoogleScrapeJob).count()
loc_count = db.query(LocationCatalog).filter(LocationCatalog.parent_location_id.is_(None)).count()

print(f"Hub tables: {opp_count} opp, {geo_count} geo, {insight_count} industry, {scrape_count} scrape, {loc_count} parent locs")

if not all([opp_count, geo_count, insight_count, scrape_count]):
    print("ERROR: Hub tables not populated. Run populate_hub_tables.py first.")
    sys.exit(1)

# ── Helpers ──────────────────────────────────────────────────────
TIER = {0: 29, 1: 49, 2: 79}
NATIONAL_TIER = {0: 79, 1: 99}

def existing(name):
    return db.query(Dataset).filter(Dataset.name == name).first()

def create_dataset(name, record_count, data_sources, scope_type, city, state, category):
    if existing(name):
        print(f"  SKIP (exists): {name}")
        return None
    price = TIER.get(2 if record_count > 50 else 1 if record_count > 10 else 0)
    ds = Dataset(
        id=str(uuid.uuid4()),
        name=name,
        description=f"Market research dataset for {scope_type} — {record_count} records",
        category=category,
        price_cents=price * 100,
        record_count=record_count,
        data_sources=data_sources,
        scope_type=scope_type,
        city=city,
        state=state,
        quality_score=0.8,
        created_at=datetime.utcnow(),
    )
    db.add(ds)
    db.commit()
    print(f"  CREATED: {name} — {record_count} records, ${price}")
    return ds

# ── City datasets (parent-level only) ────────────────────────────
print("\n--- CITY DATASETS (parent locations only) ---")
parent_locs = (
    db.query(LocationCatalog)
    .filter(LocationCatalog.parent_location_id.is_(None))
    .all()
)

for loc in parent_locs:
    # Count GoogleScrapeJob via location_id (no city column on the model)
    job_count = (
        db.query(func.count(GoogleScrapeJob.id))
        .filter(GoogleScrapeJob.location_id == loc.id)
        .scalar()
    )
    rec_count = job_count or 0
    if not rec_count:
        rec_count = (
            db.query(HubOpportunityEnriched)
            .filter(
                HubOpportunityEnriched.city == loc.city,
                HubOpportunityEnriched.state == loc.state,
            )
            .count()
        )
    if not rec_count:
        continue

    create_dataset(
        name=f"{loc.city}, {loc.state} Business Opportunities",
        record_count=rec_count,
        data_sources=["HubOpportunityEnriched", "GoogleScrapeJob"],
        scope_type="city",
        city=loc.city,
        state=loc.state,
        category="Business Opportunities",
    )

# ── National datasets ────────────────────────────────────────────
print("\n--- NATIONAL DATASETS ---")

for category in ["B2B Services", "Healthcare", "Technology"]:
    # Count via KeywordGroup join (GoogleScrapeJob has no category column)
    kg = db.query(KeywordGroup).filter(KeywordGroup.category == category).first()
    job_count = 0
    if kg:
        job_count = (
            db.query(func.count(GoogleScrapeJob.id))
            .filter(GoogleScrapeJob.keyword_group_id == kg.id)
            .scalar()
        )
    rec_count = job_count or 0
    if not rec_count:
        rec_count = (
            db.query(HubOpportunityEnriched)
            .filter(HubOpportunityEnriched.category == category)
            .count()
        )
    if not rec_count:
        continue

    create_dataset(
        name=f"National {category} Opportunities",
        record_count=rec_count,
        data_sources=["HubOpportunityEnriched", "HubIndustryInsight"],
        scope_type="national",
        city=None,
        state=None,
        category=category,
    )

# ── Summary ──────────────────────────────────────────────────────
all_datasets = db.query(Dataset).all()
print(f"\n{'=' * 60}")
print(f"DATASET CATALOG: {len(all_datasets)} datasets")
print(f"{'=' * 60}")
for ds in all_datasets:
    city_str = f"{ds.city}, {ds.state}" if ds.city else "National"
    print(f"  {city_str} — {ds.name} — {ds.record_count} records — ${ds.price_cents / 100:.2f}")

db.close()
print(f"{'=' * 60}")
print("Catalog complete.")
