import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class APIKey(Base):
    """
    Public API keys for external developer access.

    Keys are stored as SHA-256 hashes only — the plaintext key is returned
    exactly once at creation time and never persisted.  The key_prefix column
    stores the first 8 characters for display / identification purposes.

    Tier controls rate limits and data freshness:
      starter:      10 rpm / 1 000 req/day  / opportunities >30 days old
      professional: 100 rpm / 10 000 req/day / opportunities >7 days old
      enterprise:   1 000 rpm / 100 000 req/day / all opportunities
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)

    name = Column(String(100), nullable=False)
    environment = Column(String(20), nullable=False, default="production")

    tier = Column(String(20), nullable=False, default="starter")
    scopes = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )

    rate_limit_rpm = Column(Integer, nullable=False, default=10)
    daily_limit = Column(Integer, nullable=False, default=1000)

    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    stripe_subscription_item_id = Column(String(100), nullable=True)

    user = relationship("User", back_populates="api_keys")
    usage = relationship(
        "APIUsage",
        back_populates="api_key",
        passive_deletes=True,
    )
