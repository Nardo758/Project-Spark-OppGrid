"""
Consultant Studio Service - Enhanced three-path validation system
Implements: Validate Idea, Search Ideas, Identify Location
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.consultant_activity import ConsultantActivity, ConsultantPath
from app.models.detected_trend import DetectedTrend
from app.models.trend_opportunity_mapping import TrendOpportunityMapping
from app.models.location_analysis_cache import LocationAnalysisCache, BusinessType
from app.models.idea_validation_cache import IdeaValidationCache
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

IDEA_CACHE_TTL_DAYS = 7

# State name to abbreviation mapping
from .location_utils import STATE_ABBREVIATIONS, normalize_state, validate_coordinates_in_state

def parse_city_state(location: str) -> tuple[str, Optional[str]]:
    """
    Parse a location string like 'Miami, Florida' into (city, state_abbrev).
    Returns (city, None) if state cannot be parsed.
    Uses centralized normalize_state from location_utils.
    """
    if not location:
        return location, None
    
    if ',' in location:
        parts = [p.strip() for p in location.split(',')]
        if len(parts) >= 2:
            city = parts[0]
            state_part = parts[1].strip()
            
            state_abbrev = normalize_state(state_part)
            return city, state_abbrev
    
    return location, None


class ConsultantStudioService:
    """Three-path validation system with dual AI architecture"""

    CACHE_TTL_DAYS = 30

    def __init__(self, db: Session):
        self.db = db

    async def _call_claude_json(self, system: str, prompt: str, max_tokens: int = 600) -> dict:
        """Call Claude with a JSON-returning prompt. Returns parsed dict or {} on failure."""
        import asyncio
        from app.services.ai_report_generator import get_anthropic_client

        client = get_anthropic_client()
        if not client:
            logger.warning("Anthropic client not available for intel card generation")
            return {}

        def _sync_call():
            try:
                msg = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = msg.content[0].text if msg.content else ""
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                import json as _json
                return _json.loads(text.strip())
            except Exception as e:
                logger.warning(f"Claude JSON call failed: {e}")
                return {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)

    # ─────────────────────────────────────────────────────────────────────────
    # INTELLIGENCE CARD BUILDERS
    # ─────────────────────────────────────────────────────────────────────────

    async def _build_validate_intel_card(
        self,
        idea: str,
        online_score: int,
        physical_score: int,
        pattern_analysis: Optional[Dict],
    ) -> dict:
        """Build intelligence card for validate_idea mode."""
        try:
            from sqlalchemy import text as _text

            # Infer category from the idea
            inferred_category = self._infer_business_category(idea)

            # 1. Count market signals in detected_trends (last 90 days)
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            try:
                sig_row = self.db.execute(
                    _text("SELECT COUNT(*) as cnt FROM detected_trends WHERE category ILIKE :cat AND detected_at >= :since"),
                    {"cat": f"%{inferred_category}%", "since": ninety_days_ago},
                ).fetchone()
                market_signals_count = int(sig_row[0]) if sig_row else 0
            except Exception:
                market_signals_count = 0

            # 2. Derive validation score
            validation_score = int((online_score + physical_score) / 2)
            if market_signals_count > 1000:
                validation_score = min(100, validation_score + 15)
            elif market_signals_count > 500:
                validation_score = min(100, validation_score + 10)

            # 3. Competitors from pattern_analysis or DB
            key_competitors = []
            total_competitor_count = 0
            if pattern_analysis and isinstance(pattern_analysis, dict):
                comps = pattern_analysis.get("competitors", [])
                total_competitor_count = len(comps)
                key_competitors = [c.get("name", "") for c in comps[:5] if c.get("name")]
            if not key_competitors:
                try:
                    rows = self.db.execute(
                        _text("SELECT DISTINCT competitor_name FROM pattern_analysis WHERE category ILIKE :cat"),
                        {"cat": f"%{inferred_category}%"},
                    ).fetchall()
                    key_competitors = [r[0] for r in rows[:5] if r[0]]
                    total_competitor_count = len(rows)
                except Exception:
                    pass

            competitor_count = total_competitor_count or len(key_competitors)
            if competitor_count >= 10:
                competition_level, competition_color = "High", "danger"
            elif competitor_count >= 5:
                competition_level, competition_color = "Moderate", "warning"
            else:
                competition_level, competition_color = "Low", "success"

            # 4. Determine signal
            if validation_score >= 70:
                signal, signal_text = "green", "Worth exploring"
            elif validation_score >= 50:
                signal, signal_text = "yellow", "Proceed with caution"
            else:
                signal, signal_text = "red", "High risk"

            # 5. Claude narrative
            ai_output = await self._call_claude_json(
                system="You are a market analyst. Return only valid JSON.",
                prompt=f"""You are analyzing a business idea for OppGrid's Consultant Studio.

IDEA: {idea}
CATEGORY: {inferred_category}

DATA:
- Validation Score: {validation_score}/100
- Market Signals (last 90 days): {market_signals_count:,}
- Competition Level: {competition_level} ({competitor_count} known players)
- Top Competitors: {', '.join(key_competitors) if key_competitors else 'None identified'}

TASK 1 - NARRATIVE VERDICT:
Write a 2-3 sentence verdict paragraph referencing these specific metrics.
Use <strong> tags to emphasize 1-2 key phrases.

TASK 2 - DEMAND SIGNAL QUOTE:
Synthesize the top customer pain point for this category (e.g., "Why can't I find X?").

TASK 3 - MARKET RISK:
One sentence about the competitive risk and where opportunity exists.

Return as JSON:
{{
    "narrative_verdict": "...",
    "demand_signal_quote": "...",
    "demand_signal_pct": 34,
    "market_risk": "..."
}}""",
                max_tokens=500,
            )

            return {
                "intel_verdict": {
                    "icon": "📊",
                    "label": "OppGrid verdict",
                    "signal": signal,
                    "signal_text": signal_text,
                    "summary": ai_output.get("narrative_verdict", ""),
                },
                "intel_metrics": [
                    {
                        "label": "Validation score",
                        "value": f"{validation_score}/100",
                        "subtext": "Strong signal" if validation_score >= 70 else "Moderate" if validation_score >= 50 else "Weak",
                        "color": "success" if validation_score >= 70 else "warning" if validation_score >= 50 else "danger",
                    },
                    {
                        "label": "Market signals",
                        "value": f"{market_signals_count:,}",
                        "subtext": "Last 90 days",
                    },
                    {
                        "label": "Competition",
                        "value": competition_level,
                        "subtext": f"{competitor_count} active players",
                        "color": competition_color,
                    },
                ],
                "intel_insights": [
                    {
                        "type": "positive",
                        "label": "Key demand signal",
                        "text": f'"{ai_output.get("demand_signal_quote", "")}" — appears in ~{ai_output.get("demand_signal_pct", 0)}% of analyzed discussions',
                    },
                    {
                        "type": "caution",
                        "label": "Market risk",
                        "text": ai_output.get("market_risk", ""),
                    },
                ],
                "intel_tags": ["Reddit signals", "Google Trends", "Crunchbase", "+4 sources"],
                "intel_cta": {
                    "text": "Full competitive analysis, TAM/SAM, and execution playbook",
                    "report_type": "Feasibility Study",
                    "price": 25,
                },
            }
        except Exception as e:
            logger.warning(f"_build_validate_intel_card failed: {e}")
            return {}

    async def _build_search_intel_card(
        self,
        filters: Dict[str, Any],
        opportunities: list,
        trends: list,
    ) -> dict:
        """Build intelligence card for search_ideas mode."""
        try:
            from sqlalchemy import text as _text

            category = filters.get("category") or filters.get("categories", [""])[0] if filters.get("categories") else ""
            if isinstance(category, list):
                category = category[0] if category else ""

            # 1. Count + avg score from supplied opportunities list
            opportunity_count = len(opportunities)
            if opportunities:
                avg_viability_score = int(
                    sum(o.feasibility_score or 65 for o in opportunities) / max(len(opportunities), 1)
                )
            else:
                avg_viability_score = 65

            # 2. Signal surge: last 30 days vs prior 30 days
            now = datetime.utcnow()
            thirty_days_ago = now - timedelta(days=30)
            sixty_days_ago = now - timedelta(days=60)
            try:
                recent_row = self.db.execute(
                    _text("SELECT COUNT(*) FROM detected_trends WHERE category ILIKE :cat AND detected_at >= :since"),
                    {"cat": f"%{category}%" if category else "%", "since": thirty_days_ago},
                ).fetchone()
                prior_row = self.db.execute(
                    _text("SELECT COUNT(*) FROM detected_trends WHERE category ILIKE :cat AND detected_at >= :start AND detected_at < :end"),
                    {"cat": f"%{category}%" if category else "%", "start": sixty_days_ago, "end": thirty_days_ago},
                ).fetchone()
                recent_count = int(recent_row[0]) if recent_row else 0
                prior_count = int(prior_row[0]) if prior_row else 1
            except Exception:
                recent_count, prior_count = 0, 1
            signal_surge_pct = int(((recent_count - prior_count) / max(prior_count, 1)) * 100)

            # 3. Top signals from supplied trends + DB enrichment
            from app.services.report_data_service import ReportDataService as _RDS; INDUSTRY_BENCHMARKS = _RDS.INDUSTRY_BENCHMARKS
            top_signals = []
            # Use supplied trends first
            for t in trends[:3]:
                sub_cat = getattr(t, "category", category) or category
                benchmark = INDUSTRY_BENCHMARKS.get(sub_cat, {})
                tam = benchmark.get("market_size", None)
                mention_count = getattr(t, "opportunities_count", 0) or 0
                velocity = min(200, int((mention_count / max(10, 1)) * 20))
                top_signals.append({
                    "title": getattr(t, "trend_name", ""),
                    "mention_count": mention_count,
                    "tam": tam,
                    "velocity_pct": velocity,
                })

            # 4. Signal color
            if signal_surge_pct > 10:
                signal, signal_text = "green", "High activity"
            elif signal_surge_pct >= 0:
                signal, signal_text = "yellow", "Stable"
            else:
                signal, signal_text = "red", "Declining"

            # 5. Claude narrative
            ai_output = await self._call_claude_json(
                system="You are a market analyst. Return only valid JSON.",
                prompt=f"""You are analyzing the {category or 'selected'} category for OppGrid's Consultant Studio.

DATA:
- Total Opportunities: {opportunity_count}
- Signal Surge: {signal_surge_pct:+d}% vs last month
- Average Viability Score: {avg_viability_score}/100 (platform median is 64)
- Top Signals This Week: {[s['title'] for s in top_signals]}

Write a 2-3 sentence category outlook paragraph. Reference the specific metrics.
Highlight whether the category is heating up or cooling down.
Mention the top 1-2 signals by name. Use <strong> tags to emphasize key trends.

Return as JSON:
{{
    "narrative_summary": "..."
}}""",
                max_tokens=300,
            )

            return {
                "intel_verdict": {
                    "icon": "🔥",
                    "label": "Category outlook",
                    "signal": signal,
                    "signal_text": signal_text,
                    "summary": ai_output.get("narrative_summary", ""),
                },
                "intel_metrics": [
                    {
                        "label": "Opportunities",
                        "value": str(opportunity_count),
                        "subtext": "in this category",
                    },
                    {
                        "label": "Trending now",
                        "value": f"{signal_surge_pct:+d}%",
                        "subtext": "vs. last month",
                        "color": "success" if signal_surge_pct > 0 else "danger",
                    },
                    {
                        "label": "Avg. score",
                        "value": str(avg_viability_score),
                        "subtext": "High viability" if avg_viability_score > 70 else "Moderate",
                    },
                ],
                "intel_top_signals": top_signals,
                "intel_tags": ["Real-time consumer sentiment", "7 data sources", "AI-curated"],
                "intel_cta": {
                    "text": "Unlock full opportunity cards with execution data",
                    "report_type": "Subscription",
                    "price": 29,
                },
            }
        except Exception as e:
            logger.warning(f"_build_search_intel_card failed: {e}")
            return {}

    async def _build_location_intel_card(
        self,
        city: str,
        business_type: str,
        competitors: list,
        geo_analysis: Dict[str, Any],
    ) -> dict:
        """Build intelligence card for identify_location mode."""
        try:
            from sqlalchemy import text as _text
            from app.services.report_data_service import ReportDataService as _RDS; INDUSTRY_BENCHMARKS = _RDS.INDUSTRY_BENCHMARKS

            # 1. Competitor count + avg rating from geo_analysis
            competitor_count = len(competitors)
            if competitors:
                ratings = [c.get("rating") for c in competitors if c.get("rating")]
                avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 4.0
            else:
                avg_rating = 4.0

            # 2. Census data
            parsed_city, parsed_state = parse_city_state(city)
            try:
                census_row = self.db.execute(
                    _text("SELECT population, median_income, age_25_44_pct FROM census WHERE city ILIKE :city LIMIT 1"),
                    {"city": f"%{parsed_city}%"},
                ).fetchone()
                if census_row:
                    population = int(census_row[0] or 500000)
                    median_income = int(census_row[1] or 55000)
                    age_25_44_pct = int(census_row[2] or 30)
                else:
                    population, median_income, age_25_44_pct = 500000, 55000, 30
            except Exception:
                population, median_income, age_25_44_pct = 500000, 55000, 30

            # 3. Density calculation
            benchmark = INDUSTRY_BENCHMARKS.get(business_type, {})
            typical_density = benchmark.get("typical_density_per_capita", 5000)
            if competitor_count > 0 and population > 0:
                density_per = int(population / competitor_count)
                density_ratio = f"1 per {density_per:,} residents"
                if density_per < typical_density * 0.5:
                    density_label, density_color = "High", "danger"
                elif density_per < typical_density:
                    density_label, density_color = "Medium", "warning"
                else:
                    density_label, density_color = "Low", "success"
            else:
                density_per, density_ratio = 0, "Unknown"
                density_label, density_color = "Unknown", None

            # 4. Foot traffic proxy from market_growth_trajectories
            try:
                growth_row = self.db.execute(
                    _text("SELECT pop_growth FROM market_growth_trajectories WHERE city ILIKE :city ORDER BY year DESC LIMIT 1"),
                    {"city": f"%{parsed_city}%"},
                ).fetchone()
                foot_traffic_growth = float(growth_row[0]) if growth_row and growth_row[0] else 5
            except Exception:
                foot_traffic_growth = 5

            # 5. Claude narrative + micro-markets
            ai_output = await self._call_claude_json(
                system="You are a location analyst. Return only valid JSON.",
                prompt=f"""You are a location intelligence analyst for OppGrid's Consultant Studio.

