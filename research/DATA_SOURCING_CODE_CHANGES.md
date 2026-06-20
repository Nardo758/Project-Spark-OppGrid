# DATA SOURCING — CODE CHANGE SPECIFICATION

## Scope
Concrete code changes mapped to the OppGrid FastAPI monolith + HTML frontend. Every file, model, router, and migration listed with purpose and relationship to existing code.

---

## Phase 0: Infrastructure — New Models & Migrations (Must Ship First)

### 1. New Model: `RawEnrichment` (Staging Layer)
**Purpose:** The Practitioner's "never let enrichment write to production fields" rule. Every external data source writes here first. Only promoted records reach production tables.

**New file:** `backend/app/models/raw_enrichment.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"

class RawEnrichment(Base):
    __tablename__ = "raw_enrichment"

    id = Column(Integer, primary_key=True, index=True)
    target_entity = Column(String(50), nullable=False, index=True)  # 'company', 'lead', 'opportunity'
    target_id = Column(Integer, nullable=False, index=True)         # FK to production entity (not enforced for flexibility)
    source = Column(String(50), nullable=False, index=True)       # 'sec_edgar', 'companies_house', 'apollo', 'lusha', 'crustdata', 'predictleads', 'user_generated'
    source_url = Column(Text, nullable=True)
    field_name = Column(String(100), nullable=False, index=True)    # 'headcount', 'revenue', 'email', 'job_title', 'funding_round'
    raw_value = Column(Text, nullable=True)
    parsed_value = Column(JSONB, nullable=True)                     # structured variant if applicable
    confidence_score = Column(Float, default=0.0)                  # 0.00–1.00
    enriched_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)     # computed: enriched_at + field_decay_ttl
    status = Column(String(20), default="pending", nullable=False, index=True)
    
    # Audit trail
    promoted_at = Column(DateTime(timezone=True), nullable=True)
    promoted_by = Column(String(50), nullable=True)                # 'system', 'admin', 'user_id:123'
    rejection_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Alembic migration:** `alembic/versions/20260620_0001_add_raw_enrichment.py`

**Update `models/__init__.py`:** Add `RawEnrichment` import and `__all__` export.

---

### 2. New Model: `OpportunitySignal` (Timing Layer)
**Purpose:** The Economist's "value is in timing, not identity" — real-time event detection that triggers outreach before competitors.

**New file:** `backend/app/models/opportunity_signal.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class OpportunitySignal(Base):
    __tablename__ = "opportunity_signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=True, index=True)         # FK to company/lead entity (if known)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True, index=True)
    
    signal_type = Column(String(50), nullable=False, index=True)    # 'funding', 'hiring_surge', 'exec_change', 'contract_award', 'patent_filing', 'new_office'
    signal_value = Column(JSON, nullable=False)                     # structured payload
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source_url = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    
    # Pairing with contact (waterfall lookup)
    paired_contact_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    paired_at = Column(DateTime(timezone=True), nullable=True)
    contact_lookup_source = Column(String(50), nullable=True)       # 'apollo', 'lusha', 'prospeo'
    
    # Action tracking
    actioned = Column(Boolean, default=False, index=True)
    actioned_by_user_id = Column(Integer, nullable=True)
    actioned_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Alembic migration:** `alembic/versions/20260620_0002_add_opportunity_signals.py`

**Update `models/__init__.py`:** Add `OpportunitySignal` import and `__all__` export.

**Update `models/opportunity.py`:** Add relationship:
```python
signals = relationship("OpportunitySignal", back_populates="opportunity")
```
**Update `models/lead.py`:** Add relationship:
```python
signals = relationship("OpportunitySignal", back_populates="paired_contact")
```

---

### 3. New Model: `DataQualityAudit` (Academic's Credible Commitment)
**Purpose:** Third-party-auditable quality metrics published to users. Solves the "lemons problem" by making quality verifiable.

