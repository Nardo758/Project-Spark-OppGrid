from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import logging
import re
import time
import hmac
import hashlib
import os

from app.db.database import get_db
from app.models import (
    ReportTemplate, GeneratedReport, ReportType, ReportStatus,
    User, Subscription, Opportunity, UserWorkspace, PurchasedTemplate
)
from app.core.dependencies import get_current_user
from app.services.llm_ai_engine import llm_ai_engine_service
from app.services.ai_report_generator import AIReportGenerator
from app.data.report_templates_seed import REPORT_TEMPLATES

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
logger = logging.getLogger(__name__)

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}
STATE_NAME_TO_CODE = {v.lower(): k for k, v in US_STATES.items()}


def normalize_state(state_input: Optional[str]) -> Optional[str]:
    """Normalize a state value to a 2-letter code. Handles full names, codes, and mixed casing."""
    if not state_input:
        return None
    cleaned = state_input.strip()
    upper = cleaned.upper()
    if upper in US_STATES:
        return upper
    lower = cleaned.lower()
    if lower in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[lower]
    return cleaned


def extract_location_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract city, state from free-form text. Returns (city, state_code) or (None, None)."""
    if not text:
        return None, None

    pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b'
    m = re.search(pattern, text)
    if m and m.group(2) in US_STATES:
        return m.group(1).strip(), m.group(2)

    for code, name in US_STATES.items():
        pattern = rf'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+{re.escape(name)}\b'
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip(), code

    for code, name in US_STATES.items():
        pattern = rf'(?:in|near|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+{re.escape(code)}\b'
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip(), code

    return None, None


def extract_business_type(text: str) -> Optional[str]:
    """Extract a business type/category from free-form text."""
    if not text:
        return None
    text_lower = text.lower()
    for keyword in [
        "restaurant", "cafe", "coffee shop", "bakery", "gym", "fitness center",
        "salon", "barbershop", "clinic", "dental", "medical", "pharmacy",
        "daycare", "tutoring", "yoga studio", "pilates", "spa", "hotel", "motel",
        "brewery", "laundromat", "car wash", "pet grooming",
        "auto repair", "real estate", "coworking", "mental health",
        "therapy", "counseling", "consulting", "ecommerce", "saas",
        "retail", "grocery", "convenience store", "gas station",
        "bar and grill", "fitness",
    ]:
        if keyword in text_lower:
            return keyword
    return None


def serialize_report_data_for_prompt(report_data: Any) -> str:
    """Serialize a ReportDataContext into structured prompt text for AI consumption."""
    if not report_data:
        return ""

    lines = ["\n📊 COMPREHENSIVE 4 P's MARKET DATA:"]

    if report_data.product:
        p = report_data.product
        lines.append("\n**PRODUCT (Demand Validation):**")
        if p.opportunity_score is not None:
            lines.append(f"- Opportunity Score: {p.opportunity_score:.0f}/100")
        if p.pain_intensity is not None:
            lines.append(f"- Pain Intensity: {p.pain_intensity:.1f}/10")
        if p.urgency_level:
            lines.append(f"- Urgency Level: {p.urgency_level}")
        if p.trend_strength is not None:
            lines.append(f"- Trend Strength: {p.trend_strength:.0f}/100")
        if p.signal_density is not None:
            lines.append(f"- Signal Density: {p.signal_density:.0%}")
        if p.validation_confidence is not None:
            lines.append(f"- Validation Confidence: {p.validation_confidence:.0%}")
        if p.google_trends_interest is not None:
            lines.append(f"- Google Trends Interest: {p.google_trends_interest}/100 ({p.google_trends_direction or 'N/A'})")
        if p.amenity_demand:
            lines.append("- Top Consumer Demands:")
            for sig in p.amenity_demand[:5]:
                lines.append(f"  * {sig.get('amenity_type', '').replace('_', ' ').title()}: {sig.get('demand_pct', 0)}%")

    if report_data.price:
        pr = report_data.price
        lines.append("\n**PRICE (Economics):**")
        if pr.market_size_estimate:
            lines.append(f"- Market Size: {pr.market_size_estimate}")
        if pr.addressable_market_value:
            lines.append(f"- Addressable Market: ${pr.addressable_market_value:,.0f}")
        if pr.median_income:
            lines.append(f"- Median Income: ${pr.median_income:,}")
        if pr.revenue_benchmark:
            lines.append(f"- Revenue Benchmark: ${pr.revenue_benchmark:,.0f}/year")
        if pr.capital_required:
            lines.append(f"- Capital Required: ${pr.capital_required:,.0f}")
        if pr.median_rent:
            lines.append(f"- Median Rent: ${pr.median_rent}/month")
        if pr.spending_power_index:
            lines.append(f"- Spending Power Index: {pr.spending_power_index}/100")
        if pr.income_growth_rate:
            lines.append(f"- Income Growth Rate: {pr.income_growth_rate}%")

    if report_data.place:
        pl = report_data.place
        lines.append("\n**PLACE (Location Intelligence):**")
        if pl.growth_score is not None:
            lines.append(f"- Market Growth Score: {pl.growth_score:.0f}/100")
        if pl.growth_category:
            lines.append(f"- Growth Category: {pl.growth_category}")
        if pl.population:
            lines.append(f"- Population: {pl.population:,}")
        if pl.population_growth_rate is not None:
            lines.append(f"- Population Growth: {pl.population_growth_rate}%")
        if pl.job_growth_rate is not None:
            lines.append(f"- Job Growth: {pl.job_growth_rate}%")
        if pl.business_formation_rate is not None:
            lines.append(f"- Business Formation Rate: {pl.business_formation_rate}%")
        if pl.traffic_aadt:
            lines.append(f"- Traffic AADT: {pl.traffic_aadt:,}")
        if pl.vacancy_rate is not None:
            lines.append(f"- Vacancy Rate: {pl.vacancy_rate}%")
        if pl.unemployment_rate is not None:
            lines.append(f"- Unemployment Rate: {pl.unemployment_rate}%")
        if pl.job_postings_count:
            lines.append(f"- Active Job Postings: {pl.job_postings_count:,}")

    if report_data.promotion:
        pm = report_data.promotion
        lines.append("\n**PROMOTION (Competition):**")
        if pm.competition_level:
            lines.append(f"- Competition Level: {pm.competition_level}")
        if pm.competitor_count:
            lines.append(f"- Competitors Found: {pm.competitor_count}")
        if pm.avg_competitor_rating:
            lines.append(f"- Avg Competitor Rating: {pm.avg_competitor_rating:.1f}/5.0")
        if pm.success_factors:
            lines.append(f"- Success Factors: {', '.join(pm.success_factors[:3])}")
        if pm.key_risks:
            lines.append(f"- Key Risks: {', '.join(pm.key_risks[:3])}")
        if pm.competitive_advantages:
            lines.append(f"- Competitive Advantages: {', '.join(pm.competitive_advantages[:3])}")

    if report_data.data_quality:
        dq = report_data.data_quality
        lines.append(f"\nData Quality: {dq.completeness:.0%} complete, {dq.confidence:.0%} confidence")
        if dq.weakest_pillar:
            lines.append(f"Weakest Pillar: {dq.weakest_pillar}")

    lines.append("--- End Market Intelligence Data ---\n")
    return "\n".join(lines)


class ReportTemplateResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    category: str
    min_tier: str
    display_order: int

    class Config:
        from_attributes = True


class GeneratedReportResponse(BaseModel):
    id: int
    report_type: str
    status: str
    title: Optional[str]
    summary: Optional[str]
    content: Optional[str]
    confidence_score: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    template_slug: str
    opportunity_id: Optional[int] = None
    workspace_id: Optional[int] = None
    custom_context: Optional[str] = None


class CategoryWithTemplates(BaseModel):
    category: str
    display_name: str
    templates: List[ReportTemplateResponse]


def get_user_tier(user: User, db: Session) -> str:
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "ACTIVE"
    ).first()
    if subscription:
        tier_val = subscription.tier.value if hasattr(subscription.tier, 'value') else str(subscription.tier)
        return tier_val.lower()
    return "explorer"


def tier_has_access(user_tier: str, required_tier: str) -> bool:
    tier_order = ["free", "explorer", "starter", "builder", "growth", "pro", "business", "team", "enterprise"]
    user_level = tier_order.index(user_tier) if user_tier in tier_order else 0
    if required_tier not in tier_order:
        logger.warning(f"Unknown required_tier '{required_tier}', denying access")
        return False
    required_level = tier_order.index(required_tier)
    return user_level >= required_level


@router.get("/templates", response_model=List[CategoryWithTemplates])
async def get_report_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    templates = db.query(ReportTemplate).filter(
        ReportTemplate.is_active == True
    ).order_by(ReportTemplate.display_order).all()
    
    if not templates:
        await seed_templates(db)
        templates = db.query(ReportTemplate).filter(
            ReportTemplate.is_active == True
        ).order_by(ReportTemplate.display_order).all()
    
    category_map = {
        "popular": "Popular",
        "marketing": "Marketing",
        "product": "Product",
        "business": "Business",
        "research": "Research",
        "analysis": "Analysis Reports",
        "location": "Location Intelligence",
    }
    
    categories = {}
    for template in templates:
        cat = template.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    result = []
    for cat_key in ["popular", "marketing", "product", "business", "research", "analysis", "location"]:
        if cat_key in categories:
            result.append(CategoryWithTemplates(
                category=cat_key,
                display_name=category_map.get(cat_key, cat_key.title()),
                templates=[ReportTemplateResponse.model_validate(t) for t in categories[cat_key]]
            ))
    
    return result


@router.get("/templates/public", response_model=List[CategoryWithTemplates])
async def get_public_report_templates(
    db: Session = Depends(get_db)
):
    """Get report templates - no authentication required for browsing"""
    templates = db.query(ReportTemplate).filter(
        ReportTemplate.is_active == True
    ).order_by(ReportTemplate.display_order).all()
    
    if not templates:
        await seed_templates(db)
        templates = db.query(ReportTemplate).filter(
            ReportTemplate.is_active == True
        ).order_by(ReportTemplate.display_order).all()
    
    category_map = {
        "popular": "Popular",
        "marketing": "Marketing",
        "product": "Product",
        "business": "Business",
        "research": "Research",
        "analysis": "Analysis Reports",
        "location": "Location Intelligence",
    }
    
    categories = {}
    for template in templates:
        cat = template.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    result = []
    for cat_key in ["popular", "marketing", "product", "business", "research", "analysis", "location"]:
        if cat_key in categories:
            result.append(CategoryWithTemplates(
                category=cat_key,
                display_name=category_map.get(cat_key, cat_key.title()),
                templates=[ReportTemplateResponse.model_validate(t) for t in categories[cat_key]]
            ))
    
    return result


@router.post("/generate", response_model=GeneratedReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(ReportTemplate).filter(
        ReportTemplate.slug == request.template_slug,
        ReportTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    
    user_tier = get_user_tier(current_user, db)
    has_tier_access = tier_has_access(user_tier, template.min_tier)
    
    # Check if user purchased this template
    has_purchased = False
    if not has_tier_access:
        purchase = db.query(PurchasedTemplate).filter(
            PurchasedTemplate.user_id == current_user.id,
            PurchasedTemplate.template_slug == request.template_slug
        ).first()
        has_purchased = purchase is not None
    
    if not has_tier_access and not has_purchased:
        raise HTTPException(
            status_code=403,
            detail=f"This report requires {template.min_tier.upper()} tier or purchase. Current tier: {user_tier.upper()}. Purchase this template to use it."
        )
    
    context_parts = []
    city = None
    state = None
    business_type = None
    opportunity = None
    
    if request.opportunity_id:
        opportunity = db.query(Opportunity).filter(Opportunity.id == request.opportunity_id).first()
        if opportunity:
            context_parts.append(f"Opportunity: {opportunity.title}")
            context_parts.append(f"Description: {opportunity.description}")
            context_parts.append(f"Category: {opportunity.category}")
            if opportunity.market_size:
                context_parts.append(f"Market Size: {opportunity.market_size}")
            city = opportunity.city
            state = normalize_state(opportunity.region)
            business_type = opportunity.category
    
    if request.workspace_id:
        workspace = db.query(UserWorkspace).filter(UserWorkspace.id == request.workspace_id).first()
        if workspace:
            context_parts.append(f"Workspace: {workspace.name}")
            if workspace.description:
                context_parts.append(f"Workspace Description: {workspace.description}")
    
    if request.custom_context:
        context_parts.append(f"Additional Context: {request.custom_context}")
        if not city or not state:
            text_city, text_state = extract_location_from_text(request.custom_context)
            if text_city and text_state:
                city = text_city
                state = text_state
        if not business_type:
            business_type = extract_business_type(request.custom_context)
    
    if not context_parts:
        raise HTTPException(
            status_code=400,
            detail="Please provide an opportunity, workspace, or custom context for report generation"
        )
    
    context = "\n".join(context_parts)
    
    report_data = None
    report_data_text = ""
    if city and state:
        try:
            from app.services.report_data_service import ReportDataService
            data_service = ReportDataService(db)
            report_data = data_service.get_report_data(
                city=city,
                state=state,
                business_type=business_type,
                report_type=template.slug,
                opportunity_id=request.opportunity_id
            )
            report_data_text = serialize_report_data_for_prompt(report_data)
            logger.info(
                f"[ReportGenerate] 4P's data fetched for {city}, {state}: "
                f"{report_data.data_quality.completeness:.0%} complete, "
                f"{report_data.data_quality.confidence:.0%} confidence"
            )
        except Exception as data_err:
            logger.warning(f"[ReportGenerate] Could not fetch market data for {city}, {state}: {data_err}")
    else:
        logger.info("[ReportGenerate] No city/state available, skipping market data enrichment")
    
    enriched_context = context
    if report_data_text:
        enriched_context = f"{context}\n{report_data_text}"
    
    prompt = template.ai_prompt.replace("{context}", enriched_context)
    
    report_type_map = {
        "ad_creatives": ReportType.AD_CREATIVES,
        "brand_package": ReportType.BRAND_PACKAGE,
        "landing_page": ReportType.LANDING_PAGE,
        "content_calendar": ReportType.CONTENT_CALENDAR,
        "email_funnel": ReportType.EMAIL_FUNNEL,
        "email_sequence": ReportType.EMAIL_SEQUENCE,
        "lead_magnet": ReportType.LEAD_MAGNET,
        "sales_funnel": ReportType.SALES_FUNNEL,
        "seo_content": ReportType.SEO_CONTENT,
        "tweet_landing": ReportType.TWEET_LANDING,
        "user_personas": ReportType.USER_PERSONAS,
        "feature_specs": ReportType.FEATURE_SPECS,
        "mvp_roadmap": ReportType.MVP_ROADMAP,
        "prd": ReportType.PRD,
        "gtm_calendar": ReportType.GTM_CALENDAR,
        "gtm_strategy": ReportType.GTM_STRATEGY,
        "kpi_dashboard": ReportType.KPI_DASHBOARD,
        "pricing_strategy": ReportType.PRICING_STRATEGY,
        "competitive_analysis": ReportType.COMPETITIVE_ANALYSIS,
        "customer_interview": ReportType.CUSTOMER_INTERVIEW,
        "feasibility_study": ReportType.FEASIBILITY_STUDY,
        "business_plan": ReportType.BUSINESS_PLAN,
        "financial_model": ReportType.FINANCIAL_MODEL,
        "market_analysis": ReportType.MARKET_ANALYSIS,
        "pestle_analysis": ReportType.PESTLE_ANALYSIS,
        "strategic_assessment": ReportType.STRATEGIC_ASSESSMENT,
        "pitch_deck": ReportType.PITCH_DECK,
        "location_analysis": ReportType.LOCATION_ANALYSIS,
    }
    
    report_type = report_type_map.get(template.slug, ReportType.MARKET_ANALYSIS)
    
    generated_report = GeneratedReport(
        user_id=current_user.id,
        opportunity_id=request.opportunity_id,
        workspace_id=request.workspace_id,
        template_id=template.id,
        report_type=report_type,
        status=ReportStatus.GENERATING,
        title=f"{template.name} Report"
    )
    db.add(generated_report)
    db.commit()
    db.refresh(generated_report)
    
    start_time = time.time()
    try:
        data_instruction = ""
        if report_data_text:
            data_instruction = " Use the OppGrid Market Intelligence Data provided to ground your analysis in real data points. Cite specific metrics where relevant."

        full_prompt = f"""You are OppGrid's senior market intelligence analyst producing institutional-grade business reports.{data_instruction}

