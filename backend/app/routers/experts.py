"""
Experts Router - Expert API Gateway

Provides:
- Expert catalog (CRUD)
- AI-powered expert matching
- Instant quote generation
- Session/project booking
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json

from app.core.dependencies import get_current_admin_user, get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.models.expert import Expert, ExpertPricingModel
from app.models.opportunity import Opportunity
from app.models.user_profile import UserProfile
from app.models.booking import ExpertBooking, BookingType, BookingStatus, PaymentModel
from app.schemas.expert import ExpertCreate, ExpertUpdate, ExpertResponse
from app.services.json_codec import dumps_json, loads_json


from app.services.launch_entitlements import monthly_feature_lock

router = APIRouter(dependencies=[Depends(monthly_feature_lock("expert_marketplace"))])


class ExpertMatchRequest(BaseModel):
    opportunity_id: Optional[int] = None
    required_skills: Optional[List[str]] = None
    budget_min_cents: Optional[int] = None
    budget_max_cents: Optional[int] = None
    timeline_max_days: Optional[int] = None


class ExpertMatchResponse(BaseModel):
    expert_id: int
    name: str
    headline: Optional[str]
    match_score: float
    pricing_options: List[dict]
    availability: Optional[str]
    ai_confidence: float


class QuoteRequest(BaseModel):
    opportunity_id: Optional[int] = None
    service_type: str = "consultation"
    estimated_hours: Optional[float] = None
    description: Optional[str] = None


class QuoteResponse(BaseModel):
    expert_id: int
    quote_type: str
    amount_cents: int
    currency: str
    valid_until: datetime
    pricing_options: List[dict]
    estimated_delivery_days: Optional[int]


class BookingRequest(BaseModel):
    opportunity_id: Optional[int] = None
    booking_type: str = "session"
    payment_model: str = "fixed"
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = 60
    amount_cents: Optional[int] = None


class BookingResponse(BaseModel):
    id: int
    expert_id: int
    user_id: int
    booking_type: str
    status: str
    title: Optional[str]
    quoted_amount_cents: Optional[int]
    scheduled_at: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ExpertResponse])
def list_experts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(Expert)
    if active_only:
        q = q.filter(Expert.is_active == True)
    experts = q.order_by(desc(Expert.created_at)).offset(skip).limit(limit).all()

    # Normalize JSON fields for response model
    out: list[ExpertResponse] = []
    for e in experts:
        out.append(
            ExpertResponse(
                id=e.id,
                name=e.name,
                headline=e.headline,
                bio=e.bio,
                website_url=e.website_url,
                skills=loads_json(e.skills, default=[]),
                specialization=loads_json(e.specialization, default=[]),
                pricing_model=e.pricing_model.value if hasattr(e.pricing_model, "value") else str(e.pricing_model),
                hourly_rate_cents=e.hourly_rate_cents,
                fixed_price_cents=e.fixed_price_cents,
                success_fee_bps=e.success_fee_bps,
                currency=e.currency,
                availability=loads_json(e.availability, default=None),
                is_active=e.is_active,
            )
        )
    return out


@router.post("/", response_model=ExpertResponse, status_code=status.HTTP_201_CREATED)
def create_expert(
    payload: ExpertCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    try:
        pricing_model = ExpertPricingModel(payload.pricing_model)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid pricing_model")

    expert = Expert(
        name=payload.name,
        headline=payload.headline,
        bio=payload.bio,
        website_url=payload.website_url,
        skills=dumps_json(payload.skills or []),
        specialization=dumps_json(payload.specialization or []),
        pricing_model=pricing_model,
        hourly_rate_cents=payload.hourly_rate_cents,
        fixed_price_cents=payload.fixed_price_cents,
        success_fee_bps=payload.success_fee_bps,
        currency=payload.currency,
        availability=dumps_json(payload.availability) if payload.availability is not None else None,
        is_active=payload.is_active,
    )
    db.add(expert)
    db.commit()
    db.refresh(expert)

    return ExpertResponse(
        id=expert.id,
        name=expert.name,
        headline=expert.headline,
        bio=expert.bio,
        website_url=expert.website_url,
        skills=loads_json(expert.skills, default=[]),
        specialization=loads_json(expert.specialization, default=[]),
        pricing_model=expert.pricing_model.value,
        hourly_rate_cents=expert.hourly_rate_cents,
        fixed_price_cents=expert.fixed_price_cents,
        success_fee_bps=expert.success_fee_bps,
        currency=expert.currency,
        availability=loads_json(expert.availability, default=None),
        is_active=expert.is_active,
    )


@router.get("/{expert_id}", response_model=ExpertResponse)
def get_expert(
    expert_id: int,
    db: Session = Depends(get_db),
):
    """Get expert by ID."""
    expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    return ExpertResponse(
        id=expert.id,
        name=expert.name,
        headline=expert.headline,
        bio=expert.bio,
        website_url=expert.website_url,
        skills=loads_json(expert.skills, default=[]),
        specialization=loads_json(expert.specialization, default=[]),
        pricing_model=expert.pricing_model.value if hasattr(expert.pricing_model, "value") else str(expert.pricing_model),
        hourly_rate_cents=expert.hourly_rate_cents,
        fixed_price_cents=expert.fixed_price_cents,
        success_fee_bps=expert.success_fee_bps,
        currency=expert.currency,
        availability=loads_json(expert.availability, default=None),
        is_active=expert.is_active,
    )


@router.post("/match", response_model=List[ExpertMatchResponse])
def match_experts(
    payload: ExpertMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    AI-powered expert matching.
    
    Matches experts based on user profile, opportunity requirements, and constraints.
    """
    experts = db.query(Expert).filter(Expert.is_active == True).all()
    
    if not experts:
        return []
    
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    user_skills = loads_json(user_profile.skills if user_profile else None, default=[])
    user_skills_normalized = {s.lower().strip() for s in user_skills if s}
    
    opportunity = None
    required_skills = set()
    if payload.opportunity_id:
        opportunity = db.query(Opportunity).filter(Opportunity.id == payload.opportunity_id).first()
    
    if payload.required_skills:
        required_skills = {s.lower().strip() for s in payload.required_skills}
    
    skill_gaps = required_skills - user_skills_normalized
    
    matches = []
    for expert in experts:
        expert_skills = loads_json(expert.skills, default=[])
        expert_specs = loads_json(expert.specialization, default=[])
        expert_terms = {s.lower().strip() for s in (expert_skills + expert_specs) if s}
        
        match_score = 0.0
        
        if skill_gaps:
            gaps_covered = len(skill_gaps & expert_terms)
            match_score += (gaps_covered / len(skill_gaps)) * 50 if skill_gaps else 0
        else:
            if expert_terms:
                match_score += 30
        
        if opportunity and opportunity.category:
            cat_lower = opportunity.category.lower()
            if any(cat_lower in s for s in expert_terms):
                match_score += 20
        
        if expert.success_rate:
            match_score += float(expert.success_rate) * 0.2
        
        if payload.budget_max_cents:
            if expert.fixed_price_cents and expert.fixed_price_cents <= payload.budget_max_cents:
                match_score += 10
        
        pricing_options = []
        if expert.fixed_price_cents:
            pricing_options.append({
                "type": "fixed_price",
                "amount_cents": expert.fixed_price_cents,
                "currency": expert.currency or "usd",
            })
        if expert.hourly_rate_cents:
            pricing_options.append({
                "type": "hourly",
                "amount_cents": expert.hourly_rate_cents,
                "currency": expert.currency or "usd",
            })
        if expert.success_fee_bps:
            pricing_options.append({
                "type": "success_fee",
                "percentage_bps": expert.success_fee_bps,
            })
        
        ai_confidence = min(0.95, 0.5 + (match_score / 200))
        availability_text = "Available now"
        
        matches.append(ExpertMatchResponse(
            expert_id=expert.id,
            name=expert.name,
            headline=expert.headline,
            match_score=round(match_score, 2),
            pricing_options=pricing_options,
            availability=availability_text,
            ai_confidence=round(ai_confidence, 2),
        ))
    
    matches.sort(key=lambda x: x.match_score, reverse=True)
    return matches[:10]


