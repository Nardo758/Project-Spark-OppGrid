"""
Subscriptions Router

Endpoints for managing subscriptions, billing, and usage
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
import csv
import io
import json
import logging
import os
import stripe

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.subscription import SubscriptionTier, SubscriptionStatus
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionLimits,
    UsageStats,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PortalSessionCreate,
    PortalSessionResponse,
    SubscriptionIntentCreate,
    SubscriptionIntentResponse,
    UnlockOpportunityRequest,
    UnlockOpportunityResponse,
    ExportRequest,
    BillingInfo,
    PayPerUnlockRequest,
    PayPerUnlockResponse,
    OpportunityAccessInfo
)
from datetime import datetime, timedelta
from app.core.dependencies import get_current_active_user
from app.services.stripe_service import stripe_service
from app.services.stripe_service import get_stripe_client
from app.services.usage_service import usage_service
from app.core.config import settings
from app.services.entitlements import get_opportunity_entitlements
from app.services.audit import log_event

router = APIRouter()


@router.get("/stripe-key")
def get_stripe_publishable_key():
    """Get Stripe publishable key for frontend"""
    from app.services.stripe_service import get_stripe_credentials
    _, publishable_key = get_stripe_credentials()
    if not publishable_key:
        raise HTTPException(
            status_code=500,
            detail="Stripe not configured"
        )
    return {"publishable_key": publishable_key}


@router.get("/", response_model=BillingInfo)
def get_billing_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's billing and subscription information"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    usage = usage_service.get_current_usage(current_user, db)

    limits = stripe_service.get_tier_limits(subscription.tier)

    return {
        "stripe_customer_id": subscription.stripe_customer_id,
        "has_payment_method": subscription.stripe_customer_id is not None,
        "subscription": subscription,
        "usage": {
            **usage.__dict__,
            "limits": limits
        }
    }


@router.get("/my-subscription")
def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get simplified subscription status for frontend"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    usage = usage_service.get_current_usage(current_user, db)
    limits = stripe_service.get_tier_limits(subscription.tier)
    remaining_unlocks = usage_service.get_remaining_unlocks(current_user, db)

    return {
        "tier": subscription.tier.value if hasattr(subscription.tier, 'value') else subscription.tier,
        "status": subscription.status.value if hasattr(subscription.status, 'value') else subscription.status,
        "views_remaining": remaining_unlocks,
        "views_limit": limits.get("monthly_unlocks", 10),
        "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "is_active": subscription.status == SubscriptionStatus.ACTIVE
    }


@router.get("/limits", response_model=SubscriptionLimits)
def get_subscription_limits(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current subscription tier limits"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    return stripe_service.get_tier_limits(subscription.tier)


@router.get("/usage", response_model=UsageStats)
def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current usage statistics"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    usage = usage_service.get_current_usage(current_user, db)
    limits = stripe_service.get_tier_limits(subscription.tier)

    return {
        **usage.__dict__,
        "limits": limits
    }


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout session for subscription"""
    # Validate tier - normalize to uppercase to match database enum
    tier_value = checkout_data.tier.upper() if checkout_data.tier else ""
    try:
        tier = SubscriptionTier(tier_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription tier: {checkout_data.tier}"
        )

    if tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create checkout for free tier"
        )

    if tier == SubscriptionTier.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enterprise tier requires custom setup. Please contact sales."
        )

    # Get or create Stripe customer
    subscription = usage_service.get_or_create_subscription(current_user, db)

    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()

    # Get price ID for tier
    price_id = stripe_service.STRIPE_PRICES.get(tier)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe price not configured for this tier"
        )

    # Create checkout session
    session = stripe_service.create_checkout_session(
        customer_id=subscription.stripe_customer_id,
        price_id=price_id,
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "user_id": current_user.id,
            "tier": tier.value
        }
    )

    log_event(
        db,
        action="subscription.checkout_session.create",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="subscription",
        resource_id=str(getattr(subscription, "id", "")),
        metadata={"tier": tier.value, "session_id": session.id},
    )

    return {
        "session_id": session.id,
        "url": session.url
    }


