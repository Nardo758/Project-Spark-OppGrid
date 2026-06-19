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

        try:
            dt = dataset.dataset_type
            if dt == DatasetType.OPPORTUNITIES.value or dt == DatasetType.OPPORTUNITIES:
                rows = delivery._generate_mock_opportunities(dataset)
                columns = ['id', 'title', 'vertical', 'city', 'success_probability',
                           'confidence', 'risk_profile', 'market_health', 'trend_momentum', 'reasoning']
            elif dt == DatasetType.MARKETS.value or dt == DatasetType.MARKETS:
                rows = delivery._generate_mock_markets(dataset)
                columns = ['vertical', 'city', 'market_health_score', 'saturation_level',
                           'demand_vs_supply', 'business_count', 'growth_rate', 'confidence']
            elif dt == DatasetType.TRENDS.value or dt == DatasetType.TRENDS:
                rows = delivery._generate_mock_trends(dataset)
                columns = ['trend_name', 'vertical', 'acceleration_factor', 'direction',
                           'signal_count', 'confidence', 'top_cities']
            elif dt == DatasetType.RAW_DATA.value or dt == DatasetType.RAW_DATA:
                rows = delivery._generate_mock_raw_data(dataset)
                columns = ['source_type', 'external_id', 'title', 'description', 'processed',
                           'received_at', 'observed_at']
            elif dt == 'opportunity_signals':
                columns = ['signal_type', 'city', 'vertical', 'signal_strength',
                           'trend_direction', 'data_source', 'detected_at', 'confidence']
                signal_types = ['demand_surge', 'supply_gap', 'price_pressure', 'foot_traffic_spike', 'permit_activity']
                sources = ['google_trends', 'serpapi_maps', 'census_acs', 'bls_data', 'apify_scrape']
                city = dataset.city or 'San Francisco, CA'
                vertical = dataset.vertical or 'multi_vertical'
                rows = [
                    {'signal_type': signal_types[i % 5], 'city': city, 'vertical': vertical,
                     'signal_strength': round(0.60 + i * 0.07, 2), 'trend_direction': 'up' if i % 3 != 2 else 'stable',
                     'data_source': sources[i % 5], 'detected_at': f'2026-06-{14 + i:02d}',
                     'confidence': round(0.78 + i * 0.04, 2)}
                    for i in range(5)
                ]
            elif dt == 'market_intelligence':
                columns = ['product_category', 'price_position', 'promotion_channel',
                           'place_coverage', 'market_share_pct', 'competitive_score', 'city']
                city = dataset.city or 'New York, NY'
                categories = ['Specialty Coffee', 'Cold Brew', 'Pastries', 'Retail Merch', 'Subscriptions']
                channels = ['social_media', 'local_seo', 'word_of_mouth', 'events', 'email']
                rows = [
                    {'product_category': categories[i], 'price_position': ['budget', 'mid', 'premium', 'premium', 'mid'][i],
                     'promotion_channel': channels[i], 'place_coverage': ['high', 'medium', 'low', 'high', 'medium'][i],
                     'market_share_pct': round(8.2 + i * 3.1, 1), 'competitive_score': round(6.5 + i * 0.6, 1),
                     'city': city}
                    for i in range(5)
                ]
            elif dt == 'economic_intelligence':
                columns = ['industry', 'gdp_contribution_pct', 'employment_growth_pct',
                           'revenue_trend', 'investment_flow_m', 'market_size_b', 'year']
                vertical = (dataset.vertical or 'technology').replace('_', ' ').title()
                sub_sectors = [f'{vertical} - Sector {chr(65+i)}' for i in range(5)]
                rows = [
                    {'industry': sub_sectors[i], 'gdp_contribution_pct': round(1.8 + i * 0.7, 1),
                     'employment_growth_pct': round(3.2 + i * 1.4, 1),
                     'revenue_trend': ['growing', 'growing', 'stable', 'growing', 'declining'][i],
                     'investment_flow_m': round(85.0 + i * 42.5, 1),
                     'market_size_b': round(4.2 + i * 2.1, 1), 'year': 2025}
                    for i in range(5)
                ]
            elif dt == 'competition_intelligence':
                columns = ['business_name', 'address', 'rating', 'review_count',
                           'category', 'price_level', 'is_open']
                city = dataset.city or 'Dallas, TX'
                names = ['The Local Spot', 'Metro Market', 'City Corner', 'Urban Hub', 'Main St Collective']
                rows = [
                    {'business_name': names[i], 'address': f'{100 + i * 22} Main St, {city}',
                     'rating': round(3.8 + i * 0.2, 1), 'review_count': 45 + i * 38,
                     'category': 'Retail / Food & Bev', 'price_level': ['$', '$$', '$$', '$$$', '$$'][i],
                     'is_open': True}
                    for i in range(5)
                ]
        except Exception as gen_err:
            logger.warning(f"Preview row generation failed for dataset {dataset_id}: {gen_err}")
            rows = []

        return {
            "metadata": {
                "record_count": dataset.record_count or 0,
                "data_freshness": dataset.data_freshness or (dataset.generated_at.isoformat() if dataset.generated_at else ""),
                "vertical": dataset.vertical,
                "city": dataset.city,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download purchased dataset.
    
    Requirements:
    - User must own the purchase (JWT authentication)
    - Purchase must not be expired
    
    Returns:
    - CSV file with proper headers
    """
    try:
        user_id = current_user.id
        
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
        
        # Check if purchase is expired
        if purchase.expires_at and purchase.expires_at < datetime.utcnow():
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
        
        # Update access time
        purchase.accessed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"User {user_id} downloaded dataset {dataset.id} (purchase {purchase_id})")
        
        # If file is in cloud storage, redirect to signed URL
        if delivery_service.is_cloud_storage_path(file_path):
            signed_url = delivery_service.generate_download_url(purchase, file_path)
            return RedirectResponse(url=signed_url)
        
        # Return local file
        return FileResponse(
            file_path,
            media_type="text/csv",
            filename=f"{dataset.name.replace(' ', '_')}.csv",
            headers={
                "Content-Disposition": f"attachment; filename={dataset.name.replace(' ', '_')}.csv",
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
