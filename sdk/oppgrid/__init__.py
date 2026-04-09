"""
OppGrid Python SDK
Access real-time market intelligence and validated business opportunities.

Usage:
    from oppgrid import OppGrid

    client = OppGrid(api_key="og_live_...")
    result = client.opportunities.list(category="fintech", min_score=80)
    for opp in result["data"]:
        print(f"{opp.title} (Score: {opp.signal_quality_score})")
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

__version__ = "1.0.0"
__all__ = [
    "OppGrid",
    "OppGridError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OppGridError(Exception):
    """Base exception for all OppGrid SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(OppGridError):
    """Raised when the API key is missing, invalid, or expired (HTTP 401)."""

    def __init__(self, message: str = "Invalid or expired API key"):
        super().__init__(message, status_code=401, error_code="authentication_error")


class RateLimitError(OppGridError):
    """Raised when the rate limit is exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, status_code=429, error_code="rate_limit_exceeded")
        self.retry_after = retry_after


class NotFoundError(OppGridError):
    """Raised when the requested resource does not exist (HTTP 404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, error_code="not_found")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Opportunity:
    """Represents a market opportunity returned by the OppGrid API."""

    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    city: Optional[str]
    region: Optional[str]
    ai_opportunity_score: Optional[int]
    ai_market_size_estimate: Optional[str]
    ai_target_audience: Optional[str]
    ai_competition_level: Optional[str]
    growth_rate: Optional[float]
    created_at: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            category=data.get("category"),
            city=data.get("city"),
            region=data.get("region"),
            ai_opportunity_score=data.get("ai_opportunity_score"),
            ai_market_size_estimate=data.get("ai_market_size_estimate"),
            ai_target_audience=data.get("ai_target_audience"),
            ai_competition_level=data.get("ai_competition_level"),
            growth_rate=data.get("growth_rate"),
            created_at=data.get("created_at"),
        )


@dataclass
class Trend:
    """Represents a detected market trend signal."""

    id: int
    trend_name: str
    trend_strength: int
    category: Optional[str]
    opportunities_count: int
    growth_rate: Optional[float]
    detected_at: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trend":
        return cls(
            id=data["id"],
            trend_name=data["trend_name"],
            trend_strength=int(data.get("trend_strength", 0)),
            category=data.get("category"),
            opportunities_count=int(data.get("opportunities_count", 0)),
            growth_rate=data.get("growth_rate"),
            detected_at=data.get("detected_at"),
        )


@dataclass
class Market:
    """Represents a market category segment."""

    category: str
    total_opportunities: int
    avg_score: Optional[float]
    top_regions: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Market":
        return cls(
            category=data.get("category", ""),
            total_opportunities=int(data.get("total_opportunities", 0)),
            avg_score=data.get("avg_score"),
            top_regions=data.get("top_regions", []),
        )


# ---------------------------------------------------------------------------
# Resource classes
# ---------------------------------------------------------------------------


