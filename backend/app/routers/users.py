import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.user import User
from app.models.validation import Validation
from app.schemas.user import User as UserSchema, UserUpdate, BadgeInfo
from app.core.dependencies import get_current_active_user
from app.core.security import verify_password, get_password_hash
from app.services.badges import BadgeService

router = APIRouter()

DEFAULT_NOTIFICATION_PREFS = {
    "newOpportunities": True,
    "validationUpdates": True,
    "weeklyDigest": False,
    "productUpdates": True,
}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class NotificationPrefsUpdate(BaseModel):
    newOpportunities: Optional[bool] = None
    validationUpdates: Optional[bool] = None
    weeklyDigest: Optional[bool] = None
    productUpdates: Optional[bool] = None


def enrich_user_with_stats(user: User, db: Session) -> User:
    """Add computed stats to user object"""
    validation_count = db.query(Validation).filter(Validation.user_id == user.id).count()
    user.validation_count = validation_count
    return user


def _load_notification_prefs(user: User) -> dict:
    if user.notification_preferences:
        try:
            stored = json.loads(user.notification_preferences)
            prefs = dict(DEFAULT_NOTIFICATION_PREFS)
            prefs.update(stored)
            return prefs
        except Exception:
            pass
    return dict(DEFAULT_NOTIFICATION_PREFS)


@router.get("/me", response_model=UserSchema)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with stats"""
    BadgeService.check_and_award_badges(current_user, db)
    db.commit()
    return enrich_user_with_stats(current_user, db)


@router.put("/me", response_model=UserSchema)
def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user profile"""
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return enrich_user_with_stats(current_user, db)


@router.post("/me/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password (requires current password)"""
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change is not available for accounts created via social login."
        )
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long."
        )
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@router.get("/me/preferences")
def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's notification preferences"""
    return _load_notification_prefs(current_user)


@router.put("/me/preferences")
def update_notification_preferences(
    prefs: NotificationPrefsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences"""
    current = _load_notification_prefs(current_user)
    update_data = prefs.model_dump(exclude_unset=True)
    current.update(update_data)
    current_user.notification_preferences = json.dumps(current)
    db.commit()
    return current


@router.delete("/me")
def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Permanently delete the current user's account and all associated data"""
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully."}


@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return enrich_user_with_stats(user, db)


@router.get("/me/badges/available", response_model=List[BadgeInfo])
def get_available_badges():
    """Get all available badges"""
    return BadgeService.get_all_badges()


@router.post("/me/badges/check")
def check_badges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check and award new badges for current user"""
    newly_awarded = BadgeService.check_and_award_badges(current_user, db)
    db.commit()
    return {
        "newly_awarded": newly_awarded,
        "total_badges": len(BadgeService.get_user_badges(current_user))
    }
