"""
LLM-Backed AI Engine Service

Provides LLM-enhanced opportunity matching, roadmap generation, and validation.
Falls back to heuristic methods when LLM is unavailable.
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

AI_CALL_TIMEOUT_SECONDS = 90

from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.expert import Expert
from app.models.success_pattern import SuccessPattern
from app.services.json_codec import loads_json
from app.services.ai_engine import ai_engine_service

logger = logging.getLogger(__name__)


_cached_client = None

def get_anthropic_client():
    """
    Get Anthropic client - prioritizes direct API key over Replit connector.
    
    Priority:
    1. Direct API key (ANTHROPIC_API_KEY) - no model limits
    2. Replit AI Integrations (fallback, has 2-model limit)
    """
    global _cached_client
    if _cached_client is not None:
        return _cached_client
    
    # Priority 1: Direct Anthropic API key (no connector limitations)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        api_key = os.getenv("CLAUDE_API")
    
    if api_key:
        try:
            import anthropic
            logger.info("Using direct Anthropic API key (no model limits)")
            _cached_client = anthropic.Anthropic(api_key=api_key)
            return _cached_client
        except Exception as e:
            logger.error(f"Failed to create Anthropic client with direct key: {e}")
    
    # Priority 2: Replit AI Integrations (fallback, has 2-model limit)
    connector_key = os.getenv("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
    connector_url = os.getenv("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
    
    if connector_key and connector_url:
        try:
            import anthropic
            logger.info("Using Replit AI Integrations for Anthropic (2-model limit applies)")
            _cached_client = anthropic.Anthropic(api_key=connector_key, base_url=connector_url)
            return _cached_client
        except Exception as e:
            logger.error(f"Failed to create Anthropic client with AI Integrations: {e}")
    
    logger.warning("No Anthropic API key found - set ANTHROPIC_API_KEY for unlimited models")
    return None


def call_with_cache(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-opus-4-5",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    user_id: Optional[int] = None,
    db=None,
    event_type: Optional[str] = None,
) -> Optional[str]:
    """
    Make an API call with Anthropic prompt caching enabled.
    
    The system prompt is cached server-side for 5 minutes, reducing costs
    by up to 90% on subsequent calls with the same system prompt.
    
    Args:
        system_prompt: The system message (will be cached)
        user_prompt: The user message
        model: Model to use (default: claude-opus-4-5)
        max_tokens: Max response tokens
        temperature: Sampling temperature
        user_id: Optional user ID to record token usage for billing
        db: Optional DB session required when user_id is provided
        event_type: Optional label for the AI call (e.g. "opportunity_analysis")
    
    Returns:
        Response text or None on error
    """
    client = get_anthropic_client()
    if not client:
        logger.error("[CachedAI] No Anthropic client available")
        return None
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Log cache stats and record usage for billing
        if hasattr(response, 'usage'):
            usage = response.usage
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            cache_create = getattr(usage, 'cache_creation_input_tokens', 0)
            if cache_read > 0:
                logger.info(f"[CachedAI] Cache HIT: {cache_read} tokens from cache (90% savings)")
            elif cache_create > 0:
                logger.info(f"[CachedAI] Cache MISS: {cache_create} tokens cached for next call")

            # Record to Stripe Token Billing + local tracking if user context provided
            if user_id and db:
                try:
                    from app.services.stripe_token_billing import record_token_usage
                    record_token_usage(
                        user_id=user_id,
                        model=model,
                        input_tokens=getattr(usage, 'input_tokens', 0),
                        output_tokens=getattr(usage, 'output_tokens', 0),
                        db=db,
                        event_type=event_type,
                    )
                except Exception as billing_err:
                    logger.warning(f"[CachedAI] Token billing record failed: {billing_err}")

        return response.content[0].text
        
    except Exception as e:
        logger.error(f"[CachedAI] Error: {e}")
        return None


class LLMAIEngineService:
    """
    LLM-enhanced AI Engine service.
    
    Uses Claude for:
    - Smarter opportunity-user matching with personalized insights
    - Detailed roadmap generation with customized milestones
    - Comprehensive validation with market analysis
    - Learning from success_patterns for better predictions
    """
    
    def __init__(self):
        self.model = "claude-opus-4-5"
        self.fast_model = "claude-haiku-4-5"
    
    def _get_success_patterns_context(self, db: Session, opportunity_type: str = None, limit: int = 5) -> str:
        """Get relevant success patterns for context."""
        q = db.query(SuccessPattern)
        if opportunity_type:
            q = q.filter(SuccessPattern.opportunity_type == opportunity_type)
        patterns = q.order_by(SuccessPattern.created_at.desc()).limit(limit).all()
        
        if not patterns:
            return "No historical success patterns available yet."
        
        context_parts = []
        for p in patterns:
            experts = loads_json(p.experts_used, default=[])
            factors = loads_json(p.success_factors, default=[])
            context_parts.append(
                f"- Revenue: ${float(p.revenue_generated or 0):,.0f}, "
                f"Capital: ${float(p.capital_spent or 0):,.0f}, "
                f"Experts: {len(experts)}, "
                f"Key factors: {', '.join(factors[:3]) if factors else 'N/A'}"
            )
        
        return "Historical success patterns:\n" + "\n".join(context_parts)
    
    def match_opportunity_to_user_llm(
        self, 
        db: Session, 
        user: User, 
        opportunity_id: int,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        LLM-enhanced opportunity matching.
        
        Provides personalized fit analysis and recommendations.
        """
        opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opp:
            raise ValueError("Opportunity not found")
        
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        
        heuristic_result = ai_engine_service.match_opportunity_to_user(db, user, opportunity_id)
        
        if not use_llm:
            return heuristic_result
        
        client = get_anthropic_client()
        if not client:
            logger.info("LLM not available, using heuristic match")
            return heuristic_result
        
        try:
            user_skills = loads_json(profile.skills if profile else None, default=[])
            user_capital = profile.available_capital if profile else None
            user_time = profile.time_commitment_hours_per_week if profile else None
            
            success_context = self._get_success_patterns_context(db, opp.category)
            
            prompt = f"""Analyze the fit between this user and opportunity.

OPPORTUNITY:
- Title: {opp.title}
- Category: {opp.category}
- Description: {opp.description[:500] if opp.description else 'N/A'}
- Validation Count: {opp.validation_count or 0}
- AI Score: {opp.ai_opportunity_score or 'Not scored'}

USER PROFILE:
- Skills: {', '.join(user_skills[:10]) if user_skills else 'Not specified'}
- Available Capital: ${float(user_capital):,.0f} if {user_capital} else 'Not specified'
- Weekly Time Commitment: {user_time} hours if {user_time} else 'Not specified'

{success_context}

Provide a JSON response with:
1. "fit_score": 0-100 score of how well this opportunity fits the user
2. "confidence": 0-1 confidence in the assessment
3. "gaps": array of skill/resource gaps the user has
4. "insights": 2-3 personalized insights about this match
5. "recommended_actions": 2-3 specific next steps

Respond only with valid JSON."""

            response = client.messages.create(
                model=self.fast_model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            llm_result = json.loads(response_text)
            
            return {
                "fit_score": llm_result.get("fit_score", heuristic_result["fit_score"]),
                "confidence": llm_result.get("confidence", heuristic_result["confidence"]),
                "gaps": llm_result.get("gaps", heuristic_result["gaps"]),
                "insights": llm_result.get("insights", []),
                "recommended_actions": llm_result.get("recommended_actions", []),
                "recommended_experts": heuristic_result["recommended_experts"],
                "llm_enhanced": True,
            }
            
        except Exception as e:
            logger.error(f"LLM match failed, using heuristic: {e}")
            return heuristic_result
    
    def generate_roadmap_llm(
        self,
        db: Session,
        user: User,
        opportunity_id: int,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        LLM-enhanced roadmap generation.
        
        Creates personalized milestones based on user profile and success patterns.
        """
        opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opp:
            raise ValueError("Opportunity not found")
        
        heuristic_result = ai_engine_service.generate_roadmap(db, user, opportunity_id)
        
        if not use_llm:
            return heuristic_result
        
        client = get_anthropic_client()
        if not client:
            logger.info("LLM not available, using heuristic roadmap")
            return heuristic_result
        
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            user_skills = loads_json(profile.skills if profile else None, default=[])
            user_time = profile.time_commitment_hours_per_week if profile else 10
            
            success_context = self._get_success_patterns_context(db, opp.category)
            
            prompt = f"""Generate a personalized execution roadmap for this opportunity.

OPPORTUNITY:
- Title: {opp.title}
- Category: {opp.category}
- Description: {opp.description[:500] if opp.description else 'N/A'}
- AI Next Steps: {loads_json(opp.ai_next_steps, default=['Validate problem', 'Build MVP', 'Launch'])}

USER CONTEXT:
- Skills: {', '.join(user_skills[:8]) if user_skills else 'General'}
- Weekly hours available: {user_time}

{success_context}

Create a JSON response with:
1. "timeline_weeks": estimated total weeks to MVP
2. "milestones": array of 5-8 milestones, each with:
   - "week": target week number
   - "title": milestone title
   - "description": what to accomplish
   - "deliverables": specific deliverables
   - "estimated_hours": hours needed
3. "success_probability": 0-100 probability estimate
4. "capital_estimate_cents": estimated capital needed in cents
5. "key_assumptions": list of assumptions

Respond only with valid JSON."""

            response = client.messages.create(
                model=self.fast_model,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            llm_result = json.loads(response_text)
            
            return {
                "opportunity_id": opportunity_id,
                "timeline_weeks": llm_result.get("timeline_weeks", heuristic_result["timeline_weeks"]),
                "milestones": llm_result.get("milestones", heuristic_result["milestones"]),
                "success_probability": llm_result.get("success_probability", 50),
                "capital_estimate_cents": llm_result.get("capital_estimate_cents"),
                "key_assumptions": llm_result.get("key_assumptions", []),
                "risks": heuristic_result.get("risks", []),
                "llm_enhanced": True,
            }
            
        except Exception as e:
            logger.error(f"LLM roadmap failed, using heuristic: {e}")
            return heuristic_result
    
    def validate_opportunity_llm(
        self,
        db: Session,
        user: User,
        opportunity_id: int,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        LLM-enhanced opportunity validation.
        
        Provides comprehensive market and feasibility analysis.
        """
        opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opp:
            raise ValueError("Opportunity not found")
        
        heuristic_result = ai_engine_service.validate_opportunity(db, user, opportunity_id)
        
        if not use_llm:
            return heuristic_result
        
        client = get_anthropic_client()
        if not client:
            logger.info("LLM not available, using heuristic validation")
            return heuristic_result
        
        try:
            success_context = self._get_success_patterns_context(db, opp.category)
            
            prompt = f"""Validate this business opportunity and provide actionable analysis.

OPPORTUNITY:
- Title: {opp.title}
- Category: {opp.category}
- Description: {opp.description[:800] if opp.description else 'N/A'}
- Validation Count: {opp.validation_count or 0}
- Current AI Score: {opp.ai_opportunity_score or 'Not scored'}
- Severity: {opp.severity or 3}/5

{success_context}

Provide a comprehensive JSON response with:
1. "validation_score": 0-100 overall score
2. "verdict": "fast_track" (80+), "refine" (60-79), or "pivot" (<60)
3. "market_analysis": brief market opportunity assessment
4. "competitive_landscape": brief competitive analysis
5. "key_risks": array of top 3-5 risks
6. "next_steps": array of 3-5 actionable next steps
7. "success_factors": what would make this succeed
8. "pivot_suggestions": alternative directions if score is low

Respond only with valid JSON."""

            response = client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            llm_result = json.loads(response_text)
            
            return {
                "opportunity_id": opportunity_id,
                "validation_score": llm_result.get("validation_score", heuristic_result["validation_score"]),
                "verdict": llm_result.get("verdict", heuristic_result["verdict"]),
                "market_analysis": llm_result.get("market_analysis"),
                "competitive_landscape": llm_result.get("competitive_landscape"),
                "key_risks": llm_result.get("key_risks", heuristic_result["key_risks"]),
                "next_steps": llm_result.get("next_steps", heuristic_result["next_steps"]),
                "success_factors": llm_result.get("success_factors"),
                "pivot_suggestions": llm_result.get("pivot_suggestions"),
                "llm_enhanced": True,
            }
            
        except Exception as e:
            logger.error(f"LLM validation failed, using heuristic: {e}")
            return heuristic_result


    async def generate_response(self, prompt: str, model: str = "deepseek") -> Dict[str, Any]:
        """
        Generate a response from the AI model.
        
        Args:
            prompt: The prompt to send to the model
            model: Which model to use ("deepseek" or "claude")
        
        Returns:
            Dictionary with the response
        """
        client = get_anthropic_client()
        if not client:
            logger.warning("No AI client available, returning empty response")
            return {"error": "ai_unavailable", "error_message": "AI service not available", "response": None}
        
        try:
            model_id = self.fast_model if model == "deepseek" else self.model
            
            def sync_call():
                return client.messages.create(
                    model=model_id,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
            
            response = await asyncio.wait_for(
                asyncio.to_thread(sync_call),
                timeout=AI_CALL_TIMEOUT_SECONDS
            )
            
            response_text = response.content[0].text.strip()
            
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            try:
                parsed = json.loads(response_text)
                return {"response": parsed, "raw": response_text}
            except json.JSONDecodeError:
                return {"response": response_text, "raw": response_text}
        
        except asyncio.TimeoutError:
            logger.error(f"AI generation timed out after {AI_CALL_TIMEOUT_SECONDS}s")
            return {"error": "ai_timeout", "error_message": f"AI call timed out after {AI_CALL_TIMEOUT_SECONDS} seconds", "response": None}
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return {"error": "ai_error", "error_message": str(e), "response": None}


llm_ai_engine_service = LLMAIEngineService()
