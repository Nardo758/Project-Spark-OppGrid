"""
Public API authentication dependency for the OppGrid v1 API.

Usage:
    from app.middleware.api_auth import get_authenticated_key, require_scope

    @router.get("/foo")
    def foo(api_key: APIKey = Depends(require_scope("read:opportunities"))):
        ...
"""
import logging
from typing import Optional

from fastapi import Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.api_key import APIKey
from app.services import api_key_service

logger = logging.getLogger(__name__)


class APIAuthError(Exception):
    """Raised inside auth dependencies; caught by the v1_app exception handler."""

    def __init__(self, status_code: int, error: str, detail: str, extra_headers: dict = None):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        self.extra_headers = extra_headers or {}


async def get_authenticated_key(
    request: Request,
    x_api_key: Optional[str] = Header(
        None,
        alias="X-API-Key",
        description="Your OppGrid API key (og_live_… or og_test_…)",
    ),
    db: Session = Depends(get_db),
) -> APIKey:
    """
    Validate the ``X-API-Key`` header and enforce RPM + daily rate limits.

    Stashes ``request.state.api_key`` *before* raising any 429 so that the
    UsageTrackingMiddleware can inject the full v2.1 header set on error
    responses too.

    On failure, raises APIAuthError which is converted to a canonical
    {"error": "...", "detail": "..."} JSON response by the v1_app exception handler.
    """
    if not x_api_key:
        raise APIAuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="missing_api_key",
            detail="X-API-Key header is required",
            extra_headers={"WWW-Authenticate": "ApiKey"},
        )

    is_valid, api_key, error = api_key_service.validate_api_key(x_api_key, db)

    if not is_valid:
        raise APIAuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="missing_api_key",
            detail=error,
            extra_headers={"WWW-Authenticate": "ApiKey"},
        )

    # --- RPM sliding-window check -------------------------------------------
    rpm_ok, rpm_remaining = api_key_service.check_rate_limit(
        str(api_key.id), api_key.rate_limit_rpm
    )

    # --- Daily quota check --------------------------------------------------
    daily_ok, daily_remaining = api_key_service.check_daily_limit(
        api_key.id, api_key.daily_limit, db
    )

    # Stash api_key for middleware BEFORE any 429 raise so the response
    # middleware can inject the full v2.1 header set even on error responses.
    request.state.api_key = api_key
    request.state.rpm_remaining = max(0, rpm_remaining) if rpm_ok else 0
    request.state.daily_remaining = max(0, daily_remaining) if daily_ok else 0

    if not rpm_ok:
        raise APIAuthError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="rate_limit_exceeded",
            detail="Rate limit exceeded. Slow down and retry in 60 seconds.",
            extra_headers={
                "X-RateLimit-Limit": str(api_key.rate_limit_rpm),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "60",
            },
        )

    if not daily_ok:
        raise APIAuthError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="daily_limit_exceeded",
            detail="Daily request limit exceeded. Quota resets at midnight UTC.",
            extra_headers={
                # v2.1 header names (spec-compliant)
                "X-Daily-Limit": str(api_key.daily_limit),
                "X-Daily-Remaining": "0",
                # Backward-compat alias
                "X-RateLimit-Remaining-Daily": "0",
                "Retry-After": "86400",
            },
        )

    return api_key


def require_scope(scope: str):
    """
    Dependency factory that validates the API key **and** checks for *scope*.

    Example::

        @router.get("/opportunities")
        def list_opps(api_key: APIKey = Depends(require_scope("read:opportunities"))):
            ...
    """

    async def _check_scope(
        api_key: APIKey = Depends(get_authenticated_key),
    ) -> APIKey:
        granted = api_key.scopes or []
        if scope not in granted and "*" not in granted:
            raise APIAuthError(
                status_code=status.HTTP_403_FORBIDDEN,
                error="insufficient_scope",
                detail=f"API key does not have the required scope: {scope}",
            )
        return api_key

    return _check_scope
