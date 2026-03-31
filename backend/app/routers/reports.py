from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
import time

from app.db.database import get_db
from app.models import (
    ReportTemplate, GeneratedReport, ReportType, ReportStatus,
    User, Subscription, Opportunity, UserWorkspace, PurchasedTemplate
)
from app.core.dependencies import get_current_user
from app.services.llm_ai_engine import llm_ai_engine_service
from app.data.report_templates_seed import REPORT_TEMPLATES

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
logger = logging.getLogger(__name__)


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
        Subscription.status == "active"
    ).first()
    if subscription:
        return subscription.tier.lower()
    return "explorer"


def tier_has_access(user_tier: str, required_tier: str) -> bool:
    tier_order = ["explorer", "builder", "pro", "business", "enterprise"]
    user_level = tier_order.index(user_tier) if user_tier in tier_order else 0
    required_level = tier_order.index(required_tier) if required_tier in tier_order else 0
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
    }
    
    categories = {}
    for template in templates:
        cat = template.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    result = []
    for cat_key in ["popular", "marketing", "product", "business", "research", "analysis"]:
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
    }
    
    categories = {}
    for template in templates:
        cat = template.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    result = []
    for cat_key in ["popular", "marketing", "product", "business", "research", "analysis"]:
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
    
    if request.opportunity_id:
        opportunity = db.query(Opportunity).filter(Opportunity.id == request.opportunity_id).first()
        if opportunity:
            context_parts.append(f"Opportunity: {opportunity.title}")
            context_parts.append(f"Description: {opportunity.description}")
            context_parts.append(f"Category: {opportunity.category}")
            if opportunity.market_size:
                context_parts.append(f"Market Size: {opportunity.market_size}")
    
    if request.workspace_id:
        workspace = db.query(UserWorkspace).filter(UserWorkspace.id == request.workspace_id).first()
        if workspace:
            context_parts.append(f"Workspace: {workspace.name}")
            if workspace.description:
                context_parts.append(f"Workspace Description: {workspace.description}")
    
    if request.custom_context:
        context_parts.append(f"Additional Context: {request.custom_context}")
    
    if not context_parts:
        raise HTTPException(
            status_code=400,
            detail="Please provide an opportunity, workspace, or custom context for report generation"
        )
    
    context = "\n".join(context_parts)
    prompt = template.ai_prompt.replace("{context}", context)
    
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
        # Analysis Reports
        "feasibility_study": ReportType.FEASIBILITY_STUDY,
        "business_plan": ReportType.BUSINESS_PLAN,
        "financial_model": ReportType.FINANCIAL_MODEL,
        "market_analysis": ReportType.MARKET_ANALYSIS,
        "pestle_analysis": ReportType.PESTLE_ANALYSIS,
        "strategic_assessment": ReportType.STRATEGIC_ASSESSMENT,
        "pitch_deck": ReportType.PITCH_DECK,
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
        full_prompt = f"""You are a business strategy expert creating professional reports. Provide actionable, specific, and well-structured content.

{prompt}"""
        result = await llm_ai_engine_service.generate_response(full_prompt, model="claude")
        content = result.get("content", result.get("response", str(result)))
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        lines = content.split('\n')
        summary = lines[0][:500] if lines else "Report generated successfully"
        
        generated_report.content = content
        generated_report.summary = summary
        generated_report.status = ReportStatus.COMPLETED
        generated_report.completed_at = datetime.utcnow()
        generated_report.generation_time_ms = generation_time_ms
        generated_report.confidence_score = 85
        
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


@router.get("/{report_id}", response_model=GeneratedReportResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return GeneratedReportResponse(
        id=report.id,
        report_type=report.report_type.value,
        status=report.status.value,
        title=report.title,
        summary=report.summary,
        content=report.content,
        confidence_score=report.confidence_score,
        created_at=report.created_at,
        completed_at=report.completed_at
    )


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
    has_access = tier_has_access(user_tier, template.min_tier)
    
    return {
        "has_access": has_access,
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
