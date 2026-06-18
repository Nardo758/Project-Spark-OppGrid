"""
Seed dataset catalog — V3: clean deduplication + curated national
Creates city datasets (deduplicated by normalized name) + national datasets.
Idempotent: skips if exists. Uses DISTINCT to prevent duplicates.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.data_hub import HubOpportunityEnriched, HubIndustryInsight
from app.models.google_scraping import LocationCatalog, GoogleScrapeJob, KeywordGroup
from sqlalchemy import func
import uuid
from datetime import datetime

db = next(get_db())

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

print("=" * 60)
print("Dataset Catalog Seeder v3 (deduplicated)")
print("=" * 60)

# ── Check available data ───────────────────────────────────────
opp_count = db.query(HubOpportunityEnriched).count()
scrape_count = db.query(GoogleScrapeJob).count()
loc_count = db.query(LocationCatalog).filter(LocationCatalog.parent_location_id.is_(None)).count()

print(f"Hub tables: {opp_count} opp, {scrape_count} scrape, {loc_count} parent locs")

if not all([opp_count, scrape_count]):
    print("ERROR: Hub tables not populated. Run populate_hub_tables.py first.")
    sys.exit(1)

# ── Helpers ──────────────────────────────────────────────────────
TIER = {0: 29, 1: 49, 2: 79}

def existing(name):
    return db.query(Dataset).filter(Dataset.name == name).first()

def create_dataset(name, record_count, dataset_type, vertical, city, data_freshness, query_definition):
    if existing(name):
        print(f"  SKIP (exists): {name}")
        return None
    price = TIER.get(2 if record_count > 50 else 1 if record_count > 10 else 0)
    ds = Dataset(
        id=str(uuid.uuid4()),
        name=name,
        description=f"Market research dataset — {record_count} records",
        dataset_type=dataset_type,
        vertical=vertical,
        city=city,
        price_cents=price * 100,
        record_count=record_count,
        data_freshness=data_freshness,
        created_by_user_id=SYSTEM_USER_ID,
        query_definition=query_definition,
    )
    db.add(ds)
    db.commit()
    print(f"  CREATED: {name} — {record_count} records, ${price}")
    return ds

def normalize_city(name):
    """Normalize city name to avoid duplicates like 'New York City' vs 'New York'."""
    name = name.strip()
    # Remove common suffixes
    name = name.replace(" City", "").replace(" city", "")
    # Standardize abbreviations
    replacements = {
        "NYC": "New York",
        "LA": "Los Angeles",
        "SF": "San Francisco",
    }
    for short, full in replacements.items():
        if name.startswith(short + ","):
            name = name.replace(short, full, 1)
    return name.strip()

# ── City datasets (deduplicated) ─────────────────────────────────
print("\n--- CITY DATASETS (deduplicated) ---")
parent_locs = (
    db.query(LocationCatalog)
    .filter(LocationCatalog.parent_location_id.is_(None))
    .all()
)

# Deduplicate by normalized city name, keeping the one with highest record count
city_candidates = {}
for loc in parent_locs:
    rec_count = (
        db.query(func.count(GoogleScrapeJob.id))
        .filter(GoogleScrapeJob.location_id == loc.id)
        .scalar()
    ) or 0
    if not rec_count:
        continue
    
    norm = normalize_city(loc.name)
    if norm not in city_candidates or city_candidates[norm][1] < rec_count:
        city_candidates[norm] = (loc, rec_count)

city_count = 0
for norm_name, (loc, rec_count) in city_candidates.items():
    city_count += 1
    create_dataset(
        name=f"{loc.name} Business Opportunities",
        record_count=rec_count,
        dataset_type="opportunities",
        vertical="business",
        city=loc.name,
        data_freshness=f"Hub tables + {rec_count} GoogleScrapeJob records",
        query_definition={
            "location_id": loc.id,
            "location_name": loc.name,
            "source_tables": ["HubOpportunityEnriched", "GoogleScrapeJob"],
        },
    )

# ── National datasets (top categories by record count) ─────────────
print("\n--- NATIONAL DATASETS ---")

# Get actual category counts from HubOpportunityEnriched
national_categories = (
    db.query(
        HubOpportunityEnriched.category,
        func.count(HubOpportunityEnriched.opportunity_id).label("cnt")
    )
    .group_by(HubOpportunityEnriched.category)
    .order_by(func.count(HubOpportunityEnriched.id).desc())
    .limit(5)
    .all()
)

national_count = 0
for category, cat_count in national_categories:
    # Also try KeywordGroup for additional count
    kg = db.query(KeywordGroup).filter(KeywordGroup.category == category).first()
    job_count = 0
    if kg:
        job_count = (
            db.query(func.count(GoogleScrapeJob.id))
            .filter(GoogleScrapeJob.keyword_group_id == kg.id)
            .scalar()
        ) or 0
    
    total_count = max(cat_count, job_count)
    if not total_count:
        continue

    national_count += 1
    create_dataset(
        name=f"National {category} Opportunities",
        record_count=total_count,
        dataset_type="opportunities",
        vertical=category.lower().replace(" ", "_"),
        city=None,
        data_freshness=f"Hub tables + {total_count} records",
        query_definition={
            "category": category,
            "source_tables": ["HubOpportunityEnriched", "HubIndustryInsight"],
        },
    )

# ── Summary ──────────────────────────────────────────────────────
all_datasets = db.query(Dataset).all()
print(f"\n{'=' * 60}")
print(f"DATASET CATALOG: {len(all_datasets)} datasets")
print(f"  City datasets: {city_count}")
print(f"  National datasets: {national_count}")
print(f"{'=' * 60}")
for ds in all_datasets:
    city_str = ds.city or "National"
    print(f"  {city_str} — {ds.name} — {ds.record_count} records — ${ds.price_cents / 100:.2f}")

db.close()
print(f"{'=' * 60}")
print("Catalog complete.")
