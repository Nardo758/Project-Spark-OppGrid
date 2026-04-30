"""
Phase 3: AI Intelligence Layer for Agent API

Provides intelligent, predictive analysis for opportunities, trends, and market data.
Enhances raw metrics with:
- Predictive opportunity ranking (success probability NOW)
- Momentum detection (trend acceleration/deceleration)
- Market health scoring (saturation, bullish/bearish signals)
- Risk scoring (saturation, fatigue, seasonality, execution)
- Historical pattern matching

The intelligence engine is the moat: agents get smarter answers than anywhere else.
"""
import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceScore:
    """A scored insight with confidence interval"""
    score: float  # 0-100
    confidence: float  # 0-100 (how sure are we?)
    data_freshness_hours: int  # How old is the underlying data?
    reasoning: str  # Plain English explanation
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MomentumMetric:
    """Trend acceleration/deceleration data"""
    acceleration_factor: float  # 1.0 = neutral, 1.45 = 45% faster
    direction: str  # "accelerating", "decelerating", "stable"
    seven_day_rate: float  # Growth rate in last 7 days
    thirty_day_rate: float  # Growth rate in last 30 days
    ninety_day_rate: float  # Growth rate in last 90 days
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketHealthSnapshot:
    """Market health indicator"""
    market_health_score: float  # 0-100 (100 = hot, 20 = declining)
    saturation_level: str  # "emerging", "growing", "mature", "saturated"
    demand_vs_supply: str  # "bullish", "neutral", "bearish"
    business_count: int  # Number of businesses in this market vertical
    confidence: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskProfile:
    """Comprehensive risk assessment"""
    overall_risk_score: float  # 0-100 (100 = critical risk)
    saturation_risk: float  # 0-100 (too many competitors?)
    trend_fatigue_risk: float  # 0-100 (is demand declining?)
    seasonal_risk: float  # 0-100 (is this seasonal business?)
    execution_risk: float  # 0-100 (how hard to execute?)
    confidence: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OpportunityRanker:
    """
    Ranks opportunities by predicted success probability RIGHT NOW.
    
    Combines:
    - AI confidence score
    - Momentum (is this trend accelerating?)
    - Risk profile (what could go wrong?)
    - Market fit (how hot is this market?)
    
    Result: Opportunities ranked by "likelihood of success RIGHT NOW"
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def rank_opportunities(
        self,
        opportunities: List[Opportunity],
        trend_analyzer: Optional['TrendAnalyzer'] = None,
        risk_scorer: Optional['RiskScorer'] = None,
        market_analyzer: Optional['MarketHealthAnalyzer'] = None,
    ) -> List[Tuple[Opportunity, IntelligenceScore]]:
        """
        Rank opportunities by predicted success probability.
        
        Returns: List of (opportunity, success_score) tuples, ranked by score DESC
        """
        results = []
        
        for opp in opportunities:
            # Base score from AI analysis
            base_score = float(opp.ai_opportunity_score or 50)
            
            # Momentum boost (is this trend accelerating?)
            momentum_boost = 0.0
            if trend_analyzer:
                momentum = trend_analyzer.analyze_momentum(opp)
                if momentum.direction == "accelerating":
                    momentum_boost = 10.0 * (momentum.acceleration_factor - 1.0)
            
            # Risk adjustment (subtract risk)
            risk_adjustment = 0.0
            if risk_scorer:
                risk = risk_scorer.calculate_risk(opp)
                risk_adjustment = -(risk.overall_risk_score * 0.3)  # 30% impact
            
            # Market fit boost (is this market hot?)
            market_boost = 0.0
            if market_analyzer:
                market_health = market_analyzer.analyze_market_health(opp)
                if market_health.demand_vs_supply == "bullish":
                    market_boost = 5.0
            
            # Calculate final score
            final_score = base_score + momentum_boost + risk_adjustment + market_boost
            final_score = max(0.0, min(final_score, 100.0))
            
            # Confidence: lower if we have less data
            confidence = 70.0  # Base confidence
            if opp.validation_count and opp.validation_count > 10:
                confidence = 85.0
            if not opp.ai_opportunity_score:
                confidence = 50.0
            
            # Data freshness
            data_freshness = self._calculate_data_freshness(opp)
            
            score = IntelligenceScore(
                score=final_score,
                confidence=confidence,
                data_freshness_hours=data_freshness,
                reasoning=self._generate_reasoning(
                    opp, base_score, momentum_boost, risk_adjustment, market_boost
                )
            )
            
            results.append((opp, score))
        
        # Sort by score DESC
        results.sort(key=lambda x: x[1].score, reverse=True)
        return results
    
    def _calculate_data_freshness(self, opp: Opportunity) -> int:
        """Calculate how old the underlying data is (in hours)"""
        now = datetime.now(timezone.utc)
        if opp.updated_at:
            age = now - opp.updated_at
            return int(age.total_seconds() / 3600)
        else:
            return 24 * 365  # 1 year if unknown
    
    def _generate_reasoning(
        self,
        opp: Opportunity,
        base: float,
        momentum: float,
        risk: float,
        market: float
    ) -> str:
        """Generate plain English explanation of the score"""
        parts = []
        
        parts.append(f"Base AI score: {base:.0f}")
        
        if momentum > 0:
            parts.append(f"Momentum boost: +{momentum:.0f} (trend accelerating)")
        elif momentum < 0:
            parts.append(f"Momentum penalty: {momentum:.0f} (trend slowing)")
        
        if risk < 0:
            parts.append(f"Risk penalty: {risk:.0f}")
        
        if market > 0:
            parts.append(f"Market boost: +{market:.0f} (strong demand)")
        
        return " • ".join(parts)


class TrendAnalyzer:
    """
    Detects trend momentum and acceleration.
    
    Compares:
    - 7-day growth vs. historical average
    - 30-day growth vs. historical average
    - 90-day growth vs. historical average
    
    Returns: Whether trend is accelerating, decelerating, or stable
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_momentum(self, opportunity: Opportunity) -> MomentumMetric:
        """
        Analyze trend momentum for a single opportunity.
        
        If we have growth_rate, use it as the current trajectory.
        Calculate acceleration by comparing to historical baseline.
        """
        # Get current growth rate (proxy for 7-day rate)
        current_growth = opportunity.growth_rate or 0.0
        
        # Historical baseline (estimated from similar opportunities)
        historical_baseline = self._estimate_historical_baseline(opportunity)
        
        # Calculate acceleration factor
        if historical_baseline > 0:
            acceleration_factor = (current_growth + 100.0) / (historical_baseline + 100.0)
        else:
            acceleration_factor = 1.0
        
        # Determine direction
        if acceleration_factor > 1.2:
            direction = "accelerating"
        elif acceleration_factor < 0.8:
            direction = "decelerating"
        else:
            direction = "stable"
        
        # For now, estimate 30/90 day rates from current growth
        # In production, query time series data if available
        growth_30d = current_growth * 0.7  # Assume slower aggregate
        growth_90d = current_growth * 0.5  # Even slower aggregate
        
        return MomentumMetric(
            acceleration_factor=acceleration_factor,
            direction=direction,
            seven_day_rate=current_growth,
            thirty_day_rate=growth_30d,
            ninety_day_rate=growth_90d,
        )
    
    def _estimate_historical_baseline(self, opportunity: Opportunity) -> float:
        """
        Estimate historical growth baseline for comparison.
        
        Query similar opportunities to find average growth rate.
        """
        try:
            # Find opportunities in same category
            similar = self.db.query(func.avg(Opportunity.growth_rate)).filter(
                Opportunity.category == opportunity.category,
                Opportunity.growth_rate.isnot(None),
            ).scalar() or 0.0
            
            return float(similar)
        except Exception as e:
            logger.warning(f"Error calculating baseline: {e}")
            return 5.0  # Default baseline


