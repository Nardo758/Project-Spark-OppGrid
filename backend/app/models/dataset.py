"""Dataset models."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Enum, Index
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.database import Base


class DatasetType(str, enum.Enum):
    """Dataset type enum."""
    OPPORTUNITIES = "opportunities"
    MARKETS = "markets"
    TRENDS = "trends"
    RAW_DATA = "raw_data"


class Dataset(Base):
    """Dataset model for marketplace."""
    __tablename__ = "datasets"
    
    # Core fields
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1024), nullable=True)
    
    # Dataset classification
    dataset_type = Column(Enum(DatasetType), nullable=False, index=True)
    vertical = Column(String(100), nullable=True, index=True)  # coffee, gyms, coworking, etc.
    city = Column(String(100), nullable=True, index=True)      # Austin, NYC, etc.
    
    # Pricing and metadata
    price_cents = Column(Integer, nullable=False)  # 9900 = $99.00
    record_count = Column(Integer, nullable=False)  # Number of rows in dataset
    data_freshness = Column(String(255), nullable=False)  # "as of 2026-04-30"
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Ownership and status
    created_by_user_id = Column(String(36), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Query definition for regeneration
    query_definition = Column(JSON, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_vertical_city', 'vertical', 'city'),
        Index('idx_created_at', 'created_at'),
        Index('idx_dataset_type_active', 'dataset_type', 'is_active'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'dataset_type': self.dataset_type.value,
            'vertical': self.vertical,
            'city': self.city,
            'price_cents': self.price_cents,
            'record_count': self.record_count,
            'data_freshness': self.data_freshness,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_user_id': self.created_by_user_id,
            'is_active': self.is_active,
        }


class DatasetPurchase(Base):
    """Dataset purchase audit trail."""
    __tablename__ = "dataset_purchases"
    
    id = Column(String(36), primary_key=True, index=True)
    dataset_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    # Purchase details
    price_cents = Column(Integer, nullable=False)  # Price paid (may differ from dataset price)
    payment_method = Column(String(50), nullable=False)  # "stripe", "subscription", "free"
    stripe_invoice_id = Column(String(255), nullable=True, index=True)
    
    # Access details
    download_url = Column(String(512), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    status = Column(String(50), nullable=False, default="completed", index=True)  # completed, expired, cancelled
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_dataset', 'user_id', 'dataset_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'dataset_id': self.dataset_id,
            'user_id': self.user_id,
            'price_cents': self.price_cents,
            'payment_method': self.payment_method,
            'stripe_invoice_id': self.stripe_invoice_id,
            'download_url': self.download_url,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'accessed_at': self.accessed_at.isoformat() if self.accessed_at else None,
        }
