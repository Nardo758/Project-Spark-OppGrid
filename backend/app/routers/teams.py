"""
Team Management API - January 2026

Endpoints for Business Track team features:
- Team creation and management
- Member invitations
- Team settings and branding
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.models.team import Team, TeamMember, TeamInvitation, TeamRole, InviteStatus
from app.services import team_service
from app.services.branding_service import get_report_branding_preview, is_whitelabel_eligible
from app.services import api_key_service
from app.services import team_collaboration_service

router = APIRouter()


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
    slug: str
    owner_id: int
    max_seats: int
    member_count: int
    seats_available: int
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    api_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_name: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InvitationResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    invite_token: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None
    website_url: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    token: str


@router.post("/", response_model=TeamResponse)
def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new team (Business Track only)"""
    success, message, team = team_service.create_team(current_user, payload.name, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        owner_id=team.owner_id,
        max_seats=team.max_seats,
        member_count=team.member_count,
        seats_available=team.seats_available if team.seats_available >= 0 else 999,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        api_enabled=team.api_enabled,
        created_at=team.created_at
    )


@router.get("/my-team", response_model=Optional[TeamResponse])
def get_my_team(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's team"""
    team = team_service.get_user_team(current_user, db)
    
    if not team:
        return None
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        owner_id=team.owner_id,
        max_seats=team.max_seats,
        member_count=team.member_count,
        seats_available=team.seats_available if team.seats_available >= 0 else 999,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        api_enabled=team.api_enabled,
        created_at=team.created_at
    )


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get team details"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team")
    
    team = member.team
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        owner_id=team.owner_id,
        max_seats=team.max_seats,
        member_count=team.member_count,
        seats_available=team.seats_available if team.seats_available >= 0 else 999,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        api_enabled=team.api_enabled,
        created_at=team.created_at
    )


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    payload: UpdateTeamRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update team settings (admin/owner only)"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update this team")
    
    team = member.team
    
    if payload.name is not None:
        team.name = payload.name
    if payload.logo_url is not None:
        team.logo_url = payload.logo_url
    if payload.primary_color is not None:
        team.primary_color = payload.primary_color
    if payload.company_name is not None:
        team.company_name = payload.company_name
    if payload.website_url is not None:
        team.website_url = payload.website_url
    
    db.commit()
    db.refresh(team)
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        owner_id=team.owner_id,
        max_seats=team.max_seats,
        member_count=team.member_count,
        seats_available=team.seats_available if team.seats_available >= 0 else 999,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        api_enabled=team.api_enabled,
        created_at=team.created_at
    )


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
def get_team_members(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get team members"""
    my_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not my_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team")
    
    members = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.is_active == True
    ).all()
    
    return [
        TeamMemberResponse(
            id=m.id,
            user_id=m.user_id,
            user_email=m.user.email,
            user_name=m.user.name,
            role=m.role.value,
            joined_at=m.joined_at
        )
        for m in members
    ]


@router.post("/{team_id}/invite", response_model=InvitationResponse)
def invite_member(
    team_id: int,
    payload: InviteMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Invite a user to join the team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    try:
        role = TeamRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role. Use 'member' or 'admin'")
    
    success, message, invitation = team_service.invite_member(team, current_user, payload.email, role, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value,
        status=invitation.status.value,
        invite_token=invitation.invite_token,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at
    )


@router.get("/{team_id}/invitations", response_model=List[InvitationResponse])
def get_pending_invitations(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get pending invitations for a team"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view invitations")
    
    invitations = db.query(TeamInvitation).filter(
        TeamInvitation.team_id == team_id,
        TeamInvitation.status == InviteStatus.PENDING
    ).all()
    
    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role.value,
            status=inv.status.value,
            invite_token=inv.invite_token,
            expires_at=inv.expires_at,
            created_at=inv.created_at
        )
        for inv in invitations
    ]


@router.post("/accept-invite")
def accept_invitation(
    payload: AcceptInviteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Accept a team invitation"""
    success, message, team = team_service.accept_invitation(payload.token, current_user, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {
        "message": message,
        "team_id": team.id,
        "team_name": team.name
    }


@router.delete("/{team_id}/members/{user_id}")
def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    success, message = team_service.remove_member(team, current_user, user_id, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


@router.post("/{team_id}/leave")
def leave_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Leave a team"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not a member of this team")
    
    if member.role == TeamRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team owners cannot leave. Transfer ownership first or delete the team.")
    
    member.is_active = False
    db.commit()
    
    return {"message": "You have left the team"}


class BrandingConfig(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None
    website_url: Optional[str] = None


class BrandingResponse(BaseModel):
    team_id: int
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    is_whitelabel_eligible: bool

    class Config:
        from_attributes = True


@router.get("/{team_id}/branding", response_model=BrandingResponse)
def get_branding(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get team branding configuration"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team")
    
    team = member.team
    
    return BrandingResponse(
        team_id=team.id,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        is_whitelabel_eligible=is_whitelabel_eligible(current_user)
    )


@router.patch("/{team_id}/branding", response_model=BrandingResponse)
def update_branding(
    team_id: int,
    payload: BrandingConfig,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update team branding configuration (admin/owner only)"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update branding")
    
    if not is_whitelabel_eligible(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="White-label reports are only available on Business Track plans (Team, Business, Enterprise)"
        )
    
    team = member.team
    
    if payload.logo_url is not None:
        team.logo_url = payload.logo_url
    if payload.primary_color is not None:
        if not payload.primary_color.startswith('#') or len(payload.primary_color) != 7:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid color format. Use hex format like #6366f1")
        team.primary_color = payload.primary_color
    if payload.company_name is not None:
        team.company_name = payload.company_name
    if payload.website_url is not None:
        team.website_url = payload.website_url
    
    db.commit()
    db.refresh(team)
    
    return BrandingResponse(
        team_id=team.id,
        logo_url=team.logo_url,
        primary_color=team.primary_color,
        company_name=team.company_name,
        website_url=team.website_url,
        is_whitelabel_eligible=is_whitelabel_eligible(current_user)
    )


@router.get("/{team_id}/branding/preview")
def preview_branding(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Preview how branded reports will look"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team")
    
    if not is_whitelabel_eligible(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label reports are only available on Business Track plans"
        )
    
    team = member.team
    preview_html = get_report_branding_preview(team)
    
    return {
        "team_id": team.id,
        "preview_html": preview_html,
        "has_logo": bool(team.logo_url),
        "has_company_name": bool(team.company_name),
        "primary_color": team.primary_color or "#6366f1"
    }


class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    scopes: List[str]
    last_used_at: Optional[str] = None
    usage_count: int
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class ApiKeyCreatedResponse(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str
    scopes: List[str]
    message: str


@router.get("/{team_id}/api-keys")
def list_api_keys(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all API keys for a team"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view API keys")
    
    keys = api_key_service.list_api_keys(team_id, db)
    return {"api_keys": keys}


@router.post("/{team_id}/api-keys")
def create_api_key(
    team_id: int,
    payload: CreateApiKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for a team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    success, message, full_key = api_key_service._create_team_api_key(
        team=team,
        user=current_user,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {
        "message": message,
        "key": full_key,
        "key_prefix": full_key[:10] if full_key else None,
        "warning": "Save this key now. You won't be able to see it again."
    }


@router.delete("/{team_id}/api-keys/{key_id}")
def revoke_api_key(
    team_id: int,
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    success, message = api_key_service._revoke_team_api_key(key_id, current_user, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


@router.post("/{team_id}/api-access/enable")
def enable_api_access(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable API access for a team (owner only)"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role != TeamRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owners can enable API access")
    
    team = member.team
    api_key_service.enable_team_api_access(team, rate_limit=100, db=db)
    
    return {"message": "API access enabled", "rate_limit": team.api_rate_limit}


@router.post("/{team_id}/api-access/disable")
def disable_api_access(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disable API access for a team (owner only)"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not member or member.role != TeamRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owners can disable API access")
    
    team = member.team
    api_key_service.disable_team_api_access(team, db)
    
    return {"message": "API access disabled"}


class ShareOpportunityRequest(BaseModel):
    opportunity_id: int
    notes: Optional[str] = None
    priority: Optional[str] = "medium"


class UpdateTeamOpportunityRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class AddNoteRequest(BaseModel):
    content: str


@router.post("/{team_id}/opportunities")
def share_opportunity(
    team_id: int,
    payload: ShareOpportunityRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Share an opportunity with the team"""
    success, message, team_opp = team_collaboration_service.share_opportunity_with_team(
        team_id=team_id,
        opportunity_id=payload.opportunity_id,
        user=current_user,
        notes=payload.notes,
        priority=payload.priority,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {
        "message": message,
        "id": team_opp.id,
        "opportunity_id": team_opp.opportunity_id
    }


@router.get("/{team_id}/opportunities")
def get_team_opportunities(
    team_id: int,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all opportunities shared with the team"""
    success, message, opportunities = team_collaboration_service.get_team_opportunities(
        team_id=team_id,
        user=current_user,
        status_filter=status_filter,
        priority_filter=priority_filter,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    
    return {"opportunities": opportunities}


@router.patch("/{team_id}/opportunities/{team_opp_id}")
def update_team_opportunity(
    team_id: int,
    team_opp_id: int,
    payload: UpdateTeamOpportunityRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a team opportunity's status or priority"""
    success, message = team_collaboration_service.update_team_opportunity_status(
        team_opportunity_id=team_opp_id,
        user=current_user,
        status=payload.status,
        priority=payload.priority,
        notes=payload.notes,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


@router.delete("/{team_id}/opportunities/{team_opp_id}")
def remove_team_opportunity(
    team_id: int,
    team_opp_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove an opportunity from the team"""
    success, message = team_collaboration_service.remove_shared_opportunity(
        team_opportunity_id=team_opp_id,
        user=current_user,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


@router.post("/{team_id}/opportunities/{team_opp_id}/notes")
def add_opportunity_note(
    team_id: int,
    team_opp_id: int,
    payload: AddNoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a note to a team opportunity"""
    success, message, note = team_collaboration_service.add_opportunity_note(
        team_opportunity_id=team_opp_id,
        user=current_user,
        content=payload.content,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {
        "message": message,
        "note_id": note.id
    }


@router.get("/{team_id}/opportunities/{team_opp_id}/notes")
def get_opportunity_notes(
    team_id: int,
    team_opp_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all notes for a team opportunity"""
    success, message, notes = team_collaboration_service.get_opportunity_notes(
        team_opportunity_id=team_opp_id,
        user=current_user,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    
    return {"notes": notes}


@router.get("/{team_id}/activity")
def get_team_activity(
    team_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the team activity feed"""
    success, message, activities = team_collaboration_service.get_team_activity_feed(
        team_id=team_id,
        user=current_user,
        limit=limit,
        offset=offset,
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    
    return {"activities": activities}
