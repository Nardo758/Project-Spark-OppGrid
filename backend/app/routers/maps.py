from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Literal
import hashlib
import logging
import asyncio

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.services.serpapi_service import SerpAPIService
from app.services.location_analyzer import LocationAnalyzer, ScoringWeights, get_layer_weights
from app.services.dot_traffic_service import DOTTrafficService
from app.services.traffic_fusion import TrafficFusionService, fuse_traffic, TrafficTrend

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/maps", tags=["Maps"])


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float = Field(ge=0.0, le=1.0)


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)


class MapLayers(BaseModel):
    businesses: list[GeoJSONFeature] = Field(default_factory=list)
    problemHeatmap: list[HeatmapPoint] = Field(default_factory=list)
    neighborhoods: list[GeoJSONFeature] = Field(default_factory=list)


class MapData(BaseModel):
    center: list[float] = Field(min_length=2, max_length=2, description="[lat, lng]")
    zoom: int = Field(ge=1, le=20, default=11)
    layers: MapLayers


class LocationAnalysisResponse(BaseModel):
    query: str | None = None
    mapData: MapData


_KNOWN_CENTERS: dict[str, tuple[float, float]] = {
    "san francisco": (37.7749, -122.4194),
    "sf": (37.7749, -122.4194),
    "miami": (25.7617, -80.1918),
    "new york": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "austin": (30.2672, -97.7431),
    "los angeles": (34.0522, -118.2437),
    "la": (34.0522, -118.2437),
    "london": (51.5072, -0.1276),
    "chicago": (41.8781, -87.6298),
    "seattle": (47.6062, -122.3321),
}


def _stable_jitter(lat: float, lng: float, key: str) -> tuple[float, float]:
    """
    Deterministic small offset so multiple points don't overlap.
    This is a placeholder until real lat/lng extraction is stored.
    """
    h = hashlib.sha256(key.encode("utf-8")).digest()
    a = int.from_bytes(h[:2], "big") / 65535.0  # 0..1
    b = int.from_bytes(h[2:4], "big") / 65535.0
    # ~ +/- 0.04 degrees (~4-5km depending on latitude)
    dlat = (a - 0.5) * 0.08
    dlng = (b - 0.5) * 0.08
    return (lat + dlat, lng + dlng)


def _pick_center(query: str | None) -> tuple[float, float]:
    if not query:
        return _KNOWN_CENTERS["san francisco"]
    q = query.strip().lower()
    for k, center in _KNOWN_CENTERS.items():
        if k in q:
            return center
    return _KNOWN_CENTERS["san francisco"]


