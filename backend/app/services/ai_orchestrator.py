"""
AI Orchestrator - Coordinates between DeepSeek and Claude AI services
Implements the dual-AI architecture from the OppGrid roadmap
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

AI_CALL_TIMEOUT_SECONDS = 45


class AITaskType(Enum):
    """Types of AI tasks for routing decisions"""
    PLATFORM_COORDINATION = "platform_coordination"
    OPPORTUNITY_VALIDATION = "opportunity_validation"
    CONTENT_REWRITING = "content_rewriting"
    BUSINESS_PLAN_GENERATION = "business_plan_generation"
    MARKET_RESEARCH = "market_research"
    IDEA_ANALYSIS = "idea_analysis"
    DOCUMENT_GENERATION = "document_generation"
    LEAD_SCORING = "lead_scoring"
    EXPERT_MATCHING = "expert_matching"


class AIOrchestrator:
    """Routes requests between DeepSeek and Claude based on task type"""

    def __init__(self):
        self.deepseek_tasks = {
            AITaskType.PLATFORM_COORDINATION,
            AITaskType.OPPORTUNITY_VALIDATION,
            AITaskType.LEAD_SCORING,
        }
        self.claude_tasks = {
            AITaskType.BUSINESS_PLAN_GENERATION,
            AITaskType.MARKET_RESEARCH,
            AITaskType.DOCUMENT_GENERATION,
        }
        self.hybrid_tasks = {
            AITaskType.CONTENT_REWRITING,
            AITaskType.IDEA_ANALYSIS,
            AITaskType.EXPERT_MATCHING,
        }

    async def process_request(
        self, task_type: AITaskType, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route AI request to appropriate service based on task type.
        Falls back to Claude if DeepSeek fails.
        """
        logger.info(f"Processing {task_type.value} request")

        if task_type in self.deepseek_tasks:
            result = await self._call_deepseek(data, task_type)
            # Fallback to Claude if DeepSeek failed
            if not result.get("processed"):
                logger.info(f"DeepSeek failed for {task_type.value}, falling back to Claude")
                result = await self._call_claude(data, task_type)
            return result
        elif task_type in self.claude_tasks:
            return await self._call_claude(data, task_type)
        elif task_type in self.hybrid_tasks:
            return await self._process_hybrid(data, task_type)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _call_deepseek(
        self, data: Dict[str, Any], task_type: AITaskType
    ) -> Dict[str, Any]:
        """Call DeepSeek service for platform coordination tasks"""
        import openai
        import json

        deepseek_key = os.getenv("DEEPSEEK_API_KEY")

        if not deepseek_key:
            logger.warning("DeepSeek API key not found, falling back to Claude")
            return await self._call_claude(data, task_type)

        prompt = self._build_prompt_for_task(task_type, data)

        def sync_deepseek_call():
            client = openai.OpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com",
                timeout=AI_CALL_TIMEOUT_SECONDS
            )
            return client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(sync_deepseek_call),
                timeout=AI_CALL_TIMEOUT_SECONDS
            )

            response_text = response.choices[0].message.content.strip()

            try:
                clean_text = response_text
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("```")[1]
                    if clean_text.startswith("json"):
                        clean_text = clean_text[4:]
                parsed = json.loads(clean_text)
                result = {"response": parsed, "raw": response_text}
            except json.JSONDecodeError:
                result = {"response": response_text, "raw": response_text}

            return {
                "ai_service": "deepseek",
                "task_type": task_type.value,
                "processed": True,
                "result": result,
            }
        except asyncio.TimeoutError:
            logger.error(f"DeepSeek call timed out after {AI_CALL_TIMEOUT_SECONDS}s")
            return {
                "ai_service": "deepseek",
                "task_type": task_type.value,
                "processed": False,
                "error": "ai_timeout",
                "error_message": f"AI call timed out after {AI_CALL_TIMEOUT_SECONDS} seconds",
            }
        except Exception as e:
            logger.error(f"DeepSeek processing error: {e}")
            return {
                "ai_service": "deepseek",
                "task_type": task_type.value,
                "processed": False,
                "error": "ai_error",
                "error_message": str(e),
            }

    async def _call_claude(
        self, data: Dict[str, Any], task_type: AITaskType
    ) -> Dict[str, Any]:
        """Call Claude service for creative generation tasks"""
        from .llm_ai_engine import llm_ai_engine_service

        engine = llm_ai_engine_service

        prompt = self._build_prompt_for_task(task_type, data)

        try:
            result = await asyncio.wait_for(
                engine.generate_response(prompt, model="claude"),
                timeout=AI_CALL_TIMEOUT_SECONDS
            )

            # Parse JSON from Claude response if possible
            import json
            raw = result.get("response") or result.get("raw", "")
            parsed = raw
            if isinstance(raw, str):
                try:
                    clean = raw.strip()
                    if clean.startswith("```"):
                        clean = clean.split("```")[1]
                        if clean.startswith("json"):
                            clean = clean[4:]
                    parsed = json.loads(clean)
                except (json.JSONDecodeError, IndexError):
                    parsed = raw

            return {
                "ai_service": "claude",
                "task_type": task_type.value,
                "processed": True,
                "result": {"response": parsed, "raw": raw} if isinstance(parsed, dict) else result,
            }
        except asyncio.TimeoutError:
            logger.error(f"Claude call timed out after {AI_CALL_TIMEOUT_SECONDS}s")
            return {
                "ai_service": "claude",
                "task_type": task_type.value,
                "processed": False,
                "error": "ai_timeout",
                "error_message": f"AI call timed out after {AI_CALL_TIMEOUT_SECONDS} seconds",
            }
        except Exception as e:
            logger.error(f"Claude processing error: {e}")
            return {
                "ai_service": "claude",
                "task_type": task_type.value,
                "processed": False,
                "error": "ai_error",
                "error_message": str(e),
            }

    async def _process_hybrid(
        self, data: Dict[str, Any], task_type: AITaskType
    ) -> Dict[str, Any]:
        """Process tasks requiring both DeepSeek and Claude"""
        platform_result = await self._call_deepseek(data, task_type)

        enriched_data = {**data, "platform_insights": platform_result}
        enriched_result = await self._call_claude(enriched_data, task_type)

        return {
            "ai_service": "hybrid",
            "task_type": task_type.value,
            "processed": enriched_result.get("processed", False) or platform_result.get("processed", False),
            "result": enriched_result.get("result", platform_result.get("result", {})),
            "deepseek_phase": platform_result,
            "claude_phase": enriched_result,
        }

    def _build_prompt_for_task(
        self, task_type: AITaskType, data: Dict[str, Any]
    ) -> str:
        """Build structured prompts based on task type"""
        idea = data.get("idea", data.get("idea_description", ""))
        context = data.get("context", {})
        request = data.get("request", "")

        context_str = ""
        if isinstance(context, dict) and context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items() if v)

        if task_type == AITaskType.OPPORTUNITY_VALIDATION:
            return f"""You are a business analyst. Analyze this business idea and return a JSON object.

Business Idea: {idea}
{f"Additional Context:{chr(10)}{context_str}" if context_str else ""}
{f"Specific Request: {request}" if request else ""}

Return a JSON object with these fields:
{{
  "online_score": <0-100 score for online business viability>,
  "physical_score": <0-100 score for physical business viability>,
  "recommendation": "ONLINE" | "PHYSICAL" | "HYBRID",
  "market_signals": {{
    "demand_level": "high" | "medium" | "low",
    "competition_level": "high" | "medium" | "low",
    "growth_trend": "growing" | "stable" | "declining",
    "key_insights": ["insight1", "insight2", "insight3"]
  }},
  "category_distribution": {{
    "Technology": <0.0-1.0>,
    "Local Services": <0.0-1.0>,
    "E-commerce": <0.0-1.0>,
    "Professional Services": <0.0-1.0>
  }}
}}

Return ONLY valid JSON, no markdown formatting."""

        elif task_type == AITaskType.MARKET_RESEARCH:
            return f"""You are a senior business consultant. Provide a comprehensive SWOT viability analysis.

Business Idea: {idea}
{f"Additional Context:{chr(10)}{context_str}" if context_str else ""}
{f"Specific Request: {request}" if request else ""}

Return a JSON object with these fields:
{{
  "summary": "<2-3 sentence executive summary>",
  "strengths": ["strength1", "strength2", "strength3", "strength4"],
  "weaknesses": ["weakness1", "weakness2", "weakness3"],
  "opportunities": ["opportunity1", "opportunity2", "opportunity3"],
  "threats": ["threat1", "threat2", "threat3"],
  "market_size_estimate": "<estimate like '$X billion' or 'Unknown'>",
  "confidence": <60-95 confidence score>,
  "recommendation": "GO" | "NO-GO" | "CONDITIONAL",
  "key_actions": ["action1", "action2", "action3"]
}}

Be specific to the actual business idea. Avoid generic statements.
Return ONLY valid JSON, no markdown formatting."""

        elif task_type == AITaskType.BUSINESS_PLAN_GENERATION:
            return f"""You are a business strategy expert. Create a comprehensive business plan.

Business Idea: {idea}
{f"Additional Context:{chr(10)}{context_str}" if context_str else ""}
{f"Specific Request: {request}" if request else ""}

Provide a detailed, actionable business plan with specific numbers and strategies."""

        elif task_type == AITaskType.IDEA_ANALYSIS:
            return f"""You are an innovation analyst. Analyze this business idea thoroughly.

Business Idea: {idea}
{f"Additional Context:{chr(10)}{context_str}" if context_str else ""}
{f"Specific Request: {request}" if request else ""}

Return a JSON object with:
{{
  "viability_score": <0-100>,
  "innovation_score": <0-100>,
  "market_fit": "strong" | "moderate" | "weak",
  "key_risks": ["risk1", "risk2"],
  "key_advantages": ["advantage1", "advantage2"],
  "suggested_pivots": ["pivot1", "pivot2"],
  "estimated_startup_cost": "<range like '$10K-$50K'>",
  "time_to_market": "<range like '3-6 months'>"
}}

Return ONLY valid JSON, no markdown formatting."""

        elif task_type == AITaskType.LEAD_SCORING:
            return f"""Score this business lead on quality indicators. Return a JSON object with score (0-100) and reasoning.

Lead Data: {data}

Return ONLY valid JSON."""

        else:
            return f"""Process this request as a business intelligence analyst.

{f"Business Idea: {idea}" if idea else ""}
{f"Context:{chr(10)}{context_str}" if context_str else ""}
{f"Request: {request}" if request else f"Data: {data}"}

Provide a thorough, actionable analysis."""


ai_orchestrator = AIOrchestrator()
