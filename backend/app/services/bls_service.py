"""
BLS Service — Fetches industry labor market data from the Bureau of Labor Statistics.

Primary source: BLS QCEW Open Data API
  URL pattern: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics_code}.json
  Quarter: "a" for annual, or "1"/"2"/"3"/"4" for quarterly data
  Returns: employment, establishment count, wages by NAICS code

Graceful degradation:
  - Returns None when BLS_API_KEY is not configured (explicit contract)
  - If QCEW endpoint returns a non-200 response, falls back to BLS CES timeseries API
    (the QCEW endpoint returns 404 from some network environments; the CES timeseries
    API at api.bls.gov/publicAPI/v1/ works without authentication)
  - CES fallback populates all fields except establishment_count (set to 0)

Data period format:
  - QCEW: "{year} Q{quarter}" or "{year} Annual" (e.g. "2024 Q3", "2024 Annual")
  - CES fallback: converted to QCEW quarter style (e.g. "December 2025" -> "2025 Q4")

Results cached 7 days via LocationAnalysisCache.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List, TYPE_CHECKING

import httpx

from app.models.report_context import IndustryLaborData

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

QCEW_BASE_URL = "https://data.bls.gov/cew/data/api"
BLS_API_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_API_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
CACHE_TTL_DAYS = 7

# Business type keyword → (CES employment series, CES earnings series, NAICS code, industry name)
# CES format: CEU{supersector/industry_group}{datatype}
#   01 = all employees (thousands), 11 = average weekly earnings ($)
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
SUPERSECTOR_FALLBACKS: Dict[str, Tuple[str, str, str, str]] = {
    "health":      ("CEU6562000001", "CEU6562000011", "621", "Health Care & Social Assistance"),
    "medical":     ("CEU6562000001", "CEU6562000011", "621", "Health Care & Social Assistance"),
    "tech":        ("CEU5051800001", "CEU5051800011", "518", "Information Technology"),
    "retail":      ("CEU4200000001", "CEU4200000011", "44-45", "Retail Trade"),
    "real estate": ("CEU5500000001", "CEU5500000011", "53", "Real Estate & Rental"),
}

# Month number → quarter mapping
_MONTH_TO_QUARTER: Dict[int, int] = {
    1: 1, 2: 1, 3: 1,
    4: 2, 5: 2, 6: 2,
    7: 3, 8: 3, 9: 3,
    10: 4, 11: 4, 12: 4,
}

# BLS QCEW field indices in the flat data arrays
# Column layout from QCEW API: area_fips, own_code, industry_code, agglvl_code,
# size_code, year, qtr, disclosure_code, area_title, own_title, industry_title,
# agglvl_title, size_title, month1_emplvl, month2_emplvl, month3_emplvl,
# total_qtrly_wages, taxable_qtrly_wages, qtrly_contributions, avg_wkly_wage,
# lq_disclosure_code, lq_month1_emplvl, ..., lq_avg_wkly_wage,
# oty_month1_emplvl_chg, oty_month1_emplvl_pct_chg, ..., oty_avg_wkly_wage_pct_chg,
# establishment_count
#
# When fetched via the /industry/{naics}.json endpoint (national, all ownerships),
# each record in the data array is a dict with named fields.


def _month_name_to_quarter(month_name: str, year: str) -> str:
    """Convert a BLS CES month name like 'December' and year '2025' to '2025 Q4'."""
    months = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
    }
    month_num = months.get(month_name.strip(), 0)
    qtr = _MONTH_TO_QUARTER.get(month_num, 4)
    return f"{year} Q{qtr}"


def _latest_complete_qcew_period() -> Tuple[int, str]:
    """Return (year, qtr_str) for the most recently available QCEW release.

    QCEW data is released approximately 5 months after quarter close.
    Q4 data is typically available by late May of the following year.
    """
    now = datetime.utcnow()
    year = now.year
    month = now.month
    # Estimate latest available quarter (lag ≈ 5 months)
    available_month = month - 5
    if available_month <= 0:
        year -= 1
        available_month += 12
    qtr = _MONTH_TO_QUARTER.get(available_month, 4)
    return year, str(qtr)


class BLSService:
    """Fetches and caches BLS QCEW industry labor data.

    Requires BLS_API_KEY to be set; returns None gracefully when the key is absent.
    Falls back to CES timeseries API if QCEW endpoint is unavailable.
    """

    def __init__(self):
        self.api_key = os.environ.get("BLS_API_KEY", "").strip()

    def _is_configured(self) -> bool:
        return bool(self.api_key)

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
        """Return IndustryLaborData for the given NAICS code.

        Checks database cache first (7-day TTL), then fetches from BLS QCEW.
        Returns None when BLS_API_KEY is not configured.
        """
        if not self._is_configured():
            logger.debug("[BLS] BLS_API_KEY not configured — skipping QCEW fetch")
            return None

        # Find the CES series for this NAICS code (needed for CES fallback)
        emp_series = wage_series = None
        for keyword, (emp_s, wage_s, naics, name) in BUSINESS_TO_CES.items():
            if naics == naics_code:
                emp_series, wage_series = emp_s, wage_s
                industry_name = industry_name or name
                break

        cache_key = f"bls_qcew_{naics_code}"
        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_qcew(naics_code, industry_name)
        if result is None and emp_series:
            logger.debug(f"[BLS] QCEW unavailable for {naics_code}, falling back to CES")
            result = await self._fetch_ces(emp_series, wage_series, naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def get_industry_data_for_business(
        self,
        business_type: str,
        db: Optional["Session"] = None,
    ) -> Optional[IndustryLaborData]:
        """Main entry point: looks up the NAICS code from the business type string
        and returns IndustryLaborData, or None if not mapped or key absent.
        """
        if not self._is_configured():
            logger.debug("[BLS] BLS_API_KEY not configured — skipping QCEW fetch")
            return None

        mapping = self.get_ces_for_business(business_type)
        if not mapping:
            logger.debug(f"[BLS] No mapping for business type: '{business_type}'")
            return None

        emp_series, wage_series, naics_code, industry_name = mapping
        cache_key = f"bls_qcew_{naics_code}"

        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_qcew(naics_code, industry_name)
        if result is None:
            logger.debug(f"[BLS] QCEW unavailable for {naics_code}, falling back to CES")
            result = await self._fetch_ces(emp_series, wage_series, naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def _fetch_qcew(
        self,
        naics_code: str,
        industry_name: str,
    ) -> Optional[IndustryLaborData]:
        """Fetch employment, wages, and establishment count from the QCEW Open Data API.

        URL: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics_code}.json
        Returns None on any HTTP/parse failure so caller can fall back to CES.
        """
        year, qtr = _latest_complete_qcew_period()
        quarters_to_try: List[Tuple[int, str]] = [(year, qtr)]
        # Also try annual data and prior year if recent quarter unavailable
        if qtr != "a":
            quarters_to_try.append((year, "a"))
        quarters_to_try.append((year - 1, "a"))

        for try_year, try_qtr in quarters_to_try:
            url = f"{QCEW_BASE_URL}/{try_year}/{try_qtr}/industry/{naics_code}.json"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.debug(f"[BLS] QCEW {url} → HTTP {resp.status_code}")
                        continue
                    raw = resp.json()
            except Exception as exc:
                logger.debug(f"[BLS] QCEW request failed for {url}: {exc}")
                continue

            result = self._parse_qcew_response(raw, naics_code, industry_name, try_year, try_qtr)
            if result is not None:
                logger.info(
                    f"[BLS] QCEW {naics_code} FY{try_year} Q{try_qtr}: "
                    f"{result.total_employment:,} employed, {result.establishment_count:,} establishments, "
                    f"${result.avg_weekly_wage:,.2f}/wk"
                )
                return result

        return None

    def _parse_qcew_response(
        self,
        raw: dict,
        naics_code: str,
        industry_name: str,
        year: int,
        qtr: str,
    ) -> Optional[IndustryLaborData]:
        """Parse the QCEW API JSON response into IndustryLaborData."""
        # QCEW API returns a dict with area-code keys, each containing a list of records.
        # For national data, the key is "US000" or similar.
        try:
            records: List[dict] = []
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, list):
                        records.extend(val)
                    elif isinstance(val, dict):
                        records.append(val)
            elif isinstance(raw, list):
                records = raw

            if not records:
                return None

            # Find national total private + government ownership record
            # own_code: 0=total all, 5=private, 1=federal, 2=state, 3=local
            # agglvl_code: 14=national by industry, 74=county by industry, etc.
            target_record = None
            for rec in records:
                own = str(rec.get("own_code", rec.get("ownCode", "")))
                agglvl = str(rec.get("agglvl_code", rec.get("agglvlCode", "")))
                area = str(rec.get("area_fips", rec.get("areaFips", ""))).upper()
                # Prefer national total-all-ownerships at national industry level
                if area.startswith("US") or area == "00000":
                    if own in ("0", "5") and agglvl in ("14", "13", "12"):
                        target_record = rec
                        break
                    elif own in ("0", "5"):
                        target_record = rec

            if target_record is None and records:
                target_record = records[0]

            # Extract employment (use month3 as end-of-quarter, or month1 as fallback)
            emp = (
                _safe_int(target_record.get("month3_emplvl") or target_record.get("month3Emplvl"))
                or _safe_int(target_record.get("month1_emplvl") or target_record.get("month1Emplvl"))
                or 0
            )

            # Establishment count
            est_count = (
                _safe_int(target_record.get("qtrly_estabs") or target_record.get("qtrlyEstabs"))
                or _safe_int(target_record.get("annual_avg_estabs") or target_record.get("annualAvgEstabs"))
                or 0
            )

            # Average weekly wage
            avg_wage = (
                _safe_float(target_record.get("avg_wkly_wage") or target_record.get("avgWklyWage"))
                or 0.0
            )

            # YoY employment change pct
            yoy_pct = (
                _safe_float(
                    target_record.get("oty_month3_emplvl_pct_chg")
                    or target_record.get("otyMonth3EmplvlPctChg")
                )
                or 0.0
            )

            # Industry name from record if not provided
            if not industry_name:
                industry_name = (
                    target_record.get("industry_title")
                    or target_record.get("industryTitle")
                    or f"NAICS {naics_code}"
                )

            period_label = f"{year} Q{qtr}" if qtr.isdigit() else f"{year} Annual"
            period_source = f"BLS QCEW {period_label}"

            return IndustryLaborData(
                naics_code=naics_code,
                industry_name=industry_name,
                total_employment=emp,
                employment_change_yoy=round(yoy_pct, 2),
                avg_weekly_wage=avg_wage,
                establishment_count=est_count,
                data_period=period_label,
                source=period_source,
            )
        except Exception as exc:
            logger.warning(f"[BLS] QCEW parse error for {naics_code}: {exc}")
            return None

    async def _fetch_ces(
        self,
        emp_series: str,
        wage_series: str,
        naics_code: str,
        industry_name: str,
    ) -> Optional[IndustryLaborData]:
        """Fallback: fetch employment and wage data via CES timeseries API.

        Uses v2 (registered key) when available, otherwise v1 (public).
        Data period formatted as QCEW-style quarter (e.g. "2025 Q4").
        establishment_count will be 0 as CES does not provide it.
        """
        series_ids = [emp_series, wage_series]
        payload: dict = {"seriesid": series_ids, "startyear": "2023", "endyear": "2025"}
        if self.api_key:
            payload["registrationkey"] = self.api_key

        url = BLS_API_V2 if self.api_key else BLS_API_V1
        data = None

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(f"[BLS] CES fetch failed for {emp_series}: {exc}")
            return None

        # If registered key is rejected (not yet email-verified), retry with v1
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
            # Convert CES month/year to QCEW quarter format
            data_period = _month_name_to_quarter(period_month, period_year)

            logger.info(
                f"[BLS] CES fallback {emp_series}: {total_employment:,} employed, "
                f"${avg_weekly_wage:,.2f}/wk, {employment_change_yoy:+.1f}% YoY, period={data_period}"
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
            logger.warning(f"[BLS] CES parse error for {emp_series}: {exc}")
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


def _safe_int(val) -> Optional[int]:
    """Safely convert a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
