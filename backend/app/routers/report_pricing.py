"""
Report Pricing Router
Endpoints for report pricing, purchases, and access checks
"""

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.db.database import get_db


def validate_redirect_url(url: str, request: Request) -> bool:
    """Validate that redirect URLs are from trusted origins to prevent open redirect attacks."""
    if not url:
        return False
    
    parsed = urlparse(url)
    
    allowed_hosts = [
        request.headers.get("host", "").split(":")[0],
        "localhost",
        "127.0.0.1",
    ]
    
    replit_domain = os.getenv("REPLIT_DOMAINS", "").split(",")
    allowed_hosts.extend([d.strip() for d in replit_domain if d.strip()])
    
    if os.getenv("REPLIT_DEPLOYMENT"):
        allowed_hosts.append(f"{os.getenv('REPL_SLUG', '')}.{os.getenv('REPL_OWNER', '')}.repl.co")
    
    return parsed.netloc.split(":")[0] in allowed_hosts or parsed.netloc == ""


from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.purchased_report import PurchasedReport, PurchasedBundle, ConsultantLicense, PurchaseType, GuestReportPurchase, PurchasedTemplate
from app.models.report_template import ReportTemplate
from app.core.dependencies import get_current_user, get_current_active_user, get_current_user_optional
from app.core.report_pricing import (
    REPORT_PRODUCTS,
    BUNDLES,
    ReportProductType,
    BundleType,
    get_pricing_summary,
    is_report_included_for_tier,
    get_report_price,
    get_bundle_price,
    get_tier_report_discount,
    calculate_discounted_price,
)
from app.services.stripe_service import stripe_service, get_stripe_client
from app.services.usage_service import usage_service
from app.services.entitlements import get_opportunity_entitlements
from app.services.audit import log_event
from app.services.report_usage_service import report_usage_service

router = APIRouter(prefix="/report-pricing", tags=["Report Pricing"])


class PublicPricingResponse(BaseModel):
    """Public pricing data - no auth required"""
    reports: List[dict]
    bundles: List[dict]
    subscription_tiers: List[dict]


class ReportPricingResponse(BaseModel):
    reports: List[dict]
    bundles: List[dict]
    user_tier: Optional[str] = None
    purchased_reports: List[dict] = []
    has_consultant_license: bool = False


class ReportPurchaseRequest(BaseModel):
    opportunity_id: int
    report_type: str


class BundlePurchaseRequest(BaseModel):
    opportunity_id: int
    bundle_type: str


class PurchaseResponse(BaseModel):
    client_secret: str
    amount: int
    publishable_key: str


class ConfirmPurchaseRequest(BaseModel):
    payment_intent_id: str


SUBSCRIPTION_TIERS = [
    {
        "id": "explorer",
        "name": "Explorer",
        "price_cents": 0,
        "price_label": "Free",
        "description": "Try quality, pay for what you need",
        "access_window_days": 91,
        "features": [
            "Browse validated opportunities",
            "Layer 1 access (91+ days)",
            "FREE Feasibility Study per opportunity",
            "Pay-per-report execution tools",
        ],
    },
    {
        "id": "builder",
        "name": "Builder",
        "price_cents": 9900,
        "price_label": "$99/mo",
        "description": "Unlimited research, professional execution",
        "access_window_days": 31,
        "features": [
            "Layer 1 + 2 access (31+ days)",
            "Unlimited Layer 1 reports",
            "10 Layer 2 reports/month",
            "All Explorer features",
        ],
        "is_popular": True,
    },
    {
        "id": "scaler",
        "name": "Scaler",
        "price_cents": 49900,
        "price_label": "$499/mo",
        "description": "Move faster with deep intelligence",
        "access_window_days": 8,
        "features": [
            "Full Layer 1-3 access (8+ days)",
            "Unlimited Layer 1-2 reports",
            "5 Layer 3 execution packages/month",
            "Priority AI processing",
        ],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_cents": 250000,
        "price_label": "$2,500+/mo",
        "description": "First-mover advantage + unlimited execution",
        "access_window_days": 0,
        "features": [
            "Real-time opportunity access (0+ days)",
            "Unlimited all layers",
            "API access",
            "Dedicated support",
        ],
    },
]


@router.get("/public", response_model=PublicPricingResponse)
def get_public_pricing():
    """Get public pricing data - no authentication required"""
    pricing = get_pricing_summary()
    
    reports_with_details = []
    consultant_prices = {
        "feasibility_study": "$1,500-$15,000",
        "business_plan": "$3,000-$15,000",
        "financial_model": "$2,500-$10,000",
        "market_analysis": "$2,000-$8,000",
        "strategic_assessment": "$1,500-$5,000",
        "pestle_analysis": "$1,500-$5,000",
        "pitch_deck": "$2,000-$5,000",
    }
    
    for report in pricing["reports"]:
        report["consultant_price"] = consultant_prices.get(report["id"], "$1,500-$5,000")
        report["user_price"] = report["price"]
        report["is_included"] = False
        reports_with_details.append(report)
    
    bundles_with_details = []
    bundle_consultant_values = {
        "starter": "$8,500-$35,000",
        "professional": "$17,000-$98,000",
        "consultant_license": "$50,000-$250,000",
    }
    
    for bundle in pricing["bundles"]:
        bundle["consultant_value"] = bundle_consultant_values.get(bundle["id"], "$10,000+")
        bundles_with_details.append(bundle)
    
    return PublicPricingResponse(
        reports=reports_with_details,
        bundles=bundles_with_details,
        subscription_tiers=SUBSCRIPTION_TIERS,
    )


