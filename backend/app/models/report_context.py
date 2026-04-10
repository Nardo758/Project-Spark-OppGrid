"""
Report Context — Unified data object passed through the ReportOrchestrator pipeline.

Every report type receives the same ReportContext so the secret sauce (formulas, signals,
competitor data, demographics) is consistently applied regardless of which generator is called.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Competitor:
    name: str
    address: str = ""
    lat: float = 0.0
    lng: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    distance_miles: float = 0.0
    source: str = "Google Maps"
    scraped_at: Optional[datetime] = None


@dataclass
class Demographics:
    population: int = 0
    median_income: int = 0
    age_25_44_pct: float = 0.0
    growth_rate_yoy: float = 0.0
    census_year: str = "2020-2024"
    source: str = "U.S. Census Bureau, American Community Survey 5-Year Estimates"


@dataclass
class Signal:
    text: str
    source: str = "OppGrid"
    subreddit_or_business: str = ""
    discovered_at: Optional[datetime] = None
    quality_score: float = 0.7
    pain_point_category: str = "General"


@dataclass
class FormulaScores:
    tai: float = 0.0   # Traffic Anomaly Index
    wmm: float = 0.0   # Wealth Migration Momentum
    dvs: float = 0.0   # Demand Velocity Score
    cwi: float = 0.0   # Competitive Whitespace Index
    bfv: float = 0.0   # Business Formation Velocity (per 10k residents)
    ati: float = 0.0   # Affordability Trend Index
    fmw: float = 0.0   # First-Mover Window (days)
    dsi: float = 0.0   # Demographic Shift Index
    cls: float = 0.0   # Composite Location Score (0-100)
    tai_available: bool = False  # True only when real traffic API is wired

    def interpret(self, formula: str) -> str:
        """Return human-readable interpretation for a given formula score."""
        val = getattr(self, formula, 0.0)

        if formula == "tai":
            if not self.tai_available:
                return "Traffic API not connected"
            if val >= 0.15:
                return "Emerging hotspot — traffic well above baseline"
            if val >= 0.05:
                return "Positive signal — traffic above normal"
            if val >= -0.05:
                return "Stable traffic pattern"
            return "Declining — traffic below historical baseline"

        if formula == "wmm":
            if val >= 1.20:
                return "Strong wealth influx — new residents earning well above local median"
            if val >= 1.05:
                return "Moderate wealth migration momentum"
            if val >= 0.95:
                return "Neutral — inbound income near local median"
            return "Outbound or low-income migration trend"

        if formula == "dvs":
            if val >= 50:
                return "Rapidly emerging demand — first-mover window is wide open"
            if val >= 15:
                return "Growing demand signals"
            if val >= 0:
                return "Stable demand"
            return "Declining demand signals"

        if formula == "cwi":
            if val >= 8:
                return "Wide open market — significant unmet demand"
            if val >= 3:
                return "Opportunity exists — moderate competitive gap"
            if val >= 1:
                return "Competitive but viable"
            return "Saturated market — low whitespace"

        if formula == "bfv":
            if val >= 15:
                return "Above-average business formation rate — entrepreneurial market"
            if val >= 8:
                return "Moderate formation velocity"
            return "Below-average business formation"

        if formula == "ati":
            if val >= 3:
                return "Incomes growing faster than rents — favorable affordability trend"
            if val >= 0:
                return "Affordability roughly neutral"
            return "Rents growing faster than incomes — affordability pressure"

        if formula == "fmw":
            if val >= 180:
                return "Demand preceded competition by 6+ months — strong first-mover window"
            if val >= 60:
                return "First-mover window active — move soon"
            if val >= 0:
                return "Window closing — competitors are catching up"
            return "Competitors already ahead of demand signal"

        if formula == "dsi":
            if val >= 15:
                return "Strong structural demographic tailwind"
            if val >= 5:
                return "Moderate demographic shift in target direction"
            if val >= 0:
                return "Stable demographic mix"
            return "Target demographic shrinking"

        if formula == "cls":
            if val >= 80:
                return "Excellent — high-confidence opportunity"
            if val >= 60:
                return "Good — solid opportunity with manageable risks"
            if val >= 40:
                return "Moderate — proceed with targeted strategy"
            return "Challenging — significant headwinds present"

        return "—"


@dataclass
class ReportContext:
    """Single source of truth for all data passed to every report generator."""
    business_type: str
    city: str
    state: str
    coordinates: tuple = field(default_factory=lambda: (0.0, 0.0))

    competitors: List[Competitor] = field(default_factory=list)
    demographics: Optional[Demographics] = None
    signals: List[Signal] = field(default_factory=list)

    formula_scores: Optional[FormulaScores] = None

    maps: Dict[str, bytes] = field(default_factory=dict)

    generated_at: Optional[datetime] = None
    data_sources: List[str] = field(default_factory=list)
