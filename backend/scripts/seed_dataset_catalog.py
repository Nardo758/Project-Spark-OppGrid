"""
Seed Dataset Catalog Script

Creates marketplace Dataset definitions from HubOpportunityEnriched data.
Generates city-specific and national dataset packages priced by record count.

Usage:
    cd backend
    python scripts/seed_dataset_catalog.py

Idempotent: safe to run multiple times (skips duplicates by name).
"""
import os
import sys
import uuid
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_db
from app.models.data_hub import HubOpportunityEnriched
from app.models.dataset import Dataset
from app.models.google_scraping import LocationCatalog, GoogleScrapeJob
from sqlalchemy import func
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DATA_FRESHNESS = "Backfilled from HubOpportunityEnriched as of 2026-06-17"


def _price_cents_for_city(count: int) -> int:
    """Return price in cents for a city-specific dataset based on record count."""
    if count > 50:
        return 7900  # Premium
    if count < 10:
        return 2900  # Budget
    return 4900  # Standard


def _price_cents_for_national(count: int) -> int:
    """Return price in cents for a national dataset based on record count."""
    if count > 100:
        return 9900
    return 7900


def _vertical_display(category: str) -> str:
    """Human-friendly vertical name from a snake_case category."""
    return category.replace("_", " ").title()


def _create_dataset(
    db: Session,
    name: str,
    description: str,
    dataset_type: str,
    vertical: str,
    city: str | None,
    price_cents: int,
    record_count: int,
    query_definition: dict,
) -> Dataset | None:
    """Create a Dataset if one with the same name does not already exist."""
    existing = db.query(Dataset).filter(Dataset.name == name).first()
    if existing:
        return None

    ds = Dataset(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        dataset_type=dataset_type,
        vertical=vertical,
        city=city,
        price_cents=price_cents,
        record_count=record_count,
        data_freshness=DATA_FRESHNESS,
        generated_at=datetime.now(timezone.utc),
        created_by_user_id="system",
        is_active=True,
        query_definition=query_definition,
    )
    db.add(ds)
    return ds


def seed_city_datasets(db: Session) -> tuple[list[Dataset], list[str]]:
    """Create city-specific datasets using LocationCatalog real city names."""
    from app.models.google_scraping import LocationCatalog, GoogleScrapeJob

    # Get top-level cities from LocationCatalog (not zip codes or neighborhoods)
    cities = (
        db.query(LocationCatalog)
        .filter(
            LocationCatalog.location_type.in_(["city"]),
            LocationCatalog.is_active == True,
        )
        .order_by(LocationCatalog.name)
        .all()
    )

    created: list[Dataset] = []
    skipped: list[str] = []

    for city in cities:
        if not city.name:
            continue

        # Count GoogleScrapeJob for this city
        job_count = (
            db.query(func.count(GoogleScrapeJob.id))
            .filter(GoogleScrapeJob.location_id == city.id)
            .scalar()
            or 0
        )

        # Count opportunities in HubOpportunityEnriched for this city
        # Use approximate matching by name
        opp_count = (
            db.query(func.count(HubOpportunityEnriched.opportunity_id))
            .filter(
                HubOpportunityEnriched.city.ilike(f"%{city.name}%"),
            )
            .scalar()
            or 0
        )

        total_records = job_count + opp_count
        if total_records < 3:
            continue

        name = f"{city.name} Business Opportunities"
        description = (
            f"{total_records} curated business opportunities in {city.name} including "
            f"{job_count} Google Maps scraped records and {opp_count} AI-analyzed opportunities "
            f"with market size, startup cost, and competition data."
        )
        price = _price_cents_for_city(total_records)
        query = {
            "location_id": city.id,
            "city": city.name,
            "tables": ["google_scrape_jobs", "hub_opportunities_enriched"],
        }

        ds = _create_dataset(
            db, name, description, "opportunities", "mixed", city.name, price, total_records, query
        )
        if ds:
            created.append(ds)
        else:
            skipped.append(name)

    return created, skipped


def seed_national_datasets(db: Session, max_national: int = 3) -> tuple[list[Dataset], list[str]]:
    """Create national (all-cities) datasets for the top categories by record count."""
    categories = (
        db.query(
            HubOpportunityEnriched.category,
            func.count(HubOpportunityEnriched.opportunity_id).label("cnt"),
        )
        .group_by(HubOpportunityEnriched.category)
        .having(func.count(HubOpportunityEnriched.opportunity_id) >= 3)
        .order_by(func.count(HubOpportunityEnriched.opportunity_id).desc())
        .limit(max_national)
        .all()
    )

    created: list[Dataset] = []
    skipped: list[str] = []

    for category, cnt in categories:
        if not category:
            continue

        display = _vertical_display(category)
        name = f"National {display} Opportunities"
        description = (
            f"{cnt} curated {display} opportunities across all cities with AI opportunity scores, "
            f"estimated market size, and startup cost data."
        )
        price = _price_cents_for_national(cnt)
        query = {
            "category": category,
            "city": None,
            "table": "hub_opportunities_enriched",
        }

        ds = _create_dataset(
            db, name, description, "opportunities", category, None, price, cnt, query
        )
        if ds:
            created.append(ds)
        else:
            skipped.append(name)

    return created, skipped


def main():
    print("=" * 70)
    print("  OppGrid Dataset Catalog Seeding")
    print("=" * 70)
    print()

    db = next(get_db())
    try:
        # Check Hub data availability
        hub_count = db.query(HubOpportunityEnriched).count()
        if hub_count == 0:
            logger.warning("HubOpportunityEnriched is empty. No datasets will be created.")
            print("  HubOpportunityEnriched has 0 rows. Nothing to seed.")
            return

        logger.info(f"HubOpportunityEnriched has {hub_count} rows. Starting seeding.")

        city_created, city_skipped = seed_city_datasets(db)
        national_created, national_skipped = seed_national_datasets(db)

        db.commit()

        total_created = len(city_created) + len(national_created)
        total_skipped = len(city_skipped) + len(national_skipped)

        print(f"  City-specific datasets created : {len(city_created)}")
        print(f"  City-specific datasets skipped  : {len(city_skipped)}")
        print(f"  National datasets created      : {len(national_created)}")
        print(f"  National datasets skipped      : {len(national_skipped)}")
        print()
        print(f"  TOTAL CREATED : {total_created}")
        print(f"  TOTAL SKIPPED : {total_skipped}")
        print()

        if total_created:
            print("  Created datasets:")
            for ds in city_created + national_created:
                price_dollars = ds.price_cents / 100
                print(
                    f"    + {ds.name} ({ds.record_count} records, ${price_dollars:.0f})"
                )
            print()

        if total_skipped:
            print("  Skipped (already exist):")
            for name in city_skipped + national_skipped:
                print(f"    ~ {name}")
            print()

        print("=" * 70)
        print("  Done.")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