@router.get("/", response_model=ReportPricingResponse)
def get_report_pricing(
    opportunity_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get report pricing, user's tier, and purchased reports for opportunity"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    
    pricing = get_pricing_summary()
    
    for report in pricing["reports"]:
        report["is_included"] = is_report_included_for_tier(report["id"], user_tier)
        if report["is_included"]:
            report["user_price"] = 0
        else:
            report["user_price"] = report["price"]
    
    for bundle in pricing["bundles"]:
        bundle["is_available"] = True
    
    purchased_reports = []
    if opportunity_id:
        purchases = db.query(PurchasedReport).filter(
            PurchasedReport.user_id == current_user.id,
            PurchasedReport.opportunity_id == opportunity_id
        ).all()
        purchased_reports = [
            {
                "report_type": p.report_type,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
                "is_generated": p.is_generated,
            }
            for p in purchases
        ]
    
    has_consultant_license = db.query(ConsultantLicense).filter(
        ConsultantLicense.user_id == current_user.id,
        ConsultantLicense.is_active == True
    ).first() is not None
    
    return ReportPricingResponse(
        reports=pricing["reports"],
        bundles=pricing["bundles"],
        user_tier=user_tier,
        purchased_reports=purchased_reports,
        has_consultant_license=has_consultant_license,
    )


@router.get("/check-access/{opportunity_id}")
def check_report_access(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if user has Layer 1 access to opportunity (required for report purchase)"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    
    return {
        "opportunity_id": opportunity_id,
        "has_layer1_access": ent.is_accessible,
        "user_tier": ent.user_tier.value if ent.user_tier else "free",
        "can_purchase_reports": ent.is_accessible,
        "message": "Layer 1 access required to purchase reports" if not ent.is_accessible else "Ready to purchase reports"
    }


@router.post("/purchase-report", response_model=PurchaseResponse)
def create_report_purchase(
    purchase_data: ReportPurchaseRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a payment intent for report purchase"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == purchase_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    if not ent.is_accessible:
        raise HTTPException(
            status_code=403, 
            detail="Layer 1 access required. Unlock this opportunity first or upgrade your subscription."
        )
    
    if purchase_data.report_type not in REPORT_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {purchase_data.report_type}")
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    
    if is_report_included_for_tier(purchase_data.report_type, user_tier):
        raise HTTPException(
            status_code=400, 
            detail=f"This report is included in your {user_tier} subscription. No purchase needed."
        )
    
    existing = db.query(PurchasedReport).filter(
        PurchasedReport.user_id == current_user.id,
        PurchasedReport.opportunity_id == purchase_data.opportunity_id,
        PurchasedReport.report_type == purchase_data.report_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this report for this opportunity")
    
    amount_cents = get_report_price(purchase_data.report_type)
    report_product = REPORT_PRODUCTS[purchase_data.report_type]
    
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()
    
    stripe_client = get_stripe_client()
    payment_intent = stripe_client.payment_intents.create(
        amount=amount_cents,
        currency="usd",
        customer=subscription.stripe_customer_id,
        metadata={
            "user_id": str(current_user.id),
            "opportunity_id": str(purchase_data.opportunity_id),
            "report_type": purchase_data.report_type,
            "payment_type": "report_purchase",
        },
        description=f"OppGrid Report: {report_product.name} for Opportunity #{purchase_data.opportunity_id}",
        automatic_payment_methods={"enabled": True},
    )
    
    log_event(
        db,
        action="report_pricing.purchase_intent_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=purchase_data.opportunity_id,
        metadata={
            "payment_intent_id": payment_intent.id,
            "report_type": purchase_data.report_type,
            "amount_cents": amount_cents,
        },
    )
    
    from app.services.stripe_service import get_stripe_credentials
    _, publishable_key = get_stripe_credentials()
    
    return PurchaseResponse(
        client_secret=payment_intent.client_secret,
        amount=amount_cents,
        publishable_key=publishable_key,
    )


class ReportCheckoutRequest(BaseModel):
    opportunity_id: int
    report_type: str
    success_url: str
    cancel_url: str


class BundleCheckoutRequest(BaseModel):
    opportunity_id: int
    bundle_type: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


@router.post("/checkout-report", response_model=CheckoutResponse)
def create_report_checkout(
    checkout_data: ReportCheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for report purchase"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == checkout_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    if not ent.is_accessible:
        raise HTTPException(
            status_code=403, 
            detail="Layer 1 access required. Unlock this opportunity first or upgrade your subscription."
        )
    
    if checkout_data.report_type not in REPORT_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {checkout_data.report_type}")
    
    existing = db.query(PurchasedReport).filter(
        PurchasedReport.user_id == current_user.id,
        PurchasedReport.opportunity_id == checkout_data.opportunity_id,
        PurchasedReport.report_type == checkout_data.report_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this report for this opportunity")
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    report_product = REPORT_PRODUCTS[checkout_data.report_type]
    
    if is_report_included_for_tier(checkout_data.report_type, subscription.tier):
        raise HTTPException(status_code=400, detail="This report is included with your subscription. No purchase needed.")
    
    amount_cents = get_report_price(checkout_data.report_type, subscription.tier)
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Invalid price for this report")
    
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    stripe_client = get_stripe_client()
    
    session = stripe_client.checkout.Session.create(
        customer=subscription.stripe_customer_id,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid Report: {report_product.name}",
                    "description": f"AI-generated {report_product.name} for opportunity #{checkout_data.opportunity_id}",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "user_id": str(current_user.id),
            "opportunity_id": str(checkout_data.opportunity_id),
            "report_type": checkout_data.report_type,
            "payment_type": "report_purchase",
        },
    )
    
    log_event(
        db,
        action="report_pricing.checkout_session_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=checkout_data.opportunity_id,
        metadata={
            "session_id": session.id,
            "report_type": checkout_data.report_type,
            "amount_cents": amount_cents,
        },
    )
    
    return CheckoutResponse(session_id=session.id, url=session.url)


@router.post("/checkout-bundle", response_model=CheckoutResponse)
def create_bundle_checkout(
    checkout_data: BundleCheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for bundle purchase"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == checkout_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    if not ent.is_accessible:
        raise HTTPException(
            status_code=403, 
            detail="Layer 1 access required. Unlock this opportunity first or upgrade your subscription."
        )
    
    if checkout_data.bundle_type not in BUNDLES:
        raise HTTPException(status_code=400, detail=f"Invalid bundle type: {checkout_data.bundle_type}")
    
    existing = db.query(PurchasedBundle).filter(
        PurchasedBundle.user_id == current_user.id,
        PurchasedBundle.opportunity_id == checkout_data.opportunity_id,
        PurchasedBundle.bundle_type == checkout_data.bundle_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this bundle for this opportunity")
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    bundle = BUNDLES[checkout_data.bundle_type]
    
    amount_cents = get_bundle_price(checkout_data.bundle_type, subscription.tier)
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Invalid price for this bundle")
    
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    stripe_client = get_stripe_client()
    
    session = stripe_client.checkout.Session.create(
        customer=subscription.stripe_customer_id,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid Bundle: {bundle.name}",
                    "description": f"Includes: {', '.join(bundle.reports)}",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "user_id": str(current_user.id),
            "opportunity_id": str(checkout_data.opportunity_id),
            "bundle_type": checkout_data.bundle_type,
            "payment_type": "bundle_purchase",
            "reports": ",".join(bundle.reports),
        },
    )
    
    log_event(
        db,
        action="report_pricing.bundle_checkout_session_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=checkout_data.opportunity_id,
        metadata={
            "session_id": session.id,
            "bundle_type": checkout_data.bundle_type,
            "amount_cents": amount_cents,
        },
    )
    
    return CheckoutResponse(session_id=session.id, url=session.url)


class GuestCheckoutRequest(BaseModel):
    opportunity_id: int
    report_type: str
    email: str
    success_url: str
    cancel_url: str


class GuestBundleCheckoutRequest(BaseModel):
    opportunity_id: int
    bundle_type: str
    email: str
    success_url: str
    cancel_url: str


@router.post("/guest-checkout-report", response_model=CheckoutResponse)
def create_guest_report_checkout(
    checkout_data: GuestCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for guest report purchase (no auth required)"""
    import secrets
    import re
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, checkout_data.email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == checkout_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    if checkout_data.report_type not in REPORT_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {checkout_data.report_type}")
    
    report_product = REPORT_PRODUCTS[checkout_data.report_type]
    amount_cents = report_product.price_cents
    
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    access_token = secrets.token_urlsafe(32)
    
    stripe_client = get_stripe_client()
    
    session = stripe_client.checkout.Session.create(
        customer_email=checkout_data.email,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid Report: {report_product.name}",
                    "description": f"AI-generated {report_product.name} for opportunity #{checkout_data.opportunity_id}",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "guest_email": checkout_data.email,
            "opportunity_id": str(checkout_data.opportunity_id),
            "report_type": checkout_data.report_type,
            "payment_type": "guest_report_purchase",
            "access_token": access_token,
        },
    )
    
    log_event(
        db,
        action="report_pricing.guest_checkout_session_created",
        actor=None,
        actor_type="guest",
        request=request,
        resource_type="opportunity",
        resource_id=checkout_data.opportunity_id,
        metadata={
            "session_id": session.id,
            "report_type": checkout_data.report_type,
            "amount_cents": amount_cents,
            "guest_email": checkout_data.email[:3] + "***",
        },
    )
    
    return CheckoutResponse(session_id=session.id, url=session.url)


@router.post("/guest-checkout-bundle", response_model=CheckoutResponse)
def create_guest_bundle_checkout(
    checkout_data: GuestBundleCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for guest bundle purchase (no auth required)"""
    import secrets
    import re
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, checkout_data.email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == checkout_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    if checkout_data.bundle_type not in BUNDLES:
        raise HTTPException(status_code=400, detail=f"Invalid bundle type: {checkout_data.bundle_type}")
    
    bundle = BUNDLES[checkout_data.bundle_type]
    amount_cents = bundle.price_cents
    
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    access_token = secrets.token_urlsafe(32)
    
    stripe_client = get_stripe_client()
    
    session = stripe_client.checkout.Session.create(
        customer_email=checkout_data.email,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid Bundle: {bundle.name}",
                    "description": f"Includes: {', '.join(bundle.reports)}",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "guest_email": checkout_data.email,
            "opportunity_id": str(checkout_data.opportunity_id),
            "bundle_type": checkout_data.bundle_type,
            "payment_type": "guest_bundle_purchase",
            "reports": ",".join(bundle.reports),
            "access_token": access_token,
        },
    )
    
    log_event(
        db,
        action="report_pricing.guest_bundle_checkout_session_created",
        actor=None,
        actor_type="guest",
        request=request,
        resource_type="opportunity",
        resource_id=checkout_data.opportunity_id,
        metadata={
            "session_id": session.id,
            "bundle_type": checkout_data.bundle_type,
            "amount_cents": amount_cents,
            "guest_email": checkout_data.email[:3] + "***",
        },
    )
    
    return CheckoutResponse(session_id=session.id, url=session.url)


class StudioReportCheckoutRequest(BaseModel):
    """Request for standalone studio report checkout (no opportunity required)"""
    report_type: str  # market_analysis, strategic_assessment, pestle_analysis, business_plan, financial_model, pitch_deck
    success_url: str
    cancel_url: str
    email: Optional[str] = None  # Required for guest purchases
    report_context: Optional[dict] = None  # User-provided context for report generation


STUDIO_REPORT_PRICES = {
    "market_analysis": {"name": "Market Analysis", "price_cents": 9900},
    "strategic_assessment": {"name": "Strategic Assessment", "price_cents": 8900},
    "pestle_analysis": {"name": "PESTLE Analysis", "price_cents": 9900},
    "business_plan": {"name": "Business Plan", "price_cents": 14900},
    "financial_model": {"name": "Financial Model", "price_cents": 12900},
    "pitch_deck": {"name": "Pitch Deck", "price_cents": 7900},
    "competitive_analysis": {"name": "Competitive Analysis", "price_cents": 14900},
    "pricing_strategy": {"name": "Pricing Strategy", "price_cents": 13900},
    "ad_creatives": {"name": "Ad Creatives", "price_cents": 7900},
    "brand_package": {"name": "Brand Package", "price_cents": 14900},
    "landing_page": {"name": "Landing Page", "price_cents": 9900},
    "content_calendar": {"name": "Content Calendar", "price_cents": 12900},
    "email_funnel": {"name": "Email Funnel System", "price_cents": 17900},
    "email_sequence": {"name": "Email Sequence", "price_cents": 7900},
    "lead_magnet": {"name": "Lead Magnet", "price_cents": 8900},
    "sales_funnel": {"name": "Sales Funnel", "price_cents": 14900},
    "seo_content": {"name": "SEO Content", "price_cents": 12900},
    "feature_specs": {"name": "Feature Specs", "price_cents": 14900},
    "mvp_roadmap": {"name": "MVP Roadmap", "price_cents": 17900},
    "prd": {"name": "Product Requirements Doc", "price_cents": 16900},
    "gtm_strategy": {"name": "GTM Strategy", "price_cents": 18900},
    "gtm_calendar": {"name": "GTM Launch Calendar", "price_cents": 15900},
    "kpi_dashboard": {"name": "KPI Dashboard", "price_cents": 11900},
    "user_personas": {"name": "User Personas", "price_cents": 9900},
    "customer_interview": {"name": "Customer Interview Guide", "price_cents": 8900},
    "tweet_landing": {"name": "Tweet Landing Page", "price_cents": 4900},
    "feasibility_study": {"name": "Feasibility Study", "price_cents": 2500},
    "location_analysis": {"name": "Location Analysis Report", "price_cents": 11900},
}


@router.post("/studio-report-checkout", response_model=CheckoutResponse)
async def create_studio_report_checkout(
    checkout_data: StudioReportCheckoutRequest,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for standalone studio report purchase (supports guest purchases)"""
    if checkout_data.report_type not in STUDIO_REPORT_PRICES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid report type: {checkout_data.report_type}. Valid types: {list(STUDIO_REPORT_PRICES.keys())}"
        )
    
    # Guest purchases require email
    if not current_user and not checkout_data.email:
        raise HTTPException(status_code=400, detail="Email is required for guest purchases")
    
    report_info = STUDIO_REPORT_PRICES[checkout_data.report_type]
    amount_cents = report_info["price_cents"]
    
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    stripe_client = get_stripe_client()
    
    # Build metadata based on whether user is authenticated
    metadata = {
        "report_type": checkout_data.report_type,
        "payment_type": "studio_report_purchase",
    }
    if current_user:
        metadata["user_id"] = str(current_user.id)
    if checkout_data.email:
        metadata["guest_email"] = checkout_data.email
    if checkout_data.report_context:
        import json
        metadata["report_context"] = json.dumps(checkout_data.report_context)[:500]
    
    session_params = {
        "payment_method_types": ["card"],
        "line_items": [{
            "price_data": {
                "currency": "usd",
                "unit_amount": amount_cents,
                "product_data": {
                    "name": f"OppGrid {report_info['name']}",
                    "description": f"AI-generated {report_info['name']} report",
                },
            },
            "quantity": 1,
        }],
        "mode": "payment",
        "success_url": checkout_data.success_url,
        "cancel_url": checkout_data.cancel_url,
        "metadata": metadata,
    }
    
    # Pre-fill email: use authenticated user's email or provided guest email
    prefill_email = (current_user.email if current_user else None) or checkout_data.email
    if prefill_email:
        session_params["customer_email"] = prefill_email
    
    session = stripe_client.checkout.Session.create(**session_params)
    
    log_event(
        db,
        action="report_pricing.studio_checkout_session_created",
        actor=current_user,
        actor_type="user" if current_user else "guest",
        request=request,
        resource_type="studio_report",
        resource_id=None,
        metadata={
            "session_id": session.id,
            "report_type": checkout_data.report_type,
            "amount_cents": amount_cents,
            "is_guest": current_user is None,
        },
    )
    
    return CheckoutResponse(session_id=session.id, url=session.url)


class TriggerReportRequest(BaseModel):
    """Request to trigger generation for a pending report"""
    session_id: Optional[str] = None
    payment_intent: Optional[str] = None


class TriggerReportResponse(BaseModel):
    """Response from triggering report generation"""
    report_id: Optional[int] = None
    status: str
    message: str


@router.post("/trigger-report-generation", response_model=TriggerReportResponse)
async def trigger_report_generation(
    trigger_data: TriggerReportRequest,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Trigger generation for a pending studio report after successful payment.
    
    Called from the success page after Stripe checkout completes.
    Finds the pending report and starts AI generation.
    """
    from app.models.generated_report import GeneratedReport, ReportStatus
    from app.services.ai_report_generator import AIReportGenerator
    from app.services.email_service import email_service
    
    # Find the pending report by session_id or payment_intent stored in summary
    query = db.query(GeneratedReport).filter(
        GeneratedReport.status == ReportStatus.PENDING
    )
    
    pending_report = None
    if trigger_data.session_id:
        all_pending = query.all()
        for report in all_pending:
            try:
                summary = json.loads(report.summary) if report.summary else {}
                if summary.get("stripe_session_id") == trigger_data.session_id:
                    pending_report = report
                    break
            except:
                continue
    
    if not pending_report and trigger_data.payment_intent:
        all_pending = query.all()
        for report in all_pending:
            try:
                summary = json.loads(report.summary) if report.summary else {}
                if summary.get("payment_intent") == trigger_data.payment_intent:
                    pending_report = report
                    break
            except:
                continue
    
    if not pending_report:
        return TriggerReportResponse(
            status="not_found",
            message="No pending report found for this payment"
        )
    
    # Mark as generating
    pending_report.status = ReportStatus.GENERATING
    db.commit()
    
    # Extract context from summary
    try:
        report_metadata = json.loads(pending_report.summary) if pending_report.summary else {}
    except:
        report_metadata = {}
    
    report_context = report_metadata.get("report_context", {})
    guest_email = report_metadata.get("guest_email")
    report_type = pending_report.report_type.value
    
    # Determine recipient email
    recipient_email = guest_email
    if pending_report.user_id:
        user = db.query(User).filter(User.id == pending_report.user_id).first()
        if user:
            recipient_email = user.email
    
    # Generate the report
    try:
        # Parse city and state from location
        location = report_context.get("location", "")
        city, state = "", ""
        if "," in location:
            parts = location.split(",")
            city = parts[0].strip()
            state = parts[1].strip() if len(parts) > 1 else ""
        else:
            city = location

        from app.services.report_orchestrator import ReportOrchestrator
        orchestrator = ReportOrchestrator()
        report_content = await orchestrator.generate(
            report_type=report_type,
            business_type=report_context.get("businessConcept", "Business Opportunity"),
            city=city,
            state=state,
            db=db,
            user_notes=report_context.get("businessConcept", ""),
            category=report_context.get("category"),
            target_audience=report_context.get("targetMarket"),
        )
        
        # Update report
        pending_report.status = ReportStatus.COMPLETED
        pending_report.content = report_content
        pending_report.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send email if we have a recipient
        if recipient_email:
            try:
                from app.routers.reports import generate_report_view_token
                report_name = report_type.replace("_", " ").title()
                view_token = generate_report_view_token(pending_report.id)
                base_url = os.getenv("APP_BASE_URL", "https://oppgrid.replit.app")
                view_url = f"{base_url}/reports/view/{pending_report.id}?token={view_token}"
                email_service.send_email(
                    to_email=recipient_email,
                    subject=f"Your {report_name} Report is Ready - OppGrid",
                    html_content=f"""
                    <html><body style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;">
                    <h2 style="color:#0F6E56;">Your {report_name} Report is Ready!</h2>
                    <p>Thank you for your purchase. Your AI-generated report has been completed.</p>
                    <div style="margin:24px 0;">
                        <a href="{view_url}"
                           style="background:#0F6E56;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:600;display:inline-block;">
                           View Your Report →
                        </a>
                    </div>
                    <p style="color:#666;font-size:13px;">
                        <strong>Report:</strong> {report_name}<br>
                        <strong>Business:</strong> {report_context.get('businessConcept', report_context.get('idea_description', 'N/A'))}<br>
                        <strong>Link valid for:</strong> 30 days
                    </p>
                    <p style="color:#999;font-size:11px;">If the button doesn't work, copy this link: {view_url}</p>
                    </body></html>
                    """
                )
            except Exception as email_err:
                logger.error(f"Failed to send report email: {email_err}")
        
        return TriggerReportResponse(
            report_id=pending_report.id,
            status="completed",
            message="Report generated successfully"
        )
        
    except Exception as gen_err:
        logger.error(f"Report generation failed: {gen_err}")
        pending_report.status = ReportStatus.FAILED
        pending_report.error_message = str(gen_err)
        db.commit()
        
        return TriggerReportResponse(
            report_id=pending_report.id,
            status="failed",
            message=f"Report generation failed: {str(gen_err)}"
        )


@router.post("/purchase-bundle", response_model=PurchaseResponse)
def create_bundle_purchase(
    purchase_data: BundlePurchaseRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a payment intent for bundle purchase"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == purchase_data.opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    if not ent.is_accessible:
        raise HTTPException(
            status_code=403, 
            detail="Layer 1 access required. Unlock this opportunity first or upgrade your subscription."
        )
    
    if purchase_data.bundle_type not in BUNDLES:
        raise HTTPException(status_code=400, detail=f"Invalid bundle type: {purchase_data.bundle_type}")
    
    existing = db.query(PurchasedBundle).filter(
        PurchasedBundle.user_id == current_user.id,
        PurchasedBundle.opportunity_id == purchase_data.opportunity_id,
        PurchasedBundle.bundle_type == purchase_data.bundle_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this bundle for this opportunity")
    
    bundle = BUNDLES[purchase_data.bundle_type]
    amount_cents = bundle.price_cents
    
    subscription = usage_service.get_or_create_subscription(current_user, db)
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()
    
    stripe_client = get_stripe_client()
    payment_intent = stripe_client.payment_intents.create(
        amount=amount_cents,
        currency="usd",
        customer=subscription.stripe_customer_id,
        metadata={
            "user_id": str(current_user.id),
            "opportunity_id": str(purchase_data.opportunity_id),
            "bundle_type": purchase_data.bundle_type,
            "payment_type": "bundle_purchase",
            "reports": ",".join(bundle.reports),
        },
        description=f"OppGrid Bundle: {bundle.name} for Opportunity #{purchase_data.opportunity_id}",
        automatic_payment_methods={"enabled": True},
    )
    
    log_event(
        db,
        action="report_pricing.bundle_intent_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="opportunity",
        resource_id=purchase_data.opportunity_id,
        metadata={
            "payment_intent_id": payment_intent.id,
            "bundle_type": purchase_data.bundle_type,
            "amount_cents": amount_cents,
        },
    )
    
    from app.services.stripe_service import get_stripe_credentials
    _, publishable_key = get_stripe_credentials()
    
    return PurchaseResponse(
        client_secret=payment_intent.client_secret,
        amount=amount_cents,
        publishable_key=publishable_key,
    )


@router.post("/confirm-report-purchase")
def confirm_report_purchase(
    confirm_data: ConfirmPurchaseRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Confirm a successful report or bundle payment and grant access"""
    stripe_client = get_stripe_client()
    
    try:
        payment_intent = stripe_client.payment_intents.retrieve(confirm_data.payment_intent_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payment intent: {str(e)}")
    
    if payment_intent.status != "succeeded":
        raise HTTPException(status_code=400, detail=f"Payment not completed. Status: {payment_intent.status}")
    
    payment_type = payment_intent.metadata.get("payment_type")
    user_id = int(payment_intent.metadata.get("user_id", 0))
    opportunity_id = int(payment_intent.metadata.get("opportunity_id", 0))
    
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Payment belongs to another user")
    
    if payment_type == "report_purchase":
        report_type = payment_intent.metadata.get("report_type")
        
        existing = db.query(PurchasedReport).filter(
            PurchasedReport.user_id == current_user.id,
            PurchasedReport.opportunity_id == opportunity_id,
            PurchasedReport.report_type == report_type,
            PurchasedReport.stripe_payment_intent_id == confirm_data.payment_intent_id
        ).first()
        
        if existing:
            return {
                "success": True,
                "message": "Report already confirmed",
                "report_type": report_type,
                "opportunity_id": opportunity_id,
            }
        
        purchased = PurchasedReport(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            report_type=report_type,
            purchase_type=PurchaseType.INDIVIDUAL,
            amount_paid=payment_intent.amount,
            stripe_payment_intent_id=confirm_data.payment_intent_id,
        )
        db.add(purchased)
        db.commit()
        
        log_event(
            db,
            action="report_pricing.report_purchase_confirmed",
            actor=current_user,
            actor_type="user",
            request=request,
            resource_type="opportunity",
            resource_id=opportunity_id,
            metadata={
                "payment_intent_id": confirm_data.payment_intent_id,
                "report_type": report_type,
                "amount_cents": payment_intent.amount,
            },
        )
        
        return {
            "success": True,
            "message": f"Report '{report_type}' unlocked successfully",
            "report_type": report_type,
            "opportunity_id": opportunity_id,
        }
    
    elif payment_type == "bundle_purchase":
        bundle_type = payment_intent.metadata.get("bundle_type")
        reports_str = payment_intent.metadata.get("reports", "")
        reports = reports_str.split(",") if reports_str else []
        
        existing = db.query(PurchasedBundle).filter(
            PurchasedBundle.user_id == current_user.id,
            PurchasedBundle.opportunity_id == opportunity_id,
            PurchasedBundle.bundle_type == bundle_type,
            PurchasedBundle.stripe_payment_intent_id == confirm_data.payment_intent_id
        ).first()
        
        if existing:
            return {
                "success": True,
                "message": "Bundle already confirmed",
                "bundle_type": bundle_type,
                "opportunity_id": opportunity_id,
                "reports": reports,
            }
        
        bundle_record = PurchasedBundle(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            bundle_type=bundle_type,
            amount_paid=payment_intent.amount,
            stripe_payment_intent_id=confirm_data.payment_intent_id,
        )
        db.add(bundle_record)
        
        for report_type in reports:
            existing_report = db.query(PurchasedReport).filter(
                PurchasedReport.user_id == current_user.id,
                PurchasedReport.opportunity_id == opportunity_id,
                PurchasedReport.report_type == report_type
            ).first()
            
            if not existing_report:
                purchased = PurchasedReport(
                    user_id=current_user.id,
                    opportunity_id=opportunity_id,
                    report_type=report_type,
                    purchase_type=PurchaseType.BUNDLE,
                    bundle_id=bundle_type,
                    amount_paid=0,
                    stripe_payment_intent_id=confirm_data.payment_intent_id,
                )
                db.add(purchased)
        
        db.commit()
        
        log_event(
            db,
            action="report_pricing.bundle_purchase_confirmed",
            actor=current_user,
            actor_type="user",
            request=request,
            resource_type="opportunity",
            resource_id=opportunity_id,
            metadata={
                "payment_intent_id": confirm_data.payment_intent_id,
                "bundle_type": bundle_type,
                "reports": reports,
                "amount_cents": payment_intent.amount,
            },
        )
        
        return {
            "success": True,
            "message": f"Bundle '{bundle_type}' unlocked successfully",
            "bundle_type": bundle_type,
            "opportunity_id": opportunity_id,
            "reports": reports,
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid payment type")


@router.get("/my-purchases")
def get_my_purchases(
    opportunity_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's purchased reports"""
    query = db.query(PurchasedReport).filter(PurchasedReport.user_id == current_user.id)
    
    if opportunity_id:
        query = query.filter(PurchasedReport.opportunity_id == opportunity_id)
    
    purchases = query.order_by(PurchasedReport.purchased_at.desc()).all()
    
    return {
        "purchases": [
            {
                "id": p.id,
                "opportunity_id": p.opportunity_id,
                "report_type": p.report_type,
                "purchase_type": p.purchase_type.value if p.purchase_type else "individual",
                "bundle_id": p.bundle_id,
                "amount_paid": p.amount_paid,
                "is_generated": p.is_generated,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
            }
            for p in purchases
        ],
        "total": len(purchases),
    }


@router.get("/can-generate/{opportunity_id}/{report_type}")
def can_generate_report(
    opportunity_id: int,
    report_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if user can generate a specific report (included in tier or purchased)"""
    subscription = usage_service.get_or_create_subscription(current_user, db)
    user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    
    if is_report_included_for_tier(report_type, user_tier):
        return {
            "can_generate": True,
            "reason": "included_in_tier",
            "user_tier": user_tier,
        }
    
    purchased = db.query(PurchasedReport).filter(
        PurchasedReport.user_id == current_user.id,
        PurchasedReport.opportunity_id == opportunity_id,
        PurchasedReport.report_type == report_type
    ).first()
    
    if purchased:
        return {
            "can_generate": True,
            "reason": "purchased",
            "purchased_at": purchased.purchased_at.isoformat() if purchased.purchased_at else None,
        }
    
    license_active = db.query(ConsultantLicense).filter(
        ConsultantLicense.user_id == current_user.id,
        ConsultantLicense.is_active == True
    ).first()
    
    if license_active and license_active.opportunities_used < license_active.max_opportunities:
        return {
            "can_generate": True,
            "reason": "consultant_license",
            "opportunities_remaining": license_active.max_opportunities - license_active.opportunities_used,
        }
    
    price = get_report_price(report_type)
    return {
        "can_generate": False,
        "reason": "purchase_required",
        "price": price,
        "price_formatted": f"${price / 100:.0f}",
    }


@router.get("/usage")
def get_report_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's monthly report usage status"""
    status = report_usage_service.get_usage_status(current_user, db)
    return status


@router.get("/effective-price/{report_type}")
def get_effective_report_price(
    report_type: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get effective price for a report considering free allocation and tier discount"""
    if report_type not in REPORT_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")
    
    base_price = REPORT_PRODUCTS[report_type].price_cents
    pricing = report_usage_service.get_effective_price(base_price, current_user, db)
    
    return {
        "report_type": report_type,
        "report_name": REPORT_PRODUCTS[report_type].name,
        **pricing,
    }


class ReportOptionItem(BaseModel):
    report_type: str
    label: str
    price_cents: int
    is_included: bool
    display_price: str


class CheckoutPanelConfig(BaseModel):
    state: str
    report_options: List[ReportOptionItem]
    reports_remaining: Optional[int] = None
    reports_total: Optional[int] = None
    email_on_file: Optional[str] = None
    selected_report: str
    base_price_cents: int
    discount_pct: int = 0
    final_price_cents: int
    primary_cta: str
    secondary_cta: Optional[str] = None
    upsell_message: Optional[str] = None


@router.get("/checkout-state")
def get_checkout_state_endpoint(
    report_type: str = "business_plan",
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> CheckoutPanelConfig:
    """Return checkout panel config for the 3-state report generation flow."""
    from app.core.report_pricing import get_tier_free_reports, calculate_discounted_price

    if report_type not in STUDIO_REPORT_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report type: {report_type}. Valid types: {list(STUDIO_REPORT_PRICES.keys())}",
        )

    studio_product = STUDIO_REPORT_PRICES[report_type]
    base_price = studio_product["price_cents"]
    report_name = studio_product["name"]

    def build_options(credits_remaining: int, is_paid: bool) -> List[ReportOptionItem]:
        use_credits = is_paid and credits_remaining > 0
        items = []
        for rtype, info in STUDIO_REPORT_PRICES.items():
            if use_credits:
                display = "use 1 credit"
                label = f"{info['name']} — use 1 credit"
                is_included = True
            else:
                display = f"${info['price_cents'] // 100}"
                label = f"{info['name']} — ${info['price_cents'] // 100}"
                is_included = False
            items.append(ReportOptionItem(
                report_type=rtype,
                label=label,
                price_cents=info["price_cents"],
                is_included=is_included,
                display_price=display,
            ))
        return items

    if not current_user:
        return CheckoutPanelConfig(
            state="guest",
            report_options=build_options(0, False),
            selected_report=report_type,
            base_price_cents=base_price,
            discount_pct=0,
            final_price_cents=base_price,
            primary_cta=f"Pay ${base_price // 100} & generate",
            secondary_cta="Create free account (save 20%)",
        )

    usage_status = report_usage_service.get_usage_status(current_user, db)
    tier = usage_status["tier"]
    free_remaining = usage_status["free_remaining"]
    is_unlimited = usage_status["is_unlimited"]
    free_total = usage_status["free_reports_allocation"]
    discount_pct = usage_status["discount_percent"]

    is_paid_tier = tier != "free"
    has_credits = is_unlimited or free_remaining > 0

    if tier == "free":
        return CheckoutPanelConfig(
            state="free_tier",
            report_options=build_options(0, False),
            email_on_file=current_user.email,
            selected_report=report_type,
            base_price_cents=base_price,
            discount_pct=0,
            final_price_cents=base_price,
            primary_cta=f"Pay ${base_price // 100} & generate",
            secondary_cta="Subscribe & save 20%+",
            upsell_message="Subscribe to get monthly report credits.",
        )

    if is_paid_tier and has_credits:
        remaining = -1 if is_unlimited else free_remaining
        total = -1 if is_unlimited else free_total
        return CheckoutPanelConfig(
            state="subscriber_has_credits",
            report_options=build_options(free_remaining if not is_unlimited else 1, True),
            reports_remaining=remaining,
            reports_total=total,
            email_on_file=current_user.email,
            selected_report=report_type,
            base_price_cents=base_price,
            discount_pct=100,
            final_price_cents=0,
            primary_cta="Generate report (use 1 credit)",
        )

    final_price = calculate_discounted_price(base_price, tier)
    upsell = (
        f"You've used all {free_total} reports this month. Upgrade for more."
        if not is_unlimited and free_remaining == 0 and free_total > 0
        else "Upgrade your plan to get more monthly report credits."
    )

    return CheckoutPanelConfig(
        state="subscriber_no_credits",
        report_options=build_options(0, True),
        reports_remaining=free_remaining if not is_unlimited else None,
        reports_total=free_total if not is_unlimited else None,
        email_on_file=current_user.email,
        selected_report=report_type,
        base_price_cents=base_price,
        discount_pct=discount_pct,
        final_price_cents=final_price,
        primary_cta=f"Pay ${final_price // 100} & generate",
        secondary_cta="Upgrade plan",
        upsell_message=upsell,
    )


class FreeReportGenerateRequest(BaseModel):
    opportunity_id: Optional[int] = None
    report_type: str
    idea_description: Optional[str] = None
    analysis_context: Optional[str] = None
    target_market: Optional[str] = None
    location: Optional[str] = None


@router.post("/generate-free-report")
async def generate_free_report(
    request_data: FreeReportGenerateRequest,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Generate a report using free allocation (no payment required, supports guests)"""
    from app.models.generated_report import GeneratedReport, ReportType, ReportStatus
    from app.services.llm_ai_engine import llm_ai_engine_service
    import time
    import logging
    logger = logging.getLogger(__name__)

    GUEST_FREE_REPORT_TYPES = {"feasibility_study"}

    if not current_user:
        if request_data.report_type not in GUEST_FREE_REPORT_TYPES:
            raise HTTPException(
                status_code=403,
                detail="Authentication required for this report type. Only feasibility studies are available for guest users."
            )
        free_check = {"is_free": True, "reason": "guest_free_report"}
    else:
        free_check = report_usage_service.check_free_available(current_user, db)
        if not free_check["is_free"]:
            raise HTTPException(
                status_code=402,
                detail="No free reports remaining. Please purchase this report."
            )

    if request_data.report_type not in REPORT_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {request_data.report_type}")

    opportunity = None
    title_suffix = request_data.idea_description or "General Analysis"

    if request_data.opportunity_id:
        opportunity = db.query(Opportunity).filter(Opportunity.id == request_data.opportunity_id).first()
        if opportunity:
            title_suffix = opportunity.title

    report_type_map = {
        "feasibility_study": ReportType.FEASIBILITY_STUDY,
        "market_analysis": ReportType.MARKET_ANALYSIS,
        "strategic_assessment": ReportType.STRATEGIC_ASSESSMENT,
        "pestle_analysis": ReportType.PESTLE_ANALYSIS,
        "business_plan": ReportType.BUSINESS_PLAN,
        "financial_model": ReportType.FINANCIAL_MODEL,
        "pitch_deck": ReportType.PITCH_DECK,
        "location_analysis": ReportType.LOCATION_ANALYSIS,
    }

    report_type_enum = report_type_map.get(request_data.report_type)
    if not report_type_enum:
        raise HTTPException(status_code=400, detail=f"Unsupported report type: {request_data.report_type}")

    report_product = REPORT_PRODUCTS[request_data.report_type]

    raw_title = f"{report_product.name}: {title_suffix}"
    report = GeneratedReport(
        user_id=current_user.id if current_user else None,
        opportunity_id=request_data.opportunity_id if opportunity else None,
        report_type=report_type_enum,
        status=ReportStatus.GENERATING,
        title=raw_title[:255],
        summary=f"Free report - {free_check['reason']}. {request_data.idea_description or ''}".strip()[:1000],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Extract city and state from location for orchestrator
    _free_location = request_data.location or (opportunity.city if opportunity else "") or ""
    _free_city, _free_state = "", ""
    if "," in _free_location:
        _free_parts = _free_location.split(",")
        _free_city = _free_parts[0].strip()
        _free_state = _free_parts[1].strip() if len(_free_parts) > 1 else ""
    else:
        _free_city = _free_location

    _free_business_type = (
        request_data.idea_description
        or (opportunity.title if opportunity else "")
        or "Business Opportunity"
    )
    _free_category = (
        request_data.analysis_context
        or (opportunity.category if opportunity else None)
    )

    from app.services.report_orchestrator import ReportOrchestrator
    _orchestrator = ReportOrchestrator()

    reservation_used = False
    if current_user:
        atomic_check = report_usage_service.atomic_reserve_free_report(current_user, db)
        if not atomic_check["is_free"]:
            report.status = ReportStatus.FAILED
            report.error_message = "No free reports remaining (concurrent reservation)"
            db.commit()
            raise HTTPException(
                status_code=402,
                detail="No free reports remaining. Please purchase this report."
            )
        reservation_used = atomic_check.get("reserved", False)

    start_time = time.time()
    try:
        content = await _orchestrator.generate(
            report_type=request_data.report_type,
            business_type=_free_business_type,
            city=_free_city,
            state=_free_state,
            db=db,
            user_notes=request_data.idea_description or "",
            category=_free_category,
            target_audience=request_data.target_market,
        )
        if not content:
            raise Exception("AI returned empty response")

        generation_time_ms = int((time.time() - start_time) * 1000)

        lines = content.split('\n')
        summary = lines[0][:500] if lines else "Report generated successfully"
        # Strip HTML from summary
        import re
        summary = re.sub(r'<[^>]+>', '', summary).strip()
        if not summary:
            summary = f"{report_product.name} generated successfully"

        report.content = content
        report.summary = summary
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.utcnow()
        report.generation_time_ms = generation_time_ms
        report.confidence_score = 85

        db.commit()
        db.refresh(report)

    except Exception as e:
        logger.error(f"Free report generation failed: {e}")
        report.status = ReportStatus.FAILED
        report.error_message = str(e)
        if reservation_used:
            try:
                report_usage_service.release_free_report_reservation(current_user.id, db)
            except Exception as release_err:
                logger.warning(f"Failed to release free report reservation for user {current_user.id}: {release_err}")
        db.commit()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    log_event(
        db,
        action="report_pricing.free_report_generated",
        actor=current_user,
        actor_type="user" if current_user else "guest",
        request=request,
        resource_type="report",
        resource_id=report.id,
        metadata={
            "report_type": request_data.report_type,
            "opportunity_id": request_data.opportunity_id,
            "reason": free_check["reason"],
        },
    )

    return {
        "success": True,
        "id": report.id,
        "report_id": report.id,
        "report_type": request_data.report_type,
        "title": report.title,
        "summary": report.summary,
        "content": report.content,
        "confidence_score": report.confidence_score,
        "generation_time_ms": report.generation_time_ms,
        "status": "completed",
        "message": "Report generated successfully",
        "usage_reason": free_check["reason"],
    }


CLONE_ANALYSIS_BASE_PRICE_CENTS = 4900


class CloneAnalysisAccessRequest(BaseModel):
    source_business: str
    target_city: str
    target_state: str


@router.post("/clone-analysis/check-access")
def check_clone_analysis_access(
    request_data: CloneAnalysisAccessRequest,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Check if user has free access to Clone Analysis or needs to pay"""
    if not current_user:
        return {
            "has_free_access": False,
            "requires_payment": True,
            "price_cents": CLONE_ANALYSIS_BASE_PRICE_CENTS,
            "discounted_price_cents": CLONE_ANALYSIS_BASE_PRICE_CENTS,
            "discount_percent": 0,
            "reason": "guest_user",
        }
    
    free_check = report_usage_service.check_free_available(current_user, db)
    
    if free_check["is_free"]:
        return {
            "has_free_access": True,
            "requires_payment": False,
            "price_cents": 0,
            "reason": free_check["reason"],
            "free_remaining": free_check.get("free_remaining"),
        }
    
    discount_percent = free_check["discount_percent"]
    discounted_price = int(CLONE_ANALYSIS_BASE_PRICE_CENTS * (1 - discount_percent / 100))
    
    return {
        "has_free_access": False,
        "requires_payment": True,
        "price_cents": CLONE_ANALYSIS_BASE_PRICE_CENTS,
        "discounted_price_cents": discounted_price,
        "discount_percent": discount_percent,
        "reason": free_check["reason"],
    }


@router.post("/clone-analysis/unlock-free")
def unlock_clone_analysis_free(
    request_data: CloneAnalysisAccessRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Unlock Clone Analysis using free allocation"""
    free_check = report_usage_service.check_free_available(current_user, db)
    
    if not free_check["is_free"]:
        raise HTTPException(
            status_code=402,
            detail="No free reports remaining. Please purchase this analysis."
        )
    
    report_usage_service.increment_usage(current_user.id, db)
    
    log_event(
        db,
        action="report_pricing.clone_analysis_free_unlock",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="clone_analysis",
        metadata={
            "source_business": request_data.source_business,
            "target_city": request_data.target_city,
            "target_state": request_data.target_state,
            "reason": free_check["reason"],
        },
    )
    
    return {
        "success": True,
        "message": "Clone Analysis unlocked successfully",
        "usage_reason": free_check["reason"],
    }


# ============================================================================
# TEMPLATE PRICING ENDPOINTS
# ============================================================================

class TemplatePricingItem(BaseModel):
    slug: str
    name: str
    description: str
    category: str
    min_tier: str
    base_price_cents: int
    member_price_cents: int
    discount_percent: int
    is_included: bool  # True if user's tier >= min_tier
    is_purchased: bool  # True if user already purchased this template


class TemplatePricingResponse(BaseModel):
    templates: List[TemplatePricingItem]
    user_tier: Optional[str] = None
    tier_discount_percent: int = 0


@router.get("/template-pricing", response_model=TemplatePricingResponse)
def get_template_pricing(
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get all template pricing with member/non-member prices"""
    templates = db.query(ReportTemplate).filter(
        ReportTemplate.is_active == True
    ).order_by(ReportTemplate.display_order).all()
    
    # Get user tier and discount
    user_tier = "free"
    tier_discount = 0
    purchased_slugs = set()
    
    if current_user:
        subscription = usage_service.get_or_create_subscription(current_user, db)
        user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
        tier_discount = get_tier_report_discount(user_tier)
        
        # Get purchased templates
        purchases = db.query(PurchasedTemplate).filter(
            PurchasedTemplate.user_id == current_user.id
        ).all()
        purchased_slugs = {p.template_slug for p in purchases}
    
    # Tier order for access check
    tier_order = ["free", "starter", "growth", "pro", "team", "business", "enterprise"]
    user_tier_idx = tier_order.index(user_tier.lower()) if user_tier.lower() in tier_order else 0
    
    result = []
    for template in templates:
        min_tier_idx = tier_order.index(template.min_tier.lower()) if template.min_tier.lower() in tier_order else 99
        is_included = user_tier_idx >= min_tier_idx
        
        base_price = template.price_cents
        member_price = calculate_discounted_price(base_price, user_tier) if current_user else base_price
        
        result.append(TemplatePricingItem(
            slug=template.slug,
            name=template.name,
            description=template.description,
            category=template.category,
            min_tier=template.min_tier,
            base_price_cents=base_price,
            member_price_cents=member_price if not is_included else 0,
            discount_percent=tier_discount if not is_included else 100,
            is_included=is_included,
            is_purchased=template.slug in purchased_slugs,
        ))
    
    return TemplatePricingResponse(
        templates=result,
        user_tier=user_tier if current_user else None,
        tier_discount_percent=tier_discount,
    )


@router.get("/template-pricing/{slug}")
def get_single_template_pricing(
    slug: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get pricing for a single template"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.slug == slug,
        ReportTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get user tier
    user_tier = "free"
    tier_discount = 0
    is_purchased = False
    
    if current_user:
        subscription = usage_service.get_or_create_subscription(current_user, db)
        user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
        tier_discount = get_tier_report_discount(user_tier)
        
        # Check if purchased
        existing = db.query(PurchasedTemplate).filter(
            PurchasedTemplate.user_id == current_user.id,
            PurchasedTemplate.template_slug == slug
        ).first()
        is_purchased = existing is not None
    
    # Check tier access
    tier_order = ["free", "starter", "growth", "pro", "team", "business", "enterprise"]
    user_tier_idx = tier_order.index(user_tier.lower()) if user_tier.lower() in tier_order else 0
    min_tier_idx = tier_order.index(template.min_tier.lower()) if template.min_tier.lower() in tier_order else 99
    is_included = user_tier_idx >= min_tier_idx
    
    base_price = template.price_cents
    member_price = calculate_discounted_price(base_price, user_tier)
    
    return {
        "slug": template.slug,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "min_tier": template.min_tier,
        "base_price_cents": base_price,
        "base_price_formatted": f"${base_price / 100:.0f}",
        "member_price_cents": member_price if not is_included else 0,
        "member_price_formatted": f"${member_price / 100:.0f}" if not is_included else "Included",
        "discount_percent": tier_discount,
        "savings_cents": base_price - member_price if tier_discount > 0 else 0,
        "is_included": is_included,
        "is_purchased": is_purchased,
        "user_tier": user_tier if current_user else None,
        "access_status": "included" if is_included else ("purchased" if is_purchased else "purchase_required"),
    }


class TemplateCheckoutRequest(BaseModel):
    template_slug: str
    success_url: str
    cancel_url: str


class TemplateCheckoutResponse(BaseModel):
    session_id: str
    url: str


@router.post("/template-checkout", response_model=TemplateCheckoutResponse)
def create_template_checkout(
    checkout_data: TemplateCheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for template purchase"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.slug == checkout_data.template_slug,
        ReportTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if already purchased
    existing = db.query(PurchasedTemplate).filter(
        PurchasedTemplate.user_id == current_user.id,
        PurchasedTemplate.template_slug == checkout_data.template_slug
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this template")
    
    # Check if included in tier
    subscription = usage_service.get_or_create_subscription(current_user, db)
    user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    
    tier_order = ["free", "starter", "growth", "pro", "team", "business", "enterprise"]
    user_tier_idx = tier_order.index(user_tier.lower()) if user_tier.lower() in tier_order else 0
    min_tier_idx = tier_order.index(template.min_tier.lower()) if template.min_tier.lower() in tier_order else 99
    
    if user_tier_idx >= min_tier_idx:
        raise HTTPException(
            status_code=400,
            detail=f"This template is included with your {user_tier} subscription. No purchase needed."
        )
    
    # Calculate discounted price
    base_price = template.price_cents
    discount_percent = get_tier_report_discount(user_tier)
    final_price = calculate_discounted_price(base_price, user_tier)
    
    if final_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid price for this template")
    
    # Validate redirect URLs
    if not validate_redirect_url(checkout_data.success_url, request) or not validate_redirect_url(checkout_data.cancel_url, request):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    # Ensure customer exists
    if not subscription.stripe_customer_id:
        customer = stripe_service.create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        subscription.stripe_customer_id = customer.id
        db.commit()
    
    stripe_client = get_stripe_client()
    
    # Create product description with discount info
    description = template.description
    if discount_percent > 0:
        description += f" ({discount_percent}% member discount applied)"
    
    session = stripe_client.checkout.Session.create(
        customer=subscription.stripe_customer_id,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid Template: {template.name}",
                    "description": description,
                },
                "unit_amount": final_price,
            },
            "quantity": 1,
        }],
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url,
        metadata={
            "user_id": str(current_user.id),
            "template_slug": checkout_data.template_slug,
            "template_id": str(template.id),
            "payment_type": "template_purchase",
            "original_price": str(base_price),
            "discount_percent": str(discount_percent),
        },
    )
    
    log_event(
        db,
        action="report_pricing.template_checkout_created",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="template",
        resource_id=template.id,
        metadata={
            "session_id": session.id,
            "template_slug": checkout_data.template_slug,
            "original_price_cents": base_price,
            "final_price_cents": final_price,
            "discount_percent": discount_percent,
        },
    )
    
    return TemplateCheckoutResponse(session_id=session.id, url=session.url)


@router.post("/confirm-template-purchase")
def confirm_template_purchase(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Confirm a successful template payment and grant access"""
    stripe_client = get_stripe_client()
    
    try:
        session = stripe_client.checkout.Session.retrieve(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid session: {str(e)}")
    
    if session.payment_status != "paid":
        raise HTTPException(status_code=400, detail=f"Payment not completed. Status: {session.payment_status}")
    
    payment_type = session.metadata.get("payment_type")
    if payment_type != "template_purchase":
        raise HTTPException(status_code=400, detail="Invalid payment type")
    
    user_id = int(session.metadata.get("user_id", 0))
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Payment belongs to another user")
    
    template_slug = session.metadata.get("template_slug")
    template_id = int(session.metadata.get("template_id", 0))
    original_price = int(session.metadata.get("original_price", 0))
    discount_percent = int(session.metadata.get("discount_percent", 0))
    
    # Check if already recorded
    existing = db.query(PurchasedTemplate).filter(
        PurchasedTemplate.user_id == current_user.id,
        PurchasedTemplate.template_slug == template_slug,
        PurchasedTemplate.stripe_session_id == session_id
    ).first()
    
    if existing:
        return {
            "success": True,
            "message": "Template already confirmed",
            "template_slug": template_slug,
        }
    
    # Record purchase
    purchase = PurchasedTemplate(
        user_id=current_user.id,
        template_slug=template_slug,
        template_id=template_id if template_id else None,
        amount_paid=session.amount_total,
        original_price=original_price,
        discount_percent=discount_percent,
        stripe_session_id=session_id,
        uses_remaining=-1,  # Unlimited uses
    )
    db.add(purchase)
    db.commit()
    
    log_event(
        db,
        action="report_pricing.template_purchase_confirmed",
        actor=current_user,
        actor_type="user",
        request=request,
        resource_type="template",
        resource_id=template_id,
        metadata={
            "session_id": session_id,
            "template_slug": template_slug,
            "amount_paid": session.amount_total,
            "discount_percent": discount_percent,
        },
    )
    
    return {
        "success": True,
        "message": f"Template '{template_slug}' unlocked successfully",
        "template_slug": template_slug,
    }


@router.get("/my-template-purchases")
def get_my_template_purchases(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's purchased templates"""
    purchases = db.query(PurchasedTemplate).filter(
        PurchasedTemplate.user_id == current_user.id
    ).order_by(PurchasedTemplate.purchased_at.desc()).all()
    
    return {
        "purchases": [
            {
                "id": p.id,
                "template_slug": p.template_slug,
                "amount_paid": p.amount_paid,
                "original_price": p.original_price,
                "discount_percent": p.discount_percent,
                "uses_remaining": p.uses_remaining,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
            }
            for p in purchases
        ],
        "total": len(purchases),
    }


@router.get("/can-use-template/{slug}")
def can_use_template(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if user can use a template (included in tier or purchased)"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.slug == slug,
        ReportTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check tier access
    subscription = usage_service.get_or_create_subscription(current_user, db)
    user_tier = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
    
    tier_order = ["free", "starter", "growth", "pro", "team", "business", "enterprise"]
    user_tier_idx = tier_order.index(user_tier.lower()) if user_tier.lower() in tier_order else 0
    min_tier_idx = tier_order.index(template.min_tier.lower()) if template.min_tier.lower() in tier_order else 99
    
    if user_tier_idx >= min_tier_idx:
        return {
            "can_use": True,
            "reason": "included_in_tier",
            "user_tier": user_tier,
        }
    
    # Check purchase
    purchase = db.query(PurchasedTemplate).filter(
        PurchasedTemplate.user_id == current_user.id,
        PurchasedTemplate.template_slug == slug
    ).first()
    
    if purchase:
        return {
            "can_use": True,
            "reason": "purchased",
            "purchased_at": purchase.purchased_at.isoformat() if purchase.purchased_at else None,
            "uses_remaining": purchase.uses_remaining,
        }
    
    # Need to purchase
    price = calculate_discounted_price(template.price_cents, user_tier)
    return {
        "can_use": False,
        "reason": "purchase_required",
        "price_cents": price,
        "price_formatted": f"${price / 100:.0f}",
        "original_price_cents": template.price_cents,
        "discount_percent": get_tier_report_discount(user_tier),
    }
