import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from app.services.enrichment_service import EnrichmentService
from app.models.opportunity_signal import OpportunitySignal
from app.models.census_demographics import CensusPopulationEstimate

logger = logging.getLogger(__name__)

# State postal code to FIPS mapping
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09",
    "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17",
    "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31",
    "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56",
}

FIPS_TO_STATE = {v: k for k, v in STATE_FIPS.items()}


class GovernmentDataService:
    """Ingest free government/open data sources. Zero cost, Tier 1 compliance."""

    def __init__(self, db: Session):
        self.db = db
        self.enrichment = EnrichmentService(db)

    # ───────────────────────────────────────────────────────────────
    # Existing methods (kept intact)
    # ───────────────────────────────────────────────────────────────

    def ingest_sec_edgar(self, cik: str, target_entity: str, target_id: int) -> Dict:
        """Fetch latest SEC filing for a company."""
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
        try:
            user_agent = os.getenv(
                "SEC_EDGAR_USER_AGENT", "OppGrid Platform contact@oppgrid.com"
            )
            headers = {"User-Agent": user_agent}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            facts = data.get("facts", {}).get("us-gaap", {})
            if "Revenues" in facts:
                latest = facts["Revenues"]["units"]["USD"][-1]
                self.enrichment.stage(
                    target_entity=target_entity,
                    target_id=target_id,
                    source="sec_edgar",
                    field_name="revenue",
                    raw_value=str(latest.get("val")),
                    confidence=1.0,
                    source_url=url,
                )
            return {"status": "ok", "cik": cik}
        except Exception as e:
            logger.error(f"SEC EDGAR ingestion failed for CIK {cik}: {e}")
            return {"status": "error", "error": str(e)}

    def ingest_companies_house(self, company_number: str, target_entity: str, target_id: int) -> Dict:
        """Fetch UK Companies House data. Requires API key in env."""
        api_key = os.getenv("COMPANIES_HOUSE_API_KEY")
        if not api_key:
            logger.warning("COMPANIES_HOUSE_API_KEY not set; skipping")
            return {"status": "skipped"}

        url = f"https://api.company-information.service.gov.uk/company/{company_number}"
        try:
            resp = requests.get(url, auth=(api_key, ""), timeout=30)
            resp.raise_for_status()
            data = resp.json()

            self.enrichment.stage(
                target_entity=target_entity,
                target_id=target_id,
                source="companies_house",
                field_name="company_registration",
                raw_value=data.get("company_name", ""),
                confidence=1.0,
                source_url=url,
            )
            return {"status": "ok", "company_number": company_number}
        except Exception as e:
            logger.error(f"Companies House ingestion failed: {e}")
            return {"status": "error", "error": str(e)}

    def ingest_sam_gov_awards(self, naics_code: str = None, limit: int = 100) -> Dict:
        """Fetch recent US government contract awards from SAM.gov."""
        url = "https://sam.gov/api/prod/opportunities/v1/search"
        try:
            params = {"limit": limit, "sort": "-modifiedDate", "noticeType": "a"}
            if naics_code:
                params["naics"] = naics_code
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            opportunities = data.get("opportunitiesData", [])
            for opp in opportunities:
                signal = OpportunitySignal(
                    signal_type="contract_award",
                    signal_value={
                        "title": opp.get("title"),
                        "agency": opp.get("agency"),
                        "award_amount": opp.get("awardAmount"),
                        "naics": opp.get("naicsCode"),
                    },
                    source_url=opp.get("uiLink"),
                    confidence_score=0.95,
                )
                self.db.add(signal)
            self.db.commit()
            return {"status": "ok", "count": len(opportunities)}
        except Exception as e:
            logger.error(f"SAM.gov ingestion failed: {e}")
            return {"status": "error", "error": str(e)}

    # ───────────────────────────────────────────────────────────────
    # NEW: US Census Bureau ACS 5-year estimates
    # ───────────────────────────────────────────────────────────────

    def bulk_census_ingestion(self, state_code: str) -> Dict:
        """
        Fetch ACS 5-year demographic data for all places in a state.
        Creates RawEnrichment staging records and CensusPopulationEstimate rows.
        """
        state_fips = STATE_FIPS.get(state_code.upper())
        if not state_fips:
            return {"status": "error", "error": f"Invalid state_code: {state_code}"}

        api_key = os.getenv("CENSUS_API_KEY", "")
        fields = "NAME,B01003_001E,B19013_001E,B25077_001E,B25003_001E,B25003_002E,B08303_001E,B15003_001E"
        url = (
            f"https://api.census.gov/data/2023/acs/acs5"
            f"?get={fields}&for=place:*&in=state:{state_fips}"
        )
        if api_key:
            url += f"&key={api_key}"

        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if not data or len(data) < 2:
                return {"status": "ok", "count": 0, "source": "census_acs5"}

            headers = data[0]
            rows = data[1:]
            staged = 0
            census_records = 0

            for row in rows:
                record = dict(zip(headers, row))
                place_name = record.get("NAME", "")
                population = self._safe_int(record.get("B01003_001E"))
                median_income = self._safe_int(record.get("B19013_001E"))
                median_home_value = self._safe_int(record.get("B25077_001E"))
                total_housing = self._safe_int(record.get("B25003_001E"))
                owner_occupied = self._safe_int(record.get("B25003_002E"))
                commute_time = self._safe_int(record.get("B08303_001E"))
                education_total = self._safe_int(record.get("B15003_001E"))
                place_fips = record.get("place", "")

                # Skip places with zero population
                if not population:
                    continue

                # 1. Stage enrichment record (aggregated JSON)
                self.enrichment.stage(
                    target_entity="census_place",
                    target_id=0,  # generic geography entity
                    source="census_acs5",
                    field_name="demographic_snapshot",
                    raw_value=str(record),
                    confidence=0.95,
                    source_url=url,
                    parsed_value={
                        "state_code": state_code.upper(),
                        "state_fips": state_fips,
                        "place_fips": place_fips,
                        "place_name": place_name,
                        "population": population,
                        "median_income": median_income,
                        "median_home_value": median_home_value,
                        "total_housing": total_housing,
                        "owner_occupied": owner_occupied,
                        "commute_time": commute_time,
                        "education_total": education_total,
                    },
                )
                staged += 1

                # 2. Upsert CensusPopulationEstimate
                existing = (
                    self.db.query(CensusPopulationEstimate)
                    .filter(
                        CensusPopulationEstimate.state_fips == state_fips,
                        CensusPopulationEstimate.place_fips == place_fips,
                        CensusPopulationEstimate.year == 2023,
                    )
                    .first()
                )
                if existing:
                    existing.population = population
                    existing.population_estimate = population
                    existing.median_income = median_income
                    existing.demographics_snapshot = {
                        "median_home_value": median_home_value,
                        "total_housing": total_housing,
                        "owner_occupied": owner_occupied,
                        "commute_time": commute_time,
                        "education_total": education_total,
                        "place_name": place_name,
                    }
                    existing.fetched_at = datetime.utcnow()
                else:
                    estimate = CensusPopulationEstimate(
                        state_fips=state_fips,
                        place_fips=place_fips,
                        geography_name=place_name,
                        geography_type="place",
                        year=2023,
                        population=population,
                        population_estimate=population,
                        median_income=median_income,
                        demographics_snapshot={
                            "median_home_value": median_home_value,
                            "total_housing": total_housing,
                            "owner_occupied": owner_occupied,
                            "commute_time": commute_time,
                            "education_total": education_total,
                            "place_name": place_name,
                        },
                        source_api="Census ACS5",
                    )
                    self.db.add(estimate)
                census_records += 1

                # Batch commit every 100 records to avoid huge transactions
                if census_records % 100 == 0:
                    self.db.commit()

            self.db.commit()
            logger.info(
                f"Census ACS5 ingestion complete for {state_code}: "
                f"{staged} staged, {census_records} census records"
            )
            return {
                "status": "ok",
                "count": staged,
                "census_records": census_records,
                "source": "census_acs5",
                "state_code": state_code.upper(),
            }
        except Exception as e:
            logger.error(f"Census ACS5 ingestion failed for {state_code}: {e}")
            return {"status": "error", "error": str(e)}

    # ───────────────────────────────────────────────────────────────
    # NEW: BLS employment / unemployment / CPI / wage data
    # ───────────────────────────────────────────────────────────────

    def bulk_bls_ingestion(self, state_code: str) -> Dict:
        """
        Fetch BLS employment, unemployment, CPI, and wage data for a state.
        No API key required for <25 series / <500 requests/day.
        """
        state_fips = STATE_FIPS.get(state_code.upper())
        if not state_fips:
            return {"status": "error", "error": f"Invalid state_code: {state_code}"}

        # BLS Local Area Unemployment series IDs
        unemployment_series = f"LAUST{state_fips}0000000003"
        employment_series = f"LAUST{state_fips}0000000004"
        # Wage series: all-employment avg weekly earnings (statewide)
        wage_series = f"CES{state_fips}0000000003"
        # National CPI
        cpi_series = "CUUR0000SA0"

        series_list = [unemployment_series, employment_series, wage_series, cpi_series]

        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        payload = {
            "seriesid": series_list,
            "startyear": str(datetime.utcnow().year - 2),
            "endyear": str(datetime.utcnow().year),
            "registrationkey": os.getenv("BLS_API_KEY", ""),
        }

        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("Results", {}).get("series", [])
            staged = 0
            signals = 0

            for series in results:
                series_id = series.get("seriesID", "")
                item_data = series.get("data", [])
                if not item_data:
                    continue

                # Take the most recent data point
                latest = item_data[0]
                value = latest.get("value")
                period = latest.get("periodName", "")
                year = latest.get("year", "")
                month = period if period else ""

                # Determine metric type from series ID suffix
                if series_id.endswith("0003") and not series_id.startswith("CES"):
                    metric = "unemployment_rate"
                    field_name = "unemployment_rate"
                elif series_id.endswith("0004"):
                    metric = "employment_level"
                    field_name = "employment"
                elif series_id.startswith("CES"):
                    metric = "avg_weekly_earnings"
                    field_name = "wages"
                elif series_id == "CUUR0000SA0":
                    metric = "cpi_all_items"
                    field_name = "cpi"
                else:
                    metric = "bls_metric"
                    field_name = "bls_data"

                # Stage enrichment
                self.enrichment.stage(
                    target_entity="bls_state",
                    target_id=0,
                    source="bls_api",
                    field_name=field_name,
                    raw_value=str(value),
                    confidence=0.95,
                    source_url=url,
                    parsed_value={
                        "state_code": state_code.upper(),
                        "state_fips": state_fips,
                        "metric": metric,
                        "series_id": series_id,
                        "value": value,
                        "year": year,
                        "month": month,
                        "period": period,
                    },
                )
                staged += 1

                # Create signal for unemployment rate (market indicator)
                if metric == "unemployment_rate":
                    try:
                        rate_val = float(value)
                    except (TypeError, ValueError):
                        rate_val = None
                    if rate_val is not None:
                        signal = OpportunitySignal(
                            signal_type="economic_indicator",
                            signal_value={
                                "indicator": "unemployment_rate",
                                "state_code": state_code.upper(),
                                "state_fips": state_fips,
                                "rate": rate_val,
                                "year": year,
                                "month": month,
                                "source": "bls_api",
                            },
                            source_url=url,
                            confidence_score=0.95,
                        )
                        self.db.add(signal)
                        signals += 1

            self.db.commit()
            logger.info(
                f"BLS ingestion complete for {state_code}: {staged} staged, {signals} signals"
            )
            return {
                "status": "ok",
                "count": staged,
                "signals": signals,
                "source": "bls_api",
                "state_code": state_code.upper(),
            }
        except Exception as e:
            logger.error(f"BLS ingestion failed for {state_code}: {e}")
            return {"status": "error", "error": str(e)}

    # ───────────────────────────────────────────────────────────────
    # NEW: USASpending.gov contract awards by state
    # ───────────────────────────────────────────────────────────────

    def ingest_usaspending_by_state(self, state_code: str, limit: int = 100) -> Dict:
        """
        Fetch federal contract awards by state from USASpending.gov.
        Creates OpportunitySignal records for contract awards.
        """
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        payload = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],  # contracts
                "place_of_performance_locations": [
                    {
                        "country": "USA",
                        "state": state_code.upper(),
                    }
                ],
                "time_period": [
                    {
                        "start_date": f"{datetime.utcnow().year - 1}-01-01",
                        "end_date": f"{datetime.utcnow().year}-12-31",
                    }
                ],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Start Date",
                "End Date",
                "Award Amount",
                "Awarding Agency",
                "Awarding Sub Agency",
                "Contract Award Type",
                "Funding Agency",
                "Place of Performance State Code",
                "NAICS",
                "Description",
            ],
            "sort": "Award Amount",
            "order": "desc",
            "limit": limit,
            "page": 1,
        }

        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            awards = data.get("results", [])
            staged = 0
            signals = 0

            for award in awards:
                award_id = award.get("Award ID", "")
                recipient = award.get("Recipient Name", "")
                amount = award.get("Award Amount", "")
                agency = award.get("Awarding Agency", "")
                sub_agency = award.get("Awarding Sub Agency", "")
                award_date = award.get("Start Date", "")
                naics = award.get("NAICS", "")
                description = award.get("Description", "")

                # Stage enrichment
                self.enrichment.stage(
                    target_entity="usaspending_award",
                    target_id=0,
                    source="usaspending",
                    field_name="contract_award",
                    raw_value=str(amount),
                    confidence=0.90,
                    source_url=url,
                    parsed_value={
                        "state_code": state_code.upper(),
                        "award_id": award_id,
                        "recipient": recipient,
                        "amount": amount,
                        "agency": agency,
                        "sub_agency": sub_agency,
                        "award_date": award_date,
                        "naics": naics,
                        "description": description,
                    },
                )
                staged += 1

                # Create OpportunitySignal
                try:
                    amount_val = float(amount) if amount else 0.0
                except (TypeError, ValueError):
                    amount_val = 0.0

                signal = OpportunitySignal(
                    signal_type="federal_contract_award",
                    signal_value={
                        "award_id": award_id,
                        "recipient": recipient,
                        "amount": amount_val,
                        "agency": agency,
                        "sub_agency": sub_agency,
                        "award_date": award_date,
                        "naics": naics,
                        "description": description,
                        "state_code": state_code.upper(),
                        "source": "usaspending",
                    },
                    source_url=url,
                    confidence_score=0.90,
                )
                self.db.add(signal)
                signals += 1

            self.db.commit()
            logger.info(
                f"USASpending ingestion complete for {state_code}: {staged} staged, {signals} signals"
            )
            return {
                "status": "ok",
                "count": staged,
                "signals": signals,
                "source": "usaspending",
                "state_code": state_code.upper(),
            }
        except Exception as e:
            logger.error(f"USASpending ingestion failed for {state_code}: {e}")
            return {"status": "error", "error": str(e)}

    # ───────────────────────────────────────────────────────────────
    # NEW: SBA loan data ingestion
    # ───────────────────────────────────────────────────────────────

    def ingest_sba_loans(self, state_code: str) -> Dict:
        """
        Fetch SBA loan data. Uses the SBA public API where available,
        falling back to SBA.gov static data if the API is unavailable.
        """
        # Try the SBA public API first (loans/7a endpoint pattern)
        api_url = f"https://api.sba.gov/loans/7a?state={state_code.upper()}"
        try:
            resp = requests.get(api_url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return self._process_sba_api_data(state_code, data, api_url)
        except Exception as e:
            logger.warning(f"SBA API endpoint unavailable for {state_code}: {e}")

        # Fallback: use static SBA loan program data as enrichment signals
        return self._ingest_sba_static_data(state_code)

    def _process_sba_api_data(self, state_code: str, data: Any, source_url: str) -> Dict:
        """Process SBA API response data."""
        loans = data if isinstance(data, list) else data.get("loans", [])
        staged = 0
        signals = 0

        for loan in loans:
            loan_amount = loan.get("loan_amount", loan.get("amount", "0"))
            borrower = loan.get("borrower_name", loan.get("recipient", "Unknown"))
            lender = loan.get("lender_name", "Unknown")
            approval_date = loan.get("approval_date", loan.get("date", ""))
            naics = loan.get("naics_code", loan.get("naics", ""))

            self.enrichment.stage(
                target_entity="sba_loan",
                target_id=0,
                source="sba_api",
                field_name="sba_7a_loan",
                raw_value=str(loan_amount),
                confidence=0.85,
                source_url=source_url,
                parsed_value={
                    "state_code": state_code.upper(),
                    "borrower": borrower,
                    "lender": lender,
                    "loan_amount": loan_amount,
                    "approval_date": approval_date,
                    "naics": naics,
                },
            )
            staged += 1

            try:
                amount_val = float(loan_amount) if loan_amount else 0.0
            except (TypeError, ValueError):
                amount_val = 0.0

            signal = OpportunitySignal(
                signal_type="sba_loan",
                signal_value={
                    "borrower": borrower,
                    "lender": lender,
                    "amount": amount_val,
                    "approval_date": approval_date,
                    "naics": naics,
                    "state_code": state_code.upper(),
                    "source": "sba_api",
                },
                source_url=source_url,
                confidence_score=0.85,
            )
            self.db.add(signal)
            signals += 1

        self.db.commit()
        logger.info(
            f"SBA API ingestion complete for {state_code}: {staged} staged, {signals} signals"
        )
        return {
            "status": "ok",
            "count": staged,
            "signals": signals,
            "source": "sba_api",
            "state_code": state_code.upper(),
        }

    def _ingest_sba_static_data(self, state_code: str) -> Dict:
        """Fallback: ingest static SBA loan program data as enrichment."""
        from app.services.sba_service import SBA_LOAN_PROGRAMS

        staged = 0
        for program in SBA_LOAN_PROGRAMS:
            self.enrichment.stage(
                target_entity="sba_loan_program",
                target_id=0,
                source="sba_static",
                field_name="loan_program",
                raw_value=program.get("name", ""),
                confidence=0.80,
                source_url=program.get("link", "https://www.sba.gov"),
                parsed_value={
                    "state_code": state_code.upper(),
                    "program_name": program.get("name"),
                    "category": program.get("category"),
                    "amount": program.get("amount"),
                    "description": program.get("description"),
                    "uses": program.get("uses"),
                    "terms": program.get("terms"),
                },
            )
            staged += 1

        self.db.commit()
        logger.info(
            f"SBA static ingestion complete for {state_code}: {staged} staged"
        )
        return {
            "status": "ok",
            "count": staged,
            "source": "sba_static",
            "state_code": state_code.upper(),
        }

    # ───────────────────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert a string/None to int, returning None on failure."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    # ───────────────────────────────────────────────────────────────
    # Orchestrator: run all new government ingestions for a state
    # ───────────────────────────────────────────────────────────────

    def ingest_all_for_state(self, state_code: str) -> Dict:
        """
        Run all government data ingestion methods for a given state.
        Designed to be called from the scheduler.
        """
        results = {}
        errors = []

        for method_name, method in [
            ("census", self.bulk_census_ingestion),
            ("bls", self.bulk_bls_ingestion),
            ("usaspending", self.ingest_usaspending_by_state),
            ("sba_loans", self.ingest_sba_loans),
        ]:
            try:
                results[method_name] = method(state_code)
            except Exception as e:
                logger.error(f"{method_name} ingestion failed for {state_code}: {e}")
                errors.append(f"{method_name}: {str(e)}")
                results[method_name] = {"status": "error", "error": str(e)}

        return {
            "status": "partial" if errors else "ok",
            "state_code": state_code.upper(),
            "results": results,
            "errors": errors,
        }
