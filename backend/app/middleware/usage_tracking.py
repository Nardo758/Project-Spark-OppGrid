"""
Async usage tracking middleware for the OppGrid Public API v1.

Logs every request to the api_usage table using a dedicated DB session.
Attached to the v1_app sub-application; does not run on the main app.
"""
import time
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.database import SessionLocal
from app.services import api_key_service

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Asynchronous middleware that records every /v1/ request to api_usage.

    - api_key_id is taken from request.state.api_key (set by get_authenticated_key).
    - For unauthenticated requests, api_key_id is None (still recorded for audit).
    - Uses a fresh SessionLocal for each request so the main request session
      is never blocked waiting for the write.
    - Failures are swallowed — usage recording must never affect the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Attach timing header
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        # Propagate rate-limit window headers set by auth dependency
        if hasattr(request.state, "rpm_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(request.state.rpm_remaining)
        if hasattr(request.state, "daily_remaining"):
            response.headers["X-RateLimit-Remaining-Daily"] = str(request.state.daily_remaining)

        # Async usage write using a dedicated session
        api_key = getattr(request.state, "api_key", None)
        api_key_id = api_key.id if api_key is not None else None

        db = SessionLocal()
        try:
            api_key_service.record_usage(
                api_key_id=api_key_id,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                db=db,
            )
        except Exception as exc:
            logger.warning("UsageTrackingMiddleware: failed to record usage: %s", exc)
        finally:
            db.close()

        return response
