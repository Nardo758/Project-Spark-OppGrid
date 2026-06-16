"""
Unified AI Pricing Service

Provides a single source of truth for AI model pricing across the platform.
Both ai_metering_service.py and stripe_token_billing.py should import from here.

Priority:
1. Database ai_models table (live pricing from admin panel)
2. Unified static fallback (kept in sync with stripe_token_billing.py)

Usage:
    from app.services.ai_pricing_service import get_model_cost, get_all_model_costs

    cost = get_model_cost(db_session, "gpt-4o")
    # Returns: {"input": 2.5, "output": 10.0, "markup_percent": 50.0}
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Unified fallback pricing (per 1M tokens, USD)
FALLBACK_COSTS = {
    "claude-opus-4-5": {"input": 15.0, "output": 75.0, "markup_percent": 50.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0, "markup_percent": 50.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "markup_percent": 50.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "markup_percent": 50.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "markup_percent": 50.0},
    "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25, "markup_percent": 50.0},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25, "markup_percent": 50.0},
    "gpt-5": {"input": 10.0, "output": 30.0, "markup_percent": 50.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0, "markup_percent": 50.0},
    "gpt-4": {"input": 10.0, "output": 30.0, "markup_percent": 50.0},
    "gpt-4o": {"input": 2.5, "output": 10.0, "markup_percent": 50.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "markup_percent": 50.0},
    "o1": {"input": 15.0, "output": 60.0, "markup_percent": 50.0},
    "o1-mini": {"input": 3.0, "output": 12.0, "markup_percent": 50.0},
    "o3-mini": {"input": 1.1, "output": 4.4, "markup_percent": 50.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5, "markup_percent": 50.0},
    "deepseek-chat": {"input": 0.14, "output": 0.28, "markup_percent": 50.0},
    "deepseek-coder": {"input": 0.14, "output": 0.28, "markup_percent": 50.0},
    "deepseek-reasoner": {"input": 0.14, "output": 0.28, "markup_percent": 50.0},
    "gemini-pro": {"input": 0.5, "output": 1.5, "markup_percent": 50.0},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.0, "markup_percent": 50.0},
    "gemini-2.5-pro-preview-05-06": {"input": 1.25, "output": 5.0, "markup_percent": 50.0},
    "gemini-2.5-flash-preview-05-20": {"input": 0.5, "output": 1.5, "markup_percent": 50.0},
    "gemini_flash": {"input": 0.5, "output": 1.5, "markup_percent": 50.0},
    "grok-2-latest": {"input": 5.0, "output": 15.0, "markup_percent": 50.0},
    "grok-3-latest": {"input": 5.0, "output": 15.0, "markup_percent": 50.0},
    "default": {"input": 3.0, "output": 15.0, "markup_percent": 50.0},
}

MODEL_ALIASES = {
    "claude-opus-4-5": "claude-opus-4-5",
    "claude-3-opus-20240229": "claude-opus-4-5",
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-sonnet-4-20250514": "claude-sonnet-4-5",
    "claude-3-5-sonnet-20241022": "claude-sonnet-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-3-5-haiku-20241022": "claude-haiku-4-5",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o1": "o1",
    "o3-mini": "o3-mini",
    "gpt-4": "gpt-4",
    "gpt-4-turbo": "gpt-4",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "deepseek-chat": "deepseek-chat",
    "deepseek-coder": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    "gemini-pro": "gemini-pro",
    "gemini-1.5-pro": "gemini-1.5-pro",
    "gemini-2.5-pro-preview-05-06": "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash-preview-05-20": "gemini-2.5-flash-preview-05-20",
    "grok-2-latest": "grok-2-latest",
    "grok-3-latest": "grok-3-latest",
}


def _normalize_model_name(model: str) -> str:
    model_lower = model.lower().strip()
    return MODEL_ALIASES.get(model_lower, model_lower)


def get_model_cost(db_session=None, model: str = "default") -> Dict[str, Any]:
    canonical = _normalize_model_name(model)
    if db_session is not None:
        try:
            from sqlalchemy import text
            row = db_session.execute(
                text(
                    "SELECT cost_per_million_input, cost_per_million_output, billing_markup_percent "
                    "FROM ai_models WHERE api_model_name = :m OR model_id = :m LIMIT 1"
                ),
                {"m": canonical}
            ).fetchone()
            if row:
                return {
                    "input": float(row[0]),
                    "output": float(row[1]),
                    "markup_percent": float(row[2] or 0),
                    "source": "db",
                }
        except Exception as e:
            logger.warning(f"[AIPricing] DB lookup failed for {model}: {e}")
    fallback = FALLBACK_COSTS.get(canonical)
    if fallback:
        result = dict(fallback)
        result["source"] = "fallback"
        return result
    logger.warning(f"[AIPricing] Unknown model '{model}', using default pricing")
    return {"input": 3.0, "output": 15.0, "markup_percent": 50.0, "source": "default"}


def get_all_model_costs() -> Dict[str, Dict[str, Any]]:
    return dict(FALLBACK_COSTS)


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
    db_session=None,
    apply_markup: bool = True,
) -> Dict[str, Any]:
    pricing = get_model_cost(db_session, model)
    cost_per_m_input = pricing["input"]
    cost_per_m_output = pricing["output"]
    markup_percent = pricing["markup_percent"]
    input_cost = (input_tokens / 1_000_000) * cost_per_m_input
    output_cost = (output_tokens / 1_000_000) * cost_per_m_output
    base_cost = input_cost + output_cost
    if apply_markup and markup_percent > 0:
        multiplier = 1 + (markup_percent / 100)
        total_cost = base_cost * multiplier
    else:
        total_cost = base_cost
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_per_million_input_usd": cost_per_m_input,
        "cost_per_million_output_usd": cost_per_m_output,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "base_cost_usd": round(base_cost, 6),
        "markup_percent": markup_percent,
        "total_cost_usd": round(total_cost, 6),
        "source": pricing.get("source", "unknown"),
    }
