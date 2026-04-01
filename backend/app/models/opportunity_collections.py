from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from app.db.database import Base
from app.models.watchlist import OpportunityNote

opportunity_in_collection = Table(
    'opportunity_in_collection',
    Base.metadata,
    Column('opportunity_id', Integer, ForeignKey('opportunities.id'), primary_key=True),
    Column('collection_id', Integer, ForeignKey('opportunity_collections.id'), primary_key=True),
    Column('position', Integer, default=0),
    Column('added_at', DateTime, default=datetime.utcnow),
)

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

    user = relationship('User', backref=backref('opportunity_collections', lazy='dynamic'))
    opportunities = relationship('Opportunity', secondary=opportunity_in_collection, backref=backref('collections', lazy='dynamic'))

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

    user = relationship('User', backref=backref('opportunity_tags', lazy='dynamic'))
    opportunities = relationship('Opportunity', secondary=opportunity_has_tag, backref=backref('tags', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
        }


class UserSavedOpportunity(Base):
    __tablename__ = 'user_saved_opportunities'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    priority = Column(Integer, default=3)
    saved_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', backref=backref('saved_opportunities', lazy='dynamic'))
    opportunity = relationship('Opportunity', backref=backref('saved_by_users', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'opportunity_id': self.opportunity_id,
            'priority': self.priority,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None,
        }
