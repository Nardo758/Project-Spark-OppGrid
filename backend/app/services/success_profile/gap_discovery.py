"""
Gap Discovery Engine

Tier B: White-space zone identification using H3 hex grid.
Identifies gaps in the market (low competitor density + viable demographics).
Uses H3 resolution 8 for reliable geographical tiling.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from app.schemas.identify_location import (
    TargetMarket, TargetMarketType, CandidateProfile, CandidateSource, MeasuredSignal
)

logger = logging.getLogger(__name__)

try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    logger.warning("h3 package not available, gap discovery will be limited")


class GapDiscoveryEngine:
    """
    Identifies white-space zones in target market using H3 hex grid.
    Tier B: Finds areas with low competitor density + viable demographics.
    """

    # H3 resolution 8: ~360m-ish hexagon size, good balance of granularity/performance
    H3_RESOLUTION = 8
    
    # Configuration
    MIN_POPULATION_DENSITY = 100  # people per sq mile
    MAX_COMPETITOR_DENSITY = 2  # competitors per 100k population
    MIN_VIABILITY_SCORE = 50.0

    def __init__(self, db=None):
        """Initialize gap discovery engine"""
        self.db = db
        if not H3_AVAILABLE:
            logger.warning("H3 not available - gap discovery limited to basic grid")

    async def discover_gaps(
        self,
        target_market: TargetMarket,
        category: str,
        competitor_data: Optional[List[Dict[str, Any]]] = None,
        demographic_data: Optional[Dict[str, Any]] = None,
    ) -> List[CandidateProfile]:
        """
        Discover white-space gaps in target market.
        
        Process:
        1. Generate H3 hex grid for target market
        2. Score each hex based on:
           - Competitor density (lower is better)
           - Demographic fit
           - Foot traffic potential
        3. Filter to viable gaps (score >= MIN_VIABILITY_SCORE)
        4. Reverse geocode to human-readable names
        5. Convert to CandidateProfile
        """
        try:
            if not H3_AVAILABLE:
                logger.warning("H3 not available, returning empty gap list")
                return []
            
            # Get hex cells for target market
            hex_cells = self._generate_hex_grid(target_market)
            logger.info(f"Generated {len(hex_cells)} hex cells for gap discovery")
            
            # Score each hex
            scored_cells = await self._score_hex_cells(
                hex_cells, category, competitor_data, demographic_data
            )
            logger.info(f"Scored {len(scored_cells)} hex cells")
            
            # Filter to viable gaps
            gaps = [c for c in scored_cells if c["viability_score"] >= self.MIN_VIABILITY_SCORE]
            logger.info(f"Found {len(gaps)} viable gaps")
            
            # Convert to candidates
            candidates = await self._gaps_to_candidates(gaps, category)
            return candidates
        
        except Exception as e:
            logger.error(f"Error in gap discovery: {e}")
            return []

    def _generate_hex_grid(self, target_market: TargetMarket) -> List[str]:
        """
        Generate H3 hex cells for target market.
        Returns list of hex cell IDs at resolution 8.
        """
        try:
            if target_market.market_type == TargetMarketType.METRO:
                # For metro, use approximate bounds
                lat, lng, radius = self._get_metro_bounds(target_market.metro, target_market.state)
            elif target_market.market_type == TargetMarketType.CITY:
                # For city, similar bounds
                lat, lng, radius = self._get_city_bounds(target_market.city, target_market.state)
            else:  # POINT_RADIUS
                lat = target_market.latitude
                lng = target_market.longitude
                radius = target_market.radius_miles
            
            # Convert radius miles to degrees (rough: 1 degree ≈ 69 miles)
            radius_degrees = radius / 69.0
            
            # Generate grid
            hex_cells = []
            if H3_AVAILABLE:
                # Create a disk of hexagons around center point
                center_hex = h3.latlng_to_h3(lat, lng, self.H3_RESOLUTION)
                hex_cells = h3.k_ring(center_hex, k=8)  # Radius of 8 rings
            
            return list(hex_cells) if hex_cells else []
        
        except Exception as e:
            logger.error(f"Error generating hex grid: {e}")
            return []

    async def _score_hex_cells(
        self,
        hex_cells: List[str],
        category: str,
        competitor_data: Optional[List[Dict[str, Any]]] = None,
        demographic_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Score each hex cell based on viability.
        Score = (100 - competitor_density) + demographic_fit + foot_traffic_potential
        """
        scored = []
        
        for hex_cell in hex_cells:
            try:
                # Get center of hex
                if H3_AVAILABLE:
                    lat, lng = h3.h3_to_latlng(hex_cell)
                else:
                    lat, lng = 0, 0  # Fallback
                
                # Score components
                competitor_score = self._score_competitors(hex_cell, competitor_data)
                demographic_score = self._score_demographics(hex_cell, demographic_data)
                foot_traffic_score = self._score_foot_traffic(hex_cell)
                
                # Weighted average
                overall_score = (
                    competitor_score * 0.4 +  # Competition is critical
                    demographic_score * 0.4 +
                    foot_traffic_score * 0.2
                )
                
                scored.append({
                    "hex_id": hex_cell,
                    "latitude": lat,
                    "longitude": lng,
                    "competitor_score": competitor_score,
                    "demographic_score": demographic_score,
                    "foot_traffic_score": foot_traffic_score,
                    "viability_score": overall_score,
                })
            except Exception as e:
                logger.warning(f"Error scoring hex {hex_cell}: {e}")
                continue
        
        # Sort by viability score (descending)
        scored.sort(key=lambda x: x["viability_score"], reverse=True)
        return scored

    def _score_competitors(
        self,
        hex_cell: str,
        competitor_data: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """
        Score based on competitor density in this hex.
        Lower competitor density = higher score.
        """
        if not competitor_data:
            return 50.0  # Neutral if no data
        
        try:
            # Count competitors in this hex (simplified: using lat/lng proximity)
            if H3_AVAILABLE:
                hex_bounds = h3.h3_to_geo_boundary(hex_cell)
            else:
                return 50.0
            
            count = 0
            for comp in competitor_data:
                if self._is_point_in_hex(comp.get("lat"), comp.get("lng"), hex_cell):
                    count += 1
            
            # Score: fewer competitors = higher score
            # Max 10 competitors per hex = 0 score, 0 competitors = 100 score
            competitor_score = max(0, 100 - (count * 10))
            return competitor_score
        except Exception as e:
            logger.warning(f"Error scoring competitors: {e}")
            return 50.0

    def _score_demographics(
        self,
        hex_cell: str,
        demographic_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score based on demographic viability.
        """
        if not demographic_data:
            return 50.0  # Neutral if no data
        
        try:
            # For now, simple scoring based on population density
            # In production, would use detailed demographic API
            pop_density = demographic_data.get("population_density", 500)
            
            if pop_density < self.MIN_POPULATION_DENSITY:
                return 20.0  # Too sparse
            elif pop_density > 5000:
                return 80.0  # High density, good
            else:
                # Scale between 20-80
                return 20 + ((pop_density - self.MIN_POPULATION_DENSITY) / (5000 - self.MIN_POPULATION_DENSITY)) * 60
        except Exception as e:
            logger.warning(f"Error scoring demographics: {e}")
            return 50.0

    def _score_foot_traffic(self, hex_cell: str) -> float:
        """
        Score based on foot traffic potential.
        In production, would use foot traffic APIs.
        For now, use demographic density as proxy.
        """
        # Placeholder: return moderate score
        return 60.0

    def _is_point_in_hex(self, lat: float, lng: float, hex_cell: str) -> bool:
        """Check if a point is in a hex cell"""
        try:
            if not H3_AVAILABLE:
                return False
            point_hex = h3.latlng_to_h3(lat, lng, self.H3_RESOLUTION)
            return point_hex == hex_cell
        except:
            return False

    def _get_metro_bounds(self, metro: str, state: str) -> Tuple[float, float, float]:
        """Get approximate center and radius for metro"""
        metro_data = {
            ("Miami", "FL"): (25.7617, -80.1918, 15),
            ("Atlanta", "GA"): (33.7490, -84.3880, 18),
            ("Orlando", "FL"): (28.5421, -81.3723, 12),
            ("Tampa", "FL"): (27.9506, -82.4693, 10),
            ("New York", "NY"): (40.7128, -74.0060, 20),
            ("Los Angeles", "CA"): (34.0522, -118.2437, 20),
            ("Houston", "TX"): (29.7604, -95.3698, 15),
            ("Dallas", "TX"): (32.7767, -96.7970, 15),
            ("Chicago", "IL"): (41.8781, -87.6298, 18),
            ("Austin", "TX"): (30.2672, -97.7431, 10),
        }
        return metro_data.get((metro, state), (25.7617, -80.1918, 15))

    def _get_city_bounds(self, city: str, state: str) -> Tuple[float, float, float]:
        """Get approximate center and radius for city"""
        # For simplicity, use metro bounds
        return self._get_metro_bounds(city, state)

    async def _gaps_to_candidates(
        self,
        gaps: List[Dict[str, Any]],
        category: str
    ) -> List[CandidateProfile]:
        """
        Convert gap hexes to candidate profiles.
        Includes reverse geocoding to human-readable location names.
        """
        candidates = []
        
        for idx, gap in enumerate(gaps):
            try:
                # Reverse geocode to get location name
                location_name = await self._reverse_geocode(gap["latitude"], gap["longitude"])
                
                candidate_id = f"gap_{gap['hex_id']}_{category}"
                
                # Create measured signals from scores
                measured_signals = [
                    MeasuredSignal(
                        signal_name="competitor_density",
                        signal_value=gap["competitor_score"],
                        percentile_rank=80,
                        confidence=0.7,
                        data_source="h3_grid_analysis"
                    ),
                    MeasuredSignal(
                        signal_name="demographic_fit",
                        signal_value=gap["demographic_score"],
                        percentile_rank=70,
                        confidence=0.6,
                        data_source="census_data"
                    ),
                    MeasuredSignal(
                        signal_name="foot_traffic_potential",
                        signal_value=gap["foot_traffic_score"],
                        percentile_rank=60,
                        confidence=0.5,
                        data_source="foot_traffic_model"
                    ),
                ]
                
                # Determine archetype from viability score
                if gap["viability_score"] >= 80:
                    archetype = "pioneer"
                elif gap["viability_score"] >= 65:
                    archetype = "mainstream"
                else:
                    archetype = "specialist"
                
                candidate = CandidateProfile(
                    candidate_id=candidate_id,
                    location_name=location_name,
                    latitude=gap["latitude"],
                    longitude=gap["longitude"],
                    archetype=archetype,
                    archetype_confidence=0.70,
                    archetype_rationale=f"Gap discovered via H3 hex grid analysis with viability score {gap['viability_score']:.1f}",
                    risk_factors=["Emerging market", "Requires validation", "Less established"],
                    measured_signals=measured_signals,
                    source=CandidateSource.GAP_DISCOVERY,
                    source_id=gap["hex_id"],
                    zip_code=None,
                    neighborhood=location_name,
                    city="Unknown",
                    state="XX",
                    overall_score=gap["viability_score"]
                )
                candidates.append(candidate)
            
            except Exception as e:
                logger.warning(f"Error converting gap to candidate: {e}")
                continue
        
        return candidates

    async def _reverse_geocode(self, latitude: float, longitude: float) -> str:
        """
        Reverse geocode a lat/lng to human-readable location name.
        Uses a simple approach; in production would use GeoCoding API.
        """
        try:
            # Simple placeholder: would call Google Maps Geocoding API
            # For now, return a generic name
            return f"Location ({latitude:.4f}, {longitude:.4f})"
        except Exception as e:
            logger.warning(f"Error reverse geocoding: {e}")
            return f"Location ({latitude:.4f}, {longitude:.4f})"