class MarketHealthAnalyzer:
    """
    Analyzes market health and saturation.
    
    Signals:
    - Market saturation (80+ businesses = saturated)
    - Demand vs. supply (more demand than supply = bullish)
    - Trend direction (momentum in market)
    - Market health score (0-100, 100 = hot)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_market_health(self, opportunity: Opportunity) -> MarketHealthSnapshot:
        """
        Analyze market health for opportunity's vertical in its geography.
        """
        vertical = opportunity.category
        
        # Count businesses in this vertical
        business_count = self._count_businesses_in_vertical(vertical)
        
        # Determine saturation level
        if business_count >= 150:
            saturation_level = "saturated"
            health_base = 20
        elif business_count >= 80:
            saturation_level = "mature"
            health_base = 40
        elif business_count >= 30:
            saturation_level = "growing"
            health_base = 70
        else:
            saturation_level = "emerging"
            health_base = 90
        
        # Analyze demand signals
        demand_signals = self._get_demand_signals(opportunity)
        
        # Demand vs supply analysis
        if demand_signals >= 3:
            demand_vs_supply = "bullish"
            health_boost = 15
        elif demand_signals == 2:
            demand_vs_supply = "neutral"
            health_boost = 0
        else:
            demand_vs_supply = "bearish"
            health_boost = -15
        
        # Final market health score
        market_health_score = max(0.0, min(health_base + health_boost, 100.0))
        
        return MarketHealthSnapshot(
            market_health_score=market_health_score,
            saturation_level=saturation_level,
            demand_vs_supply=demand_vs_supply,
            business_count=business_count,
            confidence=75.0,
        )
    
    def _count_businesses_in_vertical(self, vertical: str) -> int:
        """Count active opportunities in this vertical"""
        try:
            count = self.db.query(func.count(Opportunity.id)).filter(
                Opportunity.category == vertical,
                Opportunity.status == "active",
                Opportunity.moderation_status == "approved"
            ).scalar() or 0
            return count
        except Exception as e:
            logger.warning(f"Error counting businesses: {e}")
            return 50
    
    def _get_demand_signals(self, opportunity: Opportunity) -> int:
        """Count demand signals (0-5)"""
        signals = 0
        
        if opportunity.validation_count and opportunity.validation_count > 5:
            signals += 1
        
        if opportunity.growth_rate and opportunity.growth_rate > 10:
            signals += 1
        
        if opportunity.ai_urgency_level == "critical":
            signals += 1
        
        if opportunity.ai_competition_level == "low":
            signals += 1
        
        if opportunity.market_size and ("M" in str(opportunity.market_size) or "B" in str(opportunity.market_size)):
            signals += 1
        
        return signals


class RiskScorer:
    """
    Comprehensive risk assessment.
    
    Evaluates:
    - Market saturation risk (too many competitors?)
    - Trend fatigue risk (is demand declining?)
    - Seasonal risk (does this vertical have seasonality?)
    - Execution risk (how hard is this business type?)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_risk(self, opportunity: Opportunity) -> RiskProfile:
        """
        Calculate comprehensive risk score (0-100, 100 = critical risk).
        """
        saturation_risk = self._calculate_saturation_risk(opportunity)
        trend_fatigue_risk = self._calculate_trend_fatigue_risk(opportunity)
        seasonal_risk = self._calculate_seasonal_risk(opportunity)
        execution_risk = self._calculate_execution_risk(opportunity)
        
        # Average all risks
        overall_risk = (saturation_risk + trend_fatigue_risk + seasonal_risk + execution_risk) / 4.0
        
        return RiskProfile(
            overall_risk_score=overall_risk,
            saturation_risk=saturation_risk,
            trend_fatigue_risk=trend_fatigue_risk,
            seasonal_risk=seasonal_risk,
            execution_risk=execution_risk,
            confidence=70.0,
        )
    
    def _calculate_saturation_risk(self, opportunity: Opportunity) -> float:
        """
        Risk from market saturation.
        
        Too many competitors = high risk
        """
        try:
            # Count similar opportunities
            similar_count = self.db.query(func.count(Opportunity.id)).filter(
                Opportunity.category == opportunity.category,
                Opportunity.ai_competition_level == "high",
                Opportunity.status == "active"
            ).scalar() or 0
            
            # Saturation risk scales with competitor count
            if similar_count >= 100:
                return 90.0  # Highly saturated
            elif similar_count >= 50:
                return 70.0
            elif similar_count >= 20:
                return 50.0
            elif similar_count >= 10:
                return 30.0
            else:
                return 10.0
        except Exception as e:
            logger.warning(f"Error calculating saturation risk: {e}")
            return 50.0
    
    def _calculate_trend_fatigue_risk(self, opportunity: Opportunity) -> float:
        """
        Risk from trend fatigue (demand is declining).
        
        Negative growth = fatigue
        """
        growth = opportunity.growth_rate or 0.0
        
        if growth < -15:
            return 90.0  # Rapidly declining
        elif growth < -5:
            return 70.0
        elif growth < 0:
            return 40.0
        elif growth < 5:
            return 20.0
        else:
            return 0.0  # Growing demand
    
    def _calculate_seasonal_risk(self, opportunity: Opportunity) -> float:
        """
        Risk from seasonality.
        
        Some verticals are highly seasonal (Christmas, back-to-school, etc.)
        We estimate based on category patterns.
        """
        seasonal_categories = {
            "holiday": 80.0,
            "seasonal": 70.0,
            "retail": 50.0,
            "outdoor": 60.0,
            "winter": 60.0,
            "summer": 40.0,
        }
        
        category_lower = (opportunity.category or "").lower()
        
        for seasonal_keyword, risk in seasonal_categories.items():
            if seasonal_keyword in category_lower:
                return risk
        
        return 20.0  # Low seasonal risk by default
    
    def _calculate_execution_risk(self, opportunity: Opportunity) -> float:
        """
        Risk from execution difficulty.
        
        Some business types are harder to execute than others.
        We estimate based on category and pain intensity.
        """
        # Pain intensity is inverse proxy for difficulty
        # High pain intensity = serious problem = easier to execute solution
        pain = opportunity.ai_pain_intensity or 5
        
        pain_based_risk = (10 - pain) * 10.0  # 0-100 scale
        
        # Category-based difficulty estimates
        difficult_categories = {
            "healthcare": 20.0,  # Regulated, hard
            "legal": 20.0,
            "financial": 20.0,
            "real_estate": 30.0,
            "software": 40.0,
        }
        
        category_lower = (opportunity.category or "").lower()
        
        category_risk = 50.0  # Default
        for cat, risk in difficult_categories.items():
            if cat in category_lower:
                category_risk = risk
                break
        
        # Combine: 60% category, 40% pain-based
        return (category_risk * 0.6) + (pain_based_risk * 0.4)