**New file:** `backend/app/models/data_quality_audit.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from app.db.database import Base

class DataQualityAudit(Base):
    __tablename__ = "data_quality_audits"

    id = Column(Integer, primary_key=True, index=True)
    dataset = Column(String(50), nullable=False, index=True)       # 'leads', 'opportunities', 'companies', 'signals'
    check_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_records = Column(Integer, default=0)
    stale_records = Column(Integer, default=0)
    missing_records = Column(Integer, default=0)
    accuracy_score = Column(Float, default=0.0)                    # computed from sampling
    freshness_score = Column(Float, default=0.0)                   # % of records within expiry window
    published = Column(Boolean, default=False, index=True)         # TRUE = visible to users
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Alembic migration:** `alembic/versions/20260620_0003_add_data_quality_audit.py`

**Update `models/__init__.py`:** Add `DataQualityAudit` import and `__all__` export.

---

### 4. New Model: `UserBehaviorSignal` (First-Party Data Generation)
**Purpose:** The Historian's "become the source" strategy. Capture every user interaction as proprietary training data.

**New file:** `backend/app/models/user_behavior_signal.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, JSONB, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class UserBehaviorSignal(Base):
    __tablename__ = "user_behavior_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)   # 'problem', 'opportunity', 'lead', 'dataset', 'report'
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)        # 'validated', 'scored', 'skipped', 'noted', 'shared', 'purchased', 'exported'
    metadata = Column(JSONB, nullable=True)                          # score value, note content, tags, time_spent_seconds
    session_id = Column(String(100), nullable=True, index=True)    # for grouping actions into sessions
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

**Alembic migration:** `alembic/versions/20260620_0004_add_user_behavior_signals.py`

**Update `models/__init__.py`:** Add `UserBehaviorSignal` import and `__all__` export.

**Update `models/user.py`:** Add relationship:
```python
behavior_signals = relationship("UserBehaviorSignal", back_populates="user")
```

---

## Phase 1: Foundation — New Services & API (Ship After Phase 0)

### 5. New Service: `EnrichmentService` (Staging Layer Logic)
**Purpose:** The brain that sits between vendor output and production DB. Handles promotion, rejection, staleness detection.

**New file:** `backend/app/services/enrichment_service.py`
```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.raw_enrichment import RawEnrichment, EnrichmentStatus
from app.models.data_quality_audit import DataQualityAudit

# Field-specific decay TTLs (from Practitioner research: 2.1% monthly ≈ 30 days for contacts, 90 days for firmographics)
FIELD_DECAY_TTL = {
    "email": timedelta(days=30),
    "phone": timedelta(days=30),
    "job_title": timedelta(days=60),
    "headcount": timedelta(days=90),
    "revenue": timedelta(days=90),
    "funding_round": timedelta(days=7),   # funding changes fast
    "company_registration": timedelta(days=365),  # government data is annual
    "sec_filing": timedelta(days=90),
}

class EnrichmentService:
    def __init__(self, db: Session):
        self.db = db
    
    def stage(self, target_entity: str, target_id: int, source: str, field_name: str, 
              raw_value: str, confidence: float = 0.0, source_url: str = None):
        """Write vendor output to staging. Never touches production."""
        ttl = FIELD_DECAY_TTL.get(field_name, timedelta(days=30))
        enrichment = RawEnrichment(
            target_entity=target_entity,
            target_id=target_id,
            source=source,
            source_url=source_url,
            field_name=field_name,
            raw_value=raw_value,
            confidence_score=confidence,
            expires_at=datetime.utcnow() + ttl,
            status=EnrichmentStatus.PENDING,
        )
        self.db.add(enrichment)
        self.db.commit()
        return enrichment
    
    def approve(self, enrichment_id: int, promoted_by: str = "system"):
        """Promote a staged record to production. This is the ONLY path to production fields."""
        record = self.db.query(RawEnrichment).filter(RawEnrichment.id == enrichment_id).first()
        if not record:
            return None
        record.status = EnrichmentStatus.APPROVED
        record.promoted_at = datetime.utcnow()
        record.promoted_by = promoted_by
        self.db.commit()
        # TODO: write to production entity (e.g., Lead.company, Opportunity.market_size)
        return record
    
    def mark_stale(self):
        """Job: mark records past expiry as stale."""
        cutoff = datetime.utcnow()
        self.db.query(RawEnrichment).filter(
            RawEnrichment.expires_at < cutoff,
            RawEnrichment.status.in_(["pending", "approved"])
        ).update({"status": EnrichmentStatus.STALE})
        self.db.commit()
    
    def get_quality_score(self, dataset: str) -> dict:
        """Compute real-time quality score for a dataset."""
        total = self.db.query(RawEnrichment).filter(
            RawEnrichment.target_entity == dataset
        ).count()
        stale = self.db.query(RawEnrichment).filter(
            RawEnrichment.target_entity == dataset,
            RawEnrichment.status == EnrichmentStatus.STALE
        ).count()
        accuracy = ((total - stale) / total * 100) if total > 0 else 0.0
        return {
            "dataset": dataset,
            "total_records": total,
            "stale_records": stale,
            "accuracy_score": round(accuracy, 2),
            "freshness_score": round((total - stale) / total * 100, 2) if total > 0 else 0.0,
        }
```

