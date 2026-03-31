"""
Purchased Report Model
Tracks user's report purchases (individual and bundle)
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class PurchaseType(str, enum.Enum):
    INDIVIDUAL = "individual"
    BUNDLE = "bundle"


class PurchasedReport(Base):
    __tablename__ = "purchased_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    
    report_type = Column(String(100), nullable=False)
    purchase_type = Column(String(50), default="individual", nullable=False)
    bundle_id = Column(String(100), nullable=True)
    
    amount_paid = Column(Integer, default=0)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    is_generated = Column(Boolean, default=False)
    generated_report_id = Column(Integer, ForeignKey("generated_reports.id", ondelete="SET NULL"), nullable=True)
    
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")
    opportunity = relationship("Opportunity")


class PurchasedBundle(Base):
    __tablename__ = "purchased_bundles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    
    bundle_type = Column(String(100), nullable=False)
    amount_paid = Column(Integer, default=0)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")
    opportunity = relationship("Opportunity")


class ConsultantLicense(Base):
    __tablename__ = "consultant_licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    amount_paid = Column(Integer, default=0)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    opportunities_used = Column(Integer, default=0)
    max_opportunities = Column(Integer, default=25)
    
    is_active = Column(Boolean, default=True)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")


class PurchasedTemplate(Base):
    """Track template report purchases by users"""
    __tablename__ = "purchased_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    template_slug = Column(String(100), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True)
    
    amount_paid = Column(Integer, default=0)  # Amount in cents after discount
    original_price = Column(Integer, default=0)  # Original price before discount
    discount_percent = Column(Integer, default=0)  # Discount applied
    stripe_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    uses_remaining = Column(Integer, default=-1)  # -1 = unlimited, >0 = limited uses
    
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")


class GuestReportPurchase(Base):
    """Track report purchases by guest users (no account required)"""
    __tablename__ = "guest_report_purchases"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    
    report_type = Column(String(100), nullable=False)
    bundle_type = Column(String(100), nullable=True)
    
    amount_paid = Column(Integer, default=0)
    stripe_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    is_generated = Column(Boolean, default=False)
    generated_report_id = Column(Integer, ForeignKey("generated_reports.id", ondelete="SET NULL"), nullable=True)
    
    access_token = Column(String(255), nullable=True, unique=True)
    
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    opportunity = relationship("Opportunity")
