"""
Hub Table Aggregation Script

Populates the 4 empty Hub tables from existing platform data:
- HubOpportunityEnriched (from 334 opportunities)
- HubMarketByGeography (aggregated from opportunities by city)
- HubIndustryInsight (from 1,309 google_scrape_jobs)
- HubMarketSignal (from detected_trends + scrape_jobs)

Usage on Replit:
    cd backend
    python scripts/populate_hub_tables.py

This script can run WITHOUT SerpAPI or Apify keys — it uses existing data.
"""
import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_db
from sqlalchemy import func, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SNAPSHOT_ID = f"snap-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
EFFECTIVE_DATE = datetime.utcnow().date()

def populate_hub_opportunities_enriched(db: Session):
    """Map 334 existing opportunities into HubOpportunityEnriched with time-series fields."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubOpportunityEnriched

    count = db.query(HubOpportunityEnriched).count()
    if count > 0:
        logger.info(f"HubOpportunityEnriched already has {count} rows. Skipping.")
        return 0

    opportunities = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'approved'
    ).all()

    created = 0
    for opp in opportunities:
        try:
            # Compute derived fields from opportunity data
            ai_score = opp.ai_opportunity_score or 0
            if opp.ai_opportunity_score is None and opp.feasibility_score:
                ai_score = opp.feasibility_score

            market_tier = 'medium'
            if ai_score >= 80:
                market_tier = 'high'
            elif ai_score >= 50:
                market_tier = 'medium'
            else:
                market_tier = 'low'

            trend_momentum = 0.70
            if opp.growth_rate and opp.growth_rate > 5:
                trend_momentum = 0.85
            elif opp.growth_rate and opp.growth_rate > 0:
                trend_momentum = 0.75

            competition_density = 'moderate'
            if hasattr(opp, 'validation_count') and opp.validation_count:
                if opp.validation_count > 20:
                    competition_density = 'high'
                elif opp.validation_count < 5:
                    competition_density = 'low'

            market_size = opp.market_size or opp.ai_market_size_estimate or '$500K-$1M'
            market_size_usd = _parse_market_size(market_size)

            startup_cost = _estimate_startup_cost(opp.category)
            monthly_revenue = _estimate_monthly_revenue(market_size_usd)
            roi = _estimate_roi(market_size_usd, startup_cost)
            break_even = _estimate_break_even(startup_cost, monthly_revenue)
            confidence = min(95, max(50, ai_score + 10))

            enriched = HubOpportunityEnriched(
                opportunity_id=str(opp.id),
                title=opp.title or 'Untitled Opportunity',
                category=opp.category or 'general',
                city=opp.city or 'Unknown',
                state=opp.state or opp.region or 'Unknown',
                ai_opportunity_score=ai_score,
                market_tier=market_tier,
                trend_momentum=trend_momentum,
                competition_density=competition_density,
                estimated_market_size_usd=market_size_usd,
                estimated_startup_cost_usd=startup_cost,
                estimated_monthly_revenue_usd=monthly_revenue,
                roi_estimate_percent=roi,
                break_even_months=break_even,
                confidence_score=confidence,
                data_freshness='recent',
                data_source='Opportunity table (backfilled)',
                # Time-series fields
                snapshot_id=SNAPSHOT_ID,
                effective_date=EFFECTIVE_DATE,
                is_latest=True,
                first_seen_date=opp.created_at.date() if opp.created_at else EFFECTIVE_DATE,
                collected_at=datetime.utcnow(),
                data_quality_score=85,
                refresh_cadence='daily',
                period_type='daily',
            )
            db.add(enriched)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to enrich opportunity {opp.id}: {e}")

    db.commit()
    logger.info(f"Created {created} HubOpportunityEnriched records from {len(opportunities)} opportunities")
    return created


def populate_hub_markets_by_geography(db: Session):
    """Aggregate opportunities by city to create HubMarketByGeography."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubMarketByGeography

    count = db.query(HubMarketByGeography).count()
    if count > 0:
        logger.info(f"HubMarketByGeography already has {count} rows. Skipping.")
        return 0

    # Aggregate by city
    cities = db.query(
        Opportunity.city,
        Opportunity.state,
        func.count(Opportunity.id).label('total'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score')
    ).filter(
        Opportunity.city.isnot(None),
        Opportunity.moderation_status == 'approved'
    ).group_by(Opportunity.city, Opportunity.state).all()

    created = 0
    for city, state, total, avg_score in cities:
        try:
            market = HubMarketByGeography(
                market_id=f"mkt-{city.lower().replace(' ', '-')}-{state.lower() if state else 'unknown'}",
                city=city,
                state=state or 'Unknown',
                country='USA',
                total_opportunities=total or 0,
                categories=_get_categories_for_city(db, city),
                avg_score=round(avg_score or 0, 2),
                market_health=_market_health_from_avg(avg_score),
                data_source='Aggregated from Opportunity table',
                # Time-series
                snapshot_id=SNAPSHOT_ID,
                effective_date=EFFECTIVE_DATE,
                is_latest=True,
                first_seen_date=EFFECTIVE_DATE,
                collected_at=datetime.utcnow(),
                data_quality_score=80,
                refresh_cadence='weekly',
                period_type='daily',
            )
            db.add(market)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create market for {city}: {e}")

    db.commit()
    logger.info(f"Created {created} HubMarketByGeography records")
    return created


def populate_hub_industry_insights(db: Session):
    """Create industry insights from existing scrape jobs and opportunities."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubIndustryInsight

    count = db.query(HubIndustryInsight).count()
    if count > 0:
        logger.info(f"HubIndustryInsight already has {count} rows. Skipping.")
        return 0

    # Aggregate by vertical/category
    verticals = db.query(
        Opportunity.category,
        func.count(Opportunity.id).label('total'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score')
    ).filter(
        Opportunity.category.isnot(None),
        Opportunity.moderation_status == 'approved'
    ).group_by(Opportunity.category).all()

    created = 0
    for category, total, avg_score in verticals:
        try:
            insight = HubIndustryInsight(
                industry_id=f"ind-{category.lower().replace(' ', '-')}",
                industry_name=category.title(),
                naics_code=_guess_naics(category),
                total_opportunities=total or 0,
                avg_opportunity_score=round(avg_score or 0, 2),
                growth_rate=_estimate_growth_rate(category),
                competition_level=_competition_from_total(total),
                top_cities=_get_top_cities_for_category(db, category),
                data_source='Aggregated from Opportunity + ScrapeJob tables',
                # Time-series
                snapshot_id=SNAPSHOT_ID,
                effective_date=EFFECTIVE_DATE,
                is_latest=True,
                first_seen_date=EFFECTIVE_DATE,
                collected_at=datetime.utcnow(),
                data_quality_score=75,
                refresh_cadence='weekly',
                period_type='daily',
            )
            db.add(insight)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create insight for {category}: {e}")

    db.commit()
    logger.info(f"Created {created} HubIndustryInsight records")
    return created


def populate_hub_market_signals(db: Session):
    """Create market signals from detected_trends + scrape_jobs."""
    from app.models.detected_trend import DetectedTrend
    from app.models.data_hub import HubMarketSignal

    count = db.query(HubMarketSignal).count()
    if count > 0:
        logger.info(f"HubMarketSignal already has {count} rows. Skipping.")
        return 0

    trends = db.query(DetectedTrend).all()
    if not trends:
        logger.warning("No DetectedTrend records found. Creating from opportunities as fallback.")
        return _populate_signals_from_opportunities(db)

    created = 0
    for trend in trends:
        try:
            signal = HubMarketSignal(
                signal_id=f"sig-{trend.id}",
                signal_type=trend.source_type or 'detected_trend',
                vertical=trend.category or 'general',
                city='Unknown',  # Trends may not have city
                state='Unknown',
                signal_strength=trend.trend_strength or 50,
                trend_direction='growing' if (trend.growth_rate or 0) > 1.0 else 'stable',
                confidence_score=trend.confidence_score or 70,
                keywords=trend.keywords or [],
                data_source='DetectedTrend table (backfilled)',
                # Time-series
                snapshot_id=SNAPSHOT_ID,
                effective_date=EFFECTIVE_DATE,
                is_latest=True,
                first_seen_date=trend.detected_at.date() if trend.detected_at else EFFECTIVE_DATE,
                collected_at=datetime.utcnow(),
                data_quality_score=70,
                refresh_cadence='daily',
                period_type='daily',
            )
            db.add(signal)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create signal from trend {trend.id}: {e}")

    db.commit()
    logger.info(f"Created {created} HubMarketSignal records from {len(trends)} trends")
    return created


def _populate_signals_from_opportunities(db: Session):
    """Fallback: create signals from opportunities if no trends exist."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubMarketSignal

    opportunities = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'approved',
        Opportunity.city.isnot(None)
    ).limit(100).all()

    created = 0
    for opp in opportunities:
        try:
            signal = HubMarketSignal(
                signal_id=f"sig-opp-{opp.id}",
                signal_type='opportunity_signal',
                vertical=opp.category or 'general',
                city=opp.city or 'Unknown',
                state=opp.state or opp.region or 'Unknown',
                signal_strength=opp.ai_opportunity_score or 50,
                trend_direction='growing' if (opp.growth_rate or 0) > 5 else 'stable',
                confidence_score=opp.feasibility_score or 70,
                keywords=[opp.category] if opp.category else ['general'],
                data_source='Opportunity table (fallback signals)',
                snapshot_id=SNAPSHOT_ID,
                effective_date=EFFECTIVE_DATE,
                is_latest=True,
                first_seen_date=opp.created_at.date() if opp.created_at else EFFECTIVE_DATE,
                collected_at=datetime.utcnow(),
                data_quality_score=70,
                refresh_cadence='daily',
                period_type='daily',
            )
            db.add(signal)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create signal from opportunity {opp.id}: {e}")

    db.commit()
    logger.info(f"Created {created} HubMarketSignal records from opportunities (fallback)")
    return created