---

### 6. New Router: `EnrichmentRouter` (Staging API)
**Purpose:** API endpoints for the staging layer. The Practitioner's "parallel `_enriched` fields" exposed via API.

**New file:** `backend/app/routers/enrichment.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.models.raw_enrichment import RawEnrichment, EnrichmentStatus
from app.services.enrichment_service import EnrichmentService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/enrichment", tags=["enrichment"])

class StageRequest(BaseModel):
    target_entity: str
    target_id: int
    source: str
    field_name: str
    raw_value: str
    confidence: float = 0.0
    source_url: Optional[str] = None

class ApproveRequest(BaseModel):
    enrichment_id: int

@router.post("/stage", status_code=status.HTTP_201_CREATED)
def stage_enrichment(
    request: StageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stage external enrichment data. Does NOT write to production tables."""
    svc = EnrichmentService(db)
    record = svc.stage(
        target_entity=request.target_entity,
        target_id=request.target_id,
        source=request.source,
        field_name=request.field_name,
        raw_value=request.raw_value,
        confidence=request.confidence,
        source_url=request.source_url,
    )
    return {"id": record.id, "status": record.status, "expires_at": record.expires_at}

@router.post("/approve/{enrichment_id}")
def approve_enrichment(
    enrichment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promote staged enrichment to production."""
    svc = EnrichmentService(db)
    record = svc.approve(enrichment_id, promoted_by=f"user_id:{current_user.id}")
    if not record:
        raise HTTPException(status_code=404, detail="Enrichment record not found")
    return {"id": record.id, "status": record.status, "promoted_at": record.promoted_at}

@router.get("/quality/{dataset}")
def get_data_quality(
    dataset: str,
    db: Session = Depends(get_db),
):
    """Public endpoint: real-time data quality score for a dataset."""
    svc = EnrichmentService(db)
    return svc.get_quality_score(dataset)

@router.get("/pending/{target_entity}/{target_id}")
def get_pending_enrichment(
    target_entity: str,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all pending enrichment for a specific entity."""
    records = db.query(RawEnrichment).filter(
        RawEnrichment.target_entity == target_entity,
        RawEnrichment.target_id == target_id,
    ).order_by(RawEnrichment.enriched_at.desc()).all()
    return records
```

**Update `backend/app/main.py`:** Add import and register router:
```python
from app.routers import enrichment
app.include_router(enrichment.router)
```

---

### 7. New Service: `GovernmentDataIngestionService` (Free Foundation Layer)
**Purpose:** Ingest free government data as the Tier 1 compliance base. Explorium ranks this as lowest risk.

