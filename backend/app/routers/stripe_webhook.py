"""
Unified Stripe Webhook Router

Handles all Stripe webhook events and updates the transactions table automatically.
This router consolidates payment_intent, invoice, and subscription events.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import logging
import json
import re
from werkzeug.security import generate_password_hash

from app.db.database import get_db
from app.models.user import User
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus, UnlockedOpportunity, UnlockMethod
from app.models.stripe_event import (
    StripeWebhookEvent,
    StripeWebhookEventStatus,
    PayPerUnlockAttempt,
    PayPerUnlockAttemptStatus,
)
from app.models.idea_validation import IdeaValidation, IdeaValidationStatus
from app.models.purchased_report import PurchasedTemplate
from app.services.stripe_service import get_stripe_client
from app.services.usage_service import usage_service
from datetime import datetime, timedelta, timezone
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/stripe", tags=["Stripe Webhooks"])


def get_webhook_secret():
    return os.getenv("STRIPE_WEBHOOK_SECRET", "")


def is_stripe_dev_mode():
    """Check if Stripe dev mode is enabled (skips signature verification in development only)."""
    dev_mode = os.getenv("STRIPE_DEV_MODE", "0") == "1"
    is_development = os.getenv("REPLIT_DEPLOYMENT", "") != "1"
    return dev_mode and is_development


@router.post("")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Unified Stripe webhook handler.
    
    Handles:
    - payment_intent.succeeded: Update transaction status, trigger fulfillment
    - payment_intent.payment_failed: Update transaction status to failed
    - invoice.paid: Record subscription payment in transactions
    - invoice.payment_failed: Handle failed subscription payment
    - checkout.session.completed: Link subscription to user
    - customer.subscription.updated: Sync subscription status
    - customer.subscription.deleted: Cancel subscription
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")
    
    webhook_secret = get_webhook_secret()
    event_id = None
    event_created = None
    livemode = False
    
    if not webhook_secret:
        if is_stripe_dev_mode():
            logger.warning("STRIPE_DEV_MODE enabled - skipping signature verification (development only)")
            try:
                event_data = json.loads(payload)
                event_id = event_data.get("id")
                event_type = event_data.get("type")
                event_object = event_data.get("data", {}).get("object", {})
                livemode = bool(event_data.get("livemode", False))
                created_raw = event_data.get("created")
                if isinstance(created_raw, (int, float)):
                    event_created = datetime.fromtimestamp(created_raw, tz=timezone.utc)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        else:
            logger.error("STRIPE_WEBHOOK_SECRET not configured - rejecting webhook in production")
            raise HTTPException(
                status_code=500, 
                detail="Stripe webhook secret not configured. This is a server configuration error."
            )
    else:
        try:
            stripe = get_stripe_client()
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            event_id = getattr(event, "id", None)
            event_type = event.type
            event_object = event.data.object
            livemode = bool(getattr(event, "livemode", False))
            created_raw = getattr(event, "created", None)
            if isinstance(created_raw, (int, float)):
                event_created = datetime.fromtimestamp(created_raw, tz=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")
    
    logger.info(f"Processing Stripe webhook: {event_type}")

    # Idempotency: ensure we only process each Stripe event once.
    if event_id:
        existing = db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == event_id).first()
        if existing and existing.status == StripeWebhookEventStatus.PROCESSED:
            return {"status": "success", "event_type": event_type, "idempotent": True}

        if not existing:
            db.add(
                StripeWebhookEvent(
                    stripe_event_id=event_id,
                    event_type=event_type or "",
                    livemode=livemode,
                    status=StripeWebhookEventStatus.PROCESSING,
                    attempt_count=1,
                    stripe_created_at=event_created,
                )
            )
        else:
            existing.status = StripeWebhookEventStatus.PROCESSING
            existing.attempt_count = (existing.attempt_count or 0) + 1
            existing.event_type = event_type or existing.event_type
            existing.livemode = livemode
            if event_created:
                existing.stripe_created_at = event_created

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "already_processed", "event_type": event_type}

    try:
        if event_type == "payment_intent.succeeded":
            handle_payment_intent_succeeded(event_object, db)
        elif event_type == "payment_intent.payment_failed":
            handle_payment_intent_failed(event_object, db)
        elif event_type == "invoice.paid":
            handle_invoice_paid(event_object, db)
        elif event_type == "invoice.payment_failed":
            handle_invoice_payment_failed(event_object, db)
        elif event_type == "checkout.session.completed":
            handle_checkout_completed(event_object, db)
        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(event_object, db)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(event_object, db)
        elif event_type == "checkout.session.expired":
            handle_checkout_expired(event_object, db)
        elif event_type == "invoice.voided":
            handle_invoice_voided(event_object, db)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {str(e)}")
        if event_id:
            row = db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == event_id).first()
            if row:
                row.status = StripeWebhookEventStatus.FAILED
                db.commit()
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")

    if event_id:
        row = db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == event_id).first()
        if row:
            row.status = StripeWebhookEventStatus.PROCESSED
            db.commit()

    return {"status": "success", "event_type": event_type}


def handle_payment_intent_succeeded(payment_intent: dict, db: Session):
    """
    Handle successful payment intent.
    Updates transaction status and triggers fulfillment based on payment type.
    
    ALSO: Handles subscription tier upgrades from direct payment intents.
    """
    payment_intent_id = payment_intent.get("id")
    metadata = payment_intent.get("metadata", {})
    payment_type = metadata.get("type", "")
    customer_id = payment_intent.get("customer")
    
    logger.info(f"Payment intent succeeded: {payment_intent_id}, type: {payment_type}")
    
    tx = db.query(Transaction).filter(
        Transaction.stripe_payment_intent_id == payment_intent_id
    ).first()
    
    if tx:
        tx.status = TransactionStatus.SUCCEEDED
        tx.stripe_charge_id = payment_intent.get("latest_charge")
        db.commit()
        logger.info(f"Updated transaction {tx.id} to SUCCEEDED")
    else:
        user_id = metadata.get("user_id")
        transaction_type = _map_payment_type_to_transaction_type(payment_type)
        
        if user_id and transaction_type:
            tx = Transaction(
                user_id=int(user_id),
                type=transaction_type,
                status=TransactionStatus.SUCCEEDED,
                amount_cents=payment_intent.get("amount"),
                currency=payment_intent.get("currency", "usd"),
                stripe_payment_intent_id=payment_intent_id,
                stripe_charge_id=payment_intent.get("latest_charge"),
                metadata_json=json.dumps(metadata),
            )
            
            if metadata.get("opportunity_id"):
                tx.opportunity_id = int(metadata.get("opportunity_id"))
            if metadata.get("expert_id"):
                tx.expert_id = int(metadata.get("expert_id"))
            
            db.add(tx)
            db.commit()
            logger.info(f"Created new transaction {tx.id} from webhook")
    
    # Handle subscription tier upgrade from direct payment
    if payment_type == "subscription_upgrade" and customer_id:
        _handle_subscription_upgrade_payment(payment_intent, customer_id, db)
    elif payment_type == "pay_per_unlock":
        _fulfill_pay_per_unlock(payment_intent, metadata, db)
    elif payment_type == "micro_payment":
        _fulfill_micro_payment(payment_intent, metadata, db)
    elif payment_type == "project_payment":
        _fulfill_project_payment(payment_intent, metadata, db)
    elif payment_type == "idea_validation" or metadata.get("service") == "idea_validation":
        _fulfill_idea_validation(payment_intent, metadata, db)
    elif payment_type == "deep_dive":
        _fulfill_deep_dive(payment_intent, metadata, db)
    elif payment_type == "fast_pass":
        _fulfill_fast_pass(payment_intent, metadata, db)


def handle_payment_intent_failed(payment_intent: dict, db: Session):
    """Handle failed payment intent - update transaction status."""
    payment_intent_id = payment_intent.get("id")
    
    logger.info(f"Payment intent failed: {payment_intent_id}")
    
    tx = db.query(Transaction).filter(
        Transaction.stripe_payment_intent_id == payment_intent_id
    ).first()
    
    if tx:
        tx.status = TransactionStatus.FAILED
        error = payment_intent.get("last_payment_error", {})
        if error:
            existing_meta = json.loads(tx.metadata_json) if tx.metadata_json else {}
            existing_meta["payment_error"] = {
                "code": error.get("code"),
                "message": error.get("message"),
                "type": error.get("type"),
            }
            tx.metadata_json = json.dumps(existing_meta)
        db.commit()
        logger.info(f"Updated transaction {tx.id} to FAILED")

    metadata = payment_intent.get("metadata", {}) or {}
    if metadata.get("type") == "pay_per_unlock":
        attempt = db.query(PayPerUnlockAttempt).filter(
            PayPerUnlockAttempt.stripe_payment_intent_id == payment_intent_id
        ).first()
        if attempt:
            attempt.status = PayPerUnlockAttemptStatus.FAILED
            db.commit()

    if metadata.get("type") == "idea_validation" or metadata.get("service") == "idea_validation":
        _fail_idea_validation(payment_intent, metadata, db)


def handle_invoice_paid(invoice: dict, db: Session):
    """
    Handle paid invoice - typically for subscription payments.
    Records the payment in the transactions table.
    """
    invoice_id = invoice.get("id")
    subscription_id = invoice.get("subscription")
    customer_id = invoice.get("customer")
    amount_paid = invoice.get("amount_paid", 0)
    
    logger.info(f"Invoice paid: {invoice_id}, subscription: {subscription_id}")
    
    existing = db.query(Transaction).filter(
        Transaction.stripe_invoice_id == invoice_id
    ).first()
    
    if existing:
        logger.info(f"Invoice {invoice_id} already recorded")
        return
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    
    user_id = subscription.user_id if subscription else None
    
    tx = Transaction(
        user_id=user_id,
        type=TransactionType.SUBSCRIPTION,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=amount_paid,
        currency=invoice.get("currency", "usd"),
        stripe_invoice_id=invoice_id,
        metadata_json=json.dumps({
            "subscription_id": subscription_id,
            "billing_reason": invoice.get("billing_reason"),
            "period_start": invoice.get("period_start"),
            "period_end": invoice.get("period_end"),
        }),
    )
    db.add(tx)
    db.commit()
    logger.info(f"Recorded subscription payment transaction {tx.id}")


def handle_invoice_payment_failed(invoice: dict, db: Session):
    """Handle failed invoice payment."""
    invoice_id = invoice.get("id")
    customer_id = invoice.get("customer")
    
    logger.info(f"Invoice payment failed: {invoice_id}")
    
    tx = Transaction(
        type=TransactionType.SUBSCRIPTION,
        status=TransactionStatus.FAILED,
        amount_cents=invoice.get("amount_due", 0),
        currency=invoice.get("currency", "usd"),
        stripe_invoice_id=invoice_id,
        metadata_json=json.dumps({
            "billing_reason": invoice.get("billing_reason"),
            "attempt_count": invoice.get("attempt_count"),
        }),
    )
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    
    if subscription:
        tx.user_id = subscription.user_id
    
    db.add(tx)
    db.commit()
    logger.info(f"Recorded failed invoice transaction {tx.id}")


def handle_invoice_voided(invoice: dict, db: Session):
    """
    Handle voided invoice - typically when a subscription is cancelled before payment.
    Updates any related transactions and logs the event.
    """
    invoice_id = invoice.get("id")
    subscription_id = invoice.get("subscription")
    customer_id = invoice.get("customer")
    
    logger.info(f"Invoice voided: {invoice_id}, subscription: {subscription_id}")
    
    existing_tx = db.query(Transaction).filter(
        Transaction.stripe_invoice_id == invoice_id
    ).first()
    
    if existing_tx:
        existing_tx.status = TransactionStatus.REFUNDED
        existing_meta = json.loads(existing_tx.metadata_json) if existing_tx.metadata_json else {}
        existing_meta["voided"] = True
        existing_meta["voided_reason"] = invoice.get("voided_reason") or "Invoice voided"
        existing_tx.metadata_json = json.dumps(existing_meta)
        db.commit()
        logger.info(f"Updated transaction {existing_tx.id} to REFUNDED (voided)")
    else:
        logger.info(f"No existing transaction found for voided invoice {invoice_id}")


def handle_checkout_completed(session: dict, db: Session):
    """Handle successful checkout session - link subscription to user or process slot/report/bundle purchase."""
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    payment_type = metadata.get("payment_type") or metadata.get("type", "")
    
    # Handle studio report purchase (supports guest purchases)
    if payment_type == "studio_report_purchase":
        _handle_studio_report_purchase(session, db)
        return
    
    # For subscriptions, try to auto-create account if it doesn't exist
    if not user_id and not payment_type:
        # This is likely a subscription checkout without explicit user_id
        customer_id = session.get("customer")
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        
        if customer_id and customer_email:
            logger.info(f"Auto-creating account for subscription checkout, customer: {customer_id}")
            user = _auto_create_account_from_stripe(customer_id, {"email": customer_email, "name": "Subscriber"}, db)
            if not user:
                logger.error(f"Failed to auto-create account for subscription, customer: {customer_id}")
                return
            user_id = user.id
        else:
            logger.warning("No user_id or customer info in subscription checkout session")
            return
    elif not user_id:
        logger.warning("No user_id in checkout session metadata")
        return
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        # Try to find user by email and auto-link
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        if customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
        
        if not user:
            logger.warning(f"User {user_id} not found and no email available")
            return
    
    if payment_type == "slot_purchase":
        _handle_slot_purchase(session, user, db)
    elif payment_type == "report_purchase":
        _handle_report_purchase(session, user, db)
    elif payment_type == "bundle_purchase":
        _handle_bundle_purchase(session, user, db)
    elif payment_type == "template_purchase":
        _handle_template_purchase(session, user, db)
    else:
        _handle_subscription_checkout(session, user, db)


def _handle_slot_purchase(session: dict, user: User, db: Session):
    """Handle slot purchase completion."""
    from app.services.slot_service import slot_service
    from app.models.slot_purchase import SlotPurchase

    session_id = session.get("id", "")
    metadata = session.get("metadata", {})
    quantity = int(metadata.get("quantity", 1))

    existing = db.query(SlotPurchase).filter(
        SlotPurchase.stripe_session_id == session_id
    ).first()
    if existing:
        logger.info(f"Slot purchase {session_id} already fulfilled, skipping")
        return

    logger.info(f"Processing slot purchase for user {user.id}: {quantity} slots")

    slot_purchase = SlotPurchase(
        stripe_session_id=session_id,
        user_id=user.id,
        slots=quantity,
    )
    db.add(slot_purchase)
    db.flush()

    balance = slot_service.add_bonus_slots(user, quantity, db)
    
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.ADDON,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=session.get("amount_total", 0),
        currency=session.get("currency", "usd"),
        metadata_json=json.dumps({
            "type": "slot_purchase",
            "quantity": quantity,
            "session_id": session.get("id"),
        }),
    )
    db.add(tx)
    db.commit()
    
    logger.info(f"Added {quantity} slots to user {user.id}. New balance: {balance.bonus_slots} bonus slots")


def _handle_report_purchase(session: dict, user: User, db: Session):
    """Handle report purchase completion from checkout session."""
    from app.models.purchased_report import PurchasedReport
    
    metadata = session.get("metadata", {})
    opportunity_id = int(metadata.get("opportunity_id", 0))
    report_type = metadata.get("report_type", "")
    
    logger.info(f"Processing report purchase for user {user.id}: {report_type} for opportunity {opportunity_id}")
    
    existing = db.query(PurchasedReport).filter(
        PurchasedReport.user_id == user.id,
        PurchasedReport.opportunity_id == opportunity_id,
        PurchasedReport.report_type == report_type,
    ).first()
    
    if existing:
        logger.info(f"Report already purchased: {report_type} for opportunity {opportunity_id}")
        return
    
    purchased = PurchasedReport(
        user_id=user.id,
        opportunity_id=opportunity_id,
        report_type=report_type,
        amount_cents=session.get("amount_total", 0),
        stripe_payment_intent_id=session.get("payment_intent"),
    )
    db.add(purchased)
    
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.UNLOCK,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=session.get("amount_total", 0),
        currency=session.get("currency", "usd"),
        metadata_json=json.dumps({
            "type": "report_purchase",
            "report_type": report_type,
            "opportunity_id": opportunity_id,
            "session_id": session.get("id"),
        }),
    )
    db.add(tx)
    db.commit()
    
    logger.info(f"Report purchase completed: {report_type} for user {user.id}")


def _handle_bundle_purchase(session: dict, user: User, db: Session):
    """Handle bundle purchase completion from checkout session."""
    from app.models.purchased_report import PurchasedReport, PurchasedBundle
    
    metadata = session.get("metadata", {})
    opportunity_id = int(metadata.get("opportunity_id", 0))
    bundle_type = metadata.get("bundle_type", "")
    reports = metadata.get("reports", "").split(",")
    
    logger.info(f"Processing bundle purchase for user {user.id}: {bundle_type} for opportunity {opportunity_id}")
    
    existing_bundle = db.query(PurchasedBundle).filter(
        PurchasedBundle.user_id == user.id,
        PurchasedBundle.opportunity_id == opportunity_id,
        PurchasedBundle.bundle_type == bundle_type,
    ).first()
    
    if existing_bundle:
        logger.info(f"Bundle already purchased: {bundle_type} for opportunity {opportunity_id}")
        return
    
    bundle = PurchasedBundle(
        user_id=user.id,
        opportunity_id=opportunity_id,
        bundle_type=bundle_type,
        amount_cents=session.get("amount_total", 0),
        stripe_payment_intent_id=session.get("payment_intent"),
    )
    db.add(bundle)
    
    for report_type in reports:
        report_type = report_type.strip()
        if not report_type:
            continue
        existing = db.query(PurchasedReport).filter(
            PurchasedReport.user_id == user.id,
            PurchasedReport.opportunity_id == opportunity_id,
            PurchasedReport.report_type == report_type,
        ).first()
        if not existing:
            purchased = PurchasedReport(
                user_id=user.id,
                opportunity_id=opportunity_id,
                report_type=report_type,
                amount_cents=0,
                stripe_payment_intent_id=session.get("payment_intent"),
            )
            db.add(purchased)
    
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.UNLOCK,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=session.get("amount_total", 0),
        currency=session.get("currency", "usd"),
        metadata_json=json.dumps({
            "type": "bundle_purchase",
            "bundle_type": bundle_type,
            "opportunity_id": opportunity_id,
            "reports": reports,
            "session_id": session.get("id"),
        }),
    )
    db.add(tx)
    db.commit()
    
    logger.info(f"Bundle purchase completed: {bundle_type} ({len(reports)} reports) for user {user.id}")


def _handle_template_purchase(session: dict, user: User, db: Session):
    """Handle template purchase completion from checkout session."""
    metadata = session.get("metadata", {})
    template_slug = metadata.get("template_slug", "")
    template_id = metadata.get("template_id")
    original_price = int(metadata.get("original_price", 0))
    discount_percent = int(metadata.get("discount_percent", 0))
    
    logger.info(f"Processing template purchase for user {user.id}: {template_slug}")
    
    # Check if already purchased
    existing = db.query(PurchasedTemplate).filter(
        PurchasedTemplate.user_id == user.id,
        PurchasedTemplate.template_slug == template_slug,
    ).first()
    
    if existing:
        logger.info(f"Template already purchased: {template_slug} for user {user.id}")
        return
    
    # Record purchase
    purchase = PurchasedTemplate(
        user_id=user.id,
        template_slug=template_slug,
        template_id=int(template_id) if template_id else None,
        amount_paid=session.get("amount_total", 0),
        original_price=original_price,
        discount_percent=discount_percent,
        stripe_session_id=session.get("id"),
        uses_remaining=-1,  # Unlimited uses
    )
    db.add(purchase)
    
    # Record transaction
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.UNLOCK,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=session.get("amount_total", 0),
        currency=session.get("currency", "usd"),
        metadata_json=json.dumps({
            "type": "template_purchase",
            "template_slug": template_slug,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "session_id": session.get("id"),
        }),
    )
    db.add(tx)
    db.commit()
    
    logger.info(f"Template purchase completed: {template_slug} for user {user.id} (${session.get('amount_total', 0)/100:.2f}, {discount_percent}% discount)")


def _handle_studio_report_purchase(session: dict, db: Session):
    """Handle studio report purchase - records purchase and queues report generation.
    
    Note: Report generation is deferred to success page load to keep webhook fast.
    This function only records the transaction and sets up the pending report.
    """
    from app.models.generated_report import GeneratedReport, ReportStatus, ReportType as GenReportType
    
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    guest_email = metadata.get("guest_email")
    report_type_raw = metadata.get("report_type", "")
    report_context_str = metadata.get("report_context", "{}")
    
    # Normalize report type (hyphen to underscore)
    report_type = report_type_raw.replace("-", "_")
    
    try:
        report_context = json.loads(report_context_str) if report_context_str else {}
    except:
        report_context = {}
    
    logger.info(f"Processing studio report purchase: {report_type}, user_id: {user_id}, guest_email: {guest_email}")
    
    # Determine the email to send results to
    recipient_email = guest_email
    if user_id:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            recipient_email = user.email
    
    if not recipient_email:
        logger.warning(f"No email available for studio report delivery - will use session email")
        recipient_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
    
    # Map report type string to enum (handle various naming conventions)
    report_type_map = {
        "market_analysis": GenReportType.MARKET_ANALYSIS,
        "strategic_assessment": GenReportType.STRATEGIC_ASSESSMENT,
        "strategic": GenReportType.STRATEGIC,
        "pestle_analysis": GenReportType.PESTLE_ANALYSIS,
        "pestle": GenReportType.PESTLE,
        "business_plan": GenReportType.BUSINESS_PLAN,
        "financial_model": GenReportType.FINANCIAL_MODEL,
        "financial": GenReportType.FINANCIAL,
        "financials": GenReportType.FINANCIAL,
        "pitch_deck": GenReportType.PITCH_DECK,
        "feasibility": GenReportType.FEASIBILITY,
        "feasibility_study": GenReportType.FEASIBILITY_STUDY,
        "location_analysis": GenReportType.LOCATION_ANALYSIS,
    }
    gen_report_type = report_type_map.get(report_type, GenReportType.MARKET_ANALYSIS)
    
    # Create a pending generated report record
    # For guest purchases, user_id can be None - the model should allow this
    # Store guest email and report context in summary for retrieval
    report_metadata = {
        "guest_email": guest_email,
        "report_context": report_context,
        "stripe_session_id": session.get("id"),
        "payment_intent": session.get("payment_intent"),
    }
    
    generated_report = GeneratedReport(
        user_id=int(user_id) if user_id else None,
        report_type=gen_report_type,
        status=ReportStatus.PENDING,
        title=f"{report_type.replace('_', ' ').title()} Report",
        summary=json.dumps(report_metadata),
    )
    db.add(generated_report)
    db.flush()  # Assign ID without committing
    report_id = generated_report.id
    
    # Record transaction (atomic with report creation)
    tx = Transaction(
        user_id=int(user_id) if user_id else None,
        type=TransactionType.UNLOCK,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=session.get("amount_total", 0),
        currency=session.get("currency", "usd"),
        metadata_json=json.dumps({
            "type": "studio_report_purchase",
            "report_type": report_type,
            "report_id": report_id,
            "guest_email": guest_email,
            "session_id": session.get("id"),
        }),
    )
    db.add(tx)
    db.commit()  # Single atomic commit for both report and transaction
    
    logger.info(f"Studio report purchase recorded: report_id={report_id}, amount={session.get('amount_total', 0)}")


def _handle_subscription_checkout(session: dict, user: User, db: Session):
    """Handle subscription checkout completion.
    
    This only links the Stripe subscription/customer IDs to the user record.
    Actual activation happens via customer.subscription.updated webhook when
    Stripe confirms the subscription is active.
    """
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    tier = session.get("metadata", {}).get("tier")
    payment_status = session.get("payment_status", "")
    
    logger.info(f"Checkout completed for user {user.id}, subscription {subscription_id}, payment_status: {payment_status}")
    
    subscription = usage_service.get_or_create_subscription(user, db)
    subscription.stripe_subscription_id = subscription_id
    subscription.stripe_customer_id = customer_id
    
    # Store the tier to be applied once subscription is confirmed active by Stripe
    if tier:
        try:
            # Validate tier exists
            SubscriptionTier(tier)
            subscription.metadata_json = json.dumps({"pending_tier": tier})
        except (ValueError, KeyError):
            logger.warning(f"Invalid tier '{tier}' provided, will be set by price_id mapping instead")
    
    db.commit()
    logger.info(f"Linked Stripe subscription {subscription_id} to user {user.id}, awaiting subscription.updated for activation")


def handle_subscription_updated(stripe_subscription: dict, db: Session):
    """Handle subscription update from Stripe.
    
    This is the authoritative source for subscription status. Only activate
    subscriptions when Stripe confirms status is 'active' or 'trialing'.
    
    ALSO: Auto-creates user account if it doesn't exist (account creation on first payment).
    """
    subscription_id = stripe_subscription.get("id")
    customer_id = stripe_subscription.get("customer")
    status = stripe_subscription.get("status")
    cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)
    current_period_end = stripe_subscription.get("current_period_end")
    
    logger.info(f"Subscription updated: {subscription_id}, customer: {customer_id}, status: {status}")
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription and customer_id:
        logger.info(f"Subscription not found by ID, trying customer ID: {customer_id}")
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        if subscription:
            subscription.stripe_subscription_id = subscription_id
            logger.info(f"Linked subscription {subscription_id} to user {subscription.user_id} via customer ID")
    
    # If subscription still not found, try to auto-create account
    if not subscription:
        logger.info(f"Subscription {subscription_id} not found, attempting auto-account creation from Stripe")
        
        # Fetch customer data from Stripe to get email
        try:
            stripe = get_stripe_client()
            customer = stripe.Customer.retrieve(customer_id)
            customer_email = customer.get("email")
            customer_name = customer.get("name", "Subscriber")
            
            if not customer_email:
                logger.warning(f"No email found for Stripe customer {customer_id}, cannot auto-create account")
                return
            
            # Auto-create user account from Stripe customer data
            user = _auto_create_account_from_stripe(customer_id, {"email": customer_email, "name": customer_name}, db)
            if not user:
                logger.error(f"Failed to auto-create account for subscription {subscription_id}")
                return
            
            # Create subscription record linked to the new user
            subscription = Subscription(
                user_id=user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
            )
            db.add(subscription)
            db.flush()
            logger.info(f"Auto-created subscription record for user {user.id}, subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Failed to auto-create account from Stripe: {str(e)}")
            return
    
    if not subscription:
        logger.warning(f"Subscription {subscription_id} could not be created or found (customer: {customer_id})")
        return
    
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "unpaid": SubscriptionStatus.PAST_DUE,
        "incomplete": SubscriptionStatus.PAST_DUE,
        "incomplete_expired": SubscriptionStatus.CANCELED,
    }
    
    new_status = status_map.get(status)
    if new_status is None:
        logger.warning(f"Unknown subscription status '{status}', not updating")
        return
    
    old_status = subscription.status
    subscription.status = new_status
    subscription.cancel_at_period_end = cancel_at_period_end
    
    if current_period_end:
        subscription.current_period_end = datetime.fromtimestamp(current_period_end)
    
    price_id = None
    items = stripe_subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
    
    # Determine tier from price or pending metadata
    tier_changed = False
    if price_id:
        tier = _map_price_to_tier(price_id)
        if tier and subscription.tier != tier:
            subscription.tier = tier
            tier_changed = True
            logger.info(f"Subscription {subscription_id}: tier updated to {tier.value}")
    elif subscription.metadata_json and new_status == SubscriptionStatus.ACTIVE:
        try:
            meta = json.loads(subscription.metadata_json)
            pending_tier = meta.get("pending_tier")
            if pending_tier:
                tier = SubscriptionTier(pending_tier.upper())
                if subscription.tier != tier:
                    subscription.tier = tier
                    tier_changed = True
                subscription.metadata_json = None
                logger.info(f"Subscription {subscription_id}: tier activated to {tier.value} from pending")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to apply pending tier: {e}")
    
    db.commit()
    logger.info(
        f"Updated subscription {subscription_id}: {old_status} -> {new_status}"
        f"{f', tier: {subscription.tier.value}' if tier_changed else ''}"
    )


def handle_subscription_deleted(stripe_subscription: dict, db: Session):
    """Handle subscription cancellation from Stripe."""
    subscription_id = stripe_subscription.get("id")
    
    logger.info(f"Subscription deleted: {subscription_id}")
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        logger.warning(f"Subscription {subscription_id} not found in database")
        return
    
    subscription.tier = SubscriptionTier.FREE
    subscription.status = SubscriptionStatus.CANCELED
    subscription.stripe_subscription_id = None
    db.commit()
    logger.info(f"Canceled subscription for user {subscription.user_id}")


def handle_checkout_expired(checkout_session: dict, db: Session):
    """
    Handle expired checkout session.
    This is an informational event - the customer started checkout but didn't complete it.
    We log it for analytics purposes.
    """
    session_id = checkout_session.get("id")
    customer_email = checkout_session.get("customer_details", {}).get("email")
    metadata = checkout_session.get("metadata", {}) or {}
    tier = metadata.get("tier")
    user_id = metadata.get("user_id")
    
    logger.info(
        f"Checkout session expired: {session_id}, "
        f"customer: {customer_email}, tier: {tier}, user_id: {user_id}"
    )
    # No database action needed - this is purely informational
    # Could be used for abandoned cart analytics in the future


def _map_payment_type_to_transaction_type(payment_type: str) -> TransactionType | None:
    """Map metadata payment type to TransactionType enum."""
    mapping = {
        "micro_payment": TransactionType.MICRO_PAYMENT,
        "project_payment": TransactionType.PROJECT_PAYMENT,
        "pay_per_unlock": TransactionType.PAY_PER_UNLOCK,
        "success_fee": TransactionType.SUCCESS_FEE,
        "revenue_share": TransactionType.REVENUE_SHARE,
    }
    return mapping.get(payment_type)


def _map_price_to_tier(price_id: str) -> SubscriptionTier | None:
    """Map Stripe price ID to subscription tier.
    
    Supports all 6 subscription tiers:
    - Individual Track: Starter, Growth, Pro
    - Business Track: Team, Business, Enterprise
    """
    price_mappings = {
        os.getenv("STRIPE_PRICE_STARTER"): SubscriptionTier.STARTER,
        os.getenv("STRIPE_PRICE_GROWTH"): SubscriptionTier.GROWTH,
        os.getenv("STRIPE_PRICE_PRO"): SubscriptionTier.PRO,
        os.getenv("STRIPE_PRICE_TEAM"): SubscriptionTier.TEAM,
        os.getenv("STRIPE_PRICE_BUSINESS"): SubscriptionTier.BUSINESS,
        os.getenv("STRIPE_PRICE_ENTERPRISE"): SubscriptionTier.ENTERPRISE,
    }
    
    tier = price_mappings.get(price_id)
    if tier:
        logger.info(f"Mapped price {price_id} to tier {tier.value}")
    else:
        logger.warning(f"Unknown price ID: {price_id}, available mappings: {list(k for k in price_mappings.keys() if k)}")
    
    return tier


def _auto_create_account_from_stripe(customer_id: str, stripe_customer_data: dict, db: Session) -> User | None:
    """
    Auto-create a user account from Stripe customer data.
    
    Used when payment succeeds but user doesn't have an account yet.
    Extracts email and name from Stripe customer object.
    
    Args:
        customer_id: Stripe customer ID
        stripe_customer_data: Customer object from Stripe API or webhook
        db: Database session
        
    Returns:
        Created User object or None if account couldn't be created
    """
    
    email = stripe_customer_data.get("email") or stripe_customer_data.get("customer_email")
    name = stripe_customer_data.get("name") or stripe_customer_data.get("customer_name") or "Stripe User"
    
    # Validate email format
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        logger.warning(f"Invalid or missing email for customer {customer_id}: {email}")
        return None
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        logger.info(f"User {existing_user.id} already exists for email {email}")
        return existing_user
    
    try:
        # Create new user account with a placeholder password
        # User will need to set real password or use OAuth on first login
        user = User(
            email=email,
            name=name,
            hashed_password=generate_password_hash(""),  # No password initially
            is_active=True,
            is_verified=False,  # Mark as not email-verified yet
        )
        db.add(user)
        db.flush()  # Assign ID without committing
        user_id = user.id
        
        # Create free subscription tier by default
        # Will be upgraded when subscription is confirmed active
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            stripe_customer_id=customer_id,
        )
        db.add(subscription)
        db.commit()
        
        logger.info(f"Auto-created account user_id={user_id}, email={email} from Stripe customer {customer_id}")
        return user
        
    except IntegrityError:
        # Race condition: another process created this user simultaneously
        db.rollback()
        logger.info(f"User creation race condition, retrying query for {email}")
        return db.query(User).filter(User.email == email).first()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to auto-create account from Stripe: {str(e)}")
        return None


def _handle_subscription_upgrade_payment(payment_intent: dict, customer_id: str, db: Session):
    """
    Handle subscription tier upgrade from a direct payment intent.
    
    This occurs when a user pays for a tier upgrade outside the normal
    subscription flow (e.g., immediate upgrade without waiting for renewal).
    """
    metadata = payment_intent.get("metadata", {})
    new_tier = metadata.get("tier")
    payment_intent_id = payment_intent.get("id")
    
    if not new_tier or not customer_id:
        logger.warning(f"Missing tier or customer_id for subscription upgrade")
        return
    
    logger.info(f"Processing subscription upgrade: customer {customer_id} -> tier {new_tier}")
    
    # Find subscription by customer ID
    subscription = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    
    if not subscription:
        logger.warning(f"Subscription not found for customer {customer_id}")
        # Try to auto-create account from Stripe
        try:
            stripe = get_stripe_client()
            customer = stripe.Customer.retrieve(customer_id)
            user = _auto_create_account_from_stripe(customer_id, customer, db)
            if user:
                subscription = usage_service.get_or_create_subscription(user, db)
                subscription.stripe_customer_id = customer_id
        except Exception as e:
            logger.error(f"Failed to create subscription from customer {customer_id}: {str(e)}")
            return
    
    if not subscription:
        logger.error(f"Could not find or create subscription for customer {customer_id}")
        return
    
    # Upgrade the tier
    try:
        old_tier = subscription.tier
        subscription.tier = SubscriptionTier(new_tier.upper())
        subscription.metadata_json = json.dumps({
            "upgraded_at": datetime.utcnow().isoformat(),
            "upgrade_payment_intent": payment_intent_id,
        })
        db.commit()
        logger.info(f"Subscription {subscription.id}: tier upgraded from {old_tier.value} to {subscription.tier.value}")
    except ValueError as e:
        logger.error(f"Invalid tier '{new_tier}': {str(e)}")


def _fulfill_pay_per_unlock(payment_intent: dict, metadata: dict, db: Session):
    """Fulfill pay-per-unlock after successful payment."""
    user_id = metadata.get("user_id")
    opportunity_id = metadata.get("opportunity_id")
    payment_intent_id = payment_intent.get("id")
    
    if not user_id or not opportunity_id:
        logger.warning("Missing user_id or opportunity_id for pay_per_unlock fulfillment")
        return
    
    existing = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.stripe_payment_intent_id == payment_intent_id
    ).first()
    
    if existing:
        logger.info(f"Opportunity already unlocked with payment {payment_intent_id}")
        return
    
    now = datetime.utcnow()
    expires_at = now + timedelta(days=30)
    
    unlock = UnlockedOpportunity(
        user_id=int(user_id),
        opportunity_id=int(opportunity_id),
        unlock_method=UnlockMethod.PAY_PER_UNLOCK,
        amount_paid=payment_intent.get("amount"),
        stripe_payment_intent_id=payment_intent_id,
        expires_at=expires_at
    )
    db.add(unlock)
    db.commit()
    logger.info(f"Fulfilled pay-per-unlock for user {user_id}, opportunity {opportunity_id}")

    attempt = db.query(PayPerUnlockAttempt).filter(
        PayPerUnlockAttempt.stripe_payment_intent_id == payment_intent_id
    ).first()
    if attempt:
        attempt.status = PayPerUnlockAttemptStatus.SUCCEEDED
        db.commit()


def _fulfill_micro_payment(payment_intent: dict, metadata: dict, db: Session):
    """Fulfill micro-payment (expert quick service)."""
    logger.info(f"Micro-payment fulfilled: {payment_intent.get('id')}")


def _fulfill_project_payment(payment_intent: dict, metadata: dict, db: Session):
    """Fulfill project payment (larger expert engagement)."""
    logger.info(f"Project payment fulfilled: {payment_intent.get('id')}")


def _fulfill_idea_validation(payment_intent: dict, metadata: dict, db: Session):
    """Mark an IdeaValidation record as paid (idempotent)."""
    validation_id = metadata.get("idea_validation_id")
    payment_intent_id = payment_intent.get("id")
    if not validation_id or not payment_intent_id:
        return
    row = db.query(IdeaValidation).filter(IdeaValidation.id == int(validation_id)).first()
    if not row:
        return
    if row.stripe_payment_intent_id and row.stripe_payment_intent_id != payment_intent_id:
        return
    if row.status in (IdeaValidationStatus.PAID, IdeaValidationStatus.PROCESSING, IdeaValidationStatus.COMPLETED):
        return
    row.status = IdeaValidationStatus.PAID
    row.stripe_payment_intent_id = payment_intent_id
    row.amount_cents = payment_intent.get("amount") or row.amount_cents
    row.currency = payment_intent.get("currency") or row.currency
    db.commit()


def _fail_idea_validation(payment_intent: dict, metadata: dict, db: Session):
    """Mark an IdeaValidation record as failed when payment fails."""
    validation_id = metadata.get("idea_validation_id")
    payment_intent_id = payment_intent.get("id")
    if not validation_id or not payment_intent_id:
        return
    row = db.query(IdeaValidation).filter(IdeaValidation.id == int(validation_id)).first()
    if not row:
        return
    if row.stripe_payment_intent_id and row.stripe_payment_intent_id != payment_intent_id:
        return
    if row.status in (IdeaValidationStatus.COMPLETED,):
        return
    row.status = IdeaValidationStatus.FAILED
    row.error_message = "payment_failed"
    db.commit()


def _fulfill_deep_dive(payment_intent: dict, metadata: dict, db: Session):
    """Fulfill Deep Dive ($49) - add Layer 2 access to opportunity."""
    user_id = metadata.get("user_id")
    opportunity_id = metadata.get("opportunity_id")
    payment_intent_id = payment_intent.get("id")
    
    if not user_id or not opportunity_id:
        logger.warning("Missing user_id or opportunity_id for deep_dive fulfillment")
        return
    
    unlock = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.user_id == int(user_id),
        UnlockedOpportunity.opportunity_id == int(opportunity_id)
    ).first()
    
    if unlock:
        if unlock.has_deep_dive:
            logger.info(f"Deep Dive already unlocked for user {user_id}, opportunity {opportunity_id}")
            return
        unlock.has_deep_dive = True
        unlock.deep_dive_payment_intent_id = payment_intent_id
        unlock.deep_dive_unlocked_at = datetime.utcnow()
    else:
        unlock = UnlockedOpportunity(
            user_id=int(user_id),
            opportunity_id=int(opportunity_id),
            unlock_method=UnlockMethod.DEEP_DIVE,
            amount_paid=payment_intent.get("amount"),
            stripe_payment_intent_id=payment_intent_id,
            has_deep_dive=True,
            deep_dive_payment_intent_id=payment_intent_id,
            deep_dive_unlocked_at=datetime.utcnow()
        )
        db.add(unlock)
    
    db.commit()
    logger.info(f"Fulfilled Deep Dive for user {user_id}, opportunity {opportunity_id}")


def _fulfill_fast_pass(payment_intent: dict, metadata: dict, db: Session):
    """Fulfill Fast Pass ($99) - unlock HOT opportunity for Business tier."""
    user_id = metadata.get("user_id")
    opportunity_id = metadata.get("opportunity_id")
    payment_intent_id = payment_intent.get("id")
    
    if not user_id or not opportunity_id:
        logger.warning("Missing user_id or opportunity_id for fast_pass fulfillment")
        return
    
    existing = db.query(UnlockedOpportunity).filter(
        UnlockedOpportunity.user_id == int(user_id),
        UnlockedOpportunity.opportunity_id == int(opportunity_id)
    ).first()
    
    if existing:
        logger.info(f"Opportunity already unlocked for user {user_id}, opportunity {opportunity_id}")
        return
    
    now = datetime.utcnow()
    expires_at = now + timedelta(days=30)
    
    unlock = UnlockedOpportunity(
        user_id=int(user_id),
        opportunity_id=int(opportunity_id),
        unlock_method=UnlockMethod.FAST_PASS,
        amount_paid=payment_intent.get("amount"),
        stripe_payment_intent_id=payment_intent_id,
        expires_at=expires_at,
        has_deep_dive=True
    )
    db.add(unlock)
    db.commit()
    logger.info(f"Fulfilled Fast Pass for user {user_id}, opportunity {opportunity_id}")