@router.post("/subscription-intent", response_model=SubscriptionIntentResponse)
def create_subscription_intent(
    payload: SubscriptionIntentCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create an in-app subscription flow (Stripe Elements modal).

    This creates a Stripe Subscription in `default_incomplete` mode and returns the
    latest invoice PaymentIntent client_secret for confirmation via stripe.confirmCardPayment().
    """
    from datetime import timezone

    # Validate tier - normalize to uppercase to match database enum
    tier_value = payload.tier.upper() if payload.tier else ""
    try:
        tier = SubscriptionTier(tier_value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid subscription tier: {payload.tier}")

    if tier in (SubscriptionTier.FREE, SubscriptionTier.ENTERPRISE):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This tier is not self-serve via card payment.")

    subscription = usage_service.get_or_create_subscription(current_user, db)

    # Prevent accidental duplicate active subscriptions. Use portal for upgrades/changes.
    # Check both: users with Stripe subscription OR users with active paid tier (e.g., Enterprise set up manually)
    is_paid_tier = subscription.tier and subscription.tier not in (SubscriptionTier.FREE,)
    if subscription.status == SubscriptionStatus.ACTIVE and is_paid_tier:
        if subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="You already have an active subscription. Use 'Manage Billing' to change your plan."
            )
        else:
            # Active paid subscription without Stripe (e.g., Enterprise) - cannot self-serve change
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You have an active {subscription.tier.value} subscription. Please contact support to modify your plan."
            )

    # If there's an old incomplete subscription attempt, best-effort cancel it on Stripe.
    if subscription.stripe_subscription_id and subscription.status == SubscriptionStatus.INCOMPLETE:
        try:
            client = get_stripe_client()
            client.Subscription.cancel(subscription.stripe_subscription_id)
        except Exception:
            # ignore; we'll proceed with a fresh attempt
            pass

    # Ensure Stripe customer exists
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id},
        )
        subscription.stripe_customer_id = customer.id
        db.commit()

    price_id = stripe_service.STRIPE_PRICES.get(tier)
    if not price_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe price not configured for this tier")

    try:
        client = get_stripe_client()
        stripe_sub = client.Subscription.create(
            customer=subscription.stripe_customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent"],
            metadata={"user_id": str(current_user.id), "tier": tier.value},
        )
        
        sub_status = getattr(stripe_sub, "status", None)
        latest_invoice = getattr(stripe_sub, "latest_invoice", None)
        payment_intent = getattr(latest_invoice, "payment_intent", None) if latest_invoice else None
        client_secret = getattr(payment_intent, "client_secret", None)
        
        # Debug logging for subscription creation
        invoice_status = getattr(latest_invoice, "status", None) if latest_invoice else None
        pi_status = getattr(payment_intent, "status", None) if payment_intent else None
        logger.info(
            f"Stripe subscription created: sub_id={stripe_sub.id}, sub_status={sub_status}, "
            f"invoice_status={invoice_status}, pi_status={pi_status}, "
            f"has_invoice={bool(latest_invoice)}, has_pi={bool(payment_intent)}, has_secret={bool(client_secret)}"
        )
        
        # Handle active subscription (already paid, no payment needed)
        if sub_status == "active":
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.stripe_price_id = price_id
            subscription.tier = tier
            subscription.status = SubscriptionStatus.ACTIVE
            cps = getattr(stripe_sub, "current_period_start", None)
            cpe = getattr(stripe_sub, "current_period_end", None)
            if isinstance(cps, (int, float)):
                subscription.current_period_start = datetime.fromtimestamp(int(cps), tz=timezone.utc)
            if isinstance(cpe, (int, float)):
                subscription.current_period_end = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
            db.commit()
            return {"stripe_subscription_id": stripe_sub.id, "client_secret": None, "status": "active"}
        
        # Handle trialing subscription (trial period, no payment needed now)
        if sub_status == "trialing":
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.stripe_price_id = price_id
            subscription.tier = tier
            subscription.status = SubscriptionStatus.ACTIVE  # Treat trial as active
            cps = getattr(stripe_sub, "current_period_start", None)
            cpe = getattr(stripe_sub, "current_period_end", None)
            if isinstance(cps, (int, float)):
                subscription.current_period_start = datetime.fromtimestamp(int(cps), tz=timezone.utc)
            if isinstance(cpe, (int, float)):
                subscription.current_period_end = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
            db.commit()
            logger.info(f"Subscription {stripe_sub.id} is in trial period, treating as active")
            return {"stripe_subscription_id": stripe_sub.id, "client_secret": None, "status": "active"}
        
        # Handle paid invoice (already charged, subscription starting)
        if invoice_status == "paid" and sub_status == "incomplete":
            # Edge case: invoice was paid but subscription still incomplete
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.stripe_price_id = price_id
            subscription.tier = tier
            subscription.status = SubscriptionStatus.ACTIVE
            db.commit()
            logger.info(f"Subscription {stripe_sub.id} invoice already paid, activating")
            return {"stripe_subscription_id": stripe_sub.id, "client_secret": None, "status": "active"}
        
        if not client_secret:
            # No client_secret means no payment is required right now
            # This can happen with trials, $0 invoices, or already-paid subscriptions
            logger.warning(
                f"Stripe subscription created without client_secret. "
                f"sub_status={sub_status}, invoice_status={invoice_status}, pi_status={pi_status}, "
                f"latest_invoice={bool(latest_invoice)}, payment_intent={bool(payment_intent)}. "
                f"Treating as successful subscription creation."
            )
            # Save the subscription and return success - frontend will handle appropriately
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.stripe_price_id = price_id
            subscription.tier = tier
            # For incomplete subscriptions without payment, treat as active since no payment is needed
            subscription.status = SubscriptionStatus.ACTIVE
            cps = getattr(stripe_sub, "current_period_start", None)
            cpe = getattr(stripe_sub, "current_period_end", None)
            if isinstance(cps, (int, float)):
                subscription.current_period_start = datetime.fromtimestamp(int(cps), tz=timezone.utc)
            if isinstance(cpe, (int, float)):
                subscription.current_period_end = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
            db.commit()
            return {"stripe_subscription_id": stripe_sub.id, "client_secret": None, "status": "active"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe subscription creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Unable to create subscription: {e}")

    # Persist linkage for webhook reconciliation
    subscription.stripe_subscription_id = stripe_sub.id
    subscription.stripe_price_id = price_id
    subscription.tier = tier
    subscription.status = SubscriptionStatus.INCOMPLETE

    cps = getattr(stripe_sub, "current_period_start", None)
    cpe = getattr(stripe_sub, "current_period_end", None)
    if isinstance(cps, (int, float)):
        subscription.current_period_start = datetime.fromtimestamp(int(cps), tz=timezone.utc)
    if isinstance(cpe, (int, float)):
        subscription.current_period_end = datetime.fromtimestamp(int(cpe), tz=timezone.utc)

    db.commit()

    log_event(
        db,
        action="subscription.intent.create",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="subscription",
        resource_id=str(getattr(subscription, "id", "")),
        metadata={"tier": tier.value, "stripe_subscription_id": stripe_sub.id},
    )

    return {"stripe_subscription_id": stripe_sub.id, "client_secret": client_secret}


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    request: Request,
    portal_data: PortalSessionCreate | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Customer Portal session"""
    subscription = usage_service.get_or_create_subscription(current_user, db)

    return_url = (portal_data.return_url if portal_data else None) or request.query_params.get("return_url")
    if not return_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="return_url is required"
        )

    if not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe first."
        )

    try:
        session = stripe_service.create_portal_session(
            customer_id=subscription.stripe_customer_id,
            return_url=return_url
        )
    except stripe.InvalidRequestError as e:
        logger.error(f"Stripe InvalidRequestError creating portal session for customer {subscription.stripe_customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to open billing portal. Your billing account may be invalid. Please contact support."
        )

    return {"url": session.url}


