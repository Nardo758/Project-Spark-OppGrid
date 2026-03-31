"""
Cached AI Service - Anthropic Prompt Caching for Cost Reduction

Uses Anthropic's prompt caching to reduce costs by up to 90% on repeated
system prompts. Cache is maintained server-side by Anthropic for 5 minutes.

Strategy:
- Opus for critical content (problem statement, risks, market sizing)
- Sonnet for supporting content (with caching)
- Haiku for lightweight tasks

Cost comparison (per 1M tokens):
- Opus: $15 input / $75 output
- Opus Cached: $1.50 input (90% off)
- Sonnet: $3 input / $15 output
- Sonnet Cached: $0.30 input (90% off)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Initialize client
_client: Optional[Anthropic] = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(
            base_url=os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL"),
            api_key=os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
        )
    return _client


# =============================================================================
# SYSTEM PROMPTS (Cached)
# =============================================================================

OPPORTUNITY_ANALYSIS_PROMPT = """You are a market research analyst for OppGrid, a platform that identifies business opportunities from real consumer pain points.

Analyze the given raw data and provide a structured assessment. Your job is to:
1. Define a clear, compelling IDEA title (what solution could address this pain)
2. Write a professional PROBLEM STATEMENT describing the core issue
3. Provide market analysis and scoring

Respond in valid JSON format only with the following structure:
{
    "idea_title": "<clear, compelling idea name, max 80 chars - describe the solution concept>",
    "problem_statement": "<2-3 sentence professional problem statement explaining the pain point and why it matters>",
    "opportunity_score": <int 0-100, higher = better opportunity>,
    "summary": "<one line, max 100 chars, compelling insight for the opportunity>",
    "market_size_estimate": "<range like $50M-$200M, $1B-$5B based on the problem scope>",
    "competition_level": "<low|medium|high>",
    "urgency_level": "<low|medium|high|critical>",
    "target_audience": "<primary demographic, max 100 chars>",
    "pain_intensity": <int 1-10, how painful is this problem>,
    "business_model_suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"],
    "competitive_advantages": ["<advantage 1>", "<advantage 2>"],
    "key_risks": ["<risk 1>", "<risk 2>"],
    "next_steps": ["<action 1>", "<action 2>", "<action 3>"]
}

Scoring guidelines:
- 80-100: Exceptional opportunity - clear pain, large market, low competition
- 60-79: Strong opportunity - validated pain, good market potential
- 40-59: Moderate opportunity - some validation, competitive market
- 20-39: Weak opportunity - unclear pain or saturated market
- 0-19: Poor opportunity - no clear pain or very niche

Consider:
- Validation signals (upvotes/engagement indicate real pain)
- Market size (who else has this problem?)
- Competition (existing solutions and their gaps)
- Timing (is this problem growing or shrinking?)
- Feasibility (can a startup solve this?)"""


VALIDATION_ANALYSIS_PROMPT = """You are a validation analyst for OppGrid. Analyze user validations of business opportunities and provide insights.

For each validation, assess:
1. Validation quality (is this a real pain point confirmation?)
2. Additional context provided
3. Strength of the signal

Respond in valid JSON format:
{
    "validation_quality": "<high|medium|low>",
    "signal_strength": <int 1-10>,
    "key_insight": "<one sentence insight from this validation>",
    "suggested_follow_up": "<what should be explored next>"
}"""


QUICK_ACTION_PROMPT = """You are a strategic advisor for OppGrid, helping entrepreneurs take action on business opportunities.

Provide actionable, specific guidance. Be concise but thorough. Focus on practical next steps that can be executed immediately.

Always respond in valid JSON format as specified in the user prompt."""


CHAT_SYSTEM_PROMPT = """You are OppGrid's AI research assistant, helping entrepreneurs discover and validate business opportunities.

You have access to:
- Real-time opportunity data from validated consumer pain points
- Market intelligence and competitive analysis
- Trend data and growth indicators

Be helpful, specific, and actionable. When discussing opportunities, reference real data when available. Help users understand market dynamics and make informed decisions.

Keep responses concise but valuable. Use bullet points for lists. Highlight key insights."""


# =============================================================================
# CACHED API CALLS
# =============================================================================

def call_with_cache(
    prompt: str,
    system_prompt: str,
    model: str = "claude-opus-4-5",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    user_id: Optional[int] = None,
    db = None,
    event_type: Optional[str] = None
) -> Optional[str]:
    """
    Make an API call with prompt caching enabled.
    
    The system prompt is cached server-side for 5 minutes, reducing costs
    by up to 90% on subsequent calls with the same system prompt.
    
    If user_id and db are provided, usage is recorded to Stripe Token Billing.
    """
    client = get_client()
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Log cache stats and record usage
        if hasattr(response, 'usage'):
            usage = response.usage

            # Record to Stripe Token Billing if user context provided
            if user_id and db:
                try:
                    from app.services.stripe_token_billing import record_token_usage
                    record_token_usage(
                        user_id=user_id,
                        model=model,
                        input_tokens=getattr(usage, 'input_tokens', 0),
                        output_tokens=getattr(usage, 'output_tokens', 0),
                        db=db,
                        event_type=event_type
                    )
                except Exception as e:
                    logger.warning(f"[CachedAI] Failed to record token usage: {e}")
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            cache_create = getattr(usage, 'cache_creation_input_tokens', 0)
            if cache_read > 0:
                logger.info(f"[CachedAI] Cache HIT: {cache_read} tokens read from cache")
            elif cache_create > 0:
                logger.info(f"[CachedAI] Cache MISS: {cache_create} tokens cached for next call")
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"[CachedAI] Error: {e}")
        return None


def parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from API response."""
    if not response:
        return None
    
    try:
        # Find JSON in response
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"[CachedAI] JSON parse error: {e}")
    
    return None


