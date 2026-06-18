"""
Hub Table Population Script

Populates the 4 empty Hub tables from existing platform data:
- HubOpportunityEnriched (from 334 opportunities)
- HubMarketByGeography (aggregated from opportunities by city + scrape jobs)
- HubIndustryInsight (from opportunities by category + scrape job keyword groups)
- HubMarketSignal (from detected_trends + GoogleScrapeJob)

Usage on Replit:
    cd backend
    python scripts/populate_hub_tables.py

This script can run WITHOUT SerpAPI or Apify keys.
"""
import os
import sys
import uuid
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_db
from sqlalchemy import func, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def populate_hub_opportunities_enriched(db: Session):
    """Map 334 existing opportunities into HubOpportunityEnriched."""
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
    now = datetime.utcnow()
    for opp in opportunities:
        try:
            market_size = _parse_market_size(opp.market_size)
            startup_cost = _estimate_startup_cost(opp.category)
            monthly_revenue = _estimate_monthly_revenue(market_size)
            roi = _estimate_roi(market_size, startup_cost)
            break_even = _estimate_break_even(startup_cost, monthly_revenue)
            ai_score = opp.ai_opportunity_score or 50

            enriched = HubOpportunityEnriched(
                opportunity_id=opp.id,
                title=opp.title or 'Untitled',
                description=opp.description or '',
                category=opp.category or 'general',
                subcategory=opp.subcategory,
                source_platform=opp.source_platform or 'craigslist',
                city=opp.city,
                state=opp.state,
                region=opp.region,
                latitude=opp.latitude,
                longitude=opp.longitude,
                ai_opportunity_score=ai_score,
                market_tier=_market_tier_from_score(ai_score),
                trend_momentum=opp.growth_rate or 0.0,
                competition_density=opp.ai_competition_level or 'moderate',
                difficulty_score=opp.feasibility_score or 50,
                market_readiness_score=opp.feasibility_score or 50,
                estimated_market_size_usd=market_size,
                target_market_size_usd=int(market_size * 0.5),
                tam_saw_som={
                    'tam': market_size,
                    'sam': int(market_size * 0.3),
                    'som': int(market_size * 0.05)
                },
                growth_rate_percent=opp.growth_rate or 0.0,
                time_to_profitability_months=break_even,
                direct_competitors_count=0,
                indirect_competitors_count=0,
                key_competitors=[],
                competitive_advantages=[],
                barriers_to_entry=[],
                estimated_startup_cost_usd=startup_cost,
                estimated_monthly_costs_usd=int(startup_cost * 0.02),
                estimated_monthly_revenue_usd=monthly_revenue,
                roi_estimate_percent=roi,
                break_even_months=break_even,
                technical_difficulty='medium',
                regulatory_risk='low',
                market_risk='medium',
                key_risks=[],
                critical_success_factors=[],
                project_overview={},
                technical_feasibility={},
                market_feasibility={},
                financial_feasibility={},
                operational_feasibility={},
                legal_regulatory={},
                case_study_example={},
                success_patterns=[],
                failure_patterns=[],
                expert_perspective='',
                aggregated_at=now,
                last_updated_at=now,
                data_freshness='backfilled',
                confidence_score=70.0,
            )
            db.add(enriched)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to enrich opportunity {opp.id}: {e}")

    db.commit()
    logger.info(f"Created {created} HubOpportunityEnriched records from {len(opportunities)} opportunities")
    return created


