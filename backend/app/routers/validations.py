from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db
from app.models.validation import Validation
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.user_behavior_signal import UserBehaviorSignal
from app.schemas.validation import ValidationCreate, Validation as ValidationSchema
from app.core.dependencies import get_current_active_user
from app.services.badges import BadgeService, award_impact_points
from app.services.notification import notification_service

router = APIRouter()


@router.post("/", response_model=ValidationSchema, status_code=status.HTTP_201_CREATED)
def create_validation(
    validation_data: ValidationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate an opportunity (I Need This Too)"""
    # Check if opportunity exists
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == validation_data.opportunity_id
    ).first()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Create validation
    new_validation = Validation(
        user_id=current_user.id,
        opportunity_id=validation_data.opportunity_id
    )

    try:
        db.add(new_validation)

        # Update opportunity validation count
        opportunity.validation_count = opportunity.validation_count + 1

        # Award impact points for validating
        award_impact_points(current_user, 10, db)

        # Also award points to the opportunity author
        if opportunity.author:
            award_impact_points(opportunity.author, 5, db)

        db.commit()
        db.refresh(new_validation)

        # Send notification to opportunity author
        notification_service.notify_new_validation(
            db=db,
            opportunity_author_id=opportunity.author_id,
            validator_id=current_user.id,
            validator_name=current_user.name,
            opportunity_id=opportunity.id,
            opportunity_title=opportunity.title,
            validation_type="validated"
        )

        # Capture first-party behavior signal
        behavior_signal = UserBehaviorSignal(
            user_id=current_user.id,
            entity_type="opportunity",
            entity_id=opportunity.id,
            action="validated",
            meta={"validation_score": getattr(validation_data, "score", None)},
        )
        db.add(behavior_signal)
        db.commit()

        return new_validation

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already validated this opportunity"
        )


@router.delete("/{validation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation(
    validation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a validation"""
    validation = db.query(Validation).filter(
        Validation.id == validation_id,
        Validation.user_id == current_user.id
    ).first()

    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation not found"
        )

    # Update opportunity validation count
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == validation.opportunity_id
    ).first()

    if opportunity and opportunity.validation_count > 0:
        opportunity.validation_count = opportunity.validation_count - 1

    db.delete(validation)
    db.commit()

    return None


@router.get("/opportunity/{opportunity_id}", response_model=list[ValidationSchema])
def get_opportunity_validations(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """Get all validations for an opportunity"""
    validations = db.query(Validation).filter(
        Validation.opportunity_id == opportunity_id
    ).all()

    return validations
