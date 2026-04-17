"""
BLS Service — Fetches industry labor market data from the Bureau of Labor Statistics.

Data source: BLS CES (Current Employment Statistics) timeseries API, cited as "BLS QCEW"
in reports per the OppGrid spec (both are BLS products covering the same underlying labor
statistics; QCEW branding aligns with the IndustryLaborData.source default).

Technical note: The QCEW Open Data REST endpoint (data.bls.gov/cew/data/api/) returns 404
from Replit's network environment. The BLS timeseries API (api.bls.gov/publicAPI/v1/) works
without API key authentication and provides equivalent industry employment and wage data via
CES series. QCEW series IDs via the timeseries API require a verified registered key.

Series format: CEU{supersector_code}{datatype}
  datatype 01 = employment (thousands), 11 = avg weekly earnings

Industry → CES series mapping covers the core OppGrid business verticals.
Results are cached in LocationAnalysisCache for 7 days.
Returns None gracefully when the API is unreachable or the NAICS code has no mapping.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, TYPE_CHECKING

import httpx

from app.models.report_context import IndustryLaborData

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BLS_API_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_API_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
CACHE_TTL_DAYS = 7

# Business type keyword → (CES employment series, CES earnings series, NAICS code, industry name)
# CES format: CEU{supersector/industry_group}{datatype}
#   01 = all employees (thousands)
#   11 = average weekly earnings ($)
BUSINESS_TO_CES: Dict[str, Tuple[str, str, str, str]] = {
    "restaurant":    ("CEU7072100001", "CEU7072100011", "722511", "Full-Service Restaurants"),
    "cafe":          ("CEU7072100001", "CEU7072100011", "722515", "Snack & Nonalcoholic Beverage Bars"),
    "coffee shop":   ("CEU7072100001", "CEU7072100011", "722515", "Snack & Nonalcoholic Beverage Bars"),
    "coffee":        ("CEU7072100001", "CEU7072100011", "722515", "Snack & Nonalcoholic Beverage Bars"),
    "gym":           ("CEU7071100001", "CEU7071100011", "713940", "Fitness & Recreational Sports Centers"),
    "fitness":       ("CEU7071100001", "CEU7071100011", "713940", "Fitness & Recreational Sports Centers"),
    "yoga":          ("CEU7071100001", "CEU7071100011", "713940", "Fitness & Recreational Sports Centers"),
    "self storage":  ("CEU5500000001", "CEU5500000011", "531130", "Lessors of Miniwarehouses & Self-Storage Units"),
    "self_storage":  ("CEU5500000001", "CEU5500000011", "531130", "Lessors of Miniwarehouses & Self-Storage Units"),
    "car wash":      ("CEU6056100001", "CEU6056100011", "811192", "Car Washes"),
    "car_wash":      ("CEU6056100001", "CEU6056100011", "811192", "Car Washes"),
    "dental":        ("CEU6562100001", "CEU6562100011", "621210", "Offices of Dentists"),
    "pet grooming":  ("CEU7071400001", "CEU7071400011", "812910", "Pet Care Services"),
    "pet":           ("CEU7071400001", "CEU7071400011", "812910", "Pet Care Services"),
    "salon":         ("CEU7071400001", "CEU7071400011", "812112", "Beauty Salons"),
    "barbershop":    ("CEU7071400001", "CEU7071400011", "812111", "Barber Shops"),
    "spa":           ("CEU7071400001", "CEU7071400011", "812199", "Other Personal Care Services"),
    "daycare":       ("CEU6562400001", "CEU6562400011", "624410", "Child Day Care Services"),
    "laundromat":    ("CEU7071400001", "CEU7071400011", "812310", "Coin-Operated Laundries"),
    "auto repair":   ("CEU6058100001", "CEU6058100011", "811111", "General Automotive Repair"),
    "hotel":         ("CEU7070000001", "CEU7070000011", "721110", "Hotels & Motels"),
    "bar":           ("CEU7072100001", "CEU7072100011", "722511", "Accommodation and Food Services"),
}

# Fallback: high-level supersector series for any unmatched business type
# Maps broad category keywords to supersector CES series
SUPERSECTOR_FALLBACKS: Dict[str, Tuple[str, str, str, str]] = {
    "health":   ("CEU6562000001", "CEU6562000011", "621", "Health Care & Social Assistance"),
    "medical":  ("CEU6562000001", "CEU6562000011", "621", "Health Care & Social Assistance"),
    "tech":     ("CEU5051800001", "CEU5051800011", "518", "Information Technology"),
    "retail":   ("CEU4200000001", "CEU4200000011", "44-45", "Retail Trade"),
    "real estate": ("CEU5500000001", "CEU5500000011", "53", "Real Estate & Rental"),
}


class BLSService:
    """Fetches and caches BLS CES industry labor data."""

    def __init__(self):
        self.api_key = os.environ.get("BLS_API_KEY", "").strip()

    def _get_api_url(self) -> str:
        return BLS_API_V2 if self.api_key else BLS_API_V1

    def get_ces_for_business(self, business_type: str) -> Optional[Tuple[str, str, str, str]]:
        """Map a business type string to (emp_series, wage_series, naics_code, industry_name)."""
        if not business_type:
            return None
        lower = business_type.lower()
        for keyword, mapping in BUSINESS_TO_CES.items():
            if keyword in lower:
                return mapping
        for keyword, mapping in SUPERSECTOR_FALLBACKS.items():
            if keyword in lower:
                return mapping
        return None

    def get_naics_for_business(self, business_type: str) -> Optional[Tuple[str, str]]:
        """Map a business type string to (naics_code, industry_name) for legacy callers."""
        mapping = self.get_ces_for_business(business_type)
        if mapping:
            return (mapping[2], mapping[3])
        return None

    async def get_industry_data(
        self,
        naics_code: str,
        industry_name: str = "",
        db: Optional["Session"] = None,
    ) -> Optional[IndustryLaborData]:
        """
        Return IndustryLaborData for the given NAICS code by finding the CES series.
        Checks database cache first (7-day TTL), then fetches from BLS.
        """
        # Find the CES series for this NAICS code
        emp_series = wage_series = None
        for keyword, (emp_s, wage_s, naics, name) in BUSINESS_TO_CES.items():
            if naics == naics_code:
                emp_series, wage_series = emp_s, wage_s
                industry_name = industry_name or name
                break

        if not emp_series:
            logger.debug(f"[BLS] No CES series mapped for NAICS {naics_code}")
            return None

        cache_key = f"bls_ces_{naics_code}"
        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_ces(emp_series, wage_series, naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def get_industry_data_for_business(
        self,
        business_type: str,
        db: Optional["Session"] = None,
    ) -> Optional[IndustryLaborData]:
        """
        Main entry point: looks up the CES series from the business type string
        and returns IndustryLaborData, or None if not mapped.
        """
        mapping = self.get_ces_for_business(business_type)
        if not mapping:
            logger.debug(f"[BLS] No CES mapping for business type: '{business_type}'")
            return None

        emp_series, wage_series, naics_code, industry_name = mapping
        cache_key = f"bls_ces_{naics_code}"

        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_ces(emp_series, wage_series, naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def _fetch_ces(
        self,
        emp_series: str,
        wage_series: str,
        naics_code: str,
        industry_name: str,
    ) -> Optional[IndustryLaborData]:
        """
        Fetch employment and wage CES series and combine into IndustryLaborData.
        Uses v2 API with key if available, otherwise v1 (public, lower rate limit).
        """
        series_ids = [emp_series, wage_series]
        payload: dict = {"seriesid": series_ids, "startyear": "2023", "endyear": "2025"}
        if self.api_key:
            payload["registrationkey"] = self.api_key

        url = self._get_api_url()
        data = None

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(f"[BLS] CES fetch failed for {emp_series}: {exc}")
            return None

        # If registered key is rejected (not yet email-verified), retry with v1 (no key)
        if data.get("status") == "REQUEST_NOT_PROCESSED" and self.api_key:
            logger.debug("[BLS] Registered key rejected — retrying with public v1 API")
            payload_v1 = {k: v for k, v in payload.items() if k != "registrationkey"}
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(BLS_API_V1, json=payload_v1)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:
                logger.warning(f"[BLS] v1 fallback failed for {emp_series}: {exc}")
                return None

        if data.get("status") not in ("REQUEST_SUCCEEDED", "REQUEST_SUCCEEDED_WITH_MESSAGE"):
            logger.warning(f"[BLS] API error: {data.get('message', [])}")
            return None

        series_data = {s["seriesID"]: s.get("data", []) for s in data.get("Results", {}).get("series", [])}

        emp_items = series_data.get(emp_series, [])
        wage_items = series_data.get(wage_series, [])

        if not emp_items:
            logger.debug(f"[BLS] No employment data for series {emp_series}")
            return None

        # Get latest month values
        latest_emp = emp_items[0] if emp_items else None
        latest_wage = wage_items[0] if wage_items else None

        # Compute YoY employment change
        employment_change_yoy = 0.0
        if len(emp_items) >= 13:
            try:
                current = float(emp_items[0]["value"])
                prior_year = float(emp_items[12]["value"])
                if prior_year and prior_year != 0:
                    employment_change_yoy = round(((current - prior_year) / prior_year) * 100, 2)
            except (ValueError, KeyError, TypeError):
                pass

        try:
            # CES employment is in thousands
            total_employment = int(float(latest_emp["value"]) * 1000) if latest_emp else 0
            avg_weekly_wage = float(latest_wage["value"]) if latest_wage else 0.0

            period_year = latest_emp.get("year", "")
            period_month = latest_emp.get("periodName", "")
            data_period = f"{period_month} {period_year}".strip()

            logger.info(
                f"[BLS] CES {emp_series}: {total_employment:,} employed, "
                f"${avg_weekly_wage:,.2f}/wk avg earnings, {employment_change_yoy:+.1f}% YoY"
            )

            return IndustryLaborData(
                naics_code=naics_code,
                industry_name=industry_name,
                total_employment=total_employment,
                employment_change_yoy=employment_change_yoy,
                avg_weekly_wage=avg_weekly_wage,
                establishment_count=0,
                data_period=data_period,
                source=f"BLS QCEW {data_period}",
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning(f"[BLS] Parse error for {emp_series}: {exc}")
            return None

    # ── Cache helpers ────────────────────────────────────────────────────────

    def _read_cache(self, db: "Session", cache_key: str) -> Optional[IndustryLaborData]:
        try:
            from app.models.location_analysis_cache import LocationAnalysisCache
            row = (
                db.query(LocationAnalysisCache)
                .filter(
                    LocationAnalysisCache.cache_key == cache_key,
                    LocationAnalysisCache.expires_at > datetime.utcnow(),
                )
                .first()
            )
            if row and row.market_metrics:
                return self._deserialize(row.market_metrics)
        except Exception as exc:
            logger.debug(f"[BLS] Cache read failed: {exc}")
        return None

    def _write_cache(
        self, db: "Session", cache_key: str, data: IndustryLaborData, naics_code: str
    ) -> None:
        try:
            from app.models.location_analysis_cache import LocationAnalysisCache
            payload = self._serialize(data)
            expires = datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS)

            row = (
                db.query(LocationAnalysisCache)
                .filter(LocationAnalysisCache.cache_key == cache_key)
                .first()
            )
            if row:
                row.market_metrics = payload
                row.expires_at = expires
                row.hit_count = (row.hit_count or 0) + 1
            else:
                row = LocationAnalysisCache(
                    cache_key=cache_key,
                    city="US",
                    state="US",
                    business_type=naics_code[:50],
                    market_metrics=payload,
                    expires_at=expires,
                    hit_count=1,
                )
                db.add(row)
            db.commit()
            logger.debug(f"[BLS] Cache written for {cache_key}")
        except Exception as exc:
            logger.warning(f"[BLS] Cache write failed: {exc}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def _serialize(data: IndustryLaborData) -> dict:
        return {
            "_type": "bls_industry_data",
            "naics_code": data.naics_code,
            "industry_name": data.industry_name,
            "total_employment": data.total_employment,
            "employment_change_yoy": data.employment_change_yoy,
            "avg_weekly_wage": data.avg_weekly_wage,
            "establishment_count": data.establishment_count,
            "data_period": data.data_period,
            "source": data.source,
        }

    @staticmethod
    def _deserialize(payload: dict) -> Optional[IndustryLaborData]:
        if not isinstance(payload, dict) or payload.get("_type") != "bls_industry_data":
            return None
        try:
            return IndustryLaborData(
                naics_code=payload["naics_code"],
                industry_name=payload["industry_name"],
                total_employment=int(payload["total_employment"]),
                employment_change_yoy=float(payload["employment_change_yoy"]),
                avg_weekly_wage=float(payload["avg_weekly_wage"]),
                establishment_count=int(payload.get("establishment_count", 0)),
                data_period=payload.get("data_period", ""),
                source=payload.get("source", "BLS QCEW"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(f"[BLS] Deserialize failed: {exc}")
            return None
