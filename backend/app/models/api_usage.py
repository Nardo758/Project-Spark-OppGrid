import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class APIUsage(Base):
    """
    Per-request metering log for the public API.

    Every request that passes API key authentication is recorded here.
    Used for rate-limit enforcement, billing, and analytics.
    The api_key_id is set NULL (not deleted) when a key is removed so
    historical usage data is preserved.
    """

    __tablename__ = "api_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)

    response_time_ms = Column(Integer, nullable=True)
    tokens_consumed = Column(Integer, nullable=False, default=1)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    api_key = relationship("APIKey", back_populates="usage")
