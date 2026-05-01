"""
Mapping Analysis Report Router - PDF generation for location analysis findings
Handles: Identify Location reports and Clone Success reports
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.generated_report import GeneratedReport, ReportType
from app.schemas.report_generation import (
    IdentifyLocationReportRequest,
    CloneSuccessReportRequest,
    PDFReportResponse,
    ReportStatusResponse,
)
from app.services.report_generation import (
    IdentifyLocationReportGenerator,
    CloneSuccessReportGenerator,
)
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consultant-studio", tags=["Mapping Reports"])

# Cache TTL in days
REPORT_CACHE_TTL_DAYS = 30


def _generate_pdf_filename(report_type: str, city: Optional[str] = None) -> str:
    """Generate standardized PDF filename"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    if report_type == "identify_location":
        city_str = (city or "analysis").replace(" ", "_").lower()
        return f"location_identification_{city_str}_{timestamp}.pdf"
    elif report_type == "clone_success":
        return f"clone_success_analysis_{timestamp}.pdf"
    else:
        return f"mapping_analysis_{timestamp}.pdf"


def _check_cache(
    db: Session,
    request_id: str,
    force_regenerate: bool = False,
) -> Optional[GeneratedReport]:
    """Check if valid cached report exists"""
    if force_regenerate:
        return None
    
    cached = db.query(GeneratedReport).filter(
        GeneratedReport.request_id == request_id,
    ).first()
    
    if not cached:
        return None
    
    # Check if expired
    if cached.is_expired():
        cached.is_valid = 0
        db.commit()
        return None
    
    return cached


