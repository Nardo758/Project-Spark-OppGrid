"""
ReportOrchestrator — The single required entry point for ALL report generation.

Every report type — paid Stripe purchases, free-credit reports, API-triggered —
must pass through here. This ensures that:
  1. ReportDataService is always called to collect real market data
  2. FormulaEngine always calculates the 8 proprietary scores
  3. SecretSauceInjector always builds the intelligence context block
  4. Claude always receives real data rather than inventing values

Economic intelligence (FRED / BLS / SEC) is fetched and injected for:
  - business_plan, market_analysis  (via the main `generate()` method)
  - layer_1, layer_2, layer_3       (via `generate_layer_report()`)

To add a new report type in the future, register it in REPORT_TYPE_MAP and
create a generator method — the secret sauce injection is inherited automatically.
"""
import asyncio
import json
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

REPORT_TIER_MAP = {
    "feasibility_study": 1,
    "pitch_deck": 2,
    "strategic_assessment": 2,
    "pestle_analysis": 2,
    "market_analysis": 2,
    "location_analysis": 2,
    "financial_model": 3,
    "business_plan": 3,
}

# Report types that receive full economic intelligence (FRED + BLS + SEC)
ECONOMIC_INTEL_REPORT_TYPES = {"business_plan", "market_analysis", "layer_1", "layer_2", "layer_3"}


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
    ) -> dict:
        """
        Generate a report of any type with full OppGrid intelligence injection.

        Returns dict with keys:
            "content"           — HTML content string ready for storage / PDF rendering
            "economic_snapshot" — JSON-serialisable dict of FRED/BLS/SEC data used (or None)
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
                _tier = REPORT_TIER_MAP.get(norm_type, 2)
                secret_sauce_block = SecretSauceInjector.build_context_block(
                    rdc=rdc,
                    formula_scores=formula_scores,
                    business_type=business_type,
                    city=city,
                    state=state,
                    macro_context=macro_context,
                    labor_data=labor_data,
                    industry_benchmarks=industry_benchmarks,
                    report_tier=_tier,
                )
                logger.info(f"[Orchestrator] SecretSauceInjector block built successfully (Tier {_tier})")
            except Exception as si_err:
                logger.warning(f"[Orchestrator] SecretSauceInjector failed: {si_err}")

        # ── 4a. Add DSCR calculation for lender-facing reports ──────────────
        if norm_type in {"feasibility_study", "financial_model", "business_plan"}:
            try:
                from app.services.dscr_service import DSCRService
                dscr_service = DSCRService()
                dscr_block = dscr_service.build_context_block(
                    business_type=category or business_type,
                    city=city,
                    state=state,
                    rdc=rdc,
                    labor_data=labor_data,
                )
                if dscr_block:
                    secret_sauce_block = f"{secret_sauce_block}\n\n{dscr_block}"
                    logger.info(f"[Orchestrator] DSCR block injected ({norm_type})")
            except Exception as dscr_err:
                logger.warning(f"[Orchestrator] DSCR injection failed: {dscr_err}")

        # ── 4b. Add TAM/SAM/SOM calculation for market-sizing reports ───────
        if norm_type in {"market_analysis", "business_plan", "pitch_deck", "feasibility_study"}:
            try:
                from app.services.market_sizing_service import MarketSizingService
                mss = MarketSizingService()
                tam_sam_som_block = mss.build_context_block(
                    business_type=category or business_type,
                    city=city,
                    state=state,
                    rdc=rdc,
                )
                if tam_sam_som_block:
                    secret_sauce_block = f"{secret_sauce_block}\n\n{tam_sam_som_block}"
                    logger.info(f"[Orchestrator] TAM/SAM/SOM block injected ({norm_type})")
            except Exception as mss_err:
                logger.warning(f"[Orchestrator] TAM/SAM/SOM injection failed: {mss_err}")

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
        economic_snapshot = self._build_economic_snapshot(macro_context, labor_data, industry_benchmarks)
        
        # ── 7. Wrap with OppGrid institutional header ──────────────────────
        content = self._wrap_with_institutional_header(
            content=content,
            report_type=norm_type,
            business_type=business_type,
            city=city,
            state=state,
            data_quality=rdc.data_quality if rdc else None,
            formula_scores=formula_scores,
            economic_snapshot=economic_snapshot,
        )
        
        return {"content": content, "economic_snapshot": economic_snapshot}

    def _wrap_with_institutional_header(
        self,
        content: str,
        report_type: str,
        business_type: str,
        city: str,
        state: str,
        data_quality=None,
        formula_scores=None,
        economic_snapshot=None,
    ) -> str:
        """Wrap report content with an OppGrid institutional header and footer.
        
        If the content already contains <html> tags (from AI generators), extract the body content.
        """
        from datetime import datetime
        import re
        
        report_type_display = report_type.replace("_", " ").title()
        generated_at = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
        
        # Extract body content if the report already has full HTML tags
        body_content = content
        if "<body" in content.lower() or "<html" in content.lower():
            # Extract content between <body> and </body>
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
            if body_match:
                body_content = body_match.group(1).strip()
            else:
                # Fallback: strip html, head, body tags
                body_content = re.sub(r'<html[^>]*>.*?</head>', '', content, flags=re.DOTALL | re.IGNORECASE)
                body_content = re.sub(r'</html>', '', body_content, flags=re.IGNORECASE)
                body_content = re.sub(r'<body[^>]*>|</body>', '', body_content, flags=re.IGNORECASE)
        
        # Build data quality badge
        data_quality_html = ""
        if data_quality:
            completeness_pct = int(data_quality.completeness * 100) if hasattr(data_quality, "completeness") else 0
            confidence_pct = int(data_quality.confidence * 100) if hasattr(data_quality, "confidence") else 0
            data_quality_html = f"""
            <div style="margin-top: 12px; padding: 12px; background: #f8f7f5; border-radius: 8px; border-left: 4px solid #D97757;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Data Intelligence</div>
                <div style="display: flex; gap: 24px; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 20px; font-weight: 700; color: #1a1a1a;">{completeness_pct}%</div>
                        <div style="font-size: 11px; color: #666;">Data Completeness</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: 700; color: #1a1a1a;">{confidence_pct}%</div>
                        <div style="font-size: 11px; color: #666;">Confidence Score</div>
                    </div>
                    {f'<div><div style="font-size: 20px; font-weight: 700; color: #1a1a1a;">{formula_scores.cls:.0f}/100</div><div style="font-size: 11px; color: #666;">Composite Location Score</div></div>' if formula_scores else ''}
                </div>
            </div>
            """
        
        # Build proprietary scores badge
        scores_html = ""
        if formula_scores:
            scores = [
                ("TAI", formula_scores.tai, "Traffic Anomaly"),
                ("WMM", formula_scores.wmm, "Wealth Migration"),
                ("DVS", formula_scores.dvs, "Demand Velocity"),
                ("CWI", formula_scores.cwi, "Competitive Whitespace"),
                ("BFV", formula_scores.bfv, "Business Formation"),
                ("ATI", formula_scores.ati, "Affordability Trend"),
                ("FMW", formula_scores.fmw, "First-Mover Window"),
                ("DSI", formula_scores.dsi, "Demographic Shift"),
            ]
            scores_html = """
            <div style="margin-top: 16px; padding: 12px; background: #f8f7f5; border-radius: 8px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Proprietary Scores</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
            """
            for code, value, label in scores:
                display_val = f"{value:.1f}" if value is not None else "N/A"
                scores_html += f"""
                    <div style="text-align: center; padding: 8px; background: white; border-radius: 6px; border: 1px solid #e5e5e5;">
                        <div style="font-size: 10px; color: #999; text-transform: uppercase;">{code}</div>
                        <div style="font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 2px 0;">{display_val}</div>
                        <div style="font-size: 9px; color: #666;">{label}</div>
                    </div>
                """
            scores_html += "</div></div>"
        
        header = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OppGrid — {report_type_display} for {business_type}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 900px; margin: 0 auto; padding: 40px 24px; background: #fff; }}
        h1, h2, h3 {{ color: #1a1a1a; font-weight: 600; }}
        h1 {{ font-size: 28px; margin-bottom: 8px; }}
        h2 {{ font-size: 22px; margin-top: 32px; margin-bottom: 16px; border-bottom: 2px solid #D97757; padding-bottom: 8px; }}
        h3 {{ font-size: 18px; margin-top: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e5e5; }}
        th {{ background: #f8f7f5; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #666; }}
        .institutional-header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); color: white; padding: 32px; border-radius: 12px; margin-bottom: 32px; }}
        .institutional-header .logo {{ font-size: 24px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }}
        .institutional-header .tagline {{ font-size: 13px; color: #aaa; font-weight: 400; }}
        .institutional-header .report-meta {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 32px; flex-wrap: wrap; }}
        .institutional-header .meta-item {{ font-size: 12px; }}
        .institutional-header .meta-label {{ color: #888; text-transform: uppercase; letter-spacing: 0.5px; font-size: 10px; margin-bottom: 4px; }}
        .institutional-header .meta-value {{ color: white; font-weight: 500; }}
        .footer {{ margin-top: 48px; padding-top: 24px; border-top: 2px solid #f0f0f0; text-align: center; color: #999; font-size: 11px; }}
        .footer .logo {{ font-weight: 700; color: #1a1a1a; font-size: 14px; }}
        .confidential {{ display: inline-block; padding: 4px 12px; background: #f8f7f5; border-radius: 4px; font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 8px; }}
    </style>
</head>
<body>
    <div class="institutional-header">
        <div class="logo">OppGrid</div>
        <div class="tagline">Intelligence-Driven Business Opportunity Platform</div>
        <div class="report-meta">
            <div class="meta-item">
                <div class="meta-label">Report Type</div>
                <div class="meta-value">{report_type_display}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Business Concept</div>
                <div class="meta-value">{business_type}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Location</div>
                <div class="meta-value">{city}, {state}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Generated</div>
                <div class="meta-value">{generated_at}</div>
            </div>
        </div>
        {data_quality_html}
        {scores_html}
    </div>
"""
        
        footer = """
    <div class="footer">
        <div class="logo">OppGrid</div>
        <div>Intelligence-Driven Business Opportunity Platform</div>
        <div class="confidential">Confidential — For Internal Use Only</div>
        <div style="margin-top: 8px; color: #bbb;">This report was generated using OppGrid's proprietary data pipeline, including real-time market signals, competitive intelligence, and demographic analysis.</div>
    </div>
</body>
</html>
"""
        
        return header + body_content + footer

    async def generate_layer_report(
        self,
        layer_type: str,
        opportunity,
        user,
        db: "Session",
        demographics=None,
    ) -> dict:
        """
        Generate a Layer 1/2/3 report through the full intelligence pipeline.

        Fetches FRED/BLS/SEC economic data (concurrently across those three sources),
        then generates layer-specific content via ReportGenerator, ensuring every
        layer report gets the Economic Intelligence panel.

        Returns dict with keys:
            "report"            — the GeneratedReport ORM object saved to the DB
            "economic_snapshot" — JSON-serialisable dict of FRED/BLS/SEC data (or None)
        """
        from app.services.report_generator import ReportGenerator

        business_type = getattr(opportunity, "category", None) or getattr(opportunity, "title", "Business")
        state = getattr(opportunity, "region", None) or ""

        logger.info(
            f"[Orchestrator] Starting {layer_type} for '{business_type}' (opportunity {opportunity.id})"
        )

        macro_context, labor_data, industry_benchmarks = await self._fetch_economic_intel(
            business_type=business_type,
            db=db,
            state=state,
        )

        generator = ReportGenerator(db)
        layer_method_map = {
            "layer_1": "generate_layer1_report",
            "layer_2": "generate_layer2_report",
            "layer_3": "generate_layer3_report",
        }
        method_name = layer_method_map.get(layer_type)
        if not method_name:
            raise ValueError(f"Unknown layer type: {layer_type}")

        generator_method = getattr(generator, method_name)
        report = generator_method(opportunity, user, demographics)

        economic_snapshot = self._build_economic_snapshot(macro_context, labor_data, industry_benchmarks)

        if economic_snapshot:
            import json as _json
            report.economic_snapshot = _json.dumps(economic_snapshot)
            db.commit()
            db.refresh(report)
            logger.info(f"[Orchestrator] Economic snapshot saved for {layer_type} report {report.id}")

        return {"report": report, "economic_snapshot": economic_snapshot}

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

    @staticmethod
    def _build_economic_snapshot(macro_context, labor_data, industry_benchmarks) -> Optional[dict]:
        """
        Serialise the three economic data objects into a JSON-safe dict for DB storage.
        Returns None when no economic data is available.
        """
        if not any([macro_context, labor_data, industry_benchmarks]):
            return None

        snap: dict = {}

        if macro_context:
            macro_dict: dict = {}
            for field_name in ["fed_funds_rate", "inflation_rate", "unemployment",
                                "consumer_sentiment", "mortgage_rate", "gdp_growth"]:
                indicator = getattr(macro_context, field_name, None)
                if indicator is not None:
                    macro_dict[field_name] = {
                        "value": indicator.value,
                        "date": str(indicator.date),
                        "units": indicator.units,
                        "name": indicator.name,
                    }
            if macro_dict:
                snap["macro"] = macro_dict
                snap["macro_retrieved_at"] = macro_context.retrieved_at

        if labor_data:
            snap["labor"] = {
                "naics_code": labor_data.naics_code,
                "industry_name": labor_data.industry_name,
                "total_employment": labor_data.total_employment,
                "employment_change_yoy": labor_data.employment_change_yoy,
                "avg_weekly_wage": labor_data.avg_weekly_wage,
                "establishment_count": labor_data.establishment_count,
                "data_period": labor_data.data_period,
                "source": labor_data.source,
            }

        if industry_benchmarks:
            comps = []
            for c in industry_benchmarks.public_comps:
                comps.append({
                    "ticker": c.ticker,
                    "company_name": c.company_name,
                    "fiscal_year": c.fiscal_year,
                    "revenue": c.revenue,
                    "operating_income": c.operating_income,
                    "operating_margin": c.operating_margin,
                    "net_income": c.net_income,
                })
            snap["benchmarks"] = {
                "avg_operating_margin": industry_benchmarks.avg_operating_margin,
                "avg_revenue_growth_3yr": industry_benchmarks.avg_revenue_growth_3yr,
                "public_comps": comps,
                "source": industry_benchmarks.source,
            }

        return snap if snap else None

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
        """Template-based path for Location Analysis reports.
        
        IMPORTANT: The Secret Sauce block already contains pre-calculated formula scores
        from FormulaEngine. We inject a strong instruction to prevent Claude from recomputing them.
        """
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
        
        # Override the "compute" instruction with "USE the pre-calculated values" instruction
        # This prevents Claude from hallucinating formula inputs/outputs
        prompt = prompt.replace(
            "CRITICAL: For every location you must compute all 8 proprietary formula scores and the Composite Location Score (CLS). Show your work for each formula.",
            "CRITICAL: The 8 proprietary formula scores (TAI, WMM, DVS, CWI, BFV, ATI, FMW, DSI) and the Composite Location Score (CLS) are ALREADY PRE-CALCULATED in the OppGrid Intelligence Data provided above. DO NOT recompute or invent new values. USE the pre-calculated scores exactly as provided. Show your interpretation of each score, not the derivation."
        )
        
        system = (
            "You are OppGrid's senior market intelligence analyst producing institutional-grade "
            f"location analysis reports.\n\n{AIReportGenerator.INSTITUTIONAL_STYLE_INSTRUCTIONS}"
            "\n\nCRITICAL INSTRUCTION: The formula scores (TAI, WMM, DVS, CWI, BFV, ATI, FMW, DSI, CLS) "
            "are ALREADY calculated by OppGrid's FormulaEngine and provided in the data block above. "
            "Use these exact values. Do NOT invent, estimate, or recalculate them. "
            "Your job is to INTERPRET and EXPLAIN the pre-calculated scores, not to derive them."
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
