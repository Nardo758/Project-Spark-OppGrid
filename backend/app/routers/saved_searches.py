"""
Saved Searches Router

Endpoints for managing saved opportunity searches and alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.db.database import get_db
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.models.subscription import SubscriptionTier
from app.schemas.saved_search import (
    SavedSearchCreate, 
    SavedSearchUpdate, 
    SavedSearchResponse,
    SavedSearchList
)
from app.core.dependencies import get_current_active_user, get_user_subscription_tier

router = APIRouter()

# Free tier limits
FREE_SAVED_SEARCHES_LIMIT = 1
PRO_SAVED_SEARCHES_LIMIT = 10


@router.post("/", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    search_data: SavedSearchCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new saved search with alert preferences
    
    **Tier Limits:**
    - Free: 1 saved search
    - Pro: 10 saved searches
    - Business/Enterprise: Unlimited
    """
    
    from app.services.launch_entitlements import reject_monthly_alerts

    reject_monthly_alerts(db, current_user, search_data.notification_prefs)

    # Check tier limits
    user_tier = get_user_subscription_tier(current_user, db)
    existing_count = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id,
        SavedSearch.is_active == True
    ).count()
    
    if user_tier == SubscriptionTier.FREE and existing_count >= FREE_SAVED_SEARCHES_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Free tier limited to {FREE_SAVED_SEARCHES_LIMIT} saved search. Upgrade to Pro for more."
        )
    
    if user_tier == SubscriptionTier.PRO and existing_count >= PRO_SAVED_SEARCHES_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Pro tier limited to {PRO_SAVED_SEARCHES_LIMIT} saved searches. Upgrade for unlimited."
        )
    
    # Business/Enterprise = unlimited (no check)
    
    # Create saved search
    saved_search = SavedSearch(
        user_id=current_user.id,
        name=search_data.name,
        filters=search_data.filters,
        notification_prefs=search_data.notification_prefs,
        is_active=True
    )
    
    db.add(saved_search)
    db.commit()
    db.refresh(saved_search)
    
    return saved_search


@router.get("/", response_model=SavedSearchList)
def get_saved_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's saved searches
    
    **Query Parameters:**
    - skip: Pagination offset
    - limit: Max results per page
    - include_inactive: Include deleted/inactive searches
    """
    
    query = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id
    )
    
    if not include_inactive:
        query = query.filter(SavedSearch.is_active == True)
    
    query = query.order_by(desc(SavedSearch.created_at))
    
    total = query.count()
    saved_searches = query.offset(skip).limit(limit).all()
    
    return SavedSearchList(
        saved_searches=saved_searches,
        total=total
    )


@router.get("/{search_id}", response_model=SavedSearchResponse)
def get_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific saved search by ID"""
    
    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    return saved_search


@router.patch("/{search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    search_id: int,
    update_data: SavedSearchUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a saved search
    
    Can update name, filters, notification preferences, or active status
    """
    
    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )

    from app.services.launch_entitlements import reject_monthly_alerts

    if update_data.notification_prefs is not None:
        reject_monthly_alerts(db, current_user, update_data.notification_prefs)
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(saved_search, field, value)
    
    db.commit()
    db.refresh(saved_search)
    
    return saved_search


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    search_id: int,
    hard_delete: bool = Query(False, description="Permanently delete (cannot be undone)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a saved search
    
    **Query Parameters:**
    - hard_delete: If true, permanently deletes. Otherwise soft-deletes (sets is_active=false)
    """
    
    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    if hard_delete:
        db.delete(saved_search)
    else:
        saved_search.is_active = False
    
    db.commit()
    
    return None


@router.post("/{search_id}/test", response_model=dict)
def test_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Test a saved search to see how many opportunities currently match
    
    Returns count without sending notifications
    """
    
    saved_search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    # Import here to avoid circular dependency
    from app.services.saved_search_alerts import find_matching_opportunities
    
    matches = find_matching_opportunities(saved_search, db, test_mode=True)
    
    return {
        "search_id": search_id,
        "search_name": saved_search.name,
        "current_matches": len(matches),
        "opportunities": [
            {
                "id": opp.id,
                "title": opp.title,
                "feasibility_score": opp.feasibility_score,
                "validation_count": opp.validation_count
            }
            for opp in matches[:10]  # Return first 10 as preview
        ]
    }
