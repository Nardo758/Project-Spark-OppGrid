"""Hub Refresh Service

Lightweight incremental updates to Hub tables when a new opportunity is created.
Called after OpportunityProcessor or SignalToOpportunityProcessor commits a new opportunity.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def refresh_hub_for_opportunity(opp_id: int, db: Session) -> dict:
    """
    Incrementally update Hub tables for a single newly-created opportunity.
    
    This is called after OpportunityProcessor or SignalToOpportunityProcessor
    creates and commits a new opportunity. It updates the relevant Hub rows
    without re-running the full populate_hub_tables.py script.
    
    Returns: {"status": "ok", "enriched": bool, "market": bool, "industry": bool, "signal": bool}
    """
    from app.models.opportunity import Opportunity
    from app.models.data_hub import (
        HubOpportunityEnriched, HubMarketByGeography,
        HubIndustryInsight, HubMarketSignal
    )
    from app.models.google_scraping import GoogleScrapeJob
    from app.models.detected_trend import DetectedTrend

    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        logger.warning(f"[HubRefresh] Opportunity {opp_id} not found, skipping")
        return {"status": "not_found", "enriched": False, "market": False, "industry": False, "signal": False}

    results = {"status": "ok", "enriched": False, "market": False, "industry": False, "signal": False}
    now = datetime.utcnow()

    # 1. HubOpportunityEnriched — create or update
    try:
        enriched = db.query(HubOpportunityEnriched).filter(
            HubOpportunityEnriched.opportunity_id == opp_id
        ).first()

        market_size = _parse_market_size(opp.market_size)
        startup_cost = _estimate_startup_cost(opp.category)
        monthly_revenue = _estimate_monthly_revenue(market_size)
        ai_score = opp.ai_opportunity_score or 50

        data = {
            "title": opp.title or "Untitled",
            "description": opp.description or "",
            "category": opp.category or "general",
            "subcategory": opp.subcategory,
            "source_platform": opp.source_platform or "craigslist",
            "city": opp.city,
            "state": opp.state,
            "region": opp.region,
            "latitude": opp.latitude,
            "longitude": opp.longitude,
            "ai_opportunity_score": ai_score,
            "market_tier": _market_tier_from_score(ai_score),
            "trend_momentum": opp.growth_rate or 0.0,
            "competition_density": opp.ai_competition_level or "moderate",
            "difficulty_score": opp.feasibility_score or 50,
            "market_readiness_score": opp.feasibility_score or 50,
            "estimated_market_size_usd": market_size,
            "target_market_size_usd": int(market_size * 0.5),
            "tam_saw_som": {
                "tam": market_size,
                "sam": int(market_size * 0.3),
                "som": int(market_size * 0.05)
            },
            "estimated_startup_cost_usd": startup_cost,
            "estimated_monthly_revenue_usd": monthly_revenue,
            "roi_estimate_percent": _estimate_roi(market_size, startup_cost),
            "break_even_months": _estimate_break_even(startup_cost, monthly_revenue),
            "confidence_score": min(1.0, max(0.0, ai_score / 100.0)),
            "data_freshness": "live",
            "last_updated_at": now,
        }

        if enriched:
            for key, value in data.items():
                setattr(enriched, key, value)
            logger.info(f"[HubRefresh] Updated HubOpportunityEnriched for opp {opp_id}")
        else:
            data["opportunity_id"] = opp_id
            data["aggregated_at"] = now
            enriched = HubOpportunityEnriched(**data)
            db.add(enriched)
            logger.info(f"[HubRefresh] Created HubOpportunityEnriched for opp {opp_id}")
        results["enriched"] = True
    except Exception as e:
        logger.warning(f"[HubRefresh] Failed to update HubOpportunityEnriched for opp {opp_id}: {e}")

    # 2. HubMarketByGeography — update city aggregate
    if opp.city:
        try:
            market = db.query(HubMarketByGeography).filter(
                HubMarketByGeography.city == opp.city,
                HubMarketByGeography.state == (opp.state or "")
            ).first()

            # Count opportunities in this city
            city_opp_count = db.query(Opportunity).filter(
                Opportunity.city == opp.city,
                Opportunity.moderation_status == "approved"
            ).count()

            # Count scrape jobs for this city
            try:
                city_scrape_count = db.query(GoogleScrapeJob).filter(
                    GoogleScrapeJob.city.ilike(f"%{opp.city}%")
                ).count()
            except Exception:
                city_scrape_count = 0

            categories = list(set(
                o.category for o in db.query(Opportunity).filter(
                    Opportunity.city == opp.city,
                    Opportunity.moderation_status == "approved",
                    Opportunity.category.isnot(None)
                ).all() if o.category
            ))

            market_data = {
                "city": opp.city,
                "state": opp.state or "Unknown",
                "country": "USA",
                "total_opportunities": city_opp_count,
                "total_businesses": city_scrape_count,
                "categories": categories,
                "avg_opportunity_score": _city_avg_score(db, opp.city),
                "growth_trajectory": _market_health_from_score(_city_avg_score(db, opp.city)),
                "last_updated_at": now,
            }

            if market:
                for key, value in market_data.items():
                    setattr(market, key, value)
                logger.info(f"[HubRefresh] Updated HubMarketByGeography for {opp.city}")
            else:
                market_data["aggregated_at"] = now
                market = HubMarketByGeography(**market_data)
                db.add(market)
                logger.info(f"[HubRefresh] Created HubMarketByGeography for {opp.city}")
            results["market"] = True
        except Exception as e:
            logger.warning(f"[HubRefresh] Failed to update HubMarketByGeography for {opp.city}: {e}")

    # 3. HubIndustryInsight — update category aggregate
    if opp.category:
        try:
            insight = db.query(HubIndustryInsight).filter(
                HubIndustryInsight.industry_name == opp.category
            ).first()

            # Count opportunities in this category
            cat_opp_count = db.query(Opportunity).filter(
                Opportunity.category == opp.category,
                Opportunity.moderation_status == "approved"
            ).count()

            # Estimate market size from opportunity data
            cat_opportunities = db.query(Opportunity).filter(
                Opportunity.category == opp.category,
                Opportunity.moderation_status == "approved"
            ).all()
            avg_market_size = sum(
                _parse_market_size(o.market_size) for o in cat_opportunities
            ) / max(len(cat_opportunities), 1)

            insight_data = {
                "industry_name": opp.category,
                "usa_market_size_usd": int(avg_market_size),
                "market_growth_rate_percent": _category_growth_rate(db, opp.category),
                "typical_competitors_count": cat_opp_count,
                "industry_code": _guess_naics(opp.category),
                "barrier_to_entry": _guess_barriers(opp.category),
                "last_update": now,
            }

            if insight:
                for key, value in insight_data.items():
                    setattr(insight, key, value)
                logger.info(f"[HubRefresh] Updated HubIndustryInsight for {opp.category}")
            else:
                insight_data["discovered_at"] = now
                insight = HubIndustryInsight(**insight_data)
                db.add(insight)
                logger.info(f"[HubRefresh] Created HubIndustryInsight for {opp.category}")
            results["industry"] = True
        except Exception as e:
            logger.warning(f"[HubRefresh] Failed to update HubIndustryInsight for {opp.category}: {e}")

    # 4. HubMarketSignal — update or create trend signal
    try:
        trend = db.query(HubMarketSignal).filter(
            HubMarketSignal.category == opp.category,
            HubMarketSignal.signal_name == f"opportunity_{opp.city}"
        ).first()

        signal_data = {
            "signal_type": "opportunity",
            "signal_name": f"opportunity_{opp.city}",
            "category": opp.category or "general",
            "signal_date": now.date(),
            "signal_strength": opp.ai_opportunity_score or 50,
            "trend_direction": "up" if (opp.growth_rate or 0) > 0 else "stable",
            "momentum": abs(opp.growth_rate or 0),
            "data_source": opp.source_platform or "unknown",
            "confidence_level": "medium",
            "discovered_at": now,
        }

        if trend:
            for key, value in signal_data.items():
                setattr(trend, key, value)
            logger.info(f"[HubRefresh] Updated HubMarketSignal for {opp.city}/{opp.category}")
        else:
            trend = HubMarketSignal(**signal_data)
            db.add(trend)
            logger.info(f"[HubRefresh] Created HubMarketSignal for {opp.city}/{opp.category}")
        results["signal"] = True
    except Exception as e:
        logger.warning(f"[HubRefresh] Failed to update HubMarketSignal for {opp.city}/{opp.category}: {e}")

    db.commit()
    return results


# --- Helper functions (mirrored from populate_hub_tables.py) ---

def _parse_market_size(val) -> int:
    if val is None:
        return 500000
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        clean = val.replace("$", "").replace(",", "").replace("M", "000000").replace("B", "000000000").replace("K", "000")
        try:
            return int(float(clean))
        except ValueError:
            return 500000
    return 500000


def _estimate_startup_cost(category: Optional[str]) -> int:
    costs = {
        "restaurant": 150000, "food_beverage": 80000, "childcare": 120000,
        "transportation": 50000, "home_services": 30000, "healthcare": 200000,
        "product_marketplace": 100000, "service_marketplace": 50000,
        "saas": 50000, "technology": 75000, "retail": 100000,
    }
    return costs.get((category or "").lower(), 75000)


def _estimate_monthly_revenue(market_size: int) -> int:
    if market_size < 100000:
        return 8000
    if market_size < 1000000:
        return 25000
    if market_size < 10000000:
        return 75000
    return 150000


def _estimate_roi(market_size: int, startup_cost: int) -> float:
    if startup_cost <= 0:
        return 0.0
    monthly = _estimate_monthly_revenue(market_size)
    annual = monthly * 12
    return round(((annual - (startup_cost * 0.2)) / startup_cost) * 100, 1)


def _estimate_break_even(startup_cost: int, monthly_revenue: int) -> int:
    if monthly_revenue <= 0:
        return 36
    monthly_profit = monthly_revenue * 0.3
    if monthly_profit <= 0:
        return 36
    months = startup_cost / monthly_profit
    return max(3, min(36, int(months)))


def _market_tier_from_score(score: int) -> str:
    if score >= 80: return "high"
    if score >= 60: return "medium"
    return "low"


def _market_health_from_score(score: float) -> str:
    if score >= 70: return "healthy"
    if score >= 50: return "moderate"
    return "stressed"


def _city_avg_score(db: Session, city: str) -> float:
    from app.models.opportunity import Opportunity
    from sqlalchemy import func
    result = db.query(func.avg(Opportunity.ai_opportunity_score)).filter(
        Opportunity.city == city,
        Opportunity.moderation_status == "approved"
    ).scalar()
    return float(result or 50.0)


def _category_growth_rate(db: Session, category: str) -> float:
    from app.models.opportunity import Opportunity
    from sqlalchemy import func
    result = db.query(func.avg(Opportunity.growth_rate)).filter(
        Opportunity.category == category,
        Opportunity.moderation_status == "approved"
    ).scalar()
    return float(result or 0.0)


def _guess_naics(category: Optional[str]) -> str:
    mapping = {
        "restaurant": "722511", "food_beverage": "722513", "childcare": "624410",
        "transportation": "485999", "home_services": "561710", "healthcare": "621111",
        "product_marketplace": "454111", "service_marketplace": "561499",
        "saas": "511210", "technology": "541511", "retail": "452319",
    }
    return mapping.get((category or "").lower(), "999999")


def _guess_barriers(category: Optional[str]) -> str:
    mapping = {
        "restaurant": "high", "food_beverage": "medium", "childcare": "high",
        "transportation": "medium", "home_services": "low", "healthcare": "very_high",
        "product_marketplace": "medium", "service_marketplace": "low",
        "saas": "low", "technology": "low", "retail": "medium",
    }
    return mapping.get((category or "").lower(), "medium")
