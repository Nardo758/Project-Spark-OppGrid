"""
FormulaEngine — Centralized calculation of all 8 OppGrid proprietary formulas.

Updating a formula here propagates to every report type automatically.

Formulas (from report_templates_seed.py):
  TAI  — Traffic Anomaly Index
  WMM  — Wealth Migration Momentum
  DVS  — Demand Velocity Score
  CWI  — Competitive Whitespace Index
  BFV  — Business Formation Velocity (per 10k residents)
  ATI  — Affordability Trend Index
  FMW  — First-Mover Window (days)
  DSI  — Demographic Shift Index
  CLS  — Composite Location Score (0-100, weighted sum)

CLS weights (sum = 100):
  TAI×15 + WMM×15 + DVS×15 + CWI×20 + BFV×10 + ATI×10 + FMW×5 + DSI×10
"""
import logging
from typing import TYPE_CHECKING, Optional

from app.models.report_context import FormulaScores

if TYPE_CHECKING:
    from app.services.report_data_service import ReportDataContext

logger = logging.getLogger(__name__)


class FormulaEngine:
    """Calculate all proprietary OppGrid formulas from a ReportDataContext."""

    @staticmethod
    def calculate_all(rdc: "ReportDataContext") -> FormulaScores:
        """
        Entry point. Accepts the existing ReportDataContext (from ReportDataService)
        and returns a populated FormulaScores object.
        """
        scores = FormulaScores()

        try:
            scores.tai, scores.tai_available = FormulaEngine._calculate_tai(rdc)
            scores.wmm = FormulaEngine._calculate_wmm(rdc)
            scores.dvs = FormulaEngine._calculate_dvs(rdc)
            scores.cwi = FormulaEngine._calculate_cwi(rdc)
            scores.bfv = FormulaEngine._calculate_bfv(rdc)
            scores.ati = FormulaEngine._calculate_ati(rdc)
            scores.fmw = FormulaEngine._calculate_fmw(rdc)
            scores.dsi = FormulaEngine._calculate_dsi(rdc)
            scores.cls = FormulaEngine._calculate_cls(scores)
        except Exception as e:
            logger.warning(f"[FormulaEngine] Formula calculation error: {e}")

        return scores

    @staticmethod
    def _calculate_tai(rdc: "ReportDataContext") -> tuple[float, bool]:
        """
        TAI — Traffic Anomaly Index
        Formula: (Current Traffic - Historical Avg) / Historical Avg
        
        Uses traffic_growth_index from PlaceData when available (populated by JediRE).
        Returns (score, is_available).
        """
        ti = rdc.place.traffic_growth_index if rdc.place else None
        if ti is not None:
            return round(ti / 100, 4), True
        return 0.0, False

    @staticmethod
    def _calculate_wmm(rdc: "ReportDataContext") -> float:
        """
        WMM — Wealth Migration Momentum
        Formula: (Net Migration × Avg Inbound Income) / (Population × Median Local Income)
        
        Approximated from: income_growth_rate, net_migration_rate, and census data.
        Score > 1.0 means net inbound wealth; < 1.0 means outbound or stagnant.
        """
        try:
            income_growth = rdc.price.income_growth_rate if rdc.price else None
            migration = rdc.place.net_migration_rate if rdc.place else None

            if income_growth is not None and migration is not None:
                income_factor = 1.0 + (income_growth / 100)
                migration_factor = 1.0 + max(migration / 1000, -0.5)
                return round(income_factor * migration_factor, 4)

            if income_growth is not None:
                return round(1.0 + (income_growth / 100), 4)

        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_dvs(rdc: "ReportDataContext") -> float:
        """
        DVS — Demand Velocity Score
        Formula: (Signals This Month - Signals 3 Months Ago) / Signals 3 Months Ago × 100
        
        Approximated using trend_strength and google_trends_direction from ProductData.
        """
        try:
            trend = rdc.product.trend_strength if rdc.product else None
            direction = rdc.product.google_trends_direction if rdc.product else None
            google = rdc.product.google_trends_interest if rdc.product else None

            if trend is not None:
                if direction == "rising":
                    return round(min(trend, 100), 1)
                if direction == "declining":
                    return round(max(-trend / 2, -50), 1)
                return round(trend / 2, 1)

            if google is not None:
                return round(google * 0.75, 1)

        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_cwi(rdc: "ReportDataContext") -> float:
        """
        CWI — Competitive Whitespace Index
        Formula: (Demand Signals × Signal Quality) / (Competitor Count + 1)
        
        Uses signal_density and amenity_demand from ProductData,
        competitor_count from PromotionData.
        """
        try:
            signal_density = (rdc.product.signal_density or 0) if rdc.product else 0
            amenity_demand = (rdc.product.amenity_demand or []) if rdc.product else []
            competitor_count = (rdc.promotion.competitor_count or 0) if rdc.promotion else 0
            opportunity_score = (rdc.product.opportunity_score or 0) if rdc.product else 0

            demand_count = max(len(amenity_demand), 1)
            avg_quality = 0.7
            if amenity_demand:
                pcts = [s.get("demand_pct", 50) for s in amenity_demand if s.get("demand_pct")]
                if pcts:
                    avg_quality = min(sum(pcts) / len(pcts) / 100, 1.0)

            weighted_signals = demand_count * avg_quality * (1 + signal_density)
            cwi = weighted_signals / (competitor_count + 1)

            if opportunity_score > 0:
                cwi = cwi * (opportunity_score / 50)

            return round(min(cwi, 20.0), 2)

        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_bfv(rdc: "ReportDataContext") -> float:
        """
        BFV — Business Formation Velocity (new businesses per 10k residents per year)
        Formula: (New Businesses YoY / Population) × 10,000
        
        Uses business_formation_rate from PlaceData. If stored as annual % of population,
        multiply by 10,000 to get per-10k figure.
        """
        try:
            bfr = rdc.place.business_formation_rate if rdc.place else None
            if bfr is not None:
                return round(bfr * 100, 2)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_ati(rdc: "ReportDataContext") -> float:
        """
        ATI — Affordability Trend Index
        Formula: Income Growth % - Commercial Rent Growth %
        
        Uses income_growth_rate from PriceData, home_value_change_yoy as rent proxy.
        Positive = incomes growing faster than costs (favorable).
        """
        try:
            income_growth = rdc.price.income_growth_rate if rdc.price else None
            rent_growth = rdc.price.home_value_change_yoy if rdc.price else None

            if income_growth is not None and rent_growth is not None:
                return round(income_growth - rent_growth, 2)

            if income_growth is not None:
                return round(income_growth, 2)

        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_fmw(rdc: "ReportDataContext") -> float:
        """
        FMW — First-Mover Window (days)
        Measures how much runway remains before competitors saturate the market.
        
        Estimated from competitor_count and signal_density.
        Higher competitor count = window is closing. Strong signals with few competitors = wide open.
        """
        try:
            competitor_count = (rdc.promotion.competitor_count or 0) if rdc.promotion else 0
            signal_density = (rdc.product.signal_density or 0) if rdc.product else 0
            competition_level = (rdc.promotion.competition_level or "").lower() if rdc.promotion else ""

            if competition_level == "none" or competitor_count == 0:
                return 365.0
            if competition_level == "low" or competitor_count <= 2:
                base = 270.0
            elif competition_level == "moderate" or competitor_count <= 6:
                base = 150.0
            elif competition_level == "high" or competitor_count <= 12:
                base = 60.0
            else:
                base = 15.0

            signal_bonus = signal_density * 90
            return round(min(base + signal_bonus, 365.0), 0)

        except Exception:
            pass
        return 90.0

    @staticmethod
    def _calculate_dsi(rdc: "ReportDataContext") -> float:
        """
        DSI — Demographic Shift Index
        Formula: (Target Demo % Now - 5yr Ago) / 5yr Ago × 100
        
        Approximated using population_growth_rate from PlaceData.
        Positive = target demographic is growing.
        """
        try:
            pop_growth = rdc.place.population_growth_rate if rdc.place else None
            job_growth = rdc.place.job_growth_rate if rdc.place else None

            if pop_growth is not None and job_growth is not None:
                return round((pop_growth + job_growth) / 2 * 5, 2)

            if pop_growth is not None:
                return round(pop_growth * 5, 2)

        except Exception:
            pass
        return 0.0

    @staticmethod
    def _calculate_cls(scores: FormulaScores) -> float:
        """
        CLS — Composite Location Score (0-100)
        Formula: TAI×15 + WMM×15 + DVS×15 + CWI×20 + BFV×10 + ATI×10 + FMW×5 + DSI×10

        Each component is normalized to 0-10 before applying weights.
        Total = 0-100.
        """
        def normalize(val: float, lo: float, hi: float) -> float:
            if hi == lo:
                return 5.0
            return max(0.0, min(10.0, (val - lo) / (hi - lo) * 10))

        tai_n = normalize(scores.tai, -0.5, 0.5) if scores.tai_available else 5.0
        wmm_n = normalize(scores.wmm, 0.5, 2.0)
        dvs_n = normalize(scores.dvs, -50, 100)
        cwi_n = normalize(scores.cwi, 0, 15)
        bfv_n = normalize(scores.bfv, 0, 20)
        ati_n = normalize(scores.ati, -10, 10)
        fmw_n = normalize(scores.fmw, 0, 365)
        dsi_n = normalize(scores.dsi, -10, 30)

        cls = (
            tai_n * 15 +
            wmm_n * 15 +
            dvs_n * 15 +
            cwi_n * 20 +
            bfv_n * 10 +
            ati_n * 10 +
            fmw_n * 5 +
            dsi_n * 10
        ) / 10

        return round(max(0.0, min(100.0, cls)), 1)
