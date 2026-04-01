"""Opportunity Lifecycle States API

Phase 2: Manage 8-state opportunity journey (DISCOVERED → ARCHIVED)
Track progress, transitions, milestones
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.opportunity_lifecycle import (
    OpportunityLifecycle,
    LifecycleStateTransition,
    LifecycleMilestone,
    LifecycleState,
)

router = APIRouter(prefix="/opportunities", tags=["Lifecycle States"])


# ============================================================================
# Schemas
# ============================================================================

class LifecycleStateEnum(str):
    DISCOVERED = "discovered"
    SAVED = "saved"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    LAUNCHED = "launched"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TransitionLifecycleStateRequest(BaseModel):
    to_state: str
    reason: Optional[str] = None


class UpdateProgressRequest(BaseModel):
    progress_percent: int  # 0-100


class AddMilestoneRequest(BaseModel):
    state: str
    title: str
    description: Optional[str] = None
    order: int = 0


class CompleteMilestoneRequest(BaseModel):
    is_completed: bool


# ============================================================================
# Lifecycle State Endpoints
# ============================================================================

@router.get("/{opportunity_id}/lifecycle", response_model=dict)
def get_opportunity_lifecycle(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get lifecycle state for an opportunity"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        # Create default lifecycle if doesn't exist
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        lifecycle = OpportunityLifecycle(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            current_state=LifecycleState.DISCOVERED.value,
        )
        db.add(lifecycle)
        db.commit()
        db.refresh(lifecycle)

    return lifecycle.to_dict()


@router.post("/{opportunity_id}/lifecycle/transition")
def transition_lifecycle_state(
    opportunity_id: int,
    data: TransitionLifecycleStateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Move opportunity to new lifecycle state"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    # Validate transition
    if not lifecycle.can_transition_to(data.to_state):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {lifecycle.current_state} to {data.to_state}",
        )

    # Record transition
    transition = LifecycleStateTransition(
        lifecycle_id=lifecycle.id,
        from_state=lifecycle.current_state,
        to_state=data.to_state,
        reason=data.reason,
    )
    db.add(transition)

    # Update lifecycle state
    old_state = lifecycle.current_state
    lifecycle.current_state = data.to_state

    # Update state timestamp
    timestamp_field = f"{data.to_state}_at"
    if hasattr(lifecycle, timestamp_field):
        setattr(lifecycle, timestamp_field, datetime.utcnow())

    db.commit()
    db.refresh(lifecycle)

    return {
        "status": "success",
        "message": f"Transitioned from {old_state} to {data.to_state}",
        "lifecycle": lifecycle.to_dict(),
    }


@router.get("/{opportunity_id}/lifecycle/transitions", response_model=List[dict])
def get_lifecycle_transitions(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get state transition history"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    transitions = db.query(LifecycleStateTransition).filter(
        LifecycleStateTransition.lifecycle_id == lifecycle.id,
    ).order_by(LifecycleStateTransition.transitioned_at.desc()).all()

    return [t.to_dict() for t in transitions]


@router.patch("/{opportunity_id}/lifecycle/progress", response_model=dict)
def update_lifecycle_progress(
    opportunity_id: int,
    data: UpdateProgressRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update progress percentage for current state (0-100%)"""
    if not (0 <= data.progress_percent <= 100):
        raise HTTPException(status_code=400, detail="Progress must be between 0-100")

    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    lifecycle.progress_percent = data.progress_percent
    db.commit()
    db.refresh(lifecycle)

    return {
        "status": "success",
        "progress_percent": lifecycle.progress_percent,
        "lifecycle": lifecycle.to_dict(),
    }


@router.patch("/{opportunity_id}/lifecycle/notes")
def update_lifecycle_notes(
    opportunity_id: int,
    request_data: dict,  # {"notes": "..."}
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user notes for lifecycle journey"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    lifecycle.notes = request_data.get('notes', '')
    db.commit()
    db.refresh(lifecycle)

    return {"status": "success", "notes": lifecycle.notes}


# ============================================================================
# Milestones Endpoints
# ============================================================================

@router.get("/{opportunity_id}/lifecycle/milestones", response_model=List[dict])
def get_lifecycle_milestones(
    opportunity_id: int,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get milestones for lifecycle (optionally filter by state)"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    query = db.query(LifecycleMilestone).filter(
        LifecycleMilestone.lifecycle_id == lifecycle.id,
    )

    if state:
        query = query.filter(LifecycleMilestone.state == state)

    milestones = query.order_by(LifecycleMilestone.order).all()
    return [m.to_dict() for m in milestones]


@router.post("/{opportunity_id}/lifecycle/milestones", response_model=dict)
def create_milestone(
    opportunity_id: int,
    data: AddMilestoneRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a milestone for a lifecycle state"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    milestone = LifecycleMilestone(
        lifecycle_id=lifecycle.id,
        state=data.state,
        title=data.title,
        description=data.description,
        order=data.order,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return milestone.to_dict()


@router.patch("/{opportunity_id}/lifecycle/milestones/{milestone_id}", response_model=dict)
def update_milestone(
    opportunity_id: int,
    milestone_id: int,
    data: CompleteMilestoneRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark milestone as completed or reopen"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    milestone = db.query(LifecycleMilestone).filter(
        LifecycleMilestone.id == milestone_id,
        LifecycleMilestone.lifecycle_id == lifecycle.id,
    ).first()

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.is_completed = data.is_completed
    if data.is_completed:
        milestone.completed_at = datetime.utcnow()
    else:
        milestone.completed_at = None

    db.commit()
    db.refresh(milestone)

    return milestone.to_dict()


@router.delete("/{opportunity_id}/lifecycle/milestones/{milestone_id}")
def delete_milestone(
    opportunity_id: int,
    milestone_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a milestone"""
    lifecycle = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.opportunity_id == opportunity_id,
        OpportunityLifecycle.user_id == current_user.id,
    ).first()

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")

    milestone = db.query(LifecycleMilestone).filter(
        LifecycleMilestone.id == milestone_id,
        LifecycleMilestone.lifecycle_id == lifecycle.id,
    ).first()

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.delete(milestone)
    db.commit()

    return {"status": "success"}


# ============================================================================
# Dashboard & Analytics
# ============================================================================

@router.get("/user/lifecycle-summary", response_model=dict)
def get_user_lifecycle_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get summary of user's opportunities across all states"""
    lifecycles = db.query(OpportunityLifecycle).filter(
        OpportunityLifecycle.user_id == current_user.id,
    ).all()

    # Count by state
    by_state = {}
    for state in LifecycleState:
        count = len([l for l in lifecycles if l.current_state == state.value])
        by_state[state.value] = count

    # Recent transitions
    recent_transitions = db.query(LifecycleStateTransition).join(
        OpportunityLifecycle,
        LifecycleStateTransition.lifecycle_id == OpportunityLifecycle.id,
    ).filter(
        OpportunityLifecycle.user_id == current_user.id,
    ).order_by(LifecycleStateTransition.transitioned_at.desc()).limit(10).all()

    return {
        "total_opportunities": len(lifecycles),
        "by_state": by_state,
        "recent_transitions": [t.to_dict() for t in recent_transitions],
        "avg_progress": sum([l.progress_percent for l in lifecycles]) / len(lifecycles) if lifecycles else 0,
    }
