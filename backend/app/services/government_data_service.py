import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.services.enrichment_service import EnrichmentService
from app.models.opportunity_signal import OpportunitySignal

logger = logging.getLogger(__name__)


class GovernmentDataService:
    """Ingest free government/open data sources. Zero cost, Tier 1 compliance."""

    def __init__(self, db: Session):
        self.db = db
        self.enrichment = EnrichmentService(db)

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
