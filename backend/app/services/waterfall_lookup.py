import os
import logging
import requests
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.services.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)


class WaterfallLookupService:
    """Multi-tier contact enrichment: try cheapest source first, cascade to next."""

    def __init__(self, db: Session):
        self.db = db
        self.enrichment = EnrichmentService(db)

    def lookup_email(
        self,
        first_name: str,
        last_name: str,
        company_domain: str,
        target_entity: str,
        target_id: int,
    ) -> Dict:
        """Waterfall: Apollo → Lusha → Prospeo."""

        # Tier 1: Apollo (cheapest, $49/mo for 10K credits)
        result = self._apollo_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity,
                target_id=target_id,
                source="apollo",
                field_name="email",
                raw_value=result["email"],
                confidence=0.85,
            )
            return {"source": "apollo", "email": result["email"], "cost_tier": 1}

        # Tier 2: Lusha (mobile/direct dial, $37–49/mo)
        result = self._lusha_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity,
                target_id=target_id,
                source="lusha",
                field_name="email",
                raw_value=result["email"],
                confidence=0.80,
            )
            return {"source": "lusha", "email": result["email"], "cost_tier": 2}

        # Tier 3: Prospeo (pay-as-you-go, ~$0.01/email)
        result = self._prospeo_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity,
                target_id=target_id,
                source="prospeo",
                field_name="email",
                raw_value=result["email"],
                confidence=0.75,
            )
            return {"source": "prospeo", "email": result["email"], "cost_tier": 3}

        return {"source": None, "email": None, "cost_tier": None}

    def _apollo_lookup(
        self, first_name: str, last_name: str, company_domain: str
    ) -> Optional[Dict]:
        api_key = os.getenv("APOLLO_API_KEY")
        if not api_key:
            return None
        try:
            url = "https://api.apollo.io/v1/people/match"
            headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
            payload = {
                "first_name": first_name,
                "last_name": last_name,
                "organization_name": company_domain,
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            person = data.get("person", {})
            return {"email": person.get("email")}
        except Exception as e:
            logger.warning(f"Apollo lookup failed: {e}")
            return None

    def _lusha_lookup(
        self, first_name: str, last_name: str, company_domain: str
    ) -> Optional[Dict]:
        api_key = os.getenv("LUSHA_API_KEY")
        if not api_key:
            return None
        # Lusha API implementation placeholder
        # https://lusha.com/api/
        return None

    def _prospeo_lookup(
        self, first_name: str, last_name: str, company_domain: str
    ) -> Optional[Dict]:
        api_key = os.getenv("PROSPEO_API_KEY")
        if not api_key:
            return None
        # Prospeo API implementation placeholder
        # https://prospeo.io/api
        return None
