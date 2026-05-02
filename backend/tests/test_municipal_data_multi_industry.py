"""
Test Multi-Industry Support for Municipal Data

Verifies that restaurant, fitness, and gas_station analyzers work correctly
with municipal data for Miami (restaurants), Denver (fitness), and Atlanta (gas stations).
"""

import pytest
import asyncio
from app.services.municipal_data.client import MunicipalDataClient
from app.services.municipal_data.industry_analyzers import (
    IndustryAnalyzerFactory,
    RestaurantAnalyzer,
    FitnessAnalyzer,
    GasStationAnalyzer,
)
from app.services.municipal_data.schemas import SupplyVerdict


@pytest.mark.asyncio
async def test_restaurant_analyzer_miami():
    """Test restaurant analyzer with Miami data"""
    analyzer = RestaurantAnalyzer()
    
    # Query Miami for restaurant supply
    metrics = await analyzer.analyze(
        metro="Miami",
        state="FL",
        total_facilities=2450,  # Mock restaurant count
        total_building_sqft=6_125_000,  # Mock sqft
        population=6_091_747,
        confidence=0.95,
        data_source="socrata",
    )
    
    # Assertions
    assert metrics is not None
    assert metrics.metro == "miami"
    assert metrics.industry == "restaurant"
    assert metrics.total_facilities == 2450
    assert metrics.total_facilities > 0, "Should return non-zero facility count"
    assert metrics.sqft_per_capita > 0, "Should have positive sqft per capita"
    assert metrics.verdict in [
        SupplyVerdict.OVERSATURATED,
        SupplyVerdict.BALANCED,
        SupplyVerdict.UNDERSATURATED,
    ]
    assert metrics.confidence == 0.95, "Should use provided confidence"
    assert metrics.data_source == "socrata"
    
    print(f"✅ Restaurant Analysis (Miami):")
    print(f"   Facilities: {metrics.total_facilities}")
    print(f"   Verdict: {metrics.verdict.value}")
    print(f"   Confidence: {metrics.confidence}")


@pytest.mark.asyncio
async def test_fitness_analyzer_denver():
    """Test fitness analyzer with Denver data"""
    analyzer = FitnessAnalyzer()
    
    # Query Denver for fitness supply
    metrics = await analyzer.analyze(
        metro="Denver",
        state="CO",
        total_facilities=285,  # Mock fitness facility count
        total_building_sqft=3_150_000,  # Mock sqft
        population=3_154_794,
        confidence=0.95,
        data_source="socrata",
    )
    
    # Assertions
    assert metrics is not None
    assert metrics.metro == "denver"
    assert metrics.industry == "fitness"
    assert metrics.total_facilities == 285
    assert metrics.total_facilities > 0, "Should return non-zero facility count"
    assert metrics.sqft_per_capita > 0, "Should have positive sqft per capita"
    assert metrics.verdict in [
        SupplyVerdict.OVERSATURATED,
        SupplyVerdict.BALANCED,
        SupplyVerdict.UNDERSATURATED,
    ]
    assert metrics.confidence == 0.95
    assert metrics.data_source == "socrata"
    
    print(f"✅ Fitness Analysis (Denver):")
    print(f"   Facilities: {metrics.total_facilities}")
    print(f"   Verdict: {metrics.verdict.value}")
    print(f"   Confidence: {metrics.confidence}")


@pytest.mark.asyncio
async def test_gas_station_analyzer_atlanta():
    """Test gas station analyzer with Atlanta data"""
    analyzer = GasStationAnalyzer()
    
    # Query Atlanta for gas station supply
    metrics = await analyzer.analyze(
        metro="Atlanta",
        state="GA",
        total_facilities=2145,  # Mock gas station count
        total_building_sqft=0,  # Not used for gas stations
        population=6_089_815,
        confidence=0.95,
        data_source="socrata",
    )
    
    # Assertions
    assert metrics is not None
    assert metrics.metro == "atlanta"
    assert metrics.industry == "gas_station"
    assert metrics.total_facilities == 2145
    assert metrics.total_facilities > 0, "Should return non-zero facility count"
    assert metrics.verdict in [
        SupplyVerdict.OVERSATURATED,
        SupplyVerdict.BALANCED,
        SupplyVerdict.UNDERSATURATED,
    ]
    assert metrics.confidence == 0.95
    assert metrics.data_source == "socrata"
    
    print(f"✅ Gas Station Analysis (Atlanta):")
    print(f"   Facilities: {metrics.total_facilities}")
    print(f"   Verdict: {metrics.verdict.value}")
    print(f"   Confidence: {metrics.confidence}")


@pytest.mark.asyncio
async def test_industry_factory_registration():
    """Test that all industries are registered in the factory"""
    
    # Test self-storage
    analyzer = IndustryAnalyzerFactory.get_analyzer("self-storage")
    assert analyzer is not None
    assert isinstance(analyzer, type)
    
    # Test restaurant
    analyzer = IndustryAnalyzerFactory.get_analyzer("restaurant")
    assert analyzer is not None
    assert isinstance(analyzer, RestaurantAnalyzer)
    
    # Test fitness
    analyzer = IndustryAnalyzerFactory.get_analyzer("fitness")
    assert analyzer is not None
    assert isinstance(analyzer, FitnessAnalyzer)
    
    # Test gas_station
    analyzer = IndustryAnalyzerFactory.get_analyzer("gas_station")
    assert analyzer is not None
    assert isinstance(analyzer, GasStationAnalyzer)
    
    # Test list of supported industries
    industries = IndustryAnalyzerFactory.list_supported_industries()
    assert "self-storage" in industries
    assert "restaurant" in industries
    assert "fitness" in industries
    assert "gas_station" in industries
    
    print(f"✅ All industries registered: {industries}")


@pytest.mark.asyncio
async def test_municipal_data_client_multi_industry():
    """Test MunicipalDataClient with multiple industries"""
    client = MunicipalDataClient()
    
    try:
        # Test restaurant in Miami
        result_restaurant = await client.query_facilities(
            metro="Miami",
            state="FL",
            industry="restaurant",
        )
        
        assert result_restaurant.success, f"Restaurant query failed: {result_restaurant.error}"
        assert result_restaurant.metrics.industry == "restaurant"
        assert result_restaurant.metrics.total_facilities > 0
        assert result_restaurant.metrics.verdict is not None
        print(f"✅ Restaurant (Miami): {result_restaurant.metrics.verdict.value}")
        
        # Test fitness in Denver
        result_fitness = await client.query_facilities(
            metro="Denver",
            state="CO",
            industry="fitness",
        )
        
        assert result_fitness.success, f"Fitness query failed: {result_fitness.error}"
        assert result_fitness.metrics.industry == "fitness"
        assert result_fitness.metrics.total_facilities > 0
        assert result_fitness.metrics.verdict is not None
        print(f"✅ Fitness (Denver): {result_fitness.metrics.verdict.value}")
        
        # Test gas_station in Atlanta
        result_gas = await client.query_facilities(
            metro="Atlanta",
            state="GA",
            industry="gas_station",
        )
        
        assert result_gas.success, f"Gas station query failed: {result_gas.error}"
        assert result_gas.metrics.industry == "gas_station"
        assert result_gas.metrics.total_facilities > 0
        assert result_gas.metrics.verdict is not None
        print(f"✅ Gas Station (Atlanta): {result_gas.metrics.verdict.value}")
    
    finally:
        await client.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
