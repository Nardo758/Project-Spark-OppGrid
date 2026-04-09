from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


class BadgeInfo(BaseModel):
    """Badge information"""
    id: str
    name: str
    description: str
    icon: str


class UserBase(BaseModel):
    email: EmailStr
    name: str
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    impact_points: int = 0
    badges: Optional[List[BadgeInfo]] = Field(default_factory=list)
    validation_count: int = 0
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator('impact_points', mode='before')
    @classmethod
    def set_impact_points_default(cls, v):
        """Convert None to 0 for impact_points"""
        return v if v is not None else 0

    @field_validator('badges', mode='before')
    @classmethod
    def parse_badges(cls, v):
        """Convert comma-separated badge string to list of badge objects"""
        if v is None or v == "":
            return []

        if isinstance(v, list):
            return v

        # Import here to avoid circular dependency
        from app.services.badges import BadgeService

        badge_ids = [b.strip() for b in v.split(",") if b.strip()]
        badges = []
        for badge_id in badge_ids:
            badge_info = BadgeService.get_badge_info(badge_id)
            if badge_info:
                badges.append(badge_info)

        return badges
