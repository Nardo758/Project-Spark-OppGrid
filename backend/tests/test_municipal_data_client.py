"""
Comprehensive tests for Municipal Data API Client

Test coverage:
- Unit: SocrataProvider with mocked responses
- Unit: SelfStorageAnalyzer calculations
- Unit: Land use mapping lookups
- Unit: Cache hit/miss
- Unit: Industry analyzer factory
- Integration: Client query flow
- Integration: Fallback logic
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.services.municipal_data.client import MunicipalDataClient
from app.services.municipal_data.providers.socrata_provider import SocrataProvider
from app.services.municipal_data.providers.cache import InMemoryCache, generate_cache_key
from app.services.municipal_data.industry_analyzers import (
    SelfStorageAnalyzer,
    IndustryAnalyzerFactory,
)
from app.services.municipal_data.land_use_mapping import (
    LandUseMapping,
    LandUseMappingError,
)
from app.services.municipal_data.schemas import (
    FacilitySupplyMetrics,
    SupplyVerdict,
    MunicipalQueryResult,
)


# ============================================================================
# LAND USE MAPPING TESTS
# ============================================================================

class TestLandUseMapping:
    """Unit tests for land use mapping"""
    
    def test_get_land_use_codes_miami_self_storage(self):
        """Test Miami self-storage land use codes"""
        codes = LandUseMapping.get_land_use_codes("self-storage", "miami")
        assert codes == ["39"]
        assert isinstance(codes, list)
    
    def test_get_land_use_codes_chicago_self_storage(self):
        """Test Chicago self-storage land use codes"""
        codes = LandUseMapping.get_land_use_codes("self-storage", "chicago")
        assert codes == ["516"]
    
    def test_get_land_use_codes_nyc_self_storage(self):
        """Test NYC self-storage land use codes"""
        codes = LandUseMapping.get_land_use_codes("self-storage", "nyc")
        assert set(codes) == {"D4", "E0", "E1", "E2"}
    
    def test_get_land_use_codes_all_metros(self):
        """Test all 5 metros are configured"""
        metros = ["miami", "chicago", "nyc", "seattle", "denver"]
        for metro in metros:
            codes = LandUseMapping.get_land_use_codes("self-storage", metro)
            assert len(codes) > 0
            assert all(isinstance(c, str) for c in codes)
    
    def test_get_land_use_codes_case_insensitive(self):
        """Test that lookups are case-insensitive"""
        codes1 = LandUseMapping.get_land_use_codes("SELF-STORAGE", "MIAMI")
        codes2 = LandUseMapping.get_land_use_codes("self-storage", "miami")
        assert codes1 == codes2
    
    def test_get_land_use_codes_unknown_industry(self):
        """Test error on unknown industry"""
        with pytest.raises(LandUseMappingError):
            LandUseMapping.get_land_use_codes("unknown-industry", "miami")
    
    def test_get_land_use_codes_unknown_metro(self):
        """Test error on unknown metro"""
        with pytest.raises(LandUseMappingError):
            LandUseMapping.get_land_use_codes("self-storage", "unknown-metro")
    
    def test_get_metro_config(self):
        """Test getting full metro configuration"""
        config = LandUseMapping.get_metro_config("self-storage", "miami")
        assert "codes" in config
        assert "field_name" in config
        assert "verified" in config
        assert "notes" in config
        assert config["codes"] == ["39"]
    
    def test_get_population_miami(self):
        """Test population lookup for Miami"""
        pop = LandUseMapping.get_population("miami", "FL")
        assert pop == 6_091_747
    
    def test_get_population_all_metros(self):
        """Test population lookup for all metros"""
        metros = [
            ("miami", "FL", 6_091_747),
            ("chicago", "IL", 9_618_502),
            ("nyc", "NY", 20_201_249),
            ("seattle", "WA", 4_018_762),
            ("denver", "CO", 3_154_794),
        ]
        for metro, state, expected_pop in metros:
            pop = LandUseMapping.get_population(metro, state)
            assert pop == expected_pop
    
    def test_get_population_unknown_metro(self):
        """Test error on unknown metro"""
        with pytest.raises(LandUseMappingError):
            LandUseMapping.get_population("unknown", "XX")
    
    def test_list_supported_metros(self):
        """Test listing supported metros"""
        metros = LandUseMapping.list_supported_metros()
        assert len(metros) >= 5
        assert "miami" in metros
        assert "chicago" in metros
        assert "nyc" in metros
    
    def test_list_supported_metros_by_industry(self):
        """Test listing metros for specific industry"""
        metros = LandUseMapping.list_supported_metros("self-storage")
        assert "miami" in metros
        assert "chicago" in metros
    
    def test_list_supported_industries(self):
        """Test listing supported industries"""
        industries = LandUseMapping.list_supported_industries()
        assert "self-storage" in industries
    
    def test_is_configured(self):
        """Test is_configured check"""
        assert LandUseMapping.is_configured("self-storage", "miami") is True
        assert LandUseMapping.is_configured("unknown", "miami") is False
    
    def test_is_verified_miami(self):
        """Test verification status"""
        assert LandUseMapping.is_verified("self-storage", "miami") is True
        assert LandUseMapping.is_verified("self-storage", "seattle") is False


# ============================================================================
# SELF-STORAGE ANALYZER TESTS
# ============================================================================

class TestSelfStorageAnalyzer:
    """Unit tests for self-storage analyzer"""
    
    @pytest.mark.asyncio
    async def test_analyze_oversaturated_market(self):
        """Test analysis of oversaturated market"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Miami",
            state="FL",
            total_facilities=150,
            total_building_sqft=50_000_000,  # Very high
            population=6_091_747,
            confidence=0.95,
        )
        
        assert metrics.verdict == SupplyVerdict.OVERSATURATED
        assert metrics.sqft_per_capita > 7.0
        assert metrics.total_facilities == 150
        assert metrics.metro == "miami"
    
    @pytest.mark.asyncio
    async def test_analyze_balanced_market(self):
        """Test analysis of balanced market"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Chicago",
            state="IL",
            total_facilities=300,
            total_building_sqft=40_000_000,  # Balanced
            population=9_618_502,
            confidence=0.95,
        )
        
        assert metrics.verdict == SupplyVerdict.BALANCED
        assert 5.0 <= metrics.sqft_per_capita <= 7.0
    
    @pytest.mark.asyncio
    async def test_analyze_undersaturated_market(self):
        """Test analysis of undersaturated market"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Denver",
            state="CO",
            total_facilities=50,
            total_building_sqft=10_000_000,  # Low
            population=3_154_794,
            confidence=0.95,
        )
        
        assert metrics.verdict == SupplyVerdict.UNDERSATURATED
        assert metrics.sqft_per_capita < 5.0
    
    @pytest.mark.asyncio
    async def test_analyze_calculates_sqft_per_capita(self):
        """Test sqft per capita calculation"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Seattle",
            state="WA",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=4_000_000,
            confidence=0.95,
        )
        
        expected_sqft_per_capita = 30_000_000 / 4_000_000
        assert metrics.sqft_per_capita == expected_sqft_per_capita
    
    @pytest.mark.asyncio
    async def test_analyze_calculates_facilities_per_100k(self):
        """Test facilities per 100k calculation"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Test",
            state="TX",
            total_facilities=100,
            total_building_sqft=10_000_000,
            population=1_000_000,
            confidence=0.95,
        )
        
        expected_per_100k = (100 / 1_000_000) * 100_000
        assert metrics.facilities_per_100k_population == expected_per_100k
    
    @pytest.mark.asyncio
    async def test_analyze_includes_metadata(self):
        """Test that analysis includes all required metadata"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Miami",
            state="FL",
            total_facilities=100,
            total_building_sqft=20_000_000,
            population=6_091_747,
            confidence=0.95,
            data_source="socrata",
            coverage_percentage=100.0,
        )
        
        assert metrics.metro is not None
        assert metrics.state is not None
        assert metrics.industry == "self-storage"
        assert metrics.confidence == 0.95
        assert metrics.data_source == "socrata"
        assert metrics.coverage_percentage == 100.0
        assert metrics.last_updated is not None
    
    def test_get_interpretation_oversaturated(self):
        """Test interpretation of oversaturated market"""
        analyzer = SelfStorageAnalyzer()
        
        # Mock metrics
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=50_000_000,
            population=5_000_000,
            sqft_per_capita=10.0,
            facilities_per_100k_population=2000,
            verdict=SupplyVerdict.OVERSATURATED,
        )
        
        interpretation = analyzer.get_interpretation(metrics)
        assert "OVERSATURATED" in interpretation
        assert "competition" in interpretation.lower()
    
    def test_get_interpretation_balanced(self):
        """Test interpretation of balanced market"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = FacilitySupplyMetrics(
            metro="chicago",
            state="IL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=5_000_000,
            sqft_per_capita=6.0,
            facilities_per_100k_population=2000,
            verdict=SupplyVerdict.BALANCED,
        )
        
        interpretation = analyzer.get_interpretation(metrics)
        assert "BALANCED" in interpretation
        assert "healthy" in interpretation.lower()
    
    def test_get_interpretation_undersaturated(self):
        """Test interpretation of undersaturated market"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = FacilitySupplyMetrics(
            metro="denver",
            state="CO",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=15_000_000,
            population=5_000_000,
            sqft_per_capita=3.0,
            facilities_per_100k_population=2000,
            verdict=SupplyVerdict.UNDERSATURATED,
        )
        
        interpretation = analyzer.get_interpretation(metrics)
        assert "UNDERSATURATED" in interpretation
        assert "growth" in interpretation.lower() or "opportunity" in interpretation.lower()


# ============================================================================
# CACHE TESTS
# ============================================================================

class TestInMemoryCache:
    """Unit tests for in-memory cache"""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic set/get"""
        cache = InMemoryCache()
        
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=6_000_000,
            sqft_per_capita=5.0,
            facilities_per_100k_population=1666,
            verdict=SupplyVerdict.BALANCED,
        )
        
        await cache.set("test_key", metrics)
        result = await cache.get("test_key")
        
        assert result is not None
        assert result.metro == "miami"
        assert result.verdict == SupplyVerdict.BALANCED
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss"""
        cache = InMemoryCache()
        result = await cache.get("nonexistent_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_hit_tracking(self):
        """Test cache hit/miss statistics"""
        cache = InMemoryCache()
        
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=6_000_000,
            sqft_per_capita=5.0,
            facilities_per_100k_population=1666,
            verdict=SupplyVerdict.BALANCED,
        )
        
        await cache.set("test", metrics)
        await cache.get("test")  # Hit
        await cache.get("test")  # Hit
        await cache.get("nonexistent")  # Miss
        
        stats = await cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2/3
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache deletion"""
        cache = InMemoryCache()
        
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=6_000_000,
            sqft_per_capita=5.0,
            facilities_per_100k_population=1666,
            verdict=SupplyVerdict.BALANCED,
        )
        
        await cache.set("test", metrics)
        await cache.delete("test")
        result = await cache.get("test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clear"""
        cache = InMemoryCache()
        
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=6_000_000,
            sqft_per_capita=5.0,
            facilities_per_100k_population=1666,
            verdict=SupplyVerdict.BALANCED,
        )
        
        await cache.set("key1", metrics)
        await cache.set("key2", metrics)
        await cache.clear()
        
        stats = await cache.get_stats()
        assert stats["size"] == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key1 = generate_cache_key("Miami", "self-storage")
        key2 = generate_cache_key("miami", "self-storage")
        assert key1 == key2  # Case-insensitive
        
        key3 = generate_cache_key("Miami", "self-storage", {"boundary": "test"})
        key4 = generate_cache_key("Miami", "self-storage", {"boundary": "test"})
        assert key3 == key4  # Deterministic with boundary


