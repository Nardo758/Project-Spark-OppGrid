"""
Identify Location Service Schemas

Comprehensive data models for the Success Profile System's location identification and candidate discovery.
Supports Tier A (named micro-markets) and Tier B (gap discovery) with archetype-based grouping.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# Import supply metrics if available
try:
    from app.services.municipal_data.schemas import (
        FacilitySupplyMetrics,
        SupplyVerdict,
    )
    SUPPLY_METRICS_AVAILABLE = True
except ImportError:
    SUPPLY_METRICS_AVAILABLE = False
    # Define minimal stubs if imports fail
    class SupplyVerdict(str, Enum):
        OVERSATURATED = "oversaturated"
        BALANCED = "balanced"
        UNDERSATURATED = "undersaturated"
    
    FacilitySupplyMetrics = None


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class TargetMarketType(str, Enum):
    """Type of target market specification"""
    METRO = "metro"  # e.g., "Miami, FL"
    CITY = "city"    # e.g., "Miami"
    POINT_RADIUS = "point_radius"  # Lat/lng + radius in miles


class MarketBoundaryType(str, Enum):
    """Type of market boundary filter"""
    ZIP_CODE = "zip_code"
    NEIGHBORHOOD = "neighborhood"
    POLYGON = "polygon"
    CITY = "city"


class ArchetypeType(str, Enum):
    """Business archetype classifications"""
    PIONEER = "pioneer"          # Early-stage, emerging trend
    MAINSTREAM = "mainstream"     # Established, high-volume potential
    SPECIALIST = "specialist"     # Niche, high-margin play
    ANCHOR = "anchor"            # Destination-driver, unique
    EXPERIMENTAL = "experimental" # Test market, lower viability


class CandidateSource(str, Enum):
    """Where a candidate location came from"""
    NAMED_MARKET = "named_market"  # Tier A: curated micro-market
    GAP_DISCOVERY = "gap_discovery"  # Tier B: H3 hex grid white-space


class CandidateStatus(str, Enum):
    """Status of a candidate location"""
    IDENTIFIED = "identified"        # Found by discovery engine
    PROFILED = "profiled"           # Measured and classified
    RANKED = "ranked"               # Filtered and ranked
    PROMOTED = "promoted"           # Converted to SuccessProfile


class UserTier(str, Enum):
    """User subscription tier"""
    FREE = "free"           # 1/month, named only, top 3/archetype
    BUILDER = "builder"     # 5/month, with gaps, top 5/archetype
    SCALER = "scaler"       # 25/month, with gaps, unlimited
    ENTERPRISE = "enterprise"  # Unlimited


# ─────────────────────────────────────────────────────────────────────────────
# MARKET SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────

class TargetMarket(BaseModel):
    """Target market specification (metro, city, or point+radius)"""
    market_type: TargetMarketType = Field(..., description="Type of market specification")
    metro: Optional[str] = Field(None, description="Metro name (e.g., 'Miami')")
    city: Optional[str] = Field(None, description="City name (e.g., 'Miami')")
    state: Optional[str] = Field(None, description="State abbreviation (e.g., 'FL')")
    latitude: Optional[float] = Field(None, description="Center point latitude (for point_radius)")
    longitude: Optional[float] = Field(None, description="Center point longitude (for point_radius)")
    radius_miles: Optional[float] = Field(default=5.0, ge=0.5, le=50, description="Search radius in miles")


class MarketBoundary(BaseModel):
    """Optional market boundary filters"""
    boundary_type: MarketBoundaryType = Field(..., description="Type of boundary")
    zip_codes: Optional[List[str]] = Field(None, description="ZIP codes to include/exclude")
    neighborhoods: Optional[List[str]] = Field(None, description="Neighborhood names")
    polygon_geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon for custom boundary")


# ─────────────────────────────────────────────────────────────────────────────
# CANDIDATE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

class MeasuredSignal(BaseModel):
    """A single measured signal for candidate classification"""
    signal_name: str = Field(..., description="Name of the signal (e.g., 'foot_traffic_growth')")
    signal_value: float = Field(..., description="Measured value")
    percentile_rank: Optional[int] = Field(None, description="Percentile within category (0-100)")
    confidence: float = Field(default=0.85, description="Confidence in measurement (0-1)")
    data_source: str = Field(..., description="Where data came from (e.g., 'foot_traffic_api', 'census')")


class CandidateProfile(BaseModel):
    """Lightweight measured profile per candidate location"""
    candidate_id: str = Field(..., description="Unique candidate identifier")
    location_name: str = Field(..., description="Human-readable location name (e.g., 'Brickell, Miami')")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    
    # Classification
    archetype: ArchetypeType = Field(..., description="Classified archetype")
    archetype_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in archetype (0-1)")
    archetype_rationale: str = Field(..., description="Why this archetype was assigned")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    
    # Measured signals (3 signals: foot_traffic, demographic_fit, competition_density)
    measured_signals: List[MeasuredSignal] = Field(..., description="3 signals for candidate classification")
    
    # Source & metadata
    source: CandidateSource = Field(..., description="Where candidate came from")
    source_id: Optional[str] = Field(None, description="ID in source system (e.g., H3 hex index)")
    
    # Market context
    zip_code: Optional[str] = Field(None)
    neighborhood: Optional[str] = Field(None)
    city: str = Field(...)
    state: str = Field(...)
    
    # Scoring
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall viability score")
    
    # Supply Analysis (NEW)
    supply_verdict: Optional[str] = Field(None, description="Supply verdict (oversaturated/balanced/undersaturated)")
    supply_metrics: Optional[Dict[str, Any]] = Field(None, description="Supply metrics from municipal data")
    supply_score_adjustment: Optional[float] = Field(None, ge=0.5, le=1.5, description="Score multiplier based on supply (0.75 for oversaturated, 1.25 for undersaturated)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArchetypeGroup(BaseModel):
    """Candidates grouped by archetype"""
    archetype: ArchetypeType = Field(..., description="Archetype name")
    archetype_description: str = Field(..., description="Brief description of this archetype")
    candidate_count: int = Field(..., ge=0, description="Number of candidates in this group")
    candidates: List[CandidateProfile] = Field(..., description="List of candidates in this group")
    avg_score: float = Field(..., ge=0.0, le=100.0, description="Average viability score")
    score_range: Dict[str, float] = Field(..., description="Score range {'min': ..., 'max': ...}")


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST/RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class BenchmarkSummary(BaseModel):
    """
    Public-safe benchmark summary (NO sensitive data).
    Must NOT include: tickers, SEC refs, raw thresholds, margins, revenue data.
    Only safe fields: category, typical_archetypes, total_addressable_population.
    """
    category: str = Field(..., description="Business category")
    typical_archetypes: List[str] = Field(..., description="Typical archetypes for this category")
    total_addressable_population: int = Field(..., description="Estimated TAM population")


class IdentifyLocationRequest(BaseModel):
    """Main API request for location identification"""
    # Business definition
    category: str = Field(..., min_length=3, max_length=100, description="Business category (e.g., 'coffee_shop_premium')")
    business_description: Optional[str] = Field(None, max_length=500, description="Additional business context")
    
    # Market specification
    target_market: TargetMarket = Field(..., description="Target market specification")
    market_boundary: Optional[MarketBoundary] = Field(None, description="Optional boundary filters")
    
    # Filters
    archetype_preference: Optional[List[ArchetypeType]] = Field(None, description="Preferred archetypes to prioritize")
    include_gap_discovery: bool = Field(default=True, description="Include Tier B gap discovery (if tier allows)")
    
    # Session
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class IdentifyLocationResult(BaseModel):
    """Main API response with discovered candidates"""
    # Request echo
    request_id: str = Field(..., description="Unique request ID for caching/retrieval")
    category: str = Field(..., description="Business category analyzed")
    
    # Benchmark info (public-safe only)
    benchmark_summary: Optional[BenchmarkSummary] = Field(None, description="Category benchmark (sanitized)")
    
    # Market info
    target_market: TargetMarket = Field(..., description="Market analyzed")
    
    # Results
    candidates_by_archetype: List[ArchetypeGroup] = Field(..., description="Candidates grouped by archetype")
    total_candidates: int = Field(..., ge=0, description="Total number of candidates found")
    
    # Tier info
    tier: UserTier = Field(..., description="User tier (determines limits)")
    candidates_shown: int = Field(..., description="Number of candidates shown to user")
    candidates_limited: bool = Field(..., description="True if tier limited the candidate count")
    
    # Data quality
    data_quality: Dict[str, Any] = Field(default_factory=dict, description="Data source quality info")
    
    # GeoJSON map data
    map_data: Dict[str, Any] = Field(..., description="GeoJSON FeatureCollection for map visualization")
    
    # Metadata
    processing_time_ms: int = Field(..., ge=0, description="Request processing time in ms")
    from_cache: bool = Field(default=False, description="True if result was from cache")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Analysis metadata
    named_markets_included: bool = Field(..., description="True if Tier A markets were included")
    gap_markets_included: bool = Field(..., description="True if Tier B gap markets were included")


# ─────────────────────────────────────────────────────────────────────────────
# DETAIL VIEWS
# ─────────────────────────────────────────────────────────────────────────────

class CandidateDetailResponse(BaseModel):
    """Detailed view of a single candidate"""
    candidate: CandidateProfile = Field(..., description="Full candidate profile")
    
    # Additional enrichment
    demographics: Optional[Dict[str, Any]] = Field(None, description="Demographic data")
    local_competition: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby competitors")
    foot_traffic_trend: Optional[Dict[str, Any]] = Field(None, description="Foot traffic trajectory")
    
    # Risk assessment
    risk_summary: Optional[str] = Field(None, description="Natural language risk summary")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# PROMOTION (Candidate → SuccessProfile)
# ─────────────────────────────────────────────────────────────────────────────

class PromoteCandidateRequest(BaseModel):
    """Request to convert candidate to SuccessProfile"""
    notes: Optional[str] = Field(None, max_length=500, description="User notes for the profile")


class PromoteCandidateResponse(BaseModel):
    """Response after promoting candidate to SuccessProfile"""
    success: bool = Field(..., description="Success indicator")
    success_profile_id: Optional[str] = Field(None, description="New SuccessProfile ID")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
