"""Dataset marketplace API endpoints with Stripe payment integration."""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Path, Query, Header
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import stripe

from app.db.database import get_db
from app.models.dataset import Dataset, DatasetPurchase, DatasetType
from app.models.user import User
from app.core.dependencies import get_current_user
from app.core.security import decode_access_token
from app.services.dataset_delivery_service import get_delivery_service

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_51234567890")

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PurchaseRequest(BaseModel):
    """Request to purchase a dataset."""
    dataset_id: str


class PurchaseResponse(BaseModel):
    """Response with Stripe payment details."""
    purchase_id: str
    stripe_payment_intent_id: str
    client_secret: str
    amount_cents: int
    currency: str


class PurchaseHistory(BaseModel):
    """User's dataset purchase."""
    purchase_id: str
    dataset_id: str
    dataset_name: str
    price_cents: int
    purchased_at: str
    expires_at: str
    download_url: str
    status: str


class PurchaseListResponse(BaseModel):
    """List of user's purchases."""
    purchases: List[PurchaseHistory]
    total_count: int


# ============================================================================
# Helper Functions
# ============================================================================



def _create_stripe_payment_intent(
    amount_cents: int,
    dataset_id: str,
    user_id: str
) -> dict:
    """
    Create a Stripe PaymentIntent for dataset purchase.
    
    Args:
        amount_cents: Amount in cents
        dataset_id: Dataset ID for metadata
        user_id: User ID for metadata
        
    Returns:
        Dict with payment_intent_id and client_secret
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            metadata={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "product_type": "dataset",
            },
            description=f"Dataset purchase: {dataset_id}",
        )
        
        logger.info(f"Created Stripe PaymentIntent {intent.id} for dataset {dataset_id}")
        
        return {
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing error: {str(e)}",
        )


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("", response_model=List[dict])
def list_datasets(
    vertical: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    dataset_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    x_agent_key: Optional[str] = Header(None),
) -> List[dict]:
    """
    List available datasets for purchase.

    Query Parameters:
    - vertical: Filter by vertical (partial, case-insensitive)
    - city: Filter by city (partial, case-insensitive)
    - dataset_type: Filter by type (exact match)
    - search: Full-text search across name, description, city, vertical
    """
    from sqlalchemy import or_
    try:
        query = db.query(Dataset).filter(Dataset.is_active == True)

        if vertical:
            query = query.filter(Dataset.vertical.ilike(f"%{vertical}%"))
        if city:
            query = query.filter(Dataset.city.ilike(f"%{city}%"))
        if dataset_type:
            query = query.filter(Dataset.dataset_type == dataset_type)
        if search:
            s = f"%{search}%"
            query = query.filter(or_(
                Dataset.name.ilike(s),
                Dataset.description.ilike(s),
                Dataset.city.ilike(s),
                Dataset.vertical.ilike(s),
            ))

        datasets = query.order_by(Dataset.created_at.desc()).all()
        return [d.to_dict() for d in datasets]
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/my-purchases", response_model=PurchaseListResponse)
def list_purchases_early(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PurchaseListResponse:
    """Get list of user's purchased datasets. (Declared early to avoid /{dataset_id} wildcard.)"""
    try:
        purchases = db.query(DatasetPurchase).filter(
            DatasetPurchase.user_id == current_user.id,
        ).order_by(DatasetPurchase.created_at.desc()).all()

        purchase_list = []
        for purchase in purchases:
            dataset = db.query(Dataset).filter(Dataset.id == purchase.dataset_id).first()
            if not dataset:
                continue
            purchase_list.append(PurchaseHistory(
                purchase_id=purchase.id,
                dataset_id=purchase.dataset_id,
                dataset_name=dataset.name,
                price_cents=purchase.price_cents,
                purchased_at=purchase.created_at.isoformat() if purchase.created_at else None,
                expires_at=purchase.expires_at.isoformat() if purchase.expires_at else None,
                download_url=purchase.download_url or f"/api/v1/datasets/download/{purchase.id}",
                status=purchase.status,
            ))

        return PurchaseListResponse(purchases=purchase_list, total_count=len(purchase_list))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving purchases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/preview", response_model=dict)
