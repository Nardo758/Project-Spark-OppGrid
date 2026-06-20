from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from app.db.database import get_db
from app.models.data_quality_audit import DataQualityAudit
from app.models.raw_enrichment import RawEnrichment, EnrichmentStatus
from app.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/v1/verified", tags=["verified"])


@router.get("/quality-score/{dataset}")
def get_public_quality_score(dataset: str, db: Session = Depends(get_db)):
    """Public endpoint: real-time data quality score. No auth required."""
    svc = EnrichmentService(db)
    score = svc.get_quality_score(dataset)

    audit = (
        db.query(DataQualityAudit)
        .filter(
            DataQualityAudit.dataset == dataset,
            DataQualityAudit.published == True,
        )
        .order_by(DataQualityAudit.check_date.desc())
        .first()
    )

    return {
        "dataset": dataset,
        "real_time": score,
        "last_audit": (
            {
                "date": audit.check_date.isoformat() if audit.check_date else None,
                "accuracy_score": audit.accuracy_score,
                "freshness_score": audit.freshness_score,
                "total_records": audit.total_records,
            }
            if audit
            else None
        ),
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
        report.append(
            {
                "dataset": ds,
                "accuracy_score": score["accuracy_score"],
                "freshness_score": score["freshness_score"],
                "total_records": score["total_records"],
                "stale_records": score["stale_records"],
            }
        )
    return {"generated_at": datetime.utcnow().isoformat(), "datasets": report}
