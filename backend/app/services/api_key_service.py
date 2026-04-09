"""
Public API Key Service — OppGrid v1 API

Manages user-owned API keys for the OppGrid Public API v1.

Key design decisions:
- SHA-256 hashing only (no HMAC secret dependency; the random token is the secret)
- Format: og_live_<token> (production) | og_test_<token> (sandbox)
- In-memory RPM tracking (TODO: swap for Redis in multi-process production)
- Daily usage checked against api_usage table (accurate across restarts)
"""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.api_key import APIKey
from app.models.api_usage import APIUsage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER_LIMITS: Dict[str, Dict[str, int]] = {
    "starter":      {"rpm": 10,    "daily": 1_000},
    "professional": {"rpm": 100,   "daily": 10_000},
    "enterprise":   {"rpm": 1_000, "daily": 100_000},
}

DEFAULT_SCOPES: List[str] = [
    "read:opportunities",
    "read:trends",
    "read:markets",
]

# In-memory sliding-window RPM store.
# TODO: Replace with Redis for multi-process / multi-instance deployments.
_rpm_cache: Dict[str, List[datetime]] = {}


# ---------------------------------------------------------------------------
# Key generation & hashing
# ---------------------------------------------------------------------------

def generate_api_key(environment: str = "production") -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (plaintext_key, sha256_hash, 8-char display prefix)

    The plaintext is returned exactly once and never stored.
    Format: ``og_live_<43-char url-safe token>`` (production)
             ``og_test_<43-char url-safe token>`` (sandbox)
    """
    env_tag = "live" if environment == "production" else "test"
    token = secrets.token_urlsafe(32)
    plaintext = f"og_{env_tag}_{token}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    prefix = plaintext[:8]
    return plaintext, key_hash, prefix


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of a plaintext API key."""
    return hashlib.sha256(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_api_key(
    user_id: int,
    name: str,
    environment: str = "production",
    tier: str = "starter",
    scopes: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
    db: Session = None,
) -> Tuple[str, "APIKey"]:
    """
    Create and persist a new APIKey for *user_id*.

    Returns:
        (plaintext_key, APIKey ORM object)
        — the plaintext_key is shown exactly once; store it securely.
    """
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
    plaintext, key_hash, prefix = generate_api_key(environment)

    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    api_key = APIKey(
        user_id=user_id,
        key_prefix=prefix,
        key_hash=key_hash,
        name=name,
        environment=environment,
        tier=tier,
        scopes=scopes or DEFAULT_SCOPES,
        rate_limit_rpm=limits["rpm"],
        daily_limit=limits["daily"],
        expires_at=expires_at,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info("API key created for user %s: prefix=%s tier=%s", user_id, prefix, tier)
    return plaintext, api_key


def get_api_key_by_hash(key_hash: str, db: Session) -> Optional["APIKey"]:
    """Look up an APIKey record by its SHA-256 hash."""
    return db.query(APIKey).filter(APIKey.key_hash == key_hash).first()


def validate_api_key(
    plaintext: str, db: Session
) -> Tuple[bool, Optional["APIKey"], str]:
    """
    Validate a plaintext API key supplied by an external caller.

    Returns:
        (is_valid, api_key_or_None, error_message)
    """
    if not plaintext:
        return False, None, "API key is required"
    if not (plaintext.startswith("og_live_") or plaintext.startswith("og_test_")):
        return False, None, "Invalid API key format"

    key_hash = hash_api_key(plaintext)
    api_key = get_api_key_by_hash(key_hash, db)

    if not api_key:
        return False, None, "Invalid API key"
    if not api_key.is_active:
        return False, None, "API key has been revoked"
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return False, None, "API key has expired"

    # Best-effort last_used_at update — don't fail the request if this errors.
    try:
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    return True, api_key, ""


def list_user_api_keys(user_id: int, db: Session) -> List["APIKey"]:
    """Return all APIKey records owned by *user_id*, newest first."""
    return (
        db.query(APIKey)
        .filter(APIKey.user_id == user_id)
        .order_by(APIKey.created_at.desc())
        .all()
    )


def revoke_api_key(key_id, user_id: int, db: Session) -> Tuple[bool, str]:
    """
    Revoke an API key.  Only the owning user may revoke their own key.

    *key_id* may be a UUID object or a UUID string.
    """
    from uuid import UUID

    if isinstance(key_id, str):
        try:
            key_id = UUID(key_id)
        except ValueError:
            return False, "Invalid key ID format"

    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.user_id == user_id)
        .first()
    )

    if not api_key:
        return False, "API key not found"
    if not api_key.is_active:
        return False, "API key is already revoked"

    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("API key %s revoked by user %s", key_id, user_id)
    return True, "API key revoked successfully"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def check_rate_limit(key_id: str, rpm_limit: int) -> Tuple[bool, int]:
    """
    Sliding-window in-memory RPM rate limit check.

    Returns:
        (is_allowed, requests_remaining_in_current_window)

    TODO: Replace ``_rpm_cache`` with Redis for multi-process deployments.
    """
    cache_key = str(key_id)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=1)

    _rpm_cache.setdefault(cache_key, [])
    _rpm_cache[cache_key] = [ts for ts in _rpm_cache[cache_key] if ts > window_start]

    current = len(_rpm_cache[cache_key])
    if current >= rpm_limit:
        return False, 0

    _rpm_cache[cache_key].append(now)
    return True, rpm_limit - current - 1


def check_daily_limit(
    key_id, daily_limit: int, db: Session
) -> Tuple[bool, int]:
    """
    Count today's requests against *daily_limit* using the api_usage table.

    Returns:
        (is_allowed, requests_remaining_today)
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    count = (
        db.query(func.count(APIUsage.id))
        .filter(
            APIUsage.api_key_id == key_id,
            APIUsage.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    remaining = daily_limit - count
    if remaining <= 0:
        return False, 0
    return True, remaining


# ---------------------------------------------------------------------------
# Usage recording
# ---------------------------------------------------------------------------

def record_usage(
    api_key_id,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: Session = None,
) -> None:
    """
    Persist a single API request record to api_usage.

    Failures are logged and swallowed — usage recording must never
    break the primary response path.
    """
    try:
        usage = APIUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(usage)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to record API usage: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
