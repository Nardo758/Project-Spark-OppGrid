"""
AI Model Registry Service

Dynamic model management - loads models from database instead of hardcoded config.
Supports admin CRUD operations and runtime model selection.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
import httpx
from anthropic import Anthropic
import openai
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIModelRegistry:
    """
    Central registry for AI models.
    Loads configuration from database, handles API calls, tracks costs.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._models_cache: Dict[str, Dict] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Initialize API clients lazily
        self._anthropic_client = None
        self._openai_client = None
    
    @property
    def anthropic(self):
        if self._anthropic_client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
            if api_key:
                self._anthropic_client = Anthropic(api_key=api_key, base_url=base_url)
        return self._anthropic_client
    
    @property
    def openai_client(self):
        if self._openai_client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                openai.api_key = api_key
                self._openai_client = openai
        return self._openai_client
    
    def _should_refresh_cache(self) -> bool:
        if not self._cache_timestamp:
            return True
        elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return elapsed > self._cache_ttl_seconds
    
    def get_all_models(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """Get all models from database."""
        if not self.db:
            return self._get_fallback_models()
        
        try:
            from sqlalchemy import text
            query = "SELECT * FROM ai_models"
            if not include_disabled:
                query += " WHERE is_enabled = true"
            query += " ORDER BY priority DESC, display_name"
            
            result = self.db.execute(text(query))
            rows = result.fetchall()
            
            models = []
            for row in rows:
                models.append(dict(row._mapping))
            
            return models
        except Exception as e:
            logger.error(f"Failed to fetch models from DB: {e}")
            return self._get_fallback_models()
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific model by ID."""
        if self._should_refresh_cache():
            self._refresh_cache()
        
        return self._models_cache.get(model_id)
    
    def get_model_for_task(self, task_type: str, user_tier: str = "free") -> Optional[Dict[str, Any]]:
        """Get the best model for a task type, respecting user tier."""
        models = self.get_all_models()
        
        # Filter by task type and tier
        eligible = []
        for model in models:
            task_types = model.get("task_types") or []
            if task_type in task_types or "general" in task_types:
                # Check tier access
                min_tier = model.get("min_tier", "free")
                if self._tier_allows(user_tier, min_tier):
                    eligible.append(model)
        
        if not eligible:
            # Fallback to default model
            return self.get_default_model()
        
        # Return highest priority
        return max(eligible, key=lambda m: m.get("priority", 0))
    
    def get_default_model(self) -> Optional[Dict[str, Any]]:
        """Get the default model."""
        models = self.get_all_models()
        for model in models:
            if model.get("is_default"):
                return model
        return models[0] if models else None
    
    def _tier_allows(self, user_tier: str, required_tier: str) -> bool:
        """Check if user tier allows access to required tier."""
        tier_order = ["free", "starter", "growth", "pro", "enterprise"]
        try:
            user_level = tier_order.index(user_tier.lower())
            required_level = tier_order.index(required_tier.lower())
            return user_level >= required_level
        except ValueError:
            return True  # Unknown tier = allow
    
    def _refresh_cache(self):
        """Refresh the models cache."""
        models = self.get_all_models()
        self._models_cache = {m["model_id"]: m for m in models}
        self._cache_timestamp = datetime.utcnow()
    
    def _get_fallback_models(self) -> List[Dict[str, Any]]:
        """Hardcoded fallback if database unavailable."""
        return [
            {
                "model_id": "claude-sonnet-4",
                "display_name": "Claude Sonnet 4",
                "provider": "anthropic",
                "api_model_name": "claude-sonnet-4-20250514",
                "cost_per_million_input": Decimal("3.00"),
                "cost_per_million_output": Decimal("15.00"),
                "is_default": True,
                "is_enabled": True,
                "task_types": ["general", "user_conversation"],
                "priority": 80
            },
            {
                "model_id": "gpt-4o",
                "display_name": "GPT-4o",
                "provider": "openai", 
                "api_model_name": "gpt-4o",
                "cost_per_million_input": Decimal("2.50"),
                "cost_per_million_output": Decimal("10.00"),
                "is_enabled": True,
                "task_types": ["general", "vision"],
                "priority": 85
            }
        ]
    
    # ==================== API Execution ====================
    
    async def execute(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute an AI request using the specified model.
        
        Returns:
            {
                "response": str,
                "model_id": str,
                "provider": str,
                "tokens": {"input": int, "output": int},
                "cost_usd": float
            }
        """
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        if not model.get("is_enabled"):
            raise ValueError(f"Model {model_id} is disabled")
        
        provider = model["provider"]
        
        if provider == "anthropic":
            return await self._execute_anthropic(model, prompt, system_prompt, max_tokens, temperature)
        elif provider == "openai":
            return await self._execute_openai(model, prompt, system_prompt, max_tokens, temperature)
        elif provider == "google":
            return await self._execute_google(model, prompt, system_prompt, max_tokens, temperature)
        elif provider == "deepseek":
            return await self._execute_deepseek(model, prompt, system_prompt, max_tokens, temperature)
        elif provider == "xai":
            return await self._execute_xai(model, prompt, system_prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Provider {provider} not supported")
    
    async def _execute_anthropic(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Execute Anthropic Claude request."""
        if not self.anthropic:
            raise ValueError("Anthropic client not configured")
        
        response = self.anthropic.messages.create(
            model=model["api_model_name"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        
        tokens = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
        
        cost = self._calculate_cost(model, tokens)
        
        return {
            "response": response.content[0].text,
            "model_id": model["model_id"],
            "provider": "anthropic",
            "tokens": tokens,
            "cost_usd": cost
        }
    
    async def _execute_openai(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Execute OpenAI request."""
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Handle o1/o3 models (no system prompt, no temperature)
        model_name = model["api_model_name"]
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        
        if not model_name.startswith(("o1", "o3")):
            kwargs["temperature"] = temperature
        
        response = self.openai_client.chat.completions.create(**kwargs)
        
        tokens = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens
        }
        
        cost = self._calculate_cost(model, tokens)
        
        return {
            "response": response.choices[0].message.content,
            "model_id": model["model_id"],
            "provider": "openai",
            "tokens": tokens,
            "cost_usd": cost
        }
    
    async def _execute_google(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Execute Google Gemini request."""
        api_key = os.environ.get("GOOGLE_API_KEY")
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
        
        # Estimate tokens (Gemini doesn't always provide exact counts)
        tokens = {
            "input": int(len(prompt.split()) * 1.3),
            "output": int(len(response.text.split()) * 1.3)
        }
        
        cost = self._calculate_cost(model, tokens)
        
        return {
            "response": response.text,
            "model_id": model["model_id"],
            "provider": "google",
            "tokens": tokens,
            "cost_usd": cost
        }
    
    async def _execute_deepseek(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Execute DeepSeek request (OpenAI-compatible API)."""
        api_key = os.environ.get("DEEPSEEK_API_KEY")
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
        
        tokens = {
            "input": data["usage"]["prompt_tokens"],
            "output": data["usage"]["completion_tokens"]
        }
        
        cost = self._calculate_cost(model, tokens)
        
        return {
            "response": data["choices"][0]["message"]["content"],
            "model_id": model["model_id"],
            "provider": "deepseek",
            "tokens": tokens,
            "cost_usd": cost
        }
    
    async def _execute_xai(
        self, model: Dict, prompt: str, system_prompt: Optional[str],
        max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Execute xAI Grok request (OpenAI-compatible API)."""
        api_key = os.environ.get("XAI_API_KEY")
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
        
        tokens = {
            "input": data["usage"]["prompt_tokens"],
            "output": data["usage"]["completion_tokens"]
        }
        
        cost = self._calculate_cost(model, tokens)
        
        return {
            "response": data["choices"][0]["message"]["content"],
            "model_id": model["model_id"],
            "provider": "xai",
            "tokens": tokens,
            "cost_usd": cost
        }
    
    def _calculate_cost(self, model: Dict, tokens: Dict[str, int]) -> float:
        """Calculate cost in USD."""
        input_cost = float(model["cost_per_million_input"]) * tokens["input"] / 1_000_000
        output_cost = float(model["cost_per_million_output"]) * tokens["output"] / 1_000_000
        return round(input_cost + output_cost, 6)


# ==================== CRUD Operations ====================

def create_model(db, model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new AI model."""
    from sqlalchemy import text
    
    columns = ", ".join(model_data.keys())
    placeholders = ", ".join(f":{k}" for k in model_data.keys())
    
    query = text(f"""
        INSERT INTO ai_models ({columns})
        VALUES ({placeholders})
        RETURNING *
    """)
    
    result = db.execute(query, model_data)
    db.commit()
    return dict(result.fetchone()._mapping)


def update_model(db, model_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing model."""
    from sqlalchemy import text
    
    set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
    updates["model_id"] = model_id
    
    query = text(f"""
        UPDATE ai_models
        SET {set_clause}, updated_at = NOW()
        WHERE model_id = :model_id
        RETURNING *
    """)
    
    result = db.execute(query, updates)
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None


def delete_model(db, model_id: str) -> bool:
    """Delete a model."""
    from sqlalchemy import text
    
    query = text("DELETE FROM ai_models WHERE model_id = :model_id")
    result = db.execute(query, {"model_id": model_id})
    db.commit()
    return result.rowcount > 0


def toggle_model(db, model_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
    """Enable/disable a model."""
    return update_model(db, model_id, {"is_enabled": enabled})


def set_default_model(db, model_id: str) -> Optional[Dict[str, Any]]:
    """Set a model as the default."""
    from sqlalchemy import text
    
    # Clear existing default
    db.execute(text("UPDATE ai_models SET is_default = false WHERE is_default = true"))
    
    # Set new default
    return update_model(db, model_id, {"is_default": True})


# ==================== Stripe Integration ====================

def sync_model_meters(db) -> Dict[str, Any]:
    """Create Stripe meters for models that don't have them."""
    from app.services.stripe_token_billing import get_token_billing
    
    billing = get_token_billing()
    if not billing.enabled:
        return {"error": "Stripe token billing not enabled"}
    
    registry = AIModelRegistry(db)
    models = registry.get_all_models(include_disabled=True)
    
    results = []
    for model in models:
        meter_name = model.get("stripe_meter_event_name")
        if not meter_name:
            continue
        
        # Check if meter exists
        existing_meters = billing.list_meters()
        meter_exists = any(m["event_name"] == meter_name for m in existing_meters)
        
        if not meter_exists:
            # Create meter
            result = billing.create_meter(
                display_name=f"{model['display_name']} Tokens",
                event_name=meter_name
            )
            results.append({
                "model_id": model["model_id"],
                "meter_name": meter_name,
                "created": result is not None
            })
        else:
            results.append({
                "model_id": model["model_id"],
                "meter_name": meter_name,
                "created": False,
                "exists": True
            })
    
    return {
        "synced": len([r for r in results if r.get("created")]),
        "existing": len([r for r in results if r.get("exists")]),
        "details": results
    }