@router.post("/{expert_id}/quote", response_model=QuoteResponse)
def get_expert_quote(
    expert_id: int,
    payload: QuoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get instant quote from an expert based on service type."""
    expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    if not expert.is_active:
        raise HTTPException(status_code=400, detail="Expert is not currently available")
    
    service_multipliers = {
        "quick_question": 0.25,
        "consultation": 1.0,
        "review": 1.5,
        "project": 5.0,
        "retainer": 20.0,
    }
    multiplier = service_multipliers.get(payload.service_type, 1.0)
    
    base_amount = 0
    quote_type = "fixed"
    
    if expert.fixed_price_cents:
        base_amount = int(expert.fixed_price_cents * multiplier)
        quote_type = "fixed"
    elif expert.hourly_rate_cents:
        hours = payload.estimated_hours or (2 * multiplier)
        base_amount = int(expert.hourly_rate_cents * hours)
        quote_type = "hourly"
    else:
        base_amount = int(5000 * multiplier)
        quote_type = "estimated"
    
    delivery_days = {"quick_question": 1, "consultation": 3, "review": 5, "project": 14, "retainer": 30}
    
    pricing_options = [{"type": quote_type, "amount_cents": base_amount, "description": f"{payload.service_type.replace('_', ' ').title()}"}]
    
    if expert.success_fee_bps:
        pricing_options.append({"type": "success_fee", "percentage_bps": expert.success_fee_bps})
    
    return QuoteResponse(
        expert_id=expert.id,
        quote_type=quote_type,
        amount_cents=base_amount,
        currency=expert.currency or "usd",
        valid_until=datetime.utcnow() + timedelta(days=7),
        pricing_options=pricing_options,
        estimated_delivery_days=delivery_days.get(payload.service_type, 7),
    )


@router.post("/{expert_id}/book", response_model=BookingResponse)
def book_expert(
    expert_id: int,
    payload: BookingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Book an expert session or project."""
    expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    if not expert.is_active:
        raise HTTPException(status_code=400, detail="Expert is not currently available")
    
    try:
        booking_type = BookingType(payload.booking_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid booking_type: {payload.booking_type}")
    
    try:
        payment_model = PaymentModel(payload.payment_model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment_model: {payload.payment_model}")
    
    quoted_amount = payload.amount_cents
    if not quoted_amount:
        if expert.fixed_price_cents:
            quoted_amount = expert.fixed_price_cents
        elif expert.hourly_rate_cents and payload.duration_minutes:
            hours = payload.duration_minutes / 60.0
            quoted_amount = int(expert.hourly_rate_cents * hours)
        else:
            quoted_amount = 5000
    
    booking = ExpertBooking(
        user_id=current_user.id,
        expert_id=expert_id,
        opportunity_id=payload.opportunity_id,
        booking_type=booking_type,
        status=BookingStatus.PENDING,
        payment_model=payment_model,
        title=payload.title or f"Booking with {expert.name}",
        description=payload.description,
        quoted_amount_cents=quoted_amount,
        hourly_rate_cents=expert.hourly_rate_cents,
        currency=expert.currency or "usd",
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
    )
    
    if payment_model == PaymentModel.SUCCESS_FEE:
        booking.success_fee_percentage_bps = expert.success_fee_bps or 1500
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return BookingResponse(
        id=booking.id,
        expert_id=booking.expert_id,
        user_id=booking.user_id,
        booking_type=booking.booking_type.value,
        status=booking.status.value,
        title=booking.title,
        quoted_amount_cents=booking.quoted_amount_cents,
        scheduled_at=booking.scheduled_at,
        created_at=booking.created_at,
    )


@router.get("/bookings/my", response_model=List[BookingResponse])
def list_my_bookings(
    status_filter: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List current user's expert bookings."""
    q = db.query(ExpertBooking).filter(ExpertBooking.user_id == current_user.id)
    
    if status_filter:
        try:
            status_enum = BookingStatus(status_filter)
            q = q.filter(ExpertBooking.status == status_enum)
        except ValueError:
            pass
    
    bookings = q.order_by(desc(ExpertBooking.created_at)).offset(skip).limit(limit).all()
    
    return [
        BookingResponse(
            id=b.id,
            expert_id=b.expert_id,
            user_id=b.user_id,
            booking_type=b.booking_type.value,
            status=b.status.value,
            title=b.title,
            quoted_amount_cents=b.quoted_amount_cents,
            scheduled_at=b.scheduled_at,
            created_at=b.created_at,
        )
        for b in bookings
    ]


@router.post("/bookings/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Confirm a pending booking."""
    booking = db.query(ExpertBooking).filter(ExpertBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Booking is not pending")
    
    booking.status = BookingStatus.CONFIRMED
    db.commit()
    
    return {"message": "Booking confirmed", "status": booking.status.value}


@router.post("/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    rating: Optional[int] = Query(None, ge=1, le=5),
    review: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Complete a booking and optionally leave a review."""
    booking = db.query(ExpertBooking).filter(ExpertBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status not in [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]:
        raise HTTPException(status_code=400, detail="Booking cannot be completed from current status")
    
    booking.status = BookingStatus.COMPLETED
    booking.completed_at = datetime.utcnow()
    if rating:
        booking.user_rating = rating
    if review:
        booking.user_review = review
    
    db.commit()
    
    return {"message": "Booking completed", "status": booking.status.value}


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Cancel a booking."""
    booking = db.query(ExpertBooking).filter(ExpertBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status in [BookingStatus.COMPLETED, BookingStatus.REFUNDED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed booking")
    
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Booking cancelled", "status": booking.status.value}
@router.put("/{expert_id}", response_model=ExpertResponse)
def update_expert(
    expert_id: int,
    payload: ExpertUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    data = payload.model_dump(exclude_unset=True)
    if "pricing_model" in data and data["pricing_model"] is not None:
        expert.pricing_model = ExpertPricingModel(data["pricing_model"])

    if "skills" in data:
        expert.skills = dumps_json(data.get("skills") or [])
    if "specialization" in data:
        expert.specialization = dumps_json(data.get("specialization") or [])
    if "availability" in data:
        expert.availability = dumps_json(data.get("availability")) if data.get("availability") is not None else None

    for key in [
        "name",
        "headline",
        "bio",
        "website_url",
        "hourly_rate_cents",
        "fixed_price_cents",
        "success_fee_bps",
        "currency",
        "is_active",
    ]:
        if key in data:
            setattr(expert, key, data.get(key))

    db.commit()
    db.refresh(expert)

    return ExpertResponse(
        id=expert.id,
        name=expert.name,
        headline=expert.headline,
        bio=expert.bio,
        website_url=expert.website_url,
        skills=loads_json(expert.skills, default=[]),
        specialization=loads_json(expert.specialization, default=[]),
        pricing_model=expert.pricing_model.value,
        hourly_rate_cents=expert.hourly_rate_cents,
        fixed_price_cents=expert.fixed_price_cents,
        success_fee_bps=expert.success_fee_bps,
        currency=expert.currency,
        availability=loads_json(expert.availability, default=None),
        is_active=expert.is_active,
    )