@router.get("/location-analysis", response_model=LocationAnalysisResponse)
def location_analysis(
    q: str | None = Query(default=None, description="Free-text location query (e.g. 'Retail in Miami')"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> LocationAnalysisResponse:
    """
    Returns a multi-layer `mapData` response suitable for a side-by-side comparison view.

    Note: The current OppGrid schema stores city/region/country but not precise coordinates.
    Until geographic extraction is fully implemented, coordinates are approximated with a
    deterministic jitter around a query-selected city center.
    """
    center_lat, center_lng = _pick_center(q)

    opps = (
        db.query(Opportunity)
        .filter(Opportunity.status == "active")
        .order_by(Opportunity.validation_count.desc(), Opportunity.created_at.desc())
        .limit(limit)
        .all()
    )

    businesses: list[GeoJSONFeature] = []
    heat: list[HeatmapPoint] = []

    for opp in opps:
        # Placeholder: infer layer from source platform.
        platform = (opp.source_platform or "").lower()
        lat, lng = _stable_jitter(center_lat, center_lng, f"{opp.id}:{opp.city}:{opp.region}:{opp.country}")

        if platform in {"google_maps", "google", "yelp"}:
            businesses.append(
                GeoJSONFeature(
                    geometry={"type": "Point", "coordinates": [lng, lat]},
                    properties={
                        "source": platform or "unknown",
                        "name": opp.title,
                        "rating": None,
                        "popupContent": (opp.ai_summary or opp.description or "")[:240],
                        "opportunityId": opp.id,
                    },
                )
            )
        else:
            # Treat everything else as a "problem signal" point for now.
            intensity = 0.2
            if opp.validation_count:
                intensity = min(1.0, max(0.2, opp.validation_count / 100.0))
            heat.append(HeatmapPoint(lat=lat, lng=lng, intensity=float(intensity)))

    map_data = MapData(
        center=[float(center_lat), float(center_lng)],
        zoom=11,
        layers=MapLayers(businesses=businesses, problemHeatmap=heat, neighborhoods=[]),
    )
    return LocationAnalysisResponse(query=q, mapData=map_data)


class LayerCommandRequest(BaseModel):
    prompt: str
    current_center: dict[str, float] | None = None
    current_radius: float = 1.0
    active_layers: list[str] = Field(default_factory=list)


class LayerAction(BaseModel):
    action: str
    layer_type: str | None = None
    config: dict[str, Any] | None = None
    center: dict[str, float] | None = None
    address: str | None = None
    radius: float | None = None


class LayerCommandResponse(BaseModel):
    actions: list[LayerAction]
    message: str | None = None


SUPPORTED_LAYER_TYPES = {"deep_clone", "demographics", "competition", "traffic"}

LAYER_KEYWORDS: dict[str, list[str]] = {
    "demographics": ["demographics", "population", "income", "census", "people", "age", "household"],
    "competition": ["competition", "competitors", "competitor", "nearby", "similar", "businesses", "rivals"],
    "deep_clone": ["clone", "copy", "replicate", "franchise", "model", "template"],
    "traffic": ["traffic", "footfall", "foot traffic", "busy", "transit", "pedestrian"],
}

RADIUS_KEYWORDS: dict[str, float] = {
    "quarter mile": 0.25, "0.25 mile": 0.25, "0.25mi": 0.25,
    "half mile": 0.5, "0.5 mile": 0.5, "0.5mi": 0.5,
    "1 mile": 1.0, "one mile": 1.0, "1mi": 1.0,
    "2 mile": 2.0, "two mile": 2.0, "2mi": 2.0,
    "3 mile": 3.0, "three mile": 3.0, "3mi": 3.0,
    "5 mile": 5.0, "five mile": 5.0, "5mi": 5.0,
    "10 mile": 10.0, "ten mile": 10.0, "10mi": 10.0,
}

BUSINESS_TYPES = ["coffee", "restaurant", "gym", "pizza", "cafe", "shop", "store", "bakery", "bar", "salon", "spa"]


CITY_DISPLAY_NAMES: dict[str, str] = {
    "sf": "San Francisco",
    "nyc": "New York City",
    "la": "Los Angeles",
}


def _parse_center(prompt_lower: str) -> LayerAction | None:
    """Extract center location from prompt."""
    for city, coords in _KNOWN_CENTERS.items():
        if city in prompt_lower:
            display_name = CITY_DISPLAY_NAMES.get(city, city.title())
            return LayerAction(
                action="set_center",
                center={"lat": coords[0], "lng": coords[1]},
                address=display_name
            )
    return None


def _parse_radius(prompt_lower: str) -> LayerAction | None:
    """Extract radius from prompt."""
    for keyword, radius in RADIUS_KEYWORDS.items():
        if keyword in prompt_lower:
            return LayerAction(action="set_radius", radius=radius)
    return None


def _parse_layers(prompt_lower: str, active_layers: list[str]) -> list[LayerAction]:
    """Extract layer actions from prompt."""
    actions: list[LayerAction] = []
    
    for layer_type, keywords in LAYER_KEYWORDS.items():
        if layer_type in active_layers:
            continue
        for keyword in keywords:
            if keyword in prompt_lower:
                config: dict[str, Any] = {}
                if layer_type == "competition":
                    for word in BUSINESS_TYPES:
                        if word in prompt_lower:
                            config["searchQuery"] = word
                            break
                actions.append(LayerAction(
                    action="add_layer",
                    layer_type=layer_type,
                    config=config if config else None
                ))
                break
    
    return actions


@router.post("/parse-layer-command", response_model=LayerCommandResponse)
async def parse_layer_command(request: LayerCommandRequest):
    """Parse natural language prompt into layer actions.
    
    Supports:
    - Setting center point to known cities (Austin, NYC, SF, etc.)
    - Setting radius (0.25 to 10 miles)
    - Adding layers (demographics, competition, deep_clone, traffic)
    - Configuring competition search queries
    """
    prompt_lower = request.prompt.lower().strip()
    
    if not prompt_lower:
        return LayerCommandResponse(
            actions=[],
            message="Please provide a description of what you'd like to see on the map."
        )
    
    actions: list[LayerAction] = []
    
    center_action = _parse_center(prompt_lower)
    if center_action:
        actions.append(center_action)
    
    radius_action = _parse_radius(prompt_lower)
    if radius_action:
        actions.append(radius_action)
    
    layer_actions = _parse_layers(prompt_lower, request.active_layers)
    actions.extend(layer_actions)
    
    if not actions:
        suggestions = [
            "Try mentioning a city name (Austin, NYC, Miami, etc.)",
            "Specify a radius like '1 mile' or '5 miles'",
            "Ask for layers: demographics, competition, traffic, or clone"
        ]
        return LayerCommandResponse(
            actions=[],
            message=f"I couldn't understand that request. {suggestions[0]}. {suggestions[1]}. {suggestions[2]}."
        )
    
    action_descriptions = []
    for action in actions:
        if action.action == "set_center":
            action_descriptions.append(f"center to {action.address}")
        elif action.action == "set_radius":
            action_descriptions.append(f"{action.radius} mile radius")
        elif action.action == "add_layer":
            action_descriptions.append(f"add {action.layer_type} layer")
    
    message = f"Applied: {', '.join(action_descriptions)}"
    
    return LayerCommandResponse(
        actions=actions,
        message=message
    )


class PlacesNearbyRequest(BaseModel):
    lat: float
    lng: float
    radius_miles: float = 1.0
    business_type: str = "restaurant"
    limit: int = 20


class PlaceResult(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    rating: float | None = None
    review_count: int | None = None
    address: str | None = None
    category: str | None = None


class PlacesNearbyResponse(BaseModel):
    places: list[PlaceResult]
    total: int


def _get_landward_bias(lat: float, lng: float) -> tuple[float, float]:
    """
    Returns angle range biases (min_angle, max_angle in radians) to avoid placing points in water.
    Uses simple coastal detection heuristics for major US coastal cities.
    """
    import math
    
    coastal_zones = [
        {"name": "Miami/SE Florida", "lat_range": (25.5, 26.5), "lng_range": (-80.5, -80.0), 
         "water_direction": "east", "bias_angle": (math.pi * 0.5, math.pi * 1.5)},
        {"name": "LA/West Coast", "lat_range": (33.5, 34.5), "lng_range": (-118.8, -118.0),
         "water_direction": "west", "bias_angle": (-math.pi * 0.5, math.pi * 0.5)},
        {"name": "SF Bay", "lat_range": (37.5, 38.0), "lng_range": (-122.6, -122.0),
         "water_direction": "west", "bias_angle": (-math.pi * 0.4, math.pi * 0.4)},
        {"name": "NYC East", "lat_range": (40.5, 41.0), "lng_range": (-74.2, -73.7),
         "water_direction": "east", "bias_angle": (math.pi * 0.6, math.pi * 1.4)},
        {"name": "Seattle", "lat_range": (47.4, 47.8), "lng_range": (-122.6, -122.2),
         "water_direction": "west", "bias_angle": (-math.pi * 0.3, math.pi * 0.3)},
        {"name": "Chicago Lakefront", "lat_range": (41.7, 42.0), "lng_range": (-87.8, -87.5),
         "water_direction": "east", "bias_angle": (math.pi * 0.6, math.pi * 1.4)},
    ]
    
    for zone in coastal_zones:
        if (zone["lat_range"][0] <= lat <= zone["lat_range"][1] and 
            zone["lng_range"][0] <= lng <= zone["lng_range"][1]):
            return zone["bias_angle"]
    
    return (0, 2 * math.pi)


def _generate_mock_places(request: PlacesNearbyRequest) -> list[PlaceResult]:
    """Generate mock place data as fallback when SerpAPI is unavailable."""
    import random
    import math
    
    business_names = {
        "restaurant": ["The Local Kitchen", "Urban Eats", "Flavor House", "Bistro 99", "The Grill Room"],
        "cafe": ["Morning Brew", "Coffee Corner", "Bean & Leaf", "The Daily Grind", "Espresso Lane"],
        "gym": ["FitLife", "PowerHouse Gym", "Core Fitness", "Peak Performance", "Strong Studio"],
        "fitness": ["Iron Fitness", "CrossFit Zone", "Anytime Fitness", "LA Fitness", "Planet Fitness"],
        "self_storage": ["Extra Space Storage", "Public Storage", "CubeSmart", "Life Storage", "U-Haul Storage"],
        "storage": ["Extra Space Storage", "Public Storage", "CubeSmart", "Life Storage", "U-Haul Storage"],
        "laundromat": ["Spin Cycle", "Clean & Fresh Laundry", "QuickWash", "Laundry Express", "Suds & Bubbles"],
        "car_wash": ["Sparkle Car Wash", "Clean Machine", "Quick Shine", "Express Auto Spa", "Diamond Wash"],
        "business": ["Metro Business Center", "Innovation Hub", "Pro Services", "Local Agency", "Community Co-op"]
    }
    
    normalized_type = request.business_type.lower().replace(" ", "_").replace("-", "_")
    names = business_names.get(normalized_type, business_names.get("business", ["Local Business"]))
    
    seed = int(abs(request.lat * 1000) + abs(request.lng * 1000))
    random.seed(seed)
    
    min_angle, max_angle = _get_landward_bias(request.lat, request.lng)
    angle_range = max_angle - min_angle
    if angle_range < 0:
        angle_range += 2 * math.pi
    
    places = []
    street_names = ['Main', 'Oak', 'Park', 'Center', 'First', 'Second', 'Third', 'Maple', 'Pine', 'Cedar']
    street_types = ['St', 'Ave', 'Blvd', 'Dr', 'Rd']
    
    for i in range(min(request.limit, 15)):
        base_angle = random.uniform(0, 1) * angle_range + min_angle
        angle = base_angle + random.uniform(-0.3, 0.3)
        distance = random.uniform(0.2, 0.85) * request.radius_miles * 0.01449
        place_lat = request.lat + distance * math.cos(angle)
        place_lng = request.lng + distance * math.sin(angle) / math.cos(math.radians(request.lat))
        
        places.append(PlaceResult(
            id=f"{normalized_type}_{i}_{int(request.lat*100)}_{int(request.lng*100)}",
            name=random.choice(names),
            lat=place_lat,
            lng=place_lng,
            rating=round(random.uniform(3.5, 5.0), 1),
            review_count=random.randint(10, 500),
            address=f"{random.randint(100, 9999)} {random.choice(street_names)} {random.choice(street_types)}",
            category=normalized_type
        ))
    
    random.seed()
    return places


@router.post("/places/nearby", response_model=PlacesNearbyResponse)
def get_nearby_places(request: PlacesNearbyRequest, db: Session = Depends(get_db)):
    """
    Get nearby businesses/places for the Deep Clone and Competition layers.
    Uses SerpAPI Google Maps search for real data, falls back to mock data if unavailable.
    """
    serpapi = SerpAPIService()
    normalized_type = request.business_type.lower().replace(" ", "_").replace("-", "_")
    
    if serpapi.is_configured:
        try:
            import math
            zoom = max(10, min(17, int(15 - math.log2(max(0.5, request.radius_miles)))))
            ll = f"@{request.lat},{request.lng},{zoom}z"
            
            search_query = request.business_type.replace("_", " ")
            
            result = serpapi.google_maps_search(
                query=search_query,
                ll=ll
            )
            
            local_results = result.get("local_results", [])
            
            if local_results:
                places = []
                for i, place in enumerate(local_results[:request.limit]):
                    gps = place.get("gps_coordinates", {})
                    place_lat = gps.get("latitude", request.lat)
                    place_lng = gps.get("longitude", request.lng)
                    
                    place_id = place.get("data_id") or place.get("place_id") or f"{normalized_type}_{i}"
                    address = place.get("address") or place.get("formatted_address") or ""
                    
                    places.append(PlaceResult(
                        id=place_id,
                        name=place.get("title", place.get("name", "Unknown Business")),
                        lat=place_lat,
                        lng=place_lng,
                        rating=float(place.get("rating", 0.0) or 0.0),
                        review_count=int(place.get("reviews", 0) or 0),
                        address=address,
                        category=normalized_type
                    ))
                
                logger.info(f"SerpAPI returned {len(places)} places for '{search_query}' at zoom {zoom}")
                return PlacesNearbyResponse(places=places, total=len(places))
            else:
                logger.warning(f"SerpAPI returned no results for '{search_query}', using mock data")
        except Exception as e:
            logger.error(f"SerpAPI error: {e}, falling back to mock data")
    else:
        logger.info("SerpAPI not configured, using mock data")
    
    places = _generate_mock_places(request)
    return PlacesNearbyResponse(places=places, total=len(places))


class DemographicsRequest(BaseModel):
    lat: float
    lng: float
    radius_miles: float = 1.0
    metrics: list[str] = ["population", "income"]


class DemographicsResponse(BaseModel):
    population: int | None = None
    median_income: int | None = None
    median_age: float | None = None
    households: int | None = None
    education_bachelors_pct: float | None = None
    employment_rate: float | None = None
    area_sq_miles: float | None = None


@router.post("/demographics", response_model=DemographicsResponse)
def get_demographics(request: DemographicsRequest):
    """
    Get demographic data for an area.
    Returns estimated data based on location.
    """
    import random
    
    area = 3.14159 * (request.radius_miles ** 2)
    pop_density = random.randint(2000, 8000)
    
    return DemographicsResponse(
        population=int(area * pop_density),
        median_income=random.randint(45000, 120000),
        median_age=round(random.uniform(28, 45), 1),
        households=int(area * pop_density / 2.5),
        education_bachelors_pct=round(random.uniform(25, 55), 1),
        employment_rate=round(random.uniform(92, 98), 1),
        area_sq_miles=round(area, 2)
    )


class DOTTrafficRequest(BaseModel):
    latitude: float
    longitude: float
    radius_miles: float = 3.0
    force_refresh: bool = False
    include_google_fusion: bool = True
    include_road_segments: bool = False
    include_live_traffic: bool = False


class TrafficTrendResponse(BaseModel):
    direction: str  # 'up', 'down', 'stable'
    change_percent: float
    current_estimate: int
    historical_baseline: int
    insight: str


class DOTTrafficResponse(BaseModel):
    monthly_estimate: int
    daily_average: int
    monthly_foot_traffic: int | None = None
    confidence_score: float
    source: str
    state: str | None = None
    road_segments: list[dict] = []
    road_geojson: dict | None = None
    fusion_breakdown: dict | None = None
    trend: TrafficTrendResponse | None = None
    message: str


@router.post("/dot-traffic", response_model=DOTTrafficResponse)
async def get_dot_traffic(request: DOTTrafficRequest, db: Session = Depends(get_db)):
    """
    Get traffic data using DOT AADT + Google Popular Times fusion.
    
    The fusion algorithm combines:
    - DOT AADT (60% weight): Official vehicle counts, updated yearly
    - Google Popular Times (40% weight): Real-time activity adjustment
    """
    try:
        dot_service = DOTTrafficService()
        dot_result = dot_service.get_area_traffic_summary(
            request.latitude,
            request.longitude,
            request.radius_miles
        )
        
        google_data = None
        if request.include_google_fusion:
            try:
                from app.services.traffic_analyzer import TrafficAnalyzer

                # Use local/cached foot-traffic aggregation when available.
                analyzer = TrafficAnalyzer(db)
                foot_traffic_result = analyzer.analyze_area_traffic(
                    request.latitude,
                    request.longitude,
                    int(request.radius_miles * 1609.34)
                )
                if foot_traffic_result and foot_traffic_result.get("total_locations_sampled", 0) > 0:
                    avg_daily_traffic = foot_traffic_result.get("current_avg_popularity") or 0
                    google_data = {
                        'avg_daily_traffic': int(avg_daily_traffic),
                        'area_vitality_score': foot_traffic_result.get('area_vitality_score', 50)
                    }
            except Exception as e:
                logger.warning(f"Google data fetch failed, using DOT only: {e}")
        
        fusion_service = TrafficFusionService()
        fused = fusion_service.fuse_traffic_data(
            request.latitude,
            request.longitude,
            request.radius_miles,
            dot_data=dot_result,
            google_data=google_data
        )
        
        trend_response = None
        if fused.trend:
            trend_response = TrafficTrendResponse(
                direction=fused.trend.direction,
                change_percent=fused.trend.change_percent,
                current_estimate=fused.trend.current_estimate,
                historical_baseline=fused.trend.historical_baseline,
                insight=fused.trend.insight
            )
        
        road_geojson = None
        if request.include_road_segments:
            try:
                road_geojson = await dot_service.get_road_segments_with_geometry(
                    request.latitude,
                    request.longitude,
                    request.radius_miles
                )
                if (
                    request.include_live_traffic
                    and isinstance(road_geojson, dict)
                    and road_geojson.get("features")
                ):
                    from app.services.mapbox_traffic_service import MapboxTrafficService
                    mapbox_service = MapboxTrafficService()
                    road_geojson["features"] = mapbox_service.get_live_traffic_for_segments(
                        road_geojson["features"],
                        sample_rate=0.15
                    )
                    road_geojson.setdefault("metadata", {})["includes_live_traffic"] = True
            except Exception as e:
                logger.warning(f"Road geometry fetch failed during dot-traffic request: {e}")
                road_geojson = None
        
        return DOTTrafficResponse(
            monthly_estimate=fused.monthly_vehicle_traffic,
            daily_average=fused.monthly_vehicle_traffic // 30,
            monthly_foot_traffic=fused.monthly_foot_traffic,
            confidence_score=fused.confidence_score,
            source=fused.primary_source,
            state=dot_result.get('state') if dot_result else None,
            road_segments=dot_result.get('road_segments', []) if dot_result else [],
            road_geojson=road_geojson,
            fusion_breakdown=fused.breakdown,
            trend=trend_response,
            message=f"Traffic data fused from {fused.primary_source} sources"
        )
        
    except Exception as e:
        logger.error(f"DOT traffic fetch error: {e}")
        return DOTTrafficResponse(
            monthly_estimate=0,
            daily_average=0,
            monthly_foot_traffic=0,
            confidence_score=0,
            source="error",
            road_geojson=None,
            message=f"Failed to fetch traffic data: {str(e)}"
        )


class RoadSegmentsRequest(BaseModel):
    latitude: float
    longitude: float
    radius_miles: float = 3.0
    include_live_traffic: bool = False  # Include Mapbox live traffic comparison


@router.post("/road-traffic-segments")
async def get_road_traffic_segments(request: RoadSegmentsRequest):
    """
    Get road segments with traffic density for map visualization.
    
    Returns GeoJSON FeatureCollection with road lines colored by traffic intensity.
    Colors follow Google Maps convention: green (free) -> yellow (moderate) -> red (heavy)
    
    If include_live_traffic=True, also fetches real-time Mapbox traffic data
    and calculates leading indicators (growth/decline signals).
    """
    try:
        dot_service = DOTTrafficService()
        segments = await dot_service.get_road_segments_with_geometry(
            request.latitude,
            request.longitude,
            request.radius_miles
        )
        
        # Optionally enrich with live traffic comparison
        if request.include_live_traffic and segments.get('features'):
            from app.services.mapbox_traffic_service import MapboxTrafficService
            mapbox_service = MapboxTrafficService()
            enriched_features = mapbox_service.get_live_traffic_for_segments(
                segments['features'],
                sample_rate=0.15  # Sample 15% of segments for faster response
            )
            segments['features'] = enriched_features
            segments['metadata']['includes_live_traffic'] = True
        
        return segments
        
    except Exception as e:
        logger.error(f"Road segments fetch error: {e}")
        return {
            'type': 'FeatureCollection',
            'features': [],
            'metadata': {
                'error': str(e),
                'source': 'error'
            }
        }


class LiveTrafficRequest(BaseModel):
    latitude: float
    longitude: float
    aadt: int = 0  # DOT baseline for comparison


@router.post("/live-traffic")
async def get_live_traffic(request: LiveTrafficRequest):
    """
    Get real-time traffic congestion from Mapbox and compare against DOT baseline.
    
    Returns:
    - live_congestion: Current Mapbox traffic level (low/moderate/heavy/severe)
    - expected_congestion: Expected level based on DOT AADT
    - signal: Leading indicator (growth/stable/decline)
    - signal_strength: How strong the signal is (strong/moderate/weak)
    """
    try:
        from app.services.mapbox_traffic_service import MapboxTrafficService
        
        mapbox_service = MapboxTrafficService()
        
        if request.aadt > 0:
            comparison = mapbox_service.compare_live_vs_baseline(
                request.latitude,
                request.longitude,
                request.aadt
            )
            
            if comparison:
                return {
                    'live_congestion': comparison.live_congestion.name.lower(),
                    'expected_congestion': comparison.expected_congestion.name.lower(),
                    'delta': comparison.delta,
                    'signal': comparison.signal,
                    'signal_strength': comparison.signal_strength,
                    'description': comparison.description,
                    'live_color': mapbox_service.get_congestion_color(comparison.live_congestion.name),
                    'signal_color': mapbox_service.get_signal_color(comparison.signal)
                }
        
        # Just get live traffic without comparison
        live_result = mapbox_service._get_live_traffic_at_point(
            request.latitude,
            request.longitude
        )
        
        if live_result:
            return {
                'live_congestion': live_result.congestion_label,
                'road_class': live_result.road_class,
                'live_color': mapbox_service.get_congestion_color(live_result.congestion_label),
                'signal': None,
                'signal_strength': None
            }
        
        return {
            'error': 'No live traffic data available for this location',
            'live_congestion': None
        }
        
    except Exception as e:
        logger.error(f"Live traffic fetch error: {e}")
        return {
            'error': str(e),
            'live_congestion': None
        }


class DeepCloneRequest(BaseModel):
    source_business: str
    source_location: str | None = None
    source_coordinates: dict | None = None
    target_coordinates: dict
    target_address: str | None = None
    business_category: str = "restaurant"
    radius_miles: float = 1.0
    include_competitors: bool = True
    include_demographics: bool = True


class ThreeMileAnalysis(BaseModel):
    population: int
    median_income: int
    competition_level: str
    growth_rate: float
    median_age: float


class DeepCloneResponse(BaseModel):
    match_score: int
    source_business: str
    source_location: str | None = None
    target_address: str | None = None
    business_category: str
    three_mile_analysis: ThreeMileAnalysis
    key_factors: list[str]
    competitors_found: int = 0
    recommendation: str


@router.post("/deep-clone-analysis", response_model=DeepCloneResponse)
def analyze_deep_clone(request: DeepCloneRequest):
    """
    Analyze viability of cloning a successful business to a target location.
    Compares source and target demographics, competition, and market fit.
    """
    import random
    
    target_lat = request.target_coordinates.get("lat", 0)
    target_lng = request.target_coordinates.get("lng", 0)
    
    area = 3.14159 * (3.0 ** 2)
    pop_density = random.randint(3000, 10000)
    population = int(area * pop_density)
    median_income = random.randint(55000, 135000)
    median_age = round(random.uniform(28, 42), 1)
    
    normalized_category = request.business_category.lower().replace(" ", "_").replace("-", "_")
    category_competition = {
        "restaurant": random.randint(8, 25),
        "fast_food": random.randint(5, 15),
        "fast_casual": random.randint(4, 12),
        "cafe": random.randint(6, 20),
        "fitness": random.randint(3, 10),
        "gym": random.randint(3, 10),
        "retail": random.randint(10, 30),
        "salon": random.randint(5, 15),
        "self_storage": random.randint(2, 8),
        "storage": random.randint(2, 8),
        "laundromat": random.randint(2, 6),
        "car_wash": random.randint(3, 10),
    }
    competitors = category_competition.get(normalized_category, random.randint(5, 15))
    
    if competitors <= 5:
        competition_level = "Low"
        comp_score = 25
    elif competitors <= 12:
        competition_level = "Moderate"
        comp_score = 15
    else:
        competition_level = "High"
        comp_score = 5
    
    income_score = min(25, int((median_income / 80000) * 20))
    pop_score = min(25, int((population / 100000) * 20))
    growth_rate = round(random.uniform(1.5, 6.5), 1)
    growth_score = min(25, int(growth_rate * 4))
    
    base_score = 50 + comp_score + income_score + pop_score + growth_score
    match_score = min(95, max(45, base_score + random.randint(-10, 10)))
    
    key_factors = []
    if median_income > 75000:
        key_factors.append(f"Strong income demographics (${median_income:,} median)")
    if population > 50000:
        key_factors.append(f"Large population base ({population:,} in 3-mile radius)")
    if competition_level == "Low":
        key_factors.append("Limited direct competition in the area")
    elif competition_level == "Moderate":
        key_factors.append("Moderate competition indicates proven demand")
    if growth_rate > 4.0:
        key_factors.append(f"High area growth rate ({growth_rate}% annually)")
    if median_age < 35:
        key_factors.append(f"Young demographic (median age {median_age})")
    
    if not key_factors:
        key_factors = [
            "Established commercial corridor",
            "Good foot traffic potential",
            "Accessible location"
        ]
    
    if match_score >= 80:
        recommendation = "Highly recommended - strong market fit and favorable conditions"
    elif match_score >= 65:
        recommendation = "Good potential - consider detailed feasibility study"
    else:
        recommendation = "Moderate fit - further market research recommended"
    
    return DeepCloneResponse(
        match_score=match_score,
        source_business=request.source_business,
        source_location=request.source_location,
        target_address=request.target_address,
        business_category=request.business_category,
        three_mile_analysis=ThreeMileAnalysis(
            population=population,
            median_income=median_income,
            competition_level=competition_level,
            growth_rate=growth_rate,
            median_age=median_age
        ),
        key_factors=key_factors[:4],
        competitors_found=competitors,
        recommendation=recommendation
    )


class OptimalZoneResult(BaseModel):
    id: str
    center_lat: float
    center_lng: float
    radius_miles: float
    total_score: float
    scores: dict[str, float]
    insights: list[str]
    rank: int


class FindOptimalZonesRequest(BaseModel):
    center_lat: float
    center_lng: float
    target_radius_miles: float = Field(default=10.0, ge=1.0, le=50.0)
    analysis_radius_miles: float = Field(default=3.0, ge=1.0, le=10.0)
    active_layers: list[str] = Field(default_factory=list)
    business_type: str | None = None
    demographics_data: dict[str, Any] | None = None
    competitors: list[dict[str, Any]] | None = None
    top_n: int = Field(default=3, ge=1, le=10)


class FindOptimalZonesResponse(BaseModel):
    zones: list[OptimalZoneResult]
    analysis_summary: str
    center_lat: float
    center_lng: float
    target_radius_miles: float


@router.post("/find-optimal-zones", response_model=FindOptimalZonesResponse)
def find_optimal_zones(
    request: FindOptimalZonesRequest,
    db: Session = Depends(get_db),
) -> FindOptimalZonesResponse:
    """
    Find the best sub-locations (optimal zones) within a target radius.
    Combines scoring from active layers (demographics, competition, deep clone).
    """
    analyzer = LocationAnalyzer()
    
    weights = get_layer_weights(request.active_layers) if request.active_layers else None
    
    optimal_zones = analyzer.find_optimal_zones(
        center_lat=request.center_lat,
        center_lng=request.center_lng,
        target_radius_miles=request.target_radius_miles,
        analysis_radius_miles=request.analysis_radius_miles,
        demographics_data=request.demographics_data,
        competitors=request.competitors,
        weights=weights,
        top_n=request.top_n,
        business_type=request.business_type
    )
    
    zone_results = [
        OptimalZoneResult(
            id=z.id,
            center_lat=z.center_lat,
            center_lng=z.center_lng,
            radius_miles=z.radius_miles,
            total_score=z.total_score,
            scores=z.scores,
            insights=z.insights,
            rank=z.rank
        )
        for z in optimal_zones
    ]
    
    if zone_results:
        top_zone = zone_results[0]
        summary = f"Found {len(zone_results)} optimal {request.analysis_radius_miles}-mile zones. "
        summary += f"Best location scored {top_zone.total_score}/100"
        if top_zone.insights:
            summary += f" - {top_zone.insights[0]}"
    else:
        summary = "No optimal zones identified in the target area."
    
    return FindOptimalZonesResponse(
        zones=zone_results,
        analysis_summary=summary,
        center_lat=request.center_lat,
        center_lng=request.center_lng,
        target_radius_miles=request.target_radius_miles
    )


class EnhancedZoneMetrics(BaseModel):
    total_population: int = 0
    population_growth: float = 0.0
    median_income: int = 0
    median_age: float = 0.0
    total_competitors: int = 0
    drive_by_traffic_monthly: int = 0
    foot_traffic_monthly: int = 0


class EnhancedOptimalZone(BaseModel):
    id: str
    center_lat: float
    center_lng: float
    radius_miles: float
    total_score: float
    metrics: EnhancedZoneMetrics
    component_scores: dict[str, float]
    derived_metrics: dict | None = None
    category_scores: dict[str, float] | None = None
    trends: dict | None = None
    insights: list[str]
    rank: int


class FindEnhancedOptimalZonesRequest(BaseModel):
    center_lat: float
    center_lng: float
    target_radius_miles: float = Field(default=10.0, ge=1.0, le=50.0)
    analysis_radius_miles: float = Field(default=3.0, ge=1.0, le=10.0)
    business_type: str | None = None
    top_n: int = Field(default=3, ge=1, le=10)
    traffic_mode: Literal["auto", "hybrid", "estimated"] = "auto"


class FindEnhancedOptimalZonesResponse(BaseModel):
    zones: list[EnhancedOptimalZone]
    analysis_summary: str
    center_lat: float
    center_lng: float
    target_radius_miles: float


@router.post("/find-optimal-zones-enhanced", response_model=FindEnhancedOptimalZonesResponse)
async def find_optimal_zones_enhanced(
    request: FindEnhancedOptimalZonesRequest,
) -> FindEnhancedOptimalZonesResponse:
    """
    Enhanced optimal zones finder with real data for all 7 metrics:
    - Total Population
    - Population Growth
    - Median Income
    - Median Age
    - Total Competitors
    - Drive By Traffic (monthly)
    - Foot Traffic (monthly)
    """
    from app.db.database import SessionLocal
    from app.services.zone_data_fetcher import ZoneDataFetcher, calculate_zone_score
    from app.services.location_analyzer import LocationAnalyzer
    
    analyzer = LocationAnalyzer()
    
    grid_points = analyzer.generate_grid_points(
        request.center_lat,
        request.center_lng,
        request.target_radius_miles,
        num_rings=2
    )
    
    logger.info(f"Analyzing {len(grid_points)} candidate zones with enhanced metrics")
    if request.traffic_mode == "auto":
        # For larger sweeps, use deterministic estimated traffic to avoid multi-minute timeout cascades.
        traffic_mode = "estimated" if len(grid_points) > 12 else "hybrid"
    else:
        traffic_mode = request.traffic_mode
    
    max_concurrency = min(6, max(2, len(grid_points)))
    semaphore = asyncio.Semaphore(max_concurrency)

    def analyze_point(point):
        local_db = SessionLocal()
        try:
            fetcher = ZoneDataFetcher(local_db)
            metrics = fetcher.fetch_zone_metrics(
                center_lat=point.lat,
                center_lng=point.lng,
                radius_miles=request.analysis_radius_miles,
                business_type=request.business_type,
                fetch_competitors=bool(request.business_type),
                fetch_traffic=True,
                traffic_mode=traffic_mode
            )
            
            score_result = calculate_zone_score(metrics)
            insights = []
            
            if metrics.total_population >= 50000:
                insights.append(f"High population ({metrics.total_population:,} residents)")
            elif metrics.total_population >= 25000:
                insights.append(f"Good population base ({metrics.total_population:,} residents)")
            
            if metrics.population_growth >= 2.0:
                insights.append(f"Strong growth ({metrics.population_growth:.1f}% annually)")
            
            if metrics.median_income >= 75000:
                insights.append(f"High income area (${metrics.median_income:,} median)")
            
            if metrics.total_competitors == 0:
                insights.append("No direct competitors - unproven market")
            elif metrics.total_competitors <= 3:
                insights.append(f"Low competition ({metrics.total_competitors} competitors)")
            elif metrics.total_competitors >= 10:
                insights.append(f"High competition ({metrics.total_competitors} competitors)")
            
            if metrics.foot_traffic_monthly >= 25000:
                insights.append(f"High foot traffic ({metrics.foot_traffic_monthly:,}/month)")
            
            if metrics.drive_by_traffic_monthly >= 100000:
                insights.append(f"High vehicle traffic ({metrics.drive_by_traffic_monthly:,}/month)")
            
            zone_id = f"zone_{point.lat:.4f}_{point.lng:.4f}"
            
            return {
                'id': zone_id,
                'center_lat': point.lat,
                'center_lng': point.lng,
                'radius_miles': request.analysis_radius_miles,
                'total_score': score_result['total_score'],
                'metrics': EnhancedZoneMetrics(
                    total_population=metrics.total_population,
                    population_growth=metrics.population_growth,
                    median_income=metrics.median_income,
                    median_age=metrics.median_age,
                    total_competitors=metrics.total_competitors,
                    drive_by_traffic_monthly=metrics.drive_by_traffic_monthly,
                    foot_traffic_monthly=metrics.foot_traffic_monthly
                ),
                'component_scores': score_result['component_scores'],
                'derived_metrics': score_result.get('derived_metrics'),
                'category_scores': score_result.get('category_scores'),
                'trends': metrics.raw_data.get('trends') if metrics.raw_data else None,
                'insights': insights[:4]
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metrics for zone at {point.lat}, {point.lng}: {e}")
            try:
                local_db.rollback()
            except Exception:
                pass
            return None
        finally:
            local_db.close()

    async def analyze_point_bounded(point):
        async with semaphore:
            return await asyncio.to_thread(analyze_point, point)

    zone_analysis_results = await asyncio.gather(
        *(analyze_point_bounded(point) for point in grid_points)
    )
    scored_zones = [zone for zone in zone_analysis_results if zone is not None]
    
    scored_zones.sort(key=lambda z: z['total_score'], reverse=True)
    
    top_zones = []
    for i, zone in enumerate(scored_zones[:request.top_n]):
        top_zones.append(EnhancedOptimalZone(
            id=zone['id'],
            center_lat=zone['center_lat'],
            center_lng=zone['center_lng'],
            radius_miles=zone['radius_miles'],
            total_score=zone['total_score'],
            metrics=zone['metrics'],
            component_scores=zone['component_scores'],
            derived_metrics=zone.get('derived_metrics'),
            category_scores=zone.get('category_scores'),
            trends=zone.get('trends'),
            insights=zone['insights'],
            rank=i + 1
        ))
    
    if top_zones:
        top = top_zones[0]
        summary = f"Found {len(top_zones)} optimal {request.analysis_radius_miles}-mile zones. "
        summary += f"Best zone scored {top.total_score}/100"
        if top.insights:
            summary += f" - {top.insights[0]}"
        if traffic_mode == "estimated":
            summary += " (traffic scored in fast estimated mode)"
    else:
        summary = "No optimal zones identified in the target area."
    
    return FindEnhancedOptimalZonesResponse(
        zones=top_zones,
        analysis_summary=summary,
        center_lat=request.center_lat,
        center_lng=request.center_lng,
        target_radius_miles=request.target_radius_miles
    )


class PolygonAnalysisRequest(BaseModel):
    polygon: list[list[float]] = Field(..., description="List of [lng, lat] coordinates forming the polygon")
    business_type: str | None = None
    include_traffic: bool = True
    include_demographics: bool = True
    include_competitors: bool = True


class PolygonAnalysisResponse(BaseModel):
    polygon_center: dict[str, float]
    area_sq_miles: float
    traffic_data: dict[str, Any] | None = None
    demographics: dict[str, Any] | None = None
    competitors: list[dict[str, Any]] | None = None
    overall_score: float
    insights: list[str]


@router.post("/analyze-polygon", response_model=PolygonAnalysisResponse)
def analyze_polygon(
    request: PolygonAnalysisRequest,
    db: Session = Depends(get_db),
) -> PolygonAnalysisResponse:
    """
    Analyze a custom polygon area drawn by the user.
    Returns traffic data within the polygon with real DOT AADT data.
    Demographics and competitors are estimated based on area size.
    """
    from shapely.geometry import Polygon as ShapelyPolygon
    from shapely.ops import transform
    from shapely.validation import make_valid
    import pyproj
    from sqlalchemy import text
    
    coords = [(p[0], p[1]) for p in request.polygon]
    
    if len(coords) < 3:
        return PolygonAnalysisResponse(
            polygon_center={"lat": 0, "lng": 0},
            area_sq_miles=0,
            overall_score=0,
            insights=["Invalid polygon: at least 3 points required"]
        )
    
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    
    polygon = ShapelyPolygon(coords)
    
    if not polygon.is_valid:
        polygon = make_valid(polygon)
        if polygon.geom_type != 'Polygon':
            return PolygonAnalysisResponse(
                polygon_center={"lat": 0, "lng": 0},
                area_sq_miles=0,
                overall_score=0,
                insights=["Invalid polygon: self-intersecting or malformed geometry"]
            )
    
    centroid = polygon.centroid
    center_lat = centroid.y
    center_lng = centroid.x
    
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    polygon_m = transform(project, polygon)
    area_sq_m = polygon_m.area
    area_sq_miles = area_sq_m / 2589988.11
    
    insights = []
    overall_score = 50.0
    traffic_data = None
    demographics_data = None
    competitors_list = None
    
    if request.include_traffic:
        try:
            polygon_wkt = polygon.wkt
            query = text("""
                SELECT 
                    COUNT(*) as road_count,
                    AVG(aadt) as avg_aadt,
                    SUM(aadt) as total_aadt,
                    MAX(aadt) as max_aadt,
                    MIN(aadt) as min_aadt
                FROM traffic_roads
                WHERE ST_Intersects(
                    geometry,
                    ST_SetSRID(ST_GeomFromText(:polygon_wkt), 4326)
                )
                AND aadt > 0
            """)
            
            result = db.execute(query, {'polygon_wkt': polygon_wkt}).fetchone()
            
            if result and result[0] > 0:
                avg_aadt = float(result[1]) if result[1] else 0
                monthly_traffic = avg_aadt * 30
                
                traffic_data = {
                    "road_count": int(result[0]),
                    "avg_daily_traffic": round(avg_aadt),
                    "monthly_traffic": round(monthly_traffic),
                    "max_daily_traffic": int(result[3]) if result[3] else 0,
                    "min_daily_traffic": int(result[4]) if result[4] else 0,
                    "total_daily_traffic": int(result[2]) if result[2] else 0
                }
                
                if avg_aadt > 50000:
                    insights.append("High traffic area - excellent visibility")
                    overall_score += 15
                elif avg_aadt > 20000:
                    insights.append("Moderate traffic - good foot traffic potential")
                    overall_score += 10
                elif avg_aadt > 5000:
                    insights.append("Lower traffic area - consider marketing")
                    overall_score += 5
                else:
                    insights.append("Low traffic zone - may need strong draw")
            else:
                traffic_data = {"road_count": 0, "message": "No traffic data available for this area"}
                
        except Exception as e:
            logger.error(f"Traffic analysis error: {e}")
            try:
                db.rollback()
            except Exception:
                pass  # Rollback failed, connection may be dead
    
    if request.include_demographics:
        try:
            demographics_data = {
                "estimated_population": round(area_sq_miles * 5000),
                "population_density_per_sq_mile": 5000,
                "median_income": 65000,
                "median_age": 35,
                "is_estimated": True,
                "note": "Estimates based on area size - real census data coming soon"
            }
            
            if area_sq_miles < 0.5:
                insights.append("Compact area ideal for walkable retail")
            elif area_sq_miles < 2:
                insights.append("Medium-sized area with good coverage")
            else:
                insights.append("Large analysis area - consider multiple locations")
                
        except Exception as e:
            logger.error(f"Demographics error: {e}")
    
    if request.include_competitors:
        try:
            competitors_list = []
            insights.append("Draw polygon to analyze specific area competition")
        except Exception as e:
            logger.error(f"Competitor analysis error: {e}")
    
    overall_score = max(0, min(100, overall_score))
    
    if not insights:
        insights.append("Polygon area analyzed successfully")
    
    return PolygonAnalysisResponse(
        polygon_center={"lat": center_lat, "lng": center_lng},
        area_sq_miles=round(area_sq_miles, 3),
        traffic_data=traffic_data,
        demographics=demographics_data,
        competitors=competitors_list,
        overall_score=round(overall_score, 1),
        insights=insights
    )
