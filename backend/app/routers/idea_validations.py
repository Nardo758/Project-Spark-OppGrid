"""
Idea Validation Product API

Creates persisted validation records, ties them to Stripe payments, and stores results.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.idea_validation import IdeaValidation, IdeaValidationStatus
from app.models.user import User
from app.schemas.idea_validation import (
    IdeaValidationCreatePaymentIntentRequest,
    IdeaValidationCreatePaymentIntentResponse,
    IdeaValidationDetail,
    IdeaValidationItem,
    IdeaValidationList,
    IdeaValidationRunRequest,
)
from app.services.stripe_service import get_stripe_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/my", response_model=IdeaValidationList)
def list_my_validations(
    skip: int = 0,
    limit: int = 25,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    q = db.query(IdeaValidation).filter(IdeaValidation.user_id == current_user.id)
    total = q.count()
    items = q.order_by(IdeaValidation.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.get("/{idea_validation_id}", response_model=IdeaValidationDetail)
def get_validation(
    idea_validation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = db.query(IdeaValidation).filter(IdeaValidation.id == idea_validation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Validation not found")
    if row.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = None
    if row.result_json:
        try:
            result = json.loads(row.result_json)
        except Exception:
            result = None

    payload = {
        **row.__dict__,
        "result": result,
    }
    # Remove SQLAlchemy internal state if present
    payload.pop("_sa_instance_state", None)
    return payload


@router.post("/create-payment-intent", response_model=IdeaValidationCreatePaymentIntentResponse)
def create_validation_payment_intent(
    req: IdeaValidationCreatePaymentIntentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not req.idea or len(req.idea.strip()) < 10:
        raise HTTPException(status_code=400, detail="Idea is too short")
    if not req.title or len(req.title.strip()) < 3:
        raise HTTPException(status_code=400, detail="Title is required")
    if not req.category or len(req.category.strip()) < 2:
        raise HTTPException(status_code=400, detail="Category is required")
    if req.amount_cents < 50:
        raise HTTPException(status_code=400, detail="amount_cents must be >= 50")

    # Create a persisted validation record first
    row = IdeaValidation(
        user_id=current_user.id,
        idea=req.idea.strip(),
        title=req.title.strip()[:255],
        category=req.category.strip()[:100],
        amount_cents=req.amount_cents,
        currency="usd",
        status=IdeaValidationStatus.PENDING_PAYMENT,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    try:
        stripe = get_stripe_client()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")

    intent = stripe.PaymentIntent.create(
        amount=req.amount_cents,
        currency="usd",
        metadata={
            # New canonical metadata
            "type": "idea_validation",
            "service": "idea_validation",
            "user_id": str(current_user.id),
            "idea_validation_id": str(row.id),
            "product": "OppGrid Idea Validation",
        },
        automatic_payment_methods={"enabled": True},
    )

    row.stripe_payment_intent_id = intent.id
    db.commit()

    return {
        "idea_validation_id": row.id,
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id,
        "amount_cents": req.amount_cents,
        "currency": "usd",
    }


@router.post("/{idea_validation_id}/run", response_model=IdeaValidationDetail)
async def run_validation(
    idea_validation_id: int,
    req: IdeaValidationRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = db.query(IdeaValidation).filter(IdeaValidation.id == idea_validation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Validation not found")
    if row.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not row.stripe_payment_intent_id or row.stripe_payment_intent_id != req.payment_intent_id:
        raise HTTPException(status_code=400, detail="Payment intent does not match this validation")

    # Verify payment intent status (defense in depth; webhook can also mark PAID)
    try:
        stripe = get_stripe_client()
        pi = stripe.PaymentIntent.retrieve(req.payment_intent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payment intent: {str(e)}")

    if pi.status != "succeeded":
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=f"Payment not completed. Status: {pi.status}")
    if (pi.metadata or {}).get("service") != "idea_validation":
        raise HTTPException(status_code=400, detail="Invalid payment intent for idea validation")

    if row.status == IdeaValidationStatus.COMPLETED and row.result_json:
        # Idempotent return
        return get_validation(idea_validation_id, current_user=current_user, db=db)

    # Ensure payment fields/status are up to date even if webhook hasn't run yet.
    if row.status == IdeaValidationStatus.PENDING_PAYMENT:
        row.status = IdeaValidationStatus.PAID
    if not row.amount_cents:
        row.amount_cents = pi.get("amount")
    if not row.currency:
        row.currency = pi.get("currency", "usd")
    db.commit()

    row.status = IdeaValidationStatus.PROCESSING
    db.commit()

    # Reuse the existing idea_engine validation logic/prompt by importing + calling it.
    from app.routers.idea_engine import VALIDATION_PROMPT, client as anthropic_client

    user_prompt = f"""Validate this business opportunity:

TITLE: {row.title}
CATEGORY: {row.category}

IDEA DESCRIPTION:
{row.idea}

Provide a comprehensive, actionable validation analysis."""

    try:
        response = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=VALIDATION_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = response.content[0].text
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx == -1 or end_idx <= start_idx:
            raise RuntimeError("Failed to parse validation response")

        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)

        # Persist
        row.result_json = json.dumps(result)
        row.opportunity_score = int(result.get("opportunity_score", 0) or 0)
        row.summary = str(result.get("summary", "") or "")[:255]
        row.market_size_estimate = str(result.get("market_size_estimate", "") or "")[:100]
        row.competition_level = str(result.get("competition_level", "") or "")[:50]
        row.urgency_level = str(result.get("urgency_level", "") or "")[:50]
        row.validation_confidence = int(result.get("validation_confidence", 0) or 0)
        row.status = IdeaValidationStatus.COMPLETED
        row.error_message = None
        db.commit()

        return get_validation(idea_validation_id, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Idea validation failed: {e}")
        row.status = IdeaValidationStatus.FAILED
        row.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail="Validation failed")