**New file:** `backend/app/services/government_data_service.py`
```python
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)

class GovernmentDataService:
    """Ingest free government/open data sources. Zero cost, Tier 1 compliance."""
    
    def __init__(self, db: Session):
        self.db = db
        self.enrichment = EnrichmentService(db)
    
    def ingest_sec_edgar(self, cik: str, target_entity: str, target_id: int):
        """Fetch latest SEC filing for a company."""
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
        try:
            # SEC requires a User-Agent header with contact info
            headers = {"User-Agent": "OppGrid Platform contact@oppgrid.com"}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract revenue (if available)
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
    
    def ingest_companies_house(self, company_number: str, target_entity: str, target_id: int):
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
    
    def ingest_sam_gov_awards(self, naics_code: str = None, limit: int = 100):
        """Fetch recent US government contract awards from SAM.gov."""
        url = "https://sam.gov/api/prod/opportunities/v1/search"
        try:
            # SAM.gov public search (no API key required for basic search)
            params = {"limit": limit, "sort": "-modifiedDate", "noticeType": "a"}
            if naics_code:
                params["naics"] = naics_code
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            opportunities = data.get("opportunitiesData", [])
            for opp in opportunities:
                # Stage as signal (contract awards are timing signals)
                self.db.add(OpportunitySignal(
                    signal_type="contract_award",
                    signal_value={
                        "title": opp.get("title"),
                        "agency": opp.get("agency"),
                        "award_amount": opp.get("awardAmount"),
                        "naics": opp.get("naicsCode"),
                    },
                    source_url=opp.get("uiLink"),
                    confidence_score=0.95,
                ))
            self.db.commit()
            return {"status": "ok", "count": len(opportunities)}
        except Exception as e:
            logger.error(f"SAM.gov ingestion failed: {e}")
            return {"status": "error", "error": str(e)}
```

**New config in `.env.example`:**
```
# Government Data APIs (free tier)
COMPANIES_HOUSE_API_KEY=
SEC_EDGAR_USER_AGENT=OppGrid Platform contact@oppgrid.com
```

---

### 8. Update Scheduler: Add Government Ingestion Jobs
**Purpose:** Hook the new ingestion jobs into the existing HTTP-triggered scheduler.

**Update `backend/app/routers/scheduler.py`:** Add new endpoints:
```python
@router.post("/trigger/government-ingest")
def trigger_government_ingest(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger government data ingestion for all known companies."""
    from app.services.government_data_service import GovernmentDataService
    svc = GovernmentDataService(db)
    
    # Ingest SAM.gov contract awards (daily)
    sam_result = svc.ingest_sam_gov_awards(limit=100)
    
    # Ingest SEC filings for companies with CIK (weekly)
    # TODO: iterate over companies with known CIK
    
    return {
        "status": "ok",
        "job": "government_ingest",
        "sam_gov": sam_result,
    }

# Update /trigger/all to include government ingest
@router.post("/trigger/all")
def trigger_all_scheduled_jobs(...):
    # ... existing code ...
    # 3. Government data ingest
    try:
        from app.services.government_data_service import GovernmentDataService
        svc = GovernmentDataService(db)
        results["government_ingest"] = {
            "sam_gov": svc.ingest_sam_gov_awards(limit=100),
        }
    except Exception as e:
        logger.error(f"Government ingest failed: {e}")
        errors.append(f"government_ingest: {str(e)}")
        results["government_ingest"] = {"error": str(e)}
    # ... rest of existing code ...
```

**Update `backend/app/routers/scheduler.py` status endpoint:** Add new job to the list.

---

## Phase 2: Signal Infrastructure — Timing + Waterfall (Ship After Phase 1)

### 9. New Service: `SignalDetectorService` (Real-Time Event Detection)
**Purpose:** The Economist's "value is in timing, not identity" — build signal detection from public feeds.

