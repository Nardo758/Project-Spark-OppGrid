"""
Admin Router

Administrative endpoints for managing users, content, and platform
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta, timezone
import os
import httpx

from app.db.database import get_db
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.validation import Validation
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.partner import PartnerOutreach, PartnerOutreachStatus
from app.models.tracking import TrackingEvent
from app.models.audit_log import AuditLog
from app.schemas.admin import (
    AdminUserListItem,
    AdminUserDetail,
    AdminUserUpdate,
    AdminBanUser,
    AdminStats,
    AdminOpportunityListItem,
    AdminStripeWebhookEventList,
    AdminPayPerUnlockAttemptList,
    AdminIdeaValidationList,
    AdminPartnerOutreach,
    AdminPartnerOutreachCreate,
    AdminPartnerOutreachUpdate,
)
from app.core.dependencies import get_current_admin_user
from app.services.audit import log_event
from anthropic import Anthropic
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get platform statistics for admin dashboard"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    banned_users = db.query(User).filter(User.is_banned == True).count()

    total_opportunities = db.query(Opportunity).count()
    total_validations = db.query(Validation).count()
    total_comments = db.query(Comment).count()
    total_notifications = db.query(Notification).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "banned_users": banned_users,
        "total_opportunities": total_opportunities,
        "total_validations": total_validations,
        "total_comments": total_comments,
        "total_notifications": total_notifications
    }


@router.get("/stripe/webhook-events", response_model=AdminStripeWebhookEventList)
def list_stripe_webhook_events(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, description="processing|processed|failed"),
    event_type: Optional[str] = Query(None),
    livemode: Optional[bool] = Query(None),
    search_event_id: Optional[str] = Query(None, description="Substring match on evt_* id"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List recent Stripe webhook events for debugging and reliability monitoring."""
    from app.models.stripe_event import StripeWebhookEvent, StripeWebhookEventStatus

    q = db.query(StripeWebhookEvent)

    if status_filter:
        try:
            q = q.filter(StripeWebhookEvent.status == StripeWebhookEventStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status_filter")

    if event_type:
        q = q.filter(StripeWebhookEvent.event_type == event_type)

    if livemode is not None:
        q = q.filter(StripeWebhookEvent.livemode == livemode)

    if search_event_id:
        q = q.filter(StripeWebhookEvent.stripe_event_id.ilike(f"%{search_event_id}%"))

    total = q.count()
    items = q.order_by(desc(StripeWebhookEvent.received_at)).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.get("/stripe/pay-per-unlock-attempts", response_model=AdminPayPerUnlockAttemptList)
def list_pay_per_unlock_attempts(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None),
    opportunity_id: Optional[int] = Query(None),
    attempt_date: Optional[date] = Query(None),
    status_filter: Optional[str] = Query(None, description="created|succeeded|failed|canceled"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List pay-per-unlock attempts (includes pre-payment attempts to detect spam/race)."""
    from app.models.stripe_event import PayPerUnlockAttempt, PayPerUnlockAttemptStatus

    q = db.query(PayPerUnlockAttempt)

    if user_id is not None:
        q = q.filter(PayPerUnlockAttempt.user_id == user_id)
    if opportunity_id is not None:
        q = q.filter(PayPerUnlockAttempt.opportunity_id == opportunity_id)
    if attempt_date is not None:
        q = q.filter(PayPerUnlockAttempt.attempt_date == attempt_date)

    if status_filter:
        try:
            q = q.filter(PayPerUnlockAttempt.status == PayPerUnlockAttemptStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status_filter")

    total = q.count()
    items = q.order_by(desc(PayPerUnlockAttempt.created_at)).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.get("/idea-validations", response_model=AdminIdeaValidationList)
def list_idea_validations(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(
        None,
        description="pending_payment|paid|processing|completed|failed",
    ),
    user_id: Optional[int] = Query(None),
    search_title: Optional[str] = Query(None),
    payment_intent: Optional[str] = Query(None, description="Substring match on pi_* id"),
    include_result: bool = Query(False, description="When true, include result_json and error_message"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List persisted Idea Validations for debugging (processing/failed/paid)."""
    from app.models.idea_validation import IdeaValidation, IdeaValidationStatus

    q = db.query(IdeaValidation)

    if status_filter:
        try:
            q = q.filter(IdeaValidation.status == IdeaValidationStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status_filter")

    if user_id is not None:
        q = q.filter(IdeaValidation.user_id == user_id)

    if search_title:
        q = q.filter(IdeaValidation.title.ilike(f"%{search_title}%"))

    if payment_intent:
        q = q.filter(IdeaValidation.stripe_payment_intent_id.ilike(f"%{payment_intent}%"))

    total = q.count()
    rows = q.order_by(desc(IdeaValidation.created_at)).offset(skip).limit(limit).all()

    # Return dicts so we can omit large fields unless explicitly requested.
    items = []
    for iv in rows:
        item = {
            "id": iv.id,
            "user_id": iv.user_id,
            "title": iv.title,
            "category": iv.category,
            "status": iv.status.value if hasattr(iv.status, "value") else str(iv.status),
            "stripe_payment_intent_id": iv.stripe_payment_intent_id,
            "amount_cents": iv.amount_cents,
            "currency": iv.currency,
            "opportunity_score": iv.opportunity_score,
            "validation_confidence": iv.validation_confidence,
            "summary": iv.summary,
            "created_at": iv.created_at,
            "updated_at": iv.updated_at,
        }
        if include_result:
            item["result_json"] = iv.result_json
            item["error_message"] = iv.error_message
        items.append(item)

    return {"items": items, "total": total}


@router.get("/partners", response_model=List[AdminPartnerOutreach])
def list_partners(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, description="identified|contacted|in_talks|active|paused|rejected"),
    search: Optional[str] = Query(None, description="Substring match on name/category"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(PartnerOutreach)

    if status_filter:
        try:
            q = q.filter(PartnerOutreach.status == PartnerOutreachStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status_filter")

    if search:
        s = f"%{search}%"
        q = q.filter(
            (PartnerOutreach.name.ilike(s)) |
            (PartnerOutreach.category.ilike(s))
        )

    items = q.order_by(desc(PartnerOutreach.created_at)).offset(skip).limit(limit).all()
    return items


@router.post("/partners", response_model=AdminPartnerOutreach, status_code=status.HTTP_201_CREATED)
def create_partner(
    payload: AdminPartnerOutreachCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    status_value = payload.status or PartnerOutreachStatus.IDENTIFIED.value
    try:
        status_enum = PartnerOutreachStatus(status_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    partner = PartnerOutreach(
        name=payload.name,
        category=payload.category,
        website_url=payload.website_url,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        status=status_enum,
        notes=payload.notes,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)

    log_event(
        db,
        action="admin.partner.create",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="partner_outreach",
        resource_id=partner.id,
        metadata={"name": partner.name, "status": partner.status.value if hasattr(partner.status, "value") else str(partner.status)},
    )
    return partner


@router.patch("/partners/{partner_id}", response_model=AdminPartnerOutreach)
def update_partner(
    partner_id: int,
    payload: AdminPartnerOutreachUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    partner = db.query(PartnerOutreach).filter(PartnerOutreach.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    data = payload.dict(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        try:
            partner.status = PartnerOutreachStatus(data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
        data.pop("status", None)

    for k, v in data.items():
        setattr(partner, k, v)

    db.commit()
    db.refresh(partner)

    log_event(
        db,
        action="admin.partner.update",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="partner_outreach",
        resource_id=partner_id,
        metadata={"fields": list(payload.dict(exclude_unset=True).keys())},
    )
    return partner


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner(
    partner_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    partner = db.query(PartnerOutreach).filter(PartnerOutreach.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    name = partner.name
    db.delete(partner)
    db.commit()

    log_event(
        db,
        action="admin.partner.delete",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="partner_outreach",
        resource_id=partner_id,
        metadata={"name": name},
    )
    return None


@router.get("/tracking/summary")
def tracking_summary(
    days: int = Query(7, ge=1, le=90),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)

    total = db.query(TrackingEvent).filter(TrackingEvent.created_at >= since).count()
    page_views = db.query(TrackingEvent).filter(
        TrackingEvent.created_at >= since,
        TrackingEvent.name == "page_view",
    ).count()

    top_events = db.query(
        TrackingEvent.name,
        func.count(TrackingEvent.id).label("count"),
    ).filter(
        TrackingEvent.created_at >= since
    ).group_by(
        TrackingEvent.name
    ).order_by(
        desc("count")
    ).limit(10).all()

    top_paths = db.query(
        TrackingEvent.path,
        func.count(TrackingEvent.id).label("count"),
    ).filter(
        TrackingEvent.created_at >= since,
        TrackingEvent.path.isnot(None),
    ).group_by(
        TrackingEvent.path
    ).order_by(
        desc("count")
    ).limit(10).all()

    return {
        "days": days,
        "total_events": total,
        "page_views": page_views,
        "top_events": [{"name": name, "count": count} for name, count in top_events],
        "top_paths": [{"path": path, "count": count} for path, count in top_paths],
    }


@router.get("/tracking/events")
def list_tracking_events(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    name: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(TrackingEvent)
    if name:
        q = q.filter(TrackingEvent.name == name)
    total = q.count()
    items = q.order_by(desc(TrackingEvent.created_at)).offset(skip).limit(limit).all()

    def _parse_props(s):
        if not s:
            return None
        try:
            import json
            return json.loads(s)
        except Exception:
            return None

    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "path": e.path,
                "referrer": e.referrer,
                "user_id": e.user_id,
                "anonymous_id": e.anonymous_id,
                "properties": _parse_props(e.properties),
                "created_at": e.created_at,
            }
            for e in items
        ],
    }


@router.get("/users", response_model=List[AdminUserListItem])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_banned: Optional[bool] = Query(None),
    is_admin: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List users with filtering and search"""
    query = db.query(User)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_pattern)) |
            (User.name.ilike(search_pattern))
        )

    if is_banned is not None:
        query = query.filter(User.is_banned == is_banned)

    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)

    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    # Order by created_at desc and paginate
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()

    # Convert to dict with coalesced NULL values
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_active": u.is_active if u.is_active is not None else False,
            "is_verified": u.is_verified if u.is_verified is not None else False,
            "is_admin": u.is_admin if u.is_admin is not None else False,
            "is_banned": u.is_banned if u.is_banned is not None else False,
            "impact_points": u.impact_points if u.impact_points is not None else 0,
            "created_at": u.created_at
        }
        for u in users
    ]


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get counts
    opportunity_count = db.query(Opportunity).filter(Opportunity.author_id == user_id).count()
    validation_count = db.query(Validation).filter(Validation.user_id == user_id).count()
    comment_count = db.query(Comment).filter(Comment.user_id == user_id).count()

    # Add computed fields with coalesced NULL values
    user_dict = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "oauth_provider": user.oauth_provider,
        "impact_points": user.impact_points if user.impact_points is not None else 0,
        "badges": user.badges,
        "is_active": user.is_active if user.is_active is not None else False,
        "is_verified": user.is_verified if user.is_verified is not None else False,
        "is_admin": user.is_admin if user.is_admin is not None else False,
        "is_banned": user.is_banned if user.is_banned is not None else False,
        "ban_reason": user.ban_reason,
        "otp_enabled": user.otp_enabled if user.otp_enabled is not None else False,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "opportunity_count": opportunity_count,
        "validation_count": validation_count,
        "comment_count": comment_count
    }

    return user_dict


@router.patch("/users/{user_id}", response_model=AdminUserDetail)
def update_user(
    user_id: int,
    user_update: AdminUserUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user settings (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admins from removing their own admin status
    if user_id == admin_user.id and user_update.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin status"
        )

    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Get counts for response
    opportunity_count = db.query(Opportunity).filter(Opportunity.author_id == user_id).count()
    validation_count = db.query(Validation).filter(Validation.user_id == user_id).count()
    comment_count = db.query(Comment).filter(Comment.user_id == user_id).count()

    # Coalesce NULL values
    user_dict = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "oauth_provider": user.oauth_provider,
        "impact_points": user.impact_points if user.impact_points is not None else 0,
        "badges": user.badges,
        "is_active": user.is_active if user.is_active is not None else False,
        "is_verified": user.is_verified if user.is_verified is not None else False,
        "is_admin": user.is_admin if user.is_admin is not None else False,
        "is_banned": user.is_banned if user.is_banned is not None else False,
        "ban_reason": user.ban_reason,
        "otp_enabled": user.otp_enabled if user.otp_enabled is not None else False,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "opportunity_count": opportunity_count,
        "validation_count": validation_count,
        "comment_count": comment_count
    }

    return user_dict


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    ban_data: AdminBanUser,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Ban a user"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admins from banning themselves
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself"
        )

    # Prevent banning other admins
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban admin users"
        )

    user.is_banned = True
    user.ban_reason = ban_data.ban_reason
    user.is_active = False
    db.commit()

    log_event(
        db,
        action="admin.user.ban",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="user",
        resource_id=user_id,
        metadata={"ban_reason": ban_data.ban_reason},
    )

    return {"message": "User banned successfully"}


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Unban a user"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_banned = False
    user.ban_reason = None
    user.is_active = True
    db.commit()

    log_event(
        db,
        action="admin.user.unban",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="user",
        resource_id=user_id,
    )

    return {"message": "User unbanned successfully"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (dangerous operation)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admins from deleting themselves
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Prevent deleting other admins
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )

    db.delete(user)
    db.commit()

    log_event(
        db,
        action="admin.user.delete",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="user",
        resource_id=user_id,
    )

    return {"message": "User deleted successfully"}


@router.get("/opportunities/count")
def count_opportunities(
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get total count of opportunities for pagination"""
    query = db.query(Opportunity)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Opportunity.title.ilike(search_pattern))
    
    return {"count": query.count()}


@router.get("/opportunities", response_model=List[AdminOpportunityListItem])
def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List opportunities with filtering"""
    query = db.query(
        Opportunity.id,
        Opportunity.title,
        Opportunity.author_id,
        User.name.label("author_name"),
        Opportunity.status,
        Opportunity.validation_count,
        Opportunity.created_at
    ).outerjoin(User, Opportunity.author_id == User.id)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Opportunity.title.ilike(search_pattern))

    if status_filter:
        query = query.filter(Opportunity.status == status_filter)

    # Order by created_at desc and paginate
    opportunities = query.order_by(desc(Opportunity.created_at)).offset(skip).limit(limit).all()

    return [
        {
            "id": opp.id,
            "title": opp.title,
            "author_id": opp.author_id or 0,
            "author_name": opp.author_name or "Web Scraper",
            "status": opp.status,
            "validation_count": opp.validation_count,
            "created_at": opp.created_at
        }
        for opp in opportunities
    ]


@router.delete("/opportunities/{opportunity_id}")
def delete_opportunity(
    opportunity_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    db.delete(opportunity)
    db.commit()

    log_event(
        db,
        action="admin.opportunity.delete",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="opportunity",
        resource_id=opportunity_id,
        metadata={"title": getattr(opportunity, "title", None)},
    )

    return {"message": "Opportunity deleted successfully"}


# ===== MODERATION ENDPOINTS =====

@router.get("/moderation/stats")
def get_moderation_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get moderation queue statistics"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    pending_review = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'pending_review'
    ).count()
    
    needs_edit = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'needs_edit'
    ).count()
    
    approved_today = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'approved',
        Opportunity.updated_at >= today_start
    ).count()
    
    rejected_today = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'rejected',
        Opportunity.updated_at >= today_start
    ).count()
    
    return {
        "pending_review": pending_review,
        "needs_edit": needs_edit,
        "approved_today": approved_today,
        "rejected_today": rejected_today
    }


@router.get("/moderation/queue")
def get_moderation_queue(
    moderation_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get opportunities in the moderation queue"""
    query = db.query(Opportunity)
    
    if moderation_status:
        query = query.filter(Opportunity.moderation_status == moderation_status)
    
    opportunities = query.order_by(desc(Opportunity.created_at)).offset(skip).limit(limit).all()
    
    return [
        {
            "id": opp.id,
            "title": opp.title,
            "category": opp.category,
            "moderation_status": opp.moderation_status,
            "source_platform": opp.source_platform,
            "created_at": opp.created_at,
            "updated_at": opp.updated_at
        }
        for opp in opportunities
    ]


@router.get("/opportunities/{opportunity_id}")
def get_opportunity_detail(
    opportunity_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get full opportunity details for moderation review"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "description": opportunity.description,
        "category": opportunity.category,
        "subcategory": opportunity.subcategory,
        "moderation_status": opportunity.moderation_status,
        "status": opportunity.status,
        "source_platform": opportunity.source_platform,
        "source_url": opportunity.source_url,
        "raw_source_data": opportunity.raw_source_data,
        "ai_summary": opportunity.ai_summary,
        "ai_analyzed": opportunity.ai_analyzed,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at
    }


from pydantic import BaseModel

class ModerationUpdateRequest(BaseModel):
    moderation_status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

@router.patch("/moderation/{opportunity_id}")
def update_moderation_status(
    opportunity_id: int,
    body: ModerationUpdateRequest,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update opportunity moderation status and/or content"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    updated_fields = []
    
    if body.moderation_status:
        if body.moderation_status not in ['pending_review', 'approved', 'rejected', 'needs_edit']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid moderation status"
            )
        opportunity.moderation_status = body.moderation_status
        updated_fields.append('moderation_status')
    
    if body.title:
        opportunity.title = body.title[:500]
        updated_fields.append('title')
    
    if body.description:
        opportunity.description = body.description[:5000]
        updated_fields.append('description')
    
    if body.category:
        opportunity.category = body.category[:100]
        updated_fields.append('category')
    
    opportunity.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    log_event(
        db,
        action="admin.moderation.update",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="opportunity",
        resource_id=opportunity_id,
        metadata={"updated_fields": updated_fields, "new_status": body.moderation_status},
    )
    
    return {"message": "Opportunity updated successfully", "updated_fields": updated_fields}


@router.post("/opportunities/recategorize")
async def recategorize_opportunities(
    request: Request,
    background_tasks: BackgroundTasks,
    limit: int = Query(100, ge=1, le=500, description="Max opportunities to process"),
    only_general: bool = Query(True, description="Only update opportunities with 'general' category"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Batch recategorize opportunities using AI analysis"""
    
    query = db.query(Opportunity)
    
    if only_general:
        query = query.filter(
            (Opportunity.category.ilike('%general%')) | 
            (Opportunity.category == None) |
            (Opportunity.category == '')
        )
    
    opportunities = query.order_by(Opportunity.created_at.desc()).limit(limit).all()
    
    if not opportunities:
        return {"message": "No opportunities to recategorize", "processed": 0}
    
    from app.services.llm_ai_engine import get_anthropic_client
    client = get_anthropic_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI service not available")
    updated_count = 0
    skipped_count = 0
    errors = []
    
    valid_categories = {
        'technology': 'Technology',
        'health & wellness': 'Health & Wellness',
        'health and wellness': 'Health & Wellness',
        'healthcare': 'Health & Wellness',
        'money & finance': 'Money & Finance',
        'money and finance': 'Money & Finance',
        'finance': 'Money & Finance',
        'financial': 'Money & Finance',
        'education & learning': 'Education & Learning',
        'education and learning': 'Education & Learning',
        'education': 'Education & Learning',
        'shopping & services': 'Shopping & Services',
        'shopping and services': 'Shopping & Services',
        'retail': 'Shopping & Services',
        'home & living': 'Home & Living',
        'home and living': 'Home & Living',
        'home services': 'Home & Living',
        'transportation': 'Transportation',
        'entertainment & social': 'Entertainment & Social',
        'entertainment and social': 'Entertainment & Social',
        'entertainment': 'Entertainment & Social',
        'food & beverage': 'Food & Beverage',
        'food and beverage': 'Food & Beverage',
        'restaurant': 'Food & Beverage',
        'real estate': 'Real Estate',
        'b2b services': 'B2B Services',
        'b2b': 'B2B Services',
        'professional': 'B2B Services',
        'fitness': 'Health & Wellness',
        'beauty': 'Shopping & Services',
        'automotive': 'Transportation',
        'travel': 'Transportation',
        'pet services': 'Shopping & Services',
    }
    
    for opp in opportunities:
        try:
            context = f"""
Title: {opp.title or 'Unknown'}
Description: {opp.description or 'No description'}
Current Category: {opp.category or 'None'}
City: {opp.city or 'Unknown'}
"""
            
            prompt = f"""Analyze this business opportunity and determine the best category and improved title.

{context}

Categories to choose from:
- Technology
- Health & Wellness
- Money & Finance
- Education & Learning
- Shopping & Services
- Home & Living
- Transportation
- Entertainment & Social
- Food & Beverage
- Real Estate
- B2B Services

Respond in JSON format:
{{
  "category": "Best matching category from list above",
  "title": "Professional, descriptive title (20-60 chars)",
  "reason": "Brief explanation"
}}"""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            response = message.content[0].text if message.content else ""
            
            try:
                import re
                json_match = re.search(r'\{[\s\S]*?\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                    
                    new_category = result.get('category', '').strip()
                    new_title = result.get('title', '').strip()
                    
                    updated = False
                    category_key = new_category.lower()
                    
                    if category_key in valid_categories:
                        normalized_category = valid_categories[category_key]
                        opp.category = normalized_category
                        updated = True
                    else:
                        errors.append(f"Opportunity {opp.id}: Invalid category '{new_category}'")
                        skipped_count += 1
                    
                    if new_title and len(new_title) >= 20:
                        opp.title = new_title[:500]
                        updated = True
                    
                    if updated:
                        opp.ai_analyzed = True
                        opp.ai_analyzed_at = datetime.utcnow()
                        updated_count += 1
                else:
                    errors.append(f"Opportunity {opp.id}: No JSON in response")
                    skipped_count += 1
                    
            except json.JSONDecodeError as e:
                errors.append(f"Opportunity {opp.id}: JSON parse error - {str(e)[:50]}")
                skipped_count += 1
                
        except Exception as e:
            errors.append(f"Opportunity {opp.id}: {str(e)[:100]}")
            logger.warning(f"Failed to recategorize opportunity {opp.id}: {e}")
    
    db.commit()
    
    log_event(
        db,
        action="admin.opportunities.recategorize",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="opportunity",
        metadata={"processed": updated_count, "total": len(opportunities), "errors": len(errors)},
    )
    
    return {
        "message": f"Recategorized {updated_count} opportunities",
        "processed": updated_count,
        "skipped": skipped_count,
        "total": len(opportunities),
        "errors": errors[:20] if errors else []
    }


@router.post("/signals/reprocess")
async def reprocess_signals(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Max signals to reprocess"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reprocess existing Google Maps signals through updated categorization pipeline"""
    from app.services.signal_to_opportunity import SignalToOpportunityService
    from app.models.scraped_data import ScrapedData
    
    unprocessed = db.query(ScrapedData).filter(
        ScrapedData.source_platform == 'apify_google_maps',
        ScrapedData.processed == False
    ).limit(limit).all()
    
    if not unprocessed:
        return {"message": "No unprocessed signals found", "processed": 0}
    
    service = SignalToOpportunityService(db)
    
    try:
        batch_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        result = service.process_batch(batch_id=batch_id, limit=limit)
        
        log_event(
            db,
            action="admin.signals.reprocess",
            actor=admin_user,
            actor_type="admin",
            request=request,
            resource_type="signal",
            metadata={"batch_id": batch_id, "result": result},
        )
        
        return {
            "message": f"Reprocessed signals",
            "batch_id": batch_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Signal reprocessing failed: {e}")
        return {
            "message": f"Reprocessing failed: {str(e)[:200]}",
            "processed": 0
        }


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a comment"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    db.delete(comment)
    db.commit()

    log_event(
        db,
        action="admin.comment.delete",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="comment",
        resource_id=comment_id,
    )

    return {"message": "Comment deleted successfully"}


@router.post("/users/{user_id}/promote")
def promote_to_admin(
    user_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Promote a user to admin"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an admin"
        )

    user.is_admin = True
    db.commit()

    log_event(
        db,
        action="admin.user.promote",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="user",
        resource_id=user_id,
    )

    return {"message": f"User {user.name} promoted to admin"}


@router.post("/users/{user_id}/demote")
def demote_from_admin(
    user_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Remove admin status from a user"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself"
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not an admin"
        )

    user.is_admin = False
    db.commit()

    log_event(
        db,
        action="admin.user.demote",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="user",
        resource_id=user_id,
    )

    return {"message": f"User {user.name} demoted from admin"}


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        q = q.filter(AuditLog.resource_id == resource_id)
    total = q.count()
    items = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": a.id,
                "actor_user_id": a.actor_user_id,
                "actor_type": a.actor_type,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "ip_address": a.ip_address,
                "created_at": a.created_at,
                "metadata_json": a.metadata_json,
            }
            for a in items
        ],
    }


@router.get("/job-runs")
def list_job_runs(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    job_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, description="running|succeeded|failed"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    from app.models.job_run import JobRun

    q = db.query(JobRun)
    if job_name:
        q = q.filter(JobRun.job_name == job_name)
    if status_filter:
        q = q.filter(JobRun.status == status_filter)
    total = q.count()
    items = q.order_by(desc(JobRun.started_at)).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "job_name": r.job_name,
                "status": r.status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "error": r.error,
                "details_json": r.details_json,
            }
            for r in items
        ],
    }


from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus


@router.get("/subscriptions")
def list_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tier_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all subscriptions"""
    query = db.query(
        Subscription,
        User.email,
        User.name
    ).join(User, Subscription.user_id == User.id)

    if tier_filter:
        try:
            tier = SubscriptionTier(tier_filter.upper())
            query = query.filter(Subscription.tier == tier)
        except ValueError:
            pass

    if status_filter:
        try:
            status_enum = SubscriptionStatus(status_filter)
            query = query.filter(Subscription.status == status_enum)
        except ValueError:
            pass

    total = query.count()
    results = query.order_by(desc(Subscription.created_at)).offset(skip).limit(limit).all()

    return {
        "subscriptions": [
            {
                "id": sub.id,
                "user_id": sub.user_id,
                "email": email,
                "name": name,
                "tier": sub.tier.value,
                "status": sub.status.value,
                "stripe_customer_id": sub.stripe_customer_id,
                "stripe_subscription_id": sub.stripe_subscription_id,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created_at": sub.created_at
            }
            for sub, email, name in results
        ],
        "total": total
    }


@router.post("/subscriptions/bulk-reset-invalid")
def bulk_reset_invalid_subscriptions(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reset all subscriptions with paid tiers but no Stripe subscription ID to FREE"""
    invalid_subs = db.query(Subscription).filter(
        Subscription.tier != SubscriptionTier.FREE,
        (Subscription.stripe_subscription_id == None) | (Subscription.stripe_subscription_id == '')
    ).all()
    
    count = len(invalid_subs)
    for sub in invalid_subs:
        sub.tier = SubscriptionTier.FREE
        sub.status = SubscriptionStatus.ACTIVE
    
    db.commit()
    return {"message": f"Reset {count} invalid subscriptions to FREE", "count": count}


@router.patch("/subscriptions/{subscription_id}/tier")
def update_subscription_tier(
    subscription_id: int,
    tier: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Manually update a user's subscription tier (admin override)"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    try:
        new_tier = SubscriptionTier(tier.upper())
    except ValueError:
        valid_tiers = [t.value for t in SubscriptionTier]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Valid options: {', '.join(valid_tiers)}"
        )

    subscription.tier = new_tier
    db.commit()

    return {"message": f"Subscription updated to {new_tier.value}"}


@router.post("/users/{user_id}/grant-subscription")
def grant_subscription(
    user_id: int,
    tier: str = Query(...),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Grant or create a subscription for a user"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        new_tier = SubscriptionTier(tier.upper())
    except ValueError:
        valid_tiers = [t.value for t in SubscriptionTier]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Valid options: {', '.join(valid_tiers)}"
        )

    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()

    if subscription:
        subscription.tier = new_tier
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        subscription = Subscription(
            user_id=user_id,
            tier=new_tier,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)

    db.commit()

    return {"message": f"Granted {tier} subscription to user {user.name}"}


@router.get("/map-usage/stats")
def get_map_usage_stats(
    days: int = Query(30, ge=1, le=365),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get map usage statistics for admin dashboard"""
    from datetime import datetime, timedelta
    from app.models.user_map_session import UserMapSession
    from app.models.census_demographics import (
        MarketGrowthTrajectory,
        CensusMigrationFlow,
        CensusServiceArea,
    )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    total_sessions = db.query(UserMapSession).count()
    recent_sessions = db.query(UserMapSession).filter(
        UserMapSession.created_at >= cutoff_date
    ).count()
    
    unique_users = db.query(func.count(func.distinct(UserMapSession.user_id))).filter(
        UserMapSession.created_at >= cutoff_date
    ).scalar() or 0
    
    growth_trajectories = db.query(MarketGrowthTrajectory).filter(
        MarketGrowthTrajectory.is_active == True
    ).count()
    
    migration_flows = db.query(CensusMigrationFlow).count()
    
    service_areas = db.query(CensusServiceArea).count()
    
    from sqlalchemy import text
    layer_usage_query = db.execute(text("""
        SELECT kv.key as layer_name, COUNT(*) as usage_count
        FROM user_map_sessions, 
             jsonb_each_text(layer_state) AS kv
        WHERE created_at >= :cutoff_date
          AND layer_state IS NOT NULL
          AND kv.value = 'true'
        GROUP BY kv.key
        ORDER BY usage_count DESC
    """), {"cutoff_date": cutoff_date})
    layer_usage = {row.layer_name: row.usage_count for row in layer_usage_query}
    
    daily_sessions = db.query(
        func.date_trunc('day', UserMapSession.created_at).label('date'),
        func.count(UserMapSession.id).label('count')
    ).filter(
        UserMapSession.created_at >= cutoff_date
    ).group_by(
        func.date_trunc('day', UserMapSession.created_at)
    ).order_by(
        func.date_trunc('day', UserMapSession.created_at)
    ).all()
    
    return {
        "total_sessions": total_sessions,
        "recent_sessions": recent_sessions,
        "unique_users": unique_users,
        "growth_trajectories": growth_trajectories,
        "migration_flows": migration_flows,
        "service_areas": service_areas,
        "layer_usage": layer_usage,
        "daily_sessions": [
            {"date": str(d.date), "count": d.count}
            for d in daily_sessions
        ],
        "period_days": days
    }


@router.get("/map-usage/popular-opportunities")
def get_popular_map_opportunities(
    limit: int = Query(10, ge=1, le=50),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get opportunities with most map views/sessions"""
    from app.models.census_demographics import CensusServiceArea
    
    popular = db.query(
        CensusServiceArea.opportunity_id,
        Opportunity.title,
        Opportunity.category,
        CensusServiceArea.signal_count,
        CensusServiceArea.total_population,
        CensusServiceArea.addressable_market_value,
    ).join(
        Opportunity, CensusServiceArea.opportunity_id == Opportunity.id
    ).order_by(
        desc(CensusServiceArea.signal_count)
    ).limit(limit).all()
    
    return {
        "opportunities": [
            {
                "opportunity_id": p.opportunity_id,
                "title": p.title,
                "category": p.category,
                "signal_count": p.signal_count,
                "total_population": p.total_population,
                "addressable_market": p.addressable_market_value,
            }
            for p in popular
        ]
    }


@router.get("/map-usage/growth-trajectories")
def get_growth_trajectories_admin(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get all growth trajectory data for admin review"""
    from app.models.census_demographics import MarketGrowthTrajectory
    
    trajectories = db.query(MarketGrowthTrajectory).filter(
        MarketGrowthTrajectory.is_active == True
    ).order_by(desc(MarketGrowthTrajectory.growth_score)).all()
    
    return {
        "trajectories": [
            {
                "id": t.id,
                "city": t.city,
                "state_fips": t.state_fips,
                "geography_name": t.geography_name,
                "growth_category": t.growth_category.value if t.growth_category else None,
                "growth_score": t.growth_score,
                "population_growth_rate": t.population_growth_rate,
                "net_migration_rate": t.net_migration_rate,
                "latitude": float(t.latitude) if t.latitude else None,
                "longitude": float(t.longitude) if t.longitude else None,
            }
            for t in trajectories
        ],
        "total": len(trajectories)
    }


@router.get("/map-usage/migration-flows")
def get_migration_flows_admin(
    limit: int = Query(50, ge=1, le=200),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get top migration flows for admin review"""
    from app.models.census_demographics import CensusMigrationFlow
    
    flows = db.query(CensusMigrationFlow).order_by(
        desc(CensusMigrationFlow.flow_count)
    ).limit(limit).all()
    
    return {
        "flows": [
            {
                "id": f.id,
                "origin_name": f.origin_name,
                "destination_name": f.destination_name,
                "flow_count": f.flow_count,
                "year": f.year,
                "origin_state_fips": f.origin_state_fips,
                "destination_state_fips": f.destination_state_fips,
            }
            for f in flows
        ],
        "total": len(flows)
    }


# ==================== Marketing & User Management ====================

@router.get("/marketing/users")
def get_marketing_users(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    tier_filter: Optional[str] = Query(None, description="free|pro|business|enterprise"),
    verified_only: bool = Query(False),
    has_subscription: Optional[bool] = Query(None),
    created_after: Optional[date] = Query(None),
    created_before: Optional[date] = Query(None),
    search: Optional[str] = Query(None, description="Search by name or email"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get list of users for marketing purposes with filters and pagination"""
    from app.models.subscription import Subscription
    from sqlalchemy.orm import joinedload
    from datetime import datetime, timezone
    
    q = db.query(User).outerjoin(Subscription, User.id == Subscription.user_id).filter(User.is_banned == False)
    
    if verified_only:
        q = q.filter(User.is_verified == True)
    
    if created_after:
        q = q.filter(User.created_at >= datetime.combine(created_after, datetime.min.time()).replace(tzinfo=timezone.utc))
    
    if created_before:
        q = q.filter(User.created_at <= datetime.combine(created_before, datetime.max.time()).replace(tzinfo=timezone.utc))
    
    if search:
        search_term = f"%{search}%"
        q = q.filter((User.name.ilike(search_term)) | (User.email.ilike(search_term)))
    
    if tier_filter:
        tier_lower = tier_filter.lower()
        if tier_lower == "free":
            q = q.filter((Subscription.id == None) | (Subscription.tier == "free"))
        else:
            q = q.filter(Subscription.tier == tier_lower)
    
    total = q.count()
    
    users_with_subs = q.add_columns(Subscription.tier).order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    user_list = []
    for row in users_with_subs:
        u = row[0]
        sub_tier = row[1]
        tier = sub_tier.value if sub_tier and hasattr(sub_tier, 'value') else (str(sub_tier) if sub_tier else "free")
            
        user_list.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "tier": tier,
            "is_verified": u.is_verified,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "oauth_provider": u.oauth_provider,
        })
    
    return {
        "users": user_list,
        "total": total,
        "page_size": limit,
        "skip": skip,
    }


@router.get("/marketing/users/export")
def export_marketing_users(
    tier_filter: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    format: str = Query("json", description="json|csv"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Export all users for marketing - returns all matching users"""
    from app.models.subscription import Subscription
    from fastapi.responses import Response
    import csv
    import io
    
    q = db.query(User).outerjoin(Subscription, User.id == Subscription.user_id).filter(
        User.is_banned == False, User.is_active == True
    )
    
    if verified_only:
        q = q.filter(User.is_verified == True)
    
    if tier_filter:
        tier_lower = tier_filter.lower()
        if tier_lower == "free":
            q = q.filter((Subscription.id == None) | (Subscription.tier == "free"))
        else:
            q = q.filter(Subscription.tier == tier_lower)
    
    users_with_subs = q.add_columns(Subscription.tier).order_by(desc(User.created_at)).all()
    
    user_list = []
    for row in users_with_subs:
        u = row[0]
        sub_tier = row[1]
        tier = sub_tier.value if sub_tier and hasattr(sub_tier, 'value') else (str(sub_tier) if sub_tier else "free")
            
        user_list.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "tier": tier,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "oauth_provider": u.oauth_provider or "email",
        })
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "email", "name", "tier", "is_verified", "created_at", "oauth_provider"])
        writer.writeheader()
        writer.writerows(user_list)
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=oppgrid_users.csv"}
        )
    
    return {"users": user_list, "total": len(user_list)}


@router.post("/marketing/send-campaign")
async def send_marketing_campaign(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Send marketing email campaign to selected users via Resend"""
    import os
    import resend
    
    body = await request.json()
    user_ids = body.get("user_ids", [])
    subject = body.get("subject", "")
    html_content = body.get("html_content", "")
    text_content = body.get("text_content", "")
    
    if not subject or (not html_content and not text_content):
        raise HTTPException(status_code=400, detail="Subject and content are required")
    
    if not user_ids:
        raise HTTPException(status_code=400, detail="No users selected")
    
    resend_key = os.environ.get("RESEND_API_KEY")
    if not resend_key:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    resend.api_key = resend_key
    
    users = db.query(User).filter(User.id.in_(user_ids), User.is_banned == False).all()
    
    sent_count = 0
    failed_count = 0
    errors = []
    
    for user in users:
        try:
            params = {
                "from": "OppGrid <noreply@oppgrid.com>",
                "to": [user.email],
                "subject": subject,
            }
            if html_content:
                params["html"] = html_content.replace("{{name}}", user.name or "there")
            if text_content:
                params["text"] = text_content.replace("{{name}}", user.name or "there")
            
            resend.Emails.send(params)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({"user_id": user.id, "email": user.email, "error": str(e)})
    
    log_event(
        db, 
        "marketing_campaign_sent",
        user_id=admin_user.id,
        details={"sent": sent_count, "failed": failed_count, "subject": subject}
    )
    
    return {
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:10] if errors else [],
        "message": f"Campaign sent to {sent_count} users"
    }


@router.get("/marketing/stats")
def get_marketing_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get marketing statistics - user growth, tier distribution, etc."""
    from app.models.subscription import Subscription
    from datetime import datetime, timedelta, timezone
    
    total_users = db.query(User).filter(User.is_banned == False).count()
    verified_users = db.query(User).filter(User.is_verified == True, User.is_banned == False).count()
    
    now = datetime.now(timezone.utc)
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    
    new_users_7d = db.query(User).filter(User.created_at >= last_7_days, User.is_banned == False).count()
    new_users_30d = db.query(User).filter(User.created_at >= last_30_days, User.is_banned == False).count()
    
    tier_distribution = {"free": 0, "pro": 0, "business": 0, "enterprise": 0}
    subscriptions = db.query(Subscription).all()
    for sub in subscriptions:
        tier = sub.tier.value if hasattr(sub.tier, 'value') else str(sub.tier)
        if tier.lower() in tier_distribution:
            tier_distribution[tier.lower()] += 1
    
    tier_distribution["free"] = total_users - sum([tier_distribution["pro"], tier_distribution["business"], tier_distribution["enterprise"]])
    
    oauth_breakdown = {}
    users_with_oauth = db.query(User).filter(User.oauth_provider != None, User.is_banned == False).all()
    for u in users_with_oauth:
        provider = u.oauth_provider or "email"
        oauth_breakdown[provider] = oauth_breakdown.get(provider, 0) + 1
    oauth_breakdown["email"] = total_users - sum(oauth_breakdown.values())
    
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "new_users_7d": new_users_7d,
        "new_users_30d": new_users_30d,
        "tier_distribution": tier_distribution,
        "oauth_breakdown": oauth_breakdown,
        "verification_rate": round((verified_users / total_users * 100) if total_users > 0 else 0, 1),
    }


@router.post("/data-pipeline/trigger-scrape")
async def trigger_scrape_pipeline(
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Trigger the Apify scraper to start a new data collection run.
    Returns immediately with run_id. Use /data-pipeline/status to check progress.
    After scraper completes, call /data-pipeline/import-latest to import the data.
    """
    apify_token = os.getenv("APIFY_API_TOKEN", "")
    if not apify_token:
        raise HTTPException(status_code=500, detail="APIFY_API_TOKEN not configured")
    
    actor_id = "trudax/reddit-scraper-lite"
    run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={apify_token}"
    
    run_input = {
        "debugMode": False,
        "maxItems": 200,
        "maxPostCount": 200,
        "maxComments": 0,
        "proxy": {"useApifyProxy": True},
        "scrollTimeout": 40,
        "searchComments": False,
        "searchCommunities": False,
        "searchPosts": True,
        "searchUsers": False,
        "searches": [
            "frustrated with",
            "wish there was",
            "why is it so hard to",
            "anyone else annoyed by",
            "there should be an app for",
            "I hate how",
            "biggest pain point",
            "looking for solution to"
        ],
        "skipComments": True,
        "sort": "relevance",
        "time": "week"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(run_url, json=run_input)
        
        if response.status_code != 201:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger scraper: {response.status_code} - {response.text}"
            )
        
        run_data = response.json().get("data", {})
        return {
            "status": "started",
            "run_id": run_data.get("id"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "next_steps": [
                "Wait 5-10 minutes for scraper to complete",
                "Call GET /api/v1/admin/data-pipeline/scrape-status/{run_id} to check progress",
                "Call POST /api/v1/admin/data-pipeline/import-latest to import results"
            ]
        }


@router.get("/data-pipeline/scrape-status/{run_id}")
async def get_scrape_status(
    run_id: str,
    admin_user: User = Depends(get_current_admin_user),
):
    """Check the status of an Apify scraper run"""
    apify_token = os.getenv("APIFY_API_TOKEN", "")
    if not apify_token:
        raise HTTPException(status_code=500, detail="APIFY_API_TOKEN not configured")
    
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_token}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(status_url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Run not found")
        
        run_info = response.json().get("data", {})
        return {
            "run_id": run_id,
            "status": run_info.get("status"),
            "dataset_id": run_info.get("defaultDatasetId"),
            "started_at": run_info.get("startedAt"),
            "finished_at": run_info.get("finishedAt"),
        }


@router.post("/data-pipeline/import-latest")
async def import_latest_data(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Import the latest scraped data from Apify into the database.
    Uses the existing webhook import logic for consistency.
    """
    from app.routers.webhook import fetch_latest_apify_data
    
    try:
        result = await fetch_latest_apify_data(db=db)
        return {
            "status": "completed",
            "result": result,
            "message": "Import completed using existing pipeline"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/data-pipeline/status")
def get_pipeline_status(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get current data pipeline status and recent import stats"""
    total_opportunities = db.query(Opportunity).count()
    
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_imports = db.query(Opportunity).filter(
        Opportunity.created_at >= last_24h
    ).count()
    
    ai_analyzed = db.query(Opportunity).filter(
        Opportunity.ai_analyzed == True
    ).count()
    
    pending_analysis = db.query(Opportunity).filter(
        Opportunity.ai_analyzed == False
    ).count()
    
    apify_configured = bool(os.getenv("APIFY_API_TOKEN"))
    serpapi_configured = bool(os.getenv("SERPAPI_KEY"))
    census_configured = bool(os.getenv("CENSUS_API_KEY"))
    
    return {
        "total_opportunities": total_opportunities,
        "recent_imports_24h": recent_imports,
        "ai_analyzed": ai_analyzed,
        "pending_analysis": pending_analysis,
        "configuration": {
            "apify": apify_configured,
            "serpapi": serpapi_configured,
            "census": census_configured
        }
    }


@router.post("/data-pipeline/reprocess-google-maps")
async def reprocess_google_maps_opportunities(
    limit: int = Query(10, ge=1, le=50, description="Number of opportunities to reprocess"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Re-analyze Google Maps opportunities with improved AI processing.
    This will regenerate titles and descriptions using the updated AI prompts.
    """
    from app.services.signal_to_opportunity import SignalToOpportunityProcessor
    import json
    
    opportunities = db.query(Opportunity).filter(
        Opportunity.source_platform == 'apify_google_maps'
    ).order_by(desc(Opportunity.created_at)).limit(limit).all()
    
    if not opportunities:
        return {"status": "no_opportunities", "message": "No Google Maps opportunities found"}
    
    processor = SignalToOpportunityProcessor(db)
    
    if not processor.client:
        return {"status": "error", "message": "AI client not configured"}
    
    results = []
    for opp in opportunities:
        try:
            business_idea = {
                'category': opp.category or 'general',
                'primary_keyword': 'services',
                'signal_count': opp.validation_count or 1,
                'sample_titles': [],
                'location': opp.city or 'Unknown'
            }
            
            validation = {
                'confidence_tier': 'VALIDATED' if (opp.ai_opportunity_score or 0) >= 60 else 'WEAK_SIGNAL',
                'validation_score': (opp.ai_opportunity_score or 50) / 100,
                'green_flags': [],
                'red_flags': []
            }
            
            market_estimate = {
                'market_size_category': opp.market_size or 'MEDIUM',
                'potential_customers': 50000,
                'competition_level': opp.ai_competition_level or 'Medium'
            }
            
            old_title = opp.title
            old_description = opp.description[:100] if opp.description else ""
            
            new_title, new_description = processor._ai_polish_opportunity(
                opp.title,
                opp.description or "",
                business_idea,
                validation,
                market_estimate,
                opp.city or 'Unknown'
            )
            
            opp.title = new_title
            opp.description = new_description
            opp.ai_analyzed_at = datetime.now(timezone.utc)
            
            results.append({
                "id": opp.id,
                "old_title": old_title,
                "new_title": new_title,
                "status": "updated"
            })
            
        except Exception as e:
            results.append({
                "id": opp.id,
                "old_title": opp.title,
                "status": "error",
                "error": str(e)
            })
    
    db.commit()
    
    updated_count = sum(1 for r in results if r.get("status") == "updated")
    
    return {
        "status": "completed",
        "total_processed": len(results),
        "updated": updated_count,
        "results": results
    }


@router.post("/data-pipeline/reprocess-general-category")
async def reprocess_general_category_opportunities(
    limit: int = Query(20, ge=1, le=100, description="Number of opportunities to reprocess"),
    dry_run: bool = Query(False, description="If true, only preview changes without saving"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Re-analyze opportunities with category 'General' to assign proper categories.
    This will use AI to determine the correct category and update descriptions.
    Raw source data will be preserved.
    """
    import asyncio
    from app.services.llm_ai_engine import get_anthropic_client
    
    MAX_CONCURRENT_CALLS = 5
    
    client = get_anthropic_client()
    if not client:
        return {"status": "error", "message": "AI client not configured - set ANTHROPIC_API_KEY"}
    
    opportunities = db.query(Opportunity).filter(
        Opportunity.category == 'General'
    ).order_by(desc(Opportunity.created_at)).limit(limit).all()
    
    if not opportunities:
        return {"status": "no_opportunities", "message": "No opportunities with 'General' category found", "count": 0}
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
    
    def extract_text_from_raw_data(raw_data_str: str) -> str:
        """Extract readable text from raw_source_data JSON string."""
        try:
            raw_data = json.loads(raw_data_str)
            if isinstance(raw_data, dict):
                parts = []
                for key in ['title', 'original_title', 'name', 'text', 'content', 'full_text', 'rawContent', 'body', 'selftext', 'original_description']:
                    if key in raw_data and raw_data[key]:
                        parts.append(str(raw_data[key]))
                if parts:
                    return "\n".join(parts)
                return str(raw_data)[:2000]
            return str(raw_data)[:2000]
        except (json.JSONDecodeError, TypeError):
            return raw_data_str[:2000] if raw_data_str else ""
    
    async def reprocess_single(opp: Opportunity):
        async with semaphore:
            try:
                if opp.raw_source_data:
                    raw_text = extract_text_from_raw_data(opp.raw_source_data)
                else:
                    raw_text = opp.description or opp.title or ""
                
                if not raw_text or len(raw_text) < 20:
                    return {
                        "id": opp.id,
                        "title": opp.title,
                        "status": "skipped",
                        "reason": "insufficient_content"
                    }
                
                prompt = f"""Analyze this opportunity content and determine if it's a valid business opportunity. Provide proper categorization and professional rewrite.

CURRENT DATA:
Title: {opp.title}
Content: {raw_text[:2500]}

Respond with a valid JSON object:
{{
    "is_valid_opportunity": true/false,
    "category": "One of: Technology, Healthcare, Finance, Education, Retail, Food & Beverage, Real Estate, Transportation, Entertainment, B2B Services, Consumer Services, Manufacturing, Health & Wellness, Home & Living, Pet Care, Creator Economy, Gaming & Esports, Personal Development, Work & Productivity, Other",
    "subcategory": "More specific subcategory",
    "professional_title": "A clear, professional title (50-100 chars)",
    "professional_description": "Professional business description. 2-3 paragraphs.",
    "one_line_summary": "One compelling sentence summarizing this opportunity"
}}

Important:
- If content is spam, ads, or not a business opportunity, set is_valid_opportunity to false
- Choose the most appropriate category based on the content
- Rewrite informal language to sound professional
- Keep the core meaning but make it business-ready"""

                def sync_call():
                    return client.messages.create(
                        model="claude-haiku-4-5",
                        max_tokens=1500,
                        messages=[{"role": "user", "content": prompt}]
                    )
                
                message = await asyncio.to_thread(sync_call)
                response_text = message.content[0].text
                
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                analysis = json.loads(response_text.strip())
                
                if not analysis.get("is_valid_opportunity", True):
                    return {
                        "id": opp.id,
                        "title": opp.title,
                        "status": "skipped",
                        "reason": "not_valid_opportunity"
                    }
                
                old_category = opp.category
                old_title = opp.title
                old_description = opp.description
                new_category = analysis.get("category", "Other")
                new_title = analysis.get("professional_title", opp.title)
                new_description = analysis.get("professional_description", opp.description)
                
                if not dry_run:
                    preserved_data = {
                        "previous_title": old_title,
                        "previous_description": old_description[:5000] if old_description else None,
                        "previous_category": old_category,
                        "reprocessed_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    if opp.raw_source_data:
                        try:
                            existing_raw = json.loads(opp.raw_source_data)
                            if isinstance(existing_raw, dict):
                                existing_raw["reprocess_history"] = existing_raw.get("reprocess_history", [])
                                existing_raw["reprocess_history"].append(preserved_data)
                                opp.raw_source_data = json.dumps(existing_raw)
                            else:
                                opp.raw_source_data = json.dumps({
                                    "original_raw": existing_raw,
                                    "reprocess_history": [preserved_data]
                                })
                        except json.JSONDecodeError:
                            opp.raw_source_data = json.dumps({
                                "original_raw": opp.raw_source_data,
                                "reprocess_history": [preserved_data]
                            })
                    else:
                        opp.raw_source_data = json.dumps({
                            "original_title": old_title,
                            "original_description": old_description,
                            "reprocess_history": [preserved_data]
                        })
                    
                    opp.category = new_category[:100]
                    opp.title = new_title[:500]
                    opp.description = new_description[:5000]
                    opp.ai_summary = analysis.get("one_line_summary", "")[:500]
                    opp.subcategory = analysis.get("subcategory")
                    opp.ai_analyzed = True
                    opp.ai_analyzed_at = datetime.now(timezone.utc)
                    opp.moderation_status = 'pending_review'
                
                return {
                    "id": opp.id,
                    "old_category": old_category,
                    "new_category": new_category,
                    "old_title": old_title,
                    "new_title": new_title,
                    "status": "updated" if not dry_run else "preview"
                }
                
            except json.JSONDecodeError as e:
                return {
                    "id": opp.id,
                    "title": opp.title,
                    "status": "error",
                    "error": f"JSON parse error: {str(e)}"
                }
            except Exception as e:
                return {
                    "id": opp.id,
                    "title": opp.title,
                    "status": "error",
                    "error": str(e)
                }
    
    results = await asyncio.gather(*[reprocess_single(opp) for opp in opportunities])
    
    if not dry_run:
        db.commit()
    
    updated_count = sum(1 for r in results if r.get("status") in ["updated", "preview"])
    error_count = sum(1 for r in results if r.get("status") == "error")
    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    
    return {
        "status": "completed" if not dry_run else "preview",
        "dry_run": dry_run,
        "total_found": len(opportunities),
        "total_processed": len(results),
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": error_count,
        "results": results
    }


@router.get("/report-usage-stats")
async def get_report_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
):
    """Get comprehensive report usage statistics for admin dashboard."""
    from app.models.generated_report import GeneratedReport, ReportStatus
    from app.models.subscription import Subscription
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    total_reports = db.query(func.count(GeneratedReport.id)).filter(
        GeneratedReport.created_at >= cutoff_date,
        GeneratedReport.status == ReportStatus.COMPLETED
    ).scalar() or 0
    
    reports_by_type = db.query(
        GeneratedReport.report_type,
        func.count(GeneratedReport.id).label("count")
    ).filter(
        GeneratedReport.created_at >= cutoff_date,
        GeneratedReport.status == ReportStatus.COMPLETED
    ).group_by(GeneratedReport.report_type).all()
    
    reports_by_user = db.query(
        User.id,
        User.email,
        User.name,
        Subscription.tier,
        func.count(GeneratedReport.id).label("report_count")
    ).join(
        GeneratedReport, GeneratedReport.user_id == User.id
    ).outerjoin(
        Subscription, Subscription.user_id == User.id
    ).filter(
        GeneratedReport.created_at >= cutoff_date,
        GeneratedReport.status == ReportStatus.COMPLETED
    ).group_by(
        User.id, User.email, User.name, Subscription.tier
    ).order_by(desc("report_count")).limit(50).all()
    
    reports_by_day = db.query(
        func.date(GeneratedReport.created_at).label("date"),
        func.count(GeneratedReport.id).label("count")
    ).filter(
        GeneratedReport.created_at >= cutoff_date,
        GeneratedReport.status == ReportStatus.COMPLETED
    ).group_by(func.date(GeneratedReport.created_at)).order_by("date").all()
    
    return {
        "period_days": days,
        "total_reports": total_reports,
        "by_type": [{"type": str(r[0].value) if r[0] else "unknown", "count": r[1]} for r in reports_by_type],
        "by_user": [
            {
                "user_id": r[0],
                "email": r[1],
                "name": r[2],
                "tier": str(r[3].value) if r[3] else "free",
                "report_count": r[4]
            }
            for r in reports_by_user
        ],
        "by_day": [{"date": str(r[0]), "count": r[1]} for r in reports_by_day],
    }


# =============================================================================
# AI PRICING & USAGE ADMIN
# =============================================================================

@router.get("/ai-pricing/config")
def get_ai_pricing_config(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get current AI pricing configuration."""
    from app.services.ai_metering_service import MODEL_COSTS, TIER_TOKEN_LIMITS, DEFAULT_MARKUP
    
    return {
        "model_costs": MODEL_COSTS,
        "tier_token_limits": TIER_TOKEN_LIMITS,
        "default_markup": DEFAULT_MARKUP,
        "markup_explanation": "Markup applied to base cost. 1.5 = 50% margin."
    }


@router.patch("/ai-pricing/model-costs")
def update_model_costs(
    updates: Dict[str, Dict[str, float]],
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Update model pricing.
    
    Body: {"claude-opus-4-5": {"input": 15.0, "output": 75.0}, ...}
    """
    from app.services import ai_metering_service
    
    for model, costs in updates.items():
        if "input" in costs and "output" in costs:
            ai_metering_service.MODEL_COSTS[model] = costs
    
    return {
        "status": "updated",
        "updated_models": list(updates.keys()),
        "current_config": ai_metering_service.MODEL_COSTS
    }


@router.patch("/ai-pricing/tier-limits")
def update_tier_limits(
    updates: Dict[str, int],
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Update tier token limits.
    
    Body: {"starter": 100000, "growth": 500000, ...}
    """
    from app.services import ai_metering_service
    
    for tier, limit in updates.items():
        ai_metering_service.TIER_TOKEN_LIMITS[tier] = limit
    
    return {
        "status": "updated",
        "updated_tiers": list(updates.keys()),
        "current_config": ai_metering_service.TIER_TOKEN_LIMITS
    }


@router.patch("/ai-pricing/markup")
def update_markup(
    markup: float,
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Update default markup multiplier.
    
    Example: 1.5 = 50% margin, 2.0 = 100% margin
    """
    from app.services import ai_metering_service
    
    old_markup = ai_metering_service.DEFAULT_MARKUP
    ai_metering_service.DEFAULT_MARKUP = markup
    
    return {
        "status": "updated",
        "old_markup": old_markup,
        "new_markup": markup
    }


@router.get("/ai-pricing/usage-stats")
def get_ai_usage_stats(
    days: int = Query(30, ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get AI usage statistics across all users."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    try:
        from app.models.ai_usage import UserAIUsage
        
        # Total usage
        total_stats = db.query(
            func.sum(UserAIUsage.input_tokens).label("total_input"),
            func.sum(UserAIUsage.output_tokens).label("total_output"),
            func.sum(UserAIUsage.cost_usd).label("total_cost"),
            func.sum(UserAIUsage.billed_amount_usd).label("total_billed"),
            func.count(UserAIUsage.id).label("total_requests")
        ).filter(UserAIUsage.created_at >= cutoff).first()
        
        # By model
        by_model = db.query(
            UserAIUsage.model_name,
            func.sum(UserAIUsage.input_tokens).label("input_tokens"),
            func.sum(UserAIUsage.output_tokens).label("output_tokens"),
            func.sum(UserAIUsage.cost_usd).label("cost"),
            func.count(UserAIUsage.id).label("requests")
        ).filter(UserAIUsage.created_at >= cutoff).group_by(
            UserAIUsage.model_name
        ).all()
        
        # By event type
        by_type = db.query(
            UserAIUsage.event_type,
            func.sum(UserAIUsage.input_tokens + UserAIUsage.output_tokens).label("tokens"),
            func.sum(UserAIUsage.cost_usd).label("cost"),
            func.count(UserAIUsage.id).label("requests")
        ).filter(UserAIUsage.created_at >= cutoff).group_by(
            UserAIUsage.event_type
        ).all()
        
        # Top users
        top_users = db.query(
            UserAIUsage.user_id,
            func.sum(UserAIUsage.input_tokens + UserAIUsage.output_tokens).label("tokens"),
            func.sum(UserAIUsage.cost_usd).label("cost"),
            func.count(UserAIUsage.id).label("requests")
        ).filter(UserAIUsage.created_at >= cutoff).group_by(
            UserAIUsage.user_id
        ).order_by(desc("cost")).limit(20).all()
        
        return {
            "period_days": days,
            "totals": {
                "input_tokens": int(total_stats.total_input or 0),
                "output_tokens": int(total_stats.total_output or 0),
                "cost_usd": float(total_stats.total_cost or 0),
                "billed_usd": float(total_stats.total_billed or 0),
                "margin_usd": float((total_stats.total_billed or 0) - (total_stats.total_cost or 0)),
                "total_requests": int(total_stats.total_requests or 0)
            },
            "by_model": [
                {
                    "model": r.model_name,
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cost_usd": float(r.cost or 0),
                    "requests": int(r.requests or 0)
                }
                for r in by_model
            ],
            "by_event_type": [
                {
                    "type": r.event_type,
                    "tokens": int(r.tokens or 0),
                    "cost_usd": float(r.cost or 0),
                    "requests": int(r.requests or 0)
                }
                for r in by_type
            ],
            "top_users": [
                {
                    "user_id": r.user_id,
                    "tokens": int(r.tokens or 0),
                    "cost_usd": float(r.cost or 0),
                    "requests": int(r.requests or 0)
                }
                for r in top_users
            ]
        }
    except Exception as e:
        return {
            "error": str(e),
            "note": "AI usage table may not exist. Run migrations."
        }


@router.get("/ai-pricing/user/{user_id}/usage")
def get_user_ai_usage(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get AI usage for a specific user."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    try:
        from app.models.ai_usage import UserAIUsage
        
        usage = db.query(
            func.sum(UserAIUsage.input_tokens).label("input_tokens"),
            func.sum(UserAIUsage.output_tokens).label("output_tokens"),
            func.sum(UserAIUsage.cost_usd).label("cost_usd"),
            func.sum(UserAIUsage.billed_amount_usd).label("billed_usd"),
            func.count(UserAIUsage.id).label("requests")
        ).filter(
            UserAIUsage.user_id == user_id,
            UserAIUsage.created_at >= cutoff
        ).first()
        
        recent = db.query(UserAIUsage).filter(
            UserAIUsage.user_id == user_id,
            UserAIUsage.created_at >= cutoff
        ).order_by(desc(UserAIUsage.created_at)).limit(50).all()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "totals": {
                "input_tokens": int(usage.input_tokens or 0),
                "output_tokens": int(usage.output_tokens or 0),
                "cost_usd": float(usage.cost_usd or 0),
                "billed_usd": float(usage.billed_usd or 0),
                "requests": int(usage.requests or 0)
            },
            "recent_usage": [
                {
                    "id": u.id,
                    "event_type": u.event_type,
                    "model": u.model_name,
                    "tokens": u.input_tokens + u.output_tokens,
                    "cost_usd": float(u.cost_usd),
                    "created_at": u.created_at.isoformat()
                }
                for u in recent
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/ai-pricing/user/{user_id}/set-limit")
def set_user_token_limit(
    user_id: int,
    monthly_limit: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Set a custom token limit for a specific user (overrides tier limit)."""
    try:
        from app.models.ai_usage import UserAIQuota
        
        quota = db.query(UserAIQuota).filter(UserAIQuota.user_id == user_id).first()
        
        if quota:
            quota.monthly_token_limit = monthly_limit
            quota.updated_at = datetime.utcnow()
        else:
            quota = UserAIQuota(
                user_id=user_id,
                monthly_token_limit=monthly_limit
            )
            db.add(quota)
        
        db.commit()
        
        return {
            "status": "updated",
            "user_id": user_id,
            "monthly_token_limit": monthly_limit
        }
    except Exception as e:
        return {"error": str(e)}



# =============================================================================
# STRIPE TOKEN BILLING ADMIN
# =============================================================================

@router.get("/stripe-token-billing/meters")
def list_stripe_meters(
    current_admin: User = Depends(get_current_admin_user),
):
    """List all Stripe billing meters."""
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()
    meters = billing.list_meters()

    return {
        "enabled": billing.enabled,
        "meters": meters,
        "count": len(meters)
    }


@router.post("/stripe-token-billing/setup-meters")
def setup_stripe_meters(
    current_admin: User = Depends(get_current_admin_user),
):
    """Create default billing meters in Stripe (run once)."""
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()

    if not billing.enabled:
        return {"error": "Stripe token billing not enabled"}

    result = billing.setup_default_meters()
    return result


@router.get("/stripe-token-billing/customer/{customer_id}/usage")
def get_customer_token_usage(
    customer_id: str,
    current_admin: User = Depends(get_current_admin_user),
):
    """Get token usage for a Stripe customer."""
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()
    return billing.get_customer_usage(customer_id)


@router.get("/stripe-token-billing/user/{user_id}/usage")
def get_user_token_usage(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get token usage for a user (by internal user_id)."""
    from app.services.stripe_token_billing import get_token_billing
    from app.models.subscription import Subscription

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription or not subscription.stripe_customer_id:
        return {"error": "User has no Stripe customer ID"}

    billing = get_token_billing()
    return billing.get_customer_usage(subscription.stripe_customer_id)


@router.post("/stripe-token-billing/create-meter")
def create_stripe_meter(
    display_name: str,
    event_name: str,
    current_admin: User = Depends(get_current_admin_user),
):
    """Create a custom billing meter."""
    from app.services.stripe_token_billing import get_token_billing

    billing = get_token_billing()

    if not billing.enabled:
        return {"error": "Stripe token billing not enabled"}

    result = billing.create_meter(display_name, event_name)

    if result:
        return {"status": "created", **result}
    else:
        return {"error": "Failed to create meter"}


@router.get("/tier-config")
def get_tier_config(
    admin_user: User = Depends(get_current_admin_user),
):
    """Return read-only tier configuration for all 7 v2.1 tiers."""
    from app.models.tier_config import TierConfig
    return {"tiers": TierConfig.as_list()}


@router.get("/opportunity-access/summary")
def get_opportunity_access_summary(
    billing_month: Optional[date] = Query(None, description="Filter by billing month (YYYY-MM-DD). Defaults to current month."),
    search_email: Optional[str] = Query(None, description="Substring match on user email"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Per-user monthly opportunity usage aggregate, ordered by overage_total descending."""
    from app.models.opportunity_access import OpportunityAccess
    from app.models.subscription import Subscription
    from app.models.tier_config import TierConfig
    from datetime import date as date_type
    from sqlalchemy import case

    if billing_month is None:
        today = date_type.today()
        billing_month = date_type(today.year, today.month, 1)

    included_used_col = func.count(
        case((OpportunityAccess.is_included == True, OpportunityAccess.id))
    ).label("included_used")
    overage_count_col = func.count(
        case((OpportunityAccess.is_included == False, OpportunityAccess.id))
    ).label("overage_count")
    overage_total_col = func.coalesce(func.sum(OpportunityAccess.overage_charged), 0).label("overage_total")
    total_col = func.count(OpportunityAccess.id).label("total_accessed")

    q = (
        db.query(
            User.id.label("user_id"),
            User.email.label("email"),
            included_used_col,
            overage_count_col,
            overage_total_col,
            total_col,
        )
        .join(OpportunityAccess, OpportunityAccess.user_id == User.id)
        .filter(OpportunityAccess.billing_month == billing_month)
        .group_by(User.id, User.email)
    )

    if search_email:
        q = q.filter(User.email.ilike(f"%{search_email}%"))

    total = db.query(func.count()).select_from(q.subquery()).scalar() or 0

    rows = q.order_by(desc(overage_total_col)).offset(skip).limit(limit).all()

    # Build user_id -> subscription tier map for included_cap lookup
    user_ids = [r.user_id for r in rows]
    subs = {}
    if user_ids:
        sub_rows = db.query(Subscription.user_id, Subscription.tier).filter(
            Subscription.user_id.in_(user_ids)
        ).all()
        subs = {s.user_id: s.tier for s in sub_rows}

    items = []
    for r in rows:
        tier_val = subs.get(r.user_id)
        tier_str = tier_val.value if tier_val and hasattr(tier_val, 'value') else (tier_val or "explorer")
        included_cap = TierConfig.get_monthly_cap(tier_str)
        items.append({
            "user_id": r.user_id,
            "email": r.email,
            "billing_month": billing_month.isoformat(),
            "included_cap": included_cap,
            "included_used": r.included_used,
            "overage_count": r.overage_count,
            "overage_total": float(r.overage_total),
            "total_accessed": r.total_accessed,
        })

    return {
        "billing_month": billing_month.isoformat(),
        "total": total,
        "items": items,
    }


@router.get("/opportunity-access")
def list_opportunity_access(
    user_id: Optional[int] = Query(None),
    billing_month: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List opportunity_access records with user email and opportunity title."""
    from app.models.opportunity_access import OpportunityAccess

    q = (
        db.query(
            OpportunityAccess,
            User.email.label("user_email"),
            Opportunity.title.label("opportunity_title"),
        )
        .join(User, OpportunityAccess.user_id == User.id)
        .join(Opportunity, OpportunityAccess.opportunity_id == Opportunity.id)
    )

    if user_id is not None:
        q = q.filter(OpportunityAccess.user_id == user_id)

    if billing_month is not None:
        q = q.filter(OpportunityAccess.billing_month == billing_month)

    total = q.count()
    rows = q.order_by(desc(OpportunityAccess.first_accessed_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(rec.id),
                "user_id": rec.user_id,
                "user_email": user_email,
                "opportunity_id": rec.opportunity_id,
                "opportunity_title": opportunity_title,
                "access_type": rec.access_type,
                "billing_month": rec.billing_month.isoformat() if rec.billing_month else None,
                "is_included": rec.is_included,
                "overage_charged": float(rec.overage_charged),
                "stripe_invoice_item_id": rec.stripe_invoice_item_id,
                "access_count": rec.access_count,
                "first_accessed_at": rec.first_accessed_at,
                "last_accessed_at": rec.last_accessed_at,
            }
            for rec, user_email, opportunity_title in rows
        ],
    }


@router.patch("/opportunity-access/{record_id}")
def patch_opportunity_access(
    record_id: str,
    is_included: Optional[bool] = None,
    reset_overage: Optional[bool] = Query(None, description="Set overage_charged to 0"),
    request: Request = None,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Manually correct an opportunity_access record.
    - is_included=true: mark record as within monthly allowance
    - reset_overage=true: zero out the overage_charged amount
    """
    import uuid as _uuid
    from app.models.opportunity_access import OpportunityAccess

    try:
        rec_uuid = _uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record_id format (must be UUID)")

    record = db.query(OpportunityAccess).filter(OpportunityAccess.id == rec_uuid).first()
    if not record:
        raise HTTPException(status_code=404, detail="Opportunity access record not found")

    changed = {}
    if is_included is not None:
        record.is_included = is_included
        changed["is_included"] = is_included
    if reset_overage:
        record.overage_charged = 0
        changed["overage_charged"] = 0

    if not changed:
        raise HTTPException(status_code=400, detail="No changes requested. Pass is_included or reset_overage=true")

    db.commit()

    log_event(
        db,
        action="admin.opportunity_access.patch",
        actor=admin_user,
        actor_type="admin",
        request=request,
        resource_type="opportunity_access",
        resource_id=str(record_id),
        metadata={"changes": changed, "user_id": record.user_id, "opportunity_id": record.opportunity_id},
    )

    return {
        "id": str(record.id),
        "user_id": record.user_id,
        "opportunity_id": record.opportunity_id,
        "is_included": record.is_included,
        "overage_charged": float(record.overage_charged),
        "billing_month": record.billing_month.isoformat() if record.billing_month else None,
    }


@router.get("/stripe-token-billing/config")
def get_token_billing_config(
    current_admin: User = Depends(get_current_admin_user),
):
    """Get token billing configuration."""
    from app.services.stripe_token_billing import (
        get_token_billing, METER_EVENTS, MODEL_TO_METER
    )

    billing = get_token_billing()

    return {
        "enabled": billing.enabled,
        "meter_events": METER_EVENTS,
        "model_to_meter_mapping": MODEL_TO_METER
    }
