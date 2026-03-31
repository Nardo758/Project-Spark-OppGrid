"""
User Billing Router

Endpoints for users to view their AI token usage, estimated costs,
and upcoming invoice preview — powered by Stripe Token Billing.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/billing", tags=["Billing"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_stripe_customer_id(user: User, db: Session) -> Optional[str]:
    from app.models.subscription import Subscription
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return sub.stripe_customer_id if sub else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/usage")
def get_my_token_usage(
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the authenticated user's AI token usage for the last N days.

    Returns per-model breakdown with token counts and estimated costs using
    live pricing from the ai_models registry (including any markup).
    """
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()
    since = datetime.utcnow() - timedelta(days=days)

    # Pull usage from our local tracking table
    try:
        rows = db.execute(
            text("""
                SELECT
                    model_name,
                    SUM(input_tokens)  AS input_tokens,
                    SUM(output_tokens) AS output_tokens,
                    COUNT(*)           AS requests
                FROM user_ai_usage
                WHERE user_id = :uid
                  AND created_at >= :since
                GROUP BY model_name
                ORDER BY (SUM(input_tokens) + SUM(output_tokens)) DESC
            """),
            {"uid": current_user.id, "since": since},
        ).fetchall()
    except Exception:
        rows = []

    by_model = []
    total_input = 0
    total_output = 0
    total_cost = 0.0

    for row in rows:
        model_name = row[0]
        inp = int(row[1] or 0)
        out = int(row[2] or 0)
        reqs = int(row[3] or 0)

        cost_info = billing.calculate_estimated_cost(
            model=model_name,
            input_tokens=inp,
            output_tokens=out,
            db=db,
            apply_markup=True,
        )

        by_model.append({
            "model": model_name,
            "requests": reqs,
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": inp + out,
            "estimated_cost_usd": cost_info["total_cost_usd"],
            "markup_percent": cost_info["markup_percent"],
        })
        total_input += inp
        total_output += out
        total_cost += cost_info["total_cost_usd"]

    return {
        "user_id": current_user.id,
        "period_days": days,
        "since": since.isoformat(),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_estimated_cost_usd": round(total_cost, 4),
        "by_model": by_model,
        "stripe_billing_enabled": billing.enabled,
    }


@router.get("/invoice-preview")
def get_invoice_preview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Preview the upcoming Stripe invoice for the current user.

    Shows metered token charges alongside any subscription line items
    before the invoice is finalized at the end of the billing period.
    Returns estimated totals even when no Stripe subscription exists.
    """
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()
    customer_id = _get_stripe_customer_id(current_user, db)

    # Stripe preview (requires active Stripe subscription)
    stripe_preview = None
    if billing.enabled and customer_id:
        stripe_preview = billing.get_invoice_preview(customer_id)

    # Local cost estimate for the current billing period (last 30 days)
    usage_data = get_my_token_usage(days=30, db=db, current_user=current_user)

    return {
        "user_id": current_user.id,
        "has_stripe_customer": customer_id is not None,
        "stripe_invoice_preview": stripe_preview,
        "estimated_token_charges_usd": usage_data["total_estimated_cost_usd"],
        "token_usage_summary": {
            "total_tokens": usage_data["total_tokens"],
            "by_model": usage_data["by_model"],
        },
        "note": (
            "Stripe invoice preview requires an active metered subscription. "
            "Estimated charges are calculated from local usage data."
        ) if not stripe_preview else None,
    }


@router.get("/cost-estimate")
def estimate_cost(
    model: str = Query(..., description="Model name (e.g. claude-opus-4-5)"),
    input_tokens: int = Query(..., ge=0, description="Input token count"),
    output_tokens: int = Query(..., ge=0, description="Output token count"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Calculate the estimated cost for a specific token usage scenario.

    Useful for letting users understand the cost of a particular AI call
    before they trigger it (e.g. report generation, deep analysis).
    """
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()
    return billing.calculate_estimated_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        db=db,
        apply_markup=True,
    )


@router.get("/models/pricing")
def get_model_pricing(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current AI model pricing visible to the user.

    Shows cost per 1M tokens for each available model, with markup applied.
    Useful for displaying pricing tiers and letting users choose models.
    """
    try:
        rows = db.execute(
            text("""
                SELECT
                    model_id,
                    display_name,
                    provider,
                    cost_per_million_input,
                    cost_per_million_output,
                    billing_markup_percent,
                    min_tier,
                    task_types,
                    is_default
                FROM ai_models
                WHERE is_enabled = true
                ORDER BY priority DESC, display_name
            """)
        ).fetchall()
    except Exception as e:
        logger.error(f"[Billing] Failed to fetch model pricing: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch model pricing")

    models = []
    for row in rows:
        markup = float(row[5] or 0)
        base_input = float(row[3])
        base_output = float(row[4])
        multiplier = 1 + (markup / 100)

        models.append({
            "model_id": row[0],
            "display_name": row[1],
            "provider": row[2],
            "cost_per_million_input_usd": round(base_input * multiplier, 4),
            "cost_per_million_output_usd": round(base_output * multiplier, 4),
            "markup_applied": markup > 0,
            "min_tier": row[6],
            "task_types": row[7] or [],
            "is_default": row[8],
        })

    return {"models": models, "count": len(models)}
