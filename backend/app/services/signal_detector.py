import os
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from app.models.opportunity_signal import OpportunitySignal

logger = logging.getLogger(__name__)


class SignalDetector:
    """Monitor public data feeds for high-intent business signals."""

    SIGNAL_SOURCES = {
        "sec_form_d": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=D&company=&dateb=&owner=include&count=100&output=atom",
    }

    def __init__(self, db: Session):
        self.db = db

    def detect_funding_from_sec(self) -> Dict:
        """Monitor SEC Form D (new fundings) via RSS."""
        user_agent = os.getenv(
            "SEC_EDGAR_USER_AGENT", "OppGrid Platform contact@oppgrid.com"
        )
        feed = feedparser.parse(
            self.SIGNAL_SOURCES["sec_form_d"],
            request_headers={"User-Agent": user_agent},
        )
        new_signals = 0
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            company = title.split(" - ")[0] if " - " in title else title
            signal = OpportunitySignal(
                signal_type="funding",
                signal_value={
                    "company_name": company,
                    "filing_type": "Form D",
                    "filing_date": entry.get("updated", ""),
                    "summary": entry.get("summary", "")[:500],
                },
                source_url=entry.get("link", ""),
                confidence_score=0.85,
            )
            self.db.add(signal)
            new_signals += 1
        self.db.commit()
        return {"status": "ok", "new_signals": new_signals}

    def detect_hiring_surge(self, company_name: str, job_board: str = "linkedin") -> Dict:
        """Detect hiring surge by counting job postings. Placeholder for job board API."""
        logger.info(
            f"Hiring surge detection for {company_name} via {job_board} — implementation pending"
        )
        return {"status": "pending", "company": company_name}

    def detect_exec_changes(self, linkedin_url: str) -> Dict:
        """Detect executive changes via Proxycurl."""
        api_key = os.getenv("PROXYCURL_API_KEY")
        if not api_key:
            return {"status": "skipped", "reason": "PROXYCURL_API_KEY not set"}

        url = "https://nubela.co/proxycurl/api/v2/linkedin"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(
                url, params={"url": linkedin_url}, headers=headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return {"status": "ok", "profile": data.get("full_name")}
        except Exception as e:
            logger.error(f"Proxycurl exec change detection failed: {e}")
            return {"status": "error", "error": str(e)}
