"""
Expert Collaboration Router

API endpoints for the Expert Collaboration System:
- Expert profile management
- Expert discovery and matching
- Engagement workflows
- Messaging
- Reviews
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.db.database import get_db
from app.models.user import User
from app.models.expert_collaboration import (
    ExpertCategory, ExpertSpecialization, ExpertStageExpertise,
    EngagementType, EngagementStatus, ExpertPermissionLevel,
    ExpertProfile, ExpertEngagement, EngagementMilestone,
    ExpertMessage, ExpertReview, ExpertScheduledSession
)
from app.core.dependencies import get_current_user

router = APIRouter()


class ExpertProfileCreate(BaseModel):
    title: str
    location: Optional[str] = None
    timezone: Optional[str] = None
    primary_category: Optional[ExpertCategory] = None
    specializations: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    stage_expertise: Optional[List[str]] = None
    years_experience: Optional[int] = None
    companies_json: Optional[str] = None
    exits: Optional[str] = None
    funded_companies: Optional[int] = 0
    portfolio_highlights: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    availability_description: Optional[str] = None
    availability_hours_per_week: Optional[int] = None
    engagement_types: Optional[List[str]] = None
    hourly_rate_cents: Optional[int] = None
    project_rate_min_cents: Optional[int] = None
    project_rate_max_cents: Optional[int] = None
    retainer_rate_cents: Optional[int] = None
    response_time: Optional[str] = None


class ExpertProfileUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    primary_category: Optional[ExpertCategory] = None
    specializations: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    stage_expertise: Optional[List[str]] = None
    years_experience: Optional[int] = None
    companies_json: Optional[str] = None
    exits: Optional[str] = None
    funded_companies: Optional[int] = None
    portfolio_highlights: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    availability_description: Optional[str] = None
    availability_hours_per_week: Optional[int] = None
    engagement_types: Optional[List[str]] = None
    hourly_rate_cents: Optional[int] = None
    project_rate_min_cents: Optional[int] = None
    project_rate_max_cents: Optional[int] = None
    retainer_rate_cents: Optional[int] = None
    response_time: Optional[str] = None
    is_accepting_clients: Optional[bool] = None
    max_active_clients: Optional[int] = None


class ExpertProfileResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    location: Optional[str]
    timezone: Optional[str]
    primary_category: Optional[str]
    specializations: Optional[List[str]]
    industries: Optional[List[str]]
    stage_expertise: Optional[List[str]]
    years_experience: Optional[int]
    portfolio_highlights: Optional[str]
    education: Optional[str]
    certifications: Optional[str]
    availability_description: Optional[str]
    availability_hours_per_week: Optional[int]
    engagement_types: Optional[List[str]]
    hourly_rate_cents: Optional[int]
    project_rate_min_cents: Optional[int]
    project_rate_max_cents: Optional[int]
    retainer_rate_cents: Optional[int]
    response_time: Optional[str]
    is_verified: bool
    is_accepting_clients: bool
    projects_completed: int
    avg_rating: Optional[float]
    total_reviews: int
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EngagementRequest(BaseModel):
    expert_profile_id: int
    opportunity_id: Optional[int] = None
    workspace_id: Optional[int] = None
    engagement_type: EngagementType
    title: str
    description: Optional[str] = None
    request_message: str
    shared_materials: Optional[List[str]] = None
    preferred_start_date: Optional[datetime] = None
    for_consultation_duration_minutes: Optional[int] = None
    for_project_duration_weeks: Optional[int] = None
    for_retainer_months: Optional[int] = None
    for_hourly_estimated_hours: Optional[float] = None


class EngagementResponse(BaseModel):
    id: int
    user_id: int
    expert_profile_id: int
    engagement_type: str
    status: str
    permission_level: str
    title: Optional[str]
    description: Optional[str]
    request_message: Optional[str]
    proposal_message: Optional[str]
    proposed_amount_cents: Optional[int]
    final_amount_cents: Optional[int]
    created_at: datetime
    expert_name: Optional[str] = None
    expert_avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    attachments: Optional[List[str]] = None


class MessageResponse(BaseModel):
    id: int
    engagement_id: int
    sender_id: int
    content: str
    attachments: Optional[List[str]]
    is_read: bool
    is_ai_suggestion: bool
    created_at: datetime
    sender_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    overall_rating: int = Field(..., ge=1, le=5)
    expertise_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    responsiveness_rating: Optional[int] = Field(None, ge=1, le=5)
    value_for_money_rating: Optional[int] = Field(None, ge=1, le=5)
    review_text: Optional[str] = None
    would_recommend: Optional[bool] = None
    would_work_again: Optional[bool] = None


def serialize_expert_profile(profile: ExpertProfile, user: User = None) -> dict:
    """Convert ExpertProfile to response dict"""
    user_name = None
    user_avatar = None
    
    if user:
        user_name = user.name
        user_avatar = user.avatar_url
    elif profile.user:
        user_name = profile.user.name
        user_avatar = profile.user.avatar_url
    elif profile.external_name:
        user_name = profile.external_name
        user_avatar = profile.avatar_url
    
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "title": profile.title,
        "location": profile.location,
        "timezone": profile.timezone,
        "primary_category": profile.primary_category.value.lower() if profile.primary_category else None,
        "category": profile.category.value.lower() if profile.category else None,
        "specializations": json.loads(profile.specializations) if profile.specializations else [],
        "industries": json.loads(profile.industries) if profile.industries else [],
        "stage_expertise": json.loads(profile.stage_expertise) if profile.stage_expertise else [],
        "years_experience": profile.years_experience,
        "portfolio_highlights": profile.portfolio_highlights,
        "education": profile.education,
        "certifications": profile.certifications,
        "availability_description": profile.availability_description,
        "availability_hours_per_week": profile.availability_hours_per_week,
        "engagement_types": json.loads(profile.engagement_types) if profile.engagement_types else [],
        "hourly_rate_cents": profile.hourly_rate_cents,
        "project_rate_min_cents": profile.project_rate_min_cents,
        "project_rate_max_cents": profile.project_rate_max_cents,
        "retainer_rate_cents": profile.retainer_rate_cents,
        "response_time": profile.response_time,
        "is_verified": profile.is_verified,
        "is_accepting_clients": profile.is_accepting_clients,
        "projects_completed": profile.projects_completed,
        "avg_rating": profile.avg_rating,
        "total_reviews": profile.total_reviews,
        "user_name": user_name,
        "user_avatar": user_avatar,
        "created_at": profile.created_at,
        "external_id": profile.external_id,
        "external_source": profile.external_source,
        "external_url": profile.external_url,
        "external_name": profile.external_name,
        "skills": json.loads(profile.skills) if profile.skills else [],
    }


@router.get("/experts", response_model=List[dict])
async def list_experts(
    category: Optional[ExpertCategory] = None,
    specialization: Optional[str] = None,
    industry: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_hourly_rate: Optional[int] = None,
    is_accepting: Optional[bool] = True,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all verified expert profiles and external experts with optional filtering"""
    query = db.query(ExpertProfile).filter(
        or_(
            ExpertProfile.is_verified == True,
            ExpertProfile.external_source.isnot(None)
        ),
        or_(
            ExpertProfile.external_source != "sample",
            ExpertProfile.external_source.is_(None)
        )
    )
    
    if is_accepting:
        query = query.filter(
            or_(
                ExpertProfile.is_accepting_clients == True,
                ExpertProfile.external_source.isnot(None)
            )
        )
    
    if category:
        query = query.filter(
            or_(
                ExpertProfile.primary_category == category,
                ExpertProfile.category == category
            )
        )
    
    if specialization:
        query = query.filter(ExpertProfile.specializations.contains(specialization))
    
    if industry:
        query = query.filter(ExpertProfile.industries.contains(industry))
    
    if min_rating:
        query = query.filter(ExpertProfile.avg_rating >= min_rating)
    
    if max_hourly_rate:
        query = query.filter(ExpertProfile.hourly_rate_cents <= max_hourly_rate)
    
    if search:
        search_term = f"%{search}%"
        query = query.outerjoin(User, ExpertProfile.user_id == User.id).filter(
            or_(
                User.name.ilike(search_term),
                ExpertProfile.title.ilike(search_term),
                ExpertProfile.specializations.ilike(search_term),
                ExpertProfile.industries.ilike(search_term),
                ExpertProfile.external_name.ilike(search_term),
                ExpertProfile.skills.ilike(search_term)
            )
        )
    
    query = query.order_by(ExpertProfile.avg_rating.desc().nullslast(), ExpertProfile.projects_completed.desc())
    
    profiles = query.offset(skip).limit(limit).all()
    
    return [serialize_expert_profile(p) for p in profiles]


