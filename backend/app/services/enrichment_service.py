import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.raw_enrichment import RawEnrichment, EnrichmentStatus
from app.models.data_quality_audit import DataQualityAudit

logger = logging.getLogger(__name__)

# Field-specific decay TTLs (from Practitioner research)
FIELD_DECAY_TTL = {
    "email": timedelta(days=30),
    "phone": timedelta(days=30),
    "job_title": timedelta(days=60),
    "headcount": timedelta(days=90),
    "revenue": timedelta(days=90),
    "funding_round": timedelta(days=7),
    "company_registration": timedelta(days=365),
    "sec_filing": timedelta(days=90),
}


class EnrichmentService:
    def __init__(self, db: Session):
        self.db = db

    def stage(
        self,
        target_entity: str,
        target_id: int,
        source: str,
        field_name: str,
        raw_value: str,
        confidence: float = 0.0,
        source_url: str = None,
        parsed_value: Optional[Dict] = None,
    ) -> RawEnrichment:
        """Write vendor output to staging. Never touches production."""
        ttl = FIELD_DECAY_TTL.get(field_name, timedelta(days=30))
        enrichment = RawEnrichment(
            target_entity=target_entity,
            target_id=target_id,
            source=source,
            source_url=source_url,
            field_name=field_name,
            raw_value=raw_value,
            parsed_value=parsed_value,
            confidence_score=confidence,
            expires_at=datetime.utcnow() + ttl,
            status=EnrichmentStatus.PENDING,
        )
        self.db.add(enrichment)
        self.db.commit()
        self.db.refresh(enrichment)
        return enrichment

    def approve(self, enrichment_id: int, promoted_by: str = "system") -> Optional[RawEnrichment]:
        """Promote a staged record to production. Only path to production fields."""
        record = (
            self.db.query(RawEnrichment)
            .filter(RawEnrichment.id == enrichment_id)
            .first()
        )
        if not record:
            return None
        record.status = EnrichmentStatus.APPROVED
        record.promoted_at = datetime.utcnow()
        record.promoted_by = promoted_by
        self.db.commit()
        self.db.refresh(record)
        return record

    def reject(self, enrichment_id: int, reason: str = "") -> Optional[RawEnrichment]:
        """Reject a staged record."""
        record = (
            self.db.query(RawEnrichment)
            .filter(RawEnrichment.id == enrichment_id)
            .first()
        )
        if not record:
            return None
        record.status = EnrichmentStatus.REJECTED
        record.rejection_reason = reason
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_stale(self) -> int:
        """Job: mark records past expiry as stale."""
        cutoff = datetime.utcnow()
        result = (
            self.db.query(RawEnrichment)
            .filter(
                RawEnrichment.expires_at < cutoff,
                RawEnrichment.status.in_(
                    [EnrichmentStatus.PENDING.value, EnrichmentStatus.APPROVED.value]
                ),
            )
            .update({"status": EnrichmentStatus.STALE.value}, synchronize_session=False)
        )
        self.db.commit()
        return result

    def get_quality_score(self, dataset: str) -> Dict:
        """Compute real-time quality score for a dataset."""
        total = (
            self.db.query(RawEnrichment)
            .filter(RawEnrichment.target_entity == dataset)
            .count()
        )
        stale = (
            self.db.query(RawEnrichment)
            .filter(
                RawEnrichment.target_entity == dataset,
                RawEnrichment.status == EnrichmentStatus.STALE.value,
            )
            .count()
        )
        accuracy = ((total - stale) / total * 100) if total > 0 else 0.0
        return {
            "dataset": dataset,
            "total_records": total,
            "stale_records": stale,
            "accuracy_score": round(accuracy, 2),
            "freshness_score": round((total - stale) / total * 100, 2) if total > 0 else 0.0,
        }

    def auto_approve(self, threshold: float = 0.90) -> int:
        """Auto-approve government data and high-confidence records."""
        auto_sources = os.getenv("ENRICHMENT_AUTO_APPROVE_SOURCES", "sec_edgar,companies_house,open_corporates,sam_gov").split(",")
        auto_sources = [s.strip() for s in auto_sources]

        records = (
            self.db.query(RawEnrichment)
            .filter(
                RawEnrichment.status == EnrichmentStatus.PENDING.value,
                RawEnrichment.source.in_(auto_sources),
            )
            .all()
        )

        approved = 0
        for record in records:
            record.status = EnrichmentStatus.APPROVED.value
            record.promoted_at = datetime.utcnow()
            record.promoted_by = "system_auto_approve"
            approved += 1

        # Also high-confidence non-government
        high_conf = (
            self.db.query(RawEnrichment)
            .filter(
                RawEnrichment.status == EnrichmentStatus.PENDING.value,
                RawEnrichment.source.notin_(auto_sources),
                RawEnrichment.confidence_score >= threshold,
            )
            .all()
        )
        for record in high_conf:
            record.status = EnrichmentStatus.APPROVED.value
            record.promoted_at = datetime.utcnow()
            record.promoted_by = "system_auto_approve_high_conf"
            approved += 1

        self.db.commit()
        return approved
