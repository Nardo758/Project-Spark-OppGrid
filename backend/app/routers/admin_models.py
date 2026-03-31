"""
Admin Model Management Routes

Endpoints for managing AI models from the admin panel:
- List all models
- Create/update/delete models
- Enable/disable models
- Set default model
- Manage pricing tiers
- Sync Stripe meters
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date

from app.db.database import get_db
from app.core.dependencies import get_current_admin_user
from app.services.ai_model_registry import (
    AIModelRegistry,
    create_model,
    update_model,
    delete_model,
    toggle_model,
    set_default_model,
    sync_model_meters
)
from app.services.stripe_token_billing import get_token_billing

router = APIRouter(prefix="/api/v1/admin/models", tags=["Admin - AI Models"])


# ==================== Pydantic Models ====================

class ModelCreate(BaseModel):
    model_id: str = Field(..., description="Unique model identifier (e.g., 'gpt-4o')")
    display_name: str = Field(..., description="Human-readable name")
    provider: str = Field(..., description="Provider: openai, anthropic, google, deepseek, xai")
    api_model_name: str = Field(..., description="Actual API model name")
    api_base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    
    max_tokens: int = 4096
    supports_system_prompt: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True
    context_window: int = 128000
    
    cost_per_million_input: Decimal = Field(..., description="Cost per 1M input tokens (USD)")
    cost_per_million_output: Decimal = Field(..., description="Cost per 1M output tokens (USD)")
    
    stripe_meter_event_name: Optional[str] = None
    billing_markup_percent: Decimal = Decimal("0")
    
    task_types: List[str] = ["general"]
    priority: int = 50
    min_tier: str = "free"
    
    is_enabled: bool = True
    description: Optional[str] = None


class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    api_model_name: Optional[str] = None
    api_base_url: Optional[str] = None
    
    max_tokens: Optional[int] = None
    supports_vision: Optional[bool] = None
    supports_function_calling: Optional[bool] = None
    context_window: Optional[int] = None
    
    cost_per_million_input: Optional[Decimal] = None
    cost_per_million_output: Optional[Decimal] = None
    
    billing_markup_percent: Optional[Decimal] = None
    
    task_types: Optional[List[str]] = None
    priority: Optional[int] = None
    min_tier: Optional[str] = None
    
    is_enabled: Optional[bool] = None
    description: Optional[str] = None


class PricingTierCreate(BaseModel):
    tier_name: str
    display_name: str
    monthly_token_limit: Optional[int] = None
    daily_token_limit: Optional[int] = None
    requests_per_minute: int = 60
    markup_percent: Decimal = Decimal("0")
    allowed_models: Optional[List[str]] = None


class PricingTierUpdate(BaseModel):
    display_name: Optional[str] = None
    monthly_token_limit: Optional[int] = None
    daily_token_limit: Optional[int] = None
    requests_per_minute: Optional[int] = None
    markup_percent: Optional[Decimal] = None
    allowed_models: Optional[List[str]] = None


# ==================== Model Routes ====================

@router.get("")
async def list_models(
    include_disabled: bool = Query(False, description="Include disabled models"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """List all AI models."""
    registry = AIModelRegistry(db)
    models = registry.get_all_models(include_disabled=include_disabled)
    
    if provider:
        models = [m for m in models if m["provider"] == provider]
    
    return {
        "models": models,
        "total": len(models),
        "providers": list(set(m["provider"] for m in models))
    }


@router.get("/providers")
async def list_providers(
    _: dict = Depends(get_current_admin_user)
):
    """List supported AI providers."""
    return {
        "providers": [
            {
                "id": "anthropic",
                "name": "Anthropic",
                "api_key_env": "ANTHROPIC_API_KEY",
                "docs": "https://docs.anthropic.com"
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "api_key_env": "OPENAI_API_KEY",
                "docs": "https://platform.openai.com/docs"
            },
            {
                "id": "google",
                "name": "Google AI",
                "api_key_env": "GOOGLE_API_KEY",
                "docs": "https://ai.google.dev/docs"
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "api_key_env": "DEEPSEEK_API_KEY",
                "api_base": "https://api.deepseek.com/v1",
                "docs": "https://platform.deepseek.com/docs"
            },
            {
                "id": "xai",
                "name": "xAI (Grok)",
                "api_key_env": "XAI_API_KEY",
                "api_base": "https://api.x.ai/v1",
                "docs": "https://docs.x.ai"
            }
        ]
    }


@router.get("/{model_id}")
async def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Get a specific model."""
    registry = AIModelRegistry(db)
    model = registry.get_model(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return model


@router.post("")
async def create_model_endpoint(
    model: ModelCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Create a new AI model."""
    try:
        model_data = model.dict(exclude_none=True)
        result = create_model(db, model_data)
        return {"success": True, "model": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{model_id}")
async def update_model_endpoint(
    model_id: str,
    updates: ModelUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Update an existing model."""
    update_data = updates.dict(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = update_model(db, model_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {"success": True, "model": result}


@router.delete("/{model_id}")
async def delete_model_endpoint(
    model_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a model."""
    success = delete_model(db, model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {"success": True, "deleted": model_id}


@router.post("/{model_id}/toggle")
async def toggle_model_endpoint(
    model_id: str,
    enabled: bool = Query(..., description="Enable or disable the model"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Enable or disable a model."""
    result = toggle_model(db, model_id, enabled)
    if not result:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {"success": True, "model_id": model_id, "enabled": enabled}


@router.post("/{model_id}/set-default")
async def set_default_endpoint(
    model_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Set a model as the default."""
    result = set_default_model(db, model_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {"success": True, "default_model": model_id}


@router.post("/{model_id}/test")
async def test_model_endpoint(
    model_id: str,
    prompt: str = Query("Say hello in one sentence.", description="Test prompt"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Test a model with a simple prompt."""
    registry = AIModelRegistry(db)
    model = registry.get_model(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    try:
        result = await registry.execute(
            model_id=model_id,
            prompt=prompt,
            max_tokens=100
        )
        return {
            "success": True,
            "response": result["response"],
            "tokens": result["tokens"],
            "cost_usd": result["cost_usd"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ==================== Pricing Tier Routes ====================

@router.get("/tiers/list")
async def list_tiers(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """List all pricing tiers."""
    result = db.execute(text("SELECT * FROM ai_pricing_tiers ORDER BY monthly_token_limit NULLS LAST"))
    tiers = [dict(row._mapping) for row in result.fetchall()]
    return {"tiers": tiers}


@router.post("/tiers")
async def create_tier(
    tier: PricingTierCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Create a new pricing tier."""
    try:
        result = db.execute(
            text("""
                INSERT INTO ai_pricing_tiers 
                (tier_name, display_name, monthly_token_limit, daily_token_limit, 
                 requests_per_minute, markup_percent, allowed_models)
                VALUES (:tier_name, :display_name, :monthly_token_limit, :daily_token_limit,
                        :requests_per_minute, :markup_percent, :allowed_models)
                RETURNING *
            """),
            tier.dict()
        )
        db.commit()
        return {"success": True, "tier": dict(result.fetchone()._mapping)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tiers/{tier_name}")
async def update_tier(
    tier_name: str,
    updates: PricingTierUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Update a pricing tier."""
    update_data = updates.dict(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    set_clause = ", ".join(f"{k} = :{k}" for k in update_data.keys())
    update_data["tier_name"] = tier_name
    
    result = db.execute(
        text(f"""
            UPDATE ai_pricing_tiers
            SET {set_clause}
            WHERE tier_name = :tier_name
            RETURNING *
        """),
        update_data
    )
    db.commit()
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Tier {tier_name} not found")
    
    return {"success": True, "tier": dict(row._mapping)}


@router.delete("/tiers/{tier_name}")
async def delete_tier(
    tier_name: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a pricing tier."""
    if tier_name in ["free", "enterprise"]:
        raise HTTPException(status_code=400, detail="Cannot delete system tiers")
    
    result = db.execute(
        text("DELETE FROM ai_pricing_tiers WHERE tier_name = :tier_name"),
        {"tier_name": tier_name}
    )
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Tier {tier_name} not found")
    
    return {"success": True, "deleted": tier_name}


# ==================== Stripe Integration Routes ====================

@router.get("/stripe/meters")
async def list_stripe_meters(
    _: dict = Depends(get_current_admin_user)
):
    """List all Stripe billing meters."""
    billing = get_token_billing()
    if not billing.enabled:
        return {"error": "Stripe token billing not enabled", "meters": []}
    
    meters = billing.list_meters()
    return {"meters": meters}


@router.post("/stripe/sync-meters")
async def sync_stripe_meters(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Create missing Stripe meters for all models."""
    result = sync_model_meters(db)
    return result


@router.post("/stripe/create-meter")
async def create_stripe_meter(
    display_name: str = Query(..., description="Meter display name"),
    event_name: str = Query(..., description="Meter event name"),
    _: dict = Depends(get_current_admin_user)
):
    """Manually create a Stripe meter."""
    billing = get_token_billing()
    if not billing.enabled:
        raise HTTPException(status_code=400, detail="Stripe token billing not enabled")
    
    result = billing.create_meter(display_name, event_name)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create meter")
    
    return {"success": True, "meter": result}


# ==================== Stats Routes ====================

@router.get("/stats/usage")
async def get_usage_stats(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Get AI usage statistics."""
    # This would query your usage tracking table
    # For now, return structure
    return {
        "period_days": days,
        "total_requests": 0,
        "total_tokens": {"input": 0, "output": 0},
        "total_cost_usd": 0,
        "by_model": {},
        "by_tier": {}
    }


@router.get("/stats/cost-estimate")
async def estimate_costs(
    requests_per_day: int = Query(1000, description="Expected requests per day"),
    avg_input_tokens: int = Query(500, description="Average input tokens per request"),
    avg_output_tokens: int = Query(1000, description="Average output tokens per request"),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin_user)
):
    """Estimate monthly costs for AI usage."""
    registry = AIModelRegistry(db)
    models = registry.get_all_models()
    
    estimates = []
    for model in models:
        daily_cost = (
            float(model["cost_per_million_input"]) * avg_input_tokens * requests_per_day / 1_000_000 +
            float(model["cost_per_million_output"]) * avg_output_tokens * requests_per_day / 1_000_000
        )
        monthly_cost = daily_cost * 30
        
        estimates.append({
            "model_id": model["model_id"],
            "display_name": model["display_name"],
            "daily_cost_usd": round(daily_cost, 2),
            "monthly_cost_usd": round(monthly_cost, 2)
        })
    
    estimates.sort(key=lambda x: x["monthly_cost_usd"])
    
    return {
        "assumptions": {
            "requests_per_day": requests_per_day,
            "avg_input_tokens": avg_input_tokens,
            "avg_output_tokens": avg_output_tokens
        },
        "estimates": estimates
    }
