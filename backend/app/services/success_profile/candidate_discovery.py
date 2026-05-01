"""
Candidate Discovery Module

Combines Tier A (named micro-markets) and Tier B (gap discovery) to find candidates.
Handles merging, filtering, and candidate lifecycle.
"""

import logging
from typing import List, Dict, Any, Optional

from app.schemas.identify_location import (
    TargetMarket, MarketBoundary, CandidateProfile, CandidateSource
)

logger = logging.getLogger(__name__)


class CandidateDiscoveryEngine:
    """Orchestrates candidate discovery across Tier A and Tier B"""
    
    def __init__(self, micro_market_catalog, gap_discovery_engine):
        self.catalog = micro_market_catalog
        self.gap_engine = gap_discovery_engine
    
    def discover_candidates(
        self,
        target_market: TargetMarket,
        category: str,
        include_gaps: bool = True,
        market_boundary: Optional[MarketBoundary] = None,
    ) -> List[CandidateProfile]:
        """
        Discover candidates from both Tier A and Tier B sources.
        """
        candidates = []
        
        # Tier A: Named markets (always try)
        try:
            named_candidates = self._discover_tier_a(target_market, market_boundary)
            candidates.extend(named_candidates)
            logger.info(f"Discovered {len(named_candidates)} Tier A candidates")
        except Exception as e:
            logger.error(f"Error in Tier A discovery: {e}")
        
        # Tier B: Gaps (if enabled and available)
        if include_gaps:
            try:
                gap_candidates = self._discover_tier_b(target_market, category)
                
                # Named takes precedence: remove overlapping gaps
                gap_candidates = self._remove_overlapping_gaps(
                    gap_candidates, candidates
                )
                
                candidates.extend(gap_candidates)
                logger.info(f"Discovered {len(gap_candidates)} Tier B candidates after deduplication")
            except Exception as e:
                logger.error(f"Error in Tier B discovery: {e}")
        
        return candidates
    
    def _discover_tier_a(
        self,
        target_market: TargetMarket,
        market_boundary: Optional[MarketBoundary] = None,
    ) -> List[CandidateProfile]:
        """Discover Tier A named markets"""
        # Implementation would use catalog service
        return []  # Placeholder
    
    def _discover_tier_b(
        self,
        target_market: TargetMarket,
        category: str,
    ) -> List[CandidateProfile]:
        """Discover Tier B gaps"""
        # Implementation would use gap discovery engine
        return []  # Placeholder
    
    def _remove_overlapping_gaps(
        self,
        gaps: List[CandidateProfile],
        named: List[CandidateProfile],
        overlap_threshold_km: float = 2.0,
    ) -> List[CandidateProfile]:
        """
        Remove gap candidates that overlap with named markets.
        Named markets take precedence.
        """
        from math import radians, cos, sin, asin, sqrt
        
        filtered_gaps = []
        
        for gap in gaps:
            is_overlapping = False
            
            for named in named:
                # Calculate distance between gap and named market
                distance_km = self._haversine_distance(
                    gap.latitude, gap.longitude,
                    named.latitude, named.longitude
                )
                
                if distance_km <= overlap_threshold_km:
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_gaps.append(gap)
        
        return filtered_gaps
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km"""
        from math import radians, cos, sin, asin, sqrt
        
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth's radius in km
        
        return c * r
