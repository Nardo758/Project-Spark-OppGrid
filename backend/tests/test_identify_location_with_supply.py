"""
Integration Test: Identify Location with Supply Analysis

Tests end-to-end flow of wiring real supply data into candidate profile scoring.

Scenario: User searches for "self-storage in Miami"
Expected: Candidates returned with supply-adjusted scores reflecting that
          Miami market is oversaturated (16.4 sqft/capita).
"""

import pytest
import asyncio
from app.services.success_profile.candidate_profile_builder import CandidateProfileBuilder
from app.services.municipal_data.client import MunicipalDataClient
from app.schemas.identify_location import CandidateSource, MeasuredSignal


@pytest.mark.asyncio
async def test_candidate_profile_with_supply_analysis():
    """Test building a candidate profile with supply analysis"""
    
    # Initialize client and builder
    client = MunicipalDataClient()
    builder = CandidateProfileBuilder(municipal_data_client=client)
    
    try:
        # Build a candidate profile with supply analysis
        profile = builder.build_profile(
            candidate_id="test_wynwood_001",
            location_name="Wynwood, Miami",
            latitude=25.8419,
            longitude=-80.1995,
            source=CandidateSource.NAMED_MARKET,
            city="Miami",
            state="FL",
            neighborhood="Wynwood",
            zip_code="33137",
            signal_sources={
                "foot_traffic": {
                    "daily_avg": 800,
                    "growth_pct": 5.0,
                    "recency_score": 0.85,
                },
                "demographics": {
                    "population": 45000,
                    "median_income": 55000,
                    "target_match": 0.72,
                },
                "competition": {
                    "competitor_count": 3,
                    "market_population": 100000,
                },
            },
            industry="self-storage",
            metro="Miami",
        )
        
        # Verify profile was built
        assert profile is not None
        assert profile.candidate_id == "test_wynwood_001"
        assert profile.location_name == "Wynwood, Miami"
        assert profile.overall_score > 0
        
        # Verify supply metrics were included
        assert profile.supply_verdict is not None, "Supply verdict should be set"
        assert profile.supply_metrics is not None, "Supply metrics should be set"
        assert profile.supply_score_adjustment is not None
        
        print(f"✅ Candidate Profile Built:")
        print(f"   Location: {profile.location_name}")
        print(f"   Overall Score: {profile.overall_score:.1f}")
        print(f"   Archetype: {profile.archetype}")
        print(f"   Supply Verdict: {profile.supply_verdict}")
        print(f"   Supply Adjustment: {profile.supply_score_adjustment:.2f}x")
        
        # If oversaturated, score should be penalized
        if profile.supply_verdict == "oversaturated":
            assert profile.supply_score_adjustment == 0.75, "Oversaturated should reduce score by 25%"
            print(f"   ✓ Oversaturated market correctly penalizes score")
        elif profile.supply_verdict == "undersaturated":
            assert profile.supply_score_adjustment == 1.25, "Undersaturated should boost score by 25%"
            print(f"   ✓ Undersaturated market correctly boosts score")
        else:
            assert profile.supply_score_adjustment == 1.0
            print(f"   ✓ Balanced market has no score adjustment")
    
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_multiple_candidates_with_supply_context():
    """Test building multiple candidate profiles for same metro/industry"""
    
    client = MunicipalDataClient()
    builder = CandidateProfileBuilder(municipal_data_client=client)
    
    try:
        # Miami self-storage candidates
        candidates = [
            {
                "id": "miami_001",
                "name": "Wynwood",
                "lat": 25.8419,
                "lon": -80.1995,
                "foot_traffic": {"daily_avg": 800, "growth_pct": 5.0, "recency_score": 0.85},
                "demographics": {"population": 45000, "median_income": 55000, "target_match": 0.72},
                "competition": {"competitor_count": 3, "market_population": 100000},
            },
            {
                "id": "miami_002",
                "name": "Brickell",
                "lat": 25.7617,
                "lon": -80.1918,
                "foot_traffic": {"daily_avg": 1200, "growth_pct": 8.0, "recency_score": 0.92},
                "demographics": {"population": 70000, "median_income": 85000, "target_match": 0.85},
                "competition": {"competitor_count": 8, "market_population": 150000},
            },
            {
                "id": "miami_003",
                "name": "Coral Gables",
                "lat": 25.7440,
                "lon": -80.2735,
                "foot_traffic": {"daily_avg": 600, "growth_pct": 2.0, "recency_score": 0.70},
                "demographics": {"population": 52000, "median_income": 95000, "target_match": 0.60},
                "competition": {"competitor_count": 5, "market_population": 120000},
            },
        ]
        
        profiles = []
        for candidate in candidates:
            profile = builder.build_profile(
                candidate_id=candidate["id"],
                location_name=candidate["name"],
                latitude=candidate["lat"],
                longitude=candidate["lon"],
                source=CandidateSource.NAMED_MARKET,
                city="Miami",
                state="FL",
                neighborhood=candidate["name"],
                signal_sources={
                    "foot_traffic": candidate["foot_traffic"],
                    "demographics": candidate["demographics"],
                    "competition": candidate["competition"],
                },
                industry="self-storage",
                metro="Miami",
            )
            profiles.append(profile)
        
        # Verify all profiles
        assert len(profiles) == 3
        
        # All should have same supply verdict (since they're in same market)
        verdicts = [p.supply_verdict for p in profiles]
        assert len(set(verdicts)) == 1, "All candidates in same market should have same supply verdict"
        
        print(f"✅ Multiple Candidates (Miami Self-Storage):")
        for profile in profiles:
            print(f"   {profile.location_name:20} | Score: {profile.overall_score:5.1f} | "
                  f"Verdict: {profile.supply_verdict:15} | Adjustment: {profile.supply_score_adjustment:.2f}x")
        
        # Scores should vary due to different signals, but supply adjustment is constant
        scores = [p.overall_score for p in profiles]
        assert len(set(scores)) > 1, "Scores should vary based on location signals"
        
        # Adjustments should all be the same
        adjustments = [p.supply_score_adjustment for p in profiles]
        assert len(set(adjustments)) == 1, "All should have same supply adjustment in same market"
        
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_supply_verdict_narrative():
    """Test that supply verdict is included in candidate rationale"""
    
    client = MunicipalDataClient()
    builder = CandidateProfileBuilder(municipal_data_client=client)
    
    try:
        profile = builder.build_profile(
            candidate_id="test_001",
            location_name="Downtown Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            source=CandidateSource.NAMED_MARKET,
            city="Chicago",
            state="IL",
            signal_sources={
                "foot_traffic": {"daily_avg": 1500, "growth_pct": 10.0, "recency_score": 0.90},
                "demographics": {"population": 100000, "median_income": 75000, "target_match": 0.80},
                "competition": {"competitor_count": 5, "market_population": 200000},
            },
            industry="self-storage",
            metro="Chicago",
        )
        
        # Verify supply data is present
        assert profile.supply_verdict is not None
        assert profile.supply_metrics is not None
        
        # Build a narrative that includes supply context
        narrative = (
            f"Location: {profile.location_name} ({profile.archetype}). "
            f"Score: {profile.overall_score:.0f}/100. "
        )
        
        if profile.supply_verdict:
            narrative += (
                f"Market is {profile.supply_verdict.upper()} "
                f"({profile.supply_metrics.get('sqft_per_capita', 0):.2f} sqft/capita). "
            )
        
        if profile.supply_score_adjustment and profile.supply_score_adjustment != 1.0:
            narrative += (
                f"Score adjusted {profile.supply_score_adjustment:.2f}x for market saturation. "
            )
        
        print(f"✅ Supply-Aware Narrative:")
        print(f"   {narrative}")
        
        assert "OVERSATURATED" in narrative or \
               "BALANCED" in narrative or \
               "UNDERSATURATED" in narrative
    
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_identify_location_supply_weighting():
    """Test the full supply-weighted scoring logic"""
    
    client = MunicipalDataClient()
    builder = CandidateProfileBuilder(municipal_data_client=client)
    
    try:
        # Test Miami self-storage (should be oversaturated)
        profile_miami = builder.build_profile(
            candidate_id="miami_test",
            location_name="Miami Test Location",
            latitude=25.76,
            longitude=-80.19,
            source=CandidateSource.NAMED_MARKET,
            city="Miami",
            state="FL",
            signal_sources={
                "foot_traffic": {"daily_avg": 1000, "growth_pct": 5.0, "recency_score": 0.8},
                "demographics": {"population": 50000, "median_income": 60000, "target_match": 0.7},
                "competition": {"competitor_count": 5, "market_population": 100000},
            },
            industry="self-storage",
            metro="Miami",
        )
        
        # Test Denver self-storage (for comparison)
        profile_denver = builder.build_profile(
            candidate_id="denver_test",
            location_name="Denver Test Location",
            latitude=39.74,
            longitude=-104.99,
            source=CandidateSource.NAMED_MARKET,
            city="Denver",
            state="CO",
            signal_sources={
                "foot_traffic": {"daily_avg": 1000, "growth_pct": 5.0, "recency_score": 0.8},
                "demographics": {"population": 50000, "median_income": 60000, "target_match": 0.7},
                "competition": {"competitor_count": 5, "market_population": 100000},
            },
            industry="self-storage",
            metro="Denver",
        )
        
        print(f"✅ Supply-Weighted Scoring:")
        print(f"   Miami (likely oversaturated):")
        print(f"     - Verdict: {profile_miami.supply_verdict}")
        print(f"     - Adjustment: {profile_miami.supply_score_adjustment:.2f}x")
        print(f"     - Score: {profile_miami.overall_score:.1f}")
        print(f"   Denver (likely balanced):")
        print(f"     - Verdict: {profile_denver.supply_verdict}")
        print(f"     - Adjustment: {profile_denver.supply_score_adjustment:.2f}x")
        print(f"     - Score: {profile_denver.overall_score:.1f}")
        
        # Both had same input signals, so Miami's lower score would be due to supply
        if profile_miami.supply_verdict == "oversaturated" and \
           profile_denver.supply_verdict in ["balanced", "undersaturated"]:
            assert profile_miami.supply_score_adjustment <= profile_denver.supply_score_adjustment
            print(f"   ✓ Oversaturated market has lower adjustment than balanced/undersaturated")
    
    finally:
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
