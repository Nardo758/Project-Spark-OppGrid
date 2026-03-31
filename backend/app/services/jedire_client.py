"""
JediRE Client Service

Fetches demand signals and market economics from JediRE platform
(aggregated from Apartment Locator AI data).
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# JediRE API configuration
JEDIRE_API_URL = os.environ.get(
    "JEDIRE_API_URL",
    "https://381d5707-51e5-4d3d-b340-02537a082e98-00-2gk8jsdbkwoy5.worf.replit.dev"
)
JEDIRE_API_TOKEN = os.environ.get(
    "JEDIRE_API_TOKEN",
    "69295404e382acd00de4facdaa053fd20ae0a1cf15dc63c0b8a55cffc0e088b6"
)

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600
_cache: Dict[str, tuple] = {}  # key -> (timestamp, data)


def _get_cached(key: str) -> Optional[Any]:
    """Get cached data if not expired."""
    if key in _cache:
        timestamp, data = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    """Cache data with timestamp."""
    _cache[key] = (time.time(), data)


class JediREClient:
    """Client for fetching market intelligence from JediRE."""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or JEDIRE_API_URL).rstrip('/')
        self.token = token or JEDIRE_API_TOKEN
        self.timeout = 10.0  # seconds
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    async def get_demand_signals(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demand signals for a city.
        
        Returns dict with:
        - signals: list of {amenity_type, demand_pct, avg_frequency, trend, ...}
        - count: number of signals
        - updated_at: when data was last updated
        """
        cache_key = f"demand:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            logger.debug(f"[JediRE] Cache hit for demand signals: {city}, {state}")
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/oppgrid/demand-signals",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    _set_cached(cache_key, data)
                    logger.info(f"[JediRE] Fetched {data.get('count', 0)} demand signals for {city}, {state}")
                    return data
                elif response.status_code == 404:
                    logger.info(f"[JediRE] No demand data for {city}, {state}")
                    return None
                else:
                    logger.warning(f"[JediRE] demand-signals error {response.status_code}: {response.text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching demand signals: {e}")
            return None
    
    async def get_market_economics(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market economics for a city.
        
        Returns dict with:
        - avg_rent_1br, avg_rent_2br, avg_rent_3br
        - median_rent
        - vacancy_rate
        - rent_trend
        - spending_power_index
        """
        cache_key = f"economics:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            logger.debug(f"[JediRE] Cache hit for market economics: {city}, {state}")
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/oppgrid/market-economics",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    _set_cached(cache_key, data)
                    logger.info(f"[JediRE] Fetched market economics for {city}, {state}")
                    return data
                elif response.status_code == 404:
                    logger.info(f"[JediRE] No market economics for {city}, {state}")
                    return None
                else:
                    logger.warning(f"[JediRE] market-economics error {response.status_code}: {response.text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching market economics: {e}")
            return None
    
    async def score_location(
        self,
        city: str,
        state: str,
        business_type: str,
        address: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Score a business location based on demand and demographics.
        
        Returns dict with:
        - overall_score (0-100)
        - breakdown: {demand_score, demographics_score, accessibility_score, competition_score}
        - insights: list of text insights
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/oppgrid/score-location",
                    json={
                        "city": city,
                        "state": state,
                        "business_type": business_type,
                        "address": address,
                    },
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"[JediRE] Scored location: {city}, {state} for {business_type} = {data.get('overall_score')}")
                    return data
                else:
                    logger.warning(f"[JediRE] score-location error {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error scoring location: {e}")
            return None
    
    async def get_all_market_data(
        self,
        city: str,
        state: str,
        business_type: str = None
    ) -> Dict[str, Any]:
        """
        Fetch all available market data for a location.
        
        Combines demand signals, market economics, and optional location score.
        """
        result = {
            "city": city,
            "state": state,
            "demand_signals": None,
            "market_economics": None,
            "location_score": None,
            "has_data": False,
        }
        
        # Fetch in parallel
        import asyncio
        
        tasks = [
            self.get_demand_signals(city, state),
            self.get_market_economics(city, state),
        ]
        
        if business_type:
            tasks.append(self.score_location(city, state, business_type))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        if not isinstance(results[0], Exception) and results[0]:
            result["demand_signals"] = results[0]
            result["has_data"] = True
            
        if not isinstance(results[1], Exception) and results[1]:
            result["market_economics"] = results[1]
            result["has_data"] = True
            
        if business_type and len(results) > 2:
            if not isinstance(results[2], Exception) and results[2]:
                result["location_score"] = results[2]
        
        return result


# Module-level client instance
_client: Optional[JediREClient] = None


def get_jedire_client() -> JediREClient:
    """Get or create the JediRE client singleton."""
    global _client
    if _client is None:
        _client = JediREClient()
    return _client


# Convenience functions for sync code (run in executor)
def get_demand_signals_sync(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_demand_signals."""
    import asyncio
    client = get_jedire_client()
    return asyncio.get_event_loop().run_until_complete(
        client.get_demand_signals(city, state)
    )


def get_market_economics_sync(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_market_economics."""
    import asyncio
    client = get_jedire_client()
    return asyncio.get_event_loop().run_until_complete(
        client.get_market_economics(city, state)
    )