class OpportunitiesResource:
    """CRUD operations for the /v1/opportunities endpoint."""

    def __init__(self, client: "OppGrid") -> None:
        self._client = client

    def list(
        self,
        category: Optional[str] = None,
        city: Optional[str] = None,
        region: Optional[str] = None,
        min_score: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        List opportunities with optional filters, ordered by AI opportunity score.

        Args:
            category:  Filter by category (partial match, e.g. ``"fintech"``).
            city:      Filter by city name (partial match).
            region:    Filter by region / state (partial match).
            min_score: Minimum AI opportunity score (0–100).
            page:      Page number, 1-indexed (default 1).
            limit:     Results per page, max 100 (default 20).

        Returns:
            Dict with keys ``data`` (list of :class:`Opportunity`), ``total``,
            ``page``, ``limit``, and ``has_next``.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if category is not None:
            params["category"] = category
        if city is not None:
            params["city"] = city
        if region is not None:
            params["region"] = region
        if min_score is not None:
            params["min_score"] = min_score

        response = self._client._request("GET", "/opportunities", params=params)
        if isinstance(response.get("data"), list):
            response["data"] = [Opportunity.from_dict(o) for o in response["data"]]
        return response

    def get(self, opportunity_id: int, include_sources: bool = False) -> Opportunity:
        """
        Fetch a single opportunity by its integer ID.

        Args:
            opportunity_id: The integer ID of the opportunity.
            include_sources: Reserved for Professional+ tier (currently no-op).

        Returns:
            An :class:`Opportunity` instance.

        Raises:
            NotFoundError: If the opportunity does not exist or is not accessible
                           with your current API key tier.
        """
        data = self._client._request("GET", f"/opportunities/{opportunity_id}")
        return Opportunity.from_dict(data)


class TrendsResource:
    """Operations for the /v1/trends endpoint."""

    def __init__(self, client: "OppGrid") -> None:
        self._client = client

    def list(
        self,
        category: Optional[str] = None,
        region: Optional[str] = None,
        min_velocity: Optional[float] = None,
        min_strength: Optional[int] = None,
        days: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        List AI-detected market trends, ordered by trend strength.

        Args:
            category:     Filter by category (partial match).
            region:       Filter hint by geographic region (informational).
            min_velocity: Alias for ``min_strength`` (trend velocity threshold).
            min_strength: Minimum trend strength (0–100).
            days:         Look-back period in days (informational; backend uses all detected trends).
            page:         Page number, 1-indexed (default 1).
            limit:        Results per page, max 100 (default 20).

        Returns:
            Dict with keys ``data`` (list of :class:`Trend`), ``total``,
            ``page``, ``limit``, and ``has_next``.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if category is not None:
            params["category"] = category
        # min_strength wins; fall back to min_velocity alias
        effective_strength = min_strength if min_strength is not None else (
            int(min_velocity) if min_velocity is not None else None
        )
        if effective_strength is not None:
            params["min_strength"] = effective_strength

        response = self._client._request("GET", "/trends", params=params)
        if isinstance(response.get("data"), list):
            response["data"] = [Trend.from_dict(t) for t in response["data"]]
        return response


class MarketsResource:
    """Operations for the /v1/markets endpoint."""

    def __init__(self, client: "OppGrid") -> None:
        self._client = client

    def list(self) -> Dict[str, Any]:
        """
        Get aggregated market intelligence grouped by category.

        Returns:
            Dict with keys ``data`` (list of :class:`Market`) and ``total``.
        """
        response = self._client._request("GET", "/markets")
        if isinstance(response.get("data"), list):
            response["data"] = [Market.from_dict(m) for m in response["data"]]
        return response

    def get(self, region: str) -> Dict[str, Any]:
        """
        Get market intelligence for opportunities matching a specific region.

        The ``region`` value is matched as a partial, case-insensitive string
        against opportunity region fields (e.g. ``"north_america"``,
        ``"europe"``, ``"california"``).

        Args:
            region: Region string to filter by (partial match).

        Returns:
            Dict with keys ``data`` (list of :class:`Market`) and ``total``.
        """
        response = self._client._request("GET", f"/markets/{region}")
        if isinstance(response.get("data"), list):
            response["data"] = [Market.from_dict(m) for m in response["data"]]
        return response


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class OppGrid:
    """
    OppGrid API client.

    Example::

        from oppgrid import OppGrid

        client = OppGrid(api_key="og_live_...")

        # List opportunities
        result = client.opportunities.list(category="fintech", min_score=80)
        for opp in result["data"]:
            print(f"{opp.title} (Score: {opp.ai_opportunity_score})")

        # Get a specific opportunity by integer ID
        opp = client.opportunities.get(42)

        # List trends
        trends = client.trends.list(region="north_america", days=14)

        # Market overview
        markets = client.markets.list()

        # Regional breakdown
        market = client.markets.get("north_america")
    """

    DEFAULT_BASE_URL = "https://api.oppgrid.com/v1"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialise the OppGrid client.

        Args:
            api_key:  Your OppGrid API key (starts with ``og_live_`` or ``og_test_``).
            base_url: Override the API base URL (useful for local development).
            timeout:  Request timeout in seconds (default 30).

        Raises:
            AuthenticationError: If ``api_key`` is empty.
        """
        if not api_key:
            raise AuthenticationError("api_key is required")

        self._api_key = api_key
        # Normalise base_url — always strip trailing slash so we can do
        # f"{base_url}/{path.lstrip('/')}" safely.
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": f"oppgrid-python/{__version__}",
            }
        )

        # Resource accessors
        self.opportunities = OpportunitiesResource(self)
        self.trends = TrendsResource(self)
        self.markets = MarketsResource(self)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an API request and return the decoded JSON body.

        Raises:
            AuthenticationError: HTTP 401.
            NotFoundError:       HTTP 404.
            RateLimitError:      HTTP 429 (sets ``retry_after`` from Retry-After header).
            OppGridError:        Any other HTTP 4xx / 5xx.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise OppGridError(f"Network request failed: {exc}") from exc

        if response.status_code == 401:
            body = _safe_json(response)
            msg = body.get("detail") or body.get("message") or "Invalid or expired API key"
            raise AuthenticationError(msg)

        if response.status_code == 404:
            body = _safe_json(response)
            msg = body.get("detail") or body.get("message") or "Resource not found"
            raise NotFoundError(msg)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            body = _safe_json(response)
            msg = body.get("detail") or body.get("message") or "Rate limit exceeded"
            raise RateLimitError(msg, retry_after=retry_after)

        if response.status_code >= 400:
            body = _safe_json(response)
            msg = (
                body.get("detail")
                or body.get("message")
                or f"HTTP {response.status_code}"
            )
            raise OppGridError(
                msg,
                status_code=response.status_code,
                error_code=body.get("error"),
            )

        return response.json()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_json(response: requests.Response) -> Dict[str, Any]:
    """Return parsed JSON or empty dict if the body is not valid JSON."""
    try:
        return response.json()
    except ValueError:
        return {}
