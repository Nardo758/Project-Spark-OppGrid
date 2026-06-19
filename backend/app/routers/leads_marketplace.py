"""
Signals Marketplace Router

Public endpoints for browsing, purchasing, and managing saved searches for market signals.
Signals are real opportunities derived from the Hub pipeline (scraped data, AI analysis).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.lead import Lead, LeadStatus, LeadPurchase
from app.models.saved_search import SavedSearch
from app.core.dependencies import get_current_user, get_current_user_optional

router = APIRouter()


class MarketplaceSignalResponse(BaseModel):
    id: int
    title: str
    category: str
    subcategory: Optional[str]
    location: Optional[str]
    quality_score: int
    price: float
    source_platform: Optional[str]
    confidence_tier: Optional[str]
    ai_summary: Optional[str]
    ai_urgency_level: Optional[str]
    market_size: Optional[str]
    verified: bool
    is_purchased: bool = False
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MarketplaceSignalListResponse(BaseModel):
    items: List[MarketplaceSignalResponse]
    total: int
    categories: List[dict]


class SavedSearchCreate(BaseModel):
    name: str
    query: Optional[str] = None
    filters: Optional[dict] = None
    alert_enabled: bool = True
    alert_frequency: str = "daily"


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    query: Optional[str]
    filters: Optional[dict]
    alert_enabled: bool
    alert_frequency: str
    match_count: int
    last_alerted_at: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PurchaseRequest(BaseModel):
    signal_id: int
    payment_method_id: Optional[str] = None


class PurchaseResponse(BaseModel):
    id: int
    signal_id: int
    price_paid: float
    status: str
    purchased_at: datetime
    expires_at: Optional[datetime]
    signal: Optional[MarketplaceSignalResponse]


SIGNAL_PRICING = {
    "high": 149.00,
    "medium": 99.00,
    "low": 49.00,
}

CATEGORIES = [
    {"id": "saas", "name": "SaaS", "count": 0},
    {"id": "ecommerce", "name": "E-commerce", "count": 0},
    {"id": "healthcare", "name": "Healthcare", "count": 0},
    {"id": "fintech", "name": "FinTech", "count": 0},
    {"id": "manufacturing", "name": "Manufacturing", "count": 0},
    {"id": "services", "name": "Professional Services", "count": 0},
]


def _get_signal_quality_score(opp: Opportunity) -> int:
    """Calculate quality score from opportunity AI fields."""
    score = 50
    if opp.ai_opportunity_score:
        score = opp.ai_opportunity_score
    else:
        # Fallback: derive from severity + confidence tier
        if opp.severity:
            score = opp.severity * 20
        if opp.confidence_tier == "goldmine":
            score = max(score, 85)
        elif opp.confidence_tier == "validated":
            score = max(score, 70)
        elif opp.confidence_tier == "weak_signal":
            score = max(score, 50)
    return min(score, 100)


def _get_signal_price(quality_score: int) -> float:
    """Get price based on quality score."""
    if quality_score >= 80:
        return SIGNAL_PRICING["high"]
    elif quality_score >= 60:
        return SIGNAL_PRICING["medium"]
    else:
        return SIGNAL_PRICING["low"]


def _opportunity_to_signal_response(opp: Opportunity, is_purchased: bool = False) -> dict:
    """Convert Opportunity to marketplace signal response."""
    quality = _get_signal_quality_score(opp)
    location = opp.city or opp.region or opp.country or opp.geographic_scope
    return {
        "id": opp.id,
        "title": opp.title,
        "category": opp.category or "general",
        "subcategory": opp.subcategory,
        "location": location,
        "quality_score": quality,
        "price": _get_signal_price(quality),
        "source_platform": opp.source_platform,
        "confidence_tier": opp.confidence_tier,
        "ai_summary": opp.ai_summary,
        "ai_urgency_level": opp.ai_urgency_level,
        "market_size": opp.market_size or opp.ai_market_size_estimate,
        "verified": opp.moderation_status == "approved",
        "is_purchased": is_purchased,
        "created_at": opp.created_at,
    }


@router.get("/browse", response_model=MarketplaceSignalListResponse)
def browse_signals(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    min_quality: Optional[int] = Query(None, ge=0, le=100),
    max_price: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("quality", regex="^(quality|price|recent)$"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Browse available market signals derived from real opportunity data."""
    # Build query against Opportunity (real data from Hub pipeline)
    query = db.query(Opportunity).filter(
        Opportunity.status.in_(["active"]),
        Opportunity.moderation_status.in_(["approved", "pending_review"])
    )

    if category:
        cat_lower = category.lower()
        query = query.filter(
            or_(
                Opportunity.category.ilike(f"%{cat_lower}%"),
                Opportunity.subcategory.ilike(f"%{cat_lower}%")
            )
        )

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Opportunity.title.ilike(search_term),
                Opportunity.description.ilike(search_term),
                Opportunity.category.ilike(search_term),
                Opportunity.subcategory.ilike(search_term)
            )
        )

    # Count total
    total = query.count()

    # Sort
    if sort_by == "recent":
        query = query.order_by(desc(Opportunity.created_at))
    elif sort_by == "price":
        # Price is derived from quality; sort by ai_opportunity_score as proxy
        query = query.order_by(desc(Opportunity.ai_opportunity_score))
    else:
        # quality: sort by ai_opportunity_score, then severity
        query = query.order_by(
            desc(Opportunity.ai_opportunity_score),
            desc(Opportunity.severity),
            desc(Opportunity.created_at)
        )

    opportunities = query.offset(skip).limit(limit).all()

    # Get purchased ids (for now, check LeadPurchase table as fallback)
    purchased_ids: set = set()
    if current_user:
        p_rows = db.query(LeadPurchase).filter(
            LeadPurchase.user_id == current_user.id,
            LeadPurchase.status == "completed"
        ).all()
        purchased_ids = {p.lead_id for p in p_rows}

    items = []
    for opp in opportunities:
        quality = _get_signal_quality_score(opp)
        price = _get_signal_price(quality)

        if min_quality and quality < min_quality:
            continue
        if max_price and price > max_price:
            continue

        items.append(_opportunity_to_signal_response(opp, opp.id in purchased_ids))

    # Category counts from real opportunities
    cat_rows = db.query(
        Opportunity.category,
        func.count(Opportunity.id)
    ).filter(
        Opportunity.status == "active",
        Opportunity.moderation_status.in_(["approved", "pending_review"])
    ).group_by(Opportunity.category).all()

    categories = []
    for cat in CATEGORIES:
        count = next((c[1] for c in cat_rows if c[0] and cat["id"].lower() in c[0].lower()), 0)
        categories.append({**cat, "count": count})

    return {
        "items": items,
        "total": total,
        "categories": categories,
    }