**New file:** `backend/app/services/signal_detector.py`
```python
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.opportunity_signal import OpportunitySignal

logger = logging.getLogger(__name__)

class SignalDetector:
    """Monitor public data feeds for high-intent business signals."""
    
    SIGNAL_SOURCES = {
        "crunchbase_funding": "https://www.crunchbase.com/discover/funding-rounds",
        "linkedin_jobs": None,  # requires Proxycurl or manual polling
        "sec_form_d": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=D&company=&dateb=&owner=include&count=100&output=atom",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_funding_from_sec(self):
        """Monitor SEC Form D (new fundings) via RSS."""
        feed = feedparser.parse(self.SIGNAL_SOURCES["sec_form_d"])
        new_signals = 0
        for entry in feed.entries[:20]:
            # Parse entry
            company = entry.get("title", "").split(" - ")[0] if " - " in entry.get("title", "") else entry.get("title", "")
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
    
    def detect_hiring_surge(self, company_name: str, job_board: str = "linkedin"):
        """Detect hiring surge by counting job postings. Placeholder for job board API."""
        # Implementation: integrate with LinkedIn Jobs API or Proxycurl
        # For now, log the intent
        logger.info(f"Hiring surge detection for {company_name} via {job_board} — implementation pending")
        return {"status": "pending", "company": company_name}
    
    def detect_exec_changes(self, linkedin_url: str):
        """Detect executive changes via Proxycurl."""
        api_key = os.getenv("PROXYCURL_API_KEY")
        if not api_key:
            return {"status": "skipped", "reason": "PROXYCURL_API_KEY not set"}
        
        url = "https://nubela.co/proxycurl/api/v2/linkedin"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(url, params={"url": linkedin_url}, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Compare with previous snapshot to detect changes
            # TODO: store snapshot and diff
            return {"status": "ok", "profile": data.get("full_name")}
        except Exception as e:
            logger.error(f"Proxycurl exec change detection failed: {e}")
            return {"status": "error", "error": str(e)}
```

**New config in `.env.example`:**
```
# Signal Detection APIs
PROXYCURL_API_KEY=
CRUNCHBASE_API_KEY=
```

---

### 10. New Service: `WaterfallLookupService` (Cheap Contact Identity)
**Purpose:** The Economist's "buy cheap contact lookups, don't sign enterprise contracts." Multi-tier waterfall with automatic fallback.

**New file:** `backend/app/services/waterfall_lookup.py`
```python
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
    
    def lookup_email(self, first_name: str, last_name: str, company_domain: str, target_entity: str, target_id: int) -> Dict:
        """Waterfall: Apollo → Lusha → Prospeo."""
        
        # Tier 1: Apollo (cheapest, $49/mo for 10K credits)
        result = self._apollo_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity, target_id=target_id,
                source="apollo", field_name="email",
                raw_value=result["email"], confidence=0.85,
            )
            return {"source": "apollo", "email": result["email"], "cost_tier": 1}
        
        # Tier 2: Lusha (mobile/direct dial, $37–49/mo)
        result = self._lusha_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity, target_id=target_id,
                source="lusha", field_name="email",
                raw_value=result["email"], confidence=0.80,
            )
            return {"source": "lusha", "email": result["email"], "cost_tier": 2}
        
        # Tier 3: Prospeo (pay-as-you-go, ~$0.01/email)
        result = self._prospeo_lookup(first_name, last_name, company_domain)
        if result and result.get("email"):
            self.enrichment.stage(
                target_entity=target_entity, target_id=target_id,
                source="prospeo", field_name="email",
                raw_value=result["email"], confidence=0.75,
            )
            return {"source": "prospeo", "email": result["email"], "cost_tier": 3}
        
        return {"source": None, "email": None, "cost_tier": None}
    
    def _apollo_lookup(self, first_name: str, last_name: str, company_domain: str) -> Optional[Dict]:
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
    
    def _lusha_lookup(self, first_name: str, last_name: str, company_domain: str) -> Optional[Dict]:
        # Lusha API implementation (similar pattern)
        api_key = os.getenv("LUSHA_API_KEY")
        if not api_key:
            return None
        # ... implementation ...
        return None
    
    def _prospeo_lookup(self, first_name: str, last_name: str, company_domain: str) -> Optional[Dict]:
        # Prospeo API implementation (similar pattern)
        api_key = os.getenv("PROSPEO_API_KEY")
        if not api_key:
            return None
        # ... implementation ...
        return None
```

**New config in `.env.example`:**
```
# Waterfall Enrichment APIs (cheap tier only — DO NOT sign enterprise contracts)
APOLLO_API_KEY=
LUSHA_API_KEY=
PROSPEO_API_KEY=
```

