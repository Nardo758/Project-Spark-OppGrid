"""
Lead Model

Represents potential customers/interested users for lead management and nurturing.
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"


class LeadSource(str, enum.Enum):
    ORGANIC = "organic"
    REFERRAL = "referral"
    PAID_ADS = "paid_ads"
    SOCIAL = "social"
    PARTNER = "partner"
    DIRECT = "direct"
    OTHER = "other"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    source = Column(Enum(LeadSource), default=LeadSource.ORGANIC, nullable=False)
    
    interest_category = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    
    email_opt_in = Column(Boolean, default=True, nullable=False)
    email_sequence_step = Column(Integer, default=0, nullable=False)
    last_email_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default="now()")
    updated_at = Column(DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], backref="lead_records")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    opportunity = relationship("Opportunity", backref="leads")
    signals = relationship("OpportunitySignal", back_populates="paired_contact")
