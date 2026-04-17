"""
BLS Service — Fetches industry labor market data from the Bureau of Labor Statistics QCEW API.

Uses the BLS QCEW (Quarterly Census of Employment and Wages) flat-file API to retrieve
national-level employment and wage data for a given NAICS industry code.

Endpoint: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics_code}.json
  - Filters for area_fips="US000" (national total), own_code="0" (all ownerships),
    agglvl_code="14" (national industry aggregate)

Industry → NAICS mapping covers 10 verticals per the OppGrid spec.
Results are cached in LocationAnalysisCache for 7 days.
Returns None gracefully when the API is unreachable or the NAICS code has no data.
"""
import logging
import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Tuple, TYPE_CHECKING

import httpx

from app.models.report_context import IndustryLaborData

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

QCEW_BASE_URL = "https://data.bls.gov/cew/data/api"
CACHE_TTL_DAYS = 7

# Business type keyword → (NAICS code, industry name)
NAICS_MAPPING: Dict[str, Tuple[str, str]] = {
    "self storage":   ("531130", "Lessors of Miniwarehouses & Self-Storage Units"),
    "self_storage":   ("531130", "Lessors of Miniwarehouses & Self-Storage Units"),
    "restaurant":     ("722511", "Full-Service Restaurants"),
    "gym":            ("713940", "Fitness & Recreational Sports Centers"),
    "fitness":        ("713940", "Fitness & Recreational Sports Centers"),
    "car wash":       ("811192", "Car Washes"),
    "car_wash":       ("811192", "Car Washes"),
    "coffee":         ("722515", "Snack & Nonalcoholic Beverage Bars"),
    "coffee shop":    ("722515", "Snack & Nonalcoholic Beverage Bars"),
    "cafe":           ("722515", "Snack & Nonalcoholic Beverage Bars"),
    "dental":         ("621210", "Offices of Dentists"),
    "pet":            ("812910", "Pet Care Services (except Veterinary)"),
    "pet grooming":   ("812910", "Pet Care Services (except Veterinary)"),
    "auto repair":    ("811111", "General Automotive Repair"),
    "daycare":        ("624410", "Child Day Care Services"),
    "pharmacy":       ("446110", "Pharmacies & Drug Stores"),
    "hotel":          ("721110", "Hotels (except Casino Hotels) and Motels"),
    "laundromat":     ("812310", "Coin-Operated Laundries & Drycleaners"),
    "brewery":        ("312120", "Breweries"),
    "yoga":           ("713940", "Fitness & Recreational Sports Centers"),
    "spa":            ("812199", "Other Personal Care Services"),
    "salon":          ("812112", "Beauty Salons"),
    "barbershop":     ("812111", "Barber Shops"),
}

# BLS QCEW filter constants for national industry totals
NATIONAL_AREA_FIPS = "US000"
ALL_OWNERSHIPS = "0"
NATIONAL_INDUSTRY_AGGLVL = "14"


class BLSService:
    """Fetches and caches BLS QCEW industry labor data."""

    def get_naics_for_business(self, business_type: str) -> Optional[Tuple[str, str]]:
        """Map a business type string to (naics_code, industry_name), or None."""
        if not business_type:
            return None
        lower = business_type.lower()
        for keyword, mapping in NAICS_MAPPING.items():
            if keyword in lower:
                return mapping
        return None

    async def get_industry_data(
        self,
        naics_code: str,
        industry_name: str = "",
        db: Optional["Session"] = None,
    ) -> Optional[IndustryLaborData]:
        """
        Return IndustryLaborData for the given NAICS code.
        Checks database cache first (7-day TTL), then fetches from BLS QCEW.
        Returns None on any failure.
        """
        cache_key = f"bls_industry_{naics_code}"

        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_live(naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def get_industry_data_for_business(
        self,
        business_type: str,
        db: Optional["Session"] = None,
    ) -> Optional[IndustryLaborData]:
        """
        Convenience wrapper: looks up the NAICS code from the business type string
        and returns IndustryLaborData, or None if the business type isn't mapped.
        """
        mapping = self.get_naics_for_business(business_type)
        if not mapping:
            logger.debug(f"[BLS] No NAICS mapping for business type: '{business_type}'")
            return None
        naics_code, industry_name = mapping
        return await self.get_industry_data(naics_code, industry_name, db=db)

    async def _fetch_live(
        self, naics_code: str, industry_name: str
    ) -> Optional[IndustryLaborData]:
        """
        Fetch national QCEW data for the given NAICS code.
        Tries annual data for the most recent completed year; falls back to prior year.
        """
        current_year = datetime.utcnow().year
        for year in [current_year - 1, current_year - 2]:
            result = await self._fetch_annual(naics_code, industry_name, year)
            if result is not None:
                return result
        logger.warning(f"[BLS] No QCEW data found for NAICS {naics_code}")
        return None

    async def _fetch_annual(
        self, naics_code: str, industry_name: str, year: int
    ) -> Optional[IndustryLaborData]:
        """Fetch annual QCEW data for a specific year and NAICS code."""
        url = f"{QCEW_BASE_URL}/{year}/A/industry/{naics_code}.json"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                records = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.warning(f"[BLS] HTTP error for NAICS {naics_code} year {year}: {e}")
            return None
        except Exception as exc:
            logger.warning(f"[BLS] Fetch failed for NAICS {naics_code} year {year}: {exc}")
            return None

        if not isinstance(records, list):
            return None

        # Find the national industry total row
        national_row = None
        for record in records:
            if (
                record.get("area_fips") == NATIONAL_AREA_FIPS
                and str(record.get("own_code", "")) == ALL_OWNERSHIPS
                and str(record.get("agglvl_code", "")) == NATIONAL_INDUSTRY_AGGLVL
            ):
                national_row = record
                break

        # Fallback: look for just the US000 row with any own_code
        if national_row is None:
            for record in records:
                if record.get("area_fips") == NATIONAL_AREA_FIPS:
                    national_row = record
                    break

        if national_row is None:
            logger.debug(f"[BLS] No national row found for NAICS {naics_code} year {year}")
            return None

        try:
            total_employment = int(national_row.get("annual_avg_emplvl", 0) or 0)
            avg_weekly_wage = float(national_row.get("annual_avg_wkly_wage", 0) or 0)
            establishment_count = int(national_row.get("annual_avg_estabs", 0) or 0)

            # Year-over-year employment change (percentage)
            oty_pct = national_row.get("oty_annual_avg_emplvl_pct_chg")
            if oty_pct is not None and oty_pct != "":
                employment_change_yoy = float(oty_pct)
            else:
                employment_change_yoy = 0.0

            data_period = f"{year} Annual"

            if not industry_name:
                industry_name = f"NAICS {naics_code}"

            logger.info(
                f"[BLS] NAICS {naics_code} ({year} Annual): "
                f"{total_employment:,} employees, ${avg_weekly_wage:,.0f}/wk avg wage, "
                f"{employment_change_yoy:+.1f}% YoY"
            )
            return IndustryLaborData(
                naics_code=naics_code,
                industry_name=industry_name,
                total_employment=total_employment,
                employment_change_yoy=employment_change_yoy,
                avg_weekly_wage=avg_weekly_wage,
                establishment_count=establishment_count,
                data_period=data_period,
                source=f"BLS QCEW {data_period}",
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning(f"[BLS] Parse error for NAICS {naics_code}: {exc}")
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