@router.post("/cancel")
def cancel_subscription(
    request: Request,
    at_period_end: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription"""
    subscription = usage_service.get_or_create_subscription(current_user, db)

    if not subscription.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel"
        )

    stripe_service.cancel_subscription(
        subscription.stripe_subscription_id,
        at_period_end=at_period_end
    )

    subscription.cancel_at_period_end = at_period_end
    if not at_period_end:
        subscription.status = SubscriptionStatus.CANCELED

    db.commit()

    log_event(
        db,
        action="subscription.cancel",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="subscription",
        resource_id=str(getattr(subscription, "id", "")),
        metadata={"at_period_end": at_period_end},
    )

    return {"message": "Subscription canceled successfully"}


@router.post("/unlock", response_model=UnlockOpportunityResponse)
def unlock_opportunity(
    unlock_data: UnlockOpportunityRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlock an opportunity for full viewing"""
    success, message = usage_service.unlock_opportunity(
        current_user,
        unlock_data.opportunity_id,
        db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )

    log_event(
        db,
        action="subscription.unlock",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=unlock_data.opportunity_id,
    )

    remaining = usage_service.get_remaining_unlocks(current_user, db)

    return {
        "success": True,
        "remaining_unlocks": remaining,
        "opportunity_id": unlock_data.opportunity_id
    }


@router.get("/unlocked/{opportunity_id}")
def check_opportunity_unlocked(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if user has unlocked an opportunity"""
    unlocked = usage_service.is_opportunity_unlocked(current_user, opportunity_id, db)
    remaining = usage_service.get_remaining_unlocks(current_user, db)

    return {
        "unlocked": unlocked,
        "remaining_unlocks": remaining
    }


@router.get("/access/{opportunity_id}", response_model=OpportunityAccessInfo)
def get_opportunity_access_info(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed access information for an opportunity.
    
    Returns tier-based access status, freshness badge, countdown timer info,
    and whether pay-per-unlock is available.
    """
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    ent = get_opportunity_entitlements(db, opportunity, current_user)
    return {
        "opportunity_id": opportunity_id,
        "age_days": ent.age_days,
        "freshness_badge": ent.freshness_badge,
        "is_accessible": ent.is_accessible,
        "is_unlocked": ent.is_unlocked,
        "unlock_method": ent.unlock_method,
        "days_until_unlock": ent.days_until_unlock,
        "can_pay_to_unlock": ent.can_pay_to_unlock,
        "unlock_price": ent.unlock_price,
    }


@router.post("/pay-per-unlock", response_model=PayPerUnlockResponse)
def create_pay_per_unlock(
    unlock_data: PayPerUnlockRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a payment intent for one-time unlock.
    
    Supports:
    - Free tier + Archive (91+ days): pay-per-unlock ($15)
    - Business tier + HOT (0-7 days): fast pass ($99) single-opportunity access
    
    Daily limit: best-effort 5 attempts/day (shared across these one-time unlocks).
    """
    from datetime import timezone
    from sqlalchemy import text
    from app.models.subscription import UnlockedOpportunity
    from app.models.stripe_event import PayPerUnlockAttempt, PayPerUnlockAttemptStatus
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == unlock_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    
    # Calculate opportunity age
    now = datetime.now(timezone.utc)
    created_at = opportunity.created_at or now
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = (now - created_at).days
    
    # Check if already unlocked
    existing = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.user_id == current_user.id,
        UnlockedOpportunity.opportunity_id == unlock_data.opportunity_id
    ).first()
    
    if existing and (not existing.expires_at or now <= existing.expires_at):
        raise HTTPException(
            status_code=400,
            detail="Opportunity already unlocked"
        )
    
    unlock_type: str
    amount_cents: int

    # Eligibility rules based on the product matrix.
    if subscription.tier == SubscriptionTier.FREE:
        if age_days < 91:
            raise HTTPException(
                status_code=400,
                detail=f"Pay-per-unlock only available for opportunities 91+ days old. This opportunity is {age_days} days old."
            )
        unlock_type = "pay_per_unlock"
        amount_cents = stripe_service.PAY_PER_UNLOCK_PRICE
    elif subscription.tier == SubscriptionTier.BUSINESS:
        if age_days > 7:
            raise HTTPException(
                status_code=400,
                detail="Fast pass is only available for HOT opportunities (0-7 days old)."
            )
        unlock_type = "fast_pass"
        amount_cents = stripe_service.FAST_PASS_PRICE
    else:
        raise HTTPException(
            status_code=400,
            detail="One-time unlock is only available for Free (Archive) or Business (HOT fast pass) tiers."
        )

    # Concurrency-safe daily limit (5/day): use a per-user/day advisory lock on Postgres,
    # and count attempts (not just succeeded unlocks) so users can't spam PaymentIntents.
    today = now.date()
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        # Lock scope: (user_id, YYYYMMDD)
        db.execute(
            text("SELECT pg_advisory_xact_lock(:k1, :k2)"),
            {"k1": int(current_user.id), "k2": int(today.strftime("%Y%m%d"))},
        )

    # Re-check already unlocked inside the lock window
    existing2 = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.user_id == current_user.id,
        UnlockedOpportunity.opportunity_id == unlock_data.opportunity_id
    ).first()
    if existing2 and (not existing2.expires_at or now <= existing2.expires_at):
        raise HTTPException(status_code=400, detail="Opportunity already unlocked")

    attempts_today = db.query(PayPerUnlockAttempt).filter(
        PayPerUnlockAttempt.user_id == current_user.id,
        PayPerUnlockAttempt.attempt_date == today,
        PayPerUnlockAttempt.status.in_([PayPerUnlockAttemptStatus.CREATED, PayPerUnlockAttemptStatus.SUCCEEDED]),
    ).count()

    if attempts_today >= 5:
        raise HTTPException(status_code=429, detail="Daily pay-per-unlock limit reached (5 per day). Try again tomorrow.")
    
    # Get or create Stripe customer
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()

    # Record attempt before creating PaymentIntent (prevents spamming under concurrency)
    attempt = PayPerUnlockAttempt(
        user_id=current_user.id,
        opportunity_id=unlock_data.opportunity_id,
        attempt_date=today,
        status=PayPerUnlockAttemptStatus.CREATED,
    )
    db.add(attempt)
    db.flush()
    
    # Create payment intent
    try:
        payment_intent = stripe_service.create_payment_intent_for_one_time_unlock(
            customer_id=subscription.stripe_customer_id,
            opportunity_id=unlock_data.opportunity_id,
            user_id=current_user.id,
            amount_cents=amount_cents,
            unlock_type=unlock_type,
        )
    except Exception:
        attempt.status = PayPerUnlockAttemptStatus.CANCELED
        db.commit()
        raise

    attempt.stripe_payment_intent_id = payment_intent.id
    db.commit()

    log_event(
        db,
        action="subscription.pay_per_unlock.intent_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=unlock_data.opportunity_id,
        metadata={"payment_intent_id": payment_intent.id},
    )
    
    return {
        "client_secret": payment_intent.client_secret,
        "payment_intent_id": payment_intent.id,
        "amount": amount_cents,
        "opportunity_id": unlock_data.opportunity_id
    }


@router.post("/confirm-pay-per-unlock")
def confirm_pay_per_unlock(
    payment_intent_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Confirm a successful pay-per-unlock payment and grant access.
    
    Call this after payment is confirmed on the frontend.
    """
    from datetime import timezone
    from app.models.subscription import UnlockedOpportunity, UnlockMethod
    from app.models.stripe_event import PayPerUnlockAttempt, PayPerUnlockAttemptStatus
    import stripe
    
    # Verify payment intent
    client = stripe_service.get_stripe_client() if hasattr(stripe_service, 'get_stripe_client') else None
    if not client:
        from app.services.stripe_service import get_stripe_client
        client = get_stripe_client()
    
    try:
        payment_intent = client.PaymentIntent.retrieve(payment_intent_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payment intent: {str(e)}")
    
    # Verify payment was successful
    if payment_intent.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail=f"Payment not completed. Status: {payment_intent.status}"
        )
    
    # Verify metadata
    payment_type = payment_intent.metadata.get("type")
    if payment_type not in ("pay_per_unlock", "fast_pass"):
        raise HTTPException(status_code=400, detail="Invalid payment type")
    
    opportunity_id = int(payment_intent.metadata.get("opportunity_id", 0))
    user_id = int(payment_intent.metadata.get("user_id", 0))
    
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Payment belongs to another user")
    
    # Check if already unlocked with this payment
    existing = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.stripe_payment_intent_id == payment_intent_id
    ).first()
    
    if existing:
        log_event(
            db,
            action="subscription.pay_per_unlock.confirm_already_unlocked",
            actor=current_user,
            actor_type="user",
            request=request,
            resource_type="opportunity",
            resource_id=opportunity_id,
            metadata={"payment_intent_id": payment_intent_id},
        )
        return {
            "success": True,
            "message": "Already unlocked with this payment",
            "opportunity_id": opportunity_id,
            "expires_at": existing.expires_at.isoformat() if existing.expires_at else None
        }
    
    # Create unlock record with 30-day expiration
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)
    
    unlock = UnlockedOpportunity(
        user_id=current_user.id,
        opportunity_id=opportunity_id,
        unlock_method=UnlockMethod.PAY_PER_UNLOCK,
        amount_paid=payment_intent.amount,
        stripe_payment_intent_id=payment_intent_id,
        expires_at=expires_at
    )
    db.add(unlock)
    db.commit()

    attempt = db.query(PayPerUnlockAttempt).filter(
        PayPerUnlockAttempt.stripe_payment_intent_id == payment_intent_id
    ).first()
    if attempt:
        attempt.status = PayPerUnlockAttemptStatus.SUCCEEDED
        db.commit()

    log_event(
        db,
        action="subscription.pay_per_unlock.confirm_succeeded",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=opportunity_id,
        metadata={"payment_intent_id": payment_intent_id, "expires_at": expires_at.isoformat()},
    )
    
    return {
        "success": True,
        "message": "Opportunity unlocked successfully",
        "opportunity_id": opportunity_id,
        "expires_at": expires_at.isoformat(),
        "access_days": 30
    }


@router.post("/deep-clone-checkout")
def create_deep_clone_checkout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for Deep Clone Analysis ($49 one-time payment).
    
    Returns a checkout URL that redirects to Stripe's hosted checkout page.
    """
    from app.services.stripe_service import get_stripe_client, get_stripe_credentials
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    
    # Check if user already has premium access
    if subscription.tier in [SubscriptionTier.PRO, SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE]:
        return {
            "success": True,
            "has_access": True,
            "message": "You already have access to Deep Clone Analysis with your subscription"
        }
    
    # Get or create Stripe customer
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()
    
    # Create checkout session for one-time payment
    try:
        stripe_client = get_stripe_client()
        _, publishable_key = get_stripe_credentials()
        
        # Build success and cancel URLs
        frontend_url = os.getenv("FRONTEND_URL", "")
        if not frontend_url:
            frontend_url = request.headers.get("origin", "")
        
        success_url = f"{frontend_url}/build/reports?deep_clone_success=true"
        cancel_url = f"{frontend_url}/build/reports?deep_clone_cancelled=true"
        
        session = stripe_client.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": 4900,  # $49.00
                        "product_data": {
                            "name": "Deep Clone Analysis",
                            "description": "Detailed 3-mile and 5-mile radius comparison for target city analysis",
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "type": "deep_clone",
            },
        )
        
        log_event(
            db,
            action="subscription.deep_clone_checkout.created",
            actor=current_user,
            actor_type="user",
            request=request,
            resource_type="checkout",
            resource_id=str(session.id),
            metadata={"amount_cents": 4900},
        )
        
        return {
            "success": True,
            "has_access": False,
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/export")
def export_opportunities(
    export_data: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export opportunities based on subscription tier limits"""
    batch_size = len(export_data.opportunity_ids)

    # Check if user can export
    can_export, reason = usage_service.can_export(current_user, batch_size, db)
    if not can_export:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Get opportunities (only unlocked ones)
    opportunities = []
    for opp_id in export_data.opportunity_ids:
        if usage_service.is_opportunity_unlocked(current_user, opp_id, db):
            opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
            if opp:
                opportunities.append(opp)

    if not opportunities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No unlocked opportunities found to export"
        )

    # Record export
    usage_service.record_export(current_user, len(opportunities), db)

    # Generate export
    if export_data.format == "csv":
        return export_csv(opportunities)
    elif export_data.format == "json":
        return export_json(opportunities)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export format. Use 'csv' or 'json'"
        )


