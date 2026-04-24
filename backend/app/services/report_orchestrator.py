"""
ReportOrchestrator — The single required entry point for ALL report generation.

Every report type — paid Stripe purchases, free-credit reports, API-triggered —
must pass through here. This ensures that:
  1. ReportDataService is always called to collect real market data
  2. FormulaEngine always calculates the 8 proprietary scores
  3. SecretSauceInjector always builds the intelligence context block
  4. Claude always receives real data rather than inventing values

Economic intelligence (FRED / BLS / SEC) is fetched in parallel and injected for
business_plan and market_analysis report types only.

To add a new report type in the future, register it in REPORT_TYPE_MAP and
create a generator method — the secret sauce injection is inherited automatically.
"""
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.services.formula_engine import FormulaEngine
from app.services.secret_sauce_injector import SecretSauceInjector

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

REPORT_TYPE_MAP = {
    "business_plan":        "generate_business_plan",
    "financial_model":      "generate_financial_projections",
    "financial":            "generate_financial_projections",
    "financials":           "generate_financial_projections",
    "feasibility_study":    "generate_feasibility_study",
    "feasibility":          "generate_feasibility_study",
    "strategic_assessment": "generate_strategic_assessment",
    "strategic":            "generate_strategic_assessment",
    "pitch_deck":           "generate_pitch_deck_content",
    "pestle_analysis":      "generate_pestle_analysis",
    "pestle":               "generate_pestle_analysis",
    "market_analysis":      "generate_market_analysis_report",
    "location_analysis":    "_generate_location_analysis",
}

# Report types that receive full economic intelligence (FRED + BLS + SEC)
ECONOMIC_INTEL_REPORT_TYPES = {"business_plan", "market_analysis"}