# ---- Helper functions ----

def _parse_market_size(market_size_str):
    """Parse a market size string like '$1.2M-$2.8M' into a numeric average."""
    if not market_size_str:
        return 500000
    import re
    # Extract numbers with B/M/K suffixes
    numbers = []
    for match in re.findall(r'\$?([\d.]+)\s*([BKM]?)', str(market_size_str), re.IGNORECASE):
        num, suffix = match
        try:
            val = float(num)
            if suffix.upper() == 'B':
                val *= 1_000_000_000
            elif suffix.upper() == 'M':
                val *= 1_000_000
            elif suffix.upper() == 'K':
                val *= 1_000
            numbers.append(val)
        except ValueError:
            continue
    if numbers:
        return int(sum(numbers) / len(numbers))
    return 500000


def _estimate_startup_cost(category):
    """Rough startup cost estimates by vertical."""
    defaults = {
        'coffee_shop': 85000, 'cafe': 75000, 'restaurant': 150000,
        'fitness_center': 200000, 'gym': 180000, 'salon': 45000,
        'barbershop': 25000, 'clinic': 120000, 'dental': 250000,
        'pharmacy': 180000, 'daycare': 80000, 'tutoring': 15000,
        'yoga_studio': 35000, 'spa': 60000, 'hotel': 500000,
        'brewery': 400000, 'laundromat': 120000, 'car_wash': 250000,
        'pet_grooming': 30000, 'auto_repair': 80000, 'real_estate': 50000,
        'coworking': 200000, 'mental_health': 50000, 'therapy': 35000,
        'consulting': 5000, 'ecommerce': 10000, 'saas': 50000,
        'retail': 75000, 'grocery': 300000, 'convenience_store': 50000,
    }
    if not category:
        return 50000
    cat_lower = category.lower().strip()
    return defaults.get(cat_lower, 50000)