def export_csv(opportunities):
    """Generate CSV export"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "title", "description", "category", "status",
        "validation_count", "comment_count", "created_at"
    ])
    writer.writeheader()

    for opp in opportunities:
        writer.writerow({
            "id": opp.id,
            "title": opp.title,
            "description": opp.description,
            "category": opp.category,
            "status": opp.status,
            "validation_count": opp.validation_count,
            "comment_count": opp.comment_count,
            "created_at": opp.created_at.isoformat() if opp.created_at else ""
        })

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opportunities.csv"}
    )


def export_json(opportunities):
    """Generate JSON export"""
    data = [{
        "id": opp.id,
        "title": opp.title,
        "description": opp.description,
        "category": opp.category,
        "status": opp.status,
        "validation_count": opp.validation_count,
        "comment_count": opp.comment_count,
        "created_at": opp.created_at.isoformat() if opp.created_at else None
    } for opp in opportunities]

    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=opportunities.json"}
    )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    DEPRECATED: Stripe webhook endpoint.

    Canonical endpoint is: POST /api/v1/webhook/stripe (handled by `routers/stripe_webhook.py`).
    We keep this route as a thin forwarder to avoid breaking existing Stripe configs.
    """
    # Import locally to avoid circular imports at module load time.
    from app.routers.stripe_webhook import stripe_webhook as canonical_webhook

    return await canonical_webhook(request=request, db=db)


