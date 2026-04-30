"""
Agent API Authentication — API key validation for agent endpoints.

Validates X-Agent-Key header and returns the associated API key.
Handles rate limiting tracking via get_agent_api_key_with_rate_limit.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.api_key import APIKey

logger = logging.getLogger(__name__)


def hash_api_key(plaintext_key: str) -> str:
    """Hash an API key using SHA-256"""
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


async def get_agent_api_key(
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validate and retrieve API key from X-Agent-Key header.
    
    Raises:
        HTTPException 401: Missing or invalid API key
    """
    if not x_agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-Agent-Key header.",
        )

    key_hash = hash_api_key(x_agent_key)
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Update last_used_at
    try:
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for API key: {e}")
        db.rollback()

    return api_key


async def get_agent_api_key_with_rate_limit(
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validate API key and check rate limit.
    
    Returns the API key if valid and within rate limit.
    Raises HTTPException 429 if rate limit exceeded.
    """
    api_key = await get_agent_api_key(x_agent_key, db)

    # Check rate limit (1000 qpm = ~16.67 qps)
    # For now, we'll use a simple in-memory counter per key
    # In production, use Redis for distributed rate limiting
    from app.services.rate_limiter import check_rate_limit

    if not check_rate_limit(str(api_key.id), 1000):  # 1000 qpm limit
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: 1000 requests per minute",
            headers={"X-RateLimit-Remaining": "0"},
        )

    return api_key