@router.get("/signal/{signal_id}", response_model=MarketplaceSignalResponse)
def get_signal_details(
    signal_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get details of a specific market signal."""
    opp = db.query(Opportunity).filter(Opportunity.id == signal_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Signal not found")

    is_purchased = False
    if current_user:
        purchase = db.query(LeadPurchase).filter(
            LeadPurchase.user_id == current_user.id,
            LeadPurchase.lead_id == signal_id,
            LeadPurchase.status == "completed"
        ).first()
        is_purchased = purchase is not None

    return _opportunity_to_signal_response(opp, is_purchased)


@router.post("/purchase", response_model=PurchaseResponse)
def purchase_signal(
    payload: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Purchase access to a market signal (unlocks full AI analysis + source data)."""
    opp = db.query(Opportunity).filter(Opportunity.id == payload.signal_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Check if already purchased
    existing = db.query(LeadPurchase).filter(
        LeadPurchase.user_id == current_user.id,
        LeadPurchase.lead_id == payload.signal_id,
        LeadPurchase.status == "completed"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this signal")

    quality = _get_signal_quality_score(opp)
    price = Decimal(str(_get_signal_price(quality)))

    purchase = LeadPurchase(
        user_id=current_user.id,
        lead_id=opp.id,
        price_paid=price,
        status="completed",
        expires_at=datetime.utcnow() + timedelta(days=90),
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    return {
        "id": purchase.id,
        "signal_id": purchase.lead_id,
        "price_paid": float(purchase.price_paid),
        "status": purchase.status,
        "purchased_at": purchase.purchased_at,
        "expires_at": purchase.expires_at,
        "signal": _opportunity_to_signal_response(opp, True),
    }


@router.get("/my-purchases", response_model=List[PurchaseResponse])
def get_my_purchases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of purchased signals."""
    purchases = db.query(LeadPurchase).filter(
        LeadPurchase.user_id == current_user.id
    ).order_by(desc(LeadPurchase.purchased_at)).all()

    result = []
    for p in purchases:
        signal_data = None
        opp = db.query(Opportunity).filter(Opportunity.id == p.lead_id).first()
        if opp:
            signal_data = _opportunity_to_signal_response(opp, True)

        result.append({
            "id": p.id,
            "signal_id": p.lead_id,
            "price_paid": float(p.price_paid),
            "status": p.status,
            "purchased_at": p.purchased_at,
            "expires_at": p.expires_at,
            "signal": signal_data,
        })

    return result


@router.get("/saved-searches", response_model=List[SavedSearchResponse])
def list_saved_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's saved searches."""
    searches = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id
    ).order_by(desc(SavedSearch.created_at)).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "query": s.query,
            "filters": s.filters,
            "alert_enabled": s.alert_enabled,
            "alert_frequency": s.alert_frequency,
            "match_count": s.match_count,
            "last_alerted_at": s.last_alerted_at,
            "created_at": s.created_at,
        }
        for s in searches
    ]


@router.post("/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    payload: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new saved search with optional alerts."""
    existing_count = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id
    ).count()

    if existing_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 saved searches allowed")

    search = SavedSearch(
        user_id=current_user.id,
        name=payload.name,
        query=payload.query,
        filters=payload.filters,
        alert_enabled=payload.alert_enabled,
        alert_frequency=payload.alert_frequency,
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    return {
        "id": search.id,
        "name": search.name,
        "query": search.query,
        "filters": search.filters,
        "alert_enabled": search.alert_enabled,
        "alert_frequency": search.alert_frequency,
        "match_count": search.match_count,
        "last_alerted_at": search.last_alerted_at,
        "created_at": search.created_at,
    }


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved search."""
    search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    db.delete(search)
    db.commit()
    return None


@router.patch("/saved-searches/{search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    search_id: int,
    payload: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a saved search."""
    search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    search.name = payload.name
    search.query = payload.query
    search.filters = payload.filters
    search.alert_enabled = payload.alert_enabled
    search.alert_frequency = payload.alert_frequency

    db.commit()
    db.refresh(search)

    return {
        "id": search.id,
        "name": search.name,
        "query": search.query,
        "filters": search.filters,
        "alert_enabled": search.alert_enabled,
        "alert_frequency": search.alert_frequency,
        "match_count": search.match_count,
        "last_alerted_at": search.last_alerted_at,
        "created_at": search.created_at,
    }