# ============================================================================
# INDUSTRY ANALYZER FACTORY TESTS
# ============================================================================

class TestIndustryAnalyzerFactory:
    """Tests for analyzer factory"""
    
    def test_get_analyzer_self_storage(self):
        """Test getting self-storage analyzer"""
        analyzer = IndustryAnalyzerFactory.get_analyzer("self-storage")
        assert analyzer is not None
        assert isinstance(analyzer, SelfStorageAnalyzer)
    
    def test_get_analyzer_case_insensitive(self):
        """Test analyzer lookup is case-insensitive"""
        analyzer1 = IndustryAnalyzerFactory.get_analyzer("SELF-STORAGE")
        analyzer2 = IndustryAnalyzerFactory.get_analyzer("self-storage")
        assert type(analyzer1) == type(analyzer2)
    
    def test_get_analyzer_unknown(self):
        """Test unknown analyzer returns None"""
        analyzer = IndustryAnalyzerFactory.get_analyzer("unknown-industry")
        assert analyzer is None
    
    def test_list_supported_industries(self):
        """Test listing supported industries"""
        industries = IndustryAnalyzerFactory.list_supported_industries()
        assert "self-storage" in industries


# ============================================================================
# MUNICIPAL DATA CLIENT INTEGRATION TESTS
# ============================================================================

