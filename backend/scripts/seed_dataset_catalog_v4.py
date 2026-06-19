"""
Dataset Catalog — v4: Strictly Curated, LocationCatalog-Only

Only creates datasets for clean parent-level cities from LocationCatalog.
Filters out ZIP codes, neighborhoods, bad names, and duplicates.
Creates ~15-20 high-quality datasets across 4 tiers.

Moat: Every dataset is a proprietary blend of 2+ sources + AI scoring.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.data_hub import (
    HubOpportunityEnriched, HubMarketByGeography,
    HubIndustryInsight, HubMarketSignal
)
from app.models.google_scraping import LocationCatalog, GoogleScrapeJob, KeywordGroup
from sqlalchemy import func
import uuid
from datetime import datetime
import re

db = next(get_db())
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

# ── Bad name filters ───────────────────────────────────────────
BAD_PATTERNS = [
    r"^\d+$", r"^\d{5}", r"Unknown", r"N/A", r"Remote",
    r"Variable", r"Not specified", r"Unspecified",
    r"^Service area", r"^Online", r"Dubai", r"Lagos", r"Dublin",
    r"Multiple", r"Bay Area to", r"Santa Cruz to",
    r"Northern California", r"^Varies", r"inferred from",
    r"^not specified", r"^not location",
]
BAD_RE = [re.compile(p, re.IGNORECASE) for p in BAD_PATTERNS]

def is_clean_city(name):
    if not name:
        return False
    for r in BAD_RE:
        if r.search(name):
            return False
    return True

def parse_city_state(name):
    """Parse 'Austin, TX' -> ('Austin', 'TX')."""
    if not name:
        return None, None
    if ", " in name:
        parts = name.split(", ")
        return parts[0], parts[1] if len(parts) > 1 else ""
    return name, ""

print("=" * 60)
print("Dataset Catalog v4 — Strictly Curated (LocationCatalog Only)")
print("=" * 60)

# ── Check data ─────────────────────────────────────────────────
opp_count = db.query(HubOpportunityEnriched).count()
geo_count = db.query(HubMarketByGeography).count()
insight_count = db.query(HubIndustryInsight).count()
signal_count = db.query(HubMarketSignal).count()
scrape_count = db.query(GoogleScrapeJob).count()

print(f"Hub tables: {opp_count} opp, {geo_count} geo, {insight_count} industry, {signal_count} signals, {scrape_count} scrape")

# ── Helpers ──────────────────────────────────────────────────────
def existing(name):
    return db.query(Dataset).filter(Dataset.name == name).first()

def create_dataset(name, record_count, dataset_type, vertical, city, data_freshness, query_definition, price_cents):
    if existing(name):
        print(f"  SKIP (exists): {name}")
        return None
    ds = Dataset(
        id=str(uuid.uuid4()),
        name=name,
        description=f"OppGrid proprietary data blend — {record_count} records",
        dataset_type=dataset_type,
        vertical=vertical,
        city=city,
        price_cents=price_cents,
        record_count=record_count,
        data_freshness=data_freshness,
        created_by_user_id=SYSTEM_USER_ID,
        query_definition=query_definition,
    )
    db.add(ds)
    db.commit()
    print(f"  CREATED: {name} — {record_count} records, ${price_cents/100:.0f}")
    return ds

# ── Get clean parent cities from LocationCatalog ─────────────────
parent_locs = (
    db.query(LocationCatalog)
    .filter(LocationCatalog.parent_location_id.is_(None))
    .all()
)

clean_cities = []
for loc in parent_locs:
    if is_clean_city(loc.name):
        clean_cities.append(loc)

print(f"\nClean parent cities: {len(clean_cities)} / {len(parent_locs)}")

# ════════════════════════════════════════════════════════════════
# TIER 1: Opportunity Signal Feed — per city
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 1: Opportunity Signal Feed ---")

tier1_count = 0
for loc in clean_cities:
    city_name, state_code = parse_city_state(loc.name)
    if not city_name:
        continue

    # Count opportunities for this city (fuzzy match: city name starts with or equals)
    opp_count_city = (
        db.query(HubOpportunityEnriched)
        .filter(
            HubOpportunityEnriched.city.ilike(f"{city_name}%"),
        )
        .count()
    )
    if not opp_count_city:
        continue

    opp_cats = db.query(HubOpportunityEnriched.category).filter(
        HubOpportunityEnriched.city.ilike(f"{city_name}%"),
    ).distinct().all()
    opp_cat_list = [c[0] for c in opp_cats if c[0]]
    
    signal_cnt = 0
    if opp_cat_list:
        signal_cnt = db.query(HubMarketSignal).filter(
            HubMarketSignal.category.in_(opp_cat_list)
        ).count()

    total = max(opp_count_city, signal_cnt)
    if total < 5:
        continue

    tier1_count += 1
    price = 4900 if total <= 20 else 9900
    create_dataset(
        name=f"Signal Feed — {loc.name}",
        record_count=total,
        dataset_type="opportunity_signals",
        vertical="multi_vertical",
        city=loc.name,
        data_freshness=f"HubOpportunityEnriched({opp_count_city}) + HubMarketSignal({signal_cnt})",
        query_definition={
            "sources": ["HubOpportunityEnriched", "HubMarketSignal"],
            "proprietary_fields": [
                "ai_opportunity_score", "market_tier", "trend_momentum",
                "competition_density", "signal_strength", "pain_intensity"
            ],
            "moat": "Cross-source signal correlation + AI scoring not available from any single competitor",
            "city": city_name, "state": state_code,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 2: 4P's Market Intelligence — per city
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 2: 4P's Market Intelligence ---")

tier2_count = 0
for loc in clean_cities:
    city_name, state_code = parse_city_state(loc.name)
    if not city_name:
        continue

    geo_count_city = (
        db.query(HubMarketByGeography)
        .filter(
            HubMarketByGeography.city.ilike(f"{city_name}%"),
        )
        .count()
    )
    if not geo_count_city:
        continue

    # Count opportunities for this city (fuzzy match: city name starts with or equals)
    opp_count_city = (
        db.query(HubOpportunityEnriched)
        .filter(
            HubOpportunityEnriched.city.ilike(f"{city_name}%"),
        )
        .count()
    )

    total = max(geo_count_city, opp_count_city)
    if total < 5:
        continue

    tier2_count += 1
    price = 9900 if total <= 20 else 14900 if total <= 50 else 19900
    create_dataset(
        name=f"4P's Market Intelligence — {loc.name}",
        record_count=total,
        dataset_type="market_intelligence",
        vertical="4ps_framework",
        city=loc.name,
        data_freshness=f"HubMarketByGeography({geo_count_city}) + HubOpportunityEnriched({opp_count_city})",
        query_definition={
            "sources": ["HubMarketByGeography", "HubIndustryInsight", "HubOpportunityEnriched"],
            "proprietary_fields": [
                "growth_score", "avg_opportunity_score", "hot_categories",
                "spending_power_index", "cost_of_living_index", "competitor_analysis"
            ],
            "moat": "Census + BLS + Google Maps + AI scoring pre-joined — no single competitor has all 4",
            "city": city_name, "state": state_code,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 3: Economic Intelligence — national, top categories only
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 3: Economic Intelligence ---")

top_categories = (
    db.query(
        HubOpportunityEnriched.category,
        func.count(HubOpportunityEnriched.opportunity_id).label("cnt")
    )
    .group_by(HubOpportunityEnriched.category)
    .order_by(func.count(HubOpportunityEnriched.opportunity_id).desc())
    .limit(5)
    .all()
)

tier3_count = 0
for category, cat_count in top_categories:
    if not category or not is_clean_city(category):
        continue

    city_count = db.query(
        func.count(func.distinct(HubOpportunityEnriched.city))
    ).filter(
        HubOpportunityEnriched.category == category
    ).scalar() or 0

    insight_count = db.query(HubIndustryInsight).filter(
        HubIndustryInsight.industry_name == category
    ).count()

    total = max(cat_count, city_count, insight_count)
    if total < 5:
        continue

    tier3_count += 1
    price = 4900 if total <= 10 else 9900 if total <= 30 else 19900
    create_dataset(
        name=f"Economic Intelligence — {category}",
        record_count=total,
        dataset_type="economic_intelligence",
        vertical=category.lower().replace(" ", "_"),
        city=None,
        data_freshness=f"HubOpportunityEnriched({cat_count}) + cities({city_count}) + HubIndustryInsight({insight_count})",
        query_definition={
            "sources": ["HubIndustryInsight", "HubMarketByGeography", "HubOpportunityEnriched"],
            "proprietary_fields": [
                "growth_drivers", "headwinds", "emerging_trends",
                "market_concentration", "barrier_to_entry", "time_to_profitability_months"
            ],
            "moat": "FRED/BLS macro data aligned with market signals + AI market entry timing — not available from any single source",
            "category": category,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 4: Competition & Location Intelligence — per city
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 4: Competition & Location Intelligence ---")

tier4_count = 0
for loc in clean_cities:
    city_name, state_code = parse_city_state(loc.name)
    if not city_name:
        continue

    geo = db.query(HubMarketByGeography).filter(
        HubMarketByGeography.city.ilike(f"{city_name}%"),
    ).first()
    
    if not geo or not geo.total_businesses:
        continue

    job_count = (
        db.query(func.count(GoogleScrapeJob.id))
        .filter(GoogleScrapeJob.location_id == loc.id)
        .scalar()
    ) or 0

    total = max(geo.total_businesses, job_count)
    if total < 5:
        continue

    tier4_count += 1
    price = 9900 if total <= 50 else 14900
    create_dataset(
        name=f"Competition Map — {loc.name}",
        record_count=total,
        dataset_type="competition_intelligence",
        vertical="location_analysis",
        city=loc.name,
        data_freshness=f"total_businesses({geo.total_businesses}) + active({geo.active_businesses or 0}) + avg_rating({geo.avg_business_rating or 0}) + GoogleScrapeJob({job_count})",
        query_definition={
            "sources": ["HubMarketByGeography", "LocationCatalog", "GoogleScrapeJob"],
            "proprietary_fields": [
                "competitor_analysis", "business_categories", "avg_business_rating",
                "competitive_advantages", "barriers_to_entry"
            ],
            "moat": "Google Maps business listings + Census demographics + AI competition gap analysis — no single competitor has all 3",
            "city": city_name, "state": state_code,
        },
        price_cents=price,
    )

# ── Summary ──────────────────────────────────────────────────────
all_datasets = db.query(Dataset).all()
print(f"\n{'=' * 60}")
print(f"DATASET CATALOG: {len(all_datasets)} datasets")
print(f"  Tier 1 (Signal Feed): {tier1_count}")
print(f"  Tier 2 (4P's Intelligence): {tier2_count}")
print(f"  Tier 3 (Economic Intelligence): {tier3_count}")
print(f"  Tier 4 (Competition Map): {tier4_count}")
print(f"{'=' * 60}")
for ds in all_datasets:
    city_str = ds.city or "National"
    print(f"  [{ds.dataset_type}] {city_str} — {ds.name} — {ds.record_count} records — ${ds.price_cents/100:.0f}")

db.close()
print(f"{'=' * 60}")
print("Catalog complete.")
