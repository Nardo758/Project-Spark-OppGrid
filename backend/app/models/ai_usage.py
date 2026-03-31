"""
AI Usage Model

Tracks per-user AI token consumption for Stripe usage-based billing.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.database import Base


class AIUsageEventType(str, Enum):
    """Types of AI usage events"""
    CHAT = "chat"                      # General chat/conversation
    ANALYSIS = "analysis"              # Opportunity analysis
    REPORT = "report"                  # Report generation
    CODE = "code"                      # Code generation
    SEARCH = "search"                  # Web search/summarization
    CLASSIFICATION = "classification"  # Simple classification
    EMBEDDING = "embedding"            # Vector embeddings


class UserAIUsage(Base):
    """
    Tracks individual AI API calls per user.
    
    Used for:
    - Stripe usage-based billing (tokens → charges)
    - Cost tracking and analytics
    - Rate limiting
    - Model usage insights
    """
    __tablename__ = "user_ai_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Request details
    event_type = Column(String(50), nullable=False)  # AIUsageEventType
    model_provider = Column(String(50), nullable=False)  # claude, openai, deepseek, gemini
    model_name = Column(String(100), nullable=False)  # claude-3-5-sonnet, gpt-4, etc.
    
    # Token counts
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Cost tracking (in USD, platform cost not user charge)
    cost_usd = Column(Float, nullable=False, default=0.0)
    
    # Billing
    markup_multiplier = Column(Float, nullable=False, default=1.5)  # 50% markup default
    billed_amount_usd = Column(Float, nullable=False, default=0.0)  # cost * markup
    stripe_usage_record_id = Column(String(100), nullable=True)  # Stripe usage record ID
    billed_to_stripe = Column(DateTime, nullable=True)  # When synced to Stripe
    
    # Metadata
    request_id = Column(String(100), nullable=True)  # For tracing
    endpoint = Column(String(200), nullable=True)  # Which API endpoint triggered this
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="ai_usage")
    
    __table_args__ = (
        Index('ix_user_ai_usage_user_created', 'user_id', 'created_at'),
        Index('ix_user_ai_usage_billing', 'user_id', 'billed_to_stripe'),
    )
    
    def __repr__(self):
        return f"<UserAIUsage(id={self.id}, user_id={self.user_id}, model={self.model_name}, tokens={self.total_tokens})>"


class UserAIUsageSummary(Base):
    """
    Daily/monthly aggregated AI usage per user.
    Optimizes billing queries and reporting.
    """
    __tablename__ = "user_ai_usage_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Period
    period_type = Column(String(10), nullable=False)  # 'daily' or 'monthly'
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Aggregated stats
    total_requests = Column(Integer, nullable=False, default=0)
    total_input_tokens = Column(Integer, nullable=False, default=0)
    total_output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Cost totals
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    total_billed_usd = Column(Float, nullable=False, default=0.0)
    
    # Model breakdown (JSON)
    model_breakdown = Column(Text, nullable=True)  # {"claude": 5000, "gpt4": 2000, ...}
    event_breakdown = Column(Text, nullable=True)  # {"chat": 3000, "report": 4000, ...}
    
    # Stripe billing
    stripe_invoice_id = Column(String(100), nullable=True)
    invoiced_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('ix_usage_summary_user_period', 'user_id', 'period_type', 'period_start'),
    )
    
    def __repr__(self):
        return f"<UserAIUsageSummary(user_id={self.user_id}, period={self.period_type}, tokens={self.total_tokens})>"


class AIUsageQuota(Base):
    """
    Per-user AI usage quotas and limits.
    Can be set per subscription tier or custom per user.
    """
    __tablename__ = "ai_usage_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Monthly token limits (0 = unlimited for that tier)
    monthly_token_limit = Column(Integer, nullable=False, default=0)
    
    # Current period usage
    current_period_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_tokens = Column(Integer, nullable=False, default=0)
    
    # Overage handling
    allow_overage = Column(Integer, default=1)  # 1 = yes, 0 = hard stop
    overage_rate_per_1k = Column(Float, default=0.01)  # $/1K tokens for overage
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=60)
    tokens_per_minute = Column(Integer, default=100000)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<AIUsageQuota(user_id={self.user_id}, limit={self.monthly_token_limit})>"
