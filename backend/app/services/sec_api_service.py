"""
SEC-API Service — Fetches parsed 10-K financials for public company comps via sec-api.io.

Maps each OppGrid business type to a list of relevant public company tickers, then
fetches the latest 10-K filing for up to 3 comps and calculates average operating margin.

Endpoints (sec-api.io):
  POST https://api.sec-api.io            — Query filings (Authorization header)
  GET  https://api.sec-api.io/xbrl-to-json  — Parse XBRL financials (token param)

Industry → ticker mapping covers 14 verticals (original 8 + 6 expanded in Task #29):
  Original: self storage, fitness/gym, car wash, restaurant, coffee, pet, dental
  Expanded: hotel/hospitality, pharmacy, grocery, auto repair, daycare/childcare,
            real estate/coworking
Results are cached in LocationAnalysisCache for 30 days.
Returns None gracefully when SEC_API_KEY is absent or no comps are mapped.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, TYPE_CHECKING

import httpx

from app.models.report_context import IndustryBenchmarks, PublicCompData

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SEC_API_BASE = "https://api.sec-api.io"
CACHE_TTL_DAYS = 30

# Business type keyword → list of public company tickers (most relevant first)
INDUSTRY_COMPS: Dict[str, List[str]] = {
    # ── Original 8 verticals ──────────────────────────────────────────────
    "self_storage":  ["PSA", "EXR", "CUBE", "LSI", "NSA"],
    "self storage":  ["PSA", "EXR", "CUBE", "LSI", "NSA"],
    "fitness":       ["PLNT", "XPOF"],
    "gym":           ["PLNT", "XPOF"],
    "yoga":          ["PLNT", "XPOF"],
    "car wash":      ["WASH", "DRVN"],
    "car_wash":      ["WASH", "DRVN"],
    "restaurant":    ["MCD", "YUM", "QSR", "CMG"],
    "cafe":          ["SBUX", "BROS", "MCD"],
    "coffee":        ["SBUX", "BROS"],
    "coffee shop":   ["SBUX", "BROS"],
    "pet":           ["CHWY", "WOOF", "TRUP"],
    "pet grooming":  ["CHWY", "WOOF", "TRUP"],
    "pet services":  ["CHWY", "WOOF", "TRUP"],
    "dental":        ["PDCO", "HSIC"],
    # ── Expanded verticals (Task #29) ─────────────────────────────────────
    "hotel":         ["HLT", "MAR", "H", "STAY"],
    "motel":         ["HLT", "MAR", "H", "STAY"],
    "hospitality":   ["HLT", "MAR", "H", "STAY"],
    "pharmacy":      ["CVS", "WBA", "RAD"],
    "drug store":    ["CVS", "WBA", "RAD"],
    "drugstore":     ["CVS", "WBA", "RAD"],
    "health":        ["CVS", "WBA", "UNH"],
    "grocery":       ["KR", "ACI", "SFM"],
    "supermarket":   ["KR", "ACI", "SFM"],
    "food store":    ["KR", "ACI", "SFM"],
    "auto repair":   ["AZO", "ORLY"],
    "auto_repair":   ["AZO", "ORLY"],
    "automotive":    ["AZO", "ORLY", "DRVN"],
    "mechanic":      ["AZO", "ORLY"],
    "daycare":       ["BFAM", "LRN"],
    "child care":    ["BFAM", "LRN"],
    "childcare":     ["BFAM", "LRN"],
    "preschool":     ["BFAM", "LRN"],
    "real estate":   ["CBRE", "JLL", "IWG"],
    "coworking":     ["CBRE", "JLL", "IWG"],
    "office space":  ["CBRE", "JLL", "IWG"],
    "property":      ["CBRE", "JLL", "IWG"],
}

MAX_COMPS = 3  # Limit SEC API calls per report


class SECAPIService:
    """Fetches and caches industry benchmarks from SEC 10-K filings."""

    def __init__(self):
        self.api_key = os.environ.get("SEC_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_comps_for_business(self, business_type: str) -> List[str]:
        """Map a business type string to relevant public company tickers."""
        if not business_type:
            return []
        lower = business_type.lower()
        for keyword, tickers in INDUSTRY_COMPS.items():
            if keyword in lower:
                return tickers
        return []

    async def get_latest_10k(self, ticker: str) -> Optional[Dict]:
        """Fetch the most recent 10-K filing metadata for a ticker."""
        query = {
            "query": {
                "query_string": {
                    "query": f'ticker:{ticker} AND formType:"10-K"'
                }
            },
            "from": 0,
            "size": 1,
            "sort": [{"filedAt": {"order": "desc"}}],
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    SEC_API_BASE,
                    json=query,
                    headers={"Authorization": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()
                filings = data.get("filings") or data.get("hits", {}).get("hits", [])
                if filings:
                    filing = filings[0]
                    # Handle both direct and nested formats
                    if "_source" in filing:
                        filing = filing["_source"]
                    return filing
                return None
        except Exception as exc:
            logger.warning(f"[SEC] 10-K fetch failed for {ticker}: {exc}")
            return None

    async def get_financials(self, accession_no: str) -> Optional[Dict]:
        """Parse XBRL financials for a given accession number."""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{SEC_API_BASE}/xbrl-to-json",
                    params={"accession-no": accession_no, "token": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning(f"[SEC] XBRL fetch failed for {accession_no}: {exc}")
            return None

    async def get_industry_benchmarks(
        self,
        business_type: str,
        db: Optional["Session"] = None,
    ) -> Optional[IndustryBenchmarks]:
        """
        Fetch financials for the top 3 public comps for the given business type
        and return aggregated IndustryBenchmarks, or None if no comps are mapped
        or SEC_API_KEY is not configured.
        """
        if not self.is_configured:
            logger.debug("[SEC] SEC_API_KEY not configured — skipping benchmarks")
            return None

        tickers = self.get_comps_for_business(business_type)
        if not tickers:
            logger.debug(f"[SEC] No comps mapped for business type: '{business_type}'")
            return None

        cache_key = f"sec_benchmarks_{business_type.lower().replace(' ', '_')[:40]}"

        if db is not None:
            cached = self._read_cache(db, cache_key)
            if cached is not None:
                return cached

        result = await self._fetch_live(tickers[:MAX_COMPS])

        if result is not None and db is not None:
            self._write_cache(db, cache_key, result, business_type)

        return result

    async def _fetch_live(self, tickers: List[str]) -> Optional[IndustryBenchmarks]:
        """Fetch 10-K financials for each ticker and assemble IndustryBenchmarks."""
        import asyncio

        async def fetch_one(ticker: str) -> Optional[PublicCompData]:
            filing = await self.get_latest_10k(ticker)
            if not filing:
                return None

            accession_no = filing.get("accessionNo") or filing.get("accession_no")
            if not accession_no:
                return None

            financials = await self.get_financials(accession_no)
            if not financials:
                return None

            return self._parse_comp(ticker, filing, financials)

        comps_raw = await asyncio.gather(
            *[fetch_one(t) for t in tickers], return_exceptions=True
        )
        comps: List[PublicCompData] = [
            c for c in comps_raw if isinstance(c, PublicCompData)
        ]

        if not comps:
            logger.warning(f"[SEC] No comp financials retrieved for tickers: {tickers}")
            return None

        valid_margins = [c.operating_margin for c in comps if c.operating_margin is not None]
        avg_margin = sum(valid_margins) / len(valid_margins) if valid_margins else 0.0

        logger.info(
            f"[SEC] Benchmarks built: {len(comps)} comps, "
            f"avg operating margin {avg_margin:.1%}"
        )
        return IndustryBenchmarks(
            avg_operating_margin=avg_margin,
            public_comps=comps,
            source="SEC 10-K filings via sec-api.io",
        )

    @staticmethod
    def _parse_comp(ticker: str, filing: dict, financials: dict) -> Optional[PublicCompData]:
        """Extract revenue, operating income from XBRL JSON and build PublicCompData."""
        try:
            company_name = (
                filing.get("companyName") or filing.get("companyNameLong")
                or filing.get("company_name") or ticker
            )
            # Derive fiscal year from periodOfReport (e.g. "2025-12-31") or fiscalYear field
            fiscal_year = filing.get("fiscalYear") or filing.get("fiscal_year") or 0
            if not fiscal_year or fiscal_year == "None":
                period = filing.get("periodOfReport", "") or ""
                try:
                    fiscal_year = int(period[:4])
                except (ValueError, TypeError):
                    fiscal_year = datetime.utcnow().year - 1
            else:
                try:
                    fiscal_year = int(str(fiscal_year)[:4])
                except (ValueError, TypeError):
                    fiscal_year = datetime.utcnow().year - 1

            # sec-api.io XBRL JSON structure:
            # financials["StatementsOfIncome"]["Revenues"] = [
            #   {"decimals": "-3", "unitRef": "usd", "period": {...}, "value": "3840000"}
            # ]
            def extract_xbrl_value(val) -> Optional[float]:
                """Parse a single XBRL field value (scalar or list of period entries)."""
                if val is None:
                    return None
                # List of period observations — take the one with the longest period (annual)
                if isinstance(val, list):
                    best = None
                    best_days = -1
                    for item in val:
                        if not isinstance(item, dict):
                            continue
                        raw = item.get("value")
                        if raw is None or raw == "":
                            continue
                        # Prefer annual (startDate→endDate span of ~365 days)
                        period = item.get("period", {})
                        start = period.get("startDate", "")
                        end = period.get("endDate", "")
                        days = 0
                        if start and end:
                            try:
                                from datetime import datetime as _dt
                                days = (_dt.strptime(end, "%Y-%m-%d") - _dt.strptime(start, "%Y-%m-%d")).days
                            except Exception:
                                days = 0
                        if days > best_days:
                            best_days = days
                            best = raw
                    if best is None:
                        return None
                    try:
                        return float(best)
                    except (ValueError, TypeError):
                        return None
                # Scalar
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            def extract(data: dict, *keys) -> Optional[float]:
                """Search for a financial metric across all known income statement sections."""
                for section in [None, "StatementsOfIncome", "IncomeStatement",
                                "ConsolidatedStatementsOfOperations",
                                "StatementsOfOperations"]:
                    stmt = data.get(section, {}) if section else data
                    for k in keys:
                        result = extract_xbrl_value(stmt.get(k))
                        if result is not None:
                            return result
                return None

            revenue = extract(
                financials,
                "Revenues", "Revenue", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet", "RevenueFromContractWithCustomer",
                "RealEstateRevenueNet", "TotalRevenues",
            )
            operating_income = extract(
                financials,
                "OperatingIncomeLoss", "OperatingIncome",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
            )
            net_income = extract(
                financials,
                "NetIncomeLoss", "NetIncome", "ProfitLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
            )

            if revenue is None or operating_income is None:
                logger.debug(
                    f"[SEC] Could not extract revenue/operating_income for {ticker}"
                )
                return None

            return PublicCompData(
                ticker=ticker,
                company_name=company_name,
                fiscal_year=fiscal_year,
                revenue=revenue,
                operating_income=operating_income,
                net_income=net_income,
                source=f"SEC 10-K FY{fiscal_year}",
            )
        except Exception as exc:
            logger.warning(f"[SEC] Parse error for {ticker}: {exc}")
            return None

    # ── Cache helpers ────────────────────────────────────────────────────────

    def _read_cache(self, db: "Session", cache_key: str) -> Optional[IndustryBenchmarks]:
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
            logger.debug(f"[SEC] Cache read failed: {exc}")
        return None

    def _write_cache(
        self,
        db: "Session",
        cache_key: str,
        data: IndustryBenchmarks,
        business_type: str,
    ) -> None:
        try:
            from app.models.location_analysis_cache import LocationAnalysisCache
            payload = self._serialize(data)
            expires = datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS)
            btype_short = business_type[:50]

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
                    business_type=btype_short,
                    market_metrics=payload,
                    expires_at=expires,
                    hit_count=1,
                )
                db.add(row)
            db.commit()
            logger.debug(f"[SEC] Cache written for {cache_key}")
        except Exception as exc:
            logger.warning(f"[SEC] Cache write failed: {exc}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def _serialize(data: IndustryBenchmarks) -> dict:
        comps = []
        for c in data.public_comps or []:
            comps.append({
                "ticker": c.ticker,
                "company_name": c.company_name,
                "fiscal_year": c.fiscal_year,
                "revenue": c.revenue,
                "operating_income": c.operating_income,
                "net_income": c.net_income,
                "source": c.source,
            })
        return {
            "_type": "sec_industry_benchmarks",
            "avg_operating_margin": data.avg_operating_margin,
            "avg_revenue_growth_3yr": data.avg_revenue_growth_3yr,
            "public_comps": comps,
            "source": data.source,
        }

    @staticmethod
    def _deserialize(payload: dict) -> Optional[IndustryBenchmarks]:
        if not isinstance(payload, dict) or payload.get("_type") != "sec_industry_benchmarks":
            return None
        try:
            comps = []
            for c in payload.get("public_comps") or []:
                comps.append(PublicCompData(
                    ticker=c["ticker"],
                    company_name=c["company_name"],
                    fiscal_year=int(c["fiscal_year"]),
                    revenue=float(c["revenue"]),
                    operating_income=float(c["operating_income"]),
                    net_income=float(c["net_income"]) if c.get("net_income") is not None else None,
                    source=c.get("source", "SEC 10-K"),
                ))
            return IndustryBenchmarks(
                avg_operating_margin=float(payload["avg_operating_margin"]),
                avg_revenue_growth_3yr=payload.get("avg_revenue_growth_3yr"),
                public_comps=comps,
                source=payload.get("source", "SEC 10-K filings via sec-api.io"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(f"[SEC] Deserialize failed: {exc}")
            return None