@router.get("/slots/balance")
def get_slot_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's opportunity slot balance"""
    from app.services.slot_service import slot_service
    return slot_service.get_balance_info(current_user, db)


@router.post("/slots/claim/{opportunity_id}")
def claim_opportunity(
    opportunity_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Claim an opportunity using a slot"""
    from app.services.slot_service import slot_service
    
    if not current_user.subscription or current_user.subscription.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active subscription is required to claim opportunities"
        )
    
    success, message = slot_service.claim_opportunity(current_user, opportunity_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    log_event(
        db,
        action="opportunity.claim",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=str(opportunity_id),
        metadata={"message": message},
    )
    
    return {"success": True, "message": message}


@router.get("/slots/claim-status/{opportunity_id}")
def get_opportunity_claim_status(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """Get claim status for an opportunity (public)"""
    from app.services.slot_service import slot_service
    return slot_service.get_opportunity_claim_status(opportunity_id, db)


@router.post("/slots/purchase")
def purchase_slots(
    request: Request,
    quantity: int = 1,
    success_url: str = None,
    cancel_url: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a checkout session to purchase additional opportunity slots"""
    from app.services.slot_service import slot_service
    
    if quantity < 1 or quantity > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be between 1 and 10"
        )
    
    if not current_user.subscription or current_user.subscription.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active subscription is required to purchase additional slots"
        )
    
    base_url = os.getenv("FRONTEND_URL", os.getenv("BACKEND_URL", ""))
    if not success_url:
        success_url = f"{base_url}/discover?slots_purchased=true"
    if not cancel_url:
        cancel_url = f"{base_url}/pricing"
    
    try:
        result = slot_service.create_slot_checkout_session(
            user=current_user,
            quantity=quantity,
            success_url=success_url,
            cancel_url=cancel_url,
            db=db
        )
        
        log_event(
            db,
            action="slot.checkout_session.create",
            actor=current_user,
            actor_type="user",
            request=request,
            resource_type="slot_purchase",
            metadata={"quantity": quantity, "session_id": result["session_id"]},
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )
