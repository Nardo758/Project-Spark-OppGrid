import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class ReportCategory(str, enum.Enum):
    POPULAR = "popular"
    MARKETING = "marketing"
    PRODUCT = "product"
    BUSINESS = "business"
    RESEARCH = "research"
    LOCATION = "location"


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    
    ai_prompt = Column(Text, nullable=False)
    
    min_tier = Column(String(50), default="pro")
    price_cents = Column(Integer, default=4900)  # Default $49
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
