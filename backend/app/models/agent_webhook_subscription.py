"""
Agent Webhook Subscriptions Model

Tracks webhook subscriptions for agent API integrations.
Webhooks are triggered on specific events (opportunity.new, trend.updated, market.changed).
"""
import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class AgentWebhookSubscription(Base):
    """
    Webhook subscription for Agent API.
    
    Stores subscriptions that listen for specific events and deliver payloads to webhook URLs.
    Webhook URLs are encrypted/hashed for security. Failure tracking allows for exponential backoff.
    """
    
    __tablename__ = "agent_webhook_subscriptions"
    
    # Primary Key
    subscription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key to agent_api_keys (future: for now we'll reference user/api_key context)
    # agent_api_key_id is tied to the API key used to create the subscription
    agent_api_key_id = Column(String(255), nullable=False, index=True)
    
    # Webhook URL (stored encrypted for security)
    # In production, use cryptography.fernet to encrypt, or store hashed version
    webhook_url = Column(Text, nullable=False)
    webhook_url_hash = Column(String(64), nullable=True, unique=True)  # SHA-256 hash for deduplication
    
    # Events subscribed to (JSON array of event types)
    # Valid values: "opportunity.new", "trend.updated", "market.changed"
    events = Column(JSONB, nullable=False, default=lambda: ["opportunity.new"])
    
    # Optional filters
    vertical_filter = Column(String(100), nullable=True)  # e.g., "coffee", "retail"
    city_filter = Column(String(100), nullable=True)      # e.g., "Austin"
    
    # Status flags
    active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Webhook delivery tracking
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Failure tracking for exponential backoff
    failure_count = Column(Integer, nullable=False, default=0)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    user_agent = Column(String(255), nullable=True)  # Store the User-Agent header during test
    
    # Indexes
    __table_args__ = (
        Index("ix_agent_webhook_subscriptions_agent_api_key_id", "agent_api_key_id"),
        Index("ix_agent_webhook_subscriptions_active", "active"),
        Index("ix_agent_webhook_subscriptions_created_at", "created_at"),
    )
