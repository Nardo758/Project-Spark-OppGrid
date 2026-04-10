"""
SecretSauceInjector — Builds the shared OppGrid intelligence block injected into every
report's Claude prompt.

This is where OppGrid's differentiation lives. Every report type receives the same
structured block, ensuring:
  • Real competitor data (not hallucinated)
  • Actual demographics with Census citations
  • All 8 proprietary formula scores with interpretations
  • Signal evidence ("Why This Opportunity?")
  • Data Sources section
  • Critical instructions telling Claude to use only provided data
"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from app.models.report_context import FormulaScores

if TYPE_CHECKING:
    from app.services.report_data_service import ReportDataContext

logger = logging.getLogger(__name__)


class SecretSauceInjector:
    """
    Builds the intelligence context block for ANY report type.
    Accepts the existing ReportDataContext from ReportDataService together
    with pre-calculated FormulaScores.
    """

    @staticmethod
    def build_context_block(
        rdc: "ReportDataContext",
        formula_scores: FormulaScores,
        business_type: str,
        city: str,
        state: str,
    ) -> str:
        """
        Return the complete OppGrid intelligence block to prepend to any Claude prompt.
        All sections degrade gracefully when data is unavailable.
        """
        sections = [
            SecretSauceInjector._build_header(business_type, city, state),
            SecretSauceInjector._build_competitor_section(rdc),
            SecretSauceInjector._build_demographics_section(rdc),
            SecretSauceInjector._build_formula_scores_section(formula_scores),
            SecretSauceInjector._build_signal_evidence_section(rdc, business_type, city),
            SecretSauceInjector._build_data_sources_section(rdc),
            SecretSauceInjector._build_instructions(),
        ]
        return "\n\n".join(s for s in sections if s)

    @staticmethod
    def _build_header(business_type: str, city: str, state: str) -> str:
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        return (
            "## OPPGRID INTELLIGENCE DATA\n"
            "## USE THIS DATA — DO NOT INVENT STATISTICS\n\n"
            f"Business: {business_type}\n"
            f"Location: {city}, {state}\n"
            f"Analysis Date: {date_str}"
        )

    @staticmethod
    def _build_competitor_section(rdc: "ReportDataContext") -> str:
        if not rdc or not rdc.promotion:
            return (
                "### Competitive Landscape\n"
                "Competitor data not available for this market.\n"
                "Do NOT invent competitor names or counts."
            )

        competitor_count = rdc.promotion.competitor_count
        avg_rating = rdc.promotion.avg_competitor_rating
        competition_level = rdc.promotion.competition_level
        competitors = rdc.promotion.google_places_competitors or []

        if competitor_count is None and not competitors:
            return (
                "### Competitive Landscape\n"
                "Competitor scan pending — scraper integration in progress.\n"
                "Do NOT invent competitor names or counts."
            )

        lines = ["### Competitive Landscape (Real Data)"]
        if competitor_count is not None:
            lines.append(f"Total competitors within 5 miles: {competitor_count}")
        if avg_rating is not None:
            lines.append(f"Average rating: {avg_rating:.1f}★")
        if competition_level:
            lines.append(f"Competition level: {competition_level.title()}")

        if competitors:
            lines.append("")
            lines.append("| Name | Rating | Reviews | Source |")
            lines.append("|------|--------|---------|--------|")
            scan_date = "recent scan"
            for comp in competitors[:10]:
                name = comp.get("name") or comp.get("title") or "Unknown"
                rating = comp.get("rating", 0) or 0
                reviews = comp.get("review_count") or comp.get("user_ratings_total") or comp.get("reviews", 0)
                source = comp.get("source", "Google Maps")
                scraped = comp.get("scraped_at")
                if scraped and not scan_date.startswith("20"):
                    try:
                        if isinstance(scraped, str):
                            scan_date = scraped[:7]
                        elif hasattr(scraped, "strftime"):
                            scan_date = scraped.strftime("%B %Y")
                    except Exception:
                        pass
                stars = f"{rating:.1f}★" if rating else "N/A"
                rev_str = str(reviews) if reviews else "N/A"
                lines.append(f"| {name} | {stars} | {rev_str} | {source} |")
            lines.append(f"\nSource: Google Maps competitor scan ({scan_date})")
        elif competitor_count is not None and competitor_count == 0:
            lines.append("\nNo direct competitors found in this market — potential first-mover advantage.")

        if rdc.promotion.success_factors:
            factors = rdc.promotion.success_factors[:3]
            lines.append(f"\nKey success factors: {', '.join(factors)}")
        if rdc.promotion.key_risks:
            risks = rdc.promotion.key_risks[:3]
            lines.append(f"Key risks: {', '.join(risks)}")

        return "\n".join(lines)

    @staticmethod
    def _build_demographics_section(rdc: "ReportDataContext") -> str:
        if not rdc or not rdc.place:
            return "### Demographics\nDemographic data not available for this location."

        pl = rdc.place
        pr = rdc.price if rdc.price else None
        lines = ["### Demographics (U.S. Census Bureau, American Community Survey 5-Year Estimates)"]

        if pl.population:
            lines.append(f"Population: {pl.population:,}")
        if pr and pr.median_income:
            lines.append(f"Median Household Income: ${pr.median_income:,}")
        if pl.population_growth_rate is not None:
            lines.append(f"Population Growth: {pl.population_growth_rate:+.1f}% YoY")
        if pl.job_growth_rate is not None:
            lines.append(f"Job Growth: {pl.job_growth_rate:+.1f}% YoY")
        if pr and pr.spending_power_index:
            spi = pr.spending_power_index
            label = "High" if spi >= 70 else "Moderate" if spi >= 40 else "Lower"
            lines.append(f"Spending Power Index: {spi}/100 ({label})")
        if pr and pr.median_rent:
            lines.append(f"Median Rent: ${pr.median_rent:,}/month")
        if pl.total_households:
            lines.append(f"Total Households: {pl.total_households:,}")
        if pr and pr.income_growth_rate is not None:
            lines.append(f"Income Growth Rate: {pr.income_growth_rate:+.1f}% YoY")
        if pl.unemployment_rate is not None:
            lines.append(f"Unemployment Rate: {pl.unemployment_rate:.1f}%")
        if pl.growth_category:
            lines.append(f"Market Category: {pl.growth_category.title()}")

        if len(lines) == 1:
            return "### Demographics\nCensus data not yet available for this location."

        return "\n".join(lines)

    @staticmethod
    def _build_formula_scores_section(scores: FormulaScores) -> str:
        if not scores:
            return "### OppGrid Proprietary Scores\nScores not calculated."

        cls_interp = scores.interpret("cls")
        lines = [
            "### OppGrid Proprietary Formula Scores",
            "",
            f"**Composite Location Score (CLS): {scores.cls:.0f}/100** — {cls_interp}",
            "",
            "| Formula | Score | Interpretation |",
            "|---------|-------|----------------|",
        ]

        tai_str = f"{scores.tai:+.3f}" if scores.tai_available else "N/A*"
        lines.append(f"| Traffic Anomaly Index (TAI) | {tai_str} | {scores.interpret('tai')} |")
        lines.append(f"| Wealth Migration Momentum (WMM) | {scores.wmm:.3f} | {scores.interpret('wmm')} |")
        lines.append(f"| Demand Velocity Score (DVS) | {scores.dvs:+.1f}% | {scores.interpret('dvs')} |")
        lines.append(f"| Competitive Whitespace Index (CWI) | {scores.cwi:.2f} | {scores.interpret('cwi')} |")
        lines.append(f"| Business Formation Velocity (BFV) | {scores.bfv:.1f}/10k | {scores.interpret('bfv')} |")
        lines.append(f"| Affordability Trend Index (ATI) | {scores.ati:+.1f}% | {scores.interpret('ati')} |")
        lines.append(f"| First-Mover Window (FMW) | {scores.fmw:.0f} days | {scores.interpret('fmw')} |")
        lines.append(f"| Demographic Shift Index (DSI) | {scores.dsi:+.1f}% | {scores.interpret('dsi')} |")

        if not scores.tai_available:
            lines.append("\n*TAI requires real-time traffic API integration (not yet connected).")

        lines.append(
            "\nCLS formula: (TAI×15) + (WMM×15) + (DVS×15) + (CWI×20) + (BFV×10) + (ATI×10) + (FMW×5) + (DSI×10), "
            "each normalized to 0-10 scale."
        )

        return "\n".join(lines)

    @staticmethod
    def _build_signal_evidence_section(
        rdc: "ReportDataContext", business_type: str, city: str
    ) -> str:
        if not rdc or not rdc.product:
            return "### Why This Opportunity?\nSignal data pending."

        amenity_demand = rdc.product.amenity_demand or []
        signal_density = rdc.product.signal_density
        opportunity_score = rdc.product.opportunity_score
        pain_intensity = rdc.product.pain_intensity
        urgency_level = rdc.product.urgency_level

        if not amenity_demand and signal_density is None:
            return "### Why This Opportunity?\nDemand signal collection in progress for this market."

        lines = [f"### Why This Opportunity? (OppGrid Signal Evidence)"]
        lines.append(f"\nOppGrid demand analysis for {business_type} in {city}:")

        if signal_density is not None:
            signal_pct = round(signal_density * 100, 0)
            lines.append(f"Signal Density: {signal_pct:.0f}% (share of demand signals in this category)")

        if opportunity_score is not None:
            lines.append(f"Opportunity Score: {opportunity_score:.0f}/100")
        if pain_intensity is not None:
            lines.append(f"Pain Intensity: {pain_intensity:.1f}/10")
        if urgency_level:
            lines.append(f"Urgency Level: {urgency_level.title()}")

        if amenity_demand:
            lines.append("\n**Top Consumer Pain Points:**")
            sorted_signals = sorted(amenity_demand, key=lambda x: x.get("demand_pct", 0), reverse=True)
            for sig in sorted_signals[:5]:
                amenity = sig.get("amenity_type", "").replace("_", " ").title()
                pct = sig.get("demand_pct", 0)
                trend = sig.get("trend", "stable")
                trend_icon = "↑" if trend == "rising" else "↓" if trend == "declining" else "→"
                lines.append(f"  - {amenity}: {pct}% of signals {trend_icon}")

        if rdc.product.google_trends_interest is not None:
            direction = rdc.product.google_trends_direction or "stable"
            lines.append(
                f"\nGoogle Trends Interest: {rdc.product.google_trends_interest}/100 "
                f"({direction.title()})"
            )

        sources = ["OppGrid Signal Database (aggregated from consumer demand data)"]
        if rdc.product.google_trends_interest is not None:
            sources.append("Google Trends")
        lines.append(f"\nSources: {'; '.join(sources)}")

        return "\n".join(lines)

    @staticmethod
    def _build_data_sources_section(rdc: "ReportDataContext") -> str:
        sources = [
            "U.S. Census Bureau, American Community Survey 5-Year Estimates (2020-2024)",
        ]

        if rdc and rdc.promotion and (rdc.promotion.google_places_competitors or rdc.promotion.competitor_count is not None):
            sources.append("Google Maps Places API — competitor scan within 5-mile radius")

        if rdc and rdc.product and rdc.product.amenity_demand:
            sources.append("OppGrid Signal Database — aggregated consumer demand signals")

        if rdc and rdc.product and rdc.product.google_trends_interest is not None:
            sources.append("Google Trends — search interest index")

        if rdc and rdc.price and rdc.price.zillow_home_value:
            sources.append("Zillow Research — real estate market data")

        sources.append("OppGrid FormulaEngine v1.0 — proprietary composite scoring")

        lines = ["### Data Sources"]
        lines.extend(f"- {s}" for s in sources)
        return "\n".join(lines)

    @staticmethod
    def _build_instructions() -> str:
        return (
            "### CRITICAL INSTRUCTIONS FOR CLAUDE\n"
            "1. Use ONLY the data provided above — do NOT invent statistics, competitor names, or counts\n"
            "2. Cite sources inline when referencing demographics: 'median income is $X (Census ACS 2024)'\n"
            "3. Reference specific competitor names and ratings from the table when discussing competition\n"
            "4. Explain what the OppGrid formula scores mean for this specific business decision\n"
            "5. Include the signal evidence to justify the opportunity assessment\n"
            "6. If any data section above says 'pending' or 'not available', acknowledge it — do NOT fabricate replacement values"
        )
