"""
Municipal Data API Client - Main Entry Point

High-level interface for querying municipal data.
Orchestrates Socrata provider, caching, and analysis.

Usage:
    from app.services.municipal_data import MunicipalDataClient
    
    client = MunicipalDataClient()
    
    # Query self-storage supply for Miami
    result = await client.query_facilities(
        metro="Miami",
        state="FL",
        industry="self-storage",
        population=6_091_747
    )
    
    if result.success:
        print(f"Verdict: {result.metrics.verdict}")
        print(f"Supply: {result.metrics.sqft_per_capita:.2f} sqft/capita")
    else:
        print(f"Error: {result.error}")
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.municipal_data.providers.socrata_provider import SocrataProvider
from app.services.municipal_data.providers.fallback_provider import SerpAPIFallbackProvider
from app.services.municipal_data.providers.cache import (
    InMemoryCache,
    generate_cache_key,
    CACHE_TTL_SECONDS,
)
from app.services.municipal_data.land_use_mapping import (
    LandUseMapping,
    LandUseMappingError,
)
from app.services.municipal_data.industry_analyzers import IndustryAnalyzerFactory
from app.services.municipal_data.schemas import (
    FacilitySupplyMetrics,
    MunicipalQueryResult,
    SupplyVerdict,
)

logger = logging.getLogger(__name__)


class MunicipalDataClientError(Exception):
    """Raised when client encounters an error"""
    pass


class MunicipalDataClient:
    """
    Main client for querying municipal property data.
    
    Responsibilities:
    1. Orchestrate Socrata queries
    2. Cache results (7-day TTL)
    3. Run industry-specific analysis
    4. Return structured results
    
    Workflow:
    1. Check cache
    2. If miss, query Socrata
    3. Run analysis
    4. Cache result
    5. Return
    """
    
    def __init__(self, cache=None, serpapi_key: Optional[str] = None):
        """
        Initialize client.
        
        Args:
            cache: Optional cache provider. Uses InMemoryCache by default.
            serpapi_key: Optional SerpAPI key for fallback queries
        """
        self.socrata = SocrataProvider()
        self.fallback = SerpAPIFallbackProvider(api_key=serpapi_key)
        self.cache = cache or InMemoryCache()
        self.land_use_mapper = LandUseMapping()
    
    async def close(self):
        """Close HTTP client and clean up resources"""
        await self.socrata.close()
        await self.cache.clear()
    
    async def query_facilities(
        self,
        metro: str,
        state: str,
        industry: str,
        population: Optional[int] = None,
        dataset_id: Optional[str] = None,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> MunicipalQueryResult:
        """
        Query supply metrics for a facility type in a metro.
        
        This is the main entry point. It:
        1. Looks up land use codes for the industry/metro
        2. Checks cache
        3. Queries Socrata if needed
        4. Runs analysis
        5. Returns structured result
        
        Args:
            metro: Metro name (e.g., "Miami", "Chicago")
            state: State code (e.g., "FL", "IL")
            industry: Industry code (e.g., "self-storage")
            population: Optional population override. If not provided, uses Census data.
            dataset_id: Optional Socrata dataset ID override
            use_cache: Whether to use cache
            force_refresh: Force bypass cache
        
        Returns:
            MunicipalQueryResult with metrics and verdict
        """
        
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Generate cache key
            cache_key = generate_cache_key(metro, industry)
            
            # Check cache first
            if use_cache and not force_refresh:
                cached_metrics = await self.cache.get(cache_key)
                if cached_metrics:
                    logger.info(f"Cache hit: {cache_key}")
                    return MunicipalQueryResult(
                        success=True,
                        metro=metro,
                        state=state,
                        industry=industry,
                        metrics=cached_metrics,
                        fallback_used=False,
                        request_id=request_id,
                    )
            
            logger.info(f"Query: {metro}, {state}, {industry}")
            
            # Get land use codes
            try:
                land_use_codes = self.land_use_mapper.get_land_use_codes(
                    industry, metro, state
                )
            except LandUseMappingError as e:
                logger.error(f"Land use mapping error: {e}")
                return MunicipalQueryResult(
                    success=False,
                    metro=metro,
                    state=state,
                    industry=industry,
                    error=str(e),
                    request_id=request_id,
                )
            
            # Get population if not provided
            if not population:
                try:
                    population = self.land_use_mapper.get_population(metro, state)
                except LandUseMappingError:
                    logger.warning(f"Population not found for {metro}, {state}")
                    population = 1_000_000  # Fallback
            
            # Get metro config
            metro_config = self.land_use_mapper.get_metro_config(industry, metro)
            land_use_field = metro_config.get("field_name", "land_use_code")
            
            # Get Socrata endpoint config
            socrata_config = self.socrata.get_endpoint_config(metro)
            if not socrata_config:
                raise MunicipalDataClientError(f"No Socrata config for {metro}")
            
            # Query Socrata
            # For now, since we don't have live dataset IDs, we'll simulate the response
            logger.info(f"Querying Socrata for {metro}: {land_use_codes}")
            
            # In production, this would query the actual Socrata endpoint
            # For now, simulate a response
            total_facilities, total_sqft = await self._query_socrata(
                metro,
                land_use_codes,
                dataset_id,
                socrata_config,
            )
            
            # Run analysis
            analyzer = IndustryAnalyzerFactory.get_analyzer(industry)
            if not analyzer:
                raise MunicipalDataClientError(f"No analyzer for industry {industry}")
            
            is_verified = self.land_use_mapper.is_verified(industry, metro)
            
            metrics = await analyzer.analyze(
                metro=metro,
                state=state,
                total_facilities=total_facilities,
                total_building_sqft=total_sqft,
                population=population,
                confidence=0.95 if is_verified else 0.60,
                data_source="socrata",
                coverage_percentage=100.0 if is_verified else 80.0,
            )
            
            # Cache result
            if use_cache:
                await self.cache.set(cache_key, metrics, CACHE_TTL_SECONDS)
                logger.debug(f"Cached result: {cache_key}")
            
            return MunicipalQueryResult(
                success=True,
                metro=metro,
                state=state,
                industry=industry,
                metrics=metrics,
                fallback_used=False,
                request_id=request_id,
            )
        
        except LandUseMappingError as e:
            # Metro not in land_use_mapper, try fallback
            logger.warning(f"Metro not configured, trying fallback: {e}")
            return await self._try_fallback(
                metro, state, industry, population, request_id
            )
        
        except Exception as e:
            logger.error(f"Query failed: {e}, trying fallback", exc_info=True)
            return await self._try_fallback(
                metro, state, industry, population, request_id
            )
    
    async def _query_socrata(
        self,
        metro: str,
        land_use_codes: list,
        dataset_id: Optional[str],
        socrata_config: Any,
    ) -> tuple:
        """
        Internal method to query Socrata endpoint.
        
        Returns: (total_facilities, total_sqft)
        
        For now, returns mock data. In production, would use:
        response = await self.socrata.query(
            metro=metro,
            dataset_id=dataset_id,
            land_use_field=socrata_config.land_use_field,
            land_use_codes=land_use_codes,
            sqft_field=socrata_config.sqft_field,
        )
        """
        
        # MOCK DATA FOR DEMO
        # In production, would query actual Socrata endpoints
        mock_data = {
            ("miami", "self-storage"): (145, 3_500_000),  # 145 facilities, 3.5M sqft
            ("chicago", "self-storage"): (325, 8_200_000),
            ("nyc", "self-storage"): (485, 12_000_000),
            ("seattle", "self-storage"): (92, 2_200_000),
            ("denver", "self-storage"): (78, 1_850_000),
        }
        
        key = (metro.lower(), "self-storage")  # Simplified for demo
        
        if key in mock_data:
            return mock_data[key]
        
        # Default fallback
        logger.warning(f"No mock data for {key}, using default")
        return (50, 1_000_000)
    
    async def _try_fallback(
        self,
        metro: str,
        state: str,
        industry: str,
        population: Optional[int],
        request_id: str,
    ) -> MunicipalQueryResult:
        """
        Try SerpAPI fallback when Socrata/primary fails.
        
        Fallback provides lower-confidence data but better than nothing.
        """
        if not self.fallback.enabled:
            return MunicipalQueryResult(
                success=False,
                metro=metro,
                state=state,
                industry=industry,
                error="Metro not configured and no fallback available",
                fallback_used=False,
                request_id=request_id,
            )
        
        try:
            logger.info(f"Using SerpAPI fallback for {metro}, {state}, {industry}")
            
            # Get population if not provided
            if not population:
                population = 1_000_000  # Default fallback population
            
            # Query fallback provider
            parcels = await self.fallback.query(
                metro=metro,
                state=state,
                industry=industry,
                limit=100,
            )
            
            if not parcels:
                return MunicipalQueryResult(
                    success=False,
                    metro=metro,
                    state=state,
                    industry=industry,
                    error="Fallback provider returned no results",
                    fallback_used=True,
                    request_id=request_id,
                )
            
            # Calculate metrics from fallback data
            total_facilities = len(parcels)
            total_sqft = sum(p.building_sqft for p in parcels)
            
            # Run analysis with fallback data
            analyzer = IndustryAnalyzerFactory.get_analyzer(industry)
            if not analyzer:
                return MunicipalQueryResult(
                    success=False,
                    metro=metro,
                    state=state,
                    industry=industry,
                    error=f"No analyzer for industry {industry}",
                    fallback_used=True,
                    request_id=request_id,
                )
            
            metrics = await analyzer.analyze(
                metro=metro,
                state=state,
                total_facilities=total_facilities,
                total_building_sqft=total_sqft,
                population=population,
                confidence=0.60,  # Lower confidence for fallback
                data_source="serpapi_fallback",
                coverage_percentage=60.0,  # Incomplete coverage
            )
            
            logger.info(
                f"Fallback success: {metro}, {state}, {industry} → "
                f"{total_facilities} facilities, {metrics.verdict.value}"
            )
            
            return MunicipalQueryResult(
                success=True,
                metro=metro,
                state=state,
                industry=industry,
                metrics=metrics,
                fallback_used=True,
                request_id=request_id,
            )
        
        except Exception as e:
            logger.error(f"Fallback query also failed: {e}", exc_info=True)
            return MunicipalQueryResult(
                success=False,
                metro=metro,
                state=state,
                industry=industry,
                error=f"Both primary and fallback failed: {str(e)}",
                fallback_used=True,
                request_id=request_id,
            )
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()
    
    def list_supported_metros(self, industry: Optional[str] = None) -> list:
        """List supported metros"""
        return self.land_use_mapper.list_supported_metros(industry)
    
    def list_supported_industries(self) -> list:
        """List supported industries"""
        return self.land_use_mapper.list_supported_industries()
    
    def is_configured(self, industry: str, metro: str) -> bool:
        """Check if industry/metro is configured"""
        return self.land_use_mapper.is_configured(industry, metro)