def _save_report_to_cache(
    db: Session,
    user_id: int,
    request_id: str,
    report_type: str,
    pdf_content: bytes,
    filename: str,
    generation_time_ms: int,
) -> GeneratedReport:
    """Save generated report to database cache"""
    expires_at = datetime.utcnow() + timedelta(days=REPORT_CACHE_TTL_DAYS)
    
    report = GeneratedReport(
        user_id=user_id,
        request_id=request_id,
        report_type=report_type,
        pdf_content=pdf_content,
        pdf_filename=filename,
        pdf_size_bytes=len(pdf_content),
        generation_time_ms=generation_time_ms,
        generator_version="1.0.0",
        expires_at=expires_at,
        is_valid=1,
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    logger.info(
        f"Cached report {report.id} for request {request_id} "
        f"(expires {expires_at.isoformat()})"
    )
    
    return report


@router.post(
    "/identify-location/{request_id}/report/pdf",
    response_model=PDFReportResponse,
)
async def generate_identify_location_pdf(
    request_id: str,
    report_request: IdentifyLocationReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PDFReportResponse:
    """
    Generate PDF report for Identify Location analysis
    
    Returns a professional PDF with:
    - Executive Summary
    - Market Overview
    - Candidate Locations by Archetype
    - Comparison Table
    - Investment Thesis
    - Appendix
    """
    
    start_time = datetime.utcnow()
    
    try:
        # Check cache
        cached = _check_cache(db, request_id, report_request.force_regenerate)
        if cached:
            # Update access tracking
            cached.update_access()
            db.commit()
            
            return PDFReportResponse(
                success=True,
                report_id=str(cached.id),
                filename=cached.pdf_filename,
                size_bytes=cached.pdf_size_bytes,
                generated_at=cached.created_at,
                from_cache=True,
                generation_time_ms=cached.generation_time_ms,
                download_url=f"/api/consultant-studio/reports/{cached.id}/download",
            )
        
        # Generate new report
        identify_data = report_request.identify_location_result
        
        generator = IdentifyLocationReportGenerator(
            identify_location_result=identify_data,
            request_id=request_id,
        )
        
        pdf_bytes = generator.generate()
        
        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        city = identify_data.get('city', 'Analysis')
        filename = _generate_pdf_filename("identify_location", city)
        
        # Save to cache
        cached_report = _save_report_to_cache(
            db=db,
            user_id=current_user.id,
            request_id=request_id,
            report_type="identify_location",
            pdf_content=pdf_bytes,
            filename=filename,
            generation_time_ms=generation_time,
        )
        
        logger.info(
            f"Generated Identify Location PDF for {city} "
            f"({len(pdf_bytes)} bytes, {generation_time}ms)"
        )
        
        return PDFReportResponse(
            success=True,
            report_id=str(cached_report.id),
            filename=filename,
            size_bytes=len(pdf_bytes),
            generated_at=datetime.utcnow(),
            from_cache=False,
            generation_time_ms=generation_time,
            download_url=f"/api/consultant-studio/reports/{cached_report.id}/download",
        )
        
    except Exception as e:
        logger.error(f"Failed to generate Identify Location PDF: {e}", exc_info=True)
        return PDFReportResponse(
            success=False,
            filename="error.pdf",
            generated_at=datetime.utcnow(),
            error=str(e),
        )


@router.post(
    "/clone-success/{analysis_id}/report/pdf",
    response_model=PDFReportResponse,
)
async def generate_clone_success_pdf(
    analysis_id: str,
    report_request: CloneSuccessReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PDFReportResponse:
    """
    Generate PDF report for Clone Success analysis
    
    Returns a professional PDF with:
    - Executive Summary
    - Source Business Profile
    - Matching Locations Overview
    - Detailed Location Analysis
    - Replication Strategy
    - Risk Assessment
    - Investment Summary
    """
    
    start_time = datetime.utcnow()
    
    try:
        # Check cache
        request_id = report_request.request_id
        cached = _check_cache(db, request_id, report_request.force_regenerate)
        if cached:
            cached.update_access()
            db.commit()
            
            return PDFReportResponse(
                success=True,
                report_id=str(cached.id),
                filename=cached.pdf_filename,
                size_bytes=cached.pdf_size_bytes,
                generated_at=cached.created_at,
                from_cache=True,
                generation_time_ms=cached.generation_time_ms,
                download_url=f"/api/consultant-studio/reports/{cached.id}/download",
            )
        
        # Generate new report
        clone_data = report_request.clone_success_response
        
        generator = CloneSuccessReportGenerator(
            clone_success_response=clone_data,
            request_id=request_id,
        )
        
        pdf_bytes = generator.generate()
        
        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        filename = _generate_pdf_filename("clone_success")
        
        # Save to cache
        cached_report = _save_report_to_cache(
            db=db,
            user_id=current_user.id,
            request_id=request_id,
            report_type="clone_success",
            pdf_content=pdf_bytes,
            filename=filename,
            generation_time_ms=generation_time,
        )
        
        logger.info(
            f"Generated Clone Success PDF ({len(pdf_bytes)} bytes, {generation_time}ms)"
        )
        
        return PDFReportResponse(
            success=True,
            report_id=str(cached_report.id),
            filename=filename,
            size_bytes=len(pdf_bytes),
            generated_at=datetime.utcnow(),
            from_cache=False,
            generation_time_ms=generation_time,
            download_url=f"/api/consultant-studio/reports/{cached_report.id}/download",
        )
        
    except Exception as e:
        logger.error(f"Failed to generate Clone Success PDF: {e}", exc_info=True)
        return PDFReportResponse(
            success=False,
            filename="error.pdf",
            generated_at=datetime.utcnow(),
            error=str(e),
        )


@router.get("/reports/{report_id}")
async def get_report_status(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportStatusResponse:
    """Get status of a generated report"""
    
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    status = "cached"
    if not report.is_valid:
        status = "expired"
    
    return ReportStatusResponse(
        report_id=str(report.id),
        report_type=report.report_type,
        status=status,
        created_at=report.created_at,
        expires_at=report.expires_at,
        access_count=report.access_count,
        last_accessed_at=report.last_accessed_at,
        is_valid=bool(report.is_valid),
    )


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download a generated PDF report"""
    
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.is_expired():
        raise HTTPException(status_code=410, detail="Report cache has expired")
    
    if not report.pdf_content:
        raise HTTPException(status_code=500, detail="Report content not available")
    
    # Update access tracking
    report.update_access()
    db.commit()
    
    logger.info(f"Downloaded report {report.id} for user {current_user.id}")
    
    return FileResponse(
        io.BytesIO(report.pdf_content),
        media_type="application/pdf",
        filename=report.pdf_filename,
    )


@router.get("/reports")
async def list_user_reports(
    report_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List generated reports for current user"""
    
    query = db.query(GeneratedReport).filter(
        GeneratedReport.user_id == current_user.id,
        GeneratedReport.is_valid == 1,
    )
    
    if report_type:
        query = query.filter(GeneratedReport.report_type == report_type)
    
    total = query.count()
    
    reports = query.order_by(
        GeneratedReport.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    return {
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'reports': [
            {
                'id': str(r.id),
                'request_id': r.request_id,
                'report_type': r.report_type,
                'filename': r.pdf_filename,
                'size_bytes': r.pdf_size_bytes,
                'created_at': r.created_at.isoformat(),
                'expires_at': r.expires_at.isoformat() if r.expires_at else None,
                'access_count': r.access_count,
            }
            for r in reports
        ]
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a cached report"""
    
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.delete(report)
    db.commit()
    
    logger.info(f"Deleted report {report.id} for user {current_user.id}")
    
    return {'success': True, 'message': 'Report deleted'}
