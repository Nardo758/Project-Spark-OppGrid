"""
SecretSauceInjector — Builds the shared OppGrid intelligence block injected into every
report's Claude prompt.

This is where OppGrid's differentiation lives. Every report type receives the same
structured block, ensuring:
  • Real competitor data (not hallucinated)
  • Actual demographics with Census citations
  • All 8 proprietary formula scores with interpretations
  • Signal evidence ("Why This Opportunity?")
  • Macroeconomic context with FRED citations (business_plan / market_analysis)
  • Industry labor data with BLS QCEW citations (business_plan / market_analysis)
  • Public-comp benchmarks with SEC 10-K citations (business_plan / market_analysis)
  • Data Sources section
  • Critical instructions telling Claude to use only provided data
"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from app.models.report_context import (
    FormulaScores,
    MacroeconomicContext,
    IndustryLaborData,
    IndustryBenchmarks,
)

if TYPE_CHECKING:
    from app.services.report_data_service import ReportDataContext

logger = logging.getLogger(__name__)


class SecretSauceInjector:
    """
    Builds the intelligence context block for ANY report type.
    Accepts the existing ReportDataContext from ReportDataService together
    with pre-calculated FormulaScores and optional economic data.
    """

    @staticmethod
    def build_context_block(
        rdc: "ReportDataContext",
        formula_scores: FormulaScores,
        business_type: str,
        city: str,
        state: str,
        macro_context: Optional[MacroeconomicContext] = None,
        labor_data: Optional[IndustryLaborData] = None,
        industry_benchmarks: Optional[IndustryBenchmarks] = None,
    ) -> str:
        """
        Return the complete OppGrid intelligence block to prepend to any Claude prompt.
        All sections degrade gracefully when data is unavailable.
        Economic data sections are only included when the corresponding argument is provided.
        """
        sections = [
            SecretSauceInjector._build_header(business_type, city, state),
            SecretSauceInjector._build_competitor_section(rdc),
            SecretSauceInjector._build_demographics_section(rdc),
            SecretSauceInjector._build_formula_scores_section(formula_scores),
            SecretSauceInjector._build_signal_evidence_section(rdc, business_type, city),
        ]

        # Economic intelligence sections (optional — provided for business_plan / market_analysis)
        if macro_context is not None:
            sections.append(SecretSauceInjector._build_macro_context_section(macro_context))
        if labor_data is not None:
            sections.append(SecretSauceInjector._build_labor_section(labor_data))
        if industry_benchmarks is not None:
            sections.append(SecretSauceInjector._build_benchmarks_section(industry_benchmarks))

        sections.append(SecretSauceInjector._build_data_sources_section(
            rdc, macro_context, labor_data, industry_benchmarks
        ))
        sections.append(SecretSauceInjector._build_instructions(
            has_economic_data=any(x is not None for x in [macro_context, labor_data, industry_benchmarks])
        ))

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

    # ── Economic Intelligence Sections ───────────────────────────────────────

    @staticmethod
    def _build_macro_context_section(ctx: MacroeconomicContext) -> str:
        """Format FRED macroeconomic indicators for Claude's context block."""
        lines = ["### Macroeconomic Environment (FRED — Federal Reserve Bank of St. Louis)"]

        def fmt_indicator(ind, fmt_value=None):
            if ind is None:
                return None
            val_str = fmt_value(ind.value) if fmt_value else f"{ind.value}"
            date_str = ind.date.strftime("%b %Y") if hasattr(ind.date, "strftime") else str(ind.date)
            return f"{ind.name}: {val_str} ({ind.source or 'FRED'}, {date_str})"

        rows = [
            fmt_indicator(ctx.fed_funds_rate,    lambda v: f"{v:.2f}%"),
            fmt_indicator(ctx.inflation_rate,    lambda v: f"{v:.1f} (index)"),
            fmt_indicator(ctx.unemployment,      lambda v: f"{v:.1f}%"),
            fmt_indicator(ctx.gdp_growth,        lambda v: f"{v:+.1f}% annualised"),
            fmt_indicator(ctx.consumer_sentiment, lambda v: f"{v:.1f}"),
            fmt_indicator(ctx.mortgage_rate,     lambda v: f"{v:.2f}%"),
        ]
        lines.extend(r for r in rows if r)

        if ctx.retrieved_at:
            try:
                dt = datetime.fromisoformat(ctx.retrieved_at)
                lines.append(f"\nData retrieved: {dt.strftime('%B %d, %Y')}")
            except Exception:
                pass

        return "\n".join(lines)

    @staticmethod
    def _build_labor_section(data: IndustryLaborData) -> str:
        """Format BLS QCEW / OES industry labor data for Claude's context block.

        When source begins with 'BLS OES' the data is state-level; otherwise national.
        """
        is_state = data.source.startswith("BLS OES")
        geo_label = "State" if is_state else "National"

        lines = [
            f"### Industry Labor Market — NAICS {data.naics_code}: {data.industry_name}",
            f"Source: {data.source}",
            "",
        ]

        if data.total_employment:
            lines.append(f"{geo_label} Employment: {data.total_employment:,} workers")
        if data.employment_change_yoy is not None:
            direction = "▲" if data.employment_change_yoy >= 0 else "▼"
            lines.append(
                f"Employment Change (YoY): {direction} {abs(data.employment_change_yoy):.1f}%"
            )
        if data.avg_weekly_wage:
            annual = data.avg_weekly_wage * 52
            lines.append(
                f"Avg Weekly Wage ({geo_label}): ${data.avg_weekly_wage:,.0f} "
                f"(~${annual:,.0f}/year annualised)"
            )
        if data.establishment_count:
            lines.append(f"{geo_label} Establishments: {data.establishment_count:,}")
        if data.data_period:
            lines.append(f"Data Period: {data.data_period}")

        cite_as = data.source if is_state else "BLS QCEW"
        lines.append(
            f"\nIMPORTANT: Use these {data.source} figures when estimating staffing costs and "
            f"labour market conditions for this specific location. "
            f"Cite as '({cite_as})' inline."
        )
        return "\n".join(lines)

    @staticmethod
    def _build_benchmarks_section(benchmarks: IndustryBenchmarks) -> str:
        """Format SEC 10-K public-comp benchmarks for Claude's context block."""
        lines = [
            "### Industry Financial Benchmarks (SEC 10-K Public Company Comparables)",
            f"Source: {benchmarks.source}",
            "",
        ]

        if benchmarks.avg_operating_margin is not None:
            lines.append(
                f"Industry Average Operating Margin: {benchmarks.avg_operating_margin:.1%}"
            )
        if benchmarks.avg_revenue_growth_3yr is not None:
            lines.append(
                f"Avg 3-Year Revenue Growth: {benchmarks.avg_revenue_growth_3yr:.1%}"
            )

        if benchmarks.public_comps:
            lines.append("")
            lines.append("| Company | Ticker | Revenue | Op. Income | Op. Margin | FY |")
            lines.append("|---------|--------|---------|------------|------------|----|")
            for comp in benchmarks.public_comps:
                rev_str = f"${comp.revenue / 1e9:.1f}B" if comp.revenue >= 1e9 else f"${comp.revenue / 1e6:.0f}M"
                oi_str = f"${comp.operating_income / 1e9:.1f}B" if abs(comp.operating_income) >= 1e9 else f"${comp.operating_income / 1e6:.0f}M"
                margin_str = f"{comp.operating_margin:.1%}" if comp.operating_margin is not None else "N/A"
                lines.append(
                    f"| {comp.company_name} | {comp.ticker} | {rev_str} | {oi_str} | "
                    f"{margin_str} | FY{comp.fiscal_year} |"
                )

        # Build a concrete example citation string from the first comp if available
        if benchmarks.public_comps:
            eg = benchmarks.public_comps[0]
            eg_cite = f"(e.g. '{eg.ticker} SEC 10-K FY{eg.fiscal_year}')"
        else:
            eg_cite = "(e.g. 'PSA SEC 10-K FY2025')"
        lines.append(
            f"\nIMPORTANT: Use these SEC 10-K operating margins when building financial projections. "
            f"Cite each figure inline using the company ticker and fiscal year {eg_cite}. "
            "Do NOT invent different margin assumptions."
        )
        return "\n".join(lines)

    # ── Supporting Sections ──────────────────────────────────────────────────

    @staticmethod
    def _build_data_sources_section(
        rdc: "ReportDataContext",
        macro_context: Optional[MacroeconomicContext] = None,
        labor_data: Optional[IndustryLaborData] = None,
        industry_benchmarks: Optional[IndustryBenchmarks] = None,
    ) -> str:
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

        if macro_context is not None:
            sources.append("FRED (Federal Reserve Bank of St. Louis) — macroeconomic indicators")

        if labor_data is not None:
            source_prefix = labor_data.source if labor_data.source else "BLS QCEW"
            sources.append(f"{source_prefix} — {labor_data.industry_name} industry labor data")

        if industry_benchmarks is not None:
            tickers = ", ".join(c.ticker for c in (industry_benchmarks.public_comps or []))
            sources.append(
                f"SEC 10-K filings via sec-api.io — public company financials ({tickers})"
            )

        sources.append("OppGrid FormulaEngine v1.0 — proprietary composite scoring")

        lines = ["### Data Sources"]
        lines.extend(f"- {s}" for s in sources)
        return "\n".join(lines)

    @staticmethod
    def _build_instructions(has_economic_data: bool = False) -> str:
        base = (
            "### CRITICAL INSTRUCTIONS FOR CLAUDE\n"
            "1. Use ONLY the data provided above — do NOT invent statistics, competitor names, or counts\n"
            "2. Cite sources inline when referencing demographics: 'median income is $X (Census ACS 2024)'\n"
            "3. Reference specific competitor names and ratings from the table when discussing competition\n"
            "4. Explain what the OppGrid formula scores mean for this specific business decision\n"
            "5. Include the signal evidence to justify the opportunity assessment\n"
            "6. If any data section above says 'pending' or 'not available', acknowledge it — do NOT fabricate replacement values"
        )
        if has_economic_data:
            base += (
                "\n7. USE THE MACROECONOMIC ENVIRONMENT DATA — cite FRED figures inline "
                "(e.g., 'Fed funds rate 4.25% (FRED, Apr 2026)') in any interest-rate or "
                "financing discussion\n"
                "8. USE THE BLS QCEW LABOR DATA — cite BLS figures when estimating staffing "
                "costs (e.g., 'avg weekly wage $1,234 (BLS QCEW 2024 Annual)')\n"
                "9. USE THE SEC 10-K BENCHMARKS — cite public-comp operating margins when "
                "building financial projections. Do NOT invent margin assumptions when real "
                "SEC data is provided above"
            )
        return base