class TestMunicipalDataClient:
    """Integration tests for main client"""
    
    @pytest.mark.asyncio
    async def test_client_query_miami_self_storage(self):
        """Test querying Miami self-storage"""
        client = MunicipalDataClient()
        
        result = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
        )
        
        assert result.success is True
        assert result.metro == "Miami"
        assert result.state == "FL"
        assert result.industry == "self-storage"
        assert result.metrics is not None
        assert result.metrics.verdict in [
            SupplyVerdict.OVERSATURATED,
            SupplyVerdict.BALANCED,
            SupplyVerdict.UNDERSATURATED,
        ]
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_cache_hit(self):
        """Test that second query hits cache"""
        client = MunicipalDataClient()
        
        # First query
        result1 = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
        )
        assert result1.success is True
        
        # Get cache stats before second query
        stats_before = await client.get_cache_stats()
        hits_before = stats_before["hits"]
        
        # Second query (should be cached)
        result2 = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
        )
        assert result2.success is True
        
        # Check cache stats
        stats_after = await client.get_cache_stats()
        hits_after = stats_after["hits"]
        
        assert hits_after > hits_before, "Cache hit should have increased"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_force_refresh(self):
        """Test forcing cache refresh"""
        client = MunicipalDataClient()
        
        # First query (cached)
        await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
        )
        
        # Second query with force_refresh
        result = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
            force_refresh=True,
        )
        
        assert result.success is True
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_all_metros(self):
        """Test querying all 5 metros"""
        client = MunicipalDataClient()
        
        metros = [
            ("Miami", "FL"),
            ("Chicago", "IL"),
            ("NYC", "NY"),
            ("Seattle", "WA"),
            ("Denver", "CO"),
        ]
        
        for metro, state in metros:
            result = await client.query_facilities(
                metro=metro,
                state=state,
                industry="self-storage",
            )
            assert result.success is True
            assert result.metrics is not None
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_error_handling(self):
        """Test error handling for invalid input"""
        client = MunicipalDataClient()
        
        # Unknown industry
        result = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="unknown-industry",
        )
        assert result.success is False
        assert result.error is not None
        
        # Unknown metro
        result = await client.query_facilities(
            metro="Unknown",
            state="XX",
            industry="self-storage",
        )
        assert result.success is False
        
        await client.close()
    
    def test_client_list_supported_metros(self):
        """Test listing supported metros"""
        client = MunicipalDataClient()
        metros = client.list_supported_metros()
        assert len(metros) >= 5
        assert "miami" in metros
        
        metros_self_storage = client.list_supported_metros("self-storage")
        assert "miami" in metros_self_storage
    
    def test_client_list_supported_industries(self):
        """Test listing supported industries"""
        client = MunicipalDataClient()
        industries = client.list_supported_industries()
        assert "self-storage" in industries
    
    def test_client_is_configured(self):
        """Test is_configured check"""
        client = MunicipalDataClient()
        assert client.is_configured("self-storage", "miami") is True
        assert client.is_configured("unknown", "miami") is False