def preview_dataset(
    dataset_id: str = Path(..., description="Dataset ID"),
    db: Session = Depends(get_db),
) -> dict:
    """Get a preview (first 5 rows + metadata) of a dataset."""
    try:
        dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.is_active == True,
        ).first()

        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        delivery = get_delivery_service()
        rows: List[dict] = []
        columns: List[str] = []

        # Data quality gate: count actual rows before generating preview
        actual_row_count = 0
        try:
            from app.models.data_hub import HubOpportunityEnriched, HubMarketByGeography
            from app.models.detected_trend import DetectedTrend
            from app.models.data_source import ScrapeJob
            filters = delivery._get_query_filters(dataset)
            dt = dataset.dataset_type
            if dt in (DatasetType.OPPORTUNITIES.value, 'opportunity_signals'):
                query = db.query(HubOpportunityEnriched)
                if filters.get('city'):
                    query = query.filter(HubOpportunityEnriched.city.ilike(f"%{filters['city']}%"))
                if filters.get('state'):
                    query = query.filter(HubOpportunityEnriched.state.ilike(f"%{filters['state']}%"))
                if filters.get('vertical'):
                    query = query.filter(HubOpportunityEnriched.category.ilike(f"%{filters['vertical']}%"))
                actual_row_count = query.count()
            elif dt in (DatasetType.MARKETS.value, 'market_intelligence'):
                query = db.query(HubMarketByGeography)
                if filters.get('city'):
                    query = query.filter(HubMarketByGeography.city.ilike(f"%{filters['city']}%"))
                if filters.get('state'):
                    query = query.filter(HubMarketByGeography.state.ilike(f"%{filters['state']}%"))
                actual_row_count = query.count()
            elif dt in (DatasetType.TRENDS.value, 'economic_intelligence'):
                query = db.query(DetectedTrend)
                if filters.get('vertical'):
                    query = query.filter(DetectedTrend.category.ilike(f"%{filters['vertical']}%"))
                actual_row_count = query.count()
            elif dt in (DatasetType.RAW_DATA.value, 'competition_intelligence'):
                query = db.query(ScrapeJob)
                if filters.get('city'):
                    query = query.filter(ScrapeJob.city.ilike(f"%{filters['city']}%"))
                actual_row_count = query.count()
        except Exception as count_err:
            logger.warning(f"Could not count actual rows for dataset {dataset_id}: {count_err}")

        # Tier thresholds for data quality warning
        tier_min_rows = {
            'opportunity_signals': 25,
            'market_intelligence': 50,
            'economic_intelligence': 30,
            'competition_intelligence': 100,
            DatasetType.OPPORTUNITIES.value: 25,
            DatasetType.MARKETS.value: 50,
            DatasetType.TRENDS.value: 30,
            DatasetType.RAW_DATA.value: 100,
        }
        min_rows = tier_min_rows.get(dataset.dataset_type, 25)
        is_preview_only = actual_row_count < min_rows and actual_row_count > 0
        is_insufficient = actual_row_count == 0
        data_quality = {
            "actual_row_count": actual_row_count,
            "advertised_row_count": dataset.record_count or 0,
            "min_rows_for_tier": min_rows,
            "is_preview_only": is_preview_only,
            "is_insufficient": is_insufficient,
            "quality_label": "insufficient" if is_insufficient else "preview" if is_preview_only else "ready",
        }

        try:
            dt = dataset.dataset_type
            if dt == DatasetType.OPPORTUNITIES.value or dt == DatasetType.OPPORTUNITIES:
                columns, rows = delivery.preview_opportunities(dataset, db)
                if not columns:
                    columns = ['opportunity_id', 'title', 'category', 'city', 'state',
                               'ai_opportunity_score', 'market_tier', 'trend_momentum', 'competition_density',
                               'estimated_market_size_usd', 'estimated_startup_cost_usd', 'estimated_monthly_revenue_usd',
                               'roi_estimate_percent', 'break_even_months', 'confidence_score', 'data_freshness', 'data_source']
            elif dt == DatasetType.MARKETS.value or dt == DatasetType.MARKETS:
                columns, rows = delivery.preview_markets(dataset, db)
                if not columns:
                    columns = ['market_id', 'city', 'state', 'country', 'total_opportunities', 'categories', 'avg_score', 'market_health', 'data_source']
            elif dt == DatasetType.TRENDS.value or dt == DatasetType.TRENDS:
                columns, rows = delivery.preview_trends(dataset, db)
                if not columns:
                    columns = ['id', 'trend_name', 'trend_strength', 'category', 'source_type',
                               'opportunities_count', 'growth_rate', 'confidence_score', 'keywords', 'detected_at', 'data_source']
            elif dt == DatasetType.RAW_DATA.value or dt == DatasetType.RAW_DATA:
                columns, rows = delivery.preview_raw_data(dataset, db)
                if not columns:
                    columns = ['job_id', 'source_name', 'job_type', 'status',
                               'items_processed', 'items_accepted', 'items_rejected',
                               'error_message', 'completed_at', 'created_at', 'data_source']
            elif dt == 'opportunity_signals':
                columns, rows = delivery.preview_opportunities(dataset, db)
                if not columns:
                    columns = ['signal_type', 'city', 'vertical', 'signal_strength',
                               'trend_direction', 'data_source', 'detected_at', 'confidence']
            elif dt == 'market_intelligence':
                columns, rows = delivery.preview_markets(dataset, db)
                if not columns:
                    columns = ['product_category', 'price_position', 'promotion_channel',
                               'place_coverage', 'market_share_pct', 'competitive_score', 'city']
            elif dt == 'economic_intelligence':
                columns, rows = delivery.preview_trends(dataset, db)
                if not columns:
                    columns = ['industry', 'gdp_contribution_pct', 'employment_growth_pct',
                               'revenue_trend', 'investment_flow_m', 'market_size_b', 'year']
            elif dt == 'competition_intelligence':
                columns, rows = delivery.preview_raw_data(dataset, db)
                if not columns:
                    columns = ['business_name', 'address', 'rating', 'review_count',
                               'category', 'price_level', 'is_open']
            else:
                columns = []
                rows = []
        except Exception as gen_err:
            logger.warning(f"Preview row generation failed for dataset {dataset_id}: {gen_err}")
            rows = []
            columns = []

        return {
            "metadata": {
                "record_count": dataset.record_count or 0,
                "data_freshness": dataset.data_freshness or (dataset.generated_at.isoformat() if dataset.generated_at else ""),
                "vertical": dataset.vertical,
                "city": dataset.city,
                "has_real_data": len(rows) > 0,
                "data_quality": data_quality,
            },
            "rows": rows[:5],
            "columns": columns,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{dataset_id}/purchase")
def purchase_dataset_by_id(
    dataset_id: str = Path(..., description="Dataset ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete a dataset purchase for the authenticated user."""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id, Dataset.is_active == True
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check for existing completed purchase
    existing = db.query(DatasetPurchase).filter(
        DatasetPurchase.dataset_id == dataset_id,
        DatasetPurchase.user_id == str(current_user.id),
        DatasetPurchase.status == "completed",
    ).first()
    if existing:
        return {
            "purchase_id": existing.id,
            "dataset_id": existing.dataset_id,
            "download_url": existing.download_url or f"/api/v1/datasets/{dataset_id}/download/{existing.id}",
            "expires_at": existing.expires_at.isoformat() if existing.expires_at else None,
            "status": existing.status,
        }

    purchase_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=30)
    download_url = f"/api/v1/datasets/download/{purchase_id}"

    purchase = DatasetPurchase(
        id=purchase_id,
        dataset_id=dataset.id,
        user_id=str(current_user.id),
        price_cents=dataset.price_cents,
        payment_method="direct",
        status="completed",
        download_url=download_url,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(purchase)
    db.commit()

    logger.info(f"Dataset purchase completed: {purchase_id} for user {current_user.id}")

    return {
        "purchase_id": purchase_id,
        "dataset_id": dataset_id,
        "download_url": download_url,
        "expires_at": expires_at.isoformat(),
        "status": "completed",
    }


@router.get("/{dataset_id}", response_model=dict)
def get_dataset(
    dataset_id: str = Path(..., description="Dataset ID"),
    db: Session = Depends(get_db),
) -> dict:
    """Get details for a specific dataset."""
    try:
        dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.is_active == True
        ).first()

        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        return dataset.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/purchase")
def purchase_dataset(
    request: PurchaseRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate dataset purchase with Stripe payment.
    
    Flow:
    1. Verify user authentication (JWT)
    2. Get dataset details
    3. Create Stripe PaymentIntent
    4. Return payment details for frontend checkout
    
    Request:
    {
        "dataset_id": "dataset-123"
    }
    
    Response:
    {
        "purchase_id": "purchase-456",
        "stripe_payment_intent_id": "pi_...",
        "client_secret": "pi_...secret",
        "amount_cents": 9900,
        "currency": "usd"
    }
    """
    # 1. Get dataset
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id, Dataset.is_active == True).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or inactive")

    # 2. Create a pending purchase record
    purchase_id = str(uuid.uuid4())
    purchase = DatasetPurchase(
        id=purchase_id,
        dataset_id=dataset.id,
        user_id=None,  # Guest checkout; will be updated after payment
        price_cents=dataset.price_cents,
        payment_method="stripe",
        status="pending",
        download_url=None,
        expires_at=None,
        created_at=datetime.utcnow(),
        accessed_at=None,
    )
    db.add(purchase)
    db.commit()

    # 3. Create Stripe PaymentIntent
    try:
        intent = stripe.PaymentIntent.create(
            amount=dataset.price_cents,
            currency="usd",
            metadata={
                "purchase_id": purchase_id,
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
            },
            automatic_payment_methods={"enabled": True},
        )
    except Exception as e:
        logger.error(f"Stripe PaymentIntent creation failed: {e}")
        purchase.status = "failed"
        purchase.download_url = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {e}")

    # 4. Update purchase with Stripe intent
    purchase.stripe_invoice_id = intent.id
    db.commit()

    return PurchaseResponse(
        purchase_id=purchase_id,
        stripe_payment_intent_id=intent.id,
        client_secret=intent.client_secret,
        amount_cents=dataset.price_cents,
        currency="usd",
    )


@router.get("/download/{purchase_id}")
def download_dataset(
    purchase_id: str = Path(..., description="Purchase ID"),
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Download purchased dataset.
    
    Requirements:
    - User must own the purchase (JWT authentication via Bearer header or ?token= query param)
    - Purchase must not be expired
    
    Returns:
    - CSV file with proper headers
    """
    try:
        # Resolve token from query param or Authorization header
        resolved_token = token
        if not resolved_token and authorization:
            if authorization.lower().startswith("bearer "):
                resolved_token = authorization[7:]

        if not resolved_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = decode_access_token(resolved_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        current_user = db.query(User).filter(User.email == email).first()
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        user_id = str(current_user.id)
        
        # Verify purchase exists and belongs to user
        purchase = db.query(DatasetPurchase).filter(
            DatasetPurchase.id == purchase_id,
            DatasetPurchase.user_id == user_id,
        ).first()
        
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found",
            )
        
        # Check if purchase is expired (handle both tz-aware and tz-naive)
        from datetime import timezone as _tz
        _now = datetime.now(_tz.utc)
        _expires = purchase.expires_at
        if _expires is not None and _expires.tzinfo is None:
            _expires = _expires.replace(tzinfo=_tz.utc)
        if _expires and _expires < _now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Download link has expired",
            )
        
        # Check if purchase is completed
        if purchase.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Payment not completed",
            )
        
        # Get dataset
        dataset = db.query(Dataset).filter(
            Dataset.id == purchase.dataset_id
        ).first()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )
        
        # Generate CSV if not already stored
        delivery_service = get_delivery_service()
        file_path, row_count = delivery_service.generate_csv_file(dataset, db)
        
        if row_count == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dataset has no matching data. The data may be stale or the filters may be too restrictive. Please contact support.",
            )
        
        # Update access time
        purchase.accessed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"User {user_id} downloaded dataset {dataset.id} (purchase {purchase_id})")
        
        # If file is in cloud storage, redirect to signed URL
        if delivery_service.is_cloud_storage_path(file_path):
            signed_url = delivery_service.generate_download_url(purchase, file_path)
            return RedirectResponse(url=signed_url)
        
        # Return local file — sanitize filename to ASCII for Content-Disposition header
        import unicodedata
        safe_name = unicodedata.normalize('NFKD', dataset.name)
        safe_name = safe_name.encode('ascii', 'ignore').decode('ascii')
        safe_name = safe_name.replace(' ', '_').replace('/', '_')
        safe_name = safe_name or "dataset"
        filename = f"{safe_name}.csv"
        return FileResponse(
            file_path,
            media_type="text/csv; charset=utf-8",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset {purchase_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
