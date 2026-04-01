"""Opportunity Collections, Tags, and Notes API

Phase 1: User organization system (collections, tags, notes, saved opportunities)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.opportunity_collections import (
    OpportunityCollection,
    OpportunityTag,
    OpportunityNote,
    UserSavedOpportunity,
    opportunity_in_collection,
    opportunity_has_tag,
)
from app.models.opportunity import Opportunity

router = APIRouter(prefix="/opportunities", tags=["Collections & Organization"])


# ============================================================================
# Schemas
# ============================================================================

class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class CreateTagRequest(BaseModel):
    name: str
    color: Optional[str] = None


class CreateNoteRequest(BaseModel):
    content: str


class UpdateNoteRequest(BaseModel):
    content: str


class SaveOpportunityRequest(BaseModel):
    priority: int = 3  # 1-5 stars


# ============================================================================
# Collections Endpoints
# ============================================================================

@router.get("/collections", response_model=List[dict])
def get_user_collections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all collections for current user"""
    collections = db.query(OpportunityCollection).filter(
        OpportunityCollection.user_id == current_user.id
    ).all()

    return [c.to_dict() for c in collections]


@router.post("/collections", response_model=dict)
def create_collection(
    data: CreateCollectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new collection"""
    collection = OpportunityCollection(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        color=data.color or '#3b82f6',
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection.to_dict()


@router.put("/collections/{collection_id}", response_model=dict)
def update_collection(
    collection_id: int,
    data: UpdateCollectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a collection"""
    collection = db.query(OpportunityCollection).filter(
        OpportunityCollection.id == collection_id,
        OpportunityCollection.user_id == current_user.id,
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if data.name:
        collection.name = data.name
    if data.description is not None:
        collection.description = data.description
    if data.color:
        collection.color = data.color

    db.commit()
    db.refresh(collection)
    return collection.to_dict()


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a collection (doesn't delete opportunities, just removes from collection)"""
    collection = db.query(OpportunityCollection).filter(
        OpportunityCollection.id == collection_id,
        OpportunityCollection.user_id == current_user.id,
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    db.delete(collection)
    db.commit()
    return {"status": "success"}


@router.post("/{opportunity_id}/collections/{collection_id}")
def add_opportunity_to_collection(
    opportunity_id: int,
    collection_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add opportunity to collection"""
    collection = db.query(OpportunityCollection).filter(
        OpportunityCollection.id == collection_id,
        OpportunityCollection.user_id == current_user.id,
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check if already in collection
    if opportunity not in collection.opportunities:
        collection.opportunities.append(opportunity)
        db.commit()

    return {"status": "success"}


@router.delete("/{opportunity_id}/collections/{collection_id}")
def remove_opportunity_from_collection(
    opportunity_id: int,
    collection_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove opportunity from collection"""
    collection = db.query(OpportunityCollection).filter(
        OpportunityCollection.id == collection_id,
        OpportunityCollection.user_id == current_user.id,
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opportunity in collection.opportunities:
        collection.opportunities.remove(opportunity)
        db.commit()

    return {"status": "success"}


# ============================================================================
# Tags Endpoints
# ============================================================================

@router.get("/tags", response_model=List[dict])
def get_user_tags(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all tags for current user"""
    tags = db.query(OpportunityTag).filter(
        OpportunityTag.user_id == current_user.id
    ).all()

    return [t.to_dict() for t in tags]


@router.get("/tags/suggestions", response_model=List[dict])
def get_tag_suggestions():
    """Get suggested tags (hardcoded list)"""
    suggestions = [
        {'name': 'High Priority', 'color': '#ef4444'},
        {'name': 'In Progress', 'color': '#f59e0b'},
        {'name': 'Completed', 'color': '#10b981'},
        {'name': 'Research', 'color': '#3b82f6'},
        {'name': 'Team Feedback', 'color': '#8b5cf6'},
        {'name': 'Marketplace', 'color': '#ec4899'},
        {'name': 'SaaS', 'color': '#14b8a6'},
        {'name': 'Service', 'color': '#f97316'},
        {'name': 'Real Estate', 'color': '#06b6d4'},
        {'name': 'E-commerce', 'color': '#6366f1'},
    ]
    return suggestions


@router.post("/tags", response_model=dict)
def create_tag(
    data: CreateTagRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new tag"""
    # Check if tag already exists
    existing = db.query(OpportunityTag).filter(
        OpportunityTag.user_id == current_user.id,
        OpportunityTag.name == data.name,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = OpportunityTag(
        user_id=current_user.id,
        name=data.name,
        color=data.color or '#6366f1',
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag.to_dict()


@router.post("/{opportunity_id}/tags/{tag_id}")
def add_tag_to_opportunity(
    opportunity_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add tag to opportunity"""
    tag = db.query(OpportunityTag).filter(
        OpportunityTag.id == tag_id,
        OpportunityTag.user_id == current_user.id,
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opportunity not in tag.opportunities:
        tag.opportunities.append(opportunity)
        db.commit()

    return {"status": "success"}


@router.delete("/{opportunity_id}/tags/{tag_id}")
def remove_tag_from_opportunity(
    opportunity_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove tag from opportunity"""
    tag = db.query(OpportunityTag).filter(
        OpportunityTag.id == tag_id,
        OpportunityTag.user_id == current_user.id,
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opportunity in tag.opportunities:
        tag.opportunities.remove(opportunity)
        db.commit()

    return {"status": "success"}


# ============================================================================
# Notes Endpoints
# ============================================================================

@router.get("/{opportunity_id}/notes", response_model=List[dict])
def get_opportunity_notes(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all notes for an opportunity"""
    notes = db.query(OpportunityNote).filter(
        OpportunityNote.opportunity_id == opportunity_id,
        OpportunityNote.user_id == current_user.id,
    ).all()

    return [n.to_dict() for n in notes]


@router.post("/{opportunity_id}/notes", response_model=dict)
def create_note(
    opportunity_id: int,
    data: CreateNoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a note for an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    note = OpportunityNote(
        user_id=current_user.id,
        opportunity_id=opportunity_id,
        content=data.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note.to_dict()


@router.put("/{opportunity_id}/notes/{note_id}", response_model=dict)
def update_note(
    opportunity_id: int,
    note_id: int,
    data: UpdateNoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a note"""
    note = db.query(OpportunityNote).filter(
        OpportunityNote.id == note_id,
        OpportunityNote.opportunity_id == opportunity_id,
        OpportunityNote.user_id == current_user.id,
    ).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.content = data.content
    db.commit()
    db.refresh(note)
    return note.to_dict()


@router.delete("/{opportunity_id}/notes/{note_id}")
def delete_note(
    opportunity_id: int,
    note_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a note"""
    note = db.query(OpportunityNote).filter(
        OpportunityNote.id == note_id,
        OpportunityNote.opportunity_id == opportunity_id,
        OpportunityNote.user_id == current_user.id,
    ).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return {"status": "success"}


# ============================================================================
# Saved Opportunities & Priority
# ============================================================================

@router.post("/{opportunity_id}/save", response_model=dict)
def save_opportunity(
    opportunity_id: int,
    data: SaveOpportunityRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Save an opportunity with priority (1-5 stars)"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    saved = db.query(UserSavedOpportunity).filter(
        UserSavedOpportunity.user_id == current_user.id,
        UserSavedOpportunity.opportunity_id == opportunity_id,
    ).first()

    if saved:
        saved.priority = data.priority
        db.commit()
    else:
        saved = UserSavedOpportunity(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            priority=data.priority,
        )
        db.add(saved)
        db.commit()

    db.refresh(saved)
    return saved.to_dict()


@router.get("/saved", response_model=List[dict])
def get_saved_opportunities(
    sort_by: str = 'priority',  # priority, date, alpha
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's saved opportunities"""
    query = db.query(UserSavedOpportunity).filter(
        UserSavedOpportunity.user_id == current_user.id
    )

    if sort_by == 'priority':
        query = query.order_by(UserSavedOpportunity.priority.desc())
    elif sort_by == 'date':
        query = query.order_by(UserSavedOpportunity.saved_at.desc())
    elif sort_by == 'alpha':
        # Join with opportunity for sorting by title
        query = query.join(Opportunity).order_by(Opportunity.title.asc())

    saved = query.all()
    return [s.to_dict() for s in saved]


@router.delete("/{opportunity_id}/save")
def unsave_opportunity(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Unsave an opportunity"""
    saved = db.query(UserSavedOpportunity).filter(
        UserSavedOpportunity.user_id == current_user.id,
        UserSavedOpportunity.opportunity_id == opportunity_id,
    ).first()

    if saved:
        db.delete(saved)
        db.commit()

    return {"status": "success"}


@router.get("/{opportunity_id}/saved-status")
def get_saved_status(
    opportunity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if opportunity is saved and get priority"""
    saved = db.query(UserSavedOpportunity).filter(
        UserSavedOpportunity.user_id == current_user.id,
        UserSavedOpportunity.opportunity_id == opportunity_id,
    ).first()

    if saved:
        return {"is_saved": True, "priority": saved.priority}
    else:
        return {"is_saved": False, "priority": None}
