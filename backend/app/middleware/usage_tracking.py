"""
Async usage tracking middleware for the OppGrid Public API v1.

Logs every request to the api_usage table using a dedicated DB session.
Attached to the v1_app sub-application; does not run on the main app.

Also injects all spec v2.1 response headers:
  - Rate limiting: X-RateLimit-Remaining, X-RateLimit-Limit,
                   X-Daily-Limit, X-Daily-Remaining
  - Monthly allowance: X-Monthly-Included, X-Monthly-Used,
                       X-Monthly-Remaining, X-Monthly-Overage,
                       X-Monthly-Overage-Cost, X-Overage-Rate
  - Billing period: X-Billing-Month, X-Billing-Resets
  - Timing: X-Response-Time-Ms
"""
import time
import logging
from datetime import date, timedelta
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.database import SessionLocal
from app.services import api_key_service
from app.models.tier_config import TierConfig

logger = logging.getLogger(__name__)


def _next_billing_reset(billing_month: date) -> date:
    """Return the first day of the month after *billing_month*."""
    if billing_month.month == 12:
        return date(billing_month.year + 1, 1, 1)
    return date(billing_month.year, billing_month.month + 1, 1)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Asynchronous middleware that records every /v1/ request to api_usage
    and injects spec-compliant response headers.

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

        # ---- Timing ---------------------------------------------------------
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        # ---- Rate-limit window headers set by auth dependency ---------------
        api_key = getattr(request.state, "api_key", None)

        if api_key is not None:
            rpm = api_key.rate_limit_rpm
            daily = api_key.daily_limit

            rpm_remaining = getattr(request.state, "rpm_remaining", rpm)
            daily_remaining = getattr(request.state, "daily_remaining", daily)

            response.headers["X-RateLimit-Limit"] = str(rpm)
            response.headers["X-RateLimit-Remaining"] = str(rpm_remaining)
            response.headers["X-Daily-Limit"] = str(daily)
            response.headers["X-Daily-Remaining"] = str(daily_remaining)

            # Backward-compat alias
            response.headers["X-RateLimit-Remaining-Daily"] = str(daily_remaining)

            # ---- Monthly allowance headers ----------------------------------
            tier = api_key.tier
            cap = TierConfig.get_monthly_cap(tier)
            overage_rate = TierConfig.get_overage_rate(tier)

            # Use pre-computed monthly_usage if the endpoint stored it
            monthly = getattr(request.state, "monthly_usage", None)

            if monthly is not None:
                included_used = monthly.get("included_used", 0)
                included_remaining = monthly.get("included_remaining", 0)
                overage_count = monthly.get("overage_count", 0)
                overage_cost = monthly.get("overage_cost", 0.0)
                billing_month_str = monthly.get("billing_month", "")
            else:
                included_used = 0
                included_remaining = cap
                overage_count = 0
                overage_cost = 0.0
                today = date.today()
                billing_month_str = date(today.year, today.month, 1).isoformat()

            # Parse billing month for reset calculation
            try:
                bm = date.fromisoformat(billing_month_str)
            except (ValueError, TypeError):
                today = date.today()
                bm = date(today.year, today.month, 1)

            resets_str = _next_billing_reset(bm).isoformat()

            response.headers["X-Monthly-Included"] = str(cap)
            response.headers["X-Monthly-Used"] = str(included_used)
            response.headers["X-Monthly-Remaining"] = str(included_remaining)
            response.headers["X-Monthly-Overage"] = str(overage_count)
            response.headers["X-Monthly-Overage-Cost"] = f"{overage_cost:.2f}"
            response.headers["X-Overage-Rate"] = f"{overage_rate:.2f}"
            response.headers["X-Billing-Month"] = billing_month_str
            response.headers["X-Billing-Resets"] = resets_str
        else:
            # Unauthenticated — still propagate rate-limit info if stashed
            if hasattr(request.state, "rpm_remaining"):
                response.headers["X-RateLimit-Remaining"] = str(
                    request.state.rpm_remaining
                )
            if hasattr(request.state, "daily_remaining"):
                response.headers["X-RateLimit-Remaining-Daily"] = str(
                    request.state.daily_remaining
                )

        # ---- Async usage write using a dedicated session --------------------
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
