"""
Pydantic schemas for user-owned API key management (internal /api/v1/api-keys routes).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
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


class ApiKeyResponse(BaseModel):
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
    def from_model(cls, obj) -> "ApiKeyResponse":
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


class ApiKeyCreatedResponse(BaseModel):
    plaintext_key: str = Field(
        ...,
        description="Your API key — shown ONCE. Copy and store it securely.",
    )
    key: ApiKeyResponse


class ApiKeyUsageStats(BaseModel):
    key_id: str
    requests_today: int
    requests_total: int
    daily_limit: int
    usage_remaining_today: int


class ApiKeyRevokeResponse(BaseModel):
    success: bool
    message: str
