"""Dataset marketplace API endpoints with Stripe payment integration."""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Path, Query, Header
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import stripe

from app.db.database import get_db
from app.models.dataset import Dataset, DatasetPurchase, DatasetType
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

def _get_user_id_from_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from JWT token.
    
    For now, we use a simple extraction. In production, this would validate
    the JWT token properly.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    
    # In production, parse JWT token to extract user_id
    # For development, use a test user ID
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Simple mock: if token is valid format, extract user_id from it
    # In production, use JWT.decode() to validate
    if len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    
    # For testing: use token as simple identifier
    user_id = token[:36] if len(token) >= 36 else f"user-{token[:8]}"
    return user_id


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
    db: Session = Depends(get_db),
    x_agent_key: Optional[str] = Header(None),
) -> List[dict]:
    """
    List available datasets for purchase.
    
    Query Parameters:
    - vertical: Filter by vertical (coffee, restaurants, etc.)
    - city: Filter by city
    - dataset_type: Filter by type (opportunities, markets, trends, raw_data)
    """
    try:
        # Build query
        query = db.query(Dataset).filter(Dataset.is_active == True)
        
        if vertical:
            query = query.filter(Dataset.vertical == vertical)
        if city:
            query = query.filter(Dataset.city == city)
        if dataset_type:
            query = query.filter(Dataset.dataset_type == dataset_type)
        
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
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> PurchaseListResponse:
    """Get list of user's purchased datasets. (Declared early to avoid /{dataset_id} wildcard.)"""
    return list_purchases(authorization=authorization, db=db)


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
            if dataset.dataset_type == DatasetType.OPPORTUNITIES.value or dataset.dataset_type == DatasetType.OPPORTUNITIES:
                rows = delivery._generate_mock_opportunities(dataset)
                columns = ['id', 'title', 'vertical', 'city', 'success_probability',
                           'confidence', 'risk_profile', 'market_health', 'trend_momentum', 'reasoning']
            elif dataset.dataset_type == DatasetType.MARKETS.value or dataset.dataset_type == DatasetType.MARKETS:
                rows = delivery._generate_mock_markets(dataset)
                columns = ['vertical', 'city', 'market_health_score', 'saturation_level',
                           'demand_vs_supply', 'business_count', 'growth_rate', 'confidence']
            elif dataset.dataset_type == DatasetType.TRENDS.value or dataset.dataset_type == DatasetType.TRENDS:
                rows = delivery._generate_mock_trends(dataset)
                columns = ['trend_name', 'vertical', 'acceleration_factor', 'direction',
                           'signal_count', 'confidence', 'top_cities']
            elif dataset.dataset_type == DatasetType.RAW_DATA.value or dataset.dataset_type == DatasetType.RAW_DATA:
                rows = delivery._generate_mock_raw_data(dataset)
                columns = ['source_type', 'external_id', 'title', 'description', 'processed',
                           'received_at', 'observed_at']
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


@router.post("/purchase", response_model=PurchaseResponse)
def purchase_dataset(
    request: PurchaseRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> PurchaseResponse:
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
    try:
        # 1. Authenticate user
        user_id = _get_user_id_from_token(authorization)
        logger.info(f"Purchase initiated by user {user_id} for dataset {request.dataset_id}")
        
        # 2. Get dataset details
        dataset = db.query(Dataset).filter(
            Dataset.id == request.dataset_id,
            Dataset.is_active == True
        ).first()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found or not available for purchase",
            )
        
        # Check if user already has access to this dataset (optional)
        existing_purchase = db.query(DatasetPurchase).filter(
            DatasetPurchase.user_id == user_id,
            DatasetPurchase.dataset_id == request.dataset_id,
            DatasetPurchase.status == "completed",
            DatasetPurchase.expires_at > datetime.utcnow()
        ).first()
        
        if existing_purchase:
            logger.warning(f"User {user_id} already has access to dataset {request.dataset_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have access to this dataset",
            )
        
        # 3. Create Stripe PaymentIntent
        payment_details = _create_stripe_payment_intent(
            amount_cents=dataset.price_cents,
            dataset_id=request.dataset_id,
            user_id=user_id,
        )
        
        # 4. Create purchase record (status: pending)
        purchase_id = str(uuid.uuid4())
        purchase = DatasetPurchase(
            id=purchase_id,
            dataset_id=request.dataset_id,
            user_id=user_id,
            price_cents=dataset.price_cents,
            payment_method="stripe",
            stripe_invoice_id=payment_details["payment_intent_id"],
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=24),  # Expires in 24 hours
        )
        db.add(purchase)
        db.commit()
        
        logger.info(f"Created pending purchase {purchase_id} with Stripe intent {payment_details['payment_intent_id']}")
        
        return PurchaseResponse(
            purchase_id=purchase_id,
            stripe_payment_intent_id=payment_details["payment_intent_id"],
            client_secret=payment_details["client_secret"],
            amount_cents=dataset.price_cents,
            currency="usd",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating purchase: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/my-purchases", response_model=PurchaseListResponse)
def list_purchases(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> PurchaseListResponse:
    """
    Get list of user's purchased datasets.
    
    Response:
    {
        "purchases": [
            {
                "purchase_id": "purchase-123",
                "dataset_id": "dataset-456",
                "dataset_name": "Coffee Markets in Austin",
                "price_cents": 9900,
                "purchased_at": "2024-04-30T10:30:00Z",
                "expires_at": "2024-05-01T10:30:00Z",
                "download_url": "/api/v1/datasets/download/purchase-123",
                "status": "completed"
            }
        ],
        "total_count": 1
    }
    """
    try:
        # Authenticate user
        user_id = _get_user_id_from_token(authorization)
        
        # Get user's purchases
        purchases = db.query(DatasetPurchase).filter(
            DatasetPurchase.user_id == user_id,
        ).order_by(DatasetPurchase.created_at.desc()).all()
        
        purchase_list = []
        for purchase in purchases:
            # Get dataset info
            dataset = db.query(Dataset).filter(
                Dataset.id == purchase.dataset_id
            ).first()
            
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
        
        return PurchaseListResponse(
            purchases=purchase_list,
            total_count=len(purchase_list),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving purchases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
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
    - User must own the purchase (JWT authentication)
    - Purchase must not be expired
    
    Returns:
    - CSV file with proper headers
    """
    try:
        # Authenticate user
        user_id = _get_user_id_from_token(authorization)
        
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
        
        # Return file
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