def populate_hub_markets_by_geography(db: Session):
    """Aggregate opportunities by city + GoogleScrapeJob locations."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubMarketByGeography
    from app.models.google_scraping import GoogleScrapeJob, LocationCatalog

    count = db.query(HubMarketByGeography).count()
    if count > 0:
        logger.info(f"HubMarketByGeography already has {count} rows. Skipping.")
        return 0

    now = datetime.utcnow()
    created = 0
    seen_ids = set()

    # 1. From opportunities by city
    cities = db.query(
        Opportunity.city,
        Opportunity.state,
        func.count(Opportunity.id).label('total'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score')
    ).filter(
        Opportunity.city.isnot(None),
        Opportunity.moderation_status == 'approved'
    ).group_by(Opportunity.city, Opportunity.state).all()

    for city, state, total, avg_score in cities:
        try:
            if city in seen_ids:
                continue
            seen_ids.add(city)
            market = HubMarketByGeography(
                city=city,
                state=state or 'Unknown',
                country='USA',
                total_opportunities=total or 0,
                categories=_get_categories_for_city(db, city),
                avg_opportunity_score=round(avg_score or 0, 2),
                hot_categories=[],
                total_businesses=0,
                active_businesses=0,
                avg_business_rating=0.0,
                business_categories=[],
                competitor_analysis={},
                median_startup_cost_usd=0,
                avg_monthly_revenue_usd=0,
                median_roi_percent=0.0,
                cost_of_living_index=0.0,
                commercial_rent_sqft_month=0.0,
                population=0,
                population_growth_percent=0.0,
                median_age=0,
                median_household_income=0,
                education_level_percent={},
                employment_rate_percent=0.0,
                industry_breakdown={},
                growth_trajectory='stable',
                emerging_trends=[],
                seasonal_patterns=[],
                new_opportunities_30d=total or 0,
                new_opportunities_90d=total or 0,
                monthly_opportunity_velocity=0.0,
                search_interest=0.0,
                social_mentions=0,
                news_mentions=0,
                aggregated_at=now,
                last_updated_at=now,
            )
            db.add(market)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create market for {city}: {e}")

    # 2. From GoogleScrapeJob locations (boost count)
    locations = db.query(LocationCatalog).filter(LocationCatalog.is_active == True).all()
    for loc in locations:
        try:
            if loc.name in seen_ids:
                continue
            seen_ids.add(loc.name)
            job_count = db.query(func.count(GoogleScrapeJob.id)).filter(
                GoogleScrapeJob.location_id == loc.id
            ).scalar() or 0
            market = HubMarketByGeography(
                city=loc.name,
                state='Unknown',
                country='USA',
                total_opportunities=job_count,
                categories=[],
                avg_opportunity_score=50.0,
                hot_categories=[],
                total_businesses=0,
                active_businesses=0,
                avg_business_rating=0.0,
                business_categories=[],
                competitor_analysis={},
                median_startup_cost_usd=0,
                avg_monthly_revenue_usd=0,
                median_roi_percent=0.0,
                cost_of_living_index=0.0,
                commercial_rent_sqft_month=0.0,
                population=loc.population or 0,
                population_growth_percent=0.0,
                median_age=0,
                median_household_income=0,
                education_level_percent={},
                employment_rate_percent=0.0,
                industry_breakdown={},
                growth_trajectory='stable',
                emerging_trends=[],
                seasonal_patterns=[],
                new_opportunities_30d=job_count,
                new_opportunities_90d=job_count,
                monthly_opportunity_velocity=0.0,
                search_interest=0.0,
                social_mentions=0,
                news_mentions=0,
                aggregated_at=now,
                last_updated_at=now,
            )
            db.add(market)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create market for location {loc.name}: {e}")

    db.commit()
    logger.info(f"Created {created} HubMarketByGeography records")
    return created


def populate_hub_industry_insights(db: Session):
    """Create industry insights from opportunities + GoogleScrapeJob keyword groups."""
    from app.models.opportunity import Opportunity
    from app.models.data_hub import HubIndustryInsight
    from app.models.google_scraping import GoogleScrapeJob, KeywordGroup

    count = db.query(HubIndustryInsight).count()
    if count > 0:
        logger.info(f"HubIndustryInsight already has {count} rows. Skipping.")
        return 0

    now = datetime.utcnow()
    created = 0
    seen_names = set()

    # 1. From opportunity categories
    verticals = db.query(
        Opportunity.category,
        func.count(Opportunity.id).label('total'),
        func.avg(Opportunity.ai_opportunity_score).label('avg_score')
    ).filter(
        Opportunity.category.isnot(None),
        Opportunity.moderation_status == 'approved'
    ).group_by(Opportunity.category).all()

    for category, total, avg_score in verticals:
        try:
            name = category.title()
            if name in seen_names:
                continue
            seen_names.add(name)
            startup_cost = _estimate_startup_cost(category)
            insight = HubIndustryInsight(
                industry_name=name,
                industry_code=_guess_naics(category),
                parent_industry='',
                global_market_size_usd=0,
                usa_market_size_usd=0,
                market_growth_rate_percent=_estimate_growth_rate(category),
                market_maturity=_market_maturity_from_total(total),
                growth_drivers=[],
                headwinds=[],
                emerging_trends=[],
                market_concentration='fragmented',
                typical_competitors_count=total or 0,
                barrier_to_entry='medium',
                switching_costs='medium',
                avg_startup_cost_usd=startup_cost,
                median_year_1_revenue_usd=0,
                median_gross_margin_percent=0.0,
                median_roi_percent=round(avg_score or 50, 2),
                time_to_profitability_months=_estimate_break_even(startup_cost, _estimate_monthly_revenue(500000)),
                critical_success_factors=[],
                common_pitfalls=[],
                skill_requirements=[],
                regulatory_complexity='low',
                required_licenses=[],
                compliance_requirements=[],
                top_players=[],
                disruption_threats=[],
                opportunities=[],
                avg_employee_salary_usd=0,
                skill_shortage_areas=[],
                typical_customer_profile={},
                customer_acquisition_cost_usd=0,
                customer_lifetime_value_usd=0,
                average_contract_value_usd=0,
                data_sources=[{'source': 'Opportunity table', 'count': total}],
                last_update=now,
                confidence_score=70.0,
            )
            db.add(insight)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create insight for {category}: {e}")

    # 2. From GoogleScrapeJob keyword groups
    keyword_groups = db.query(KeywordGroup).filter(KeywordGroup.is_active == True).all()
    for kg in keyword_groups:
        try:
            name = (kg.category or kg.name).title()
            if name in seen_names:
                continue
            seen_names.add(name)
            job_count = db.query(func.count(GoogleScrapeJob.id)).filter(
                GoogleScrapeJob.keyword_group_id == kg.id
            ).scalar() or 0
            insight = HubIndustryInsight(
                industry_name=name,
                industry_code=_guess_naics(kg.category or kg.name),
                parent_industry='',
                global_market_size_usd=0,
                usa_market_size_usd=0,
                market_growth_rate_percent=_estimate_growth_rate(kg.category or kg.name),
                market_maturity='growing',
                growth_drivers=[],
                headwinds=[],
                emerging_trends=[],
                market_concentration='fragmented',
                typical_competitors_count=job_count,
                barrier_to_entry='medium',
                switching_costs='medium',
                avg_startup_cost_usd=_estimate_startup_cost(kg.category or kg.name),
                median_year_1_revenue_usd=0,
                median_gross_margin_percent=0.0,
                median_roi_percent=50.0,
                time_to_profitability_months=12,
                critical_success_factors=[],
                common_pitfalls=[],
                skill_requirements=[],
                regulatory_complexity='low',
                required_licenses=[],
                compliance_requirements=[],
                top_players=[],
                disruption_threats=[],
                opportunities=[],
                avg_employee_salary_usd=0,
                skill_shortage_areas=[],
                typical_customer_profile={},
                customer_acquisition_cost_usd=0,
                customer_lifetime_value_usd=0,
                average_contract_value_usd=0,
                data_sources=[{'source': 'GoogleScrapeJob keyword group', 'count': job_count}],
                last_update=now,
                confidence_score=65.0,
            )
            db.add(insight)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create insight for keyword group {kg.name}: {e}")

    db.commit()
    logger.info(f"Created {created} HubIndustryInsight records")
    return created


def populate_hub_market_signals(db: Session):
    """Create market signals from detected_trends + GoogleScrapeJob."""
    from app.models.detected_trend import DetectedTrend
    from app.models.data_hub import HubMarketSignal
    from app.models.google_scraping import GoogleScrapeJob, LocationCatalog, KeywordGroup

    count = db.query(HubMarketSignal).count()
    if count > 0:
        logger.info(f"HubMarketSignal already has {count} rows. Skipping.")
        return 0

    now = datetime.utcnow()
    created = 0

    # 1. From DetectedTrend
    trends = db.query(DetectedTrend).all()
    for trend in trends:
        try:
            signal = HubMarketSignal(
                signal_type=trend.source_type or 'detected_trend',
                signal_name=trend.trend_name or 'Unknown',
                category=trend.category or 'general',
                signal_date=now.date(),
                signal_strength=trend.trend_strength or 50.0,
                trend_direction='growing' if (trend.growth_rate or 0) > 1.0 else 'stable',
                momentum=trend.growth_rate or 0.0,
                applies_globally=False,
                primary_regions=[],
                industries_affected=[trend.category] if trend.category else [],
                opportunities_enabled=[],
                opportunities_threatened=[],
                data_source='DetectedTrend table',
                confidence_level='medium',
                supporting_evidence=[],
                interpretation='',
                strategic_implications='',
                discovered_at=now,
                projected_duration_months=6,
            )
            db.add(signal)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create signal from trend {trend.id}: {e}")

    # 2. From GoogleScrapeJob
    jobs = db.query(GoogleScrapeJob).all()
    for job in jobs:
        try:
            loc_name = 'Unknown'
            if job.location_id:
                loc = db.query(LocationCatalog).filter(LocationCatalog.id == job.location_id).first()
                if loc:
                    loc_name = loc.name
            vertical = 'general'
            if job.keyword_group_id:
                kg = db.query(KeywordGroup).filter(KeywordGroup.id == job.keyword_group_id).first()
                if kg and kg.category:
                    vertical = kg.category

            signal = HubMarketSignal(
                signal_type=job.source_type or 'scrape_job',
                signal_name=job.name or 'Unknown',
                category=vertical,
                signal_date=now.date(),
                signal_strength=min(100.0, max(10.0, (job.opportunities_found or 0) * 5.0 + 50.0)),
                trend_direction='growing' if (job.opportunities_found or 0) > 10 else 'stable',
                momentum=0.0,
                applies_globally=False,
                primary_regions=[loc_name] if loc_name != 'Unknown' else [],
                industries_affected=[vertical],
                opportunities_enabled=[],
                opportunities_threatened=[],
                data_source='GoogleScrapeJob table',
                confidence_level='medium' if job.status == 'completed' else 'low',
                supporting_evidence=[],
                interpretation='',
                strategic_implications='',
                discovered_at=job.created_at or now,
                projected_duration_months=3,
            )
            db.add(signal)
            created += 1
        except Exception as e:
            logger.warning(f"Failed to create signal from job {job.id}: {e}")

    db.commit()
    logger.info(f"Created {created} HubMarketSignal records from {len(trends)} trends + {len(jobs)} jobs")
    return created


# ---- Helpers ----

def _parse_market_size(market_size_str):
    if not market_size_str:
        return 500000
    import re
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
    return defaults.get(category.lower().strip(), 50000)


def _estimate_monthly_revenue(market_size_usd):
    return int(market_size_usd * 0.05 / 12)


def _estimate_roi(market_size_usd, startup_cost):
    if startup_cost <= 0:
        return 25.0
    annual_revenue = market_size_usd * 0.05
    return round((annual_revenue / startup_cost) * 100, 1)


def _estimate_break_even(startup_cost, monthly_revenue):
    if monthly_revenue <= 0:
        return 24
    return max(3, int(startup_cost / monthly_revenue))


def _market_tier_from_score(score):
    if score is None:
        return 'unknown'
    if score >= 85:
        return 'tier_1'
    elif score >= 70:
        return 'tier_2'
    elif score >= 55:
        return 'tier_3'
    return 'tier_4'


def _market_maturity_from_total(total):
    if total is None:
        return 'unknown'
    if total > 50:
        return 'mature'
    elif total > 20:
        return 'growing'
    elif total > 10:
        return 'emerging'
    return 'nascent'


def _get_categories_for_city(db, city):
    from app.models.opportunity import Opportunity
    categories = db.query(Opportunity.category).filter(
        Opportunity.city == city,
        Opportunity.category.isnot(None)
    ).distinct().limit(10).all()
    return [c[0] for c in categories if c[0]]


def _guess_naics(category):
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
    high_growth = ['ecommerce', 'saas', 'mental_health', 'therapy', 'yoga_studio', 'coworking']
    if category and category.lower() in high_growth:
        return 8.5
    return 4.2


# ---- Main ----

def main():
    print("=" * 70)
    print("  OppGrid Hub Table Population Script")
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
        print("  3. Re-run python scraper_diagnostic.py")
        print("  4. When all checks are green, re-enable the marketplace")

    finally:
        db.close()


if __name__ == "__main__":
    main()
