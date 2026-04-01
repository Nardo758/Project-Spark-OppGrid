from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Text, Table, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class LifecycleState(str, enum.Enum):
    DISCOVERED = "discovered"
    SAVED = "saved"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    LAUNCHED = "launched"
    PAUSED = "paused"
    ARCHIVED = "archived"


LIFECYCLE_TRANSITIONS = {
    LifecycleState.DISCOVERED: [LifecycleState.SAVED],
    LifecycleState.SAVED: [LifecycleState.ANALYZING, LifecycleState.ARCHIVED],
    LifecycleState.ANALYZING: [LifecycleState.PLANNING, LifecycleState.PAUSED, LifecycleState.ARCHIVED],
    LifecycleState.PLANNING: [LifecycleState.EXECUTING, LifecycleState.ANALYZING, LifecycleState.PAUSED, LifecycleState.ARCHIVED],
    LifecycleState.EXECUTING: [LifecycleState.LAUNCHED, LifecycleState.PLANNING, LifecycleState.PAUSED, LifecycleState.ARCHIVED],
    LifecycleState.LAUNCHED: [LifecycleState.PAUSED, LifecycleState.ARCHIVED],
    LifecycleState.PAUSED: [LifecycleState.SAVED, LifecycleState.ANALYZING, LifecycleState.PLANNING, LifecycleState.EXECUTING, LifecycleState.LAUNCHED, LifecycleState.ARCHIVED],
    LifecycleState.ARCHIVED: [LifecycleState.SAVED],
}


watchlist_item_tags = Table(
    "watchlist_item_tags",
    Base.metadata,
    Column("watchlist_item_id", Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("user_tags.id", ondelete="CASCADE"), primary_key=True),
)


class UserCollection(Base):
    __tablename__ = "user_collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")
    icon = Column(String(50), default="folder")
    sort_order = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="collections")
    items = relationship("WatchlistItem", back_populates="collection")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_user_collection_name"),
    )


class UserTag(Base):
    __tablename__ = "user_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(50), nullable=False)
    color = Column(String(7), default="#10b981")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="tags")
    watchlist_items = relationship("WatchlistItem", secondary=watchlist_item_tags, back_populates="tags")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_user_tag_name"),
    )


class OpportunityNote(Base):
    __tablename__ = "opportunity_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    is_pinned = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="opportunity_notes")
    opportunity = relationship("Opportunity", back_populates="user_notes")

    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="unique_user_opportunity_note"),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    collection_id = Column(Integer, ForeignKey("user_collections.id", ondelete="SET NULL"), nullable=True, index=True)
    
    lifecycle_state = Column(SAEnum(LifecycleState, values_callable=lambda x: [e.value for e in x]), default=LifecycleState.SAVED, nullable=False, index=True)
    state_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    paused_reason = Column(String(255), nullable=True)
    archived_reason = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="watchlist_items")
    opportunity = relationship("Opportunity")
    collection = relationship("UserCollection", back_populates="items")
    tags = relationship("UserTag", secondary=watchlist_item_tags, back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="unique_user_opportunity_watchlist"),
    )
