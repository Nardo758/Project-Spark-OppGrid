from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


@dataclass
class _Bucket:
    window_start: float
    count: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Very small in-memory rate limiter (single-process best-effort).

    This is intentionally simple for the current single-runtime deploy shape.
    """

    def __init__(self, app, enabled: bool = True, default_limit_per_minute: int = 300):
        super().__init__(app)
        self.enabled = enabled
        self.default_limit = max(1, int(default_limit_per_minute))
        self._lock = threading.Lock()
        self._buckets: Dict[Tuple[str, str], _Bucket] = {}

        # Tighten limits on high-risk endpoints.
        self._overrides = {
            ("POST", "/api/v1/auth/login"): 20,
            ("POST", "/api/v1/auth/register"): 10,
            ("POST", "/api/v1/2fa/verify"): 30,
            ("POST", "/api/v1/magic-link/request"): 20,
            ("POST", "/api/v1/subscriptions/pay-per-unlock"): 60,
            ("POST", "/api/v1/subscriptions/confirm-pay-per-unlock"): 60,
        }

        # Do not rate-limit provider callbacks/webhooks (providers will retry).
        # Skip /v1 entirely — the public API has its own per-key slowapi limiter
        # (tier-aware, 10/100/1000 rpm), so the global middleware must not cap it.
        self._skip_prefixes = (
            "/health",
            "/docs",
            "/openapi.json",
            "/api/v1/webhook/stripe",
            "/api/v1/webhook/",
            "/api/v1/replit-auth/",
            "/auth/",
            "/v1",
        )

    def _client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _limit_for(self, method: str, path: str) -> int:
        return self._overrides.get((method, path), self.default_limit)

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        if request.scope.get("type") != "http":
            return await call_next(request)

        path = request.url.path
        for prefix in self._skip_prefixes:
            if path.startswith(prefix):
                return await call_next(request)

        method = request.method.upper()
        ip = self._client_ip(request)

        # Fixed 60s window.
        now = time.time()
        key = (ip, path)
        limit = self._limit_for(method, path)

        with self._lock:
            b = self._buckets.get(key)
            if not b or (now - b.window_start) >= 60:
                b = _Bucket(window_start=now, count=0)
                self._buckets[key] = b

            b.count += 1
            remaining = max(0, limit - b.count)
            reset_in = int(max(0, 60 - (now - b.window_start)))

            # Small pruning to avoid unbounded growth.
            if len(self._buckets) > 5000:
                cutoff = now - 120
                for k in list(self._buckets.keys())[:2000]:
                    if self._buckets[k].window_start < cutoff:
                        self._buckets.pop(k, None)

            # Calculate reset timestamp (Unix timestamp in seconds)
            reset_timestamp = int(now + reset_in)
            
            if b.count > limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded",
                            "details": [f"Max {limit} requests per minute"]
                        }
                    },
                    headers={
                        "Retry-After": str(reset_in),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_timestamp),
                    },
                )

        response: Response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(remaining))
        response.headers.setdefault("X-RateLimit-Reset", str(reset_timestamp))
        return response

