"""
Public API authentication dependency for the OppGrid v1 API.

Usage:
    from app.middleware.api_auth import get_authenticated_key, require_scope

    @router.get("/foo")
    def foo(api_key: APIKey = Depends(require_scope("read:opportunities"))):
        ...
"""
import logging
from fastapi import Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.api_key import APIKey
from app.services import api_key_service

logger = logging.getLogger(__name__)


async def get_authenticated_key(
    request: Request,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
        description="Your OppGrid API key (og_live_… or og_test_…)",
    ),
    db: Session = Depends(get_db),
) -> APIKey:
    """
    Validate the ``X-API-Key`` header and enforce RPM + daily rate limits.

    Raises:
        401 — key missing, malformed, revoked, or expired
        429 — RPM or daily quota exceeded
    """
    is_valid, api_key, error = api_key_service.validate_api_key(x_api_key, db)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # --- RPM sliding-window check -------------------------------------------
    rpm_ok, rpm_remaining = api_key_service.check_rate_limit(
        str(api_key.id), api_key.rate_limit_rpm
    )
    if not rpm_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Slow down and retry in 60 seconds.",
            headers={
                "X-RateLimit-Limit": str(api_key.rate_limit_rpm),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "60",
            },
        )

    # --- Daily quota check --------------------------------------------------
    daily_ok, daily_remaining = api_key_service.check_daily_limit(
        api_key.id, api_key.daily_limit, db
    )
    if not daily_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily request limit exceeded. Quota resets at midnight UTC.",
            headers={
                "X-RateLimit-Limit-Daily": str(api_key.daily_limit),
                "X-RateLimit-Remaining-Daily": "0",
                "Retry-After": "86400",
            },
        )

    # Stash for the response middleware (rate-limit headers & usage logging).
    request.state.api_key = api_key
    request.state.rpm_remaining = rpm_remaining
    request.state.daily_remaining = daily_remaining

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have the required scope: {scope}",
            )
        return api_key

    return _check_scope