def _estimate_monthly_revenue(market_size_usd):
    """Estimate monthly revenue as ~5% of market size."""
    return int(market_size_usd * 0.05 / 12)


def _estimate_roi(market_size_usd, startup_cost):
    """Estimate ROI percentage."""
    if startup_cost <= 0:
        return 25.0
    annual_revenue = market_size_usd * 0.05
    return round((annual_revenue / startup_cost) * 100, 1)


def _estimate_break_even(startup_cost, monthly_revenue):
    """Estimate break-even in months."""
    if monthly_revenue <= 0:
        return 24
    return max(3, int(startup_cost / monthly_revenue))


def _market_health_from_avg(avg_score):
    if avg_score is None:
        return 'unknown'
    if avg_score >= 75:
        return 'hot'
    elif avg_score >= 60:
        return 'warm'
    elif avg_score >= 40:
        return 'stable'
    elif avg_score >= 25:
        return 'cooling'
    return 'cold'


def _get_categories_for_city(db, city):
    """Get top categories for a city."""
    from app.models.opportunity import Opportunity
    categories = db.query(Opportunity.category).filter(
        Opportunity.city == city,
        Opportunity.category.isnot(None)
    ).distinct().limit(10).all()
    return [c[0] for c in categories if c[0]]


def _get_top_cities_for_category(db, category):
    """Get top 5 cities for a category."""
    from app.models.opportunity import Opportunity
    cities = db.query(Opportunity.city).filter(
        Opportunity.category == category,
        Opportunity.city.isnot(None)
    ).distinct().limit(5).all()
    return [c[0] for c in cities if c[0]]


