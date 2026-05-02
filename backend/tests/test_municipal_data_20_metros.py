"""
Test Self-Storage Supply Analysis Across All 20 Metros

Verifies that municipal data queries work across all 20 configured metros,
using Socrata data (0.95 confidence) instead of fallback (0.60 confidence).
"""

import pytest
import asyncio
from app.services.municipal_data.client import MunicipalDataClient
from app.services.municipal_data.land_use_mapping import LandUseMapping
from app.services.municipal_data.schemas import SupplyVerdict


# All 20 configured metros
METROS = [
    ("Miami", "FL"),
    ("Chicago", "IL"),
    ("NYC", "NY"),
    ("Seattle", "WA"),
    ("Denver", "CO"),
    ("Atlanta", "GA"),
    ("Boston", "MA"),
    ("Dallas", "TX"),
    ("Houston", "TX"),
    ("Los Angeles", "CA"),
    ("Phoenix", "AZ"),
    ("San Francisco", "CA"),
    ("San Diego", "CA"),
    ("Washington DC", "DC"),
    ("Austin", "TX"),
    ("Charlotte", "NC"),
    ("Nashville", "TN"),
    ("Portland", "OR"),
    ("Tampa", "FL"),
    ("Philadelphia", "PA"),
]


@pytest.mark.asyncio
async def test_all_20_metros_self_storage():
    """Test self-storage supply analysis for all 20 metros"""
    client = MunicipalDataClient()
    
    results = []
    
    try:
        for metro, state in METROS:
            result = await client.query_facilities(
                metro=metro,
                state=state,
                industry="self-storage",
            )
            
            # Verify success
            assert result.success, f"{metro}: Query failed - {result.error}"
            
            # Verify metrics
            metrics = result.metrics
            assert metrics.total_facilities > 0, f"{metro}: No facilities found"
            assert metrics.sqft_per_capita > 0, f"{metro}: Invalid sqft per capita"
            assert metrics.verdict in [
                SupplyVerdict.OVERSATURATED,
                SupplyVerdict.BALANCED,
                SupplyVerdict.UNDERSATURATED,
            ], f"{metro}: Invalid verdict"
            
            # Verify data quality (should be Socrata, not fallback)
            assert metrics.confidence >= 0.90, f"{metro}: Low confidence {metrics.confidence}"
            assert metrics.data_source == "socrata", f"{metro}: Not using Socrata"
            
            # Record result
            results.append({
                "metro": metro,
                "state": state,
                "facilities": metrics.total_facilities,
                "sqft_per_capita": metrics.sqft_per_capita,
                "verdict": metrics.verdict.value,
                "confidence": metrics.confidence,
                "data_source": metrics.data_source,
            })
            
            print(f"✅ {metro:20} | Facilities: {metrics.total_facilities:4} | "
                  f"Verdict: {metrics.verdict.value:15} | Confidence: {metrics.confidence:.2f}")
    
    finally:
        await client.close()
    
    # Verify we got all 20
    assert len(results) == 20, f"Expected 20 metros, got {len(results)}"
    
    # Verify verdicts vary (not all the same)
    verdicts = set(r["verdict"] for r in results)
    assert len(verdicts) > 1, "Verdicts should vary across metros"
    
    print(f"\n✅ All 20 metros tested successfully!")
    print(f"   Verdicts: {verdicts}")
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"   Total metros tested: {len(results)}")
    print(f"   All using Socrata: {all(r['data_source'] == 'socrata' for r in results)}")
    print(f"   Confidence 0.95: {all(r['confidence'] == 0.95 for r in results)}")
    print(f"   Verdict distribution:")
    for verdict in ['oversaturated', 'balanced', 'undersaturated']:
        count = len([r for r in results if r['verdict'] == verdict])
        if count > 0:
            print(f"     - {verdict}: {count}")


@pytest.mark.asyncio
async def test_metro_configuration_coverage():
    """Verify all 20 metros are configured in land use mapping"""
    mapper = LandUseMapping()
    
    for metro, state in METROS:
        # Check that metro is configured for self-storage
        is_configured = mapper.is_configured("self-storage", metro)
        assert is_configured, f"{metro} not configured for self-storage"
        
        # Get configuration
        config = mapper.get_metro_config("self-storage", metro)
        assert config is not None
        assert config.get("codes") is not None
        assert len(config.get("codes", [])) > 0
        
        # Get population
        pop = mapper.get_population(metro, state)
        assert pop > 0, f"{metro}: Invalid population {pop}"
    
    print(f"✅ All 20 metros are properly configured")


@pytest.mark.asyncio
async def test_verdict_consistency():
    """Test that verdicts are consistent and reasonable"""
    client = MunicipalDataClient()
    
    try:
        results = []
        
        # Test a few key metros
        test_metros = [
            ("Miami", "FL"),
            ("Chicago", "IL"),
            ("NYC", "NY"),
            ("Denver", "CO"),
            ("Austin", "TX"),
        ]
        
        for metro, state in test_metros:
            result = await client.query_facilities(
                metro=metro,
                state=state,
                industry="self-storage",
                force_refresh=True,  # Don't use cache
            )
            
            assert result.success
            metrics = result.metrics
            
            # Verify verdict logic is consistent
            if metrics.verdict == SupplyVerdict.OVERSATURATED:
                assert metrics.sqft_per_capita > 7.0
            elif metrics.verdict == SupplyVerdict.UNDERSATURATED:
                assert metrics.sqft_per_capita < 5.0
            else:  # BALANCED
                assert 5.0 <= metrics.sqft_per_capita <= 7.0
            
            results.append({
                "metro": metro,
                "sqft_per_capita": metrics.sqft_per_capita,
                "verdict": metrics.verdict.value,
            })
            
            print(f"✅ {metro}: {metrics.sqft_per_capita:.2f} sqft/capita → {metrics.verdict.value}")
    
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_facility_count_reasonableness():
    """Verify facility counts are reasonable (not 0, not unrealistic)"""
    client = MunicipalDataClient()
    
    try:
        for metro, state in METROS:
            result = await client.query_facilities(
                metro=metro,
                state=state,
                industry="self-storage",
            )
            
            assert result.success
            
            facilities = result.metrics.total_facilities
            population = result.metrics.population
            
            # Facility count should be between 1 and 1 per 5,000 people (max reasonable)
            assert facilities > 0, f"{metro}: Zero facilities"
            max_reasonable = population // 5_000
            assert facilities <= max_reasonable * 2, \
                f"{metro}: Unrealistic facility count {facilities} for population {population}"
            
            facilities_per_100k = result.metrics.facilities_per_100k_population
            assert 0 < facilities_per_100k < 50, \
                f"{metro}: Unrealistic facilities per 100k: {facilities_per_100k}"
    
    finally:
        await client.close()
    
    print(f"✅ All facility counts are reasonable")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
