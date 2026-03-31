"""
JediRE Client Service - Full 4 P's Integration

Bi-directional data flow:
- PULL: JediRE metrics → OppGrid reports (traffic, rent, demographics, digital)
- PUSH: OppGrid signals → JediRE strategy builder (demand scores, growth trajectories)

4 P's Framework:
- PRODUCT: Demand signals, pain intensity, opportunity scores
- PRICE: Rent economics, spending power, market size
- PLACE: Traffic, demographics, growth trajectories
- PROMOTION: Search trends, competition, sentiment
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from functools import lru_cache
import time
import asyncio

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
    """
    Full-featured client for bi-directional JediRE integration.
    
    PULL Methods (JediRE → OppGrid):
    - get_demand_signals() - What residents want nearby
    - get_market_economics() - Rent levels, spending power
    - get_market_data() - Full market intelligence
    - get_rent_comps() - Individual property data
    - get_traffic_data() - AADT, walk-ins, traffic scores
    - get_demographics() - Census data
    - get_search_trends() - Digital demand signals
    
    PUSH Methods (OppGrid → JediRE):
    - push_opportunity_signals() - OppGrid opportunity scores
    - push_growth_trajectory() - Market growth data
    """
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or JEDIRE_API_URL).rstrip('/')
        self.token = token or JEDIRE_API_TOKEN
        self.timeout = 15.0  # seconds
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    # =========================================================================
    # PULL: PRODUCT (Demand)
    # =========================================================================
    
    async def get_demand_signals(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demand signals for a city (from Apartment Locator AI).
        
        Returns:
        - signals: list of {amenity_type, demand_pct, avg_frequency, trend}
        - count: number of signals
        - updated_at: when data was last updated
        """
        cache_key = f"demand:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
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
                    return None
                else:
                    logger.warning(f"[JediRE] demand-signals error {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching demand signals: {e}")
            return None
    
    async def get_user_preferences(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch aggregated user preferences (from Apartment Locator AI).
        
        Returns amenity preferences, deal breakers, budget distribution.
        """
        cache_key = f"prefs:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/user-preferences-aggregate",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        _set_cached(cache_key, data.get('data'))
                        return data.get('data')
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching user preferences: {e}")
            return None
    
    # =========================================================================
    # PULL: PRICE (Economics)
    # =========================================================================
    
    async def get_market_economics(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market economics for a city.
        
        Returns:
        - avg_rent_1br, avg_rent_2br, avg_rent_3br
        - median_rent
        - vacancy_rate
        - rent_trend
        - spending_power_index (0-100)
        """
        cache_key = f"economics:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
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
                    return data
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching market economics: {e}")
            return None
    
    async def get_market_data(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch full market data from JediRE's JEDI integration.
        
        Returns supply, pricing, demand, and forecast data.
        """
        cache_key = f"market:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/market-data",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        result = data.get('data')
                        _set_cached(cache_key, result)
                        return result
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching market data: {e}")
            return None
    
    async def get_rent_comps(
        self, 
        city: str, 
        state: str,
        bedrooms: int = None,
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch individual rent comparables.
        
        Returns list of properties with rent, sqft, amenities.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"city": city, "state": state, "limit": limit}
                if bedrooms:
                    params["bedrooms"] = bedrooms
                    
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/rent-comps",
                    params=params,
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data', [])
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching rent comps: {e}")
            return None
    
    # =========================================================================
    # PULL: PLACE (Location)
    # =========================================================================
    
    async def get_absorption_rate(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch absorption rate data.
        
        Returns avg_days_to_lease, monthly_absorption_rate.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/absorption-rate",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data')
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching absorption rate: {e}")
            return None
    
    async def get_supply_pipeline(
        self, 
        city: str, 
        state: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch supply pipeline (new developments).
        
        Returns list of upcoming properties.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/supply-pipeline",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data', [])
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching supply pipeline: {e}")
            return None
    
    async def get_growth_indices(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch leading growth indicators from JediRE.
        
        Returns:
        - traffic_growth_index: (Google Realtime ADT - DOT Historical) / DOT Historical × 100
        - search_growth_index: Similar formula for online search volume
        
        Positive = growing market, Negative = declining
        """
        cache_key = f"growth:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/oppgrid/growth-indices",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        result = data.get('data', {})
                        _set_cached(cache_key, result)
                        return result
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching growth indices: {e}")
            return None
    
    async def get_composite_traffic_metrics(
        self,
        city: str,
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch composite traffic metrics for market intelligence badges.
        
        Returns:
        - surge_index: Traffic Surge Index (daily real-time vs baseline)
        - digital_physical_gap: Search momentum minus physical traffic YoY
        - tpi: Traffic Position Index (percentile 0-100)
        - tvs: Traffic Velocity Score (momentum/acceleration 0-100)
        
        Badge rules:
        - surge_index > 20 → "🔥 Hot Market"
        - digital_physical_gap > 0 → "📈 Buy Window"
        - tpi >= 70 → Premium location
        - tvs > 60 → "⚡ Accelerating"
        """
        cache_key = f"composite_traffic:{city.lower()}:{state.upper()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/oppgrid/composite-traffic",
                    params={"city": city, "state": state},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        result = data.get('data', {})
                        _set_cached(cache_key, result)
                        return result
                
                # Fallback: compute from growth indices if endpoint doesn't exist
                if response.status_code == 404:
                    return await self._compute_composite_metrics_fallback(city, state)
                    
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching composite traffic metrics: {e}")
            # Try fallback computation
            return await self._compute_composite_metrics_fallback(city, state)
    
    async def _compute_composite_metrics_fallback(
        self,
        city: str,
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compute composite metrics locally from available data.
        Used when JediRE doesn't have the dedicated endpoint.
        """
        try:
            # Get growth indices as base
            growth = await self.get_growth_indices(city, state)
            economics = await self.get_market_economics(city, state)
            
            if not growth and not economics:
                return None
            
            tgi = growth.get('traffic_growth_index', 0) if growth else 0
            sgi = growth.get('search_growth_index', 0) if growth else 0
            vacancy = economics.get('vacancy_rate', 5) if economics else 5
            rent_trend = economics.get('rent_trend', 'stable') if economics else 'stable'
            
            # Compute derived metrics
            # Surge Index: amplified version of TGI for daily signals
            surge_index = tgi * 1.2  # Amplify for badge threshold
            
            # Digital-Physical Gap: search demand vs physical traffic
            digital_physical_gap = sgi - tgi
            
            # TPI: Traffic Position Index (percentile based on growth)
            # Map TGI to 0-100 percentile (rough approximation)
            tpi = min(100, max(0, 50 + (tgi * 2)))
            
            # TVS: Traffic Velocity Score (momentum)
            # Higher if both TGI and SGI are positive and trending up
            base_tvs = 50
            if tgi > 0:
                base_tvs += min(25, tgi)
            if sgi > 0:
                base_tvs += min(25, sgi)
            if rent_trend == 'rising':
                base_tvs += 10
            if vacancy < 4:
                base_tvs += 10
            tvs = min(100, max(0, base_tvs))
            
            result = {
                'surge_index': round(surge_index, 2),
                'digital_physical_gap': round(digital_physical_gap, 2),
                'tpi': round(tpi),
                'tvs': round(tvs),
                'computed_locally': True,
                'source_metrics': {
                    'traffic_growth_index': tgi,
                    'search_growth_index': sgi,
                    'vacancy_rate': vacancy,
                    'rent_trend': rent_trend
                }
            }
            
            _set_cached(f"composite_traffic:{city.lower()}:{state.upper()}", result)
            return result
            
        except Exception as e:
            logger.error(f"[JediRE] Error computing composite metrics fallback: {e}")
            return None
    
    def get_market_badges(self, composite_metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate market intelligence badges from composite metrics.
        
        Returns list of badges with:
        - id: badge identifier
        - emoji: display emoji
        - label: short label
        - description: tooltip text
        - color: tailwind color class
        """
        badges = []
        
        if not composite_metrics:
            return badges
        
        surge = composite_metrics.get('surge_index', 0)
        gap = composite_metrics.get('digital_physical_gap', 0)
        tpi = composite_metrics.get('tpi', 50)
        tvs = composite_metrics.get('tvs', 50)
        
        # 🔥 Hot Market: surge_index > 20%
        if surge > 20:
            badges.append({
                'id': 'hot_market',
                'emoji': '🔥',
                'label': 'Hot Market',
                'description': f'Traffic surge {surge:.0f}% above baseline - demand outpacing supply',
                'color': 'bg-orange-100 text-orange-700 border-orange-200'
            })
        
        # 📈 Buy Window: digital demand exceeds physical
        if gap > 5:
            badges.append({
                'id': 'buy_window',
                'emoji': '📈',
                'label': 'Buy Window',
                'description': f'Digital demand +{gap:.0f}% ahead of physical - opportunity to position before growth materializes',
                'color': 'bg-emerald-100 text-emerald-700 border-emerald-200'
            })
        
        # 🏆 Premium Location: TPI >= 70
        if tpi >= 70:
            badges.append({
                'id': 'premium_location',
                'emoji': '🏆',
                'label': f'Top {100-tpi}%',
                'description': f'Traffic Position Index {tpi}/100 - premium location tier',
                'color': 'bg-amber-100 text-amber-700 border-amber-200'
            })
        
        # ⚡ Accelerating: TVS > 60
        if tvs > 60:
            badges.append({
                'id': 'accelerating',
                'emoji': '⚡',
                'label': 'Accelerating',
                'description': f'Traffic velocity score {tvs}/100 - growth momentum increasing',
                'color': 'bg-violet-100 text-violet-700 border-violet-200'
            })
        
        # 🐢 Decelerating: TVS < 40 (warning badge)
        if tvs < 40:
            badges.append({
                'id': 'decelerating',
                'emoji': '🐢',
                'label': 'Slowing',
                'description': f'Traffic velocity score {tvs}/100 - growth momentum declining',
                'color': 'bg-stone-100 text-stone-600 border-stone-200'
            })
        
        return badges
    
    def get_growth_indices_sync(
        self, 
        city: str, 
        state: str
    ) -> Optional[Dict[str, Any]]:
        """Sync version of get_growth_indices."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't use asyncio.run inside a running loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.get_growth_indices(city, state)
                    )
                    return future.result(timeout=self.timeout + 5)
            else:
                return asyncio.run(self.get_growth_indices(city, state))
        except Exception as e:
            logger.error(f"[JediRE] Sync growth indices error: {e}")
            return None
    
    # =========================================================================
    # PULL: PROMOTION (Digital & Competition)
    # =========================================================================
    
    async def get_search_trends(
        self, 
        city: str = None,
        state: str = None,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch search trends from Apartment Locator AI.
        
        Returns price range distribution, daily volume, unmet demand.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/search-trends",
                    params={"days": days},
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data')
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching search trends: {e}")
            return None
    
    async def get_demand_intelligence(
        self,
        city: str = None,
        state: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demand signals from JEDI integration.
        
        Returns budget distribution, bedroom demand, amenity preferences.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jedi/demand-signals",
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data')
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error fetching demand intelligence: {e}")
            return None
    
    # =========================================================================
    # PULL: Location Scoring
    # =========================================================================
    
    async def score_location(
        self,
        city: str,
        state: str,
        business_type: str,
        address: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Score a business location based on demand and demographics.
        
        Returns:
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
                return None
                    
        except Exception as e:
            logger.error(f"[JediRE] Error scoring location: {e}")
            return None
    
    # =========================================================================
    # PUSH: OppGrid Signals → JediRE
    # =========================================================================
    
    async def push_opportunity_signals(
        self,
        city: str,
        state: str,
        signals: List[Dict[str, Any]]
    ) -> bool:
        """
        Push OppGrid opportunity signals to JediRE for strategy builder.
        
        Signals format:
        [
            {
                "signal_type": "coffee_shop_demand",
                "score": 85,
                "confidence": 0.9,
                "category": "food_beverage",
                "trend": "rising"
            }
        ]
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/oppgrid/sync-signals",
                    json={
                        "city": city,
                        "state": state,
                        "source": "oppgrid",
                        "signals": signals,
                    },
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    logger.info(f"[JediRE] Pushed {len(signals)} OppGrid signals for {city}, {state}")
                    return True
                else:
                    logger.warning(f"[JediRE] Failed to push signals: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"[JediRE] Error pushing opportunity signals: {e}")
            return False
    
    async def push_growth_trajectory(
        self,
        city: str,
        state: str,
        trajectory: Dict[str, Any]
    ) -> bool:
        """
        Push OppGrid market growth trajectory to JediRE.
        
        Trajectory format:
        {
            "growth_score": 78,
            "growth_category": "growing",
            "population_growth_rate": 2.3,
            "job_growth_rate": 3.1,
            "business_formation_rate": 4.5,
            "opportunity_signal_count": 45,
            "signal_density_percentile": 82
        }
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/oppgrid/sync-trajectory",
                    json={
                        "city": city,
                        "state": state,
                        "source": "oppgrid",
                        **trajectory,
                    },
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    logger.info(f"[JediRE] Pushed growth trajectory for {city}, {state}")
                    return True
                return False
                    
        except Exception as e:
            logger.error(f"[JediRE] Error pushing growth trajectory: {e}")
            return False
    
    # =========================================================================
    # AGGREGATED: Full 4 P's Data
    # =========================================================================
    
    async def get_full_market_intelligence(
        self,
        city: str,
        state: str,
        business_type: str = None
    ) -> Dict[str, Any]:
        """
        Fetch complete market intelligence for the 4 P's framework.
        
        Returns all available data in a structured format.
        """
        result = {
            "city": city,
            "state": state,
            "product": {},  # Demand
            "price": {},    # Economics
            "place": {},    # Location
            "promotion": {},  # Competition/Digital
            "has_data": False,
        }
        
        # Fetch all data in parallel
        tasks = {
            "demand_signals": self.get_demand_signals(city, state),
            "market_economics": self.get_market_economics(city, state),
            "market_data": self.get_market_data(city, state),
            "absorption": self.get_absorption_rate(city, state),
            "demand_intelligence": self.get_demand_intelligence(city, state),
        }
        
        if business_type:
            tasks["location_score"] = self.score_location(city, state, business_type)
        
        # Run all tasks
        results = {}
        for key, coro in tasks.items():
            try:
                results[key] = await coro
            except Exception as e:
                logger.error(f"[JediRE] Error fetching {key}: {e}")
                results[key] = None
        
        # Organize into 4 P's
        
        # PRODUCT (Demand)
        if results.get("demand_signals"):
            result["product"]["demand_signals"] = results["demand_signals"].get("signals", [])
        if results.get("demand_intelligence"):
            result["product"]["budget_distribution"] = results["demand_intelligence"].get("budget", {})
            result["product"]["bedroom_demand"] = results["demand_intelligence"].get("bedroom_demand", [])
            result["product"]["top_amenities"] = results["demand_intelligence"].get("top_amenities", [])
            result["has_data"] = True
        
        # PRICE (Economics)
        if results.get("market_economics"):
            result["price"]["rent_by_bedroom"] = {
                "1br": results["market_economics"].get("avg_rent_1br"),
                "2br": results["market_economics"].get("avg_rent_2br"),
                "3br": results["market_economics"].get("avg_rent_3br"),
            }
            result["price"]["median_rent"] = results["market_economics"].get("median_rent")
            result["price"]["spending_power_index"] = results["market_economics"].get("spending_power_index")
            result["price"]["vacancy_rate"] = results["market_economics"].get("vacancy_rate")
            result["price"]["rent_trend"] = results["market_economics"].get("rent_trend")
            result["has_data"] = True
        
        if results.get("market_data"):
            md = results["market_data"]
            if md.get("pricing"):
                result["price"]["concession_rate"] = md["pricing"].get("concession_rate")
                result["price"]["avg_concession_value"] = md["pricing"].get("avg_concession_value")
            if md.get("supply"):
                result["place"]["total_properties"] = md["supply"].get("total_properties")
                result["place"]["available_units"] = md["supply"].get("available_units")
        
        # PLACE (Location)
        if results.get("absorption"):
            result["place"]["avg_days_to_lease"] = results["absorption"].get("avg_days_to_lease")
            result["place"]["monthly_absorption_rate"] = results["absorption"].get("monthly_absorption_rate")
        
        if results.get("location_score"):
            result["place"]["location_score"] = results["location_score"].get("overall_score")
            result["place"]["score_breakdown"] = results["location_score"].get("breakdown")
            result["place"]["insights"] = results["location_score"].get("insights", [])
        
        # PROMOTION (Competition/Digital)
        # Add when we have digital traffic data from JediRE
        
        return result


# Module-level client instance
_client: Optional[JediREClient] = None


def get_jedire_client() -> JediREClient:
    """Get or create the JediRE client singleton."""
    global _client
    if _client is None:
        _client = JediREClient()
    return _client


# Synchronous wrappers for non-async code
def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def get_demand_signals_sync(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_demand_signals."""
    client = get_jedire_client()
    return _run_async(client.get_demand_signals(city, state))


def get_market_economics_sync(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_market_economics."""
    client = get_jedire_client()
    return _run_async(client.get_market_economics(city, state))


def get_full_market_intelligence_sync(
    city: str, 
    state: str, 
    business_type: str = None
) -> Dict[str, Any]:
    """Synchronous wrapper for get_full_market_intelligence."""
    client = get_jedire_client()
    return _run_async(client.get_full_market_intelligence(city, state, business_type))


def get_composite_traffic_metrics_sync(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_composite_traffic_metrics."""
    client = get_jedire_client()
    return _run_async(client.get_composite_traffic_metrics(city, state))


def get_market_badges_sync(city: str, state: str) -> List[Dict[str, str]]:
    """
    Get market intelligence badges for a city.
    Combines fetching composite metrics and generating badges.
    """
    client = get_jedire_client()
    metrics = _run_async(client.get_composite_traffic_metrics(city, state))
    if not metrics:
        return []
    return client.get_market_badges(metrics)