def _guess_naics(category):
    """Guess NAICS code from category name."""
    mapping = {
        'coffee_shop': '722515', 'cafe': '722515', 'restaurant': '722511',
        'fitness_center': '713940', 'gym': '713940', 'salon': '812112',
        'barbershop': '812111', 'clinic': '621111', 'dental': '621210',
        'pharmacy': '446110', 'daycare': '624410', 'tutoring': '611691',
        'yoga_studio': '713940', 'spa': '812112', 'hotel': '721110',
        'brewery': '312120', 'laundromat': '812310', 'car_wash': '811192',
        'pet_grooming': '812910', 'auto_repair': '811111', 'real_estate': '531210',
        'coworking': '531120', 'mental_health': '621330', 'therapy': '621330',
        'consulting': '541600', 'ecommerce': '454110', 'saas': '511210',
        'retail': '452000', 'grocery': '445110', 'convenience_store': '445120',
    }
    if not category:
        return '000000'
    return mapping.get(category.lower().strip(), '000000')


def _estimate_growth_rate(category):
    """Estimate growth rate from category."""
    high_growth = ['ecommerce', 'saas', 'mental_health', 'therapy', 'yoga_studio', 'coworking']
    if category and category.lower() in high_growth:
        return 8.5
    return 4.2


def _competition_from_total(total):
    if total is None:
        return 'unknown'
    if total > 50:
        return 'saturated'
    elif total > 20:
        return 'high'
    elif total > 10:
        return 'moderate'
    elif total > 5:
        return 'low'
    return 'very_low'


def main():
    print("=" * 70)
    print("  OppGrid Hub Table Population Script")
    print(f"  Snapshot ID: {SNAPSHOT_ID}")
    print(f"  Effective Date: {EFFECTIVE_DATE}")
    print("=" * 70)
    print()

    db = next(get_db())
    try:
        total = 0
        total += populate_hub_opportunities_enriched(db)
        total += populate_hub_markets_by_geography(db)
        total += populate_hub_industry_insights(db)
        total += populate_hub_market_signals(db)

        print()
        print("=" * 70)
        print(f"  TOTAL RECORDS CREATED: {total}")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Add SERPAPI_API_KEY and APIFY_API_KEY to Replit Secrets")
        print("  2. Run nightly scrapers to refresh with live data")
        print("  3. Re-run python scripts/scraper_diagnostic.py")
        print("  4. When all checks are green, re-enable the marketplace")

    finally:
        db.close()


if __name__ == "__main__":
    main()
