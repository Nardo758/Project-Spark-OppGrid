from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os

from app.db.database import get_db
from app.models.raw_enrichment import RawEnrichment, EnrichmentStatus
from app.models.data_quality_audit import DataQualityAudit
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


class RejectRequest(BaseModel):
    enrichment_id: int
    reason: str = ""


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
    return {
        "id": record.id,
        "status": record.status,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }


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
    return {
        "id": record.id,
        "status": record.status,
        "promoted_at": record.promoted_at.isoformat() if record.promoted_at else None,
    }


@router.post("/reject/{enrichment_id}")
def reject_enrichment(
    enrichment_id: int,
    request: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a staged enrichment record."""
    svc = EnrichmentService(db)
    record = svc.reject(enrichment_id, reason=request.reason)
    if not record:
        raise HTTPException(status_code=404, detail="Enrichment record not found")
    return {"id": record.id, "status": record.status}


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
    records = (
        db.query(RawEnrichment)
        .filter(
            RawEnrichment.target_entity == target_entity,
            RawEnrichment.target_id == target_id,
        )
        .order_by(RawEnrichment.enriched_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "source": r.source,
            "field_name": r.field_name,
            "raw_value": r.raw_value,
            "confidence_score": r.confidence_score,
            "status": r.status,
            "enriched_at": r.enriched_at.isoformat() if r.enriched_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        }
        for r in records
    ]


@router.post("/run-auto-approve")
def run_auto_approve(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin endpoint: run auto-approve for pending records."""
    if not getattr(current_user, "is_admin", False) and not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    svc = EnrichmentService(db)
    threshold = float(os.getenv("ENRICHMENT_AUTO_APPROVE_THRESHOLD", "0.90"))
    count = svc.auto_approve(threshold=threshold)
    return {"approved_count": count}
