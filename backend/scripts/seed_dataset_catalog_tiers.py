"""
Dataset Catalog — 4-Tier Proprietary Data Blend

Strategy: Each dataset combines 2+ data sources + AI scoring so no single
competitor can replicate it. No dataset contains individual report depth.

Tier 1: Opportunity Signal Feed ($49-99) — raw signals + AI scoring
Tier 2: 4P's Market Intelligence ($99-199) — pre-joined multi-source data
Tier 3: Economic Intelligence ($49-199) — macro + industry + AI context
Tier 4: Competition & Location ($99-149) — Google Maps + Census + AI scoring
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.data_hub import (
    HubOpportunityEnriched, HubMarketByGeography,
    HubIndustryInsight, HubMarketSignal
)
from app.models.google_scraping import LocationCatalog
from sqlalchemy import func
import uuid
from datetime import datetime

db = next(get_db())
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

print("=" * 60)
print("Dataset Catalog — 4-Tier Proprietary Blend")
print("=" * 60)

# ── Check available data ───────────────────────────────────────
opp_count = db.query(HubOpportunityEnriched).count()
geo_count = db.query(HubMarketByGeography).count()
insight_count = db.query(HubIndustryInsight).count()
signal_count = db.query(HubMarketSignal).count()
loc_count = db.query(LocationCatalog).filter(
    LocationCatalog.parent_location_id.is_(None)
).count()

print(f"Hub tables: {opp_count} opp, {geo_count} geo, {insight_count} industry, {signal_count} signals, {loc_count} parent locs")

if not all([opp_count, geo_count, insight_count, signal_count]):
    print("WARNING: Some Hub tables empty. Proceeding with available data.")

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

# ════════════════════════════════════════════════════════════════
# TIER 1: Opportunity Signal Feed
# Moat: Cross-source signal correlation + AI scoring
# Sources: HubOpportunityEnriched + HubMarketSignal
# No single competitor has: Reddit+Craigslist+Trends+News correlated
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 1: Opportunity Signal Feed ---")

tier1_cities = db.query(
    HubOpportunityEnriched.city,
    HubOpportunityEnriched.state,
    func.count(HubOpportunityEnriched.opportunity_id).label("cnt")
).group_by(HubOpportunityEnriched.city, HubOpportunityEnriched.state).all()

tier1_count = 0
for city, state, cnt in tier1_cities:
    if not city or not state:
        continue
    # Also count signals for this city
    signal_cnt = db.query(HubMarketSignal).filter(
        HubMarketSignal.primary_regions.contains([city]) | 
        HubMarketSignal.category.in_(
            db.query(HubOpportunityEnriched.category)
            .filter(HubOpportunityEnriched.city == city)
            .distinct()
        )
    ).count()

    total = max(cnt, signal_cnt)
    if total < 5:
        continue

    tier1_count += 1
    price = 4900 if total <= 20 else 9900  # $49 or $99
    create_dataset(
        name=f"Signal Feed — {city}, {state}",
        record_count=total,
        dataset_type="opportunity_signals",
        vertical="multi_vertical",
        city=f"{city}, {state}",
        data_freshness=f"HubOpportunityEnriched({cnt}) + HubMarketSignal({signal_cnt})",
        query_definition={
            "sources": ["HubOpportunityEnriched", "HubMarketSignal"],
            "proprietary_fields": [
                "ai_opportunity_score", "market_tier", "trend_momentum",
                "competition_density", "signal_strength", "pain_intensity"
            ],
            "moat": "Cross-source signal correlation + AI scoring not available from any single competitor",
            "city": city, "state": state,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 2: 4P's Market Intelligence
# Moat: Census + BLS + Google Maps + AI scoring pre-joined
# Sources: HubMarketByGeography + HubIndustryInsight + HubOpportunityEnriched
# No single competitor has: demographics + industry + opportunity in one file
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 2: 4P's Market Intelligence ---")

tier2_cities = db.query(
    HubMarketByGeography.city,
    HubMarketByGeography.state,
    func.count(HubMarketByGeography.market_id).label("cnt")
).group_by(HubMarketByGeography.city, HubMarketByGeography.state).all()

tier2_count = 0
for city, state, cnt in tier2_cities:
    if not city or not state:
        continue
    # Count industries for this city
    opp_cats = db.query(HubOpportunityEnriched.category).filter(
        HubOpportunityEnriched.city == city,
        HubOpportunityEnriched.state == state,
    ).distinct().count()

    # Count industries with insight data
    insight_match = db.query(HubIndustryInsight).filter(
        HubIndustryInsight.opportunities.contains([city]) if hasattr(HubIndustryInsight, 'opportunities') else True
    ).count()

    total = max(cnt, opp_cats, insight_match)
    if total < 5:
        continue

    tier2_count += 1
    price = 9900 if total <= 20 else 14900 if total <= 50 else 19900  # $99, $149, $199
    create_dataset(
        name=f"4P's Market Intelligence — {city}, {state}",
        record_count=total,
        dataset_type="market_intelligence",
        vertical="4ps_framework",
        city=f"{city}, {state}",
        data_freshness=f"HubMarketByGeography({cnt}) + opp_cats({opp_cats}) + HubIndustryInsight({insight_match})",
        query_definition={
            "sources": ["HubMarketByGeography", "HubIndustryInsight", "HubOpportunityEnriched"],
            "proprietary_fields": [
                "growth_score", "avg_opportunity_score", "hot_categories",
                "spending_power_index", "cost_of_living_index", "competitor_analysis"
            ],
            "moat": "Census + BLS + Google Maps + AI scoring pre-joined — no single competitor has all 4",
            "city": city, "state": state,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 3: Economic Intelligence
# Moat: Macro + industry + AI market entry timing
# Sources: HubIndustryInsight + HubMarketByGeography (economic fields)
# No single competitor has: FRED/BLS data aligned with market signals
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 3: Economic Intelligence ---")

tier3_industries = db.query(
    HubIndustryInsight.industry_name,
    func.count(HubIndustryInsight.industry_id).label("cnt")
).group_by(HubIndustryInsight.industry_name).all()

tier3_count = 0
for industry, cnt in tier3_industries:
    if not industry:
        continue

    # Count cities with this industry
    city_count = db.query(HubOpportunityEnriched.city).filter(
        HubOpportunityEnriched.category == industry
    ).distinct().count()

    total = max(cnt, city_count)
    if total < 1:
        continue

    tier3_count += 1
    price = 4900 if total <= 10 else 9900 if total <= 30 else 19900  # $49, $99, $199
    create_dataset(
        name=f"Economic Intelligence — {industry}",
        record_count=total,
        dataset_type="economic_intelligence",
        vertical=industry.lower().replace(" ", "_"),
        city=None,  # National scope
        data_freshness=f"HubIndustryInsight({cnt}) + cities({city_count})",
        query_definition={
            "sources": ["HubIndustryInsight", "HubMarketByGeography", "HubOpportunityEnriched"],
            "proprietary_fields": [
                "growth_drivers", "headwinds", "emerging_trends",
                "market_concentration", "barrier_to_entry", "time_to_profitability_months"
            ],
            "moat": "FRED/BLS macro data aligned with market signals + AI market entry timing — not available from any single source",
            "industry": industry,
        },
        price_cents=price,
    )

# ════════════════════════════════════════════════════════════════
# TIER 4: Competition & Location Intelligence
# Moat: Google Maps + Census + AI competition scoring
# Sources: HubMarketByGeography (competition) + LocationCatalog
# No single competitor has: Google Maps listings + Census demographics + AI gap analysis
# ════════════════════════════════════════════════════════════════
print("\n--- TIER 4: Competition & Location Intelligence ---")

tier4_cities = db.query(
    HubMarketByGeography.city,
    HubMarketByGeography.state,
    HubMarketByGeography.total_businesses,
    HubMarketByGeography.active_businesses,
    HubMarketByGeography.avg_business_rating,
).all()

tier4_count = 0
for city, state, total_biz, active_biz, avg_rating in tier4_cities:
    if not city or not state:
        continue
    if not total_biz:
        continue

    tier4_count += 1
    price = 9900 if total_biz <= 50 else 14900  # $99 or $149
    create_dataset(
        name=f"Competition Map — {city}, {state}",
        record_count=total_biz,
        dataset_type="competition_intelligence",
        vertical="location_analysis",
        city=f"{city}, {state}",
        data_freshness=f"total_businesses({total_biz}), active({active_biz}), avg_rating({avg_rating})",
        query_definition={
            "sources": ["HubMarketByGeography", "LocationCatalog", "GoogleScrapeJob"],
            "proprietary_fields": [
                "competitor_analysis", "business_categories", "avg_business_rating",
                "competitive_advantages", "barriers_to_entry"
            ],
            "moat": "Google Maps business listings + Census demographics + AI competition gap analysis — no single competitor has all 3",
            "city": city, "state": state,
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