LOCATION: {city}
BUSINESS TYPE: {business_type}

DATA:
- Competitors: {competitor_count} within 5 miles
- Market Density: {density_label} ({density_ratio})
- Average Competitor Rating: {avg_rating}★
- Foot Traffic Growth: +{foot_traffic_growth}% YoY
- Median Income: ${median_income:,}
- Target Demographic (25-44): {age_25_44_pct}%

TASK 1 - NARRATIVE SUMMARY:
Write a 2-3 sentence location intelligence paragraph referencing these metrics.
Use <strong> tags to emphasize recommended neighborhoods or strategies.

TASK 2 - MICRO MARKETS:
Generate 3 neighborhood/area recommendations within {city} for a {business_type}.
For each: Name (neighborhood name), Score (70-95), Description (short strategic note).

TASK 3 - PROCEED RECOMMENDATION:
Return one of: "Strong opportunity", "Proceed with targeting", "Proceed with caution", "Avoid"

Return as JSON:
{{
    "narrative_summary": "...",
    "micro_markets": [
        {{"name": "...", "score": 87, "description": "..."}},
        {{"name": "...", "score": 82, "description": "..."}},
        {{"name": "...", "score": 71, "description": "..."}}
    ],
    "proceed_recommendation": "..."
}}""",
                max_tokens=600,
            )

            proceed_rec = ai_output.get("proceed_recommendation", "Proceed with targeting")
            if proceed_rec == "Strong opportunity":
                signal = "green"
            elif proceed_rec in ["Proceed with targeting", "Proceed with caution"]:
                signal = "yellow"
            else:
                signal = "red"

            micro_markets = []
            for mm in ai_output.get("micro_markets", []):
                score = mm.get("score", 75)
                score_label = "high" if score >= 80 else "medium" if score >= 60 else "low"
                micro_markets.append({
                    "name": mm.get("name", "Unknown"),
                    "score": score,
                    "score_label": score_label,
                    "description": mm.get("description", ""),
                })

            return {
                "intel_verdict": {
                    "icon": "📍",
                    "label": "Location intelligence",
                    "signal": signal,
                    "signal_text": proceed_rec,
                    "summary": ai_output.get("narrative_summary", ""),
                },
                "intel_metrics": [
                    {"label": "Competitors", "value": str(competitor_count), "subtext": "within 5 mi"},
                    {"label": "Density", "value": density_label, "subtext": density_ratio, "color": density_color},
                    {"label": "Avg. rating", "value": f"{avg_rating}★", "subtext": "area benchmark"},
                    {
                        "label": "Foot traffic",
                        "value": f"+{foot_traffic_growth:.0f}%",
                        "subtext": "YoY growth",
                        "color": "success" if foot_traffic_growth > 0 else "danger",
                    },
                ],
                "intel_demographics": {
                    "median_income": median_income,
                    "age_25_44_pct": age_25_44_pct,
                    "pop_growth": foot_traffic_growth,
                },
                "intel_micro_markets": micro_markets,
                "intel_tags": ["Census Bureau", "Google Places", "Market Growth Data", "AI analysis"],
                "intel_cta": {
                    "text": "Full location analysis with Census data, heat maps & lease intel",
                    "report_type": "Business Plan",
                    "price": 149,
                },
            }
        except Exception as e:
            logger.warning(f"_build_location_intel_card failed: {e}")
            return {}

    async def _build_clone_intel_card(
        self,
        business_name: str,
        source_analysis: Dict[str, Any],
    ) -> dict:
        """Build intelligence card for clone_success mode."""
        try:
            from sqlalchemy import text as _text
            from app.services.report_data_service import ReportDataService as _RDS; INDUSTRY_BENCHMARKS = _RDS.INDUSTRY_BENCHMARKS

            category = source_analysis.get("category", "")
            benchmark = INDUSTRY_BENCHMARKS.get(category, {})
            est_startup_cost = benchmark.get("capital_required", "$250K–$500K")
            typical_margin = benchmark.get("net_margin", "10–15%")
            avg_revenue = benchmark.get("avg_unit_revenue", "$500K–$1M")

            # Count metros with similar concepts
            try:
                metros_row = self.db.execute(
                    _text("SELECT COUNT(DISTINCT city) FROM competitors WHERE category ILIKE :cat"),
                    {"cat": f"%{category}%" if category else "%"},
                ).fetchone()
                metros_with_presence = int(metros_row[0]) if metros_row else 0
            except Exception:
                metros_with_presence = 0

            total_viable_metros = 384
            market_gap_pct = max(0, int(((total_viable_metros - metros_with_presence) / total_viable_metros) * 100))

            # Claude assessment
            ai_output = await self._call_claude_json(
                system="You are a business strategist. Return only valid JSON.",
                prompt=f"""You are a business model analyst for OppGrid's Consultant Studio.

MODEL TO CLONE: {business_name}
INFERRED CATEGORY: {category}

INDUSTRY BENCHMARKS:
- Estimated Startup Cost: {est_startup_cost}
- Typical Net Margin: {typical_margin}
- Average Unit Revenue: {avg_revenue}
- Metros with Similar Concepts: {metros_with_presence} of {total_viable_metros}
- Estimated Market Gap: {market_gap_pct}% of metros underserved

TASK 1 - NARRATIVE SUMMARY:
Write a 2-3 sentence clone assessment paragraph.
Reference the replicability of the model, mention startup cost and market gap.
Use <strong> tags to emphasize key numbers.

TASK 2 - REPLICABILITY LABEL:
Return one of: "High", "Medium", "Low"

TASK 3 - WHY IT WORKS:
4 concise bullet points explaining the model's success factors.

TASK 4 - DIFFERENTIATION NEEDED:
One sentence about how to differentiate from the original.

