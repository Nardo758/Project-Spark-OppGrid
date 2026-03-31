"""
Unified AI Service

Central service for all AI operations in OppGrid.
- Uses dynamic model registry (database-driven)
- Handles all providers (Anthropic, OpenAI, Google, DeepSeek, xAI)
- Tracks usage and billing via Stripe meters
- Enforces tier-based rate limits and model access
- Supports BYOK (Bring Your Own Key)

All AI calls throughout the app should use this service.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache
import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Rate limiting cache
_rate_limit_cache: Dict[str, Dict] = {}


class UnifiedAIService:
    """
    Unified AI service that wraps all AI operations.
    
    Usage:
        ai = UnifiedAIService(db, user_id=123)
        response = await ai.complete(
            prompt="Analyze this opportunity...",
            task_type="opportunity_analysis"
        )
    """
    
    def __init__(
        self,
        db: Session,
        user_id: Optional[int] = None,
        user_tier: str = "free",
        byok_key: Optional[str] = None,
        byok_provider: Optional[str] = None
    ):
        self.db = db
        self.user_id = user_id
        self.user_tier = user_tier
        self.byok_key = byok_key
        self.byok_provider = byok_provider
        
        # Lazy load registry and billing
        self._registry = None
        self._billing = None
    
    @property
    def registry(self):
        """Lazy load model registry."""
        if self._registry is None:
            from app.services.ai_model_registry import AIModelRegistry
            self._registry = AIModelRegistry(self.db)
        return self._registry
    
    @property
    def billing(self):
        """Lazy load billing service."""
        if self._billing is None:
            from app.services.stripe_token_billing import get_token_billing
            self._billing = get_token_billing()
        return self._billing
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: str = "general",
        model_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a completion using the appropriate model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            task_type: Task type for routing (general, reasoning, coding, etc.)
            model_id: Force specific model (optional)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            json_mode: Request JSON output format
            stream: Stream response (not yet implemented)
        
        Returns:
            {
                "content": str,
                "model_id": str,
                "provider": str,
                "tokens": {"input": int, "output": int},
                "cost_usd": float,
                "cached": bool
            }
        """
        # Check rate limits
        if not await self._check_rate_limit():
            raise RateLimitError("Rate limit exceeded. Please try again later.")
        
        # Check token quota
        if not await self._check_token_quota():
            raise QuotaExceededError("Monthly token quota exceeded. Upgrade your plan for more tokens.")
        
        # Select model
        model = await self._select_model(task_type, model_id)
        if not model:
            raise ModelNotFoundError(f"No suitable model found for task: {task_type}")
        
        # Check tier access
        if not self._check_tier_access(model):
            raise TierAccessError(f"Model {model['model_id']} requires {model['min_tier']} tier or higher")
        
        # Execute the call
        try:
            result = await self._execute_call(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode
            )
            
            # Record usage for billing
            await self._record_usage(model, result["tokens"])
            
            # Update rate limit counter
            self._update_rate_limit()
            
            return result
            
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            raise AICallError(f"AI call failed: {str(e)}")
    
    async def _select_model(
        self,
        task_type: str,
        model_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Select the best model for the task."""
        
        # If specific model requested, use it
        if model_id:
            model = self.registry.get_model(model_id)
            if model and model.get("is_enabled"):
                return model
        
        # If BYOK, check if user has a preferred provider
        if self.byok_key and self.byok_provider:
            models = self.registry.get_all_models()
            for m in models:
                if m["provider"] == self.byok_provider and m.get("is_enabled"):
                    return m
        
        # Route by task type
        return self.registry.get_model_for_task(task_type, self.user_tier)
    
    def _check_tier_access(self, model: Dict) -> bool:
        """Check if user tier allows access to model."""
        tier_order = ["free", "starter", "growth", "pro", "enterprise"]
        try:
            user_level = tier_order.index(self.user_tier.lower())
            required_level = tier_order.index((model.get("min_tier") or "free").lower())
            return user_level >= required_level
        except ValueError:
            return True
    
    async def _check_rate_limit(self) -> bool:
        """Check if user is within rate limits."""
        if not self.user_id:
            return True
        
        cache_key = f"rate:{self.user_id}"
        now = datetime.utcnow()
        
        if cache_key in _rate_limit_cache:
            entry = _rate_limit_cache[cache_key]
            if entry["window_start"] > now - timedelta(minutes=1):
                # Get tier limit
                tier_limits = {
                    "free": 10,
                    "starter": 30,
                    "growth": 60,
                    "pro": 120,
                    "enterprise": 300
                }
                limit = tier_limits.get(self.user_tier, 10)
                return entry["count"] < limit
            else:
                # Reset window
                _rate_limit_cache[cache_key] = {"window_start": now, "count": 0}
        else:
            _rate_limit_cache[cache_key] = {"window_start": now, "count": 0}
        
        return True
    
    def _update_rate_limit(self):
        """Increment rate limit counter."""
        if not self.user_id:
            return
        
        cache_key = f"rate:{self.user_id}"
        if cache_key in _rate_limit_cache:
            _rate_limit_cache[cache_key]["count"] += 1
    
    async def _check_token_quota(self) -> bool:
        """Check if user has remaining token quota."""
        if not self.user_id:
            return True
        
        # Enterprise has unlimited
        if self.user_tier == "enterprise":
            return True
        
        # Check from database
        try:
            from sqlalchemy import text
            result = self.db.execute(text("""
                SELECT COALESCE(SUM(total_tokens), 0) as used
                FROM user_ai_usage
                WHERE user_id = :user_id
                AND created_at >= date_trunc('month', CURRENT_DATE)
            """), {"user_id": self.user_id})
            row = result.fetchone()
            used = row[0] if row else 0
            
            # Get tier limit
            tier_limits = {
                "free": 50000,
                "starter": 500000,
                "growth": 2000000,
                "pro": 10000000
            }
            limit = tier_limits.get(self.user_tier, 50000)
            
            return used < limit
            
        except Exception as e:
            logger.error(f"Failed to check token quota: {e}")
            return True  # Allow on error
    
    async def _execute_call(
        self,
        model: Dict,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        json_mode: bool
    ) -> Dict[str, Any]:
        """Execute the actual API call."""
        
        provider = model["provider"]
        
        # Use BYOK if available for this provider
        api_key = None
        if self.byok_key and self.byok_provider == provider:
            api_key = self.byok_key
        
        if provider == "anthropic":
            return await self._call_anthropic(model, prompt, system_prompt, max_tokens, temperature, api_key)
        elif provider == "openai":
            return await self._call_openai(model, prompt, system_prompt, max_tokens, temperature, json_mode, api_key)
        elif provider == "google":
            return await self._call_google(model, prompt, system_prompt, max_tokens, temperature, api_key)
        elif provider == "deepseek":
            return await self._call_deepseek(model, prompt, system_prompt, max_tokens, temperature, api_key)
        elif provider == "xai":
            return await self._call_xai(model, prompt, system_prompt, max_tokens, temperature, api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _call_anthropic(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float, api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API."""
        import anthropic
        
        # Get API key
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
        base_url = os.getenv("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
        
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        
        response = client.messages.create(
            model=model["api_model_name"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            "content": response.content[0].text,
            "model_id": model["model_id"],
            "provider": "anthropic",
            "tokens": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            },
            "cost_usd": self._calculate_cost(model, response.usage.input_tokens, response.usage.output_tokens),
            "cached": getattr(response.usage, "cache_read_input_tokens", 0) > 0
        }
    
    async def _call_openai(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float, json_mode: bool, api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        import openai
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        openai.api_key = api_key
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        model_name = model["api_model_name"]
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        
        # o1/o3 models don't support temperature or system prompts
        if not model_name.startswith(("o1", "o3")):
            kwargs["temperature"] = temperature
        
        if json_mode and not model_name.startswith(("o1", "o3")):
            kwargs["response_format"] = {"type": "json_object"}
        
        response = openai.chat.completions.create(**kwargs)
        
        return {
            "content": response.choices[0].message.content,
            "model_id": model["model_id"],
            "provider": "openai",
            "tokens": {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens
            },
            "cost_usd": self._calculate_cost(model, response.usage.prompt_tokens, response.usage.completion_tokens),
            "cached": False
        }
    
    async def _call_google(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float, api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Call Google Gemini API."""
        import google.generativeai as genai
        
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("Google API key not configured")
        
        genai.configure(api_key=api_key)
        gemini = genai.GenerativeModel(model["api_model_name"])
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = gemini.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        # Estimate tokens
        input_tokens = int(len(prompt.split()) * 1.3)
        output_tokens = int(len(response.text.split()) * 1.3)
        
        return {
            "content": response.text,
            "model_id": model["model_id"],
            "provider": "google",
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost_usd": self._calculate_cost(model, input_tokens, output_tokens),
            "cached": False
        }
    
    async def _call_deepseek(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float, api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Call DeepSeek API."""
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not api_key:
            raise ValueError("DeepSeek API key not configured")
        
        base_url = model.get("api_base_url") or "https://api.deepseek.com/v1"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model["api_model_name"],
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "content": data["choices"][0]["message"]["content"],
            "model_id": model["model_id"],
            "provider": "deepseek",
            "tokens": {
                "input": data["usage"]["prompt_tokens"],
                "output": data["usage"]["completion_tokens"]
            },
            "cost_usd": self._calculate_cost(model, data["usage"]["prompt_tokens"], data["usage"]["completion_tokens"]),
            "cached": False
        }
    
    async def _call_xai(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float, api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Call xAI Grok API."""
        if not api_key:
            api_key = os.getenv("XAI_API_KEY")
        
        if not api_key:
            raise ValueError("xAI API key not configured")
        
        base_url = model.get("api_base_url") or "https://api.x.ai/v1"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model["api_model_name"],
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "content": data["choices"][0]["message"]["content"],
            "model_id": model["model_id"],
            "provider": "xai",
            "tokens": {
                "input": data["usage"]["prompt_tokens"],
                "output": data["usage"]["completion_tokens"]
            },
            "cost_usd": self._calculate_cost(model, data["usage"]["prompt_tokens"], data["usage"]["completion_tokens"]),
            "cached": False
        }
    
    def _calculate_cost(self, model: Dict, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD."""
        input_cost = float(model["cost_per_million_input"]) * input_tokens / 1_000_000
        output_cost = float(model["cost_per_million_output"]) * output_tokens / 1_000_000
        
        # Apply billing markup if set
        markup = float(model.get("billing_markup_percent") or 0) / 100
        total = input_cost + output_cost
        total_with_markup = total * (1 + markup)
        
        return round(total_with_markup, 6)
    
    async def _record_usage(self, model: Dict, tokens: Dict[str, int]):
        """Record usage for billing."""
        if not self.user_id:
            return
        
        try:
            # Record in database
            from sqlalchemy import text
            self.db.execute(text("""
                INSERT INTO user_ai_usage (user_id, model_id, input_tokens, output_tokens, total_tokens, created_at)
                VALUES (:user_id, :model_id, :input_tokens, :output_tokens, :total_tokens, NOW())
            """), {
                "user_id": self.user_id,
                "model_id": model["model_id"],
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "total_tokens": tokens["input"] + tokens["output"]
            })
            self.db.commit()
            
            # Record to Stripe if enabled
            if self.billing and self.billing.enabled:
                self.billing.record_usage_by_user_id(
                    user_id=self.user_id,
                    model=model["api_model_name"],
                    input_tokens=tokens["input"],
                    output_tokens=tokens["output"],
                    db=self.db
                )
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")


# ==================== Exceptions ====================

class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass

class RateLimitError(AIServiceError):
    """Rate limit exceeded."""
    pass

class QuotaExceededError(AIServiceError):
    """Token quota exceeded."""
    pass

class ModelNotFoundError(AIServiceError):
    """Model not found."""
    pass

class TierAccessError(AIServiceError):
    """User tier doesn't allow access to model."""
    pass

class AICallError(AIServiceError):
    """AI API call failed."""
    pass


# ==================== Convenience Functions ====================

def get_ai_service(
    db: Session,
    user_id: Optional[int] = None,
    user: Optional[Any] = None
) -> UnifiedAIService:
    """
    Factory function to create an AI service instance.
    
    Args:
        db: Database session
        user_id: User ID
        user: User object (optional, for getting tier and BYOK)
    
    Returns:
        UnifiedAIService instance
    """
    user_tier = "free"
    byok_key = None
    byok_provider = None
    
    if user:
        user_id = user.id
        
        # Get tier from subscription
        if hasattr(user, "subscription") and user.subscription:
            user_tier = user.subscription.tier or "free"
        
        # Get BYOK if configured
        if hasattr(user, "ai_preferences") and user.ai_preferences:
            prefs = user.ai_preferences
            if prefs.provider == "openai" and prefs.encrypted_openai_api_key:
                byok_key = prefs.get_openai_api_key()
                byok_provider = "openai"
    
    return UnifiedAIService(
        db=db,
        user_id=user_id,
        user_tier=user_tier,
        byok_key=byok_key,
        byok_provider=byok_provider
    )


async def quick_complete(
    db: Session,
    prompt: str,
    system_prompt: Optional[str] = None,
    task_type: str = "general",
    model_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> str:
    """
    Quick completion without user context (for internal/admin use).
    
    Returns just the content string.
    """
    ai = UnifiedAIService(db=db, user_id=user_id, user_tier="enterprise")
    result = await ai.complete(
        prompt=prompt,
        system_prompt=system_prompt,
        task_type=task_type,
        model_id=model_id
    )
    return result["content"]


# Sync wrapper for backwards compatibility
def complete_sync(
    db: Session,
    prompt: str,
    system_prompt: Optional[str] = None,
    task_type: str = "general",
    model_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> str:
    """Synchronous wrapper for quick_complete."""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        quick_complete(db, prompt, system_prompt, task_type, model_id, user_id)
    )
