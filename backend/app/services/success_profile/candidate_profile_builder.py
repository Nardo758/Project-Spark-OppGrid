"""
Candidate Profile Builder

Builds lightweight measured profiles for candidates.
Adapts archetype classification rules for candidates (3 signals instead of 4).
Now includes supply analysis integration.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.schemas.identify_location import (
    CandidateProfile, CandidateSource, MeasuredSignal, ArchetypeType
)

# Import MunicipalDataClient for supply analysis
try:
    from app.services.municipal_data import MunicipalDataClient
    SUPPLY_ANALYSIS_AVAILABLE = True
except ImportError:
    SUPPLY_ANALYSIS_AVAILABLE = False
    MunicipalDataClient = None

logger = logging.getLogger(__name__)


class CandidateProfileBuilder:
    """
    Builds measured profiles for candidate locations.
    Uses 3 classification signals (instead of 4 used in SuccessProfile):
    1. Foot traffic growth/potential
    2. Demographic fit
    3. Competition density
    
    Skips tenure/review signals which require extensive history.
    """

    # Archetype thresholds (using 3-signal model)
    # Archetype assignment rules based on signal values
    ARCHETYPE_RULES = {
        ArchetypeType.PIONEER: {
            "description": "Early-stage, emerging trend locations",
            "criteria": {
                "competition_density": (0, 40),      # Low competition
                "demographic_fit": (60, 100),        # Good demographics
                "foot_traffic": (30, 70),            # Moderate foot traffic
            }
        },
        ArchetypeType.MAINSTREAM: {
            "description": "Established, high-volume potential locations",
            "criteria": {
                "competition_density": (40, 75),     # Moderate competition
                "demographic_fit": (70, 100),        # Strong demographics
                "foot_traffic": (60, 100),           # Good foot traffic
            }
        },
        ArchetypeType.SPECIALIST: {
            "description": "Niche, high-margin play locations",
            "criteria": {
                "competition_density": (30, 80),     # Varies
                "demographic_fit": (60, 100),        # Focused demographics
                "foot_traffic": (20, 80),            # Lower volume OK
            }
        },
        ArchetypeType.ANCHOR: {
            "description": "Destination-driver, unique locations",
            "criteria": {
                "competition_density": (0, 50),      # Rare competition
                "demographic_fit": (80, 100),        # Excellent demographics
                "foot_traffic": (80, 100),           # Very high traffic
            }
        },
        ArchetypeType.EXPERIMENTAL: {
            "description": "Test market, lower viability locations",
            "criteria": {
                "competition_density": (0, 100),     # Any competition
                "demographic_fit": (0, 60),          # Lower demographics OK
                "foot_traffic": (0, 50),             # Lower traffic OK
            }
        },
    }

    def __init__(self, db=None, municipal_data_client=None):
        """Initialize builder"""
        self.db = db
        self.municipal_data_client = municipal_data_client

    def build_profile(
        self,
        candidate_id: str,
        location_name: str,
        latitude: float,
        longitude: float,
        source: CandidateSource,
        source_id: Optional[str] = None,
        city: str = "Unknown",
        state: str = "XX",
        zip_code: Optional[str] = None,
        neighborhood: Optional[str] = None,
        measured_signals: Optional[List[MeasuredSignal]] = None,
        signal_sources: Optional[Dict[str, Any]] = None,
        industry: Optional[str] = None,
        metro: Optional[str] = None,
    ) -> CandidateProfile:
        """
        Build a complete candidate profile.
        
        Args:
            candidate_id: Unique identifier
            location_name: Human-readable name
            latitude/longitude: Coordinates
            source: Where candidate came from
            source_id: ID in source system
            city/state/zip/neighborhood: Location details
            measured_signals: Pre-computed signals (optional)
            signal_sources: Raw data for computing signals
            industry: Business industry for supply analysis
            metro: Metro name for supply analysis
        """
        try:
            # Use provided signals or compute from sources
            if measured_signals is None:
                measured_signals = self._compute_signals(signal_sources or {})
            
            # Classify archetype
            archetype, confidence, rationale = self._classify_archetype(measured_signals)
            
            # Extract risk factors
            risk_factors = self._extract_risk_factors(archetype, measured_signals)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(measured_signals)
            
            # Supply Analysis (NEW)
            supply_verdict = None
            supply_metrics = None
            supply_score_adjustment = 1.0
            
            if industry and metro and SUPPLY_ANALYSIS_AVAILABLE and self.municipal_data_client:
                try:
                    supply_result = self._get_supply_analysis(
                        industry, metro, state
                    )
                    if supply_result:
                        supply_verdict = supply_result.get("verdict")
                        supply_metrics = supply_result.get("metrics")
                        supply_score_adjustment = supply_result.get("score_adjustment", 1.0)
                        overall_score *= supply_score_adjustment
                        
                        logger.info(
                            f"Supply analysis for {location_name}: {supply_verdict} "
                            f"(adjustment: {supply_score_adjustment:.2f}x)"
                        )
                except Exception as e:
                    logger.warning(f"Supply analysis failed for {location_name}: {e}")
            
            # Build profile
            profile = CandidateProfile(
                candidate_id=candidate_id,
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                archetype=archetype,
                archetype_confidence=confidence,
                archetype_rationale=rationale,
                risk_factors=risk_factors,
                measured_signals=measured_signals,
                source=source,
                source_id=source_id,
                city=city,
                state=state,
                zip_code=zip_code,
                neighborhood=neighborhood,
                overall_score=overall_score,
                supply_verdict=supply_verdict,
                supply_metrics=supply_metrics,
                supply_score_adjustment=supply_score_adjustment,
                created_at=datetime.utcnow()
            )
            
            return profile
        
        except Exception as e:
            logger.error(f"Error building profile for {location_name}: {e}")
            raise

    def _compute_signals(self, signal_sources: Dict[str, Any]) -> List[MeasuredSignal]:
        """
        Compute the 3 key signals from raw data sources.
        
        Signal 1: Foot Traffic Growth/Potential
        Signal 2: Demographic Fit
        Signal 3: Competition Density
        """
        signals = []
        
        # Signal 1: Foot Traffic
        foot_traffic = self._compute_foot_traffic(signal_sources.get("foot_traffic", {}))
        signals.append(MeasuredSignal(
            signal_name="foot_traffic_score",
            signal_value=foot_traffic["score"],
            percentile_rank=foot_traffic.get("percentile", 50),
            confidence=foot_traffic.get("confidence", 0.6),
            data_source=foot_traffic.get("source", "foot_traffic_api")
        ))
        
        # Signal 2: Demographic Fit
        demographic = self._compute_demographic_fit(signal_sources.get("demographics", {}))
        signals.append(MeasuredSignal(
            signal_name="demographic_fit",
            signal_value=demographic["score"],
            percentile_rank=demographic.get("percentile", 50),
            confidence=demographic.get("confidence", 0.6),
            data_source=demographic.get("source", "census_data")
        ))
        
        # Signal 3: Competition Density
        competition = self._compute_competition_density(signal_sources.get("competition", {}))
        signals.append(MeasuredSignal(
            signal_name="competition_density",
            signal_value=competition["score"],
            percentile_rank=competition.get("percentile", 50),
            confidence=competition.get("confidence", 0.6),
            data_source=competition.get("source", "business_database")
        ))
        
        return signals

    def _compute_foot_traffic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute foot traffic signal (0-100)"""
        try:
            # Expected data: {"daily_avg": X, "growth_pct": Y, "data_age_days": Z}
            if not data:
                return {"score": 50.0, "percentile": 50, "confidence": 0.4}
            
            daily_avg = data.get("daily_avg", 500)
            growth_pct = data.get("growth_pct", 0)
            
            # Score: higher daily avg + positive growth = higher score
            # Baseline: 100 daily traffic = 20 points, 1000 = 80 points
            base_score = min(100, max(10, (daily_avg / 100) * 20))
            growth_bonus = min(30, growth_pct / 2) if growth_pct > 0 else 0
            
            score = base_score + growth_bonus
            percentile = int(min(100, score))
            confidence = min(0.9, 0.5 + (data.get("recency_score", 0) or 0))
            
            return {
                "score": float(score),
                "percentile": percentile,
                "confidence": confidence,
                "source": "foot_traffic_api"
            }
        except Exception as e:
            logger.warning(f"Error computing foot traffic: {e}")
            return {"score": 50.0, "percentile": 50, "confidence": 0.4}

    def _compute_demographic_fit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute demographic fit signal (0-100)"""
        try:
            # Expected data: {"population": X, "median_income": Y, "target_match": Z}
            if not data:
                return {"score": 50.0, "percentile": 50, "confidence": 0.4}
            
            population = data.get("population", 10000)
            median_income = data.get("median_income", 50000)
            target_match = data.get("target_match", 0.5)  # 0-1 how well demographics match target
            
            # Score: population (min 5k for viability), income level, target match
            pop_score = min(40, (population / 5000) * 20) if population > 0 else 0
            income_score = min(40, (median_income / 100000) * 40)
            match_score = target_match * 20
            
            score = pop_score + income_score + match_score
            percentile = int(min(100, score))
            
            return {
                "score": float(score),
                "percentile": percentile,
                "confidence": 0.7,
                "source": "census_data"
            }
        except Exception as e:
            logger.warning(f"Error computing demographic fit: {e}")
            return {"score": 50.0, "percentile": 50, "confidence": 0.4}

    def _compute_competition_density(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute competition density signal (0-100, higher = less competition)"""
        try:
            # Expected data: {"competitor_count": X, "market_population": Y}
            if not data:
                return {"score": 50.0, "percentile": 50, "confidence": 0.4}
            
            competitor_count = data.get("competitor_count", 5)
            market_pop = data.get("market_population", 50000)
            
            # Score: fewer competitors per population = higher score
            # Formula: 100 - (competitors per 10k * 10)
            competitors_per_10k = (competitor_count / market_pop) * 10000 if market_pop > 0 else 100
            score = max(0, 100 - (competitors_per_10k * 10))
            
            percentile = int(min(100, score))
            confidence = 0.75
            
            return {
                "score": float(score),
                "percentile": percentile,
                "confidence": confidence,
                "source": "business_database"
            }
        except Exception as e:
            logger.warning(f"Error computing competition density: {e}")
            return {"score": 50.0, "percentile": 50, "confidence": 0.4}

    def _classify_archetype(
        self,
        signals: List[MeasuredSignal]
    ) -> tuple[str, float, str]:
        """
        Classify archetype based on 3 signals.
        Returns (archetype, confidence, rationale).
        """
        try:
            # Map signals to values
            signal_dict = {s.signal_name: s.signal_value for s in signals}
            
            competition = signal_dict.get("competition_density", 50)
            demographic = signal_dict.get("demographic_fit", 50)
            foot_traffic = signal_dict.get("foot_traffic_score", 50)
            
            # Score each archetype
            scores = {}
            for archetype_name, rules in self.ARCHETYPE_RULES.items():
                score = self._score_archetype(
                    archetype_name,
                    competition,
                    demographic,
                    foot_traffic,
                    rules
                )
                scores[archetype_name] = score
            
            # Pick best match
            best_archetype = max(scores, key=scores.get)
            best_score = scores[best_archetype]
            
            # Calculate confidence (0-1)
            all_scores = sorted(scores.values(), reverse=True)
            confidence = best_score / 100.0  # Convert to 0-1
            
            # Build rationale
            rationale = self._build_archetype_rationale(
                best_archetype, competition, demographic, foot_traffic
            )
            
            return str(best_archetype.value), confidence, rationale
        
        except Exception as e:
            logger.warning(f"Error classifying archetype: {e}")
            return "mainstream", 0.5, "Default archetype due to classification error"

    def _score_archetype(
        self,
        archetype: ArchetypeType,
        competition: float,
        demographic: float,
        foot_traffic: float,
        rules: Dict[str, Any]
    ) -> float:
        """Score how well signals match an archetype"""
        criteria = rules["criteria"]
        
        scores = []
        
        # Competition score (0-100)
        comp_min, comp_max = criteria["competition_density"]
        comp_score = 100 if comp_min <= competition <= comp_max else abs(competition - (comp_min + comp_max) / 2) / 50
        scores.append(comp_score)
        
        # Demographic score
        demo_min, demo_max = criteria["demographic_fit"]
        demo_score = 100 if demo_min <= demographic <= demo_max else abs(demographic - (demo_min + demo_max) / 2) / 50
        scores.append(demo_score)
        
        # Foot traffic score
        traffic_min, traffic_max = criteria["foot_traffic"]
        traffic_score = 100 if traffic_min <= foot_traffic <= traffic_max else abs(foot_traffic - (traffic_min + traffic_max) / 2) / 50
        scores.append(traffic_score)
        
        # Average (with penalty for out-of-range)
        avg = sum(scores) / len(scores)
        return avg

    def _build_archetype_rationale(
        self,
        archetype: str,
        competition: float,
        demographic: float,
        foot_traffic: float
    ) -> str:
        """Build human-readable rationale for archetype assignment"""
        parts = [f"Classified as {archetype}"]
        
        if competition < 40:
            parts.append("low competition")
        elif competition > 70:
            parts.append("high competition")
        
        if demographic > 75:
            parts.append("strong demographics")
        elif demographic < 50:
            parts.append("weaker demographics")
        
        if foot_traffic > 75:
            parts.append("high foot traffic potential")
        elif foot_traffic < 40:
            parts.append("lower foot traffic")
        
        return "Location: " + ", ".join(parts)

    def _extract_risk_factors(
        self,
        archetype: str,
        signals: List[MeasuredSignal]
    ) -> List[str]:
        """Extract risk factors from archetype and signals"""
        risks = []
        
        signal_dict = {s.signal_name: s.signal_value for s in signals}
        competition = signal_dict.get("competition_density", 50)
        demographic = signal_dict.get("demographic_fit", 50)
        foot_traffic = signal_dict.get("foot_traffic_score", 50)
        
        if archetype == "pioneer":
            risks.append("Emerging market - requires market validation")
            risks.append("Higher execution risk")
        elif archetype == "experimental":
            risks.append("Lower demographic viability")
            risks.append("Test market status")
        
        if competition > 80:
            risks.append("High competitor density")
        
        if demographic < 50:
            risks.append("Demographic uncertainty")
        
        if foot_traffic < 40:
            risks.append("Lower foot traffic potential")
        
        return risks

    def _calculate_overall_score(self, signals: List[MeasuredSignal]) -> float:
        """
        Calculate overall viability score (0-100).
        Weighted average of the 3 signals.
        """
        if not signals:
            return 50.0
        
        weights = {
            "foot_traffic_score": 0.35,
            "demographic_fit": 0.40,
            "competition_density": 0.25,
        }
        
        total_weighted = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = weights.get(signal.signal_name, 0.33)
            total_weighted += signal.signal_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return sum(s.signal_value for s in signals) / len(signals)
        
        return total_weighted / total_weight
    
    def _get_supply_analysis(
        self,
        industry: str,
        metro: str,
        state: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get supply analysis for the industry/metro and calculate score adjustment.
        
        Returns:
            Dict with:
            - verdict: 'oversaturated' | 'balanced' | 'undersaturated'
            - metrics: raw supply metrics
            - score_adjustment: multiplier for overall_score (0.75, 1.0, or 1.25)
        """
        if not self.municipal_data_client:
            return None
        
        try:
            # This should be async but we'll handle it synchronously for now
            # In production, would need to be awaited in an async context
            import asyncio
            
            # Try to get the event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new loop if needed
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async query
            result = loop.run_until_complete(
                self.municipal_data_client.query_facilities(
                    metro=metro,
                    state=state,
                    industry=industry,
                )
            )
            
            if not result.success:
                logger.warning(f"Supply query failed: {result.error}")
                return None
            
            metrics = result.metrics
            verdict = metrics.verdict.value
            
            # Calculate score adjustment based on verdict
            if verdict == "oversaturated":
                adjustment = 0.75  # Penalize oversaturated markets
            elif verdict == "undersaturated":
                adjustment = 1.25  # Boost undersaturated markets
            else:  # balanced
                adjustment = 1.0   # No change
            
            return {
                "verdict": verdict,
                "metrics": {
                    "total_facilities": metrics.total_facilities,
                    "sqft_per_capita": metrics.sqft_per_capita,
                    "facilities_per_100k": metrics.facilities_per_100k_population,
                    "benchmark": metrics.benchmark_sqft_per_capita,
                    "confidence": metrics.confidence,
                    "data_source": metrics.data_source,
                },
                "score_adjustment": adjustment,
            }
        
        except Exception as e:
            logger.warning(f"Error in supply analysis: {e}", exc_info=True)
            return None
