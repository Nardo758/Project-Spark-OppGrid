"""
Collections, Tags, and Notes API Router
Enhances the existing watchlist with organization features.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.database import get_db
from app.models.user import User
from app.models.watchlist import UserCollection, UserTag, OpportunityNote, WatchlistItem
from app.core.dependencies import get_current_user

from app.services.launch_entitlements import workhub_launch_lock

router = APIRouter(
    prefix="/workhub",
    tags=["Workhub"],
    dependencies=[Depends(workhub_launch_lock)],
)


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#6366f1"
    icon: Optional[str] = "folder"


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: str
    icon: str
    sort_order: int
    item_count: int

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#10b981"


class TagResponse(BaseModel):
    id: int
    name: str
    color: str

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    content: str
    is_pinned: Optional[int] = 0


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    is_pinned: Optional[int] = None


class NoteResponse(BaseModel):
    id: int
    opportunity_id: int
    content: str
    is_pinned: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all collections for the current user."""
    collections = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id
    ).order_by(UserCollection.sort_order, UserCollection.name).all()
    
    result = []
    for c in collections:
        item_count = db.query(WatchlistItem).filter(
            WatchlistItem.collection_id == c.id
        ).count()
        result.append(CollectionResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            color=c.color or "#6366f1",
            icon=c.icon or "folder",
            sort_order=c.sort_order or 0,
            item_count=item_count
        ))
    return result


@router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    data: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new collection."""
    existing = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.name == data.name.strip()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Collection with this name already exists")
    
    collection = UserCollection(
        user_id=current_user.id,
        name=data.name.strip(),
        description=data.description,
        color=data.color,
        icon=data.icon
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        color=collection.color or "#6366f1",
        icon=collection.icon or "folder",
        sort_order=collection.sort_order or 0,
        item_count=0
    )


@router.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a collection."""
    collection = db.query(UserCollection).filter(
        UserCollection.id == collection_id,
        UserCollection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    if data.name:
        existing = db.query(UserCollection).filter(
            UserCollection.user_id == current_user.id,
            UserCollection.name == data.name.strip(),
            UserCollection.id != collection_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Collection with this name already exists")
        collection.name = data.name.strip()
    
    if data.description is not None:
        collection.description = data.description
    if data.color:
        collection.color = data.color
    if data.icon:
        collection.icon = data.icon
    if data.sort_order is not None:
        collection.sort_order = data.sort_order
    
    db.commit()
    db.refresh(collection)
    
    item_count = db.query(WatchlistItem).filter(
        WatchlistItem.collection_id == collection.id
    ).count()
    
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        color=collection.color or "#6366f1",
        icon=collection.icon or "folder",
        sort_order=collection.sort_order or 0,
        item_count=item_count
    )


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a collection. Items are moved to uncategorized."""
    collection = db.query(UserCollection).filter(
        UserCollection.id == collection_id,
        UserCollection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db.query(WatchlistItem).filter(
        WatchlistItem.collection_id == collection_id
    ).update({"collection_id": None})
    
    db.delete(collection)
    db.commit()
    
    return {"success": True}


@router.post("/watchlist/{item_id}/collection/{collection_id}")
async def assign_to_collection(
    item_id: int,
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a watchlist item to a collection."""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    if collection_id > 0:
        collection = db.query(UserCollection).filter(
            UserCollection.id == collection_id,
            UserCollection.user_id == current_user.id
        ).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        item.collection_id = collection_id
    else:
        item.collection_id = None
    
    db.commit()
    return {"success": True, "collection_id": item.collection_id}


@router.get("/tags", response_model=List[TagResponse])
async def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tags for the current user."""
    tags = db.query(UserTag).filter(
        UserTag.user_id == current_user.id
    ).order_by(UserTag.name).all()
    return tags


@router.post("/tags", response_model=TagResponse)
async def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag."""
    existing = db.query(UserTag).filter(
        UserTag.user_id == current_user.id,
        UserTag.name == data.name.strip()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    tag = UserTag(
        user_id=current_user.id,
        name=data.name.strip(),
        color=data.color
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tag."""
    tag = db.query(UserTag).filter(
        UserTag.id == tag_id,
        UserTag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    db.delete(tag)
    db.commit()
    return {"success": True}


@router.post("/watchlist/{item_id}/tags/{tag_id}")
async def add_tag_to_item(
    item_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a tag to a watchlist item."""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    tag = db.query(UserTag).filter(
        UserTag.id == tag_id,
        UserTag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag not in item.tags:
        item.tags.append(tag)
        db.commit()
    
    return {"success": True}


@router.delete("/watchlist/{item_id}/tags/{tag_id}")
async def remove_tag_from_item(
    item_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a tag from a watchlist item."""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    tag = db.query(UserTag).filter(
        UserTag.id == tag_id,
        UserTag.user_id == current_user.id
    ).first()
    
    if tag and tag in item.tags:
        item.tags.remove(tag)
        db.commit()
    
    return {"success": True}


@router.get("/opportunities/{opportunity_id}/note", response_model=Optional[NoteResponse])
async def get_opportunity_note(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's note for an opportunity."""
    note = db.query(OpportunityNote).filter(
        OpportunityNote.user_id == current_user.id,
        OpportunityNote.opportunity_id == opportunity_id
    ).first()
    
    if not note:
        return None
    
    return NoteResponse(
        id=note.id,
        opportunity_id=note.opportunity_id,
        content=note.content,
        is_pinned=note.is_pinned or 0,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else ""
    )


@router.post("/opportunities/{opportunity_id}/note", response_model=NoteResponse)
async def create_or_update_note(
    opportunity_id: int,
    data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update user's note for an opportunity."""
    note = db.query(OpportunityNote).filter(
        OpportunityNote.user_id == current_user.id,
        OpportunityNote.opportunity_id == opportunity_id
    ).first()
    
    if note:
        note.content = data.content
        if data.is_pinned is not None:
            note.is_pinned = data.is_pinned
    else:
        note = OpportunityNote(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            content=data.content,
            is_pinned=data.is_pinned or 0
        )
        db.add(note)
    
    db.commit()
    db.refresh(note)
    
    return NoteResponse(
        id=note.id,
        opportunity_id=note.opportunity_id,
        content=note.content,
        is_pinned=note.is_pinned or 0,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else ""
    )


@router.delete("/opportunities/{opportunity_id}/note")
async def delete_note(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user's note for an opportunity."""
    note = db.query(OpportunityNote).filter(
        OpportunityNote.user_id == current_user.id,
        OpportunityNote.opportunity_id == opportunity_id
    ).first()
    
    if note:
        db.delete(note)
        db.commit()
    
    return {"success": True}
