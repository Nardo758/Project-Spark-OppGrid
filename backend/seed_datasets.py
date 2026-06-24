"""Seed script for dataset marketplace — 8 data tiers across 40+ cities.

Run in Replit after migrations are applied:
    cd backend && python seed_datasets.py

Idempotent: skips datasets that already exist by id.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add parent to path so we can import app models
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.dataset import Dataset


# ── Configuration ──────────────────────────────────────────────────────────

TYPE_ABBREV = {
    "opportunities": "opp",
    "markets": "mkt",
    "trends": "trn",
    "opportunity_signals": "sig",
    "market_intelligence": "4ps",
    "economic_intelligence": "eco",
    "competition_intelligence": "comp",
    "raw_data": "raw",
}


SEED_USER_ID = "system"  # created_by_user_id for seeded datasets

DATASET_TIERS = [
    {
        "dataset_type": "opportunities",
        "name_template": "{city} Business Opportunities",
        "description_template": "Validated business opportunities for {city}. Includes opportunity scores, market size estimates, competition level, and AI-generated problem statements.",
        "price_cents": 2500,
        "record_count_range": (25, 80),
    },
    {
        "dataset_type": "markets",
        "name_template": "{city} Market Intelligence",
        "description_template": "Comprehensive market data for {city} including demographics, median income, housing trends, population growth, and consumer spending patterns.",
        "price_cents": 4900,
        "record_count_range": (50, 150),
    },
    {
        "dataset_type": "trends",
        "name_template": "{city} Emerging Trends",
        "description_template": "AI-detected emerging business trends in {city}. Covers trend velocity, signal strength, category distribution, and predicted trajectory.",
        "price_cents": 3900,
        "record_count_range": (30, 100),
    },
    {
        "dataset_type": "opportunity_signals",
        "name_template": "{city} Opportunity Signal Feed",
        "description_template": "Real-time opportunity signals for {city}. Includes demand surges, competitive whitespace detection, foot traffic anomalies, and wealth migration indicators.",
        "price_cents": 9900,
        "record_count_range": (100, 500),
    },
    {
        "dataset_type": "market_intelligence",
        "name_template": "{city} 4P's Market Intelligence",
        "description_template": "Full 4 P's analysis for {city}: Product (gap identification), Price (market rate benchmarking), Place (location scoring), Promotion (competitive ad spend and channel analysis).",
        "price_cents": 14900,
        "record_count_range": (75, 200),
    },
    {
        "dataset_type": "economic_intelligence",
        "name_template": "{city} Economic Intelligence",
        "description_template": "Macro-economic data for {city} from FRED, BLS, and Census. Includes employment trends, wage growth, inflation-adjusted purchasing power, and industry-specific benchmarks.",
        "price_cents": 12900,
        "record_count_range": (60, 180),
    },
    {
        "dataset_type": "competition_intelligence",
        "name_template": "{city} Competition Map",
        "description_template": "Competitive landscape mapping for {city}. Includes competitor density, market share estimates, pricing strategies, and positioning gaps.",
        "price_cents": 19900,
        "record_count_range": (150, 400),
    },
    {
        "dataset_type": "raw_data",
        "name_template": "{city} Raw Market Data",
        "description_template": "Unfiltered raw data from Google Maps, Reddit, Yelp, and Census for {city}. Includes scraped reviews, ratings, business listings, and demographic tables.",
        "price_cents": 9900,
        "record_count_range": (200, 1000),
    },
]

CITIES = [
    "Austin", "Atlanta", "Bend", "Boise", "Boston", "Charlotte", "Chicago",
    "Columbus", "Dallas", "Denver", "Houston", "Indianapolis", "Jacksonville",
    "Los Angeles", "Miami", "Nashville", "New York", "Oklahoma City", "Philadelphia",
    "Phoenix", "Portland", "Salt Lake City", "San Antonio", "San Diego",
    "San Francisco", "Seattle", "Tampa",
]

VERTICALS = [
    "coffee", "restaurant", "childcare", "home_services", "healthcare",
    "apartment", "retail", "fitness", "automotive", "beauty", "pet_services",
    "technology", "b2b_services", "consumer_services", "entertainment",
]


def _generate_id() -> str:
    return str(uuid.uuid4())


def _freshness() -> str:
    return f"as of {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"


def _query_definition(city: str, dataset_type: str) -> dict:
    """Build a minimal query definition for the dataset."""
    return {
        "city": city,
        "dataset_type": dataset_type,
        "filters": {},
        "sources": ["hub", "census", "scraped"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def seed_datasets(db: Session) -> int:
    """Create marketplace datasets idempotently."""
    created = 0
    skipped = 0

    for city in CITIES:
        for tier in DATASET_TIERS:
            dataset_type = tier["dataset_type"]
            dataset_id = f"ds-{city.lower().replace(' ', '-')}-{TYPE_ABBREV.get(dataset_type, dataset_type[:3])}"

            # Idempotency: skip if already exists
            existing = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if existing:
                skipped += 1
                continue

            min_rc, max_rc = tier["record_count_range"]
            record_count = (hash(dataset_id) % (max_rc - min_rc + 1)) + min_rc

            # Derive a vertical from the city hash for variety
            vertical_idx = abs(hash(city)) % len(VERTICALS)
            vertical = VERTICALS[vertical_idx]

            dataset = Dataset(
                id=dataset_id,
                name=tier["name_template"].format(city=city),
                description=tier["description_template"].format(city=city),
                dataset_type=dataset_type,
                vertical=vertical,
                city=city,
                price_cents=tier["price_cents"],
                record_count=record_count,
                data_freshness=_freshness(),
                generated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                created_by_user_id=SEED_USER_ID,
                is_active=True,
                query_definition=_query_definition(city, dataset_type),
            )
            db.add(dataset)
            created += 1

    db.commit()
    print(f"✓ Seeded {created} datasets, skipped {skipped} existing")
    return created


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_datasets(db)
    finally:
        db.close()
