"""
FRED Service — Fetches macroeconomic indicators from the St. Louis Fed FRED API.

Provides the 6 core macro series used in OppGrid report generation:
  - GDPC1:        Real GDP (quarterly growth rate)
  - CPIAUCSL:     CPI — inflation gauge
  - FEDFUNDS:     Federal Funds Rate
  - UNRATE:       U.S. Unemployment Rate
  - UMCSENT:      University of Michigan Consumer Sentiment
  - MORTGAGE30US: 30-Year Fixed Mortgage Average

All results are cached in LocationAnalysisCache for 24 hours per the spec.
Returns None gracefully if FRED_API_KEY is absent or the API is unreachable.
"""
import json
import logging
import os
from datetime import datetime, timedelta, date
from typing import Optional, TYPE_CHECKING

import httpx

from app.models.report_context import EconomicIndicator, MacroeconomicContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
CACHE_KEY = "fred_macro_context"
CACHE_TTL_HOURS = 24

# Series definitions: (series_id, human_name, units)
FRED_SERIES = [
    ("GDPC1",        "Real GDP Growth Rate",          "Percent Change"),
    ("CPIAUCSL",     "CPI / Inflation Rate",          "Index 1982-84=100"),
    ("FEDFUNDS",     "Federal Funds Rate",            "Percent"),
    ("UNRATE",       "Unemployment Rate",             "Percent"),
    ("UMCSENT",      "Consumer Sentiment (UMich)",    "Index 1966 Q1=100"),
    ("MORTGAGE30US", "30-Year Mortgage Rate",         "Percent"),
]