---

### 11. Update Scheduler: Signal Detection + Waterfall Jobs
**Update `backend/app/routers/scheduler.py`:** Add new endpoints:
```python
@router.post("/trigger/signal-detection")
def trigger_signal_detection(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger signal detection from public feeds."""
    from app.services.signal_detector import SignalDetector
    detector = SignalDetector(db)
    
    sec_result = detector.detect_funding_from_sec()
    # TODO: add more signal types
    
    return {
        "status": "ok",
        "job": "signal_detection",
        "sec_form_d": sec_result,
    }

@router.post("/trigger/waterfall-enrich")
def trigger_waterfall_enrichment(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Run waterfall enrichment for unpaired signals."""
    from app.services.waterfall_lookup import WaterfallLookupService
    svc = WaterfallLookupService(db)
    
    # Find signals without paired contacts
    unpaired = db.query(OpportunitySignal).filter(
        OpportunitySignal.paired_contact_id.is_(None),
        OpportunitySignal.actioned == False,
    ).limit(50).all()
    
    enriched = 0
    for signal in unpaired:
        # Extract company name from signal
        company = signal.signal_value.get("company_name", "") if signal.signal_value else ""
        if not company:
            continue
        # TODO: lookup contact via waterfall
        enriched += 1
    
    return {
        "status": "ok",
        "job": "waterfall_enrich",
        "unpaired_signals": len(unpaired),
        "enriched": enriched,
    }
```

---

## Phase 3: Proprietary Moat — First-Party Data + Verified Tier (Ship After Phase 2)

### 12. Middleware: `UserBehaviorTracker` (First-Party Data Capture)
**Purpose:** The Historian's "become the source" strategy. Capture every user interaction as proprietary training data.

**New file:** `backend/app/middleware/user_behavior_tracker.py`
```python
import logging
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user_behavior_signal import UserBehaviorSignal
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

class UserBehaviorTracker:
    """Lightweight middleware to capture user interactions as proprietary data signals."""
    
    TRACKED_ENDPOINTS = {
        "POST /api/v1/validations": ("opportunity", "validated"),
        "POST /api/v1/opportunities/{id}/score": ("opportunity", "scored"),
        "POST /api/v1/leads": ("lead", "created"),
        "POST /api/v1/datasets/{id}/purchase": ("dataset", "purchased"),
        "POST /api/v1/reports": ("report", "generated"),
    }
    
    def capture(self, request: Request, response, user_id: int):
        """Capture a behavior signal after a successful request."""
        method = request.method
        path = request.url.path
        endpoint_key = f"{method} {path}"
        
        # Match against tracked endpoints (simple prefix matching)
        entity_type, action = None, None
        for pattern, (et, act) in self.TRACKED_ENDPOINTS.items():
            if endpoint_key.startswith(pattern.split(" ")[0] + " ") and path.startswith(pattern.split(" ")[1].split("{")[0]):
                entity_type, action = et, act
                break
        
        if not entity_type:
            return
        
        # Extract entity_id from path params
        entity_id = request.path_params.get("id") or request.path_params.get("opportunity_id") or 0
        try:
            entity_id = int(entity_id)
        except (ValueError, TypeError):
            entity_id = 0
        
        # Build metadata
        metadata = {}
        if hasattr(request, "state") and hasattr(request.state, "body_json"):
            body = request.state.body_json
            metadata = {k: v for k, v in body.items() if k in ["score", "rating", "notes", "tags"]}
        
        # Write to DB (fire-and-forget via background task or async)
        db = SessionLocal()
        try:
            signal = UserBehaviorSignal(
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                metadata=metadata,
                session_id=request.headers.get("x-session-id"),
            )
            db.add(signal)
            db.commit()
        except Exception as e:
            logger.warning(f"Behavior tracking failed: {e}")
        finally:
            db.close()
```

**Update `backend/app/main.py`:** Register the behavior capture hook. Since the app uses FastAPI background tasks, integrate into a custom middleware or use `BackgroundTasks` in existing routers.

