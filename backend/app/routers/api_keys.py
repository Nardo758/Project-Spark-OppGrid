"""
API Key Management — JWT-protected CRUD for user-owned public API keys.

Mounted at /api/v1/api-keys by the main application.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.api_key import APIKey
from app.models.api_usage import APIUsage
from app.services import api_key_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the key")
    environment: str = Field("production", description="'production' or 'sandbox'")
    tier: str = Field("starter", description="'starter', 'professional', or 'enterprise'")
    scopes: Optional[List[str]] = Field(
        None,
        description="OAuth-style scopes. Defaults to all read scopes.",
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until expiry (omit for no expiry)"
    )


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    environment: str
    tier: str
    scopes: List[str]
    rate_limit_rpm: int
    daily_limit: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, obj: APIKey) -> "APIKeyResponse":
        return cls(
            id=str(obj.id),
            name=obj.name,
            key_prefix=obj.key_prefix,
            environment=obj.environment,
            tier=obj.tier,
            scopes=obj.scopes or [],
            rate_limit_rpm=obj.rate_limit_rpm,
            daily_limit=obj.daily_limit,
            is_active=obj.is_active,
            last_used_at=obj.last_used_at,
            expires_at=obj.expires_at,
            created_at=obj.created_at,
        )


class CreateAPIKeyResponse(BaseModel):
    plaintext_key: str = Field(
        ...,
        description="Your API key — shown ONCE. Copy and store it securely.",
    )
    key: APIKeyResponse


class RevokeAPIKeyResponse(BaseModel):
    success: bool
    message: str


class APIKeyUsageStats(BaseModel):
    key_id: str
    requests_today: int
    requests_total: int
    daily_limit: int
    usage_remaining_today: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
def create_api_key(
    data: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new public API key for your account.

    The plaintext key is returned **once** in `plaintext_key`.
    Copy and store it immediately — it cannot be retrieved again.

    Maximum 10 active keys per account.
    """
    if data.environment not in ("production", "sandbox"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="environment must be 'production' or 'sandbox'",
        )
    if data.tier not in api_key_service.TIER_LIMITS:
        valid = ", ".join(api_key_service.TIER_LIMITS.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tier must be one of: {valid}",
        )

    active_count = (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id, APIKey.is_active == True)
        .count()
    )
    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active API keys allowed. Revoke unused keys first.",
        )

    plaintext, api_key = api_key_service.create_api_key(
        user_id=current_user.id,
        name=data.name,
        environment=data.environment,
        tier=data.tier,
        scopes=data.scopes,
        expires_in_days=data.expires_in_days,
        db=db,
    )

    return CreateAPIKeyResponse(
        plaintext_key=plaintext,
        key=APIKeyResponse.from_model(api_key),
    )


@router.get(
    "",
    response_model=List[APIKeyResponse],
    summary="List API keys",
)
def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all API keys owned by the authenticated user (newest first)."""
    keys = api_key_service.list_user_api_keys(current_user.id, db)
    return [APIKeyResponse.from_model(k) for k in keys]


@router.delete(
    "/{key_id}",
    response_model=RevokeAPIKeyResponse,
    summary="Revoke an API key",
)
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Permanently revoke an API key.

    Revoked keys are deactivated immediately. This action is irreversible.
    Historical usage data is preserved for billing / auditing.
    """
    success, message = api_key_service.revoke_api_key(key_id, current_user.id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )
    return RevokeAPIKeyResponse(success=True, message=message)


@router.get(
    "/{key_id}/usage",
    response_model=APIKeyUsageStats,
    summary="Get usage stats for a key",
)
def get_key_usage(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return today's request count and total usage for a specific API key."""
    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format",
        )

    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == key_uuid, APIKey.user_id == current_user.id)
        .first()
    )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    requests_today = (
        db.query(func.count(APIUsage.id))
        .filter(
            APIUsage.api_key_id == key_uuid,
            APIUsage.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    requests_total = (
        db.query(func.count(APIUsage.id))
        .filter(APIUsage.api_key_id == key_uuid)
        .scalar()
        or 0
    )

    return APIKeyUsageStats(
        key_id=str(api_key.id),
        requests_today=requests_today,
        requests_total=requests_total,
        daily_limit=api_key.daily_limit,
        usage_remaining_today=max(0, api_key.daily_limit - requests_today),
    )