{AIReportGenerator.INSTITUTIONAL_STYLE_INSTRUCTIONS}

{prompt}"""
        result = await llm_ai_engine_service.generate_response(full_prompt, model="claude")
        
        if result.get("error"):
            logger.error(f"AI service error: {result.get('error_message', result.get('error'))}")
            raise Exception(f"AI service unavailable: {result.get('error_message', 'Unknown error')}")
        
        raw_content = result.get("response") or result.get("raw")
        if not raw_content:
            raise Exception("AI returned empty response")
        
        formatter = AIReportGenerator()
        content = formatter._format_institutional_report(raw_content, template.slug)
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        lines = content.split('\n')
        summary = lines[0][:500] if lines else "Report generated successfully"
        
        confidence = 85
        if report_data and report_data.data_quality:
            confidence = int(report_data.data_quality.confidence * 100)
            confidence = max(10, min(100, confidence))
        
        generated_report.content = content
        generated_report.summary = summary
        generated_report.status = ReportStatus.COMPLETED
        generated_report.completed_at = datetime.utcnow()
        generated_report.generation_time_ms = generation_time_ms
        generated_report.confidence_score = confidence
        
        db.commit()
        db.refresh(generated_report)
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        generated_report.status = ReportStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to generate report")
    
    return GeneratedReportResponse(
        id=generated_report.id,
        report_type=generated_report.report_type.value,
        status=generated_report.status.value,
        title=generated_report.title,
        summary=generated_report.summary,
        content=generated_report.content,
        confidence_score=generated_report.confidence_score,
        created_at=generated_report.created_at,
        completed_at=generated_report.completed_at
    )


@router.get("/my-reports", response_model=List[GeneratedReportResponse])
async def get_my_reports(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reports = db.query(GeneratedReport).filter(
        GeneratedReport.user_id == current_user.id
    ).order_by(GeneratedReport.created_at.desc()).offset(offset).limit(limit).all()
    
    return [GeneratedReportResponse(
        id=r.id,
        report_type=r.report_type.value,
        status=r.status.value,
        title=r.title,
        summary=r.summary,
        content=r.content,
        confidence_score=r.confidence_score,
        created_at=r.created_at,
        completed_at=r.completed_at
    ) for r in reports]


@router.post("/check-access")
async def check_report_access(
    template_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(ReportTemplate).filter(
        ReportTemplate.slug == template_slug
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    user_tier = get_user_tier(current_user, db)
    has_tier_access = tier_has_access(user_tier, template.min_tier)
    
    has_purchased = False
    if not has_tier_access:
        purchase = db.query(PurchasedTemplate).filter(
            PurchasedTemplate.user_id == current_user.id,
            PurchasedTemplate.template_slug == template_slug
        ).first()
        has_purchased = purchase is not None
    
    return {
        "has_access": has_tier_access or has_purchased,
        "has_tier_access": has_tier_access,
        "has_purchased": has_purchased,
        "user_tier": user_tier,
        "required_tier": template.min_tier,
        "template_name": template.name
    }


async def seed_templates(db: Session):
    for template_data in REPORT_TEMPLATES:
        existing = db.query(ReportTemplate).filter(
            ReportTemplate.slug == template_data["slug"]
        ).first()
        
        if not existing:
            template = ReportTemplate(**template_data)
            db.add(template)
    
    db.commit()
    logger.info("Seeded report templates")


_REPORT_LINK_SECRET = os.getenv("SECRET_KEY", "oppgrid-report-link-secret-2024")
_TOKEN_TTL_SECONDS = 30 * 24 * 3600


def generate_report_view_token(report_id: int) -> str:
    expire_ts = int(datetime.now(timezone.utc).timestamp()) + _TOKEN_TTL_SECONDS
    message = f"{report_id}:{expire_ts}"
    sig = hmac.new(_REPORT_LINK_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{expire_ts}.{sig}"


def verify_report_view_token(report_id: int, token: str) -> bool:
    try:
        expire_ts_str, sig = token.split(".", 1)
        expire_ts = int(expire_ts_str)
        if int(datetime.now(timezone.utc).timestamp()) > expire_ts:
            return False
        message = f"{report_id}:{expire_ts}"
        expected_sig = hmac.new(_REPORT_LINK_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


@router.get("/public/{report_id}")
async def get_public_report(
    report_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Return a report without authentication using a signed time-limited token."""
    if not verify_report_view_token(report_id, token):
        raise HTTPException(status_code=403, detail="Invalid or expired report link.")

    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type.value if report.report_type else None,
        "status": report.status.value if report.status else None,
        "content": report.content,
        "confidence_score": report.confidence_score,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }
