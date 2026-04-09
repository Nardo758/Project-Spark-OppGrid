"""
Stripe checkout and webhook handling for guest & member report purchases.
Supports both payment processing and auto-account creation for guests.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import stripe
import logging
import secrets
import os
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.generated_report import GeneratedReport
from app.core.dependencies import get_current_user
from app.services.report_quota_service import ReportQuotaService
from app.services.report_generator import ReportGenerator
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter(prefix="/checkout", tags=["Payments"])


class CheckoutRequest(BaseModel):
    """Create Stripe checkout session for report purchase."""
    report_tier: str  # layer_1, layer_2, layer_3
    opportunity_id: int
    guest_email: Optional[EmailStr] = None  # Required if not logged in
    user_id: Optional[int] = None  # Set by auth


@router.post("/session")
def create_checkout_session(
    request: CheckoutRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create Stripe checkout session for report purchase.
    
    Supports:
    - Guest checkout (no account needed, auto-creates account)
    - Member checkout (logged in, optional saved card)
    - Overage purchases (charged overage price, not base price)
    
    Response includes Stripe checkout URL to redirect user.
    """
    
    # Validate request
    if not current_user and not request.guest_email:
        raise HTTPException(
            status_code=400,
            detail="Either logged in or guest_email required"
        )
    
    if request.report_tier not in ["layer_1", "layer_2", "layer_3"]:
        raise HTTPException(status_code=400, detail="Invalid report_tier")
    
    # Check opportunity exists
    opportunity = db.query(Opportunity).filter(Opportunity.id == request.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Determine email and user info
    customer_email = request.guest_email if not current_user else current_user.email
    user_id = current_user.id if current_user else None
    
    # Get pricing
    quota_service = ReportQuotaService(db)
    can_gen, message, price_cents = quota_service.check_access(current_user, request.report_tier)
    
    if not can_gen:
        raise HTTPException(status_code=403, detail=message)
    
    # If price is 0, user doesn't need checkout (should use direct generate endpoint)
    if price_cents == 0:
        raise HTTPException(
            status_code=400,
            detail="This report is free from your allocation. Use generate endpoint instead."
        )
    
    # Create Stripe checkout session
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"OppGrid {request.report_tier.replace('_', ' ').title()} Report",
                            "description": f"Business analysis report for {opportunity.title or 'Opportunity'}"
                        },
                        "unit_amount": price_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url="https://oppgrid.app/checkout/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://oppgrid.app/reports",
            customer_email=customer_email,
            metadata={
                "user_id": str(user_id) if user_id else "guest",
                "guest_email": customer_email if not user_id else "",
                "report_tier": request.report_tier,
                "opportunity_id": str(request.opportunity_id),
                "price_cents": str(price_cents),
            },
        )
        
        logger.info(f"Created Stripe session {session.id} for {request.report_tier}: ${price_cents/100:.2f}")
        
        return {
            "success": True,
            "session_id": session.id,
            "checkout_url": session.url,
            "amount": price_cents,
            "currency": "usd",
        }
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating session: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


