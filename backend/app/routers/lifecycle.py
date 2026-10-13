from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.watchlist import WatchlistItem, LifecycleState, LIFECYCLE_TRANSITIONS
from app.schemas.watchlist import (
    LifecycleStateEnum,
    LifecycleTransitionRequest,
    LifecycleTransitionResponse,
    LIFECYCLE_STATE_INFO
)
from app.core.dependencies import get_current_user

from app.services.launch_entitlements import workhub_launch_lock

router = APIRouter(
    prefix="/workhub/lifecycle",
    tags=["lifecycle"],
    dependencies=[Depends(workhub_launch_lock)],
)


@router.get("/states")
async def get_lifecycle_states():
    return {
        "states": [
            {
                "state": state.value,
                **info
            }
            for state, info in LIFECYCLE_STATE_INFO.items()
        ],
        "transitions": {
            state.value: [t.value for t in transitions]
            for state, transitions in LIFECYCLE_TRANSITIONS.items()
        }
    }


@router.get("/watchlist/{watchlist_id}")
async def get_watchlist_lifecycle(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == watchlist_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    current_state = item.lifecycle_state or LifecycleState.SAVED
    allowed = LIFECYCLE_TRANSITIONS.get(current_state, [])
    
    return {
        "id": item.id,
        "opportunity_id": item.opportunity_id,
        "current_state": current_state.value,
        "state_info": LIFECYCLE_STATE_INFO.get(LifecycleStateEnum(current_state.value)),
        "state_changed_at": item.state_changed_at,
        "paused_reason": item.paused_reason,
        "archived_reason": item.archived_reason,
        "allowed_transitions": [t.value for t in allowed]
    }


@router.post("/watchlist/{watchlist_id}/transition")
async def transition_lifecycle_state(
    watchlist_id: int,
    request: LifecycleTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == watchlist_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    current_state = item.lifecycle_state or LifecycleState.SAVED
    new_state = LifecycleState(request.new_state.value)
    
    allowed = LIFECYCLE_TRANSITIONS.get(current_state, [])
    if new_state not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_state.value} to {new_state.value}. Allowed: {[t.value for t in allowed]}"
        )
    
    previous_state = current_state
    item.lifecycle_state = new_state
    item.state_changed_at = func.now()
    
    if new_state == LifecycleState.PAUSED and request.reason:
        item.paused_reason = request.reason
    elif new_state == LifecycleState.ARCHIVED and request.reason:
        item.archived_reason = request.reason
    
    if new_state not in [LifecycleState.PAUSED, LifecycleState.ARCHIVED]:
        item.paused_reason = None
        item.archived_reason = None
    
    db.commit()
    db.refresh(item)
    
    new_allowed = LIFECYCLE_TRANSITIONS.get(new_state, [])
    
    return {
        "id": item.id,
        "previous_state": previous_state.value,
        "new_state": new_state.value,
        "state_changed_at": item.state_changed_at,
        "allowed_transitions": [t.value for t in new_allowed]
    }


@router.get("/summary")
async def get_lifecycle_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id
    ).all()
    
    summary = {}
    for state in LifecycleState:
        summary[state.value] = 0
    
    for item in items:
        state = item.lifecycle_state or LifecycleState.SAVED
        summary[state.value] += 1
    
    return {
        "total": len(items),
        "by_state": summary,
        "state_info": {
            state.value: info for state, info in LIFECYCLE_STATE_INFO.items()
        }
    }


@router.get("/by-state/{state}")
async def get_items_by_state(
    state: LifecycleStateEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.lifecycle_state == LifecycleState(state.value)
    ).all()
    
    return {
        "state": state.value,
        "state_info": LIFECYCLE_STATE_INFO.get(state),
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "opportunity_id": item.opportunity_id,
                "state_changed_at": item.state_changed_at,
                "created_at": item.created_at
            }
            for item in items
        ]
    }
