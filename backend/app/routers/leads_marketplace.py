"""
Leads Marketplace Router

Public endpoints for browsing, purchasing, and managing saved searches for leads.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, cast, String
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.saved_search import SavedSearch
from app.models.lead_purchase import LeadPurchase
from app.core.dependencies import get_current_user, get_current_user_optional

router = APIRouter()


class MarketplaceLeadResponse(BaseModel):
    id: int
    category: str
    company: Optional[str]
    location: Optional[str]
    quality_score: int
    price: float
    contact_count: int
    last_active: Optional[datetime]
    verified: bool
    is_purchased: bool = False

    class Config:
        from_attributes = True


class MarketplaceLeadListResponse(BaseModel):
    items: List[MarketplaceLeadResponse]
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
    lead_id: int
    payment_method_id: Optional[str] = None


class PurchaseResponse(BaseModel):
    id: int
    lead_id: int
    price_paid: float
    status: str
    purchased_at: datetime
    expires_at: Optional[datetime]
    lead: Optional[MarketplaceLeadResponse]


LEAD_PRICING = {
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


def _get_quality_score(lead: Lead) -> int:
    """Calculate quality score based on lead completeness and engagement."""
    score = 50
    if lead.name:
        score += 10
    if lead.company:
        score += 15
    if lead.phone:
        score += 10
    if lead.interest_category:
        score += 5
    if lead.status == LeadStatus.QUALIFIED:
        score += 10
    return min(score, 100)


def _get_lead_price(quality_score: int) -> float:
    """Get price based on quality score."""
    if quality_score >= 80:
        return LEAD_PRICING["high"]
    elif quality_score >= 60:
        return LEAD_PRICING["medium"]
    else:
        return LEAD_PRICING["low"]


def _lead_to_marketplace_response(lead: Lead, is_purchased: bool = False) -> dict:
    """Convert Lead to marketplace response."""
    quality = _get_quality_score(lead)
    return {
        "id": lead.id,
        "category": lead.interest_category or "general",
        "company": lead.company,
        "location": None,
        "quality_score": quality,
        "price": _get_lead_price(quality),
        "contact_count": 1,
        "last_active": lead.last_contacted_at or lead.created_at,
        "verified": lead.status in [LeadStatus.QUALIFIED, LeadStatus.CONVERTED],
        "is_purchased": is_purchased,
    }


@router.get("/browse", response_model=MarketplaceLeadListResponse)
def browse_leads(
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
    """Browse available leads in the marketplace."""
    from sqlalchemy import text as sql_text

    # Build WHERE clauses manually to avoid ORM enum mapping issues
    where_parts = ["status IN ('new', 'qualified')"]
    params: dict = {}

    if category:
        where_parts.append("interest_category ILIKE :category")
        params["category"] = f"%{category}%"

    if search:
        where_parts.append("(company ILIKE :search OR interest_category ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_parts)

    # Count
    count_row = db.execute(sql_text(f"SELECT COUNT(*) FROM leads WHERE {where_sql}"), params).scalar()
    total = count_row or 0

    # Sort
    if sort_by == "recent":
        order_sql = "created_at DESC"
    elif sort_by == "price":
        # price is derived from quality score; sort by name proxy (company) for stability
        order_sql = "company ASC NULLS LAST"
    else:
        # quality: more fields filled = higher score — sort by completeness proxy
        order_sql = "CASE WHEN company IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN phone IS NOT NULL THEN 1 ELSE 0 END DESC, created_at DESC"

    params["limit"] = limit
    params["skip"] = skip
    rows = db.execute(
        sql_text(f"""
            SELECT id, name, company, phone, interest_category, status,
                   last_contacted_at, created_at
            FROM leads
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :skip
        """),
        params,
    ).fetchall()

    # Purchased ids
    purchased_ids: set = set()
    if current_user:
        p_rows = db.execute(
            sql_text("SELECT lead_id FROM lead_purchases WHERE user_id = :uid AND status = 'completed'"),
            {"uid": current_user.id},
        ).fetchall()
        purchased_ids = {r[0] for r in p_rows if r[0]}

    def _score(row) -> int:
        score = 50
        if row[1]:   # name
            score += 10
        if row[2]:   # company
            score += 15
        if row[3]:   # phone
            score += 10
        if row[4]:   # interest_category
            score += 5
        if row[5] in ("qualified", "converted"):
            score += 10
        return min(score, 100)

    def _price(score: int) -> float:
        if score >= 80: return LEAD_PRICING["high"]
        if score >= 60: return LEAD_PRICING["medium"]
        return LEAD_PRICING["low"]

    items = []
    for row in rows:
        lead_id, name, company, phone, cat, status, last_active, created_at = row
        quality = _score(row)
        price = _price(quality)

        if min_quality and quality < min_quality:
            continue
        if max_price and price > max_price:
            continue

        items.append({
            "id": lead_id,
            "category": cat or "general",
            "company": company,
            "location": None,
            "quality_score": quality,
            "price": price,
            "contact_count": 1,
            "last_active": last_active or created_at,
            "verified": status in ("qualified", "converted"),
            "is_purchased": lead_id in purchased_ids,
        })

    # Category counts via raw SQL
    cat_rows = db.execute(
        sql_text("SELECT interest_category, COUNT(*) FROM leads WHERE status IN ('new','qualified') GROUP BY interest_category")
    ).fetchall()

    categories = []
    for cat in CATEGORIES:
        count = next((c[1] for c in cat_rows if c[0] and cat["id"].lower() in c[0].lower()), 0)
        categories.append({**cat, "count": count})

    return {
        "items": items,
        "total": total,
        "categories": categories,
    }


@router.get("/lead/{lead_id}", response_model=MarketplaceLeadResponse)
def get_lead_details(
    lead_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get details of a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    is_purchased = False
    if current_user:
        purchase = db.query(LeadPurchase).filter(
            LeadPurchase.user_id == current_user.id,
            LeadPurchase.lead_id == lead_id,
            LeadPurchase.status == "completed"
        ).first()
        is_purchased = purchase is not None
    
    return _lead_to_marketplace_response(lead, is_purchased)


@router.post("/purchase", response_model=PurchaseResponse)
def purchase_lead(
    payload: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Purchase access to a lead."""
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    existing = db.query(LeadPurchase).filter(
        LeadPurchase.user_id == current_user.id,
        LeadPurchase.lead_id == payload.lead_id,
        LeadPurchase.status == "completed"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already purchased this lead")
    
    quality = _get_quality_score(lead)
    price = Decimal(str(_get_lead_price(quality)))
    
    purchase = LeadPurchase(
        user_id=current_user.id,
        lead_id=lead.id,
        price_paid=price,
        status="completed",
        expires_at=datetime.utcnow() + timedelta(days=90),
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    
    return {
        "id": purchase.id,
        "lead_id": purchase.lead_id,
        "price_paid": float(purchase.price_paid),
        "status": purchase.status,
        "purchased_at": purchase.purchased_at,
        "expires_at": purchase.expires_at,
        "lead": _lead_to_marketplace_response(lead, True),
    }


@router.get("/my-purchases", response_model=List[PurchaseResponse])
def get_my_purchases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of purchased leads."""
    purchases = db.query(LeadPurchase).filter(
        LeadPurchase.user_id == current_user.id
    ).order_by(desc(LeadPurchase.purchased_at)).all()
    
    result = []
    for p in purchases:
        lead_data = None
        if p.lead:
            lead_data = _lead_to_marketplace_response(p.lead, True)
        
        result.append({
            "id": p.id,
            "lead_id": p.lead_id,
            "price_paid": float(p.price_paid),
            "status": p.status,
            "purchased_at": p.purchased_at,
            "expires_at": p.expires_at,
            "lead": lead_data,
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
