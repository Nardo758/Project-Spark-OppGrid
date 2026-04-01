from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

# Junction table for opportunities in collections
opportunity_in_collection = Table(
    'opportunity_in_collection',
    Base.metadata,
    Column('opportunity_id', Integer, ForeignKey('opportunities.id'), primary_key=True),
    Column('collection_id', Integer, ForeignKey('opportunity_collections.id'), primary_key=True),
    Column('position', Integer, default=0),
    Column('added_at', DateTime, default=datetime.utcnow),
)

# Junction table for tags on opportunities
opportunity_has_tag = Table(
    'opportunity_has_tag',
    Base.metadata,
    Column('opportunity_id', Integer, ForeignKey('opportunities.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('opportunity_tags.id'), primary_key=True),
    Column('added_at', DateTime, default=datetime.utcnow),
)


class OpportunityCollection(Base):
    __tablename__ = 'opportunity_collections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#3b82f6')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='opportunity_collections')
    opportunities = relationship('Opportunity', secondary=opportunity_in_collection, back_populates='collections')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'opportunity_count': len(self.opportunities) if self.opportunities else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OpportunityTag(Base):
    __tablename__ = 'opportunity_tags'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default='#6366f1')
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='opportunity_tags')
    opportunities = relationship('Opportunity', secondary=opportunity_has_tag, back_populates='tags')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
        }


class OpportunityNote(Base):
    __tablename__ = 'opportunity_notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='opportunity_notes')
    opportunity = relationship('Opportunity', back_populates='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSavedOpportunity(Base):
    __tablename__ = 'user_saved_opportunities'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    priority = Column(Integer, default=3)  # 1-5 stars
    saved_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='saved_opportunities')
    opportunity = relationship('Opportunity', back_populates='saved_by_users')

    def to_dict(self):
        return {
            'id': self.id,
            'opportunity_id': self.opportunity_id,
            'priority': self.priority,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None,
        }
