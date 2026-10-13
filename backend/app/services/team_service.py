"""
Team Management Service - January 2026

Handles team operations for Business Track subscribers:
- Team creation and management
- Member invitations and seat limits
- Tier-based seat allocation
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.team import Team, TeamMember, TeamInvitation, TeamRole, InviteStatus
from app.models.user import User
from app.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)

TIER_SEAT_LIMITS = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.MONTHLY: 1,
    SubscriptionTier.STARTER: 1,
    SubscriptionTier.GROWTH: 1,
    SubscriptionTier.PRO: 1,
    SubscriptionTier.TEAM: 3,
    SubscriptionTier.BUSINESS: 10,
    SubscriptionTier.ENTERPRISE: -1,  # Unlimited
}

BUSINESS_TIERS = [SubscriptionTier.TEAM, SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE]


def is_business_tier(tier: SubscriptionTier) -> bool:
    """Check if tier supports team features"""
    return tier in BUSINESS_TIERS


def get_seat_limit(tier: SubscriptionTier) -> int:
    """Get seat limit for a tier (-1 for unlimited)"""
    return TIER_SEAT_LIMITS.get(tier, 1)


def generate_team_slug(name: str, db: Session) -> str:
    """Generate a unique slug for a team"""
    base_slug = name.lower().replace(' ', '-')[:50]
    base_slug = ''.join(c for c in base_slug if c.isalnum() or c == '-')
    
    slug = base_slug
    counter = 1
    while db.query(Team).filter(Team.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def create_team(
    owner: User,
    name: str,
    db: Session
) -> Tuple[bool, str, Optional[Team]]:
    """
    Create a new team for a user.
    
    Returns (success, message, team)
    """
    if not owner.subscription:
        return False, "You need an active subscription to create a team", None
    
    tier = owner.subscription.tier
    if not is_business_tier(tier):
        return False, "Team features are only available on Business Track plans (Team, Business, Enterprise)", None
    
    existing = db.query(Team).filter(Team.owner_id == owner.id).first()
    if existing:
        return False, "You already have a team. Upgrade to Business or Enterprise for multiple teams.", existing
    
    slug = generate_team_slug(name, db)
    max_seats = get_seat_limit(tier)
    
    try:
        team = Team(
            name=name,
            slug=slug,
            owner_id=owner.id,
            max_seats=max_seats,
            api_enabled=tier in [SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE]
        )
        db.add(team)
        db.flush()
        
        owner_member = TeamMember(
            team_id=team.id,
            user_id=owner.id,
            role=TeamRole.OWNER,
            is_active=True
        )
        db.add(owner_member)
        db.commit()
        db.refresh(team)
        
        logger.info(f"Created team '{name}' (id={team.id}) for user {owner.id}")
        return True, "Team created successfully", team
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating team: {e}")
        return False, "A team with this name already exists", None


def invite_member(
    team: Team,
    inviter: User,
    email: str,
    role: TeamRole,
    db: Session
) -> Tuple[bool, str, Optional[TeamInvitation]]:
    """
    Invite a user to join a team.
    
    Returns (success, message, invitation)
    """
    inviter_member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == inviter.id,
        TeamMember.is_active == True
    ).first()
    
    if not inviter_member or inviter_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        return False, "You don't have permission to invite members", None
    
    if role == TeamRole.OWNER:
        return False, "Cannot invite someone as owner", None
    
    if not team.has_available_seats:
        return False, f"Team has reached its seat limit ({team.max_seats} seats). Upgrade your plan for more seats.", None
    
    existing_member = db.query(TeamMember).join(User).filter(
        TeamMember.team_id == team.id,
        User.email == email,
        TeamMember.is_active == True
    ).first()
    
    if existing_member:
        return False, "This user is already a team member", None
    
    pending_invite = db.query(TeamInvitation).filter(
        TeamInvitation.team_id == team.id,
        TeamInvitation.email == email,
        TeamInvitation.status == InviteStatus.PENDING
    ).first()
    
    if pending_invite:
        return False, "An invitation has already been sent to this email", pending_invite
    
    invite_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = TeamInvitation(
        team_id=team.id,
        email=email,
        role=role,
        status=InviteStatus.PENDING,
        invite_token=invite_token,
        invited_by_id=inviter.id,
        expires_at=expires_at
    )
    
    try:
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        logger.info(f"Invited {email} to team {team.id} with role {role.value}")
        return True, "Invitation sent successfully", invitation
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating invitation: {e}")
        return False, "Failed to create invitation", None


def accept_invitation(
    token: str,
    user: User,
    db: Session
) -> Tuple[bool, str, Optional[Team]]:
    """
    Accept a team invitation.
    
    Returns (success, message, team)
    """
    invitation = db.query(TeamInvitation).filter(
        TeamInvitation.invite_token == token,
        TeamInvitation.status == InviteStatus.PENDING
    ).first()
    
    if not invitation:
        return False, "Invalid or expired invitation", None
    
    if invitation.expires_at < datetime.utcnow():
        invitation.status = InviteStatus.EXPIRED
        db.commit()
        return False, "This invitation has expired", None
    
    if invitation.email.lower() != user.email.lower():
        return False, "This invitation was sent to a different email address", None
    
    team = invitation.team
    
    if not team.has_available_seats:
        return False, "This team has reached its seat limit", None
    
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id
    ).first()
    
    if existing:
        if existing.is_active:
            return False, "You are already a member of this team", team
        else:
            existing.is_active = True
            existing.role = invitation.role
            invitation.status = InviteStatus.ACCEPTED
            invitation.accepted_at = datetime.utcnow()
            invitation.accepted_by_id = user.id
            db.commit()
            return True, "Welcome back to the team!", team
    
    try:
        member = TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=invitation.role,
            is_active=True
        )
        db.add(member)
        
        invitation.status = InviteStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by_id = user.id
        
        db.commit()
        
        logger.info(f"User {user.id} joined team {team.id}")
        return True, f"Welcome to {team.name}!", team
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error accepting invitation: {e}")
        return False, "Failed to join team", None


def remove_member(
    team: Team,
    remover: User,
    member_id: int,
    db: Session
) -> Tuple[bool, str]:
    """
    Remove a member from a team.
    
    Returns (success, message)
    """
    remover_member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == remover.id,
        TeamMember.is_active == True
    ).first()
    
    if not remover_member or remover_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        return False, "You don't have permission to remove members"
    
    target_member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == member_id,
        TeamMember.is_active == True
    ).first()
    
    if not target_member:
        return False, "Member not found"
    
    if target_member.role == TeamRole.OWNER:
        return False, "Cannot remove the team owner"
    
    if target_member.role == TeamRole.ADMIN and remover_member.role != TeamRole.OWNER:
        return False, "Only the owner can remove admins"
    
    target_member.is_active = False
    db.commit()
    
    logger.info(f"User {member_id} removed from team {team.id} by {remover.id}")
    return True, "Member removed successfully"


def get_user_team(user: User, db: Session) -> Optional[Team]:
    """Get the team a user belongs to (as owner or member)"""
    membership = db.query(TeamMember).filter(
        TeamMember.user_id == user.id,
        TeamMember.is_active == True
    ).first()
    
    if membership:
        return membership.team
    return None


def update_team_seats_for_tier(user: User, new_tier: SubscriptionTier, db: Session) -> None:
    """Update team seat limits when subscription tier changes"""
    team = db.query(Team).filter(Team.owner_id == user.id).first()
    if not team:
        return
    
    new_limit = get_seat_limit(new_tier)
    old_limit = team.max_seats
    
    team.max_seats = new_limit
    team.api_enabled = new_tier in [SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE]
    
    db.commit()
    logger.info(f"Updated team {team.id} seats from {old_limit} to {new_limit} for tier {new_tier.value}")
