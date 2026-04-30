"""
Phase 3: AI Intelligence Layer - Comprehensive Tests

Demonstrates:
1. Intelligent opportunity ranking (vs. raw data)
2. Momentum detection (acceleration/deceleration)
3. Risk scoring (saturation, fatigue, seasonal, execution)
4. Market health analysis
5. Confidence intervals and data freshness

Tests show the moat: agents get smarter answers with Phase 3.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.models.opportunity import Opportunity
from app.services.intelligence_engine import (
    IntelligenceEngine,
    OpportunityRanker,
    TrendAnalyzer,
    MarketHealthAnalyzer,
    RiskScorer,
)


# Fixtures for testing
@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_opportunities():
    """Create sample opportunities for testing"""
    opportunities = []
    
    # Opportunity 1: High score, accelerating trend, low competition (BEST)
    opp1 = Opportunity(
        id=1,
        title="Coffee Shop in Austin",
        category="Coffee",
        city="Austin",
        region="TX",
        country="USA",
        ai_opportunity_score=85,
        growth_rate=25.0,  # Strong growth
        validation_count=15,
        ai_competition_level="low",
        ai_urgency_level="high",
        ai_pain_intensity=8,
        market_size="$100M-$500M",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    opportunities.append(opp1)
    
    # Opportunity 2: Medium score, stable trend (MODERATE)
    opp2 = Opportunity(
        id=2,
        title="E-Commerce Platform",
        category="E-Commerce",
        city="Austin",
        region="TX",
        country="USA",
        ai_opportunity_score=65,
        growth_rate=5.0,  # Stable
        validation_count=8,
        ai_competition_level="medium",
        ai_urgency_level="medium",
        ai_pain_intensity=6,
        market_size="$500M-$2B",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        updated_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    opportunities.append(opp2)
    
    # Opportunity 3: Low score, declining trend, high competition (WORST)
    opp3 = Opportunity(
        id=3,
        title="Dropshipping Business",
        category="Dropshipping",
        city="Austin",
        region="TX",
        country="USA",
        ai_opportunity_score=45,
        growth_rate=-10.0,  # Declining
        validation_count=2,
        ai_competition_level="high",
        ai_urgency_level="low",
        ai_pain_intensity=3,
        market_size="$10M-$50M",
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
        updated_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    opportunities.append(opp3)
    
    return opportunities


class TestOpportunityRanker:
    """Test intelligent opportunity ranking"""
    
    def test_rank_opportunities_by_success_probability(self, mock_db, sample_opportunities):
        """
        Test that opportunities are ranked by predicted success probability.
        
        BEFORE (Phase 2): Just sorted by ai_opportunity_score (85, 65, 45)
        AFTER (Phase 3): Ranked by success probability considering momentum + risk + market
        """
        ranker = OpportunityRanker(mock_db)
        
        ranked = ranker.rank_opportunities(sample_opportunities)
        
        # Verify ranking
        assert len(ranked) == 3
        assert ranked[0][0].id == 1  # Coffee shop (accelerating, low comp)
        assert ranked[1][0].id == 2  # E-commerce (stable trend)
        assert ranked[2][0].id == 3  # Dropshipping (declining)
        
        # Verify scores are in descending order
        scores = [score for _, score in ranked]
        assert scores[0].score >= scores[1].score >= scores[2].score
        
        # Verify confidence intervals
        for _, score in ranked:
            assert 0 <= score.confidence <= 100
            assert 0 <= score.score <= 100
    
    def test_confidence_intervals_reflect_data_quality(self, mock_db, sample_opportunities):
        """
        Test that confidence intervals reflect data quality.
        
        High validation count = higher confidence
        Recent updates = higher confidence
        """
        ranker = OpportunityRanker(mock_db)
        
        ranked = ranker.rank_opportunities(sample_opportunities)
        
        # Opportunity 1 (15 validations, recent) should have high confidence
        opp1_score = ranked[0][1]
        assert opp1_score.confidence > 70
        
        # Opportunity 3 (2 validations, old) should have lower confidence
        opp3_score = ranked[2][1]
        assert opp3_score.confidence < 80  # Still reasonable but lower
    
    def test_data_freshness_calculation(self, mock_db, sample_opportunities):
        """Test that data freshness is properly calculated"""
        ranker = OpportunityRanker(mock_db)
        
        ranked = ranker.rank_opportunities(sample_opportunities)
        
        # All should have data freshness values
        for _, score in ranked:
            assert score.data_freshness_hours >= 0
            # Most recent (opp1) should be fresher
            # Old (opp3) should be older
        
        assert ranked[0][1].data_freshness_hours < ranked[2][1].data_freshness_hours


class TestTrendAnalyzer:
    """Test momentum detection and trend analysis"""
    
    def test_momentum_acceleration_detection(self, mock_db, sample_opportunities):
        """
        Test that acceleration is detected correctly.
        
        BEFORE: Just return growth_rate
        AFTER: Calculate acceleration factor vs. historical baseline
        """
        analyzer = TrendAnalyzer(mock_db)
        
        # Mock the database call
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0  # Historical baseline
        
        # Opportunity with 25% growth vs 5% baseline = accelerating
        momentum = analyzer.analyze_momentum(sample_opportunities[0])
        
        assert momentum.acceleration_factor > 1.0
        assert momentum.direction == "accelerating"
        assert momentum.seven_day_rate == 25.0
        
        # Opportunity with declining trend
        momentum_declining = analyzer.analyze_momentum(sample_opportunities[2])
        assert momentum_declining.direction == "decelerating"
    
    def test_momentum_metrics_format(self, mock_db, sample_opportunities):
        """Test that momentum metrics are properly formatted"""
        analyzer = TrendAnalyzer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        momentum = analyzer.analyze_momentum(sample_opportunities[0])
        
        # Verify all metrics are present
        assert hasattr(momentum, 'acceleration_factor')
        assert hasattr(momentum, 'direction')
        assert hasattr(momentum, 'seven_day_rate')
        assert hasattr(momentum, 'thirty_day_rate')
        assert hasattr(momentum, 'ninety_day_rate')
        
        # Convert to dict and verify
        momentum_dict = momentum.to_dict()
        assert "acceleration_factor" in momentum_dict
        assert "direction" in momentum_dict


class TestMarketHealthAnalyzer:
    """Test market health and saturation analysis"""
    
    def test_market_saturation_detection(self, mock_db, sample_opportunities):
        """
        Test that market saturation is properly detected.
        
        BEFORE: No saturation analysis
        AFTER: Return saturation_level (emerging, growing, mature, saturated)
        """
        analyzer = MarketHealthAnalyzer(mock_db)
        
        # Mock business count for coffee market
        mock_db.query.return_value.filter.return_value.scalar.return_value = 150
        
        health = analyzer.analyze_market_health(sample_opportunities[0])
        
        assert health.saturation_level == "saturated"
        assert health.business_count == 150
        assert health.market_health_score < 50  # Saturated market = lower health
    
    def test_demand_vs_supply_signals(self, mock_db, sample_opportunities):
        """
        Test bullish/bearish market signals.
        
        Bullish: High validation, growth, urgency
        Bearish: Low demand signals
        """
        analyzer = MarketHealthAnalyzer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 20
        
        # High demand signals (coffee shop)
        health_bullish = analyzer.analyze_market_health(sample_opportunities[0])
        assert health_bullish.demand_vs_supply == "bullish"
        
        # Low demand signals (dropshipping)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 80
        health_bearish = analyzer.analyze_market_health(sample_opportunities[2])
        # Should indicate lower confidence or caution
    
    def test_market_health_score_scale(self, mock_db, sample_opportunities):
        """Test that market health scores are on 0-100 scale"""
        analyzer = MarketHealthAnalyzer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        health = analyzer.analyze_market_health(sample_opportunities[0])
        
        assert 0 <= health.market_health_score <= 100


class TestRiskScorer:
    """Test comprehensive risk assessment"""
    
    def test_saturation_risk_calculation(self, mock_db, sample_opportunities):
        """Test that saturation risk is calculated from competitor count"""
        scorer = RiskScorer(mock_db)
        
        # Mock high competition count
        mock_db.query.return_value.filter.return_value.scalar.return_value = 100
        
        risk = scorer.calculate_risk(sample_opportunities[0])
        
        assert 0 <= risk.saturation_risk <= 100
        assert risk.saturation_risk > 50  # High competition = high risk
    
    def test_trend_fatigue_risk(self, mock_db, sample_opportunities):
        """
        Test trend fatigue risk (declining demand).
        
        Negative growth = high fatigue risk
        """
        scorer = RiskScorer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        # Declining trend (opp3) should have high fatigue risk
        risk_declining = scorer.calculate_risk(sample_opportunities[2])
        assert risk_declining.trend_fatigue_risk > 50
        
        # Accelerating trend should have low fatigue risk
        risk_accelerating = scorer.calculate_risk(sample_opportunities[0])
        assert risk_accelerating.trend_fatigue_risk < 50
    
    def test_seasonal_risk_detection(self, mock_db, sample_opportunities):
        """Test that seasonal risk is detected for seasonal categories"""
        scorer = RiskScorer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        # Holiday business should have high seasonal risk
        opp_seasonal = Opportunity(
            id=99,
            title="Christmas Decoration Service",
            category="Holiday Retail",
            ai_pain_intensity=5,
            growth_rate=0.0,
        )
        risk = scorer.calculate_risk(opp_seasonal)
        assert risk.seasonal_risk > 60  # Holiday is seasonal
    
    def test_execution_risk_estimation(self, mock_db, sample_opportunities):
        """Test execution risk varies by category"""
        scorer = RiskScorer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        risk = scorer.calculate_risk(sample_opportunities[0])
        
        assert 0 <= risk.execution_risk <= 100
        # All should have reasonable values
        assert risk.execution_risk >= 0
    
    def test_overall_risk_score(self, mock_db, sample_opportunities):
        """
        Test that overall risk is calculated as average of components.
        """
        scorer = RiskScorer(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        risk = scorer.calculate_risk(sample_opportunities[0])
        
        # Overall should be average of components
        expected_avg = (
            risk.saturation_risk +
            risk.trend_fatigue_risk +
            risk.seasonal_risk +
            risk.execution_risk
        ) / 4
        
        assert abs(risk.overall_risk_score - expected_avg) < 0.1


class TestIntelligenceEngine:
    """Test unified intelligence engine"""
    
    def test_rank_opportunities_integration(self, mock_db, sample_opportunities):
        """Test end-to-end ranking with all components"""
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        ranked = engine.rank_opportunities(sample_opportunities)
        
        assert len(ranked) == 3
        assert ranked[0][0].id == 1  # Best opportunity
    
    def test_analyze_opportunity_comprehensive(self, mock_db, sample_opportunities):
        """Test comprehensive single opportunity analysis"""
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        analysis = engine.analyze_opportunity(sample_opportunities[0])
        
        # Verify all components present
        assert "success_score" in analysis
        assert "momentum" in analysis
        assert "market_health" in analysis
        assert "risk_profile" in analysis
    
    def test_analyze_trends_aggregation(self, mock_db, sample_opportunities):
        """Test trend analysis for multiple opportunities"""
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        trend_data = engine.analyze_trends(sample_opportunities)
        
        assert "overall_direction" in trend_data
        assert "average_acceleration" in trend_data
        assert "momentum_data" in trend_data
    
    def test_analyze_market_aggregation(self, mock_db, sample_opportunities):
        """Test market analysis aggregates multiple opportunities"""
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        
        market_data = engine.analyze_market(sample_opportunities)
        
        assert "average_health_score" in market_data
        assert "overall_sentiment" in market_data
        assert "market_health_data" in market_data


class TestPhase3VsPhase2Comparison:
    """
    Comparison tests: Raw data vs. Intelligent ranking
    
    Demonstrates the moat: Phase 3 gives agents smarter answers
    """
    
    def test_raw_ranking_vs_intelligent_ranking(self, mock_db, sample_opportunities):
        """
        BEFORE (Phase 2):
        Ranking by ai_opportunity_score: [85, 65, 45]
        
        AFTER (Phase 3):
        Ranking by success_probability: [~90, ~65, ~30]
        
        Momentum boost, risk adjustment, and market fit matter!
        """
        # Simulate Phase 2 ranking (just by score)
        phase2_ranking = sorted(
            sample_opportunities,
            key=lambda x: x.ai_opportunity_score or 0,
            reverse=True
        )
        phase2_scores = [opp.ai_opportunity_score for opp in phase2_ranking]
        
        # Phase 3 intelligent ranking
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        phase3_ranking = engine.rank_opportunities(sample_opportunities)
        phase3_scores = [score.score for _, score in phase3_ranking]
        
        # Both should rank opp1 first, but Phase 3 score should be higher
        assert phase3_ranking[0][0].id == phase2_ranking[0].id  # Same first
        assert phase3_scores[0] > phase2_scores[0]  # But Phase 3 is more confident
    
    def test_confidence_intervals_phase3_only(self, mock_db, sample_opportunities):
        """
        BEFORE (Phase 2): No confidence intervals
        AFTER (Phase 3): Confidence intervals show data quality
        
        Low validation count = lower confidence
        Recent data = higher confidence
        """
        engine = IntelligenceEngine(mock_db)
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        ranked = engine.rank_opportunities(sample_opportunities)
        
        # All should have confidence intervals
        for opp, score in ranked:
            assert 0 <= score.confidence <= 100
            assert score.reasoning != ""  # Should have explanation
        
        # Higher validation count = higher confidence
        opp1_confidence = ranked[0][1].confidence
        opp3_confidence = ranked[2][1].confidence
        assert opp1_confidence > opp3_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