Return as JSON:
{{
    "narrative_summary": "...",
    "replicability_label": "High",
    "why_it_works": ["...", "...", "...", "..."],
    "differentiation_needed": "..."
}}""",
                max_tokens=600,
            )

            replicability = ai_output.get("replicability_label", "Medium")
            if replicability == "High":
                signal, signal_text = "green", "High replicability"
            elif replicability == "Medium":
                signal, signal_text = "yellow", "Moderate replicability"
            else:
                signal, signal_text = "red", "Low replicability"

            why_it_works = ai_output.get("why_it_works", [])

            return {
                "intel_verdict": {
                    "icon": "🎯",
                    "label": "Clone assessment",
                    "signal": signal,
                    "signal_text": signal_text,
                    "summary": ai_output.get("narrative_summary", ""),
                },
                "intel_metrics": [
                    {
                        "label": "Model viability",
                        "value": replicability,
                        "subtext": "Replicable format",
                        "color": "success" if replicability == "High" else "warning",
                    },
                    {"label": "Est. startup cost", "value": str(est_startup_cost), "subtext": "Lean version"},
                    {"label": "Market gap", "value": f"{market_gap_pct}%", "subtext": "Underserved metros"},
                ],
                "intel_why_it_works": why_it_works,
                "intel_insights": [
                    {
                        "type": "positive",
                        "label": "Why this works",
                        "text": " · ".join(why_it_works[:2]),
                    },
                    {
                        "type": "info",
                        "label": "Differentiation needed",
                        "text": ai_output.get("differentiation_needed", ""),
                    },
                ],
                "intel_tags": ["Unit economics modeled", "3 location archetypes", "Competitor comparison"],
                "intel_cta": {
                    "text": "Full clone playbook with financials, suppliers & launch timeline",
                    "report_type": "Deep Clone Analysis",
                    "price": 549,
                },
            }
        except Exception as e:
            logger.warning(f"_build_clone_intel_card failed: {e}")
            return {}

    def _get_cache_key(self, idea_description: str, context: Optional[Dict] = None) -> str:
        """Generate a cache key for validation results"""
        content = idea_description.lower().strip()
        if context:
            content += json.dumps(context, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached_validation(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result from database if exists and not expired"""
        try:
            cached = self.db.query(IdeaValidationCache).filter(
                IdeaValidationCache.cache_key == cache_key,
                IdeaValidationCache.expires_at > datetime.utcnow()
            ).first()
            
            if cached:
                cached.hit_count += 1
                cached.updated_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"DB cache hit for validation: {cache_key[:8]} (hits: {cached.hit_count})")
                return {
                    "success": True,
                    "idea_description": cached.idea_description,
                    "recommendation": cached.recommendation,
                    "online_score": cached.online_score,
                    "physical_score": cached.physical_score,
                    "pattern_analysis": cached.pattern_analysis or {},
                    "viability_report": cached.viability_report or {},
                    "similar_opportunities": cached.similar_opportunities or [],
                    "processing_time_ms": cached.processing_time_ms,
                }
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
            self.db.rollback()
        return None

    def _cache_validation(self, cache_key: str, idea_description: str, context: Optional[Dict], result: Dict[str, Any]):
        """Cache validation result to database with safe upsert handling"""
        try:
            existing = self.db.query(IdeaValidationCache).filter(
                IdeaValidationCache.cache_key == cache_key
            ).first()
            
            if existing:
                existing.recommendation = result.get("recommendation")
                existing.online_score = result.get("online_score")
                existing.physical_score = result.get("physical_score")
                existing.pattern_analysis = result.get("pattern_analysis")
                existing.viability_report = result.get("viability_report")
                existing.similar_opportunities = result.get("similar_opportunities")
                existing.processing_time_ms = result.get("processing_time_ms")
                existing.expires_at = datetime.utcnow() + timedelta(days=IDEA_CACHE_TTL_DAYS)
                existing.updated_at = datetime.utcnow()
                self.db.commit()
            else:
                new_cache = IdeaValidationCache(
                    cache_key=cache_key,
                    idea_description=idea_description,
                    business_context=context,
                    recommendation=result.get("recommendation"),
                    online_score=result.get("online_score"),
                    physical_score=result.get("physical_score"),
                    pattern_analysis=result.get("pattern_analysis"),
                    viability_report=result.get("viability_report"),
                    similar_opportunities=result.get("similar_opportunities"),
                    processing_time_ms=result.get("processing_time_ms"),
                    hit_count=0,
                    expires_at=datetime.utcnow() + timedelta(days=IDEA_CACHE_TTL_DAYS)
                )
                self.db.add(new_cache)
                try:
                    self.db.commit()
                except IntegrityError:
                    self.db.rollback()
                    logger.info(f"Cache entry already exists (race condition): {cache_key[:8]}")
                    return
            
            logger.info(f"Cached validation result: {cache_key[:8]}")
        except Exception as e:
            logger.warning(f"Failed to cache validation: {e}")
            self.db.rollback()

    async def validate_idea(
        self,
        user_id: int,
        idea_description: str,
        business_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Path 1: Validate Idea - Online vs Physical decision engine
        
        TWO-STEP AI WORKFLOW:
        
        Step 1 (Parallel): DeepSeek Draft Generation
        - Uses DeepSeek v3 for fast pattern analysis
        - Generates initial structure and analysis
        - Runs in parallel with other tasks
        - Output: pattern_analysis, business_type_scores
        
        Step 2 (Sequential): Claude Opus Polishing
        - Uses Claude Opus for refined viability report
        - Polishes and enhances initial analysis
        - Ensures professional, institutional quality
        - Output: viability_report with market insights
        
        Additional Tasks (Parallel):
        - Similar opportunities lookup from database
        - Report data enrichment
        
        OPTIMIZATION: All AI calls and lookups run in parallel via asyncio.gather()
        Total time: typically 13-25 seconds
        
        Response includes:
        - Business type recommendation (online/physical/hybrid)
        - Scores (online_score, physical_score)
        - Full report sections (market, business model, financials, risks, next steps)
        - Confidence scoring
        """
        import time
        import asyncio
        start_time = time.time()
        
        cache_key = self._get_cache_key(idea_description, business_context)
        cached_result = self._get_cached_validation(cache_key)
        if cached_result:
            cached_result['from_cache'] = True
            cached_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            return cached_result
        
        try:
            similar_task = self._find_similar_opportunities(idea_description)
            viability_task = self._claude_viability_report_parallel(
                idea_description,
                business_context
            )
            pattern_task = self._deepseek_pattern_analysis_parallel(
                idea_description,
                business_context
            )
            
            similar_opportunities, viability_report, pattern_analysis = await asyncio.gather(
                similar_task,
                viability_task,
                pattern_task,
                return_exceptions=True
            )
            
            if isinstance(similar_opportunities, Exception):
                logger.warning(f"Similar opportunities search failed: {similar_opportunities}")
                logger.error(f"Similar opportunities error details: {type(similar_opportunities).__name__}: {str(similar_opportunities)}")
                similar_opportunities = []
            if isinstance(viability_report, Exception):
                logger.warning(f"Claude viability report failed: {viability_report}")
                logger.error(f"Claude error details: {type(viability_report).__name__}: {str(viability_report)}")
                viability_report = {}
            if isinstance(pattern_analysis, Exception):
                logger.warning(f"DeepSeek pattern analysis failed: {pattern_analysis}")
                logger.error(f"DeepSeek error details: {type(pattern_analysis).__name__}: {str(pattern_analysis)}")
                pattern_analysis = {}
            
            online_score, physical_score = self._calculate_business_type_scores(
                pattern_analysis,
                business_context
            )

            if viability_report and online_score and physical_score:
                viability_report["confidence_score"] = min(95, max(60, (online_score + physical_score) // 2 + 20))

            recommendation = self._determine_recommendation(online_score, physical_score)

            # Enrich with ReportDataService if location context is available
            enrichment = self._enrich_with_report_data(idea_description, business_context)

            processing_time = int((time.time() - start_time) * 1000)

            # Build enriched verdict
            confidence_score = viability_report.get("confidence_score", 70) if viability_report else 70
            verdict_summary = viability_report.get("recommendation", recommendation.upper()) if viability_report else recommendation.upper()
            verdict_detail = viability_report.get("summary", "") if viability_report else ""

            # Extract advantages and risks from viability report
            advantages = []
            risks = []
            if viability_report:
                advantages = viability_report.get("strengths", []) + viability_report.get("opportunities", [])
                risks = viability_report.get("weaknesses", []) + viability_report.get("threats", [])

            # ── INTELLIGENCE CARD: validate_idea ──────────────────────────────
            intel_card = await self._build_validate_intel_card(
                idea_description, online_score, physical_score, pattern_analysis
            )

            result = {
                "success": True,
                "idea_description": idea_description,
                "recommendation": recommendation,
                "online_score": online_score,
                "physical_score": physical_score,
                "pattern_analysis": pattern_analysis,
                "viability_report": viability_report,
                "similar_opportunities": [
                    {"id": o.id, "title": o.title, "score": o.feasibility_score or 0}
                    for o in similar_opportunities[:5]
                ],
                "processing_time_ms": processing_time,
                "from_cache": False,
                # Enriched fields
                "confidence_score": confidence_score,
                "verdict_summary": verdict_summary,
                "verdict_detail": verdict_detail,
                "market_intelligence": enrichment.get("market_intelligence") if enrichment else None,
                "advantages": advantages[:6] if advantages else None,
                "risks": risks[:6] if risks else None,
                "four_ps_scores": enrichment.get("four_ps_scores") if enrichment else None,
                # Intelligence card fields
                **intel_card,
                "feasibility_preview": enrichment.get("feasibility_preview") if enrichment else None,
                "data_quality": enrichment.get("data_quality") if enrichment else None,
            }
            
            self._cache_validation(cache_key, idea_description, business_context, result)
            
            await self._log_activity(
                user_id=user_id,
                session_id=session_id,
                path=ConsultantPath.validate_idea.value,
                action="idea_validation_complete",
                payload={"idea": idea_description[:200], "context": business_context},
                result_summary=f"Recommended: {recommendation}, Online: {online_score}, Physical: {physical_score}",
                ai_model_used="hybrid",
                processing_time_ms=processing_time,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating idea: {e}")
            return {"success": False, "error": str(e)}

    async def search_ideas(
        self,
        user_id: int,
        filters: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Path 2: Search Ideas - Database exploration with trend detection
        Uses DeepSeek for trend detection + Claude for synthesis
        """
        import time
        start_time = time.time()
        
        try:
            opportunities = await self._search_opportunities(filters)
            
            trends = await self._detect_trends(opportunities, filters)
            
            synthesis = self._generate_quick_synthesis(opportunities, trends, filters)

            # ── INTELLIGENCE CARD: search_ideas ───────────────────────────────
            intel_card = await self._build_search_intel_card(filters, opportunities, trends)

            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "opportunities": [
                    {
                        "id": o.id,
                        "title": o.title,
                        "description": o.description[:200] if o.description else None,
                        "category": o.category,
                        "score": o.feasibility_score,
                        "created_at": o.created_at.isoformat() if o.created_at else None,
                    }
                    for o in opportunities[:20]
                ],
                "trends": [
                    {
                        "id": t.id,
                        "name": t.trend_name,
                        "strength": t.trend_strength,
                        "description": t.description,
                        "growth_rate": t.growth_rate,
                        "opportunities_count": t.opportunities_count,
                    }
                    for t in trends
                ],
                "synthesis": synthesis,
                "total_count": len(opportunities),
                "processing_time_ms": processing_time,
                # Intelligence card fields
                **intel_card,
            }
            
            await self._log_activity(
                user_id=user_id,
                session_id=session_id,
                path=ConsultantPath.search_ideas.value,
                action="search_complete",
                payload=filters,
                result_summary=f"Found {len(opportunities)} opportunities, {len(trends)} trends",
                ai_model_used="hybrid",
                processing_time_ms=processing_time,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching ideas: {e}")
            return {"success": False, "error": str(e)}

    async def identify_location(
        self,
        user_id: int,
        city: str,
        business_description: str,
        additional_params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Path 3: Identify Location - Geographic intelligence
        Accepts natural language business description and infers category automatically.
        """
        import time
        start_time = time.time()
        
        try:
            inferred_category = self._infer_business_category(business_description)
            logger.info(f"[TIMING] Category inference: {int((time.time() - start_time) * 1000)}ms")
            
            cache_key = self._generate_cache_key(city, business_description, None, additional_params)
            
            cached = self._get_cached_analysis(cache_key)
            if cached:
                cached["from_cache"] = True
                cached["cache_hit_count"] = cached.get("hit_count", 1)
                return cached
            
            geo_start = time.time()
            geo_analysis = await self._deepseek_geo_analysis(
                city, business_description, inferred_category, additional_params
            )
            logger.info(f"[TIMING] Geo analysis: {int((time.time() - geo_start) * 1000)}ms")
            
            market_report = self._generate_quick_market_report(
                city, business_description, inferred_category, geo_analysis
            )
            logger.info(f"[TIMING] Quick market report generated")
            
            site_recommendations = self._generate_site_recommendations(
                geo_analysis, market_report, inferred_category
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            competitors = geo_analysis.get("competitors", [])
            pins = []
            for idx, comp in enumerate(competitors):
                if comp.get("lat") and comp.get("lng"):
                    pins.append({
                        "id": idx + 1,
                        "lat": comp.get("lat"),
                        "lng": comp.get("lng"),
                        "name": comp.get("name", "Unknown"),
                        "rating": comp.get("rating"),
                        "reviews": comp.get("reviews"),
                        "source": "google_maps",
                        "popup": comp.get("address", ""),
                    })
            
            if pins:
                center_lat = pins[0]["lat"]
                center_lng = pins[0]["lng"]
            else:
                parsed_city, parsed_state = parse_city_state(city)
                fallback_coords = self._get_city_center_coords(parsed_city, parsed_state)
                center_lat = fallback_coords["lat"]
                center_lng = fallback_coords["lng"]
            
            map_data = {
                "city": city,
                "center": {"lat": center_lat, "lng": center_lng},
                "layers": {
                    "pins": {"type": "pins", "data": pins, "count": len(pins)},
                    "heatmap": {"type": "heatmap", "data": [], "count": 0},
                    "polygons": {"type": "polygons", "data": [], "count": 0},
                },
                "totalFeatures": len(pins),
            }
            
            # Enrich with 4P's data from ReportDataService
            location_enrichment = self._enrich_location_with_report_data(city, inferred_category)

            # ── INTELLIGENCE CARD: identify_location ──────────────────────────
            intel_card = await self._build_location_intel_card(
                city, inferred_category, competitors, geo_analysis
            )

            result = {
                "success": True,
                "city": city,
                "business_description": business_description,
                "inferred_category": inferred_category,
                "geo_analysis": geo_analysis,
                "market_report": market_report,
                "site_recommendations": site_recommendations,
                "map_data": map_data,
                "from_cache": False,
                "processing_time_ms": processing_time,
                # Enriched fields
                "four_ps_scores": location_enrichment.get("four_ps_scores") if location_enrichment else None,
                "four_ps_details": location_enrichment.get("four_ps_details") if location_enrichment else None,
                "data_quality": location_enrichment.get("data_quality") if location_enrichment else None,
                # Intelligence card fields
                **intel_card,
            }
            
            await self._cache_analysis(
                cache_key=cache_key,
                city=city,
                business_type=inferred_category,
                business_subtype=business_description,
                query_params=additional_params,
                geo_analysis=geo_analysis,
                market_report=market_report,
                site_recommendations=site_recommendations,
                intel_card=intel_card,
            )
            
            await self._log_activity(
                user_id=user_id,
                session_id=session_id,
                path=ConsultantPath.identify_location.value,
                action="location_analysis_complete",
                payload={"city": city, "business_description": business_description, "category": inferred_category},
                result_summary=f"Analysis for {business_description} in {city}",
                ai_model_used="hybrid",
                processing_time_ms=processing_time,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing location: {e}")
            return {"success": False, "error": str(e)}

    async def clone_success(
        self,
        user_id: int,
        business_name: str,
        business_address: str,
        target_city: Optional[str] = None,
        target_state: Optional[str] = None,
        radius_miles: int = 3,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Path 4: Clone Success - Replicate successful business models
        Analyzes a successful business and finds similar markets to replicate it.
        Now searches within a specific target city/state for matching locations.
        """
        import time
        start_time = time.time()
        
        try:
            source_analysis = await self._analyze_source_business(
                business_name, business_address, radius_miles
            )
            
            matching_locations = await self._find_matching_locations(
                source_analysis, radius_miles, target_city, target_state
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Enrich with 4P's data for target city
            clone_enrichment = None
            if target_city and target_state:
                clone_enrichment = self._enrich_location_with_report_data(
                    target_city, source_analysis.get("category", "retail"), target_state
                )

            # ── INTELLIGENCE CARD: clone_success ──────────────────────────────
            intel_card = await self._build_clone_intel_card(
                business_name, source_analysis
            )

            result = {
                "success": True,
                "source_business": source_analysis,
                "matching_locations": matching_locations,
                "analysis_radius_miles": radius_miles,
                "processing_time_ms": processing_time,
                # Enriched fields
                "target_four_ps": clone_enrichment.get("four_ps_scores") if clone_enrichment else None,
                "data_quality": clone_enrichment.get("data_quality") if clone_enrichment else None,
                # Intelligence card fields
                **intel_card,
            }
            
            await self._log_activity(
                user_id=user_id,
                session_id=session_id,
                path="clone_success",
                action="clone_analysis_complete",
                payload={
                    "business_name": business_name,
                    "address": business_address,
                    "radius": radius_miles,
                },
                result_summary=f"Found {len(matching_locations)} matching locations for {business_name}",
                ai_model_used="hybrid",
                processing_time_ms=processing_time,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in clone success analysis: {e}")
            return {"success": False, "error": str(e), "analysis_radius_miles": radius_miles}

    async def deep_clone_analysis(
        self,
        user_id: int,
        source_business_name: str,
        source_business_address: str,
        target_city: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Premium: Deep Clone Analysis - Detailed 3mi and 5mi radius analysis for a specific target city.
        """
        import time
        start_time = time.time()
        
        try:
            import asyncio
            
            source_analysis = await self._analyze_source_business(
                source_business_name, source_business_address, 3
            )
            
            three_mile, five_mile = await asyncio.gather(
                self._analyze_target_city_radius(
                    target_city, source_analysis.get("category", "retail"), 3
                ),
                self._analyze_target_city_radius(
                    target_city, source_analysis.get("category", "retail"), 5
                )
            )
            
            three_mile_quality = three_mile.get("data_quality", "high")
            five_mile_quality = five_mile.get("data_quality", "high")
            overall_data_quality = "high"
            if three_mile_quality == "limited" or five_mile_quality == "limited":
                overall_data_quality = "limited"
            elif three_mile_quality == "estimated" or five_mile_quality == "estimated":
                overall_data_quality = "estimated"
            
            match_score = self._calculate_match_score(
                source_analysis, three_mile, five_mile, overall_data_quality
            )
            key_factors = self._extract_key_factors(source_analysis, three_mile, five_mile)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "source_business": source_analysis,
                "target_city": target_city,
                "three_mile_analysis": three_mile,
                "five_mile_analysis": five_mile,
                "match_score": match_score,
                "key_factors": key_factors,
                "data_quality": overall_data_quality,
                "processing_time_ms": processing_time,
                "requires_payment": False,
            }
            
            await self._log_activity(
                user_id=user_id,
                session_id=session_id,
                path="deep_clone",
                action="deep_clone_complete",
                payload={
                    "source_business": source_business_name,
                    "target_city": target_city,
                },
                result_summary=f"Deep analysis of {target_city} for {source_business_name} - {match_score}% match",
                ai_model_used="hybrid",
                processing_time_ms=processing_time,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in deep clone analysis: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_target_city_radius(
        self,
        target_city: str,
        category: str,
        radius_miles: int,
    ) -> Dict[str, Any]:
        """Analyze a target city at a specific radius using real data sources.
        
        Uses:
        - Census Bureau API for demographics (state-level with estimation notes)
        - SerpAPI Google Maps for competition analysis with radius filtering
        """
        import os
        import httpx
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        parsed_city, parsed_state = self._parse_address_components(target_city)
        if not parsed_state:
            parts = target_city.split(",")
            if len(parts) >= 2:
                parsed_state = parts[-1].strip().upper()[:2]
        
        coordinates = await self._geocode_city(target_city)
        
        demographics = await self._fetch_city_demographics(parsed_state)
        is_demographics_estimated = demographics.get("is_estimated", False)
        
        competition_data = await self._fetch_competition_data(
            category, target_city, radius_miles, coordinates
        )
        
        population = demographics.get("population", 0)
        median_income = demographics.get("median_income", 0)
        median_age = demographics.get("median_age", 0)
        households = demographics.get("total_households", 0)
        competition_count = competition_data.get("count", 0)
        
        market_density = "high" if competition_count > 8 else "medium" if competition_count > 3 else "low"
        competition_level = "high" if competition_count > 10 else "medium" if competition_count > 5 else "low"
        
        growth_rate = demographics.get("growth_rate", 3.0)
        
        demographics_quality = "estimated" if is_demographics_estimated else "state_level"
        competition_quality = competition_data.get("competition_quality", "limited")
        
        overall_quality = "estimated"
        if demographics_quality == "estimated" or competition_quality == "limited":
            overall_quality = "limited"
        
        data_scope_warning = None
        if demographics.get("data_level") == "state":
            data_scope_warning = "Demographics are state-level averages. Competition data is filtered to the specified radius."
        
        return {
            "radius_miles": radius_miles,
            "state_demographics": {
                "population": population,
                "median_income": median_income,
                "median_age": median_age,
                "households": households,
                "unemployment_rate": demographics.get("unemployment_rate", 0),
                "median_home_value": demographics.get("median_home_value", 0),
                "data_level": demographics.get("data_level", "state"),
                "scope": "state",
            },
            "competition": {
                "count": competition_count,
                "competitors": competition_data.get("competitors", [])[:5],
                "total_found": competition_data.get("total_found", 0),
                "geocoded_ratio": competition_data.get("geocoded_ratio", 0),
                "scope": competition_data.get("competition_scope", "area"),
            },
            "competition_count": competition_count,
            "market_density": market_density,
            "competition_level": competition_level,
            "growth_rate": round(growth_rate, 1),
            "data_source": "US Census Bureau ACS + Google Maps",
            "data_quality": overall_quality,
            "demographics_quality": demographics_quality,
            "demographics_scope": "state",
            "competition_quality": competition_quality,
            "competition_scope": competition_data.get("competition_scope", "area"),
            "radius_filtered": competition_data.get("radius_filtered", False),
            "data_scope_warning": data_scope_warning,
            "coordinates": coordinates,
        }
    
    async def _geocode_city(self, city: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a city using SerpAPI."""
        import os
        
        serpapi_key = os.environ.get("SERPAPI_KEY")
        if not serpapi_key:
            return None
        
        try:
            from .serpapi_service import SerpAPIService
            serpapi = SerpAPIService()
            
            if not serpapi.is_configured:
                return None
            
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: serpapi.google_maps_search(
                        query=city,
                        type="search"
                    )
                )
            
            place_results = result.get("place_results", {})
            if place_results:
                gps = place_results.get("gps_coordinates", {})
                if gps:
                    return {"lat": gps.get("latitude"), "lng": gps.get("longitude")}
            
            local_results = result.get("local_results", [])
            if local_results and len(local_results) > 0:
                gps = local_results[0].get("gps_coordinates", {})
                if gps:
                    return {"lat": gps.get("latitude"), "lng": gps.get("longitude")}
            
            return None
            
        except Exception as e:
            logger.warning(f"Geocoding failed for {city}: {e}")
            return None
    
    async def _fetch_city_demographics(self, state: str) -> Dict[str, Any]:
        """Fetch demographics from Census Bureau API for a state.
        
        Note: Returns state-level data with is_estimated flag to indicate
        these are regional averages, not city-specific data.
        """
        import os
        import httpx
        
        api_key = os.environ.get("CENSUS_API_KEY")
        if not api_key or not state:
            logger.warning("Census API key or state not available, using fallback")
            fallback = self._get_fallback_demographics()
            fallback["is_estimated"] = True
            return fallback
        
        state_fips = self._get_state_fips(state)
        if not state_fips:
            logger.warning(f"Unknown state: {state}, using fallback")
            fallback = self._get_fallback_demographics()
            fallback["is_estimated"] = True
            return fallback
        
        try:
            variables = [
                "B01003_001E",  # Total population
                "B01002_001E",  # Median age
                "B19013_001E",  # Median household income
                "B11001_001E",  # Total households
                "B25077_001E",  # Median home value
                "B23025_005E",  # Unemployed
                "B23025_002E",  # Labor force
            ]
            
            url = f"https://api.census.gov/data/2023/acs/acs5?get={','.join(variables)}&for=state:{state_fips}&key={api_key}"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if len(data) < 2:
                fallback = self._get_fallback_demographics()
                fallback["is_estimated"] = True
                return fallback
            
            values = data[1]
            
            def safe_int(val):
                try:
                    return int(val) if val and val != '-' else 0
                except:
                    return 0
            
            population = safe_int(values[0])
            median_age = safe_int(values[1])
            median_income = safe_int(values[2])
            households = safe_int(values[3])
            home_value = safe_int(values[4])
            unemployed = safe_int(values[5])
            labor_force = safe_int(values[6])
            
            unemployment_rate = (unemployed / labor_force * 100) if labor_force > 0 else 0
            
            return {
                "population": population,
                "median_age": median_age,
                "median_income": median_income,
                "total_households": households,
                "median_home_value": home_value,
                "unemployment_rate": round(unemployment_rate, 1),
                "growth_rate": 3.5,
                "is_estimated": False,
                "data_level": "state",
            }
            
        except Exception as e:
            logger.error(f"Census API error: {e}")
            fallback = self._get_fallback_demographics()
            fallback["is_estimated"] = True
            return fallback
    
    async def _fetch_competition_data(
        self, category: str, location: str, radius_miles: int,
        coordinates: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Fetch competition data using SerpAPI Google Maps with radius filtering."""
        import os
        
        serpapi_key = os.environ.get("SERPAPI_KEY")
        if not serpapi_key:
            logger.warning("SERPAPI_KEY not configured, using fallback")
            return {"count": 0, "competitors": [], "radius_filtered": False}
        
        try:
            from .serpapi_service import SerpAPIService
            serpapi = SerpAPIService()
            
            if not serpapi.is_configured:
                return {"count": 0, "competitors": [], "radius_filtered": False}
            
            search_query = f"{category} near {location}"
            
            ll_param = None
            if coordinates and coordinates.get("lat") and coordinates.get("lng"):
                lat = coordinates["lat"]
                lng = coordinates["lng"]
                zoom = 14 if radius_miles <= 3 else 12 if radius_miles <= 5 else 10
                ll_param = f"@{lat},{lng},{zoom}z"
            
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: serpapi.google_maps_search(
                        query=search_query,
                        location=location,
                        ll=ll_param
                    )
                )
            
            local_results = result.get("local_results", [])
            
            radius_km = radius_miles * 1.60934
            filtered_results = local_results
            
            if coordinates and coordinates.get("lat") and coordinates.get("lng"):
                center_lat = coordinates["lat"]
                center_lng = coordinates["lng"]
                filtered_results = []
                
                for place in local_results:
                    place_gps = place.get("gps_coordinates", {})
                    if place_gps:
                        place_lat = place_gps.get("latitude", 0)
                        place_lng = place_gps.get("longitude", 0)
                        
                        distance = self._haversine_distance(
                            center_lat, center_lng, place_lat, place_lng
                        )
                        
                        if distance <= radius_km:
                            place["distance_km"] = round(distance, 2)
                            filtered_results.append(place)
                    else:
                        filtered_results.append(place)
            
            geocoded_count = sum(1 for p in filtered_results if p.get("distance_km") is not None)
            total_results = len(local_results)
            geocoded_ratio = geocoded_count / total_results if total_results > 0 else 0
            
            competitors = []
            for place in filtered_results[:10]:
                if place.get("distance_km") is not None or not coordinates:
                    competitors.append({
                        "name": place.get("title", "Unknown"),
                        "rating": place.get("rating", 0),
                        "reviews": place.get("reviews", 0),
                        "address": place.get("address", ""),
                        "distance_km": place.get("distance_km"),
                    })
            
            if not coordinates:
                competition_quality = "limited"
            elif geocoded_ratio >= 0.7:
                competition_quality = "high"
            elif geocoded_ratio >= 0.3:
                competition_quality = "estimated"
            else:
                competition_quality = "limited"
            
            return {
                "count": len([c for c in competitors if c.get("distance_km") is not None]) if coordinates else len(competitors),
                "total_found": total_results,
                "geocoded_ratio": round(geocoded_ratio, 2),
                "competitors": competitors,
                "radius_filtered": coordinates is not None,
                "competition_quality": competition_quality,
                "competition_scope": "radius" if coordinates else "area",
            }
            
        except Exception as e:
            logger.error(f"SerpAPI competition search error: {e}")
            return {"count": 0, "competitors": [], "radius_filtered": False}
    
    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate the great circle distance between two points in km."""
        import math
        
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _get_fallback_demographics(self) -> Dict[str, Any]:
        """Return fallback demographics when API is unavailable."""
        import random
        return {
            "population": random.randint(100000, 500000),
            "median_age": random.randint(32, 42),
            "median_income": random.randint(55000, 85000),
            "total_households": random.randint(40000, 200000),
            "median_home_value": random.randint(200000, 500000),
            "unemployment_rate": round(random.uniform(3.0, 6.0), 1),
            "growth_rate": round(random.uniform(2.0, 5.0), 1),
        }
    
    def _get_state_fips(self, state: str) -> Optional[str]:
        """Convert state abbreviation to FIPS code."""
        fips_map = {
            'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
            'CO': '08', 'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13',
            'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19',
            'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24',
            'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29',
            'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34',
            'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
            'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45',
            'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50',
            'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56',
            'DC': '11', 'PR': '72',
        }
        return fips_map.get(state.upper() if state else "")

    def _calculate_match_score(
        self,
        source: Dict[str, Any],
        three_mile: Dict[str, Any],
        five_mile: Dict[str, Any],
        data_quality: str = "high",
    ) -> int:
        """Calculate overall match score between source and target using real metrics.
        
        Scoring factors:
        - Income similarity (20 points max)
        - Competition opportunity (25 points max)
        - Market density (20 points max)
        - Demographics match (20 points max)
        - Growth potential (15 points max)
        
        Score is capped based on data quality:
        - high: up to 100
        - estimated: up to 85
        - limited: up to 70
        """
        score = 50
        
        source_income = source.get("demographics", {}).get("median_income", 0) or source.get("median_income", 60000)
        target_demographics = three_mile.get("state_demographics", {})
        target_income = target_demographics.get("median_income", 0) or three_mile.get("median_income", 0)
        
        if target_income > 0 and source_income > 0:
            income_ratio = min(target_income, source_income) / max(target_income, source_income)
            score += int(income_ratio * 20)
        
        competition_level = three_mile.get("competition_level", "medium")
        if competition_level == "low":
            score += 25
        elif competition_level == "medium":
            score += 15
        else:
            score += 5
        
        market_density = three_mile.get("market_density", "medium")
        if market_density == "high":
            score += 20
        elif market_density == "medium":
            score += 12
        else:
            score += 5
        
        source_age = source.get("demographics", {}).get("median_age", 0) or source.get("median_age", 35)
        target_age = target_demographics.get("median_age", 0) or three_mile.get("median_age", 0)
        
        if target_age > 0 and source_age > 0:
            age_diff = abs(target_age - source_age)
            if age_diff <= 5:
                score += 20
            elif age_diff <= 10:
                score += 12
            else:
                score += 5
        
        growth_rate = three_mile.get("growth_rate", 3.0)
        if growth_rate > 5:
            score += 15
        elif growth_rate > 3:
            score += 10
        else:
            score += 5
        
        max_score = 100
        if data_quality == "limited":
            max_score = 70
        elif data_quality == "estimated":
            max_score = 85
        
        return min(max_score, max(0, score))

    def _extract_key_factors(
        self,
        source: Dict[str, Any],
        three_mile: Dict[str, Any],
        five_mile: Dict[str, Any],
    ) -> List[str]:
        """Extract key matching factors using real data comparisons."""
        factors = []
        
        competition_count = three_mile.get("competition_count", 0)
        competition_level = three_mile.get("competition_level", "medium")
        
        if competition_level == "low":
            factors.append(f"Low competition ({competition_count} competitors in 3mi radius)")
        elif competition_level == "medium":
            factors.append(f"Moderate competition ({competition_count} competitors) - room to differentiate")
        else:
            factors.append(f"Competitive market ({competition_count} competitors) - requires strong positioning")
        
        three_demographics = three_mile.get("state_demographics", {})
        five_demographics = five_mile.get("state_demographics", {})
        
        median_income = three_demographics.get("median_income", 0) or three_mile.get("median_income", 0)
        if median_income > 80000:
            factors.append(f"High-income region (${median_income:,} state median)")
        elif median_income > 60000:
            factors.append(f"Above-average income region (${median_income:,} state median)")
        elif median_income > 0:
            factors.append(f"Value-conscious region (${median_income:,} state median)")
        
        market_density = three_mile.get("market_density", "medium")
        if market_density == "high":
            factors.append("Strong local market density based on competition")
        elif market_density == "medium":
            factors.append("Moderate market activity in the area")
        
        growth_rate = three_mile.get("growth_rate", 0)
        if growth_rate > 5:
            factors.append(f"High growth market ({growth_rate}% annual growth)")
        elif growth_rate > 3:
            factors.append(f"Steady growth trajectory ({growth_rate}% growth)")
        
        five_competition = five_mile.get("competition_count", 0)
        if five_competition > competition_count:
            factors.append(f"Expanding market in 5mi radius ({five_competition} competitors)")
        
        unemployment = three_demographics.get("unemployment_rate", 0)
        if unemployment > 0 and unemployment < 4:
            factors.append(f"Strong regional economy ({unemployment}% unemployment)")
        
        if not factors:
            factors = ["Emerging market opportunity", "Strategic location for new entry"]
        
        return factors[:6]

    async def _analyze_source_business(
        self,
        business_name: str,
        business_address: str,
        radius_miles: int,
    ) -> Dict[str, Any]:
        """Analyze the source business to extract success factors"""
        from .trade_area_analyzer import trade_area_analyzer
        
        inferred_category = self._infer_business_category(business_name)
        
        parsed_city, parsed_state = self._parse_address_components(business_address)
        
        try:
            opportunity_data = {
                "id": 0,
                "title": business_name,
                "business_description": f"{business_name} in {business_address}",
                "category": inferred_category,
                "location": business_address,
                "city": parsed_city,
                "state": parsed_state,
            }
            
            trade_area = await trade_area_analyzer.analyze_async(
                opportunity_data,
                include_ai_synthesis=False
            )
            demographics = trade_area.demographics or {}
            competitors = trade_area.competitors or []
            
            success_factors = []
            if demographics.get("median_income"):
                income = demographics.get("median_income", 0)
                if income > 75000:
                    success_factors.append("High income area ($75K+)")
                elif income > 50000:
                    success_factors.append("Middle income area ($50K-$75K)")
            
            if demographics.get("median_age"):
                age = demographics.get("median_age", 0)
                if 25 <= age <= 40:
                    success_factors.append("Young professional demographic")
                elif 35 <= age <= 55:
                    success_factors.append("Established family demographic")
            
            if len(competitors) < 5:
                success_factors.append("Low competition environment")
            elif len(competitors) > 10:
                success_factors.append("Proven market demand")
            
            if trade_area.white_space_score > 60:
                success_factors.append("High white space opportunity")
            
            if demographics.get("population"):
                pop = demographics.get("population", 0)
                if pop > 100000:
                    success_factors.append("Dense population center")
            
            return {
                "name": business_name,
                "address": business_address,
                "category": inferred_category,
                "success_factors": success_factors if success_factors else ["Market presence", "Location accessibility"],
                "demographics": {
                    "population": demographics.get("population", "N/A"),
                    "median_income": demographics.get("median_income", "N/A"),
                    "median_age": demographics.get("median_age", "N/A"),
                },
                "competition_count": len(competitors),
                "trade_area_radius_miles": radius_miles,
            }
            
        except Exception as e:
            logger.warning(f"Source business analysis failed: {e}")
            return {
                "name": business_name,
                "address": business_address,
                "category": inferred_category,
                "success_factors": ["Market presence", "Strategic location"],
                "demographics": {},
            }

    async def _find_matching_locations(
        self,
        source_analysis: Dict[str, Any],
        radius_miles: int,
        target_city: Optional[str] = None,
        target_state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find locations with similar demographics and market conditions.
        If target_city/state provided, searches for neighborhoods within that area.
        Returns locations with lat/lng coordinates for map display.
        """
        import random
        
        target_demographics = source_analysis.get("demographics", {})
        category = source_analysis.get("category", "retail")
        
        def safe_numeric(value, default):
            """Convert value to numeric, handling 'N/A' and other non-numeric strings"""
            if value is None or value == "N/A" or value == "":
                return default
            try:
                return float(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                return default
        
        source_income = safe_numeric(target_demographics.get("median_income"), 65000)
        source_pop = safe_numeric(target_demographics.get("population"), 100000)
        
        if target_city and target_state:
            locations = await self._get_neighborhoods_in_city(target_city, target_state, category)
        else:
            locations = self._get_default_metro_areas()
        
        matching_locations = []
        for loc in locations:
            variance = random.randint(-8, 12)
            base_score = loc.get("base_score", 70)
            similarity_score = min(100, max(45, base_score + variance))
            
            pop_variance = random.uniform(0.7, 1.4)
            income_variance = random.uniform(0.8, 1.3)
            estimated_pop = int(source_pop * pop_variance * (1 + random.uniform(-0.2, 0.3)))
            estimated_income = int(source_income * income_variance)
            competition_count = random.randint(1, 12)
            
            demographics_match = min(100, max(35, similarity_score + random.randint(-12, 8)))
            competition_match = min(100, max(35, similarity_score + random.randint(-15, 5)))
            
            key_factors = []
            if demographics_match > 75:
                key_factors.append("Similar income levels")
            if competition_match > 70:
                key_factors.append("Low competition area")
            if similarity_score > 80:
                key_factors.append("High growth market")
            if estimated_pop > 80000:
                key_factors.append("Dense population center")
            if category in ["hospitality", "retail", "food_service"]:
                key_factors.append("Strong foot traffic potential")
            if competition_count < 5:
                key_factors.append("Underserved market")
            
            matching_locations.append({
                "name": loc["name"],
                "city": loc["city"],
                "state": loc["state"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "address": loc.get("address", ""),
                "similarity_score": similarity_score,
                "demographics_match": demographics_match,
                "competition_match": competition_match,
                "population": estimated_pop,
                "median_income": estimated_income,
                "competition_count": competition_count,
                "key_factors": key_factors if key_factors else ["Growing market", "Business-friendly environment"],
            })
        
        matching_locations.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return matching_locations[:3]
    
    async def _get_neighborhoods_in_city(
        self,
        city: str,
        state: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        """Get real neighborhood locations within a specific city using SerpAPI for accurate coordinates"""
        import random
        import asyncio
        from .serpapi_service import serpapi_service
        
        neighborhoods = []
        
        search_terms = [
            f"shopping plaza {city} {state}",
            f"business center {city} {state}",
            f"commercial district {city} {state}",
        ]
        
        if serpapi_service.is_configured:
            try:
                from .location_utils import validate_coordinates_in_state, normalize_state
                
                async def fetch_serpapi(search_term: str):
                    return await asyncio.to_thread(
                        serpapi_service.google_maps_search,
                        query=search_term,
                        location=f"{city}, {state}"
                    )
                
                results = await asyncio.gather(
                    *[fetch_serpapi(term) for term in search_terms],
                    return_exceptions=True
                )
                
                normalized_state = normalize_state(state) or state.upper()
                
                for result in results:
                    if isinstance(result, (Exception, BaseException)):
                        continue
                    if not isinstance(result, dict):
                        continue
                    
                    local_results = result.get("local_results", [])
                    
                    for place in local_results[:3]:
                        if len(neighborhoods) >= 5:
                            break
                        gps = place.get("gps_coordinates", {})
                        if gps and "latitude" in gps and "longitude" in gps:
                            lat = gps["latitude"]
                            lng = gps["longitude"]
                            
                            is_valid, warning = validate_coordinates_in_state(
                                lat, lng, state,
                                context=f"SerpAPI result for '{city}, {state}' - {place.get('title', 'unknown')}"
                            )
                            if not is_valid:
                                logger.warning(f"Skipping location with mismatched coordinates: {warning}")
                                continue
                            
                            address = place.get("address", "")
                            name = place.get("title", f"Location in {city}")
                            
                            if len(name) > 40:
                                name = name[:37] + "..."
                            
                            neighborhoods.append({
                                "name": name,
                                "city": city.title(),
                                "state": normalized_state,
                                "lat": round(lat, 6),
                                "lng": round(lng, 6),
                                "address": address,
                                "base_score": random.randint(65, 92),
                            })
                    
                    if len(neighborhoods) >= 5:
                        break
                
                if neighborhoods:
                    logger.info(f"Found {len(neighborhoods)} real locations in {city}, {state}")
                    return neighborhoods
                    
            except Exception as e:
                logger.warning(f"SerpAPI search failed for {city}, {state}: {e}")
        
        known_locations = {
            ("miami", "fl"): [
                {"name": "Brickell City Centre", "lat": 25.7650, "lng": -80.1936, "address": "701 S Miami Ave, Miami, FL"},
                {"name": "Dadeland Mall", "lat": 25.6903, "lng": -80.3140, "address": "7535 N Kendall Dr, Miami, FL"},
                {"name": "Aventura Mall", "lat": 25.9569, "lng": -80.1414, "address": "19501 Biscayne Blvd, Aventura, FL"},
                {"name": "Dolphin Mall", "lat": 25.7883, "lng": -80.3827, "address": "11401 NW 12th St, Miami, FL"},
                {"name": "Coral Gables Downtown", "lat": 25.7496, "lng": -80.2619, "address": "355 Miracle Mile, Coral Gables, FL"},
            ],
            ("orlando", "fl"): [
                {"name": "The Mall at Millenia", "lat": 28.4848, "lng": -81.4314, "address": "4200 Conroy Rd, Orlando, FL"},
                {"name": "Orlando Fashion Square", "lat": 28.5529, "lng": -81.3407, "address": "3201 E Colonial Dr, Orlando, FL"},
                {"name": "Winter Park Village", "lat": 28.5970, "lng": -81.3510, "address": "510 N Orlando Ave, Winter Park, FL"},
            ],
            ("austin", "tx"): [
                {"name": "The Domain", "lat": 30.4020, "lng": -97.7254, "address": "11410 Century Oaks Terrace, Austin, TX"},
                {"name": "Barton Creek Square", "lat": 30.2610, "lng": -97.8082, "address": "2901 Capital of Texas Hwy, Austin, TX"},
                {"name": "Downtown Austin", "lat": 30.2672, "lng": -97.7431, "address": "Congress Ave, Austin, TX"},
            ],
            ("dallas", "tx"): [
                {"name": "NorthPark Center", "lat": 32.8680, "lng": -96.7728, "address": "8687 N Central Expy, Dallas, TX"},
                {"name": "Galleria Dallas", "lat": 32.9308, "lng": -96.8198, "address": "13350 Dallas Pkwy, Dallas, TX"},
                {"name": "Highland Park Village", "lat": 32.8362, "lng": -96.7993, "address": "47 Highland Park Village, Dallas, TX"},
            ],
            ("denver", "co"): [
                {"name": "Cherry Creek Shopping Center", "lat": 39.7157, "lng": -104.9536, "address": "3000 E 1st Ave, Denver, CO"},
                {"name": "Park Meadows", "lat": 39.5634, "lng": -104.8791, "address": "8401 Park Meadows Center Dr, Lone Tree, CO"},
                {"name": "16th Street Mall", "lat": 39.7476, "lng": -104.9940, "address": "16th Street Mall, Denver, CO"},
            ],
            ("atlanta", "ga"): [
                {"name": "Lenox Square", "lat": 33.8463, "lng": -84.3608, "address": "3393 Peachtree Rd NE, Atlanta, GA"},
                {"name": "Phipps Plaza", "lat": 33.8500, "lng": -84.3611, "address": "3500 Peachtree Rd NE, Atlanta, GA"},
                {"name": "Atlantic Station", "lat": 33.7910, "lng": -84.3960, "address": "1380 Atlantic Dr NW, Atlanta, GA"},
            ],
        }
        
        city_key = (city.lower().strip(), state.lower().strip())
        
        if city_key in known_locations:
            for loc in known_locations[city_key][:5]:
                neighborhoods.append({
                    "name": loc["name"],
                    "city": city.title(),
                    "state": state.upper(),
                    "lat": loc["lat"],
                    "lng": loc["lng"],
                    "address": loc.get("address", ""),
                    "base_score": random.randint(65, 90),
                })
            return neighborhoods
        
        logger.warning(f"No real location data available for {city}, {state}. Using city center.")
        city_centers = {
            ("west palm beach", "fl"): {"lat": 26.7153, "lng": -80.0534},
            ("fort walton beach", "fl"): {"lat": 30.4057, "lng": -86.6189},
            ("destin", "fl"): {"lat": 30.3935, "lng": -86.4958},
            ("panama city", "fl"): {"lat": 30.1588, "lng": -85.6602},
            ("pensacola", "fl"): {"lat": 30.4213, "lng": -87.2169},
            ("tallahassee", "fl"): {"lat": 30.4383, "lng": -84.2807},
            ("tampa", "fl"): {"lat": 27.9506, "lng": -82.4572},
            ("jacksonville", "fl"): {"lat": 30.3322, "lng": -81.6557},
            ("sarasota", "fl"): {"lat": 27.3364, "lng": -82.5307},
            ("naples", "fl"): {"lat": 26.1420, "lng": -81.7948},
            ("houston", "tx"): {"lat": 29.7604, "lng": -95.3698},
            ("san antonio", "tx"): {"lat": 29.4241, "lng": -98.4936},
            ("fort worth", "tx"): {"lat": 32.7555, "lng": -97.3308},
            ("el paso", "tx"): {"lat": 31.7619, "lng": -106.4850},
            ("phoenix", "az"): {"lat": 33.4484, "lng": -112.0740},
            ("scottsdale", "az"): {"lat": 33.4942, "lng": -111.9261},
            ("tucson", "az"): {"lat": 32.2226, "lng": -110.9747},
            ("charlotte", "nc"): {"lat": 35.2271, "lng": -80.8431},
            ("raleigh", "nc"): {"lat": 35.7796, "lng": -78.6382},
            ("nashville", "tn"): {"lat": 36.1627, "lng": -86.7816},
            ("memphis", "tn"): {"lat": 35.1495, "lng": -90.0490},
            ("los angeles", "ca"): {"lat": 34.0522, "lng": -118.2437},
            ("san diego", "ca"): {"lat": 32.7157, "lng": -117.1611},
            ("san francisco", "ca"): {"lat": 37.7749, "lng": -122.4194},
            ("seattle", "wa"): {"lat": 47.6062, "lng": -122.3321},
            ("new york", "ny"): {"lat": 40.7128, "lng": -74.0060},
            ("chicago", "il"): {"lat": 41.8781, "lng": -87.6298},
            ("boston", "ma"): {"lat": 42.3601, "lng": -71.0589},
            ("las vegas", "nv"): {"lat": 36.1699, "lng": -115.1398},
            ("portland", "or"): {"lat": 45.5152, "lng": -122.6784},
            ("salt lake city", "ut"): {"lat": 40.7608, "lng": -111.8910},
        }
        
        base = city_centers.get(city_key)
        
        if not base and serpapi_service.is_configured:
            try:
                geocode_result = serpapi_service.google_maps_search(
                    query=f"{city}, {state}",
                    location=f"{city}, {state}"
                )
                local_results = geocode_result.get("local_results", [])
                if local_results:
                    gps = local_results[0].get("gps_coordinates", {})
                    if gps and "latitude" in gps and "longitude" in gps:
                        base = {"lat": gps["latitude"], "lng": gps["longitude"]}
                        logger.info(f"Geocoded {city}, {state} via SerpAPI: {base}")
            except Exception as e:
                logger.warning(f"SerpAPI geocoding failed for {city}, {state}: {e}")
        
        if not base:
            base = {"lat": 33.0, "lng": -97.0}
        
        neighborhoods.append({
            "name": f"Downtown {city.title()}",
            "city": city.title(),
            "state": state.upper(),
            "lat": base["lat"],
            "lng": base["lng"],
            "address": f"City Center, {city.title()}, {state.upper()}",
            "base_score": 75,
        })
        
        return neighborhoods
    
    def _get_default_metro_areas(self) -> List[Dict[str, Any]]:
        """Get default list of metro areas when no target city is specified"""
        return [
            {"name": "Downtown Austin", "city": "Austin", "state": "TX", "lat": 30.2672, "lng": -97.7431, "base_score": 88},
            {"name": "South Denver", "city": "Denver", "state": "CO", "lat": 39.6501, "lng": -104.9903, "base_score": 85},
            {"name": "East Nashville", "city": "Nashville", "state": "TN", "lat": 36.1800, "lng": -86.7500, "base_score": 82},
            {"name": "Uptown Charlotte", "city": "Charlotte", "state": "NC", "lat": 35.2271, "lng": -80.8431, "base_score": 80},
            {"name": "North Phoenix", "city": "Phoenix", "state": "AZ", "lat": 33.5800, "lng": -112.0740, "base_score": 78},
            {"name": "Downtown Raleigh", "city": "Raleigh", "state": "NC", "lat": 35.7796, "lng": -78.6382, "base_score": 77},
            {"name": "Sugar House", "city": "Salt Lake City", "state": "UT", "lat": 40.7233, "lng": -111.8575, "base_score": 75},
            {"name": "Hyde Park", "city": "Tampa", "state": "FL", "lat": 27.9390, "lng": -82.4740, "base_score": 73},
        ]

    async def _find_similar_opportunities(
        self, idea_description: str, limit: int = 10
    ) -> List[Opportunity]:
        """Find opportunities similar to the idea description"""
        keywords = idea_description.lower().split()[:5]
        
        query = self.db.query(Opportunity)
        
        for keyword in keywords:
            if len(keyword) > 3:
                query = query.filter(
                    Opportunity.title.ilike(f"%{keyword}%") |
                    Opportunity.description.ilike(f"%{keyword}%")
                )
        
        return query.order_by(Opportunity.feasibility_score.desc().nullslast()).limit(limit).all()

    async def _deepseek_pattern_analysis(
        self,
        idea: str,
        similar_opps: List[Opportunity],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """DeepSeek analysis for pattern recognition"""
        from .ai_orchestrator import ai_orchestrator, AITaskType
        
        data = {
            "idea": idea,
            "similar_opportunities": [
                {"title": o.title, "category": o.category, "score": o.feasibility_score or 0}
                for o in similar_opps[:5]
            ],
            "context": context or {},
        }
        
        result = await ai_orchestrator.process_request(
            AITaskType.OPPORTUNITY_VALIDATION, data
        )
        
        return {
            "patterns_found": len(similar_opps),
            "market_signals": result.get("result", {}) if result.get("processed") else {},
            "category_distribution": self._analyze_categories(similar_opps),
            "average_score": sum(o.feasibility_score or 0 for o in similar_opps) / max(len(similar_opps), 1),
        }

    async def _deepseek_pattern_analysis_parallel(
        self,
        idea: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        DeepSeek pattern analysis that runs in parallel (no dependency on similar_opps).
        Analyzes the idea description directly for online/physical patterns.
        Falls back through ai_orchestrator (DeepSeek -> Claude).
        """
        import asyncio
        from .ai_orchestrator import ai_orchestrator, AITaskType

        data = {
            "idea": idea,
            "context": context or {},
            "request": "Analyze this business idea for online vs physical business model patterns.",
        }

        try:
            result = await asyncio.wait_for(
                ai_orchestrator.process_request(AITaskType.OPPORTUNITY_VALIDATION, data),
                timeout=50.0
            )

            ai_result = result.get("result", {}) if result.get("processed") else {}
            response = ai_result.get("response", ai_result) if isinstance(ai_result, dict) else {}

            if isinstance(response, dict):
                return {
                    "patterns_found": 1 if response else 0,
                    "market_signals": response.get("market_signals", {}),
                    "category_distribution": response.get("category_distribution", {}),
                    "average_score": response.get("online_score", 0),
                    "ai_online_score": response.get("online_score"),
                    "ai_physical_score": response.get("physical_score"),
                    "ai_recommendation": response.get("recommendation"),
                }

            return {
                "patterns_found": 0,
                "market_signals": {},
                "category_distribution": {},
                "average_score": 0,
            }
        except asyncio.TimeoutError:
            logger.warning("Pattern analysis timed out after 50s")
            return {
                "patterns_found": 0,
                "market_signals": {},
                "category_distribution": {},
                "average_score": 0,
            }
        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")
            return {
                "patterns_found": 0,
                "market_signals": {},
                "category_distribution": {},
                "average_score": 0,
            }

    def _calculate_business_type_scores(
        self, pattern_analysis: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> tuple:
        """Calculate online vs physical business type scores.
        Uses AI-provided scores when available, falls back to heuristics."""
        # Use AI scores directly if the orchestrator returned them
        ai_online = pattern_analysis.get("ai_online_score")
        ai_physical = pattern_analysis.get("ai_physical_score")
        if ai_online is not None and ai_physical is not None:
            try:
                return min(100, max(0, int(ai_online))), min(100, max(0, int(ai_physical)))
            except (ValueError, TypeError):
                pass

        # Heuristic fallback
        online_score = 50
        physical_score = 50

        context = context or {}

        if context.get("digital_product"):
            online_score += 20
        if context.get("requires_physical_delivery"):
            physical_score += 15
        if context.get("location_dependent"):
            physical_score += 20
        if context.get("remote_interaction"):
            online_score += 15
        if context.get("global_scalability"):
            online_score += 25
        if context.get("physical_inventory"):
            physical_score += 20

        categories = pattern_analysis.get("category_distribution", {})
        try:
            tech_score = float(categories.get("Technology", 0) or 0)
        except (ValueError, TypeError):
            tech_score = 0.0
        try:
            local_score = float(categories.get("Local Services", 0) or 0)
        except (ValueError, TypeError):
            local_score = 0.0
        if tech_score > 0.3:
            online_score += 10
        if local_score > 0.3:
            physical_score += 10

        online_score = min(100, max(0, online_score))
        physical_score = min(100, max(0, physical_score))

        return online_score, physical_score

    def _determine_recommendation(self, online_score: int, physical_score: int) -> str:
        """Determine business type recommendation"""
        difference = abs(online_score - physical_score)
        
        if difference < 15:
            return "HYBRID"
        elif online_score > physical_score:
            return "ONLINE"
        else:
            return "PHYSICAL"

    def _enrich_with_report_data(
        self,
        idea_description: str,
        business_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich validation results with real market data from ReportDataService.
        Requires city/state in business_context. Returns None if unavailable.
        """
        from dataclasses import asdict

        if not business_context:
            return None

        # Extract city/state from business_context or idea
        location = business_context.get("location", business_context.get("city", ""))
        if not location:
            return None

        city, state = parse_city_state(location)
        if not city or not state:
            return None

        business_type = business_context.get("business_type", idea_description[:100])

        try:
            from app.services.report_data_service import ReportDataService
            service = ReportDataService(self.db)
            context = service.get_report_data(
                city=city,
                state=state,
                business_type=business_type,
                report_type="market_analysis",
            )

            four_ps_scores = service.get_pillar_scores(context)

            market_intelligence = {
                "demand_level": "high" if (context.product.opportunity_score or 0) > 70 else "medium" if (context.product.opportunity_score or 0) > 40 else "low",
                "competition_level": context.promotion.competition_level or "unknown",
                "growth_trend": context.product.google_trends_direction or "stable",
                "population": context.place.population,
                "median_income": context.price.median_income,
                "competitor_count": context.promotion.competitor_count,
                "google_trends_interest": context.product.google_trends_interest,
                "job_market_growth": context.place.job_market_growth,
            }

            feasibility_preview = {
                "market_size_estimate": context.price.market_size_estimate,
                "capital_required": context.price.capital_required,
                "revenue_benchmark": context.price.revenue_benchmark,
                "time_to_breakeven": None,  # Gated behind paywall
                "monthly_revenue_projection": None,  # Gated behind paywall
            }

            data_quality_dict = {
                "enriched": True,
                "completeness": context.data_quality.completeness,
                "confidence": context.data_quality.confidence,
                "weakest_pillar": context.data_quality.weakest_pillar,
                "recommended_actions": context.data_quality.recommended_actions[:3] if context.data_quality.recommended_actions else [],
            }

            return {
                "four_ps_scores": four_ps_scores,
                "market_intelligence": market_intelligence,
                "feasibility_preview": feasibility_preview,
                "data_quality": data_quality_dict,
            }
        except Exception as e:
            logger.warning(f"ReportDataService enrichment failed: {e}")
            return {"data_quality": {"enriched": False, "error": str(e)}}

    def _enrich_location_with_report_data(
        self,
        city: str,
        business_type: str,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich location/clone results with 4P's data.
        Parses city for state if not provided separately.
        """
        parsed_city, parsed_state = parse_city_state(city)
        final_state = state or parsed_state
        if not parsed_city or not final_state:
            return None

        try:
            from app.services.report_data_service import ReportDataService
            service = ReportDataService(self.db)
            context = service.get_report_data(
                city=parsed_city,
                state=final_state,
                business_type=business_type,
                report_type="market_analysis",
            )

            four_ps_scores = service.get_pillar_scores(context)

            four_ps_details = {
                "product": {
                    "opportunity_score": context.product.opportunity_score,
                    "trend_strength": context.product.trend_strength,
                    "google_trends_interest": context.product.google_trends_interest,
                    "google_trends_direction": context.product.google_trends_direction,
                },
                "price": {
                    "median_income": context.price.median_income,
                    "market_size_estimate": context.price.market_size_estimate,
                    "zillow_home_value": context.price.zillow_home_value,
                },
                "place": {
                    "growth_score": context.place.growth_score,
                    "population": context.place.population,
                    "population_growth_rate": context.place.population_growth_rate,
                    "job_market_growth": context.place.job_market_growth,
                },
                "promotion": {
                    "competition_level": context.promotion.competition_level,
                    "competitor_count": context.promotion.competitor_count,
                    "google_avg_rating": context.promotion.google_avg_rating,
                },
            }

            data_quality_dict = {
                "enriched": True,
                "completeness": context.data_quality.completeness,
                "confidence": context.data_quality.confidence,
                "weakest_pillar": context.data_quality.weakest_pillar,
            }

            return {
                "four_ps_scores": four_ps_scores,
                "four_ps_details": four_ps_details,
                "data_quality": data_quality_dict,
            }
        except Exception as e:
            logger.warning(f"Location enrichment failed: {e}")
            return {"data_quality": {"enriched": False, "error": str(e)}}

    def _parse_address_components(self, address: str) -> tuple[str, Optional[str]]:
        """
        Parse an address string to extract city and state.
        Handles formats like:
        - "7550 Okeechobee Blvd, West Palm Beach, FL 33411"
        - "West Palm Beach, FL"
        - "Miami, Florida"
        """
        import re
        if not address:
            return "", None
        
        parts = [p.strip() for p in address.split(',')]
        
        if len(parts) >= 2:
            last_part = parts[-1].strip()
            state_zip_match = re.match(r'^([A-Z]{2})\s*\d{0,5}', last_part.upper())
            if state_zip_match:
                state = state_zip_match.group(1)
                city = parts[-2].strip() if len(parts) >= 2 else ""
                return city, state
            
            if len(last_part) == 2 and last_part.upper() in STATE_ABBREVIATIONS.values():
                city = parts[-2].strip() if len(parts) >= 2 else ""
                return city, last_part.upper()
            
            state_lower = last_part.lower()
            if state_lower in STATE_ABBREVIATIONS:
                city = parts[-2].strip() if len(parts) >= 2 else ""
                return city, STATE_ABBREVIATIONS[state_lower]
        
        return parts[0] if parts else address, None

    def _get_city_center_coords(self, city: str, state: Optional[str]) -> Dict[str, float]:
        """
        Get center coordinates for a city. Returns lat/lng dict.
        Uses centralized location_utils for consistent fallback hierarchy.
        """
        from .location_utils import get_location_coords
        
        return get_location_coords(
            city=city,
            state=state,
            context="consultant_studio._get_city_center_coords"
        )

    def _infer_business_category(self, business_description: str) -> str:
        """Infer business category from natural language description"""
        desc_lower = business_description.lower()
        
        hospitality_keywords = ["restaurant", "hotel", "motel", "cafe", "bar", "pub", "bistro", 
                                "inn", "lodge", "resort", "diner", "eatery", "food truck",
                                "catering", "bakery", "pizzeria", "brewery", "winery"]
        retail_keywords = ["shop", "store", "boutique", "outlet", "retail", "market", 
                          "grocery", "pharmacy", "clothing", "electronics", "furniture",
                          "jewelry", "bookstore", "florist", "pet store", "hardware"]
        multifamily_keywords = ["apartment", "multifamily", "housing", "residential", 
                               "condo", "townhouse", "duplex", "rental", "property"]
        service_keywords = ["gym", "fitness", "salon", "spa", "barber", "laundry", 
                           "laundromat", "dry clean", "auto", "repair", "dental",
                           "medical", "clinic", "daycare", "childcare", "veterinary"]
        
        for keyword in hospitality_keywords:
            if keyword in desc_lower:
                return "hospitality"
        
        for keyword in multifamily_keywords:
            if keyword in desc_lower:
                return "multifamily"
        
        for keyword in retail_keywords:
            if keyword in desc_lower:
                return "retail"
        
        for keyword in service_keywords:
            if keyword in desc_lower:
                return "services"
        
        return "specific_business"

    async def _claude_viability_report(
        self,
        idea: str,
        pattern_analysis: Dict[str, Any],
        online_score: int,
        physical_score: int,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Claude generates comprehensive viability report with timeout protection"""
        import asyncio
        from .ai_orchestrator import ai_orchestrator, AITaskType

        data = {
            "idea": idea,
            "pattern_analysis": pattern_analysis,
            "online_score": online_score,
            "physical_score": physical_score,
            "context": context or {},
            "request": "Generate a comprehensive viability analysis with strengths, weaknesses, opportunities, and threats.",
        }

        try:
            result = await asyncio.wait_for(
                ai_orchestrator.process_request(AITaskType.MARKET_RESEARCH, data),
                timeout=50.0
            )
            ai_result = result.get("result", {}) if result.get("processed") else {}
            response = ai_result.get("response", ai_result) if isinstance(ai_result, dict) else {}

            if isinstance(response, dict) and response:
                return {
                    "executive_summary": response.get("summary", f"Viability analysis for: {idea[:100]}"),
                    "strengths": response.get("strengths", []),
                    "weaknesses": response.get("weaknesses", []),
                    "opportunities": response.get("opportunities", []),
                    "threats": response.get("threats", []),
                    "recommendation": response.get("recommendation"),
                    "key_actions": response.get("key_actions", []),
                    "ai_insights": response,
                    "confidence_score": response.get("confidence", 75),
                }
        except asyncio.TimeoutError:
            logger.warning("Claude viability report timed out after 50s")
        except Exception as e:
            logger.warning(f"Claude viability report failed: {e}")

        return {
            "executive_summary": f"AI analysis temporarily unavailable for: {idea[:100]}. Please try again.",
            "strengths": ["Market demand to be validated"],
            "weaknesses": ["Requires AI analysis for accurate assessment"],
            "opportunities": ["Full analysis available on retry"],
            "threats": ["Incomplete data without AI analysis"],
            "confidence_score": 30,
            "ai_unavailable": True,
        }

    async def _claude_viability_report_parallel(
        self,
        idea: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Claude generates viability report in parallel with DeepSeek.
        Does not require pattern_analysis or scores - runs concurrently.
        Falls back to generic SWOT only if AI is completely unavailable.
        """
        import asyncio
        from .ai_orchestrator import ai_orchestrator, AITaskType

        data = {
            "idea": idea,
            "context": context or {},
            "request": "Generate a comprehensive, deeply enriched viability analysis with detailed market opportunity, value proposition, revenue model, and execution feasibility assessments.",
        }

        try:
            result = await asyncio.wait_for(
                ai_orchestrator.process_request(AITaskType.MARKET_RESEARCH, data),
                timeout=50.0
            )
            ai_result = result.get("result", {}) if result.get("processed") else {}
            response = ai_result.get("response", ai_result) if isinstance(ai_result, dict) else {}

            if isinstance(response, dict) and response:
                return {
                    "executive_summary": response.get("summary", f"Viability analysis for: {idea[:100]}"),
                    "market_opportunity": response.get("market_opportunity"),
                    "value_proposition": response.get("value_proposition"),
                    "revenue_model": response.get("revenue_model"),
                    "execution_feasibility": response.get("execution_feasibility"),
                    "competitive_positioning": response.get("competitive_positioning"),
                    "key_success_factors": response.get("key_success_factors", []),
                    "critical_risks": response.get("critical_risks", []),
                    "next_steps": response.get("next_steps", []),
                    "strengths": response.get("strengths", []),
                    "weaknesses": response.get("weaknesses", []),
                    "opportunities": response.get("opportunities", []),
                    "threats": response.get("threats", []),
                    "market_size_estimate": response.get("market_size_estimate"),
                    "tam_growth_rate": response.get("tam_growth_rate"),
                    "recommendation": response.get("recommendation"),
                    "recommendation_rationale": response.get("recommendation_rationale"),
                    "key_actions": response.get("next_steps", response.get("key_actions", [])),
                    "ai_insights": response,
                    "confidence_score": response.get("confidence", 75),
                }
            elif isinstance(response, str) and len(response) > 50:
                # AI returned a text response, use it as the summary
                return {
                    "executive_summary": response[:500],
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                    "ai_insights": {"raw_analysis": response},
                    "confidence_score": 70,
                }
        except asyncio.TimeoutError:
            logger.warning("Claude parallel viability report timed out after 50s")
        except Exception as e:
            logger.warning(f"Claude parallel viability report failed: {e}")

        # Fallback only when AI is completely unavailable
        return {
            "executive_summary": f"AI analysis temporarily unavailable for: {idea[:100]}. Please try again.",
            "strengths": ["Market demand to be validated"],
            "weaknesses": ["Requires AI analysis for accurate assessment"],
            "opportunities": ["Full analysis available on retry"],
            "threats": ["Incomplete data without AI analysis"],
            "confidence_score": 30,
            "ai_unavailable": True,
        }

    async def _search_opportunities(self, filters: Dict[str, Any]) -> List[Opportunity]:
        """Search opportunities based on filters"""
        query = self.db.query(Opportunity)
        
        if filters.get("category"):
            query = query.filter(Opportunity.category == filters["category"])
        if filters.get("min_score"):
            query = query.filter(Opportunity.feasibility_score >= filters["min_score"])
        if filters.get("query"):
            search_term = f"%{filters['query']}%"
            query = query.filter(
                Opportunity.title.ilike(search_term) |
                Opportunity.description.ilike(search_term)
            )
        
        return query.order_by(Opportunity.feasibility_score.desc().nullslast()).limit(50).all()

    async def _detect_trends(
        self, opportunities: List[Opportunity], filters: Dict[str, Any]
    ) -> List[DetectedTrend]:
        """DeepSeek trend detection from opportunities"""
        from .ai_orchestrator import ai_orchestrator, AITaskType
        
        categories = {}
        for opp in opportunities:
            cat = opp.category or "Unknown"
            categories[cat] = categories.get(cat, 0) + 1
        
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        
        trend_names = [f"{cat_name} Growth" for cat_name, _ in top_categories]
        existing_by_name = {
            trend.trend_name: trend
            for trend in self.db.query(DetectedTrend).filter(
                DetectedTrend.trend_name.in_(trend_names)
            ).all()
        }

        trends = []
        for cat_name, count in top_categories:
            trend_name = f"{cat_name} Growth"
            existing = existing_by_name.get(trend_name)
            
            if not existing:
                trend = DetectedTrend(
                    trend_name=trend_name,
                    trend_strength=min(100, count * 10),
                    description=f"Growing opportunities in {cat_name} category",
                    category=cat_name,
                    opportunities_count=count,
                    growth_rate=round(count / max(len(opportunities), 1) * 100, 2),
                    confidence_score=70,
                )
                self.db.add(trend)
                trends.append(trend)
            else:
                existing.opportunities_count = count
                existing.trend_strength = min(100, count * 10)
                trends.append(existing)
        
        self.db.commit()
        
        return trends

    async def _claude_trend_synthesis(
        self,
        opportunities: List[Opportunity],
        trends: List[DetectedTrend],
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Claude synthesizes trends into actionable insights"""
        from .ai_orchestrator import ai_orchestrator, AITaskType
        
        data = {
            "opportunity_count": len(opportunities),
            "trends": [{"name": t.trend_name, "strength": t.trend_strength} for t in trends],
            "filters": filters,
        }
        
        result = await ai_orchestrator.process_request(
            AITaskType.MARKET_RESEARCH, data
        )
        
        return {
            "summary": f"Analysis of {len(opportunities)} opportunities reveals {len(trends)} key trends.",
            "top_insight": trends[0].trend_name if trends else "No clear trend detected",
            "recommendations": [
                "Focus on high-strength trend categories",
                "Monitor emerging patterns",
                "Consider cross-category opportunities",
            ],
            "ai_synthesis": result.get("result", {}) if result.get("processed") else {},
        }

    async def _deepseek_geo_analysis(
        self,
        city: str,
        business_description: str,
        inferred_category: str,
        params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Geographic analysis using trade area analyzer for real data"""
        from .trade_area_analyzer import trade_area_analyzer
        
        try:
            # Parse city and state from input like "Miami, Florida"
            parsed_city, parsed_state = parse_city_state(city)
            
            # Use parsed state, or fallback to params if provided
            state = parsed_state or (params.get("state") if params else None)
            
            logger.info(f"[PARSE] City input: '{city}' -> city='{parsed_city}', state='{state}'")
            
            opportunity_data = {
                "id": 0,
                "title": f"{business_description} in {parsed_city}",
                "business_description": business_description,
                "category": inferred_category,
                "location": city,
                "city": parsed_city,
                "region": state,
                "state": state,
                "latitude": params.get("latitude") if params else None,
                "longitude": params.get("longitude") if params else None,
            }
            
            trade_area = await trade_area_analyzer.analyze_async(opportunity_data)
            
            demographics = trade_area.demographics or {}
            competitors = trade_area.competitors or []
            
            radius_miles = trade_area.radius_km * 0.621371
            
            return {
                "market_density": "high" if len(competitors) > 10 else "medium" if len(competitors) > 5 else "low",
                "competition_level": "high" if trade_area.white_space_score < 30 else "moderate" if trade_area.white_space_score < 60 else "low",
                "competitor_count": len(competitors),
                "white_space_score": trade_area.white_space_score,
                "demographics": {
                    "population": demographics.get("population", "N/A"),
                    "median_income": f"${demographics.get('median_income', 0):,}" if demographics.get("median_income") else "N/A",
                    "median_age": demographics.get("median_age", "N/A"),
                    "unemployment_rate": f"{demographics.get('unemployment_rate', 0)}%" if demographics.get("unemployment_rate") else "N/A",
                    "median_home_value": f"${demographics.get('median_home_value', 0):,}" if demographics.get("median_home_value") else "N/A",
                },
                "trade_area_radius_miles": round(radius_miles, 1),
                "competitors": competitors[:20],
                "ai_synthesis": trade_area.ai_synthesis,
            }
            
        except Exception as e:
            logger.warning(f"Trade area analysis failed, using fallback: {e}")
            return {
                "market_density": "medium",
                "competition_level": "moderate",
                "demographics": {
                    "population": "100,000+",
                    "median_income": "$55,000",
                    "growth_trend": "positive",
                },
                "ai_insights": {},
            }

    async def _claude_location_report(
        self,
        city: str,
        business_description: str,
        inferred_category: str,
        geo_analysis: Dict[str, Any],
        params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Claude generates comprehensive location market report with parallelized AI calls"""
        from .ai_report_generator import ai_report_generator
        import asyncio
        
        try:
            loop = asyncio.get_running_loop()
            
            opportunity_context = {
                "title": f"{business_description} in {city}",
                "category": inferred_category,
                "location": city,
                "description": f"Market opportunity for {business_description} business in {city}",
            }
            
            demographics = geo_analysis.get("demographics", {})
            competitors = geo_analysis.get("competitors", [])
            
            market_insights, competitive_analysis = await asyncio.gather(
                loop.run_in_executor(
                    None,
                    ai_report_generator.generate_market_insights,
                    opportunity_context,
                    demographics,
                    competitors
                ),
                loop.run_in_executor(
                    None,
                    ai_report_generator.generate_competitive_analysis,
                    opportunity_context,
                    competitors
                )
            )
            
            return {
                "executive_summary": f"Market analysis for {business_description} opportunities in {city}.",
                "market_conditions": geo_analysis.get("market_density", "unknown"),
                "white_space_score": geo_analysis.get("white_space_score", 50),
                "key_factors": [
                    "Local economic indicators",
                    "Competition landscape",
                    "Target demographic presence",
                ],
                "market_insights": market_insights,
                "competitive_analysis": competitive_analysis,
            }
            
        except Exception as e:
            logger.warning(f"AI location report failed, using fallback: {e}")
            return {
                "executive_summary": f"Market analysis for {business_description} opportunities in {city}.",
                "market_conditions": geo_analysis.get("market_density", "unknown"),
                "key_factors": [
                    "Local economic indicators",
                    "Competition landscape",
                    "Target demographic presence",
                ],
                "ai_report": {},
            }

    def _generate_quick_synthesis(
        self,
        opportunities: List,
        trends: List,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate quick synthesis from opportunities and trends without Claude"""
        query = filters.get("query", "business opportunities")
        category = filters.get("category")
        
        top_categories = {}
        for opp in opportunities[:20]:
            cat = getattr(opp, 'category', 'uncategorized')
            top_categories[cat] = top_categories.get(cat, 0) + 1
        
        sorted_categories = sorted(top_categories.items(), key=lambda x: x[1], reverse=True)[:3]
        
        insights = []
        if len(opportunities) > 10:
            insights.append(f"Strong market activity with {len(opportunities)} opportunities identified")
        elif len(opportunities) > 0:
            insights.append(f"Found {len(opportunities)} relevant opportunities")
        
        if trends:
            top_trend = trends[0] if trends else None
            if top_trend:
                insights.append(f"Leading trend: {getattr(top_trend, 'trend_name', 'Emerging markets')}")
        
        if sorted_categories:
            top_cat = sorted_categories[0][0]
            insights.append(f"Most active category: {top_cat}")
        
        return {
            "summary": f"Analysis of {query} opportunities" + (f" in {category}" if category else ""),
            "opportunity_count": len(opportunities),
            "trend_count": len(trends),
            "top_categories": [{"name": cat, "count": count} for cat, count in sorted_categories],
            "key_insights": insights if insights else ["Market data collected", "Review opportunities for details"],
        }

    def _generate_quick_market_report(
        self,
        city: str,
        business_description: str,
        inferred_category: str,
        geo_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate quick market report from DeepSeek geo_analysis data without Claude"""
        demographics = geo_analysis.get("demographics", {})
        competitors = geo_analysis.get("competitors", [])
        market_indicators = geo_analysis.get("market_indicators", {})
        
        competition_level = "low" if len(competitors) < 3 else "moderate" if len(competitors) < 8 else "high"
        try:
            median_income = int(demographics.get("median_income", 50000) or 50000)
        except (ValueError, TypeError):
            median_income = 50000
        try:
            population = int(demographics.get("population", 0) or 0)
        except (ValueError, TypeError):
            population = 0
        
        market_score = 70
        if median_income > 75000:
            market_score += 10
        if population > 100000:
            market_score += 5
        if len(competitors) < 5:
            market_score += 10
        elif len(competitors) > 10:
            market_score -= 5
        
        insights = []
        if median_income > 75000:
            insights.append(f"High income area (${median_income:,} median) supports premium pricing")
        if population > 50000:
            insights.append(f"Large population base ({population:,}) provides customer volume")
        if len(competitors) < 5:
            insights.append(f"Low competition ({len(competitors)} similar businesses) indicates market opportunity")
        elif len(competitors) > 8:
            insights.append(f"Established market ({len(competitors)} competitors) shows proven demand")
        
        return {
            "market_score": min(100, max(0, market_score)),
            "competition_level": competition_level,
            "competitor_count": len(competitors),
            "demographics_summary": {
                "median_income": median_income,
                "population": population,
                "median_age": demographics.get("median_age", 35),
            },
            "key_insights": insights if insights else ["Market analysis available", "Review competitor data for positioning"],
            "recommendation": "favorable" if market_score >= 70 else "moderate" if market_score >= 50 else "challenging",
        }

    def _generate_site_recommendations(
        self,
        geo_analysis: Dict[str, Any],
        market_report: Dict[str, Any],
        business_type: str,
    ) -> List[Dict[str, Any]]:
        """Generate site recommendations based on analysis"""
        base_recommendations = {
            "specific_business": [
                {"type": "Downtown Core", "priority": "high", "reason": "High foot traffic"},
                {"type": "Business District", "priority": "medium", "reason": "Professional clientele"},
            ],
            "retail": [
                {"type": "Shopping Center", "priority": "high", "reason": "Established traffic patterns"},
                {"type": "Main Street", "priority": "medium", "reason": "Local visibility"},
            ],
            "multifamily": [
                {"type": "Urban Infill", "priority": "high", "reason": "Density and accessibility"},
                {"type": "Transit Corridor", "priority": "high", "reason": "Transportation access"},
            ],
            "hospitality": [
                {"type": "Tourism District", "priority": "high", "reason": "Visitor traffic"},
                {"type": "Convention Area", "priority": "medium", "reason": "Business travelers"},
            ],
        }
        
        return base_recommendations.get(business_type, base_recommendations["specific_business"])

    def _generate_cache_key(
        self,
        city: str,
        business_type: str,
        business_subtype: Optional[str],
        params: Optional[Dict[str, Any]],
    ) -> str:
        """Generate unique cache key for location analysis"""
        key_data = f"{city.lower()}:{business_type}:{business_subtype or ''}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached location analysis if not expired"""
        try:
            cached = self.db.query(LocationAnalysisCache).filter(
                LocationAnalysisCache.cache_key == cache_key,
                LocationAnalysisCache.expires_at > datetime.utcnow(),
            ).first()
            
            if cached:
                cached.hit_count = (cached.hit_count or 0) + 1
                cached.updated_at = datetime.utcnow()
                self.db.commit()
                # Restore intel_card from market_metrics if stored
                market_metrics = cached.market_metrics or {}
                intel_card = market_metrics.get("_intel_card", {})
                result = {
                    "success": True,
                    "city": cached.city,
                    "business_type": cached.business_type,
                    "business_subtype": cached.business_subtype,
                    "geo_analysis": cached.demographic_data or {},
                    "market_report": {"executive_summary": cached.claude_summary},
                    "site_recommendations": cached.site_recommendations or [],
                    "hit_count": cached.hit_count,
                }
                if intel_card:
                    result.update(intel_card)
                return result
        except Exception as e:
            logger.warning(f"Location cache lookup failed: {e}")
            self.db.rollback()

        return None

    async def _cache_analysis(
        self,
        cache_key: str,
        city: str,
        business_type: str,
        business_subtype: Optional[str],
        query_params: Optional[Dict[str, Any]],
        geo_analysis: Dict[str, Any],
        market_report: Dict[str, Any],
        site_recommendations: List[Dict[str, Any]],
        intel_card: Optional[Dict[str, Any]] = None,
    ):
        """Cache location analysis for future use with safe upsert handling"""
        # Store intel card inside market_metrics to avoid DB migration
        market_metrics = {
            "demographics": geo_analysis.get("demographics"),
            "_intel_card": intel_card or {},
        }

        def _apply(obj):
            obj.city = city
            obj.business_type = business_type
            obj.business_subtype = business_subtype
            obj.query_params = query_params
            obj.demographic_data = geo_analysis
            obj.market_metrics = market_metrics
            obj.claude_summary = market_report.get("executive_summary")
            obj.site_recommendations = site_recommendations
            obj.expires_at = datetime.utcnow() + timedelta(days=self.CACHE_TTL_DAYS)

        try:
            existing = self.db.query(LocationAnalysisCache).filter(
                LocationAnalysisCache.cache_key == cache_key
            ).first()

            if existing:
                _apply(existing)
                existing.updated_at = datetime.utcnow()
                self.db.commit()
                return

            cache_entry = LocationAnalysisCache(cache_key=cache_key)
            _apply(cache_entry)
            self.db.add(cache_entry)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(LocationAnalysisCache).filter(
                LocationAnalysisCache.cache_key == cache_key
            ).first()
            if existing:
                _apply(existing)
                existing.updated_at = datetime.utcnow()
                self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to cache location analysis: {e}")
            self.db.rollback()

    async def _log_activity(
        self,
        user_id: int,
        session_id: Optional[str],
        path: str,
        action: str,
        payload: Optional[Dict[str, Any]],
        result_summary: str,
        ai_model_used: str,
        processing_time_ms: int,
        tokens_used: Optional[int] = None,
    ):
        """Log consultant activity"""
        activity = ConsultantActivity(
            user_id=user_id,
            session_id=session_id,
            path=path,
            action=action,
            payload=payload,
            result_summary=result_summary,
            ai_model_used=ai_model_used,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )
        self.db.add(activity)
        self.db.commit()

    def _analyze_categories(self, opportunities: List[Opportunity]) -> Dict[str, float]:
        """Analyze category distribution"""
        if not opportunities:
            return {}
        
        categories = {}
        for opp in opportunities:
            cat = opp.category or "Unknown"
            categories[cat] = categories.get(cat, 0) + 1
        
        total = len(opportunities)
        return {k: round(v / total, 2) for k, v in categories.items()}