# =============================================================================
# HIGH-LEVEL API FUNCTIONS
# =============================================================================

def analyze_opportunity(
    title: str,
    description: str,
    category: str,
    subcategory: Optional[str] = None,
    validation_count: int = 0,
    severity: int = 3,
    geographic_scope: str = "national"
) -> Optional[Dict[str, Any]]:
    """
    Analyze an opportunity using Opus with prompt caching.
    
    Returns structured analysis with problem statement, scores, risks, etc.
    """
    prompt = f"""Analyze this opportunity:

TITLE: {title}

DESCRIPTION: {description[:2000] if description else 'No description'}

CATEGORY: {category}
SUBCATEGORY/SOURCE: {subcategory or 'N/A'}
VALIDATION COUNT (upvotes): {validation_count}
SEVERITY RATING: {severity}/5
GEOGRAPHIC SCOPE: {geographic_scope}

Provide your structured JSON analysis."""

    response = call_with_cache(
        prompt=prompt,
        system_prompt=OPPORTUNITY_ANALYSIS_PROMPT,
        model="claude-opus-4-5",
        max_tokens=1024
    )
    
    return parse_json_response(response)


def analyze_validation(
    opportunity_title: str,
    validation_text: str,
    validator_context: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze a user validation using Sonnet with prompt caching.
    """
    prompt = f"""Analyze this validation:

OPPORTUNITY: {opportunity_title}

VALIDATION TEXT: {validation_text}

VALIDATOR CONTEXT: {validator_context or 'Not provided'}

Provide your structured JSON analysis."""

    response = call_with_cache(
        prompt=prompt,
        system_prompt=VALIDATION_ANALYSIS_PROMPT,
        model="claude-sonnet-4-5",  # Sonnet for validations (cheaper)
        max_tokens=512
    )
    
    return parse_json_response(response)


def quick_action(
    action_type: str,
    context: Dict[str, Any],
    output_format: str
) -> Optional[Dict[str, Any]]:
    """
    Execute a quick action using Opus with prompt caching.
    """
    prompt = f"""Action: {action_type}

Context:
{json.dumps(context, indent=2)}

Respond in this JSON format:
{output_format}"""

    response = call_with_cache(
        prompt=prompt,
        system_prompt=QUICK_ACTION_PROMPT,
        model="claude-opus-4-5",
        max_tokens=1024
    )
    
    return parse_json_response(response)


def chat_response(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    opportunity_context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Generate a chat response using Opus with prompt caching.
    """
    context_str = ""
    if opportunity_context:
        context_str = f"\n\nCurrent opportunity context:\n{json.dumps(opportunity_context, indent=2)}"
    
    prompt = f"{user_message}{context_str}"
    
    return call_with_cache(
        prompt=prompt,
        system_prompt=CHAT_SYSTEM_PROMPT,
        model="claude-opus-4-5",
        max_tokens=2048
    )


# =============================================================================
# SELECTIVE MODEL ROUTING
# =============================================================================

class ModelRouter:
    """
    Routes requests to optimal model based on task complexity.
    
    - Critical content (problem statement, risks) → Opus
    - Supporting content (descriptions, tags) → Sonnet  
    - Lightweight tasks (classification, extraction) → Haiku
    """
    
    OPUS_TASKS = {
        'problem_statement',
        'key_risks',
        'market_sizing',
        'competitive_analysis',
        'opportunity_analysis',
        'strategic_advice'
    }
    
    SONNET_TASKS = {
        'validation_analysis',
        'summary_generation',
        'category_suggestion',
        'similar_opportunities'
    }
    
    HAIKU_TASKS = {
        'classification',
        'entity_extraction',
        'sentiment_analysis',
        'keyword_extraction'
    }
    
    @classmethod
    def get_model(cls, task: str) -> str:
        """Get optimal model for task."""
        if task in cls.OPUS_TASKS:
            return "claude-opus-4-5"
        elif task in cls.SONNET_TASKS:
            return "claude-sonnet-4-5"
        elif task in cls.HAIKU_TASKS:
            return "claude-haiku-4-5"
        else:
            # Default to Sonnet for unknown tasks
            return "claude-sonnet-4-5"
    
    @classmethod
    def execute(
        cls,
        task: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """Execute task with optimal model."""
        model = cls.get_model(task)
        logger.info(f"[ModelRouter] Task '{task}' → {model}")
        
        return call_with_cache(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens
        )
