"""
Leads Router

Admin endpoints for managing leads and lead nurturing.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.user_behavior_signal import UserBehaviorSignal
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadStats,
)
from app.core.dependencies import get_current_admin_user
from app.services.audit import log_event
from app.services import email_service

router = APIRouter()


@router.get("/stats", response_model=LeadStats)
def get_lead_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get lead pipeline statistics."""
    total = db.query(Lead).count()
    
    status_counts = {}
    for st in LeadStatus:
        count = db.query(Lead).filter(Lead.status == st).count()
        status_counts[st.value] = count
    
    converted = status_counts.get("converted", 0)
    conversion_rate = (converted / total * 100) if total > 0 else 0.0
    
    return {
        "total": total,
        "new": status_counts.get("new", 0),
        "contacted": status_counts.get("contacted", 0),
        "qualified": status_counts.get("qualified", 0),
        "nurturing": status_counts.get("nurturing", 0),
        "converted": converted,
        "lost": status_counts.get("lost", 0),
        "conversion_rate": round(conversion_rate, 2),
    }


@router.get("/", response_model=LeadListResponse)
def list_leads(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, description="new|contacted|qualified|nurturing|converted|lost"),
    source_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by email, name, or company"),
    assigned_to_id: Optional[int] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List leads with filtering and search."""
    q = db.query(Lead)
    
    if status_filter:
        try:
            q = q.filter(Lead.status == LeadStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status_filter")
    
    if source_filter:
        try:
            q = q.filter(Lead.source == LeadSource(source_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid source_filter")
    
    if search:
        s = f"%{search}%"
        q = q.filter(
            (Lead.email.ilike(s)) |
            (Lead.name.ilike(s)) |
            (Lead.company.ilike(s))
        )
    
    if assigned_to_id:
        q = q.filter(Lead.assigned_to_id == assigned_to_id)
    
    total = q.count()
    items = q.order_by(desc(Lead.created_at)).offset(skip).limit(limit).all()
    
    return {
        "items": [_lead_to_response(lead) for lead in items],
        "total": total,
    }


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Create a new lead."""
    existing = db.query(Lead).filter(Lead.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lead with this email already exists")
    
    try:
        source_enum = LeadSource(payload.source) if payload.source else LeadSource.ORGANIC
    except ValueError:
        source_enum = LeadSource.ORGANIC
    
    lead = Lead(
        email=payload.email,
        name=payload.name,
        company=payload.company,
        phone=payload.phone,
        source=source_enum,
        interest_category=payload.interest_category,
        notes=payload.notes,
        opportunity_id=payload.opportunity_id,
        email_opt_in=payload.email_opt_in if payload.email_opt_in is not None else True,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    log_event(
        db,
        action="admin.lead.create",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="lead",
        resource_id=lead.id,
        metadata={"email": lead.email, "source": lead.source.value},
    )
    
    if lead.email_opt_in and lead.name:
        background_tasks.add_task(
            email_service.send_welcome_email,
            to=lead.email,
            name=lead.name or "there"
        )
    
    # Capture first-party behavior signal
    behavior_signal = UserBehaviorSignal(
        user_id=admin_user.id,
        entity_type="lead",
        entity_id=lead.id,
        action="created",
        meta={"email": lead.email, "source": lead.source.value if lead.source else "organic"},
    )
    db.add(behavior_signal)
    db.commit()
    
    return _lead_to_response(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get a specific lead by ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_to_response(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Update a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    old_status = lead.status.value if lead.status else None
    data = payload.dict(exclude_unset=True)
    
    if "status" in data and data["status"] is not None:
        try:
            new_status = LeadStatus(data["status"])
            lead.status = new_status
            
            if new_status == LeadStatus.CONTACTED and not lead.last_contacted_at:
                lead.last_contacted_at = datetime.utcnow()
            elif new_status == LeadStatus.CONVERTED:
                lead.converted_at = datetime.utcnow()
            
            if lead.email_opt_in and old_status != data["status"]:
                background_tasks.add_task(
                    email_service.send_lead_status_update_email,
                    to=lead.email,
                    name=lead.name or "there",
                    old_status=old_status,
                    new_status=data["status"]
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
        data.pop("status", None)
    
    if "source" in data and data["source"] is not None:
        try:
            lead.source = LeadSource(data["source"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid source")
        data.pop("source", None)
    
    for k, v in data.items():
        setattr(lead, k, v)
    
    db.commit()
    db.refresh(lead)
    
    log_event(
        db,
        action="admin.lead.update",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="lead",
        resource_id=lead_id,
        metadata={"fields": list(payload.dict(exclude_unset=True).keys())},
    )
    
    return _lead_to_response(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    email = lead.email
    db.delete(lead)
    db.commit()
    
    log_event(
        db,
        action="admin.lead.delete",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="lead",
        resource_id=lead_id,
        metadata={"email": email},
    )
    
    return None


@router.post("/{lead_id}/send-nurture-email")
async def send_nurture_email(
    lead_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Manually trigger the next nurture email for a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.email_opt_in:
        raise HTTPException(status_code=400, detail="Lead has opted out of emails")
    
    next_step = lead.email_sequence_step + 1
    if next_step > 3:
        raise HTTPException(status_code=400, detail="Lead has completed the nurture sequence")
    
    result = await email_service.send_lead_nurture_email(
        to=lead.email,
        name=lead.name or "there",
        step=next_step,
    )
    
    if result.get("success"):
        lead.email_sequence_step = next_step
        lead.last_email_sent_at = datetime.utcnow()
        db.commit()
        
        log_event(
            db,
            action="admin.lead.nurture_email",
            actor=admin_user,
            actor_type="admin",
            request=request,
            resource_type="lead",
            resource_id=lead_id,
            metadata={"step": next_step, "email_id": result.get("id")},
        )
        
        return {"message": f"Nurture email step {next_step} sent", "email_id": result.get("id")}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email"))


@router.post("/bulk-nurture")
async def bulk_nurture_leads(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Send nurture emails to all eligible leads (status=nurturing, opted in, sequence < 3)."""
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=3)
    
    leads = db.query(Lead).filter(
        Lead.status == LeadStatus.NURTURING,
        Lead.email_opt_in == True,
        Lead.email_sequence_step < 3,
        (Lead.last_email_sent_at == None) | (Lead.last_email_sent_at < cutoff)
    ).all()
    
    sent_count = 0
    errors = []
    
    for lead in leads:
        next_step = lead.email_sequence_step + 1
        result = await email_service.send_lead_nurture_email(
            to=lead.email,
            name=lead.name or "there",
            step=next_step,
        )
        
        if result.get("success"):
            lead.email_sequence_step = next_step
            lead.last_email_sent_at = datetime.utcnow()
            sent_count += 1
        else:
            errors.append({"email": lead.email, "error": result.get("error")})
    
    db.commit()
    
    log_event(
        db,
        action="admin.lead.bulk_nurture",
        actor=admin_user,
        actor_type="admin",
        request=request,
        metadata={"sent_count": sent_count, "error_count": len(errors)},
    )
    
    return {
        "message": f"Sent {sent_count} nurture emails",
        "sent_count": sent_count,
        "error_count": len(errors),
        "errors": errors[:10],
    }


def _lead_to_response(lead: Lead) -> dict:
    """Convert Lead model to response dict."""
    return {
        "id": lead.id,
        "email": lead.email,
        "name": lead.name,
        "company": lead.company,
        "phone": lead.phone,
        "status": lead.status.value if lead.status else "new",
        "source": lead.source.value if lead.source else "organic",
        "interest_category": lead.interest_category,
        "notes": lead.notes,
        "user_id": lead.user_id,
        "assigned_to_id": lead.assigned_to_id,
        "opportunity_id": lead.opportunity_id,
        "last_contacted_at": lead.last_contacted_at,
        "converted_at": lead.converted_at,
        "email_opt_in": lead.email_opt_in,
        "email_sequence_step": lead.email_sequence_step,
        "last_email_sent_at": lead.last_email_sent_at,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }
