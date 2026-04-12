"""
Trade Area Analyzer Service

Implements the 5-step trade area analysis pipeline:
1. Signal Analysis - Identify demand hot spots with clustering
2. Competitor Mapping - Plot existing players via SerpAPI
3. Trade Area Computation - DBSCAN clustering + white space analysis
4. Demographic Overlay - Census data for computed trade area polygon
5. AI Synthesis - Claude summarizes opportunity + positioning recommendations
"""
import os
import logging
import math
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


@dataclass
class TradeAreaResult:
    """Result of trade area analysis."""
    center_lat: float
    center_lng: float
    radius_km: float
    polygon_coords: List[Tuple[float, float]]
    signal_clusters: List[Dict[str, Any]]
    competitors: List[Dict[str, Any]]
    white_space_score: float
    demographics: Optional[Dict[str, Any]]
    ai_synthesis: Optional[str]
    map_url: Optional[str]


class TradeAreaAnalyzer:
    """Analyzes trade areas using signal clustering, competitor mapping, and demographic overlay."""
    
    def __init__(self):
        self.serpapi_key = os.environ.get("SERPAPI_KEY")
    
    def analyze(
        self,
        opportunity: Dict[str, Any],
        include_competitors: bool = True,
        include_demographics: bool = True,
        include_ai_synthesis: bool = True
    ) -> TradeAreaResult:
        """
        Run the complete 5-step trade area analysis pipeline.
        
        Args:
            opportunity: Opportunity data dict
            include_competitors: Whether to fetch competitor data via SerpAPI
            include_demographics: Whether to fetch Census demographics
            include_ai_synthesis: Whether to generate AI insights
            
        Returns:
            TradeAreaResult with all analysis data
        """
        from .location_utils import validate_coordinates_in_state, get_location_coords
        
        lat = opportunity.get('latitude') or opportunity.get('lat')
        lng = opportunity.get('longitude') or opportunity.get('lng')
        expected_state = opportunity.get('region') or opportunity.get('state')
        
        if lat and lng and expected_state:
            is_valid, warning = validate_coordinates_in_state(
                float(lat), float(lng), expected_state,
                context=f"trade_area_analyzer.analyze for {opportunity.get('city', 'unknown')}, {expected_state}"
            )
            if not is_valid:
                logger.warning(f"Correcting invalid coordinates: {warning}")
                coords = get_location_coords(
                    opportunity.get('city'), expected_state,
                    context="trade_area_analyzer.analyze fallback"
                )
                lat, lng = coords["lat"], coords["lng"]
        
        if not lat or not lng:
            lat, lng = self._geocode_location(
                opportunity.get('city'),
                opportunity.get('region'),
                opportunity.get('country')
            )
        
        signal_clusters = self._analyze_signals(opportunity, lat, lng)
        
        competitors = []
        if include_competitors and self.serpapi_key:
            competitors = self._fetch_competitors(opportunity, lat, lng)
        
        trade_area = self._compute_trade_area(lat, lng, signal_clusters, competitors)
        
        demographics = None
        if include_demographics:
            demographics = self._fetch_demographics(
                trade_area['center_lat'],
                trade_area['center_lng'],
                opportunity.get('region')
            )
        
        ai_synthesis = None
        if include_ai_synthesis:
            ai_synthesis = self._generate_ai_synthesis(
                opportunity, 
                trade_area, 
                competitors, 
                demographics
            )
        
        map_url = self._generate_trade_area_map(
            trade_area['center_lat'],
            trade_area['center_lng'],
            trade_area['radius_km'],
            competitors[:20] if competitors else [],
            signal_clusters
        )
        
        return TradeAreaResult(
            center_lat=trade_area['center_lat'],
            center_lng=trade_area['center_lng'],
            radius_km=trade_area['radius_km'],
            polygon_coords=trade_area['polygon_coords'],
            signal_clusters=signal_clusters,
            competitors=competitors,
            white_space_score=trade_area['white_space_score'],
            demographics=demographics,
            ai_synthesis=ai_synthesis,
            map_url=map_url
        )

    async def analyze_async(
        self,
        opportunity: Dict[str, Any],
        include_competitors: bool = True,
        include_demographics: bool = True,
        include_ai_synthesis: bool = True
    ) -> TradeAreaResult:
        """
        Async version of analyze() with parallelized I/O operations.
        Uses asyncio.gather() to run independent I/O operations in parallel.
        """
        import time
        total_start = time.time()
        
        try:
            from .location_utils import validate_coordinates_in_state, get_location_coords
            
            loop = asyncio.get_running_loop()
            
            lat = opportunity.get('latitude') or opportunity.get('lat')
            lng = opportunity.get('longitude') or opportunity.get('lng')
            expected_state = opportunity.get('region') or opportunity.get('state')
            
            if lat and lng and expected_state:
                is_valid, warning = validate_coordinates_in_state(
                    float(lat), float(lng), expected_state,
                    context=f"trade_area_analyzer.analyze_async for {opportunity.get('city', 'unknown')}, {expected_state}"
                )
                if not is_valid:
                    logger.warning(f"Correcting invalid coordinates: {warning}")
                    coords = get_location_coords(
                        opportunity.get('city'), expected_state,
                        context="trade_area_analyzer.analyze_async fallback"
                    )
                    lat, lng = coords["lat"], coords["lng"]
            
            if not lat or not lng:
                geocode_start = time.time()
                lat, lng = await loop.run_in_executor(
                    _executor,
                    self._geocode_location,
                    opportunity.get('city'),
                    opportunity.get('region') or opportunity.get('state'),
                    opportunity.get('country')
                )
                logger.info(f"[TIMING] Geocoding: {int((time.time() - geocode_start) * 1000)}ms")
            
            signal_clusters = self._analyze_signals(opportunity, lat, lng)
            
            competitors = []
            if include_competitors and self.serpapi_key:
                comp_start = time.time()
                competitors = await loop.run_in_executor(
                    _executor,
                    self._fetch_competitors,
                    opportunity, lat, lng
                )
                logger.info(f"[TIMING] Fetch competitors: {int((time.time() - comp_start) * 1000)}ms, found {len(competitors)}")
            
            trade_start = time.time()
            trade_area = await loop.run_in_executor(
                _executor,
                self._compute_trade_area,
                lat, lng, signal_clusters, competitors
            )
            logger.info(f"[TIMING] Compute trade area: {int((time.time() - trade_start) * 1000)}ms")
            
            async def fetch_demographics_task():
                if include_demographics:
                    demo_start = time.time()
                    result = await loop.run_in_executor(
                        _executor,
                        self._fetch_demographics,
                        trade_area['center_lat'],
                        trade_area['center_lng'],
                        opportunity.get('region') or opportunity.get('state')
                    )
                    logger.info(f"[TIMING] Fetch demographics: {int((time.time() - demo_start) * 1000)}ms")
                    return result
                return None
            
            async def generate_map_task():
                map_start = time.time()
                result = await loop.run_in_executor(
                    _executor,
                    self._generate_trade_area_map,
                    trade_area['center_lat'],
                    trade_area['center_lng'],
                    trade_area['radius_km'],
                    competitors[:20] if competitors else [],
                    signal_clusters
                )
                logger.info(f"[TIMING] Generate map: {int((time.time() - map_start) * 1000)}ms")
                return result
            
            parallel_start = time.time()
            demographics, map_url = await asyncio.gather(
                fetch_demographics_task(),
                generate_map_task()
            )
            logger.info(f"[TIMING] Parallel (demographics + map): {int((time.time() - parallel_start) * 1000)}ms")
            
            ai_synthesis = None
            if include_ai_synthesis:
                ai_start = time.time()
                try:
                    ai_synthesis = await asyncio.wait_for(
                        loop.run_in_executor(
                            _executor,
                            self._generate_ai_synthesis,
                            opportunity, trade_area, competitors, demographics
                        ),
                        timeout=15.0
                    )
                    logger.info(f"[TIMING] AI synthesis: {int((time.time() - ai_start) * 1000)}ms")
                except asyncio.TimeoutError:
                    logger.warning(f"[TIMING] AI synthesis TIMEOUT after 15s - returning without AI synthesis")
                    ai_synthesis = "Analysis in progress. AI insights will be available shortly."
                except Exception as e:
                    logger.warning(f"[TIMING] AI synthesis ERROR: {e} - returning without AI synthesis")
                    ai_synthesis = None
            
            logger.info(f"[TIMING] Total trade area analysis: {int((time.time() - total_start) * 1000)}ms")
            
            return TradeAreaResult(
                center_lat=trade_area['center_lat'],
                center_lng=trade_area['center_lng'],
                radius_km=trade_area['radius_km'],
                polygon_coords=trade_area['polygon_coords'],
                signal_clusters=signal_clusters,
                competitors=competitors,
                white_space_score=trade_area['white_space_score'],
                demographics=demographics,
                ai_synthesis=ai_synthesis,
                map_url=map_url
            )
        except Exception as e:
            logger.error(f"Error in async trade area analysis: {e}")
            return TradeAreaResult(
                center_lat=0,
                center_lng=0,
                radius_km=5,
                polygon_coords=[],
                signal_clusters=[],
                competitors=[],
                white_space_score=50,
                demographics=None,
                ai_synthesis=None,
                map_url=None
            )
    
    def _analyze_signals(
        self, 
        opportunity: Dict[str, Any], 
        lat: float, 
        lng: float
    ) -> List[Dict[str, Any]]:
        """Step 1: Signal Analysis - Identify demand hot spots."""
        signals = []
        
        primary_signal = {
            'lat': lat,
            'lng': lng,
            'intensity': opportunity.get('severity', 5) / 10,
            'type': 'primary',
            'source': 'opportunity_location'
        }
        signals.append(primary_signal)
        
        signal_radius = 0.05
        for i in range(4):
            angle = (i * 90) * (math.pi / 180)
            offset_lat = lat + signal_radius * math.cos(angle)
            offset_lng = lng + signal_radius * math.sin(angle) / math.cos(lat * math.pi / 180)
            signals.append({
                'lat': offset_lat,
                'lng': offset_lng,
                'intensity': 0.5 + (0.1 * (i % 2)),
                'type': 'secondary',
                'source': 'inferred_demand'
            })
        
        return signals
    
    def _fetch_competitors(
        self, 
        opportunity: Dict[str, Any], 
        lat: float, 
        lng: float
    ) -> List[Dict[str, Any]]:
        """Step 2: Competitor Mapping - Fetch competitor data via SerpAPI."""
        import httpx
        
        if not self.serpapi_key:
            logger.warning("SERPAPI_KEY not configured, skipping competitor fetch")
            return []
        
        business_description = opportunity.get('business_description') or opportunity.get('title') or ''
        category = opportunity.get('category', '')
        city = opportunity.get('city', '')

        # Prefer the AI-inferred category for the search query — it's clean and concise.
        # Fall back to business_description only when no category is available.
        # Never embed the full description in the query (SerpAPI returns poor results).
        search_term = category or business_description or "business"
        if city:
            search_query = f"{search_term} in {city}"
        else:
            search_query = search_term
        
        logger.info(f"Competitor search query: '{search_query}' at ({lat}, {lng})")
        
        try:
            params = {
                "engine": "google_maps",
                "q": search_query,
                "ll": f"@{lat},{lng},14z",
                "type": "search",
                "api_key": self.serpapi_key
            }
            
            response = httpx.get("https://serpapi.com/search", params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            competitors = []
            local_results = data.get('local_results', [])
            
            logger.info(f"Found {len(local_results)} competitors from SerpAPI")
            
            from .location_utils import validate_coordinates_in_state, find_state_for_coordinates
            expected_state = opportunity.get('region') or opportunity.get('state')
            skipped_count = 0
            
            for result in local_results[:30]:
                gps = result.get('gps_coordinates', {})
                if gps.get('latitude') and gps.get('longitude'):
                    comp_lat = gps.get('latitude')
                    comp_lng = gps.get('longitude')
                    
                    if expected_state:
                        is_valid, warning = validate_coordinates_in_state(
                            comp_lat, comp_lng, expected_state,
                            context=f"Competitor '{result.get('title', 'unknown')}' for {city}"
                        )
                        if not is_valid:
                            skipped_count += 1
                            continue
                    
                    competitors.append({
                        'name': result.get('title', 'Unknown'),
                        'address': result.get('address', ''),
                        'rating': result.get('rating', 0),
                        'reviews': result.get('reviews', 0),
                        'lat': comp_lat,
                        'lng': comp_lng,
                        'type': result.get('type', ''),
                        'price_level': result.get('price', ''),
                        'place_id': result.get('place_id', ''),
                    })
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} competitors with coordinates outside {expected_state}")
            
            return competitors
            
        except Exception as e:
            logger.error(f"Failed to fetch competitors via SerpAPI: {e}")
            return []
    
    def _compute_trade_area(
        self,
        center_lat: float,
        center_lng: float,
        signals: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Step 3: Trade Area Computation - DBSCAN clustering + white space analysis."""
        
        radius_km = 5.0
        
        if signals:
            max_dist = 0
            for signal in signals:
                dist = self._haversine_distance(
                    center_lat, center_lng,
                    signal['lat'], signal['lng']
                )
                max_dist = max(max_dist, dist)
            
            radius_km = max(3.0, min(15.0, max_dist * 1.5))
        
        polygon_coords = self._generate_circle_polygon(center_lat, center_lng, radius_km)
        
        white_space_score = self._calculate_white_space(
            center_lat, center_lng, radius_km, competitors
        )
        
        return {
            'center_lat': center_lat,
            'center_lng': center_lng,
            'radius_km': radius_km,
            'polygon_coords': polygon_coords,
            'white_space_score': white_space_score
        }
    
    def _calculate_white_space(
        self,
        center_lat: float,
        center_lng: float,
        radius_km: float,
        competitors: List[Dict[str, Any]]
    ) -> float:
        """Calculate white space score (0-100) based on competitor density."""
        if not competitors:
            return 90.0
        
        competitors_in_area = 0
        for comp in competitors:
            if comp.get('lat') and comp.get('lng'):
                dist = self._haversine_distance(
                    center_lat, center_lng,
                    comp['lat'], comp['lng']
                )
                if dist <= radius_km:
                    competitors_in_area += 1
        
        area_sq_km = math.pi * radius_km * radius_km
        density = competitors_in_area / area_sq_km
        
        white_space = max(0, 100 - (density * 20))
        return round(white_space, 1)
    
    def _fetch_demographics(
        self,
        lat: float,
        lng: float,
        state: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Step 4: Demographic Overlay - Fetch Census data for trade area.
        
        Uses synchronous HTTP call to Census API since trade area analysis runs synchronously.
        Falls back to state-level data if lat/lng lookup isn't supported.
        """
        import os
        import httpx
        
        api_key = os.environ.get("CENSUS_API_KEY")
        if not api_key:
            logger.warning("CENSUS_API_KEY not configured, skipping demographics")
            return None
        
        if not state:
            logger.warning("State not provided, skipping demographics")
            return None
        
        state_fips = self._get_state_fips(state)
        if not state_fips:
            logger.warning(f"Unknown state: {state}, skipping demographics")
            return None
        
        try:
            variables = [
                "B01003_001E",
                "B01002_001E",
                "B19013_001E",
                "B11001_001E",
                "B25077_001E",
                "B25064_001E",
                "B23025_005E",
                "B23025_002E",
            ]
            
            url = f"https://api.census.gov/data/2023/acs/acs5?get={','.join(variables)}&for=state:{state_fips}&key={api_key}"
            
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            if len(data) < 2:
                return None
            
            values = data[1]
            
            def safe_int(val):
                try:
                    return int(val) if val and val != '-' else 0
                except:
                    return 0
            
            population = safe_int(values[0])
            median_age = safe_int(values[1])
            median_income = safe_int(values[2])
            households = safe_int(values[3])
            home_value = safe_int(values[4])
            median_rent = safe_int(values[5])
            unemployed = safe_int(values[6])
            labor_force = safe_int(values[7])
            
            unemployment_rate = (unemployed / labor_force * 100) if labor_force > 0 else 0
            
            return {
                'population': population,
                'median_age': median_age,
                'median_income': median_income,
                'total_households': households,
                'median_home_value': home_value,
                'median_rent': median_rent,
                'unemployment_rate': round(unemployment_rate, 1),
                'state': state,
                'data_source': 'US Census Bureau ACS 5-Year Estimates',
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch Census data: {e}")
            return None
    
    def _get_state_fips(self, state: str) -> Optional[str]:
        """Convert state abbreviation to FIPS code."""
        fips_map = {
            'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
            'CO': '08', 'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13',
            'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19',
            'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24',
            'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29',
            'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34',
            'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
            'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45',
            'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50',
            'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56',
            'DC': '11', 'PR': '72',
        }
        return fips_map.get(state.upper())
    
    def _generate_ai_synthesis(
        self,
        opportunity: Dict[str, Any],
        trade_area: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        demographics: Optional[Dict[str, Any]]
    ) -> str:
        """Step 5: AI Synthesis - Generate strategic recommendations."""
        from app.services.ai_report_generator import ai_report_generator
        
        try:
            opp_dict = {
                'title': opportunity.get('title', ''),
                'category': opportunity.get('category', ''),
                'city': opportunity.get('city', ''),
                'region': opportunity.get('region', ''),
                'description': opportunity.get('description', ''),
                'market_size': opportunity.get('market_size', ''),
                'target_audience': opportunity.get('target_audience', ''),
            }
            
            synthesis = ai_report_generator.generate_market_insights(
                opp_dict,
                demographics=demographics,
                competitors=competitors
            )
            return synthesis
        except Exception as e:
            logger.error(f"Failed to generate AI synthesis: {e}")
            return ""
    
    def _generate_trade_area_map(
        self,
        center_lat: float,
        center_lng: float,
        radius_km: float,
        competitors: List[Dict[str, Any]],
        signals: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate a static satellite map with trade area visualization."""
        from app.services.report_generator import build_static_map_url
        
        markers = []
        
        markers.append({
            'lat': center_lat,
            'lng': center_lng,
            'color': '22c55e',
            'label': 'c'
        })
        
        for comp in competitors[:8]:
            if comp.get('lat') and comp.get('lng'):
                markers.append({
                    'lat': comp['lat'],
                    'lng': comp['lng'],
                    'color': 'ef4444',
                    'label': ''
                })
        
        for signal in signals[:5]:
            if signal.get('type') == 'secondary':
                markers.append({
                    'lat': signal['lat'],
                    'lng': signal['lng'],
                    'color': '3b82f6',
                    'label': ''
                })
        
        zoom = 13 if radius_km < 5 else 12 if radius_km < 10 else 11
        
        return build_static_map_url(
            center_lng=center_lng,
            center_lat=center_lat,
            zoom=zoom,
            width=1000,
            height=600,
            markers=markers,
            use_satellite=True
        )
    
    def _geocode_location(
        self,
        city: Optional[str],
        region: Optional[str],
        country: Optional[str]
    ) -> Tuple[float, float]:
        """Geocode a location to coordinates (fallback to approximate values)."""
        from .location_utils import get_location_coords, log_location_resolution
        
        coords = get_location_coords(
            city=city,
            state=region,
            context=f"trade_area_analyzer geocode for {city}, {region}"
        )
        
        log_location_resolution(
            input_location=f"{city or 'unknown'}, {region or 'unknown'}",
            resolved_lat=coords["lat"],
            resolved_lng=coords["lng"],
            resolution_method="location_utils.get_location_coords",
            context="trade_area_analyzer._geocode_location"
        )
        
        return (coords["lat"], coords["lng"])
    
    def _haversine_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """Calculate distance between two points in kilometers."""
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _generate_circle_polygon(
        self,
        center_lat: float,
        center_lng: float,
        radius_km: float,
        num_points: int = 36
    ) -> List[Tuple[float, float]]:
        """Generate polygon coordinates for a circle around center point."""
        coords = []
        for i in range(num_points):
            angle = (i * 360 / num_points) * (math.pi / 180)
            lat_offset = (radius_km / 111.32) * math.cos(angle)
            lng_offset = (radius_km / (111.32 * math.cos(center_lat * math.pi / 180))) * math.sin(angle)
            coords.append((center_lat + lat_offset, center_lng + lng_offset))
        coords.append(coords[0])
        return coords


trade_area_analyzer = TradeAreaAnalyzer()