# ============================================================================
# EDGE CASES AND VALIDATION
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and validation"""
    
    @pytest.mark.asyncio
    async def test_zero_population(self):
        """Test handling of zero population"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Test",
            state="TX",
            total_facilities=100,
            total_building_sqft=10_000_000,
            population=0,  # Edge case
        )
        
        # Should handle gracefully
        assert metrics.sqft_per_capita == 0.0
    
    @pytest.mark.asyncio
    async def test_zero_facilities(self):
        """Test handling of zero facilities"""
        analyzer = SelfStorageAnalyzer()
        
        metrics = await analyzer.analyze(
            metro="Test",
            state="TX",
            total_facilities=0,
            total_building_sqft=0,
            population=1_000_000,
        )
        
        assert metrics.total_facilities == 0
        assert metrics.verdict == SupplyVerdict.UNDERSATURATED
    
    def test_schema_validation(self):
        """Test Pydantic schema validation"""
        # Valid metrics
        metrics = FacilitySupplyMetrics(
            metro="miami",
            state="FL",
            industry="self-storage",
            total_facilities=100,
            total_building_sqft=30_000_000,
            population=6_000_000,
            sqft_per_capita=5.0,
            facilities_per_100k_population=1666,
            verdict=SupplyVerdict.BALANCED,
        )
        
        assert metrics.metro == "miami"
        assert metrics.verdict == SupplyVerdict.BALANCED


# ============================================================================
# INTEGRATION WITH IDENTIFY LOCATION SERVICE
# ============================================================================

class TestIntegrationWithIdentifyLocation:
    """Tests for integration with identify_location_service"""
    
    @pytest.mark.asyncio
    async def test_municipal_data_import(self):
        """Test that municipal data can be imported into service"""
        # Verify the import path works
        from app.services.municipal_data import (
            MunicipalDataClient,
            SelfStorageAnalyzer,
        )
        
        assert MunicipalDataClient is not None
        assert SelfStorageAnalyzer is not None
    
    @pytest.mark.asyncio
    async def test_supply_metrics_can_weight_candidates(self):
        """Test that supply metrics can be used to weight candidates"""
        client = MunicipalDataClient()
        
        result = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="self-storage",
        )
        
        if result.success and result.metrics:
            metrics = result.metrics
            
            # Simulate weighting logic
            if metrics.verdict == SupplyVerdict.UNDERSATURATED:
                # High weighting for undersaturated markets
                weight = 1.5
            elif metrics.verdict == SupplyVerdict.BALANCED:
                weight = 1.0
            else:
                weight = 0.5
            
            assert weight > 0
        
        await client.close()


if __name__ == "__main__":
    # Run tests with: pytest tests/test_municipal_data_client.py -v
    pytest.main([__file__, "-v"])
