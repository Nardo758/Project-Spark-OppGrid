from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.generated_report import GeneratedReport, ReportType, ReportStatus
from app.schemas.generated_report import (
    GeneratedReportCreate,
    GeneratedReportUpdate,
    GeneratedReportResponse,
    GeneratedReportDetail,
    GeneratedReportList,
    ReportStats,
    UserReportStats,
)
from app.core.dependencies import get_current_user, get_current_admin_user
from app.services.report_quota_service import ReportQuotaService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=GeneratedReportResponse)
def create_report(
    payload: GeneratedReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new generated report record"""
    report = GeneratedReport(
        user_id=current_user.id,
        opportunity_id=payload.opportunity_id,
        report_type=ReportType(payload.report_type.value),
        title=payload.title,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.patch("/{report_id}", response_model=GeneratedReportResponse)
def update_report(
    report_id: int,
    payload: GeneratedReportUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a report (status, content, scores)"""
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    
    if "status" in update_data:
        update_data["status"] = ReportStatus(update_data["status"])
        if update_data["status"] == ReportStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(report, key, value)
    
    db.commit()
    db.refresh(report)
    return report


@router.get("/", response_model=GeneratedReportList)
def list_user_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    opportunity_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's generated reports"""
    query = db.query(GeneratedReport).filter(GeneratedReport.user_id == current_user.id)
    
    if opportunity_id:
        query = query.filter(GeneratedReport.opportunity_id == opportunity_id)
    
    if report_type:
        try:
            query = query.filter(GeneratedReport.report_type == ReportType(report_type))
        except ValueError:
            pass
    
    if status:
        try:
            query = query.filter(GeneratedReport.status == ReportStatus(status))
        except ValueError:
            pass
    
    total = query.count()
    reports = query.order_by(desc(GeneratedReport.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "reports": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/my-stats", response_model=UserReportStats)
def get_user_report_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's report statistics"""
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    
    total = db.query(GeneratedReport).filter(
        GeneratedReport.user_id == current_user.id
    ).count()
    
    this_month = db.query(GeneratedReport).filter(
        GeneratedReport.user_id == current_user.id,
        GeneratedReport.created_at >= month_ago
    ).count()
    
    by_type_results = db.query(
        GeneratedReport.report_type,
        func.count(GeneratedReport.id)
    ).filter(
        GeneratedReport.user_id == current_user.id
    ).group_by(GeneratedReport.report_type).all()
    
    by_type = {r[0].value if r[0] else "unknown": r[1] for r in by_type_results}
    
    return {
        "total_reports": total,
        "reports_this_month": this_month,
        "by_type": by_type,
    }


@router.get("/stats", response_model=ReportStats)
def get_report_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get platform-wide report statistics (admin only)"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total = db.query(GeneratedReport).count()
    
    today = db.query(GeneratedReport).filter(
        GeneratedReport.created_at >= today_start
    ).count()
    
    this_week = db.query(GeneratedReport).filter(
        GeneratedReport.created_at >= week_ago
    ).count()
    
    this_month = db.query(GeneratedReport).filter(
        GeneratedReport.created_at >= month_ago
    ).count()
    
    by_type_results = db.query(
        GeneratedReport.report_type,
        func.count(GeneratedReport.id)
    ).group_by(GeneratedReport.report_type).all()
    
    by_type = {r[0].value if r[0] else "unknown": r[1] for r in by_type_results}
    
    by_status_results = db.query(
        GeneratedReport.status,
        func.count(GeneratedReport.id)
    ).group_by(GeneratedReport.status).all()
    
    by_status = {r[0].value if r[0] else "unknown": r[1] for r in by_status_results}
    
    avg_time = db.query(func.avg(GeneratedReport.generation_time_ms)).filter(
        GeneratedReport.generation_time_ms.isnot(None)
    ).scalar()
    
    avg_confidence = db.query(func.avg(GeneratedReport.confidence_score)).filter(
        GeneratedReport.confidence_score.isnot(None)
    ).scalar()
    
    return {
        "total_reports": total,
        "reports_today": today,
        "reports_this_week": this_week,
        "reports_this_month": this_month,
        "by_type": by_type,
        "by_status": by_status,
        "avg_generation_time_ms": float(avg_time) if avg_time else None,
        "avg_confidence_score": float(avg_confidence) if avg_confidence else None,
    }


@router.get("/{report_id}", response_model=GeneratedReportDetail)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific report with full content"""
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return GeneratedReportDetail.from_orm_with_snapshot(report)


@router.post("/opportunity/{opportunity_id}/layer1")
def generate_layer1_report(
    opportunity_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate Layer 1: Problem Overview Report ($15)
    
    NEW PAYMENT MODEL:
    - Guests: Can purchase without account ($15, auto-creates account)
    - Free Members: Always pay per-report ($15)
    - Pro Members: 5 free/month + $10 overage
    - Business Members: 15 free/month + $8 overage
    
    Response:
    - If can generate: generates report, charges if needed
    - If needs payment: returns payment_required with pricing
    """
    from app.models.opportunity import Opportunity
    from app.services.report_generator import ReportGenerator
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Check access and pricing via quota service
    quota_service = ReportQuotaService(db)
    can_generate, message, price_cents = quota_service.check_access(current_user, "layer_1")
    
    if not can_generate:
        logger.warning(f"User {current_user.id if current_user else 'guest'} cannot generate Layer 1 report: {message}")
        raise HTTPException(status_code=403, detail=message)
    
    # If price > 0, user needs to pay via Stripe first
    if price_cents > 0:
        logger.info(f"User {current_user.id if current_user else 'guest'} needs payment for Layer 1: ${price_cents/100:.2f}")
        return {
            "success": False,
            "requires_payment": True,
            "message": message,
            "price_cents": price_cents,
            "report_tier": "layer_1",
            "opportunity_id": opportunity_id,
            "stripe_checkout_url": f"/checkout?tier=layer_1&opportunity_id={opportunity_id}",
        }
    
    # User has quota or is eligible for free generation
    generator = ReportGenerator(db)
    
    # Check if report already exists
    if current_user:
        existing = db.query(GeneratedReport).filter(
            GeneratedReport.user_id == current_user.id,
            GeneratedReport.opportunity_id == opportunity_id,
            GeneratedReport.report_type == ReportType.LAYER_1_OVERVIEW,
            GeneratedReport.status == ReportStatus.COMPLETED
        ).first()
        
        if existing:
            return {
                "success": True,
                "report_id": existing.id,
                "status": "existing",
                "message": "Layer 1 report already exists for this opportunity",
                "report": {
                    "id": existing.id,
                    "title": existing.title,
                    "summary": existing.summary,
                    "content": existing.content,
                    "confidence_score": existing.confidence_score,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                }
            }
    
    # Generate report
    demographics = opportunity.demographics if hasattr(opportunity, 'demographics') else None
    report = generator.generate_layer1_report(opportunity, current_user, demographics)
    
    # Decrement quota if user had free allocation
    if current_user and price_cents == 0:
        quota_service.decrement_quota(current_user, "layer_1")
        logger.info(f"Decremented Layer 1 quota for user {current_user.id}")
    
    # Log purchase
    quota_service.log_purchase(
        report_tier="layer_1",
        payment_type="quota" if price_cents == 0 else "stripe",
        amount_cents=price_cents,
        user=current_user,
        report_id=report.id,
        opportunity_id=opportunity_id,
    )
    
    return {
        "success": True,
        "report_id": report.id,
        "status": "generated",
        "message": "Layer 1 report generated successfully",
        "report": {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "content": report.content,
            "confidence_score": report.confidence_score,
            "generation_time_ms": report.generation_time_ms,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    }


@router.post("/opportunity/{opportunity_id}/layer2")
def generate_layer2_report(
    opportunity_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate Layer 2: Deep Dive Analysis Report ($25)
    
    NEW PAYMENT MODEL:
    - Guests: Can purchase without account ($25, auto-creates account)
    - Free Members: Always pay per-report ($25)
    - Pro Members: 2 free/month + $18 overage
    - Business Members: 8 free/month + $15 overage
    """
    from app.models.opportunity import Opportunity
    from app.services.report_generator import ReportGenerator
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Check access and pricing via quota service
    quota_service = ReportQuotaService(db)
    can_generate, message, price_cents = quota_service.check_access(current_user, "layer_2")
    
    if not can_generate:
        logger.warning(f"User {current_user.id if current_user else 'guest'} cannot generate Layer 2 report: {message}")
        raise HTTPException(status_code=403, detail=message)
    
    # If price > 0, user needs to pay via Stripe first
    if price_cents > 0:
        logger.info(f"User {current_user.id if current_user else 'guest'} needs payment for Layer 2: ${price_cents/100:.2f}")
        return {
            "success": False,
            "requires_payment": True,
            "message": message,
            "price_cents": price_cents,
            "report_tier": "layer_2",
            "opportunity_id": opportunity_id,
            "stripe_checkout_url": f"/checkout?tier=layer_2&opportunity_id={opportunity_id}",
        }
    
    # User has quota or is eligible for free generation
    generator = ReportGenerator(db)
    
    # Check if report already exists
    if current_user:
        existing = db.query(GeneratedReport).filter(
            GeneratedReport.user_id == current_user.id,
            GeneratedReport.opportunity_id == opportunity_id,
            GeneratedReport.report_type == ReportType.LAYER_2_DEEP_DIVE,
            GeneratedReport.status == ReportStatus.COMPLETED
        ).first()
        
        if existing:
            return {
                "success": True,
                "report_id": existing.id,
                "status": "existing",
                "message": "Layer 2 report already exists for this opportunity",
                "report": {
                    "id": existing.id,
                    "title": existing.title,
                    "summary": existing.summary,
                    "content": existing.content,
                    "confidence_score": existing.confidence_score,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                }
            }
    
    # Generate report
    demographics = opportunity.demographics if hasattr(opportunity, 'demographics') else None
    report = generator.generate_layer2_report(opportunity, current_user, demographics)
    
    # Decrement quota if user had free allocation
    if current_user and price_cents == 0:
        quota_service.decrement_quota(current_user, "layer_2")
        logger.info(f"Decremented Layer 2 quota for user {current_user.id}")
    
    # Log purchase
    quota_service.log_purchase(
        report_tier="layer_2",
        payment_type="quota" if price_cents == 0 else "stripe",
        amount_cents=price_cents,
        user=current_user,
        report_id=report.id,
        opportunity_id=opportunity_id,
    )
    
    return {
        "success": True,
        "report_id": report.id,
        "status": "generated",
        "message": "Layer 2 Deep Dive report generated successfully",
        "report": {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "content": report.content,
            "confidence_score": report.confidence_score,
            "generation_time_ms": report.generation_time_ms,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    }


@router.post("/opportunity/{opportunity_id}/layer3")
def generate_layer3_report(
    opportunity_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate Layer 3: Execution Package Report ($35)
    
    NEW PAYMENT MODEL:
    - Guests: Can purchase without account ($35, auto-creates account)
    - Free Members: Always pay per-report ($35)
    - Pro Members: 0 free (must purchase) + $25 overage
    - Business Members: 3 free/month + $20 overage
    """
    from app.models.opportunity import Opportunity
    from app.services.report_generator import ReportGenerator
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Check access and pricing via quota service
    quota_service = ReportQuotaService(db)
    can_generate, message, price_cents = quota_service.check_access(current_user, "layer_3")
    
    if not can_generate:
        logger.warning(f"User {current_user.id if current_user else 'guest'} cannot generate Layer 3 report: {message}")
        raise HTTPException(status_code=403, detail=message)
    
    # If price > 0, user needs to pay via Stripe first
    if price_cents > 0:
        logger.info(f"User {current_user.id if current_user else 'guest'} needs payment for Layer 3: ${price_cents/100:.2f}")
        return {
            "success": False,
            "requires_payment": True,
            "message": message,
            "price_cents": price_cents,
            "report_tier": "layer_3",
            "opportunity_id": opportunity_id,
            "stripe_checkout_url": f"/checkout?tier=layer_3&opportunity_id={opportunity_id}",
        }
    
    # User has quota or is eligible for free generation
    generator = ReportGenerator(db)
    
    # Check if report already exists
    if current_user:
        existing = db.query(GeneratedReport).filter(
            GeneratedReport.user_id == current_user.id,
            GeneratedReport.opportunity_id == opportunity_id,
            GeneratedReport.report_type == ReportType.LAYER_3_EXECUTION,
            GeneratedReport.status == ReportStatus.COMPLETED
        ).first()
        
        if existing:
            return {
                "success": True,
                "report_id": existing.id,
                "status": "existing",
                "message": "Layer 3 Execution Package already exists for this opportunity",
                "report": {
                    "id": existing.id,
                    "title": existing.title,
                    "summary": existing.summary,
                    "content": existing.content,
                    "confidence_score": existing.confidence_score,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                }
            }
    
    # Generate report
    demographics = opportunity.demographics if hasattr(opportunity, 'demographics') else None
    report = generator.generate_layer3_report(opportunity, current_user, demographics)
    
    # Decrement quota if user had free allocation
    if current_user and price_cents == 0:
        quota_service.decrement_quota(current_user, "layer_3")
        logger.info(f"Decremented Layer 3 quota for user {current_user.id}")
    
    # Log purchase
    quota_service.log_purchase(
        report_tier="layer_3",
        payment_type="quota" if price_cents == 0 else "stripe",
        amount_cents=price_cents,
        user=current_user,
        report_id=report.id,
        opportunity_id=opportunity_id,
    )
    
    return {
        "success": True,
        "report_id": report.id,
        "status": "generated",
        "message": "Layer 3 Execution Package generated successfully",
        "report": {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "content": report.content,
            "confidence_score": report.confidence_score,
            "generation_time_ms": report.generation_time_ms,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    }


from pydantic import BaseModel, EmailStr
from app.services.email_service import send_email


class SendReportEmailRequest(BaseModel):
    email: EmailStr
    report_type: str
    report_title: str
    report_id: str
    report_content: dict
    generated_at: str


@router.post("/send-email")
async def send_report_email(
    payload: SendReportEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a generated report to the user's email"""
    content = payload.report_content
    
    sections_html = ""
    
    if content.get("executiveSummary"):
        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Executive Summary</h2>
            <p style="color: #475569; line-height: 1.6;">{content['executiveSummary']}</p>
        </div>
        """
    
    if content.get("projectDescription"):
        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Project Description</h2>
            <p style="color: #475569; line-height: 1.6;">{content['projectDescription']}</p>
        </div>
        """
    
    if content.get("marketAnalysis"):
        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Market Analysis</h2>
            <ul style="color: #475569; padding-left: 20px;">
                {''.join(f'<li style="margin-bottom: 8px;">{item}</li>' for item in content['marketAnalysis'])}
            </ul>
        </div>
        """
    
    if content.get("swot"):
        swot = content['swot']
        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">SWOT Analysis</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div style="background: #f0fdf4; padding: 16px; border-radius: 8px;">
                    <h3 style="color: #166534; font-size: 14px; margin-bottom: 8px;">Strengths</h3>
                    <ul style="color: #475569; padding-left: 16px; margin: 0;">
                        {''.join(f'<li>{s}</li>' for s in swot.get('strengths', []))}
                    </ul>
                </div>
                <div style="background: #fef3c7; padding: 16px; border-radius: 8px;">
                    <h3 style="color: #b45309; font-size: 14px; margin-bottom: 8px;">Weaknesses</h3>
                    <ul style="color: #475569; padding-left: 16px; margin: 0;">
                        {''.join(f'<li>{w}</li>' for w in swot.get('weaknesses', []))}
                    </ul>
                </div>
                <div style="background: #dbeafe; padding: 16px; border-radius: 8px;">
                    <h3 style="color: #1e40af; font-size: 14px; margin-bottom: 8px;">Opportunities</h3>
                    <ul style="color: #475569; padding-left: 16px; margin: 0;">
                        {''.join(f'<li>{o}</li>' for o in swot.get('opportunities', []))}
                    </ul>
                </div>
                <div style="background: #fee2e2; padding: 16px; border-radius: 8px;">
                    <h3 style="color: #dc2626; font-size: 14px; margin-bottom: 8px;">Threats</h3>
                    <ul style="color: #475569; padding-left: 16px; margin: 0;">
                        {''.join(f'<li>{t}</li>' for t in swot.get('threats', []))}
                    </ul>
                </div>
            </div>
        </div>
        """
    
    if content.get("financialProjections"):
        fp = content['financialProjections']
        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Financial Projections</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;"><strong>Estimated Start-up Cost</strong></td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;">{fp.get('startupCost', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;"><strong>Monthly Operating Cost</strong></td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;">{fp.get('monthlyOperating', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;"><strong>Break-even Timeline</strong></td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;">{fp.get('breakeven', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;"><strong>ROI Potential</strong></td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;">{fp.get('roi', 'N/A')}</td>
                </tr>
            </table>
        </div>
        """
    
    if content.get("conclusion"):
        recommendation = content.get('recommendation', 'CONDITIONAL')
        rec_color = "#16a34a" if recommendation == "GO" else "#dc2626" if recommendation == "NO-GO" else "#d97706"
        sections_html += f"""
        <div style="margin-bottom: 24px; background: #1e293b; color: white; padding: 16px; border-radius: 8px;">
            <h2 style="color: white; font-size: 18px; margin-bottom: 12px;">Conclusion & Recommendation</h2>
            <p style="color: #cbd5e1; line-height: 1.6; margin-bottom: 16px;">{content['conclusion']}</p>
            <div style="display: inline-block; background: {rec_color}; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;">
                {recommendation}
            </div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc;">
        <div style="max-width: 700px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%); padding: 24px; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">OppGrid</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0 0; font-size: 14px;">Opportunity Intelligence Platform</p>
            </div>
            
            <div style="background: white; padding: 32px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px;">
                    <h1 style="color: #1e293b; font-size: 22px; margin: 0 0 8px 0;">{payload.report_title}</h1>
                    <div style="color: #64748b; font-size: 14px;">
                        <span style="background: #f0fdf4; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600; margin-right: 12px;">
                            {payload.report_type}
                        </span>
                        <span>Report ID: {payload.report_id}</span>
                        <span style="margin-left: 12px;">Generated: {payload.generated_at[:10]}</span>
                    </div>
                    <div style="color: #64748b; font-size: 14px; margin-top: 8px;">
                        Confidence Score: <strong>{content.get('score', 75)}/100</strong>
                    </div>
                </div>
                
                {sections_html}
                
                <div style="border-top: 1px solid #e2e8f0; padding-top: 24px; margin-top: 32px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                        This report was generated by OppGrid AI. For questions, visit oppgrid.com
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await send_email(
            to=payload.email,
            subject=f"Your {payload.report_type} Report: {payload.report_title}",
            html_content=html_content,
        )
        return {"success": True, "message": "Report sent successfully", "email_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/{report_id}/export/pdf")
def export_report_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a generated report as a branded PDF file."""
    from app.services.report_export_service import generate_pdf

    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
        GeneratedReport.status == ReportStatus.COMPLETED,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.content:
        raise HTTPException(status_code=400, detail="Report has no content to export")

    report_type_labels = {
        ReportType.LAYER_1_OVERVIEW: "Problem Overview",
        ReportType.LAYER_2_DEEP_DIVE: "Deep Dive Analysis",
        ReportType.LAYER_3_EXECUTION: "Execution Package",
    }
    type_label = report_type_labels.get(report.report_type, "Report")
    generated_at = report.created_at.strftime("%B %d, %Y") if report.created_at else None
    title = report.title or "OppGrid Report"

    economic_snapshot = None
    if report.economic_snapshot:
        try:
            import json as _json
            economic_snapshot = _json.loads(report.economic_snapshot)
        except Exception:
            economic_snapshot = None

    pdf_bytes = generate_pdf(
        html_content=report.content,
        title=title,
        report_type=type_label,
        generated_at=generated_at,
        economic_snapshot=economic_snapshot,
    )

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60]
    filename = f"OppGrid - {safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/export/docx")
def export_report_docx(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a generated report as a branded DOCX (Word) file."""
    from app.services.report_export_service import generate_docx

    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
        GeneratedReport.status == ReportStatus.COMPLETED,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.content:
        raise HTTPException(status_code=400, detail="Report has no content to export")

    report_type_labels = {
        ReportType.LAYER_1_OVERVIEW: "Problem Overview",
        ReportType.LAYER_2_DEEP_DIVE: "Deep Dive Analysis",
        ReportType.LAYER_3_EXECUTION: "Execution Package",
    }
    type_label = report_type_labels.get(report.report_type, "Report")
    generated_at = report.created_at.strftime("%B %d, %Y") if report.created_at else None
    title = report.title or "OppGrid Report"

    economic_snapshot = None
    if report.economic_snapshot:
        try:
            import json as _json
            economic_snapshot = _json.loads(report.economic_snapshot)
        except Exception:
            economic_snapshot = None

    docx_bytes = generate_docx(
        html_content=report.content,
        title=title,
        report_type=type_label,
        generated_at=generated_at,
        economic_snapshot=economic_snapshot,
    )

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60]
    filename = f"OppGrid - {safe_title}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class InlineExportRequest(BaseModel):
    """For exporting content that isn't yet saved as a GeneratedReport (e.g. Consultant Studio)."""
    content: str
    title: str = "OppGrid Report"
    report_type: str = "Report"


@router.post("/export/pdf")
def export_inline_pdf(
    payload: InlineExportRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a branded PDF from raw HTML content (no saved report required)."""
    from app.services.report_export_service import generate_pdf

    pdf_bytes = generate_pdf(
        html_content=payload.content,
        title=payload.title,
        report_type=payload.report_type,
    )

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in payload.title)[:60]
    filename = f"OppGrid - {safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/docx")
def export_inline_docx(
    payload: InlineExportRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a branded DOCX from raw HTML content (no saved report required)."""
    from app.services.report_export_service import generate_docx

    docx_bytes = generate_docx(
        html_content=payload.content,
        title=payload.title,
        report_type=payload.report_type,
    )

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in payload.title)[:60]
    filename = f"OppGrid - {safe_title}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/admin/cleanup-stuck")
def cleanup_stuck_reports(
    threshold_minutes: int = 5,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Clean up reports stuck in GENERATING status for more than threshold minutes.
    Marks them as FAILED with appropriate error information.
    """
    threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
    
    stuck_reports = db.query(GeneratedReport).filter(
        GeneratedReport.status == ReportStatus.GENERATING,
        GeneratedReport.created_at < threshold_time
    ).all()
    
    cleaned = []
    for report in stuck_reports:
        report.status = ReportStatus.FAILED
        report.error_type = "timeout"
        report.error_message = f"Report generation timed out after {threshold_minutes} minutes"
        report.generation_time_ms = int((datetime.utcnow() - report.created_at).total_seconds() * 1000)
        cleaned.append({
            "id": report.id,
            "title": report.title,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "user_id": report.user_id,
        })
    
    db.commit()
    
    return {
        "cleaned_count": len(cleaned),
        "threshold_minutes": threshold_minutes,
        "reports": cleaned,
    }


@router.get("/{report_id}/status")
def get_report_status(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current status of a report (for polling during async generation).
    Returns minimal data for efficient polling.
    """
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    response = {
        "id": report.id,
        "status": report.status.value,
        "progress": 100 if report.status == ReportStatus.COMPLETED else (50 if report.status == ReportStatus.GENERATING else 0),
    }
    
    if report.status == ReportStatus.FAILED:
        response["error_type"] = report.error_type
        response["error_message"] = report.error_message
    
    if report.status == ReportStatus.COMPLETED:
        response["completed_at"] = report.completed_at.isoformat() if report.completed_at else None
        response["generation_time_ms"] = report.generation_time_ms
    
    return response