@router.post("/webhook")
async def handle_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook for payment success.
    
    On successful payment:
    1. Create account if guest (auto-account)
    2. Generate report
    3. Send to email
    4. Log purchase
    """
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header or not STRIPE_WEBHOOK_SECRET:
        logger.warning("Missing Stripe webhook signature or secret")
        raise HTTPException(status_code=400, detail="Invalid request")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    from sqlalchemy.exc import IntegrityError as _IntegrityError
    from app.models.stripe_event import StripeWebhookEvent, StripeWebhookEventStatus

    event_id = event.get("id")
    if event_id:
        existing_event = db.query(StripeWebhookEvent).filter(
            StripeWebhookEvent.stripe_event_id == event_id
        ).first()
        if existing_event and existing_event.status == StripeWebhookEventStatus.PROCESSED:
            logger.info(f"Checkout webhook: duplicate event {event_id}, skipping")
            return {"status": "already_processed"}

        if not existing_event:
            db.add(
                StripeWebhookEvent(
                    stripe_event_id=event_id,
                    event_type=event.get("type", ""),
                    livemode=bool(event.get("livemode", False)),
                    status=StripeWebhookEventStatus.PROCESSING,
                )
            )
        else:
            existing_event.status = StripeWebhookEventStatus.PROCESSING
            existing_event.attempt_count = (existing_event.attempt_count or 0) + 1

        try:
            db.commit()
        except _IntegrityError:
            db.rollback()
            return {"status": "already_processed"}

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        try:
            await process_payment_success(session, db)
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return {"status": "error", "message": str(e)}

    if event_id:
        try:
            evt = db.query(StripeWebhookEvent).filter(
                StripeWebhookEvent.stripe_event_id == event_id
            ).first()
            if evt:
                evt.status = StripeWebhookEventStatus.PROCESSED
                db.commit()
        except Exception:
            pass

    return {"status": "success"}


async def process_payment_success(session: dict, db: Session):
    """Process successful payment and generate report."""
    
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    guest_email = metadata.get("guest_email")
    report_tier = metadata.get("report_tier")
    opportunity_id = int(metadata.get("opportunity_id", 0))
    price_cents = int(metadata.get("price_cents", 0))
    stripe_charge_id = session.get("payment_intent")
    
    if not all([report_tier, opportunity_id]):
        raise ValueError("Missing required metadata")
    
    # Get or create user
    if user_id != "guest":
        # Existing user
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
    else:
        # Guest checkout - create account
        customer_email = guest_email or session.get("customer_email")
        if not customer_email:
            raise ValueError("Missing customer email")
        
        # Check if user already exists
        user = db.query(User).filter(User.email == customer_email).first()
        
        if not user:
            # Auto-create account
            from app.models.user import User as UserModel
            
            # Generate temp password
            temp_password = secrets.token_urlsafe(16)
            
            user = UserModel(
                email=customer_email,
                name=customer_email.split("@")[0],  # Use email prefix as name
                hashed_password=None,  # No password - email login only
                is_verified=True,  # Auto-verify since they paid
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Auto-created account for guest: {customer_email}")
    
    # Get opportunity
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise ValueError(f"Opportunity {opportunity_id} not found")
    
    # Check if report already exists (avoid duplicates)
    existing = db.query(GeneratedReport).filter(
        GeneratedReport.user_id == user.id,
        GeneratedReport.opportunity_id == opportunity_id,
        GeneratedReport.report_type == report_tier,
    ).first()
    
    if existing:
        logger.warning(f"Report already exists for user {user.id}, opportunity {opportunity_id}")
        # Send email with existing report link
        await send_report_email(user.email, existing, report_tier)
        return
    
    # Generate report
    generator = ReportGenerator(db)
    
    if report_tier == "layer_1":
        report = generator.generate_layer1_report(opportunity, user, None)
    elif report_tier == "layer_2":
        report = generator.generate_layer2_report(opportunity, user, None)
    elif report_tier == "layer_3":
        report = generator.generate_layer3_report(opportunity, user, None)
    else:
        raise ValueError(f"Unknown report tier: {report_tier}")
    
    # Log purchase
    quota_service = ReportQuotaService(db)
    quota_service.log_purchase(
        report_tier=report_tier,
        payment_type="stripe",
        amount_cents=price_cents,
        stripe_charge_id=stripe_charge_id,
        user=user,
        report_id=report.id,
        opportunity_id=opportunity_id,
    )
    
    # Send email
    await send_report_email(user.email, report, report_tier)
    
    logger.info(f"Payment processed: {report_tier} for user {user.id}, report {report.id}")


async def send_report_email(email: str, report: GeneratedReport, report_tier: str):
    """Send report to user's email."""
    
    try:
        from app.services.email_service import send_email
        
        subject = f"Your OppGrid {report_tier.replace('_', ' ').title()} Report is Ready"
        
        html_content = f"""
        <html>
            <body>
                <h2>Your Report is Ready!</h2>
                <p>Hi,</p>
                <p>Your {report_tier.replace('_', ' ').title()} report has been generated and is ready to view.</p>
                
                <div style="margin: 20px 0;">
                    <a href="https://oppgrid.app/reports/{report.id}" 
                       style="background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                       View Your Report
                    </a>
                </div>
                
                <p style="color: #666; font-size: 12px;">
                    Report ID: {report.id}<br>
                    Generated: {report.created_at.isoformat() if report.created_at else 'Just now'}
                </p>
            </body>
        </html>
        """
        
        await send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
        )
        
        logger.info(f"Sent report email to {email}")
    
    except Exception as e:
        logger.error(f"Failed to send report email: {e}")
        # Don't fail the whole flow if email fails
