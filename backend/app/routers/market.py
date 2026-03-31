"""
Market Intelligence Router - JediRe Integration

Endpoints for fetching market intelligence data from JediRe:
- Composite traffic metrics
- Market badges (Hot Market, Buy Window, etc.)
- Growth indices
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
import logging

from app.services.jedire_client import (
    get_jedire_client,
    get_composite_traffic_metrics_sync,
    get_market_badges_sync,
    get_demand_signals_sync,
    get_market_economics_sync
)

router = APIRouter(prefix="/market", tags=["market"])
logger = logging.getLogger(__name__)


@router.get("/badges")
async def get_market_badges(
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="State code (e.g., GA)")
) -> Dict[str, Any]:
    """
    Get market intelligence badges for a city.
    
    Badges include:
    - 🔥 Hot Market (surge_index > 20%)
    - 📈 Buy Window (digital > physical demand)
    - 🏆 Premium Location (TPI >= 70)
    - ⚡ Accelerating (TVS > 60)
    - 🐢 Slowing (TVS < 40)
    """
    try:
        badges = get_market_badges_sync(city, state)
        return {
            "success": True,
            "city": city,
            "state": state,
            "badges": badges,
            "count": len(badges)
        }
    except Exception as e:
        logger.error(f"Error fetching market badges: {e}")
        return {
            "success": False,
            "city": city,
            "state": state,
            "badges": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/composite-metrics")
async def get_composite_metrics(
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="State code (e.g., GA)")
) -> Dict[str, Any]:
    """
    Get composite traffic metrics from JediRe.
    
    Returns:
    - surge_index: Traffic Surge Index (daily real-time vs baseline)
    - digital_physical_gap: Search momentum minus physical traffic YoY
    - tpi: Traffic Position Index (percentile 0-100)
    - tvs: Traffic Velocity Score (momentum/acceleration 0-100)
    """
    try:
        metrics = get_composite_traffic_metrics_sync(city, state)
        if not metrics:
            return {
                "success": False,
                "city": city,
                "state": state,
                "error": "No data available for this location"
            }
        
        return {
            "success": True,
            "city": city,
            "state": state,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error fetching composite metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence")
async def get_market_intelligence(
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="State code (e.g., GA)")
) -> Dict[str, Any]:
    """
    Get full market intelligence summary for a city.
    
    Combines:
    - Composite traffic metrics
    - Market badges
    - Demand signals (if available)
    - Market economics (if available)
    """
    try:
        client = get_jedire_client()
        
        # Gather all available data
        metrics = get_composite_traffic_metrics_sync(city, state)
        badges = client.get_market_badges(metrics) if metrics else []
        demand = get_demand_signals_sync(city, state)
        economics = get_market_economics_sync(city, state)
        
        # Build response
        response = {
            "success": True,
            "city": city,
            "state": state,
            "badges": badges,
            "metrics": {
                "composite_traffic": metrics,
                "demand_signals": demand.get("signals", []) if demand else [],
                "economics": {
                    "median_rent": economics.get("median_rent") if economics else None,
                    "vacancy_rate": economics.get("vacancy_rate") if economics else None,
                    "rent_trend": economics.get("rent_trend") if economics else None,
                    "spending_power_index": economics.get("spending_power_index") if economics else None
                } if economics else None
            },
            "has_data": bool(metrics or demand or economics)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching market intelligence: {e}")
        return {
            "success": False,
            "city": city,
            "state": state,
            "error": str(e),
            "has_data": False
        }


@router.get("/health")
async def market_health() -> Dict[str, Any]:
    """
    Health check for JediRe integration.
    """
    try:
        client = get_jedire_client()
        
        # Try to fetch data for a known city
        test_metrics = get_composite_traffic_metrics_sync("Atlanta", "GA")
        
        return {
            "status": "healthy",
            "jedire_connected": test_metrics is not None,
            "test_data_available": bool(test_metrics)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "jedire_connected": False
        }