**Simpler approach (no middleware complexity):** Add behavior capture calls directly into existing router endpoints that matter. This is more reliable.

**Update `backend/app/routers/validations.py`:** After a successful validation creation, add:
```python
from app.models.user_behavior_signal import UserBehaviorSignal
# ... after db.commit() ...
behavior_signal = UserBehaviorSignal(
    user_id=current_user.id,
    entity_type="opportunity",
    entity_id=opportunity_id,
    action="validated",
    metadata={"validation_score": payload.score if hasattr(payload, "score") else None},
)
db.add(behavior_signal)
db.commit()
```

**Update `backend/app/routers/datasets_api.py`:** After a successful purchase, add behavior signal.

**Update `backend/app/routers/leads.py`:** After lead creation, add behavior signal.

---

### 13. New Router: `VerifiedDataRouter` (Quality-Certification Tier)
**Purpose:** The Academic's "credible commitment mechanism" — publish quality metrics that competitors cannot fake.

**New file:** `backend/app/routers/verified_data.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.data_quality_audit import DataQualityAudit
from app.models.raw_enrichment import RawEnrichment
from app.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/v1/verified", tags=["verified"])

@router.get("/quality-score/{dataset}")
def get_public_quality_score(dataset: str, db: Session = Depends(get_db)):
    """Public endpoint: real-time data quality score. No auth required."""
    svc = EnrichmentService(db)
    score = svc.get_quality_score(dataset)
    
    # Get last published audit
    audit = db.query(DataQualityAudit).filter(
        DataQualityAudit.dataset == dataset,
        DataQualityAudit.published == True,
    ).order_by(DataQualityAudit.check_date.desc()).first()
    
    return {
        "dataset": dataset,
        "real_time": score,
        "last_audit": {
            "date": audit.check_date.isoformat() if audit else None,
            "accuracy_score": audit.accuracy_score if audit else None,
            "freshness_score": audit.freshness_score if audit else None,
            "total_records": audit.total_records if audit else None,
        } if audit else None,
        "verified_badge": score["accuracy_score"] >= 90 and score["freshness_score"] >= 85,
    }

@router.get("/quality-report")
def get_quality_report(db: Session = Depends(get_db)):
    """Weekly data health report for all datasets."""
    datasets = ["leads", "opportunities", "companies", "signals"]
    report = []
    for ds in datasets:
        svc = EnrichmentService(db)
        score = svc.get_quality_score(ds)
        report.append({
            "dataset": ds,
            "accuracy_score": score["accuracy_score"],
            "freshness_score": score["freshness_score"],
            "total_records": score["total_records"],
            "stale_records": score["stale_records"],
        })
    return {"generated_at": datetime.utcnow().isoformat(), "datasets": report}
```

**Update `backend/app/main.py`:** Register the new router.

---

### 14. Frontend Changes: Verified Data Badge on Lead/Opportunity Cards
**Purpose:** The Academic's "costly-to-fake quality signal" visible to users.

**New file:** `frontend/components/data-quality-badge.js` (or inline in HTML)
```javascript
// Data Quality Badge Component
// Usage: <div id="dq-badge" data-entity-type="opportunity" data-entity-id="123"></div>

async function renderDataQualityBadge(container) {
    const entityType = container.dataset.entityType;
    const entityId = container.dataset.entityId;
    
    try {
        const resp = await fetch(`/api/v1/verified/quality-score/${entityType}`);
        const data = await resp.json();
        
        const badgeClass = data.verified_badge ? 'badge-verified' : 'badge-unverified';
        const badgeText = data.verified_badge 
            ? `Verified Data · ${data.real_time.accuracy_score}% accurate · ${data.real_time.freshness_score}% fresh`
            : `Data Quality · ${data.real_time.accuracy_score}% accurate`;
        
        container.innerHTML = `<span class="data-quality-badge ${badgeClass}">${badgeText}</span>`;
    } catch (e) {
        container.innerHTML = '';
    }
}

// Auto-initialize on page load
document.querySelectorAll('[data-entity-type]').forEach(renderDataQualityBadge);
```