class IntelligenceEngine:
    """
    Unified intelligence engine.
    
    Orchestrates all intelligence components:
    - OpportunityRanker
    - TrendAnalyzer
    - MarketHealthAnalyzer
    - RiskScorer
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ranker = OpportunityRanker(db)
        self.trend_analyzer = TrendAnalyzer(db)
        self.market_analyzer = MarketHealthAnalyzer(db)
        self.risk_scorer = RiskScorer(db)
    
    def rank_opportunities(
        self,
        opportunities: List[Opportunity],
    ) -> List[Tuple[Opportunity, IntelligenceScore]]:
        """
        Rank opportunities by predicted success probability RIGHT NOW.
        """
        return self.ranker.rank_opportunities(
            opportunities,
            trend_analyzer=self.trend_analyzer,
            risk_scorer=self.risk_scorer,
            market_analyzer=self.market_analyzer,
        )
    
    def analyze_opportunity(
        self,
        opportunity: Opportunity,
    ) -> Dict[str, Any]:
        """
        Comprehensive intelligence analysis for a single opportunity.
        
        Returns all intelligence insights for the opportunity.
        """
        momentum = self.trend_analyzer.analyze_momentum(opportunity)
        market_health = self.market_analyzer.analyze_market_health(opportunity)
        risk = self.risk_scorer.calculate_risk(opportunity)
        
        # Rank this opportunity against itself (get success score)
        ranked = self.ranker.rank_opportunities(
            [opportunity],
            trend_analyzer=self.trend_analyzer,
            risk_scorer=self.risk_scorer,
            market_analyzer=self.market_analyzer,
        )
        success_score = ranked[0][1] if ranked else None
        
        return {
            "success_score": success_score.to_dict() if success_score else None,
            "momentum": momentum.to_dict(),
            "market_health": market_health.to_dict(),
            "risk_profile": risk.to_dict(),
        }
    
    def analyze_trends(
        self,
        trend_opportunities: List[Opportunity],
    ) -> Dict[str, Any]:
        """
        Analyze a collection of opportunities representing a trend.
        
        Returns momentum metrics and trend health.
        """
        if not trend_opportunities:
            return {}
        
        # Analyze momentum for each
        momentums = [
            self.trend_analyzer.analyze_momentum(opp)
            for opp in trend_opportunities
        ]
        
        # Calculate aggregate momentum
        avg_acceleration = sum(m.acceleration_factor for m in momentums) / len(momentums)
        avg_7day = sum(m.seven_day_rate for m in momentums) / len(momentums)
        
        # Determine overall direction
        if avg_acceleration > 1.15:
            overall_direction = "accelerating"
        elif avg_acceleration < 0.85:
            overall_direction = "decelerating"
        else:
            overall_direction = "stable"
        
        return {
            "momentum_data": [m.to_dict() for m in momentums],
            "overall_direction": overall_direction,
            "average_acceleration": avg_acceleration,
            "average_7day_growth": avg_7day,
            "confidence": 70.0,
        }
    
    def analyze_market(
        self,
        market_opportunities: List[Opportunity],
    ) -> Dict[str, Any]:
        """
        Analyze market health for a collection of opportunities.
        
        Returns aggregate market signals.
        """
        if not market_opportunities:
            return {}
        
        # Analyze health for each
        healths = [
            self.market_analyzer.analyze_market_health(opp)
            for opp in market_opportunities
        ]
        
        # Calculate aggregate
        avg_health = sum(h.market_health_score for h in healths) / len(healths)
        
        bullish_count = sum(1 for h in healths if h.demand_vs_supply == "bullish")
        bearish_count = sum(1 for h in healths if h.demand_vs_supply == "bearish")
        
        if bullish_count > bearish_count:
            overall_sentiment = "bullish"
        elif bearish_count > bullish_count:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"
        
        return {
            "market_health_data": [h.to_dict() for h in healths],
            "average_health_score": avg_health,
            "overall_sentiment": overall_sentiment,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "confidence": 75.0,
        }