@router.get("/experts/{expert_id}", response_model=dict)
async def get_expert_profile(
    expert_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific expert profile"""
    profile = db.query(ExpertProfile).filter(ExpertProfile.id == expert_id).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    return serialize_expert_profile(profile)


@router.post("/experts/apply", response_model=dict)
async def apply_as_expert(
    data: ExpertProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply to become an expert on the platform"""
    existing = db.query(ExpertProfile).filter(ExpertProfile.user_id == current_user.id).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have an expert profile")
    
    profile = ExpertProfile(
        user_id=current_user.id,
        title=data.title,
        location=data.location,
        timezone=data.timezone,
        primary_category=data.primary_category,
        specializations=json.dumps(data.specializations) if data.specializations else None,
        industries=json.dumps(data.industries) if data.industries else None,
        stage_expertise=json.dumps(data.stage_expertise) if data.stage_expertise else None,
        years_experience=data.years_experience,
        companies_json=data.companies_json,
        exits=data.exits,
        funded_companies=data.funded_companies or 0,
        portfolio_highlights=data.portfolio_highlights,
        education=data.education,
        certifications=data.certifications,
        availability_description=data.availability_description,
        availability_hours_per_week=data.availability_hours_per_week,
        engagement_types=json.dumps(data.engagement_types) if data.engagement_types else None,
        hourly_rate_cents=data.hourly_rate_cents,
        project_rate_min_cents=data.project_rate_min_cents,
        project_rate_max_cents=data.project_rate_max_cents,
        retainer_rate_cents=data.retainer_rate_cents,
        response_time=data.response_time,
        is_verified=False,
        member_since=datetime.utcnow()
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return serialize_expert_profile(profile, current_user)


@router.put("/experts/me", response_model=dict)
async def update_my_expert_profile(
    data: ExpertProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's expert profile"""
    profile = db.query(ExpertProfile).filter(ExpertProfile.user_id == current_user.id).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    update_data = data.dict(exclude_unset=True)
    
    if "specializations" in update_data and update_data["specializations"] is not None:
        update_data["specializations"] = json.dumps(update_data["specializations"])
    if "industries" in update_data and update_data["industries"] is not None:
        update_data["industries"] = json.dumps(update_data["industries"])
    if "stage_expertise" in update_data and update_data["stage_expertise"] is not None:
        update_data["stage_expertise"] = json.dumps(update_data["stage_expertise"])
    if "engagement_types" in update_data and update_data["engagement_types"] is not None:
        update_data["engagement_types"] = json.dumps(update_data["engagement_types"])
    
    for key, value in update_data.items():
        setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    return serialize_expert_profile(profile, current_user)


@router.get("/experts/me", response_model=dict)
async def get_my_expert_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's expert profile"""
    profile = db.query(ExpertProfile).filter(ExpertProfile.user_id == current_user.id).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    return serialize_expert_profile(profile, current_user)


@router.post("/engagements", response_model=dict)
async def request_engagement(
    data: EngagementRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request an engagement with an expert"""
    expert_profile = db.query(ExpertProfile).filter(ExpertProfile.id == data.expert_profile_id).first()
    
    if not expert_profile:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    if not expert_profile.is_accepting_clients:
        raise HTTPException(status_code=400, detail="Expert is not accepting new clients")
    
    if expert_profile.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot request engagement with yourself")
    
    permission_level = ExpertPermissionLevel.VIEWER
    if data.engagement_type == EngagementType.PROJECT:
        permission_level = ExpertPermissionLevel.CONTRIBUTOR
    elif data.engagement_type == EngagementType.RETAINER:
        permission_level = ExpertPermissionLevel.ADVISOR
    elif data.engagement_type == EngagementType.EQUITY_PARTNERSHIP:
        permission_level = ExpertPermissionLevel.PARTNER
    
    engagement = ExpertEngagement(
        user_id=current_user.id,
        expert_profile_id=data.expert_profile_id,
        opportunity_id=data.opportunity_id,
        workspace_id=data.workspace_id,
        engagement_type=data.engagement_type,
        status=EngagementStatus.REQUEST_SENT,
        permission_level=permission_level,
        title=data.title,
        description=data.description,
        request_message=data.request_message,
        shared_materials=json.dumps(data.shared_materials) if data.shared_materials else None,
        preferred_start_date=data.preferred_start_date,
        for_consultation_duration_minutes=data.for_consultation_duration_minutes,
        for_project_duration_weeks=data.for_project_duration_weeks,
        for_retainer_months=data.for_retainer_months,
        for_hourly_estimated_hours=data.for_hourly_estimated_hours,
        request_sent_at=datetime.utcnow()
    )
    
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    
    return {
        "id": engagement.id,
        "status": engagement.status.value,
        "message": "Engagement request sent successfully"
    }


@router.get("/engagements", response_model=List[dict])
async def list_my_engagements(
    role: Optional[str] = Query(None, description="'client' or 'expert'"),
    status: Optional[EngagementStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List engagements for the current user"""
    if role == "expert":
        expert_profile = db.query(ExpertProfile).filter(ExpertProfile.user_id == current_user.id).first()
        if not expert_profile:
            return []
        query = db.query(ExpertEngagement).filter(ExpertEngagement.expert_profile_id == expert_profile.id)
    else:
        query = db.query(ExpertEngagement).filter(ExpertEngagement.user_id == current_user.id)
    
    if status:
        query = query.filter(ExpertEngagement.status == status)
    
    engagements = query.order_by(ExpertEngagement.created_at.desc()).all()
    
    results = []
    for eng in engagements:
        expert_profile = eng.expert_profile
        expert_user = expert_profile.user if expert_profile else None
        client_user = eng.user
        results.append({
            "id": eng.id,
            "user_id": eng.user_id,
            "expert_profile_id": eng.expert_profile_id,
            "engagement_type": eng.engagement_type.value,
            "status": eng.status.value,
            "permission_level": eng.permission_level.value,
            "title": eng.title,
            "description": eng.description,
            "request_message": eng.request_message,
            "proposal_message": eng.proposal_message,
            "proposed_amount_cents": eng.proposed_amount_cents,
            "final_amount_cents": eng.final_amount_cents,
            "platform_fee_cents": eng.platform_fee_cents,
            "expert_payout_cents": eng.expert_payout_cents,
            "created_at": eng.created_at,
            "accepted_at": eng.accepted_at,
            "completed_at": eng.completed_at,
            "is_reviewed": eng.is_reviewed,
            "expert_name": expert_user.name if expert_user else None,
            "expert_title": expert_profile.title if expert_profile else None,
            "expert_avatar": expert_user.avatar_url if expert_user else None,
            "client_name": client_user.name if client_user else None,
            "client_email": client_user.email if client_user else None,
        })
    
    return results


@router.get("/engagements/{engagement_id}", response_model=dict)
async def get_engagement(
    engagement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific engagement"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    expert_profile = engagement.expert_profile
    is_expert = expert_profile and expert_profile.user_id == current_user.id
    is_client = engagement.user_id == current_user.id
    
    if not is_expert and not is_client and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this engagement")
    
    expert_user = expert_profile.user if expert_profile else None
    
    return {
        "id": engagement.id,
        "user_id": engagement.user_id,
        "expert_profile_id": engagement.expert_profile_id,
        "engagement_type": engagement.engagement_type.value,
        "status": engagement.status.value,
        "permission_level": engagement.permission_level.value,
        "title": engagement.title,
        "description": engagement.description,
        "scope_of_work": engagement.scope_of_work,
        "request_message": engagement.request_message,
        "shared_materials": json.loads(engagement.shared_materials) if engagement.shared_materials else [],
        "proposal_message": engagement.proposal_message,
        "proposed_scope": engagement.proposed_scope,
        "proposed_amount_cents": engagement.proposed_amount_cents,
        "proposed_duration_days": engagement.proposed_duration_days,
        "final_amount_cents": engagement.final_amount_cents,
        "platform_fee_cents": engagement.platform_fee_cents,
        "preferred_start_date": engagement.preferred_start_date,
        "actual_start_date": engagement.actual_start_date,
        "expected_end_date": engagement.expected_end_date,
        "created_at": engagement.created_at,
        "is_reviewed": engagement.is_reviewed,
        "is_expert": is_expert,
        "is_client": is_client,
        "expert_name": expert_user.name if expert_user else None,
        "expert_title": expert_profile.title if expert_profile else None,
        "expert_avatar": expert_user.avatar_url if expert_user else None,
    }


@router.post("/engagements/{engagement_id}/proposal")
async def send_proposal(
    engagement_id: int,
    proposal_message: str,
    proposed_amount_cents: int,
    proposed_duration_days: Optional[int] = None,
    proposed_scope: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Expert sends a proposal for an engagement request"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    expert_profile = engagement.expert_profile
    if not expert_profile or expert_profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the expert can send proposals")
    
    if engagement.status != EngagementStatus.REQUEST_SENT:
        raise HTTPException(status_code=400, detail="Proposal can only be sent for pending requests")
    
    engagement.proposal_message = proposal_message
    engagement.proposed_amount_cents = proposed_amount_cents
    engagement.proposed_duration_days = proposed_duration_days
    engagement.proposed_scope = proposed_scope
    engagement.status = EngagementStatus.PROPOSAL_SENT
    engagement.proposal_sent_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Proposal sent successfully"}


@router.post("/engagements/{engagement_id}/accept")
async def accept_proposal(
    engagement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Client accepts an expert's proposal"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    if engagement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can accept proposals")
    
    if engagement.status != EngagementStatus.PROPOSAL_SENT:
        raise HTTPException(status_code=400, detail="No proposal to accept")
    
    platform_fee = int(engagement.proposed_amount_cents * 0.15)
    expert_payout = engagement.proposed_amount_cents - platform_fee
    
    engagement.status = EngagementStatus.ACCEPTED
    engagement.final_amount_cents = engagement.proposed_amount_cents
    engagement.platform_fee_cents = platform_fee
    engagement.expert_payout_cents = expert_payout
    engagement.accepted_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Proposal accepted", "status": "accepted"}


@router.post("/engagements/{engagement_id}/decline")
async def decline_engagement(
    engagement_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Decline an engagement request or proposal"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    expert_profile = engagement.expert_profile
    is_expert = expert_profile and expert_profile.user_id == current_user.id
    is_client = engagement.user_id == current_user.id
    
    if not is_expert and not is_client:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    engagement.status = EngagementStatus.DECLINED
    engagement.cancellation_reason = reason
    engagement.cancelled_by = current_user.id
    engagement.cancelled_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Engagement declined"}


@router.get("/engagements/{engagement_id}/messages", response_model=List[dict])
async def get_engagement_messages(
    engagement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for an engagement"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    expert_profile = engagement.expert_profile
    is_expert = expert_profile and expert_profile.user_id == current_user.id
    is_client = engagement.user_id == current_user.id
    
    if not is_expert and not is_client and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    messages = db.query(ExpertMessage).filter(
        ExpertMessage.engagement_id == engagement_id
    ).order_by(ExpertMessage.created_at.asc()).all()
    
    db.query(ExpertMessage).filter(
        ExpertMessage.engagement_id == engagement_id,
        ExpertMessage.sender_id != current_user.id,
        ExpertMessage.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
    
    results = []
    for msg in messages:
        results.append({
            "id": msg.id,
            "engagement_id": msg.engagement_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "attachments": json.loads(msg.attachments) if msg.attachments else [],
            "is_read": msg.is_read,
            "is_ai_suggestion": msg.is_ai_suggestion,
            "created_at": msg.created_at,
            "sender_name": msg.sender.name if msg.sender else None,
        })
    
    return results


@router.post("/engagements/{engagement_id}/messages", response_model=dict)
async def send_message(
    engagement_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in an engagement"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    expert_profile = engagement.expert_profile
    is_expert = expert_profile and expert_profile.user_id == current_user.id
    is_client = engagement.user_id == current_user.id
    
    if not is_expert and not is_client:
        raise HTTPException(status_code=403, detail="Not authorized to message in this engagement")
    
    message = ExpertMessage(
        engagement_id=engagement_id,
        sender_id=current_user.id,
        content=data.content,
        attachments=json.dumps(data.attachments) if data.attachments else None,
        is_read=False
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return {
        "id": message.id,
        "engagement_id": message.engagement_id,
        "sender_id": message.sender_id,
        "content": message.content,
        "created_at": message.created_at,
    }


@router.post("/engagements/{engagement_id}/reviews", response_model=dict)
async def create_review(
    engagement_id: int,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review for a completed engagement"""
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    if engagement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can review the engagement")
    
    if engagement.status != EngagementStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only review completed engagements")
    
    if engagement.is_reviewed:
        raise HTTPException(status_code=400, detail="Engagement already reviewed")
    
    review = ExpertReview(
        engagement_id=engagement_id,
        expert_profile_id=engagement.expert_profile_id,
        reviewer_id=current_user.id,
        overall_rating=data.overall_rating,
        expertise_rating=data.expertise_rating,
        communication_rating=data.communication_rating,
        responsiveness_rating=data.responsiveness_rating,
        value_for_money_rating=data.value_for_money_rating,
        review_text=data.review_text,
        would_recommend=data.would_recommend,
        would_work_again=data.would_work_again
    )
    
    db.add(review)
    
    engagement.is_reviewed = True
    
    expert_profile = engagement.expert_profile
    if expert_profile:
        expert_profile.total_reviews += 1
        all_reviews = db.query(ExpertReview).filter(
            ExpertReview.expert_profile_id == expert_profile.id
        ).all()
        if all_reviews:
            expert_profile.avg_rating = sum(r.overall_rating for r in all_reviews) / len(all_reviews)
    
    db.commit()
    db.refresh(review)
    
    return {
        "id": review.id,
        "overall_rating": review.overall_rating,
        "message": "Review submitted successfully"
    }


@router.get("/experts/{expert_id}/reviews", response_model=List[dict])
async def get_expert_reviews(
    expert_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get reviews for an expert"""
    reviews = db.query(ExpertReview).filter(
        ExpertReview.expert_profile_id == expert_id,
        ExpertReview.is_public == True
    ).order_by(ExpertReview.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for review in reviews:
        results.append({
            "id": review.id,
            "overall_rating": review.overall_rating,
            "expertise_rating": review.expertise_rating,
            "communication_rating": review.communication_rating,
            "responsiveness_rating": review.responsiveness_rating,
            "value_for_money_rating": review.value_for_money_rating,
            "review_text": review.review_text,
            "would_recommend": review.would_recommend,
            "would_work_again": review.would_work_again,
            "expert_response": review.expert_response,
            "created_at": review.created_at,
            "reviewer_name": review.reviewer.name if review.reviewer else "Anonymous",
        })
    
    return results


@router.get("/categories")
async def list_expert_categories():
    """List all expert categories"""
    return [
        {"value": c.value, "label": c.name.replace("_", " ").title()}
        for c in ExpertCategory
    ]


@router.get("/specializations")
async def list_specializations():
    """List all specializations"""
    return [
        {"value": s.value, "label": s.name.replace("_", " ").title()}
        for s in ExpertSpecialization
    ]


@router.get("/match/opportunity/{opportunity_id}", response_model=dict)
async def get_matched_experts_for_opportunity(
    opportunity_id: int,
    limit: int = 5,
    ai_enhanced: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get experts matched to a specific opportunity.
    
    Uses weighted scoring algorithm based on:
    - Category alignment (30%)
    - Specialization overlap (25%)
    - Industry match (20%)
    - Success metrics (15%)
    - Availability (5%)
    - Rating (5%)
    
    Set ai_enhanced=true for AI-powered insights about each match.
    """
    from app.services.expert_matcher import get_recommended_experts, get_ai_enhanced_matches
    
    if ai_enhanced:
        result = await get_ai_enhanced_matches(db, opportunity_id, limit=limit)
        return result
    
    experts = get_recommended_experts(db, opportunity_id, limit=limit)
    
    return {
        "experts": experts,
        "total_matches": len(experts),
        "ai_insights": None
    }


# ==============================
# Stripe Connect for Expert Payouts
# ==============================

@router.post("/connect/onboarding", response_model=dict)
async def start_connect_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start Stripe Connect onboarding for an expert.
    Creates a Connect Express account and returns onboarding URL.
    """
    from app.services.stripe_service import StripeService
    import os
    
    expert_profile = db.query(ExpertProfile).filter(
        ExpertProfile.user_id == current_user.id
    ).first()
    
    if not expert_profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    base_url = os.getenv("REPLIT_DOMAINS", "").split(",")[0]
    if base_url:
        base_url = f"https://{base_url}"
    else:
        base_url = "http://localhost:5000"
    
    if not expert_profile.stripe_connect_account_id:
        account = StripeService.create_connect_account(
            email=current_user.email,
            expert_profile_id=expert_profile.id
        )
        expert_profile.stripe_connect_account_id = account.id
        db.commit()
    
    account_link = StripeService.create_connect_account_link(
        account_id=expert_profile.stripe_connect_account_id,
        refresh_url=f"{base_url}/expert/connect/refresh",
        return_url=f"{base_url}/expert/connect/complete"
    )
    
    return {
        "url": account_link.url,
        "account_id": expert_profile.stripe_connect_account_id
    }


@router.get("/connect/status", response_model=dict)
async def get_connect_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Stripe Connect account status for an expert.
    """
    from app.services.stripe_service import StripeService
    
    expert_profile = db.query(ExpertProfile).filter(
        ExpertProfile.user_id == current_user.id
    ).first()
    
    if not expert_profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    if not expert_profile.stripe_connect_account_id:
        return {
            "connected": False,
            "onboarding_complete": False,
            "payouts_enabled": False,
            "account_id": None
        }
    
    try:
        account = StripeService.get_connect_account(expert_profile.stripe_connect_account_id)
        
        details_submitted = account.details_submitted
        payouts_enabled = account.payouts_enabled
        
        if details_submitted != expert_profile.stripe_connect_onboarding_complete:
            expert_profile.stripe_connect_onboarding_complete = details_submitted
        if payouts_enabled != expert_profile.stripe_connect_payouts_enabled:
            expert_profile.stripe_connect_payouts_enabled = payouts_enabled
        db.commit()
        
        return {
            "connected": True,
            "onboarding_complete": details_submitted,
            "payouts_enabled": payouts_enabled,
            "account_id": expert_profile.stripe_connect_account_id,
            "charges_enabled": account.charges_enabled
        }
    except Exception as e:
        logger.error(f"Error checking Connect status: {e}")
        return {
            "connected": True,
            "onboarding_complete": expert_profile.stripe_connect_onboarding_complete,
            "payouts_enabled": expert_profile.stripe_connect_payouts_enabled,
            "account_id": expert_profile.stripe_connect_account_id,
            "error": str(e)
        }


@router.post("/engagements/{engagement_id}/pay", response_model=dict)
async def create_engagement_payment(
    engagement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a payment for an accepted engagement.
    Uses Stripe Connect to transfer funds to the expert (85/15 split).
    """
    from app.services.stripe_service import StripeService
    
    engagement = db.query(ExpertEngagement).filter(ExpertEngagement.id == engagement_id).first()
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    if engagement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can pay for the engagement")
    
    if engagement.status != EngagementStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Engagement must be accepted before payment")
    
    if engagement.stripe_payment_intent_id:
        raise HTTPException(status_code=400, detail="Payment already initiated")
    
    expert_profile = engagement.expert_profile
    if not expert_profile or not expert_profile.stripe_connect_account_id:
        raise HTTPException(
            status_code=400, 
            detail="Expert has not completed payment setup"
        )
    
    if not expert_profile.stripe_connect_payouts_enabled:
        raise HTTPException(
            status_code=400,
            detail="Expert's payment account is not yet ready for payouts"
        )
    
    if not current_user.stripe_customer_id:
        from app.services.stripe_service import get_stripe_client
        client = get_stripe_client()
        customer = client.Customer.create(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": str(current_user.id)}
        )
        current_user.stripe_customer_id = customer.id
        db.commit()
    
    amount_cents = engagement.final_amount_cents or engagement.proposed_amount_cents
    if not amount_cents:
        raise HTTPException(status_code=400, detail="No payment amount set")
    
    platform_fee_cents, expert_payout_cents = StripeService.calculate_platform_split(amount_cents)
    
    engagement.final_amount_cents = amount_cents
    engagement.platform_fee_cents = platform_fee_cents
    engagement.expert_payout_cents = expert_payout_cents
    
    payment_intent = StripeService.create_payment_intent_with_transfer(
        amount_cents=amount_cents,
        customer_id=current_user.stripe_customer_id,
        expert_connect_account_id=expert_profile.stripe_connect_account_id,
        engagement_id=engagement.id,
        user_id=current_user.id
    )
    
    engagement.stripe_payment_intent_id = payment_intent.id
    engagement.escrow_status = "pending"
    db.commit()
    
    return {
        "client_secret": payment_intent.client_secret,
        "payment_intent_id": payment_intent.id,
        "amount_cents": amount_cents,
        "platform_fee_cents": platform_fee_cents,
        "expert_payout_cents": expert_payout_cents
    }


@router.get("/connect/earnings", response_model=dict)
async def get_expert_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get earnings summary for an expert.
    """
    expert_profile = db.query(ExpertProfile).filter(
        ExpertProfile.user_id == current_user.id
    ).first()
    
    if not expert_profile:
        raise HTTPException(status_code=404, detail="Expert profile not found")
    
    completed_engagements = db.query(ExpertEngagement).filter(
        ExpertEngagement.expert_profile_id == expert_profile.id,
        ExpertEngagement.status == EngagementStatus.COMPLETED
    ).all()
    
    total_earned_cents = sum(e.expert_payout_cents or 0 for e in completed_engagements)
    total_platform_fees_cents = sum(e.platform_fee_cents or 0 for e in completed_engagements)
    
    pending_engagements = db.query(ExpertEngagement).filter(
        ExpertEngagement.expert_profile_id == expert_profile.id,
        ExpertEngagement.status.in_([EngagementStatus.IN_PROGRESS, EngagementStatus.ACCEPTED])
    ).all()
    
    pending_earnings_cents = sum(e.expert_payout_cents or 0 for e in pending_engagements)
    
    return {
        "total_earned_cents": total_earned_cents,
        "total_platform_fees_cents": total_platform_fees_cents,
        "pending_earnings_cents": pending_earnings_cents,
        "completed_engagements": len(completed_engagements),
        "active_engagements": len(pending_engagements),
        "payouts_enabled": expert_profile.stripe_connect_payouts_enabled
    }
