"""
OppGrid Signal Sync Service

Pushes OppGrid-generated signals to JediRE for use in Strategy Builder.

Signals pushed:
- Opportunity signals (demand scores by business type)
- Growth trajectories (market growth metrics)
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.models.census_demographics import MarketGrowthTrajectory
from app.models.detected_trend import DetectedTrend
from app.services.jedire_client import get_jedire_client

logger = logging.getLogger(__name__)


# Business type mappings for signals
CATEGORY_TO_SIGNAL_TYPE = {
    "food_beverage": ["coffee_shop_demand", "restaurant_demand", "bar_demand", "bakery_demand"],
    "fitness_wellness": ["gym_demand", "yoga_demand", "spa_demand", "fitness_demand"],
    "retail": ["grocery_demand", "convenience_demand", "clothing_demand", "retail_demand"],
    "services": ["laundry_demand", "salon_demand", "barber_demand", "services_demand"],
    "entertainment": ["entertainment_demand", "nightlife_demand", "recreation_demand"],
    "health": ["pharmacy_demand", "clinic_demand", "healthcare_demand"],
    "professional": ["coworking_demand", "office_demand", "professional_demand"],
    "automotive": ["parking_demand", "auto_service_demand", "ev_charging_demand"],
    "pet": ["pet_services_demand", "vet_demand", "pet_grooming_demand"],
}


async def aggregate_opportunity_signals(db: Session, city: str, state: str) -> List[Dict[str, Any]]:
    """
    Aggregate opportunity signals for a city from OppGrid data.
    
    Returns list of signals with score, confidence, trend.
    """
    signals = []
    
    # Get opportunities for this city
    opps = db.query(Opportunity).filter(
        func.lower(Opportunity.city) == city.lower(),
        func.upper(Opportunity.region) == state.upper(),
        Opportunity.status == 'active'
    ).all()
    
    if not opps:
        logger.info(f"[SignalSync] No opportunities found for {city}, {state}")
        return signals
    
    # Aggregate by category
    category_scores: Dict[str, List[Dict]] = {}
    
    for opp in opps:
        cat = (opp.category or 'general').lower().replace(' ', '_')
        if cat not in category_scores:
            category_scores[cat] = []
        
        category_scores[cat].append({
            'score': opp.ai_opportunity_score or opp.severity * 20 or 50,
            'pain': opp.ai_pain_intensity or 5,
            'competition': opp.ai_competition_level,
            'urgency': opp.ai_urgency_level,
        })
    
    # Convert to signals
    for category, scores in category_scores.items():
        avg_score = sum(s['score'] for s in scores) / len(scores)
        avg_pain = sum(s['pain'] for s in scores) / len(scores)
        
        # Map to signal types
        signal_types = CATEGORY_TO_SIGNAL_TYPE.get(category, [f"{category}_demand"])
        
        for signal_type in signal_types[:2]:  # Limit to 2 signals per category
            # Determine trend based on count and urgency
            high_urgency = sum(1 for s in scores if s.get('urgency') in ('high', 'critical'))
            trend = 'rising' if high_urgency > len(scores) * 0.3 else 'stable'
            
            signals.append({
                'signal_type': signal_type,
                'score': round(avg_score, 1),
                'confidence': min(0.95, 0.5 + (len(scores) * 0.05)),  # Higher count = higher confidence
                'category': category,
                'trend': trend,
                'metadata': {
                    'opportunity_count': len(scores),
                    'avg_pain_intensity': round(avg_pain, 1),
                }
            })
    
    return signals


async def aggregate_growth_trajectory(db: Session, city: str, state: str) -> Optional[Dict[str, Any]]:
    """
    Aggregate growth trajectory for a city from OppGrid data.
    """
    # Try to get existing trajectory
    trajectory = db.query(MarketGrowthTrajectory).filter(
        func.lower(MarketGrowthTrajectory.city) == city.lower(),
        func.upper(MarketGrowthTrajectory.state) == state.upper(),
        MarketGrowthTrajectory.is_active == True
    ).first()
    
    if not trajectory:
        # Try to calculate from opportunities
        opp_count = db.query(func.count(Opportunity.id)).filter(
            func.lower(Opportunity.city) == city.lower(),
            func.upper(Opportunity.region) == state.upper(),
            Opportunity.status == 'active'
        ).scalar() or 0
        
        avg_score = db.query(func.avg(Opportunity.ai_opportunity_score)).filter(
            func.lower(Opportunity.city) == city.lower(),
            func.upper(Opportunity.region) == state.upper(),
            Opportunity.status == 'active',
            Opportunity.ai_opportunity_score.isnot(None)
        ).scalar()
        
        if opp_count == 0:
            return None
        
        return {
            'growth_score': None,
            'growth_category': None,
            'opportunity_signal_count': opp_count,
            'avg_opportunity_score': round(float(avg_score), 1) if avg_score else None,
        }
    
    return {
        'growth_score': float(trajectory.growth_score) if trajectory.growth_score else None,
        'growth_category': trajectory.growth_category.value if trajectory.growth_category else None,
        'population_growth_rate': float(trajectory.population_growth_rate) if trajectory.population_growth_rate else None,
        'job_growth_rate': float(trajectory.job_growth_rate) if trajectory.job_growth_rate else None,
        'income_growth_rate': float(trajectory.income_growth_rate) if trajectory.income_growth_rate else None,
        'business_formation_rate': float(trajectory.business_formation_rate) if trajectory.business_formation_rate else None,
        'net_migration_rate': float(trajectory.net_migration_rate) if trajectory.net_migration_rate else None,
        'opportunity_signal_count': trajectory.opportunity_signal_count,
        'avg_opportunity_score': float(trajectory.avg_opportunity_score) if trajectory.avg_opportunity_score else None,
        'signal_density_percentile': float(trajectory.signal_density_percentile) if trajectory.signal_density_percentile else None,
    }


async def sync_city_to_jedire(db: Session, city: str, state: str) -> Dict[str, Any]:
    """
    Sync all OppGrid signals for a city to JediRE.
    """
    result = {
        'city': city,
        'state': state,
        'signals_synced': 0,
        'trajectory_synced': False,
        'errors': []
    }
    
    client = get_jedire_client()
    
    # Sync opportunity signals
    try:
        signals = await aggregate_opportunity_signals(db, city, state)
        if signals:
            success = await client.push_opportunity_signals(city, state, signals)
            if success:
                result['signals_synced'] = len(signals)
            else:
                result['errors'].append('Failed to push opportunity signals')
    except Exception as e:
        logger.error(f"[SignalSync] Error syncing signals: {e}")
        result['errors'].append(str(e))
    
    # Sync growth trajectory
    try:
        trajectory = await aggregate_growth_trajectory(db, city, state)
        if trajectory:
            success = await client.push_growth_trajectory(city, state, trajectory)
            if success:
                result['trajectory_synced'] = True
            else:
                result['errors'].append('Failed to push growth trajectory')
    except Exception as e:
        logger.error(f"[SignalSync] Error syncing trajectory: {e}")
        result['errors'].append(str(e))
    
    return result


async def sync_all_cities_to_jedire(db: Session) -> Dict[str, Any]:
    """
    Sync all cities with OppGrid data to JediRE.
    """
    # Get unique cities with opportunities
    cities = db.query(
        Opportunity.city,
        Opportunity.region
    ).filter(
        Opportunity.city.isnot(None),
        Opportunity.region.isnot(None),
        Opportunity.status == 'active'
    ).distinct().all()
    
    results = {
        'total_cities': len(cities),
        'successful': 0,
        'failed': 0,
        'details': []
    }
    
    for city, state in cities:
        if not city or not state:
            continue
            
        result = await sync_city_to_jedire(db, city, state)
        results['details'].append(result)
        
        if result['signals_synced'] > 0 or result['trajectory_synced']:
            results['successful'] += 1
        elif result['errors']:
            results['failed'] += 1
    
    logger.info(f"[SignalSync] Synced {results['successful']}/{results['total_cities']} cities to JediRE")
    
    return results


# Convenience function for running from sync code
def sync_city_to_jedire_sync(db: Session, city: str, state: str) -> Dict[str, Any]:
    """Synchronous wrapper for sync_city_to_jedire."""
    import asyncio
    return asyncio.run(sync_city_to_jedire(db, city, state))


def sync_all_cities_to_jedire_sync(db: Session) -> Dict[str, Any]:
    """Synchronous wrapper for sync_all_cities_to_jedire."""
    import asyncio
    return asyncio.run(sync_all_cities_to_jedire(db))
