import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from anthropic import Anthropic

from app.models.scraped_source import ScrapedSource
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

MAX_CONCURRENT_CLAUDE_CALLS = 5
AI_CALL_TIMEOUT_SECONDS = 30
MIN_OPPORTUNITY_SCORE = 50

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")


class OpportunityProcessor:
    def __init__(self, db: Session, user=None):
        self.db = db
        self.user = user
        self.client = None
        self._unified_ai = None
        if AI_INTEGRATIONS_ANTHROPIC_API_KEY and AI_INTEGRATIONS_ANTHROPIC_BASE_URL:
            self.client = Anthropic(
                api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
                base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
            )
    
    @property
    def unified_ai(self):
        """Lazy load unified AI service."""
        if self._unified_ai is None:
            from app.services.unified_ai_service import get_ai_service
            self._unified_ai = get_ai_service(self.db, user=self.user)
        return self._unified_ai

    async def process_pending_sources(self, limit: int = 20) -> Dict[str, Any]:
        sources = self.db.query(ScrapedSource).filter(
            ScrapedSource.processed == 0
        ).order_by(ScrapedSource.received_at.desc()).limit(limit).all()

        if not sources:
            return {"processed": 0, "opportunities_created": 0, "skipped": 0}

        stats = {"processed": 0, "opportunities_created": 0, "skipped": 0, "errors": 0}
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_CLAUDE_CALLS)
        
        async def process_with_semaphore(source: ScrapedSource) -> Tuple[ScrapedSource, Dict[str, Any]]:
            async with semaphore:
                try:
                    raw_data = source.raw_data or {}
                    raw_text = self._extract_text_from_raw_data(raw_data, source.source_type)
                    
                    if not raw_text or len(raw_text) < 20:
                        return source, {"skipped": True, "reason": "insufficient_content"}
                    
                    existing = self.db.query(Opportunity).filter(
                        Opportunity.source_id == source.external_id
                    ).first()
                    if existing:
                        return source, {"skipped": True, "reason": "duplicate"}
                    
                    analysis = await self._analyze_with_claude(raw_text, source.source_type, raw_data)
                    return source, {"analysis": analysis, "raw_data": raw_data}
                except Exception as e:
                    logger.error(f"Error analyzing source {source.id}: {e}")
                    return source, {"error": str(e)}
        
        results = await asyncio.gather(*[process_with_semaphore(s) for s in sources])
        
        for source, result in results:
            stats["processed"] += 1
            
            if result.get("error"):
                source.processed = -1
                source.error_message = result["error"][:500]
                stats["errors"] += 1
            elif result.get("skipped"):
                source.processed = 1
                source.processed_at = datetime.utcnow()
                stats["skipped"] += 1
            else:
                analysis = result.get("analysis", {})
                raw_data = result.get("raw_data", {})
                
                if not analysis.get("is_valid_opportunity", False):
                    source.processed = 1
                    source.processed_at = datetime.utcnow()
                    stats["skipped"] += 1
                else:
                    opportunity_score = analysis.get("opportunity_score") or 0
                    if opportunity_score < MIN_OPPORTUNITY_SCORE:
                        logger.info(f"Skipping source {source.id}: opportunity_score {opportunity_score} below minimum {MIN_OPPORTUNITY_SCORE}")
                        source.processed = 1
                        source.processed_at = datetime.utcnow()
                        stats["skipped"] += 1
                    else:
                        opportunity = self._create_opportunity_from_analysis(source, analysis, raw_data)
                        self.db.add(opportunity)
                        source.processed = 1
                        source.processed_at = datetime.utcnow()
                        stats["opportunities_created"] += 1

        self.db.commit()
        logger.info(f"Opportunity processing complete: {stats}")
        return stats
    
    def _create_opportunity_from_analysis(self, source: ScrapedSource, analysis: Dict, raw_data: Dict) -> Opportunity:
        lat = raw_data.get("latitude") or raw_data.get("lat")
        lng = raw_data.get("longitude") or raw_data.get("lng") or raw_data.get("lon")
        
        return Opportunity(
            title=analysis.get("professional_title", "Untitled Opportunity")[:500],
            description=analysis.get("professional_description", "")[:5000],
            category=analysis.get("category", "Other")[:100],
            subcategory=analysis.get("subcategory"),
            severity=analysis.get("severity", 3),
            market_size=analysis.get("market_size"),
            geographic_scope=analysis.get("geographic_scope", "online"),
            country=analysis.get("country"),
            region=analysis.get("region"),
            city=analysis.get("city"),
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            feasibility_score=analysis.get("feasibility_score"),
            source_id=source.external_id,
            source_url=raw_data.get("url") or raw_data.get("link"),
            source_platform=source.source_type,
            ai_analyzed=True,
            ai_analyzed_at=datetime.utcnow(),
            ai_opportunity_score=analysis.get("opportunity_score"),
            ai_summary=analysis.get("one_line_summary", "")[:500],
            ai_market_size_estimate=analysis.get("market_size_estimate"),
            ai_competition_level=analysis.get("competition_level"),
            ai_urgency_level=analysis.get("urgency_level"),
            ai_target_audience=analysis.get("target_audience"),
            ai_pain_intensity=analysis.get("pain_intensity"),
            ai_business_model_suggestions=json.dumps(analysis.get("business_models", [])),
            ai_key_risks=json.dumps(analysis.get("key_risks", [])),
            ai_next_steps=json.dumps(analysis.get("next_steps", [])),
            ai_problem_statement=analysis.get("problem_statement"),
        )

    async def _process_single_source(self, source: ScrapedSource) -> Dict[str, Any]:
        raw_data = source.raw_data or {}
        raw_text = self._extract_text_from_raw_data(raw_data, source.source_type)

        if not raw_text or len(raw_text) < 20:
            source.processed = 1
            source.processed_at = datetime.utcnow()
            return {"skipped": True, "reason": "insufficient_content"}

        existing = self.db.query(Opportunity).filter(
            Opportunity.source_id == source.external_id
        ).first()
        if existing:
            source.processed = 1
            source.processed_at = datetime.utcnow()
            return {"skipped": True, "reason": "duplicate"}

        analysis = await self._analyze_with_claude(raw_text, source.source_type)

        if not analysis.get("is_valid_opportunity", False):
            source.processed = 1
            source.processed_at = datetime.utcnow()
            return {"skipped": True, "reason": "not_an_opportunity"}

        opportunity = Opportunity(
            title=analysis.get("professional_title", "Untitled Opportunity")[:500],
            description=analysis.get("professional_description", raw_text)[:5000],
            category=analysis.get("category", "Other")[:100],
            subcategory=analysis.get("subcategory"),
            severity=analysis.get("severity", 3),
            market_size=analysis.get("market_size"),
            geographic_scope=analysis.get("geographic_scope", "online"),
            country=analysis.get("country"),
            region=analysis.get("region"),
            city=analysis.get("city"),
            feasibility_score=analysis.get("feasibility_score"),
            source_id=source.external_id,
            source_url=raw_data.get("url") or raw_data.get("link"),
            source_platform=source.source_type,
            ai_analyzed=True,
            ai_analyzed_at=datetime.utcnow(),
            ai_opportunity_score=analysis.get("opportunity_score"),
            ai_summary=analysis.get("one_line_summary", "")[:500],
            ai_market_size_estimate=analysis.get("market_size_estimate"),
            ai_competition_level=analysis.get("competition_level"),
            ai_urgency_level=analysis.get("urgency_level"),
            ai_target_audience=analysis.get("target_audience"),
            ai_pain_intensity=analysis.get("pain_intensity"),
            ai_business_model_suggestions=json.dumps(analysis.get("business_models", [])),
            ai_key_risks=json.dumps(analysis.get("key_risks", [])),
            ai_next_steps=json.dumps(analysis.get("next_steps", [])),
            ai_generated_title=analysis.get("professional_title"),
            ai_problem_statement=analysis.get("problem_statement"),
            raw_source_data=json.dumps(raw_data),
            status="active",
        )

        self.db.add(opportunity)
        source.processed = 1
        source.processed_at = datetime.utcnow()

        return {"opportunity_created": True, "title": opportunity.title}

    def _extract_text_from_raw_data(self, raw_data: Dict, source_type: str) -> str:
        if source_type == "twitter":
            return raw_data.get("full_text") or raw_data.get("text") or raw_data.get("rawContent", "")
        elif source_type == "reddit":
            title = raw_data.get("title", "")
            body = raw_data.get("body") or raw_data.get("selftext", "")
            return f"{title}\n\n{body}".strip()
        elif source_type == "google_maps":
            name = raw_data.get("title") or raw_data.get("name", "")
            category = raw_data.get("categoryName", "")
            reviews = raw_data.get("reviewsText", "")
            return f"{name} - {category}\n\n{reviews}".strip()
        elif source_type in ["craigslist", "custom"]:
            title = raw_data.get("title") or raw_data.get("Title", "")
            desc = raw_data.get("description", "")
            keyword = raw_data.get("keyword") or raw_data.get("Keyword", "")
            return f"{title}\n{keyword}\n{desc}".strip()
        elif source_type == "yelp":
            name = raw_data.get("name", "")
            categories = ", ".join(raw_data.get("categories", []))
            reviews = raw_data.get("review_text", "")
            return f"{name} - {categories}\n\n{reviews}".strip()
        else:
            return str(raw_data.get("text") or raw_data.get("content") or raw_data.get("title", ""))

    async def _analyze_with_claude(self, raw_text: str, source_type: str, raw_data: Dict = None) -> Dict[str, Any]:
        # Try unified AI service first (for billing tracking)
        use_unified = True
        if not self.client and not self.unified_ai:
            logger.warning("No AI client available, using fallback analysis")
            return self._fallback_analysis(raw_text, source_type)

        prompt = f"""Analyze this raw data from {source_type} and determine if it represents a valid business opportunity.

RAW CONTENT:
{raw_text[:3000]}

You must respond with a valid JSON object containing these fields:

{{
    "is_valid_opportunity": true/false (Is this a genuine business problem or market gap that could be solved?),
    "professional_title": "A clear, professional title for this opportunity (50-100 chars)",
    "professional_description": "A well-written, professional description of the opportunity. Rewrite any informal language to sound like a market research report. 2-3 paragraphs.",
    "one_line_summary": "One compelling sentence summarizing this opportunity",
    "problem_statement": "Clear articulation of the problem this opportunity addresses",
    "category": "One of: Technology, Healthcare, Finance, Education, Retail, Food & Beverage, Real Estate, Transportation, Entertainment, B2B Services, Consumer Services, Manufacturing, Other",
    "subcategory": "More specific subcategory",
    "severity": 1-5 (How severe is this pain point?),
    "opportunity_score": 0-100 (How promising is this as a business opportunity?),
    "feasibility_score": 0-100 (How feasible is it to execute on this?),
    "market_size_estimate": "$XM-$YB range",
    "competition_level": "low/medium/high",
    "urgency_level": "low/medium/high/critical",
    "target_audience": "Primary customer segment",
    "pain_intensity": 1-10,
    "geographic_scope": "online/local/regional/national/international",
    "country": "Country if applicable",
    "region": "Region/state if applicable",
    "city": "City if applicable",
    "business_models": ["List of 2-3 potential business models"],
    "key_risks": ["List of 2-3 main risks"],
    "next_steps": ["List of 3 recommended next steps to validate this opportunity"]
}}

Important: 
- Rewrite informal Reddit/Twitter language into professional business language
- If the content is just spam, ads, or irrelevant chatter, set is_valid_opportunity to false
- Focus on identifying real pain points and market gaps
- Be conservative with opportunity scores - only high-quality signals should score above 70"""

        try:
            # Use unified AI service if available
            if self.unified_ai:
                try:
                    result = await asyncio.wait_for(
                        self.unified_ai.complete(
                            prompt=prompt,
                            task_type="simple_classification",
                            model_id="claude-haiku-4",
                            max_tokens=2000
                        ),
                        timeout=AI_CALL_TIMEOUT_SECONDS
                    )
                    response_text = result["content"]
                except Exception as e:
                    logger.warning(f"Unified AI failed, falling back: {e}")
                    if not self.client:
                        return self._fallback_analysis(raw_text, source_type)
                    # Fall through to direct client
                    def sync_claude_call():
                        return self.client.messages.create(
                            model="claude-haiku-4-5",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": prompt}]
                        )
                    message = await asyncio.wait_for(
                        asyncio.to_thread(sync_claude_call),
                        timeout=AI_CALL_TIMEOUT_SECONDS
                    )
                    response_text = message.content[0].text
            else:
                def sync_claude_call():
                    return self.client.messages.create(
                        model="claude-haiku-4-5",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                
                message = await asyncio.wait_for(
                    asyncio.to_thread(sync_claude_call),
                    timeout=AI_CALL_TIMEOUT_SECONDS
                )
                
                response_text = message.content[0].text
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            analysis = json.loads(response_text.strip())
            return analysis
        
        except asyncio.TimeoutError:
            logger.error(f"Claude API call timed out after {AI_CALL_TIMEOUT_SECONDS}s")
            return self._fallback_analysis(raw_text, source_type)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return self._fallback_analysis(raw_text, source_type)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_analysis(raw_text, source_type)

    def _fallback_analysis(self, raw_text: str, source_type: str) -> Dict[str, Any]:
        pain_keywords = ["frustrating", "annoying", "need", "want", "wish", "problem", "issue", "difficult"]
        has_pain = any(word in raw_text.lower() for word in pain_keywords)
        
        if not has_pain or len(raw_text) < 50:
            return {"is_valid_opportunity": False}

        return {
            "is_valid_opportunity": True,
            "professional_title": raw_text[:100].strip(),
            "professional_description": raw_text[:1000],
            "one_line_summary": raw_text[:200],
            "problem_statement": raw_text[:500],
            "category": "Other",
            "severity": 3,
            "opportunity_score": MIN_OPPORTUNITY_SCORE,
            "feasibility_score": MIN_OPPORTUNITY_SCORE,
            "competition_level": "medium",
            "urgency_level": "medium",
            "geographic_scope": "online",
            "business_models": [],
            "key_risks": [],
            "next_steps": [],
        }


opportunity_processor = None

def get_opportunity_processor(db: Session) -> OpportunityProcessor:
    return OpportunityProcessor(db)
