"""
Micro Market Model

Stores curated named micro-markets (Tier A) for location identification.
Each metro has 5-15 named markets with polygon boundaries.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Index, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class MicroMarket(Base):
    """
    Curated named micro-markets for top metros.
    Tier A: Named markets with polygon geometries.
    
    Examples:
    - Miami: Brickell, Wynwood, Calle Ocho, Coral Gables, etc.
    - NYC: SoHo, East Village, Upper West Side, Brooklyn, etc.
    """
    
    __tablename__ = "micro_markets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Market identification
    market_name = Column(String(255), nullable=False, index=True)
    metro = Column(String(100), nullable=False, index=True)  # e.g., "Miami", "NYC", "LA"
    state = Column(String(2), nullable=False, index=True)    # State abbreviation
    
    # Geometry (PostGIS would be ideal, but storing as JSON for simplicity)
    # Format: GeoJSON Polygon feature
    polygon_geojson = Column(JSON, nullable=False, description="GeoJSON Polygon geometry")
    
    # Center point for quick reference
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    demographic_profile = Column(Text, nullable=True)  # JSON
    typical_archetypes = Column(Text, nullable=True)   # JSON array of archetype enums
    
    # Viability signals (cached from analysis)
    avg_foot_traffic = Column(Integer, nullable=True)
    avg_demographic_fit = Column(Float, nullable=True)  # 0-1
    avg_competition_density = Column(Float, nullable=True)  # 0-1
    
    # Control
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("ix_micro_market_metro_state", "metro", "state"),
        Index("ix_micro_market_name", "market_name"),
    )


class SuccessProfile(Base):
    """
    Success Profile: A candidate location promoted by the user.
    Created when user promotes a candidate from identify_location result.
    """
    
    __tablename__ = "success_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to user
    user_id = Column(Integer, nullable=False, index=True)
    
    # Original identification
    request_id = Column(String(100), nullable=False, index=True)  # Reference to IdentifyLocationResult
    candidate_id = Column(String(100), nullable=False)  # Original candidate ID
    
    # Business info
    category = Column(String(100), nullable=False)
    business_description = Column(Text, nullable=True)
    
    # Location
    location_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    zip_code = Column(String(10), nullable=True)
    neighborhood = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    
    # Classification
    archetype = Column(String(50), nullable=False)  # e.g., "pioneer", "mainstream"
    archetype_confidence = Column(Float, nullable=False)  # 0-1
    
    # Profile data (full candidate profile as JSON)
    candidate_profile = Column(JSON, nullable=False)  # Full CandidateProfile serialized
    
    # User notes
    user_notes = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="active")  # active, archived, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    promoted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index("ix_success_profile_user_id", "user_id"),
        Index("ix_success_profile_request_id", "request_id"),
        Index("ix_success_profile_category", "category"),
    )


class IdentifyLocationCache(Base):
    """
    Cache for identify_location results (7-day TTL).
    Keyed by (category, target_market_spec, market_boundary).
    """
    
    __tablename__ = "identify_location_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Cache key
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    
    # Request details
    category = Column(String(100), nullable=False)
    target_market = Column(JSON, nullable=False)  # TargetMarket spec
    market_boundary = Column(JSON, nullable=True)
    
    # Result (full IdentifyLocationResult as JSON)
    result = Column(JSON, nullable=False)
    
    # Metadata
    hit_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 7 days from creation
    
    # Indexes
    __table_args__ = (
        Index("ix_cache_category", "category"),
        Index("ix_cache_expires_at", "expires_at"),
    )