class FREDService:
    """Fetches and caches macroeconomic indicators from FRED."""

    def __init__(self):
        self.api_key = os.environ.get("FRED_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_series(self, series_id: str) -> Optional[dict]:
        """
        Fetch the most recent observation for a FRED series.
        Returns a dict with keys: value, date, or None on failure.
        """
        if not self.is_configured:
            return None
        try:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": "2",  # 2 so we can compute GDP growth
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(FRED_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    return None
                return {"observations": observations, "units": data.get("units", "")}
        except Exception as exc:
            logger.warning(f"[FRED] Series {series_id} fetch failed: {exc}")
            return None

    async def get_macro_context(
        self, db: Optional["Session"] = None
    ) -> Optional[MacroeconomicContext]:
        """
        Return a MacroeconomicContext with the 6 core FRED indicators.
        Checks the database cache first; falls back to live FRED API.
        Returns None if FRED_API_KEY is not configured or all fetches fail.
        """
        if not self.is_configured:
            logger.debug("[FRED] FRED_API_KEY not configured — skipping macro context")
            return None

        # ── Cache read ───────────────────────────────────────────────────────
        if db is not None:
            cached = self._read_cache(db)
            if cached is not None:
                return cached

        # ── Live fetch ───────────────────────────────────────────────────────
        ctx = await self._fetch_live()
        if ctx is None:
            return None

        # ── Cache write ──────────────────────────────────────────────────────
        if db is not None:
            self._write_cache(db, ctx)

        return ctx

    async def _fetch_live(self) -> Optional[MacroeconomicContext]:
        """Fetch all 6 series concurrently and assemble a MacroeconomicContext."""
        import asyncio
        results = await asyncio.gather(
            *[self.get_series(sid) for sid, _, _ in FRED_SERIES],
            return_exceptions=True,
        )

        indicators = {}
        for (series_id, name, units), result in zip(FRED_SERIES, results):
            if isinstance(result, Exception) or result is None:
                indicators[series_id] = None
                continue
            observations = result.get("observations", [])
            if not observations:
                indicators[series_id] = None
                continue

            latest = observations[0]
            raw_value = latest.get("value", ".")
            if raw_value == "." or raw_value is None:
                # Some series have missing values — use next observation
                if len(observations) > 1:
                    raw_value = observations[1].get("value", ".")
            if raw_value == "." or raw_value is None:
                indicators[series_id] = None
                continue

            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                indicators[series_id] = None
                continue

            # For Real GDP, compute annualised growth rate vs prior period
            if series_id == "GDPC1" and len(observations) >= 2:
                try:
                    prior = float(observations[1]["value"])
                    if prior and prior != 0:
                        value = round(((value - prior) / prior) * 400, 2)  # annualised
                        units = "% annualised"
                except (ValueError, KeyError):
                    pass

            try:
                obs_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
            except Exception:
                obs_date = date.today()

            indicators[series_id] = EconomicIndicator(
                series_id=series_id,
                name=name,
                value=value,
                date=obs_date,
                units=units,
                source=f"FRED ({latest['date']})",
            )

        if not any(v is not None for v in indicators.values()):
            return None

        ctx = MacroeconomicContext(
            gdp_growth=indicators.get("GDPC1"),
            inflation_rate=indicators.get("CPIAUCSL"),
            fed_funds_rate=indicators.get("FEDFUNDS"),
            unemployment=indicators.get("UNRATE"),
            consumer_sentiment=indicators.get("UMCSENT"),
            mortgage_rate=indicators.get("MORTGAGE30US"),
            retrieved_at=datetime.utcnow().isoformat(),
        )
        logger.info("[FRED] Macro context fetched successfully")
        return ctx

    # ── Cache helpers ────────────────────────────────────────────────────────

    def _read_cache(self, db: "Session") -> Optional[MacroeconomicContext]:
        """Return cached MacroeconomicContext if still valid, else None."""
        try:
            from app.models.location_analysis_cache import LocationAnalysisCache
            row = (
                db.query(LocationAnalysisCache)
                .filter(
                    LocationAnalysisCache.cache_key == CACHE_KEY,
                    LocationAnalysisCache.expires_at > datetime.utcnow(),
                )
                .first()
            )
            if row and row.market_metrics:
                return self._deserialize(row.market_metrics)
        except Exception as exc:
            logger.debug(f"[FRED] Cache read failed: {exc}")
        return None

    def _write_cache(self, db: "Session", ctx: MacroeconomicContext) -> None:
        """Upsert the MacroeconomicContext into the cache table."""
        try:
            from app.models.location_analysis_cache import LocationAnalysisCache
            payload = self._serialize(ctx)
            expires = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)

            row = (
                db.query(LocationAnalysisCache)
                .filter(LocationAnalysisCache.cache_key == CACHE_KEY)
                .first()
            )
            if row:
                row.market_metrics = payload
                row.expires_at = expires
                row.hit_count = (row.hit_count or 0) + 1
            else:
                row = LocationAnalysisCache(
                    cache_key=CACHE_KEY,
                    city="US",
                    state="US",
                    business_type="macro",
                    market_metrics=payload,
                    expires_at=expires,
                    hit_count=1,
                )
                db.add(row)
            db.commit()
            logger.debug("[FRED] Cache written")
        except Exception as exc:
            logger.warning(f"[FRED] Cache write failed: {exc}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def _serialize(ctx: MacroeconomicContext) -> dict:
        """Convert MacroeconomicContext → JSON-safe dict."""
        def indicator_to_dict(ind: Optional[EconomicIndicator]) -> Optional[dict]:
            if ind is None:
                return None
            return {
                "series_id": ind.series_id,
                "name": ind.name,
                "value": ind.value,
                "date": ind.date.isoformat() if isinstance(ind.date, date) else str(ind.date),
                "units": ind.units,
                "source": ind.source,
            }

        return {
            "gdp_growth": indicator_to_dict(ctx.gdp_growth),
            "inflation_rate": indicator_to_dict(ctx.inflation_rate),
            "fed_funds_rate": indicator_to_dict(ctx.fed_funds_rate),
            "unemployment": indicator_to_dict(ctx.unemployment),
            "consumer_sentiment": indicator_to_dict(ctx.consumer_sentiment),
            "mortgage_rate": indicator_to_dict(ctx.mortgage_rate),
            "retrieved_at": ctx.retrieved_at,
            "_type": "fred_macro_context",
        }

    @staticmethod
    def _deserialize(payload: dict) -> Optional[MacroeconomicContext]:
        """Convert JSON dict → MacroeconomicContext."""
        if not isinstance(payload, dict) or payload.get("_type") != "fred_macro_context":
            return None

        def dict_to_indicator(d: Optional[dict]) -> Optional[EconomicIndicator]:
            if not d:
                return None
            try:
                obs_date = datetime.strptime(d["date"], "%Y-%m-%d").date()
            except Exception:
                obs_date = date.today()
            return EconomicIndicator(
                series_id=d["series_id"],
                name=d["name"],
                value=float(d["value"]),
                date=obs_date,
                units=d["units"],
                source=d.get("source", "FRED"),
            )

        return MacroeconomicContext(
            gdp_growth=dict_to_indicator(payload.get("gdp_growth")),
            inflation_rate=dict_to_indicator(payload.get("inflation_rate")),
            fed_funds_rate=dict_to_indicator(payload.get("fed_funds_rate")),
            unemployment=dict_to_indicator(payload.get("unemployment")),
            consumer_sentiment=dict_to_indicator(payload.get("consumer_sentiment")),
            mortgage_rate=dict_to_indicator(payload.get("mortgage_rate")),
            retrieved_at=payload.get("retrieved_at", ""),
        )