**CSS additions (in `css/style.css` or inline):**
```css
.data-quality-badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 12px;
    display: inline-block;
}
.badge-verified {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.badge-unverified {
    background: #fff3cd;
    color: #856404;
    border: 1px solid #ffeeba;
}
```

**Modify `opportunity.html`:** Add the badge div near the opportunity title:
```html
<div class="opportunity-header">
    <h1 id="opportunity-title"></h1>
    <div id="dq-badge" data-entity-type="opportunity" data-entity-id=""></div>
</div>
```

**Modify `discover.html`:** Add quality badges to opportunity cards in the discovery feed.

---

## Configuration Changes

### `.env.example` additions:
```bash
# ============================================================================
# DATA SOURCING: Free Government / Open Data (Tier 1 Compliance)
# ============================================================================
COMPANIES_HOUSE_API_KEY=
SEC_EDGAR_USER_AGENT=OppGrid Platform contact@oppgrid.com

# ============================================================================
# DATA SOURCING: Signal Detection APIs (cheap tier)
# ============================================================================
PROXYCURL_API_KEY=
CRUNCHBASE_API_KEY=

# ============================================================================
# DATA SOURCING: Waterfall Enrichment (cheap tier — no enterprise contracts)
# ============================================================================
APOLLO_API_KEY=
LUSHA_API_KEY=
PROSPEO_API_KEY=

# ============================================================================
# DATA SOURCING: Staging Layer Settings
# ============================================================================
ENRICHMENT_AUTO_APPROVE_GOVERNMENT=true   # government data is auto-approved (Tier 1)
ENRICHMENT_AUTO_APPROVE_THRESHOLD=0.90     # auto-approve if confidence >= 90%
ENRICHMENT_STALENESS_CHECK_HOURS=24        # how often to run staleness job
```

---

## Summary of New Files

| Phase | File | Purpose |
|-------|------|---------|
| P0 | `backend/app/models/raw_enrichment.py` | Staging layer table |
| P0 | `backend/app/models/opportunity_signal.py` | Timing signal table |
| P0 | `backend/app/models/data_quality_audit.py` | Quality audit table |
| P0 | `backend/app/models/user_behavior_signal.py` | First-party behavior table |
| P0 | `alembic/versions/20260620_000{1-4}_*.py` | 4 migrations |
| P1 | `backend/app/services/enrichment_service.py` | Staging layer logic |
| P1 | `backend/app/services/government_data_service.py` | Free government ingestion |
| P1 | `backend/app/services/signal_detector.py` | Real-time event detection |
| P1 | `backend/app/services/waterfall_lookup.py` | Multi-tier contact lookup |
| P1 | `backend/app/routers/enrichment.py` | Staging API endpoints |
| P1 | `backend/app/routers/verified_data.py` | Public quality score API |
| P2 | `frontend/components/data-quality-badge.js` | Verified badge UI |
| P2 | `backend/app/middleware/user_behavior_tracker.py` | Behavior capture (optional) |

## Summary of Modified Files

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Import 4 new models, add to `__all__` |
| `backend/app/models/opportunity.py` | Add `signals` relationship |
| `backend/app/models/lead.py` | Add `signals` relationship |
| `backend/app/models/user.py` | Add `behavior_signals` relationship |
| `backend/app/main.py` | Register 2 new routers (`enrichment`, `verified_data`) |
| `backend/app/routers/scheduler.py` | Add 3 new trigger endpoints + update `trigger/all` |
| `backend/app/routers/validations.py` | Add `UserBehaviorSignal` capture after validation |
| `backend/app/routers/datasets_api.py` | Add `UserBehaviorSignal` capture after purchase |
| `backend/app/routers/leads.py` | Add `UserBehaviorSignal` capture after lead creation |
| `opportunity.html` | Add `data-quality-badge` div |
| `discover.html` | Add quality badges to cards |
| `.env.example` | Add 7 new API keys + 3 staging config vars |

---

*This specification is derived from the 5-expert deep research synthesis and mapped directly to the existing OppGrid FastAPI monolith codebase.*
