"""
BLS Service — Fetches industry labor market data from the Bureau of Labor Statistics.

Primary source: BLS QCEW Open Data API
  URL pattern: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics_code}.json
  Quarter: "a" for annual, or "1"/"2"/"3"/"4" for quarterly data
  Returns: employment, establishment count, wages by NAICS code

State-level support:
  The QCEW industry endpoint returns data for all geographic areas in a single response.
  When a state abbreviation is provided, the service filters for the state-level record
  (area_fips = "{state_fips_2digit}000", e.g. "12000" for Florida) and falls back to the
  national total when state-level data is absent.
  Source citation becomes "BLS OES {State} {year}" for state data, "BLS QCEW {period}"
  for national data.

Graceful degradation:
  - Returns None when BLS_API_KEY is not configured (explicit contract; same as FRED/SEC)
  - Returns None when the QCEW endpoint is unavailable (no fallback to other BLS APIs)
  - Tries latest estimated quarter → annual → prior-year annual before giving up

Data period format:
  QCEW quarter style — "{year} Q{quarter}" or "{year} Annual" (e.g. "2025 Q3", "2024 Annual")

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
CACHE_TTL_DAYS = 7

# Business type keyword → (emp_series_placeholder, wage_series_placeholder, NAICS code, industry name)
# The series ID columns are retained for potential future use; NAICS code and industry name
# are used to build the QCEW API request.
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
    "auto_repair":   ("CEU6058100001", "CEU6058100011", "811111", "General Automotive Repair"),
    "automotive":    ("CEU6058100001", "CEU6058100011", "811111", "General Automotive Repair"),
    "mechanic":      ("CEU6058100001", "CEU6058100011", "811111", "General Automotive Repair"),
    "hotel":         ("CEU7070000001", "CEU7070000011", "721110", "Hotels & Motels"),
    "motel":         ("CEU7070000001", "CEU7070000011", "721110", "Hotels & Motels"),
    "hospitality":   ("CEU7070000001", "CEU7070000011", "721110", "Hotels & Motels"),
    "pharmacy":      ("CEU6562400001", "CEU6562400011", "446110", "Pharmacies & Drug Stores"),
    "drug store":    ("CEU6562400001", "CEU6562400011", "446110", "Pharmacies & Drug Stores"),
    "drugstore":     ("CEU6562400001", "CEU6562400011", "446110", "Pharmacies & Drug Stores"),
    "grocery":       ("CEU4200000001", "CEU4200000011", "445110", "Grocery Stores"),
    "supermarket":   ("CEU4200000001", "CEU4200000011", "445110", "Grocery Stores"),
    "food store":    ("CEU4200000001", "CEU4200000011", "445110", "Grocery Stores"),
    "child care":    ("CEU6562400001", "CEU6562400011", "624410", "Child Day Care Services"),
    "childcare":     ("CEU6562400001", "CEU6562400011", "624410", "Child Day Care Services"),
    "preschool":     ("CEU6562400001", "CEU6562400011", "624410", "Child Day Care Services"),
    "coworking":     ("CEU5500000001", "CEU5500000011", "531120", "Lessors of Nonresidential Buildings"),
    "office space":  ("CEU5500000001", "CEU5500000011", "531120", "Lessors of Nonresidential Buildings"),
    "property":      ("CEU5500000001", "CEU5500000011", "53", "Real Estate & Rental"),
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

# State abbreviation → 2-digit FIPS code
# QCEW state area FIPS = "{fips}000" (e.g. Florida = "12000")
_STATE_FIPS: Dict[str, str] = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}

# Full state names for source citations
_STATE_NAMES: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def _state_area_fips(state_abbr: str) -> Optional[str]:
    """Return the QCEW area FIPS code for the given state abbreviation (e.g. 'FL' → '12000')."""
    if not state_abbr:
        return None
    fips2 = _STATE_FIPS.get(state_abbr.upper().strip())
    return f"{fips2}000" if fips2 else None

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

    Requires BLS_API_KEY to be set; returns None gracefully when the key is absent
    or when QCEW endpoint is unavailable. No CES fallback — all citations are QCEW.
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

        # Resolve industry name from NAICS code mapping if not provided
        for keyword, (_, _, naics, name) in BUSINESS_TO_CES.items():
            if naics == naics_code:
                industry_name = industry_name or name
                break

        cache_key = f"bls_qcew_{naics_code}"
        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_qcew(naics_code, industry_name)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def get_industry_data_for_business(
        self,
        business_type: str,
        db: Optional["Session"] = None,
        state: Optional[str] = None,
    ) -> Optional[IndustryLaborData]:
        """Main entry point: looks up the NAICS code from the business type string
        and returns IndustryLaborData, or None if not mapped or key absent.

        When ``state`` is a two-letter abbreviation (e.g. "FL"), the method fetches
        state-level QCEW data first and falls back to national data automatically.
        """
        if not self._is_configured():
            logger.debug("[BLS] BLS_API_KEY not configured — skipping QCEW fetch")
            return None

        mapping = self.get_ces_for_business(business_type)
        if not mapping:
            logger.debug(f"[BLS] No mapping for business type: '{business_type}'")
            return None

        _, _, naics_code, industry_name = mapping
        state_upper = state.upper().strip() if state else None
        cache_key = f"bls_qcew_{naics_code}_{state_upper}" if state_upper else f"bls_qcew_{naics_code}"

        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_qcew(naics_code, industry_name, state_abbr=state_upper)

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, naics_code)

        return result

    async def _fetch_qcew(
        self,
        naics_code: str,
        industry_name: str,
        state_abbr: Optional[str] = None,
    ) -> Optional[IndustryLaborData]:
        """Fetch employment, wages, and establishment count from the QCEW Open Data API.

        URL: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics_code}.json
        The endpoint returns data for all geographies; we filter to the requested state
        area FIPS when ``state_abbr`` is provided, falling back to national if unavailable.
        Returns None on any HTTP/parse failure.
        """
        year, qtr = _latest_complete_qcew_period()
        quarters_to_try: List[Tuple[int, str]] = [(year, qtr)]
        if qtr != "a":
            quarters_to_try.append((year, "a"))
        quarters_to_try.append((year - 1, "a"))

        target_area_fips: Optional[str] = _state_area_fips(state_abbr) if state_abbr else None
        state_name: Optional[str] = _STATE_NAMES.get(state_abbr.upper()) if state_abbr else None

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

            # Try state-level first, then fall back to national
            if target_area_fips:
                result = self._parse_qcew_response(
                    raw, naics_code, industry_name, try_year, try_qtr,
                    area_fips_filter=target_area_fips, state_name=state_name,
                )
                if result is not None:
                    logger.info(
                        f"[BLS] QCEW {naics_code} {state_abbr} FY{try_year} Q{try_qtr}: "
                        f"${result.avg_weekly_wage:,.2f}/wk (state-level)"
                    )
                    return result
                logger.debug(
                    f"[BLS] State-level data not found for {naics_code}/{state_abbr} "
                    f"({try_year} Q{try_qtr}), falling back to national"
                )

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
        area_fips_filter: Optional[str] = None,
        state_name: Optional[str] = None,
    ) -> Optional[IndustryLaborData]:
        """Parse the QCEW API JSON response into IndustryLaborData.

        When ``area_fips_filter`` is provided (e.g. "12000" for Florida), the method
        selects the matching state-level record.  Without it, it selects the national total.
        Returns None if no matching record is found or on parse error.
        """
        # QCEW API returns a dict with area-code keys, each containing a list of records.
        # For national data, the key is "US000" or similar; state keys are "12000", etc.
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

            target_record = None

            if area_fips_filter:
                # State-level: match area FIPS exactly; prefer total-all-ownerships
                # agglvl_code 51-55 = state by NAICS depth; own_code 0=total, 5=private
                target_fips = area_fips_filter.upper()
                for rec in records:
                    area = str(rec.get("area_fips", rec.get("areaFips", ""))).upper()
                    own = str(rec.get("own_code", rec.get("ownCode", "")))
                    if area == target_fips and own in ("0", "5"):
                        target_record = rec
                        if own == "0":
                            break
            else:
                # National: prefer US-level total-all-ownerships at industry level
                # own_code: 0=total all, 5=private
                # agglvl_code: 14=national by industry, 13=national 5-digit, 12=national 4-digit
                for rec in records:
                    own = str(rec.get("own_code", rec.get("ownCode", "")))
                    agglvl = str(rec.get("agglvl_code", rec.get("agglvlCode", "")))
                    area = str(rec.get("area_fips", rec.get("areaFips", ""))).upper()
                    if area.startswith("US") or area == "00000":
                        if own in ("0", "5") and agglvl in ("14", "13", "12"):
                            target_record = rec
                            break
                        elif own in ("0", "5"):
                            target_record = rec

            if target_record is None and not area_fips_filter and records:
                target_record = records[0]

            if target_record is None:
                return None

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

            if avg_wage == 0.0:
                return None

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

            # Compose source citation
            if state_name and area_fips_filter:
                year_str = str(year) + (" Annual" if not qtr.isdigit() else f" Q{qtr}")
                period_source = f"BLS OES {state_name} {year_str}"
            else:
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
