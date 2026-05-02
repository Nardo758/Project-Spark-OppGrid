from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, UserUpdate
from app.schemas.token import Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.core.tokens import (
    generate_verification_token,
    get_verification_token_expiry,
    generate_password_reset_token,
    get_password_reset_token_expiry,
    is_token_expired
)
from app.services.email import email_service

logger = logging.getLogger(__name__)
router = APIRouter()


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class RequestPasswordResetRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send verification email"""
    logger.info(f"[Auth] Registration attempt for email: {user_data.email[:3]}***")
    
    # Check if user exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        logger.warning(f"[Auth] Registration failed - email already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Generate verification token
    verification_token = generate_verification_token()
    token_expiry = get_verification_token_expiry()

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        bio=user_data.bio,
        hashed_password=hashed_password,
        verification_token=verification_token,
        verification_token_expires=token_expiry,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"[Auth] User registered successfully: id={new_user.id}")

    # Send verification email
    try:
        email_service.send_verification_email(
            to_email=new_user.email,
            verification_token=verification_token,
            user_name=new_user.name
        )
        logger.info(f"[Auth] Verification email sent to user id={new_user.id}")
    except Exception as e:
        logger.error(f"[Auth] Failed to send verification email: {e}")

    return new_user


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    logger.info(f"[Auth] Login attempt for email: {form_data.username[:3]}***")
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"[Auth] Login failed - invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"[Auth] Login failed - inactive user id={user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Check if 2FA is enabled
    if user.otp_enabled:
        logger.info(f"[Auth] 2FA required for user id={user.id}")
        return {
            "requires_2fa": True,
            "email": user.email,
            "message": "Please provide your 2FA code"
        }

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    from app.models.subscription import Subscription
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    tier = subscription.tier.value.lower() if subscription and subscription.tier else "free"
    
    logger.info(f"[Auth] Login successful: user_id={user.id}, tier={tier}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_2fa": False,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.name,
            "is_verified": user.is_verified,
            "is_admin": user.is_admin,
            "tier": tier
        }
    }


@router.post("/verify-email")
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify user's email address using token"""
    user = db.query(User).filter(User.verification_token == request.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    if user.is_verified:
        return {
            "message": "Email already verified",
            "already_verified": True
        }

    # Check if token is expired
    if is_token_expired(user.verification_token_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )

    # Verify the user
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None

    db.commit()

    return {
        "message": "Email verified successfully",
        "email": user.email
    }


@router.post("/resend-verification")
def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email to user"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Don't reveal if email exists or not for security
        return {
            "message": "If the email exists and is not verified, a verification email will be sent"
        }

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Generate new verification token
    verification_token = generate_verification_token()
    token_expiry = get_verification_token_expiry()

    user.verification_token = verification_token
    user.verification_token_expires = token_expiry

    db.commit()

    # Send verification email
    try:
        email_service.send_verification_email(
            to_email=user.email,
            verification_token=verification_token,
            user_name=user.name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

    return {
        "message": "Verification email sent successfully"
    }


@router.post("/request-password-reset")
def request_password_reset(request: RequestPasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset email"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Don't reveal if email exists or not for security
        return {
            "message": "If the email exists, a password reset link will be sent"
        }

    # Generate password reset token
    reset_token = generate_password_reset_token()
    token_expiry = get_password_reset_token_expiry()

    user.password_reset_token = reset_token
    user.password_reset_token_expires = token_expiry

    db.commit()

    # Send password reset email
    try:
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )

    return {
        "message": "Password reset email sent successfully"
    }


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using token"""
    user = db.query(User).filter(User.password_reset_token == request.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token"
        )

    # Check if token is expired
    if is_token_expired(user.password_reset_token_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired. Please request a new one."
        )

    # Validate new password length
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None

    db.commit()

    return {
        "message": "Password reset successfully",
        "email": user.email
    }


@router.get("/profile", response_model=UserSchema)
def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    return current_user


@router.put("/profile", response_model=UserSchema)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    logger.info(f"[Auth] Updating profile for user id={current_user.id}")
    
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    logger.info(f"[Auth] Profile updated for user id={current_user.id}")
    
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint (token invalidation handled by client)"""
    logger.info(f"[Auth] User logged out: user_id={current_user.id}")
    
    return {
        "message": "Successfully logged out",
        "success": True
    }
