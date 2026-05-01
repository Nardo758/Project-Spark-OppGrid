"""
Pydantic schemas for Municipal Data API Client.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class SupplyVerdict(str, Enum):
    """Supply verdict based on sq ft per capita comparison"""
    OVERSATURATED = "oversaturated"  # > 7.0 sq ft per capita
    BALANCED = "balanced"  # 5.0-7.0 sq ft per capita
    UNDERSATURATED = "undersaturated"  # < 5.0 sq ft per capita
    UNKNOWN = "unknown"  # Insufficient data


class FacilitySupplyMetrics(BaseModel):
    """Core supply metrics for a facility type in a metro"""
    
    metro: str = Field(..., description="Metro identifier (e.g., 'Miami', 'Chicago')")
    state: str = Field(..., description="State code (e.g., 'FL', 'IL')")
    industry: str = Field(..., description="Industry code (e.g., 'self-storage')")
    
    # Raw data
    total_facilities: int = Field(..., description="Total number of facilities found")
    total_building_sqft: int = Field(..., description="Sum of all building square footage")
    population: int = Field(..., description="Metro population from Census")
    
    # Calculated metrics
    sqft_per_capita: float = Field(..., description="Building sq ft / population")
    facilities_per_100k_population: float = Field(
        ..., 
        description="(Total facilities / population) * 100,000"
    )
    
    # Verdict
    verdict: SupplyVerdict = Field(..., description="Supply level verdict")
    benchmark_sqft_per_capita: float = Field(
        default=7.0,
        description="Benchmark for comparison (7.0 is typical for self-storage)"
    )
    
    # Data quality
    confidence: float = Field(
        default=0.95,
        description="Confidence score (0.95 for Socrata, 0.60 for fallback)"
    )
    data_source: str = Field(
        default="socrata",
        description="Source of data (socrata, census, fallback)"
    )
    coverage_percentage: float = Field(
        default=100.0,
        description="Estimated % of parcels covered by query"
    )
    
    # Metadata
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this data was fetched/cached"
    )
    cache_key: Optional[str] = Field(
        default=None,
        description="Cache key if this result was cached"
    )
    query_time_ms: Optional[int] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )
    
    class Config:
        use_enum_values = True


class MunicipalQueryResult(BaseModel):
    """Result of a municipal data query"""
    
    success: bool = Field(..., description="Whether query was successful")
    metro: str
    state: str
    industry: str
    
    # Results
    metrics: Optional[FacilitySupplyMetrics] = Field(
        default=None,
        description="Supply metrics if successful"
    )
    
    # Error handling
    error: Optional[str] = Field(
        default=None,
        description="Error message if unsuccessful"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback data was used"
    )
    
    # Metadata
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )


class CensusPopulationData(BaseModel):
    """Census population data for a metro"""
    
    metro: str
    state: str
    population: int
    last_updated: str = Field(default="2020", description="Census year")
    
    class Config:
        use_enum_values = True


class SocrataEndpoint(BaseModel):
    """Configuration for a Socrata endpoint"""
    
    metro: str = Field(..., description="Metro name")
    state: str = Field(..., description="State code")
    base_url: str = Field(..., description="Base URL for Socrata API")
    dataset_id: Optional[str] = Field(
        default=None,
        description="Dataset ID for self-storage (if known)"
    )
    land_use_field: str = Field(
        default="land_use_code",
        description="Field name for land use codes"
    )
    sqft_field: str = Field(
        default="building_square_feet",
        description="Field name for building square footage"
    )
    
    class Config:
        use_enum_values = True


class CacheEntry(BaseModel):
    """Cache entry metadata"""
    
    key: str
    metro: str
    industry: str
    data: FacilitySupplyMetrics
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    
    class Config:
        use_enum_values = True


class LandUseMappingEntry(BaseModel):
    """Single entry in land use mapping"""
    
    metro: str
    industry: str
    land_use_codes: List[str] = Field(
        ...,
        description="List of land use codes for this industry"
    )
    data_source: str = Field(
        default="municipal_docs",
        description="Source of the mapping"
    )
    verified: bool = Field(
        default=False,
        description="Whether this mapping has been verified"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about this mapping"
    )


class Parcel(BaseModel):
    """
    Represents a single property parcel — either from Socrata (authoritative)
    or estimated from a SerpAPI fallback search result.
    """
    facility_name: str = Field(..., description="Name of the facility/business")
    address: str = Field(default="", description="Street address or URL")
    building_sqft: int = Field(default=0, description="Estimated or actual building sq ft")
    land_sqft: Optional[float] = Field(default=None, description="Lot/parcel sq ft (if available)")
    parcel_id: str = Field(default="", description="Parcel or record identifier")
    source: str = Field(default="unknown", description="Data source (socrata, serpapi_fallback, etc.)")
    data_quality: str = Field(default="estimated", description="'verified' or 'estimated'")
    confidence: float = Field(default=0.60, ge=0.0, le=1.0, description="Confidence score for this record")

    class Config:
        use_enum_values = True
