"""
Pydantic schemas for user-owned API key management (internal /api/v1/api-keys routes).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable label for this key")
    environment: str = Field("production", pattern="^(production|sandbox)$", description="production or sandbox")
    scopes: Optional[List[str]] = Field(None, description="List of permission scopes; defaults to all read scopes")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, description="Days until expiry; None = no expiry")


class ApiKeyResponse(BaseModel):
    id: UUID
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

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str = Field(..., description="Full plaintext API key — shown exactly once, store securely")
    warning: str = "Save this key now. You won't be able to see it again."


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyResponse]
    total: int


class ApiKeyRevokeResponse(BaseModel):
    message: str
    key_id: str