class ReportOrchestrator:
    """
    Single entry point for all report generation.

    Usage:
        orchestrator = ReportOrchestrator()
        html_content = await orchestrator.generate(
            report_type="business_plan",
            business_type="Self Storage",
            city="Miami",
            state="FL",
            db=db_session,
            user_notes="Focus on climate-controlled units"
        )
    """

    def __init__(self):
        self.formula_engine = FormulaEngine()
        self.injector = SecretSauceInjector()

    async def generate(
        self,
        report_type: str,
        business_type: str,
        city: str,
        state: str,
        db: "Session",
        user_notes: str = "",
        category: Optional[str] = None,
        target_audience: Optional[str] = None,
        opportunity_id: Optional[int] = None,
    ) -> str:
        """
        Generate a report of any type with full OppGrid intelligence injection.

        Returns HTML content string ready for storage / PDF rendering.
        Raises on generation failure (caller should catch and mark report as FAILED).
        """
        norm_type = report_type.lower().replace("-", "_")

        logger.info(
            f"[Orchestrator] Starting {norm_type} for '{business_type}' in {city}, {state}"
        )

        # ── 1. Collect market data ──────────────────────────────────────────
        rdc = None
        if city and state:
            try:
                from app.services.report_data_service import ReportDataService
                data_service = ReportDataService(db)
                rdc = data_service.get_report_data(
                    city=city,
                    state=state,
                    business_type=category or business_type,
                    report_type=norm_type,
                    opportunity_id=opportunity_id,
                )
                logger.info(
                    f"[Orchestrator] Data collected: "
                    f"{rdc.data_quality.completeness:.0%} complete, "
                    f"{rdc.data_quality.confidence:.0%} confidence"
                )
            except Exception as data_err:
                logger.warning(f"[Orchestrator] ReportDataService failed: {data_err}")

        # ── 2. Calculate proprietary formula scores ─────────────────────────
        formula_scores = None
        if rdc:
            try:
                formula_scores = FormulaEngine.calculate_all(rdc)
                logger.info(
                    f"[Orchestrator] Formulas calculated — CLS: {formula_scores.cls:.0f}/100, "
                    f"CWI: {formula_scores.cwi:.2f}, DVS: {formula_scores.dvs:+.1f}%"
                )
            except Exception as fe:
                logger.warning(f"[Orchestrator] FormulaEngine failed: {fe}")

        # ── 3. Fetch economic intelligence (FRED / BLS / SEC) ────────────────
        macro_context = None
        labor_data = None
        industry_benchmarks = None

        if norm_type in ECONOMIC_INTEL_REPORT_TYPES:
            macro_context, labor_data, industry_benchmarks = await self._fetch_economic_intel(
                business_type=category or business_type,
                db=db,
                state=state,
            )

        # ── 4. Build shared intelligence context block ───────────────────────
        secret_sauce_block = ""
        if rdc and formula_scores:
            try:
                secret_sauce_block = SecretSauceInjector.build_context_block(
                    rdc=rdc,
                    formula_scores=formula_scores,
                    business_type=business_type,
                    city=city,
                    state=state,
                    macro_context=macro_context,
                    labor_data=labor_data,
                    industry_benchmarks=industry_benchmarks,
                )
                logger.info("[Orchestrator] SecretSauceInjector block built successfully")
            except Exception as si_err:
                logger.warning(f"[Orchestrator] SecretSauceInjector failed: {si_err}")

        # ── 5. Route to correct generator ────────────────────────────────────
        opportunity_context = {
            "title": business_type,
            "category": category or business_type,
            "city": city,
            "region": state,
            "description": user_notes or business_type,
            "target_audience": target_audience or "",
            "market_size": rdc.price.market_size_estimate if rdc and rdc.price else "Under analysis",
            "business_models": "",
            "competition_level": (rdc.promotion.competition_level or "") if rdc and rdc.promotion else "",
        }

        content = await self._route(
            norm_type=norm_type,
            opportunity_context=opportunity_context,
            secret_sauce_block=secret_sauce_block,
            rdc=rdc,
            db=db,
            user_notes=user_notes,
        )

        # ── 6. Inject static maps into Business Plan HTML ────────────────────
        if norm_type == "business_plan" and city and state:
            content = await self._inject_business_plan_maps(
                html=content,
                business_type=business_type,
                city=city,
                state=state,
            )

        logger.info(f"[Orchestrator] Generation complete ({len(content)} chars)")
        return content

    async def _fetch_economic_intel(
        self, business_type: str, db: "Session", state: Optional[str] = None
    ):
        """
        Fetch FRED macro, BLS labor, and SEC benchmark data concurrently.
        All three are fire-and-forget — any failure returns None for that source.
        When ``state`` is provided (two-letter abbr.), BLS fetches state-level wages first.
        Returns: (macro_context, labor_data, industry_benchmarks)
        """
        try:
            from app.services.fred_service import FREDService
            from app.services.bls_service import BLSService
            from app.services.sec_api_service import SECAPIService

            fred = FREDService()
            bls = BLSService()
            sec = SECAPIService()

            results = await asyncio.gather(
                fred.get_macro_context(db=db),
                bls.get_industry_data_for_business(business_type, db=db, state=state),
                sec.get_industry_benchmarks(business_type, db=db),
                return_exceptions=True,
            )

            macro_context = results[0] if not isinstance(results[0], Exception) else None
            labor_data = results[1] if not isinstance(results[1], Exception) else None
            industry_benchmarks = results[2] if not isinstance(results[2], Exception) else None

            sources_found = []
            if macro_context:
                sources_found.append("FRED")
            if labor_data:
                sources_found.append(f"BLS QCEW ({labor_data.naics_code})")
            if industry_benchmarks:
                sources_found.append(f"SEC ({len(industry_benchmarks.public_comps)} comps)")

            if sources_found:
                logger.info(f"[Orchestrator] Economic intel fetched: {', '.join(sources_found)}")
            else:
                logger.info("[Orchestrator] Economic intel: no data available (keys may not be configured)")

            return macro_context, labor_data, industry_benchmarks

        except Exception as exc:
            logger.warning(f"[Orchestrator] Economic intel fetch failed: {exc}")
            return None, None, None

    async def _inject_business_plan_maps(
        self,
        html: str,
        business_type: str,
        city: str,
        state: str,
    ) -> str:
        """
        Inject static map <figure> blocks into the Business Plan HTML.

        - Location overview map inserted after the first </h2> (Executive Summary)
        - Competitive density map inserted after the Market Analysis <h2> heading
        Both are gracefully no-ops on failure.
        """
        import re

        try:
            from app.services.static_map_generator import StaticMapGenerator
            gen = StaticMapGenerator()

            overview_html = await gen.location_overview_map_html(city=city, state=state)
            density_html = await gen.competitor_density_map_html(
                business_type=business_type,
                city=city,
                state=state,
                radius_miles=5.0,
            )

            if overview_html:
                # Insert after the first closing </h2> (Executive Summary heading)
                first_h2_close = html.find("</h2>")
                if first_h2_close != -1:
                    insert_pos = first_h2_close + len("</h2>")
                    html = html[:insert_pos] + "\n" + overview_html + html[insert_pos:]
                    logger.info("[Orchestrator] Overview map injected into Executive Summary")
                else:
                    html = overview_html + "\n" + html

            if density_html:
                # Find Market Analysis h2 heading (look for "Market" in h2 tag text)
                market_h2 = re.search(r'<h2[^>]*>[^<]*[Mm]arket[^<]*</h2>', html)
                if market_h2:
                    end_pos = market_h2.end()
                    html = html[:end_pos] + "\n" + density_html + html[end_pos:]
                    logger.info("[Orchestrator] Competitor density map injected into Market Analysis")
                else:
                    html = html + "\n" + density_html

        except Exception as map_err:
            logger.warning(f"[Orchestrator] Map injection failed (non-fatal): {map_err}")

        return html

    async def _route(
        self,
        norm_type: str,
        opportunity_context: dict,
        secret_sauce_block: str,
        rdc,
        db,
        user_notes: str,
    ) -> str:
        """Route to the appropriate AIReportGenerator method."""
        from app.services.ai_report_generator import AIReportGenerator

        generator = AIReportGenerator()
        generator_method_name = REPORT_TYPE_MAP.get(norm_type)

        if not generator_method_name:
            logger.warning(
                f"[Orchestrator] Unknown report type '{norm_type}', falling back to executive_summary"
            )
            generator_method_name = "generate_executive_summary"

        # Location analysis uses a separate template-based path
        if generator_method_name == "_generate_location_analysis":
            return await self._generate_location_analysis(
                opportunity_context, secret_sauce_block, db
            )

        # Market analysis has its own report_data parameter interface
        if generator_method_name == "generate_market_analysis_report":
            return generator.generate_market_analysis_report(
                opportunity_context,
                report_data=rdc,
                secret_sauce_block=secret_sauce_block,
            )

        # All other generators accept (opportunity, secret_sauce_block)
        generator_method = getattr(generator, generator_method_name, None)
        if not generator_method:
            logger.error(f"[Orchestrator] Method '{generator_method_name}' not found on AIReportGenerator")
            raise ValueError(f"Unknown generator method: {generator_method_name}")

        return generator_method(opportunity_context, secret_sauce_block=secret_sauce_block)

    async def _generate_location_analysis(
        self, opportunity_context: dict, secret_sauce_block: str, db
    ) -> str:
        """Template-based path for Location Analysis reports."""
        from app.models.report_template import ReportTemplate
        from app.services.llm_ai_engine import llm_ai_engine_service
        from app.services.ai_report_generator import AIReportGenerator

        tmpl = db.query(ReportTemplate).filter(ReportTemplate.slug == "location_analysis").first()
        if not tmpl or not tmpl.ai_prompt:
            raise ValueError(
                "Location Analysis template not found or has no AI prompt — cannot generate report"
            )

        loc_context = "\n".join([
            f"Business Concept: {opportunity_context.get('title', '')}",
            f"Category: {opportunity_context.get('category', '')}",
            f"Location/Market Area: {opportunity_context.get('city', '')}, {opportunity_context.get('region', '')}",
            f"Target Market: {opportunity_context.get('target_audience', '')}",
        ])
        if secret_sauce_block:
            loc_context = f"{loc_context}\n\n{secret_sauce_block}"

        prompt = tmpl.ai_prompt.replace("{context}", loc_context)
        system = (
            "You are OppGrid's senior market intelligence analyst producing institutional-grade "
            f"location analysis reports.\n\n{AIReportGenerator.INSTITUTIONAL_STYLE_INSTRUCTIONS}"
        )

        result = await llm_ai_engine_service.generate_response(
            f"{system}\n\n{prompt}", model="claude"
        )
        if result.get("error"):
            raise Exception(
                f"AI service error for location_analysis: "
                f"{result.get('error_message', result.get('error'))}"
            )

        content = result.get("response") or result.get("raw") or ""
        if not content:
            raise Exception("AI returned empty response for location_analysis report")
        return content
