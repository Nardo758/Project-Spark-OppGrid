from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from cryptography.fernet import Fernet
import os
from app.db.database import Base


def get_fernet():
    """Get Fernet instance for encryption/decryption.
    
    Raises RuntimeError if ENCRYPTION_KEY is not set to prevent
    data loss from generating ephemeral keys.
    """
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY environment variable is required for API key encryption. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # OAuth
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github', etc.
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID

    # Statistics
    impact_points = Column(Integer, default=0)

    # Badges (stored as comma-separated values)
    badges = Column(Text, nullable=True)

    # Verification
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Password Reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Magic Link
    magic_link_token = Column(String(255), nullable=True)
    magic_link_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Two-Factor Authentication
    otp_secret = Column(String(32), nullable=True)
    otp_enabled = Column(Boolean, default=False)
    backup_codes = Column(Text, nullable=True)  # Comma-separated encrypted backup codes

    # BYOK (Bring Your Own Key) - Encrypted API keys
    encrypted_claude_api_key = Column(Text, nullable=True)  # Fernet-encrypted Claude API key
    claude_key_validated_at = Column(DateTime(timezone=True), nullable=True)  # When key was last validated

    # Account settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    opportunities = relationship("Opportunity", back_populates="author")
    validations = relationship("Validation", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    report_quotas = relationship("UserReportQuota", back_populates="user", cascade="all, delete-orphan")
    slot_balance = relationship("UserSlotBalance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    generated_reports = relationship("GeneratedReport", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("UserWorkspace", back_populates="user", cascade="all, delete-orphan")
    enhanced_workspaces = relationship("EnhancedUserWorkspace", back_populates="user", cascade="all, delete-orphan")
    custom_workflows = relationship("CustomWorkflow", back_populates="creator", cascade="all, delete-orphan")
    collections = relationship("UserCollection", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("UserTag", back_populates="user", cascade="all, delete-orphan")
    opportunity_notes = relationship("OpportunityNote", back_populates="user", cascade="all, delete-orphan")
    copilot_messages = relationship("GlobalChatMessage", back_populates="user", cascade="all, delete-orphan", order_by="GlobalChatMessage.created_at")
    monthly_report_usage = relationship("MonthlyReportUsage", back_populates="user", cascade="all, delete-orphan")
    ai_preference = relationship("UserAIPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ai_usage = relationship("UserAIUsage", back_populates="user", cascade="all, delete-orphan")


class UserAIPreference(Base):
    """User AI provider preferences for the Dual-Realm Workspace"""
    __tablename__ = "user_ai_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    provider = Column(String(50), default="claude")
    mode = Column(String(50), default="replit")
    model = Column(String(100), nullable=True)
    
    encrypted_openai_api_key = Column(Text, nullable=True)
    openai_key_validated_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="ai_preference")
    
    def set_openai_api_key(self, api_key: str):
        """Encrypt and store OpenAI API key"""
        if api_key:
            fernet = get_fernet()
            self.encrypted_openai_api_key = fernet.encrypt(api_key.encode()).decode()
    
    def get_openai_api_key(self) -> str | None:
        """Decrypt and return OpenAI API key"""
        if self.encrypted_openai_api_key:
            try:
                fernet = get_fernet()
                return fernet.decrypt(self.encrypted_openai_api_key.encode()).decode()
            except Exception:
                return None
        return None
    
    def get_api_key(self) -> str | None:
        """Get the appropriate API key based on provider"""
        if self.provider == "openai":
            return self.get_openai_api_key()
        elif self.provider == "claude":
            if self.user and hasattr(self.user, 'encrypted_claude_api_key') and self.user.encrypted_claude_api_key:
                try:
                    fernet = get_fernet()
                    return fernet.decrypt(self.user.encrypted_claude_api_key.encode()).decode()
                except Exception:
                    return None
        return None
