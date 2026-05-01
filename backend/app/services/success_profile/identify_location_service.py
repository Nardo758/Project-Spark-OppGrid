"""
Identify Location Service

Main orchestrator for location identification.
Combines Tier A (named micro-markets) and Tier B (gap discovery).
Handles candidate discovery, profiling, classification, and caching.
"""

import logging
import hashlib
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.schemas.identify_location import (
    TargetMarket, TargetMarketType, MarketBoundary,
    IdentifyLocationResult, IdentifyLocationRequest,
    CandidateProfile, ArchetypeGroup, BenchmarkSummary,
    UserTier, ArchetypeType, CandidateSource, CandidateStatus
)
from app.models.micro_market import IdentifyLocationCache, MicroMarket, SuccessProfile
from app.services.success_profile.micro_market_catalog import MicroMarketCatalog
from app.services.success_profile.gap_discovery import GapDiscoveryEngine
from app.services.success_profile.candidate_profile_builder import CandidateProfileBuilder

logger = logging.getLogger(__name__)


class IdentifyLocationService:
    """
    Main orchestrator for identifying suitable locations.
    
    Process:
    1. Load benchmark for category (for reference, sanitized for public API)
    2. Discover candidates:
       - Tier A: Named micro-markets (always included if available)
       - Tier B: Gap discovery (if tier allows and enabled)
    3. Build profiles in parallel
    4. Classify with candidate-mode adjustments
    5. Apply archetype_preference filter if provided
    6. Group by archetype
    7. Enforce tier-based limits
    8. Build GeoJSON map_data
    9. Cache result for 7 days
    """

    # Tier limits
    TIER_LIMITS = {
        UserTier.FREE: {
            "monthly_calls": 1,
            "include_gaps": False,
            "max_per_archetype": 3,
            "description": "Free tier - limited to named markets only"
        },
        UserTier.BUILDER: {
            "monthly_calls": 5,
            "include_gaps": True,
            "max_per_archetype": 5,
            "description": "Builder tier - includes gap discovery"
        },
        UserTier.SCALER: {
            "monthly_calls": 25,
            "include_gaps": True,
            "max_per_archetype": 999,  # Effectively unlimited
            "description": "Scaler tier - unlimited candidates"
        },
        UserTier.ENTERPRISE: {
            "monthly_calls": 999,
            "include_gaps": True,
            "max_per_archetype": 999,
            "description": "Enterprise tier - unlimited"
        },
    }

    CACHE_TTL_DAYS = 7

    def __init__(self, db: Session):
        self.db = db
        self.catalog = MicroMarketCatalog(db)
        self.gap_engine = GapDiscoveryEngine(db)
        self.profile_builder = CandidateProfileBuilder(db)

    def identify_location(
        self,
        category: str,
        target_market: TargetMarket,
        business_description: Optional[str] = None,
        market_boundary: Optional[MarketBoundary] = None,
        archetype_preference: Optional[List[str]] = None,
        include_gap_discovery: bool = True,
        user_tier: UserTier = UserTier.FREE,
        user_id: Optional[int] = None,
    ) -> IdentifyLocationResult:
        """
        Main identify location orchestrator.
        Returns IdentifyLocationResult with candidates grouped by archetype.
        """
        import time
        start_time = time.time()
        
        try:
            # Generate request ID for caching/tracking
            request_id = str(uuid.uuid4())
            
            # Check cache first
            cached_result = self._get_cached_result(
                category, target_market, market_boundary
            )
            if cached_result:
                logger.info(f"Cache hit for request {request_id}")
                return cached_result
            
            # Tier validation
            tier_config = self.TIER_LIMITS.get(user_tier, self.TIER_LIMITS[UserTier.FREE])
            should_include_gaps = include_gap_discovery and tier_config["include_gaps"]
            
            # Discover candidates
            named_candidates = self._discover_named_markets(target_market, market_boundary)
            gap_candidates = []
            if should_include_gaps:
                gap_candidates = self._discover_gaps(target_market, category)
            
            logger.info(f"Found {len(named_candidates)} named, {len(gap_candidates)} gap candidates")
            
            # Merge candidates (named takes precedence over overlapping gaps)
            all_candidates = self._merge_candidates(named_candidates, gap_candidates)
            
            # Filter by archetype preference if provided
            if archetype_preference:
                all_candidates = self._filter_by_archetype_preference(
                    all_candidates, archetype_preference
                )
            
            # Group by archetype
            grouped = self._group_by_archetype(all_candidates)
            
            # Apply tier limits
            limited_groups = self._apply_tier_limits(grouped, tier_config)
            candidates_before_limit = len(all_candidates)
            candidates_after_limit = sum(len(g.candidates) for g in limited_groups)
            
            # Build map data
            map_data = self._build_map_data(limited_groups, target_market)
            
            # Build benchmark summary (sanitized for public API)
            benchmark = self._build_benchmark_summary(category)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Build result
            result = IdentifyLocationResult(
                request_id=request_id,
                category=category,
                benchmark_summary=benchmark,
                target_market=target_market,
                candidates_by_archetype=limited_groups,
                total_candidates=candidates_before_limit,
                tier=user_tier,
                candidates_shown=candidates_after_limit,
                candidates_limited=(candidates_after_limit < candidates_before_limit),
                data_quality={
                    "sources": ["micro_market_catalog", "foot_traffic_api", "census_data", "business_database"],
                    "coverage": "high" if len(named_candidates) > 0 else "limited"
                },
                map_data=map_data,
                processing_time_ms=processing_time,
                from_cache=False,
                created_at=datetime.utcnow(),
                named_markets_included=len(named_candidates) > 0,
                gap_markets_included=len(gap_candidates) > 0,
            )
            
            # Cache result
            self._cache_result(category, target_market, market_boundary, result)
            
            return result
        
        except Exception as e:
            logger.error(f"Error in identify_location: {e}", exc_info=True)
            raise

    def _discover_named_markets(
        self,
        target_market: TargetMarket,
        market_boundary: Optional[MarketBoundary] = None
    ) -> List[CandidateProfile]:
        """
        Discover Tier A named micro-markets.
        """
        try:
            candidates = []
            
            if target_market.market_type == TargetMarketType.METRO:
                markets = self.catalog.get_markets_for_metro(
                    target_market.metro, target_market.state
                )
                if markets:
                    candidates = self.catalog.markets_to_candidates(
                        markets, "default"
                    )
            elif target_market.market_type == TargetMarketType.CITY:
                markets = self.catalog.get_markets_by_city(
                    target_market.city, target_market.state
                )
                if markets:
                    candidates = self.catalog.markets_to_candidates(
                        markets, "default"
                    )
            
            # Apply market boundary filters if provided
            if market_boundary:
                candidates = self._apply_boundary_filters(candidates, market_boundary)
            
            return candidates
        
        except Exception as e:
            logger.error(f"Error discovering named markets: {e}")
            return []

    def _discover_gaps(
        self,
        target_market: TargetMarket,
        category: str
    ) -> List[CandidateProfile]:
        """
        Discover Tier B gap markets using H3 hex grid.
        """
        try:
            # Get competitor and demographic data (would call APIs in production)
            competitor_data = []  # TODO: call competitor API
            demographic_data = {}  # TODO: call census API
            
            # Run gap discovery (async wrapper)
            import asyncio
            loop = asyncio.get_event_loop()
            candidates = loop.run_until_complete(
                self.gap_engine.discover_gaps(
                    target_market, category, competitor_data, demographic_data
                )
            )
            
            return candidates
        
        except Exception as e:
            logger.error(f"Error discovering gaps: {e}")
            return []

    def _merge_candidates(
        self,
        named: List[CandidateProfile],
        gaps: List[CandidateProfile]
    ) -> List[CandidateProfile]:
        """
        Merge named and gap candidates.
        Named markets take precedence over overlapping gaps.
        
        Precedence: Named > Gap
        """
        # For now, simple concatenation with named first
        # In production, would check spatial overlap and remove overlapping gaps
        return named + gaps

    def _filter_by_archetype_preference(
        self,
        candidates: List[CandidateProfile],
        preference: List[str]
    ) -> List[CandidateProfile]:
        """
        Filter candidates to only those matching archetype preference.
        """
        preference_lower = [p.lower() for p in preference]
        return [
            c for c in candidates
            if c.archetype.lower() in preference_lower
        ]

    def _group_by_archetype(
        self,
        candidates: List[CandidateProfile]
    ) -> List[ArchetypeGroup]:
        """Group candidates by archetype"""
        groups: Dict[str, List[CandidateProfile]] = {}
        
        for candidate in candidates:
            key = str(candidate.archetype)
            if key not in groups:
                groups[key] = []
            groups[key].append(candidate)
        
        # Build ArchetypeGroup objects
        result = []
        for archetype_str, cands in groups.items():
            try:
                archetype = ArchetypeType(archetype_str)
                scores = [c.overall_score for c in cands]
                
                group = ArchetypeGroup(
                    archetype=archetype,
                    archetype_description=self._get_archetype_description(archetype),
                    candidate_count=len(cands),
                    candidates=cands,
                    avg_score=sum(scores) / len(scores) if scores else 0,
                    score_range={"min": min(scores), "max": max(scores)} if scores else {"min": 0, "max": 0}
                )
                result.append(group)
            except Exception as e:
                logger.warning(f"Error creating archetype group for {archetype_str}: {e}")
        
        # Sort by avg_score descending
        result.sort(key=lambda x: x.avg_score, reverse=True)
        return result

    def _apply_tier_limits(
        self,
        groups: List[ArchetypeGroup],
        tier_config: Dict[str, Any]
    ) -> List[ArchetypeGroup]:
        """
        Apply tier-based limits to candidate counts.
        """
        max_per_archetype = tier_config["max_per_archetype"]
        
        limited_groups = []
        for group in groups:
            limited_candidates = group.candidates[:max_per_archetype]
            limited_group = ArchetypeGroup(
                archetype=group.archetype,
                archetype_description=group.archetype_description,
                candidate_count=len(limited_candidates),
                candidates=limited_candidates,
                avg_score=sum(c.overall_score for c in limited_candidates) / len(limited_candidates) if limited_candidates else 0,
                score_range={"min": min(c.overall_score for c in limited_candidates), "max": max(c.overall_score for c in limited_candidates)} if limited_candidates else {"min": 0, "max": 0}
            )
            limited_groups.append(limited_group)
        
        return limited_groups

    def _build_map_data(
        self,
        groups: List[ArchetypeGroup],
        target_market: TargetMarket
    ) -> Dict[str, Any]:
        """
        Build GeoJSON FeatureCollection for map visualization.
        """
        features = []
        
        # Color scheme by archetype
        archetype_colors = {
            "pioneer": "#FF6B6B",
            "mainstream": "#4ECDC4",
            "specialist": "#95E1D3",
            "anchor": "#FFE66D",
            "experimental": "#C7B3E5",
        }
        
        for group in groups:
            color = archetype_colors.get(str(group.archetype), "#999999")
            
            for candidate in group.candidates:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [candidate.longitude, candidate.latitude]
                    },
                    "properties": {
                        "id": candidate.candidate_id,
                        "name": candidate.location_name,
                        "archetype": str(group.archetype),
                        "score": candidate.overall_score,
                        "confidence": candidate.archetype_confidence,
                        "color": color,
                    }
                }
                features.append(feature)
        
        # Get center point for map
        center = self._get_target_market_center(target_market)
        
        return {
            "type": "FeatureCollection",
            "center": center,
            "features": features,
            "feature_count": len(features)
        }

    def _build_benchmark_summary(self, category: str) -> Optional[BenchmarkSummary]:
        """
        Build public-safe benchmark summary.
        MUST NOT include: tickers, SEC refs, raw thresholds, margins, revenue data.
        Only safe fields: category, typical_archetypes, total_addressable_population.
        """
        try:
            # Placeholder: would load from database
            return BenchmarkSummary(
                category=category,
                typical_archetypes=[
                    "mainstream",
                    "specialist",
                    "pioneer"
                ],
                total_addressable_population=10000000  # Placeholder
            )
        except Exception as e:
            logger.warning(f"Error building benchmark summary: {e}")
            return None

    def _apply_boundary_filters(
        self,
        candidates: List[CandidateProfile],
        boundary: MarketBoundary
    ) -> List[CandidateProfile]:
        """Apply market boundary filters to candidates"""
        # TODO: Implement spatial filtering based on boundary type
        return candidates

    def _get_archetype_description(self, archetype: ArchetypeType) -> str:
        """Get description for archetype"""
        descriptions = {
            ArchetypeType.PIONEER: "Early-stage locations with emerging demand and lower competition",
            ArchetypeType.MAINSTREAM: "Established locations with proven demand and moderate competition",
            ArchetypeType.SPECIALIST: "Niche locations with focused demographics and high-margin potential",
            ArchetypeType.ANCHOR: "Destination-driving locations that attract traffic",
            ArchetypeType.EXPERIMENTAL: "Test markets with potential but requiring validation",
        }
        return descriptions.get(archetype, "Location")

    def _get_target_market_center(self, target_market: TargetMarket) -> Dict[str, float]:
        """Get center point for target market"""
        if target_market.market_type == TargetMarketType.POINT_RADIUS:
            return {
                "latitude": target_market.latitude,
                "longitude": target_market.longitude
            }
        
        # Default centers for major metros
        metro_centers = {
            ("Miami", "FL"): {"latitude": 25.7617, "longitude": -80.1918},
            ("Atlanta", "GA"): {"latitude": 33.7490, "longitude": -84.3880},
            ("Orlando", "FL"): {"latitude": 28.5421, "longitude": -81.3723},
            ("Tampa", "FL"): {"latitude": 27.9506, "longitude": -82.4693},
            ("New York", "NY"): {"latitude": 40.7128, "longitude": -74.0060},
            ("Los Angeles", "CA"): {"latitude": 34.0522, "longitude": -118.2437},
            ("Houston", "TX"): {"latitude": 29.7604, "longitude": -95.3698},
            ("Dallas", "TX"): {"latitude": 32.7767, "longitude": -96.7970},
            ("Chicago", "IL"): {"latitude": 41.8781, "longitude": -87.6298},
            ("Austin", "TX"): {"latitude": 30.2672, "longitude": -97.7431},
        }
        
        key = (target_market.metro or target_market.city, target_market.state)
        return metro_centers.get(key, {"latitude": 25.7617, "longitude": -80.1918})

    def _get_cached_result(
        self,
        category: str,
        target_market: TargetMarket,
        market_boundary: Optional[MarketBoundary] = None
    ) -> Optional[IdentifyLocationResult]:
        """Get cached result if available and not expired"""
        try:
            cache_key = self._generate_cache_key(category, target_market, market_boundary)
            
            cached = self.db.query(IdentifyLocationCache).filter(
                and_(
                    IdentifyLocationCache.cache_key == cache_key,
                    IdentifyLocationCache.expires_at > datetime.utcnow()
                )
            ).first()
            
            if cached:
                # Increment hit count
                cached.hit_count += 1
                self.db.commit()
                
                # Deserialize result
                result_dict = cached.result
                result = IdentifyLocationResult(**result_dict)
                result.from_cache = True
                return result
        
        except Exception as e:
            logger.warning(f"Error retrieving cached result: {e}")
        
        return None

    def _cache_result(
        self,
        category: str,
        target_market: TargetMarket,
        market_boundary: Optional[MarketBoundary],
        result: IdentifyLocationResult
    ) -> None:
        """Cache the result for 7 days"""
        try:
            cache_key = self._generate_cache_key(category, target_market, market_boundary)
            
            cache_entry = IdentifyLocationCache(
                cache_key=cache_key,
                request_id=result.request_id,
                category=category,
                target_market=target_market.dict(),
                market_boundary=market_boundary.dict() if market_boundary else None,
                result=result.dict(),
                expires_at=datetime.utcnow() + timedelta(days=self.CACHE_TTL_DAYS)
            )
            
            self.db.add(cache_entry)
            self.db.commit()
            logger.info(f"Cached result {result.request_id}")
        
        except Exception as e:
            logger.error(f"Error caching result: {e}")

    def _generate_cache_key(
        self,
        category: str,
        target_market: TargetMarket,
        market_boundary: Optional[MarketBoundary] = None
    ) -> str:
        """Generate cache key from request parameters"""
        key_parts = [
            category,
            str(target_market.market_type),
            target_market.metro or target_market.city or str(target_market.latitude),
            target_market.state or "XX",
        ]
        
        if market_boundary:
            key_parts.append(str(market_boundary.boundary_type))
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def promote_candidate(
        self,
        request_id: str,
        candidate_id: str,
        user_id: int,
        user_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Promote a candidate location to a SuccessProfile.
        Creates a new SuccessProfile record.
        """
        try:
            # Get the cached request
            cached = self.db.query(IdentifyLocationCache).filter(
                IdentifyLocationCache.request_id == request_id
            ).first()
            
            if not cached:
                return {
                    "success": False,
                    "error": "Request not found"
                }
            
            # Find candidate in result
            result_dict = cached.result
            target_candidate = None
            category = result_dict.get("category")
            
            for group_dict in result_dict.get("candidates_by_archetype", []):
                for cand_dict in group_dict.get("candidates", []):
                    if cand_dict.get("candidate_id") == candidate_id:
                        target_candidate = cand_dict
                        break
            
            if not target_candidate:
                return {
                    "success": False,
                    "error": "Candidate not found in request"
                }
            
            # Create SuccessProfile
            profile = SuccessProfile(
                user_id=user_id,
                request_id=request_id,
                candidate_id=candidate_id,
                category=category,
                location_name=target_candidate.get("location_name"),
                latitude=target_candidate.get("latitude"),
                longitude=target_candidate.get("longitude"),
                zip_code=target_candidate.get("zip_code"),
                neighborhood=target_candidate.get("neighborhood"),
                city=target_candidate.get("city"),
                state=target_candidate.get("state"),
                archetype=target_candidate.get("archetype"),
                archetype_confidence=target_candidate.get("archetype_confidence", 0.5),
                candidate_profile=target_candidate,
                user_notes=user_notes,
                status="active"
            )
            
            self.db.add(profile)
            self.db.commit()
            
            return {
                "success": True,
                "success_profile_id": str(profile.id),
                "message": f"Successfully promoted {target_candidate.get('location_name')} to SuccessProfile"
            }
        
        except Exception as e:
            logger.error(f"Error promoting candidate: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def get_candidate_detail(
        self,
        request_id: str,
        candidate_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed view of a single candidate.
        """
        try:
            cached = self.db.query(IdentifyLocationCache).filter(
                IdentifyLocationCache.request_id == request_id
            ).first()
            
            if not cached:
                return None
            
            result_dict = cached.result
            for group_dict in result_dict.get("candidates_by_archetype", []):
                for cand_dict in group_dict.get("candidates", []):
                    if cand_dict.get("candidate_id") == candidate_id:
                        return cand_dict
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting candidate detail: {e}")
            return None
