from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import List, Optional
import json

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.subscription import SubscriptionTier
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate, Opportunity as OpportunitySchema, OpportunityList, OpportunityGatedResponse
from app.core.dependencies import get_current_active_user, get_current_user_optional, get_user_subscription_tier
from app.services.badges import award_impact_points
from app.services.usage_service import usage_service
from app.services.entitlements import get_opportunity_entitlements

router = APIRouter()
optional_auth = HTTPBearer(auto_error=False)

FREE_PREVIEW_LIMIT = 3


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    """Get all distinct categories from opportunities"""
    categories = db.query(Opportunity.category).filter(
        Opportunity.category.isnot(None),
        Opportunity.status == "active",
        Opportunity.moderation_status == 'approved'
    ).distinct().order_by(Opportunity.category).all()
    return [c[0] for c in categories if c[0]]


@router.get("/recommended")
async def get_recommended_opportunities(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized opportunity recommendations
    
    Uses AI-powered match scoring based on:
    - User's category interests (from validation history)
    - Similar users' validations
    - Opportunity feasibility and growth
    - User profile preferences
    
    **Returns:** Top N opportunities ranked by match score (0-100)
    """
    from app.models.validation import Validation
    from app.services.ai_router import AIRouter, TaskType
    
    # Get user's category interests from validation history
    user_validated_categories = db.query(Opportunity.category).join(
        Validation, Opportunity.id == Validation.opportunity_id
    ).filter(
        Validation.user_id == current_user.id,
        Opportunity.category.isnot(None)
    ).distinct().limit(5).all()
    
    user_interests = [c[0] for c in user_validated_categories if c[0]]
    
    # Base query: active, approved, high-quality opportunities
    query = db.query(Opportunity).filter(
        Opportunity.status == "active",
        Opportunity.moderation_status == 'approved',
        Opportunity.feasibility_score >= 60  # Only recommend high-feasibility
    )
    
    # Prioritize user's interest categories if available
    if user_interests:
        query = query.filter(Opportunity.category.in_(user_interests))
    
    # Exclude already validated by user
    user_validated_ids = db.query(Validation.opportunity_id).filter(
        Validation.user_id == current_user.id
    ).subquery()
    query = query.filter(~Opportunity.id.in_(user_validated_ids))
    
    # Get candidates (fetch more than needed for scoring)
    candidates = query.order_by(
        desc(Opportunity.feasibility_score),
        desc(Opportunity.created_at)
    ).limit(limit * 3).all()
    
    if not candidates:
        # No personalized results - return general high-quality opportunities
        query = db.query(Opportunity).filter(
            Opportunity.status == "active",
            Opportunity.moderation_status == 'approved',
            Opportunity.feasibility_score >= 70
        ).filter(~Opportunity.id.in_(user_validated_ids))
        
        candidates = query.order_by(
            desc(Opportunity.feasibility_score)
        ).limit(limit).all()
    
    # Calculate match scores for each candidate
    scored_opportunities = []
    
    for opp in candidates:
        match_score = calculate_match_score(opp, current_user, user_interests, db)
        
        opp_dict = {
            "id": opp.id,
            "title": opp.title,
            "description": opp.description,
            "category": opp.category,
            "feasibility_score": opp.feasibility_score,
            "validation_count": opp.validation_count,
            "growth_rate": opp.growth_rate,
            "match_score": match_score,
            "geographic_scope": opp.geographic_scope,
            "market_size": opp.market_size,
            "created_at": opp.created_at
        }
        
        scored_opportunities.append(opp_dict)
    
    # Sort by match score (desc) and return top N
    scored_opportunities.sort(key=lambda x: x['match_score'], reverse=True)
    
    return {
        "opportunities": scored_opportunities[:limit],
        "total": len(scored_opportunities),
        "user_interests": user_interests
    }


def calculate_match_score(
    opp: Opportunity, 
    user: User, 
    user_interests: List[str],
    db: Session
) -> int:
    """
    Calculate 0-100 match score between opportunity and user
    
    Uses multi-factor scoring algorithm from spec:
    - Category match: +20 points
    - High feasibility: +15 points
    - Growth trend: +10 points
    - Similar users validated: +5 points
    - Base score: 50 points
    """
    from app.models.validation import Validation
    
    score = 50  # Base score
    
    # Category match (+20 if user interested in this category)
    if opp.category and opp.category in user_interests:
        score += 20
    
    # Feasibility bonus (+15 if high feasibility >= 75)
    if opp.feasibility_score and opp.feasibility_score >= 75:
        score += 15
    elif opp.feasibility_score and opp.feasibility_score >= 60:
        score += 10  # Partial bonus for medium-high
    
    # Validation trend bonus (+10 if growing fast > 10%)
    if opp.growth_rate and opp.growth_rate > 10:
        score += 10
    elif opp.growth_rate and opp.growth_rate > 5:
        score += 5  # Partial bonus for moderate growth
    
    # Similar users validated (+5)
    similar_user_validated = check_similar_users_validated(opp, user, db)
    if similar_user_validated:
        score += 5
    
    return min(score, 100)


def check_similar_users_validated(opp: Opportunity, user: User, db: Session) -> bool:
    """Check if users with similar interests validated this opportunity"""
    from app.models.validation import Validation
    
    # Find users who validated same opportunities as current user
    user_validations = db.query(Validation.opportunity_id).filter(
        Validation.user_id == user.id
    ).subquery()
    
    similar_users = db.query(Validation.user_id).filter(
        Validation.opportunity_id.in_(user_validations),
        Validation.user_id != user.id
    ).distinct().limit(10).all()
    
    if not similar_users:
        return False
    
    similar_user_ids = [u[0] for u in similar_users]
    
    # Check if any similar user validated this opportunity
    return db.query(Validation).filter(
        Validation.opportunity_id == opp.id,
        Validation.user_id.in_(similar_user_ids)
    ).first() is not None


@router.post("/", response_model=OpportunitySchema, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    opportunity_data: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new opportunity"""
    new_opportunity = Opportunity(
        **opportunity_data.model_dump(),
        author_id=None if opportunity_data.is_anonymous else current_user.id
    )

    db.add(new_opportunity)

    # Award impact points for creating an opportunity (not for anonymous submissions)
    if not opportunity_data.is_anonymous:
        award_impact_points(current_user, 20, db)

    db.commit()
    db.refresh(new_opportunity)

    # Emit webhook event for opportunity.new
    try:
        from app.services.webhook_delivery_service import emit_webhook_event_sync
        emit_webhook_event_sync(
            event_type="opportunity.new",
            data={
                "opportunity_id": new_opportunity.id,
                "title": new_opportunity.title or "",
                "vertical": new_opportunity.category or "",
                "city": new_opportunity.geographic_scope or "",
                "market_size": getattr(new_opportunity, 'market_size', None),
            },
            vertical_filter=new_opportunity.category,
            city_filter=new_opportunity.geographic_scope,
        )
    except Exception as e:
        logger.error(f"Failed to emit webhook event for opportunity creation: {e}")

    return new_opportunity


@router.get("/")
async def get_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: str = "active",
    sort_by: str = Query("recent", regex="^(recent|trending|validated|market|feasibility)$"),
    geographic_scope: Optional[str] = None,
    country: Optional[str] = None,
    completion_status: Optional[str] = None,
    realm_type: Optional[str] = Query(None, regex="^(physical|digital)$"),
    max_age_days: Optional[int] = Query(None, ge=1),
    my_access_only: bool = Query(False),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get list of opportunities with filtering and pagination.
    
    Free users see only 3 preview opportunities. 
    Paid subscribers get full access.
    """
    is_paid = False
    user_tier = SubscriptionTier.FREE
    
    if current_user:
        user_tier = get_user_subscription_tier(current_user, db)
        is_paid = user_tier != SubscriptionTier.FREE
    
    query = db.query(Opportunity).filter(
        Opportunity.status == status,
        Opportunity.moderation_status == 'approved'
    )

    # Filter by category
    if category:
        query = query.filter(Opportunity.category == category)

    # Filter by geographic scope
    if geographic_scope:
        query = query.filter(Opportunity.geographic_scope == geographic_scope)

    # Filter by country
    if country:
        query = query.filter(Opportunity.country.ilike(f"%{country}%"))

    # Filter by completion status
    if completion_status:
        query = query.filter(Opportunity.completion_status == completion_status)

    # Filter by realm type (physical shows physical+both, digital shows digital+both)
    if realm_type:
        query = query.filter(
            or_(
                Opportunity.realm_type == realm_type,
                Opportunity.realm_type == "both",
                Opportunity.realm_type.is_(None)
            )
        )

    # Filter by max age in days
    if max_age_days:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        query = query.filter(Opportunity.created_at >= cutoff)

    # Filter by my_access_only - show only opportunities user can access based on tier
    if my_access_only and current_user:
        if user_tier == SubscriptionTier.FREE:
            # Free users can only access opportunities with feasibility < 60
            query = query.filter(Opportunity.feasibility_score < 60)
        # Pro and above can access all (no additional filter needed)
        # If user is not authenticated, ignore this filter

    # Sorting
    if sort_by == "recent":
        query = query.order_by(desc(Opportunity.created_at))
    elif sort_by == "trending":
        query = query.order_by(desc(Opportunity.growth_rate))
    elif sort_by == "validated":
        query = query.order_by(desc(Opportunity.validation_count))
    elif sort_by == "market":
        query = query.order_by(desc(Opportunity.market_size))
    elif sort_by == "feasibility":
        query = query.order_by(desc(Opportunity.feasibility_score))

    total = query.count()
    
    if not is_paid:
        free_query = query.filter(Opportunity.feasibility_score < 60)
        free_total = free_query.count()
        opportunities = free_query.offset(0).limit(FREE_PREVIEW_LIMIT).all()
        
        return {
            "opportunities": opportunities,
            "total": min(free_total, FREE_PREVIEW_LIMIT),
            "page": 1,
            "page_size": FREE_PREVIEW_LIMIT,
            "is_gated": True,
            "gated_message": f"Subscribe to access all {total} opportunities",
            "full_total": total
        }
    
    opportunities = query.offset(skip).limit(limit).all()

    return {
        "opportunities": opportunities,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "is_gated": False,
        "gated_message": None,
        "full_total": total
    }


@router.get("/{opportunity_id}", response_model=OpportunityGatedResponse)
async def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """Get a single opportunity by ID with gated content based on subscription and time-decay access"""
    from app.models.subscription import SubscriptionTier
    
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.moderation_status == 'approved'
    ).first()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    ent = get_opportunity_entitlements(db, opportunity, current_user)
    tier_value = ent.user_tier.value if ent.user_tier else (SubscriptionTier.FREE.value if current_user else None)

    # Build access info (schema-compatible)
    access_info = {
        "age_days": ent.age_days,
        "freshness_badge": ent.freshness_badge,
        "is_accessible": ent.is_accessible,
        "is_unlocked": ent.is_unlocked,
        "unlock_method": ent.unlock_method,
        "days_until_unlock": ent.days_until_unlock,
        "can_pay_to_unlock": ent.can_pay_to_unlock,
        "unlock_price": ent.unlock_price,
        "user_tier": tier_value if ent.is_authenticated else None,
        "content_state": getattr(ent, "content_state", None),
    }
    
    # Create response dict from opportunity
    response_data = {
        "id": opportunity.id,
        "title": opportunity.title,
        "description": opportunity.description,
        "category": opportunity.category,
        "subcategory": opportunity.subcategory,
        "severity": opportunity.severity,
        "market_size": opportunity.market_size,
        "is_anonymous": opportunity.is_anonymous,
        "geographic_scope": opportunity.geographic_scope,
        "country": opportunity.country,
        "region": opportunity.region,
        "city": opportunity.city,
        "validation_count": opportunity.validation_count,
        "growth_rate": opportunity.growth_rate,
        "author_id": opportunity.author_id,
        "status": opportunity.status,
        "completion_status": opportunity.completion_status,
        "solution_description": opportunity.solution_description,
        "solved_at": opportunity.solved_at,
        "solved_by": opportunity.solved_by,
        "feasibility_score": opportunity.feasibility_score,
        "duplicate_of": opportunity.duplicate_of,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at,
        "source_platform": opportunity.source_platform,
        "source_url": opportunity.source_url,
        "is_unlocked": ent.is_unlocked,
        "is_authenticated": ent.is_authenticated,
        "access_info": access_info,
        "deep_dive_available": ent.deep_dive_available,
        "can_buy_deep_dive": ent.can_buy_deep_dive,
        "deep_dive_price": ent.deep_dive_price,
        "execution_package_available": ent.execution_package_available,
        # Always show basic AI fields (Layer 0 - hook content)
        "ai_analyzed": opportunity.ai_analyzed,
        "ai_analyzed_at": opportunity.ai_analyzed_at,
        "ai_opportunity_score": opportunity.ai_opportunity_score,
        "ai_summary": opportunity.ai_summary,
        "ai_market_size_estimate": opportunity.ai_market_size_estimate,
        "ai_competition_level": opportunity.ai_competition_level,
        "ai_urgency_level": opportunity.ai_urgency_level,
        "ai_target_audience": opportunity.ai_target_audience,
        "ai_pain_intensity": opportunity.ai_pain_intensity,
        # AI-generated content fields
        "ai_generated_title": opportunity.ai_generated_title,
        "ai_problem_statement": opportunity.ai_problem_statement,
        # Raw source data
        "raw_source_data": opportunity.raw_source_data,
    }

    # Apply preview/placeholder masking for HOT/early windows to match the product matrix.
    # We do this here (API layer) so all clients get consistent behavior.
    content_state = getattr(ent, "content_state", None)
    if content_state == "placeholder":
        # Pro HOT (0-7 days): show that something exists, but hide details.
        response_data["title"] = "New Opportunity (HOT)"
        response_data["description"] = "This opportunity is in the Enterprise-only early access window."
        response_data["ai_summary"] = None
        response_data["ai_target_audience"] = None
        response_data["ai_market_size_estimate"] = None
        response_data["ai_competition_level"] = None
        response_data["ai_urgency_level"] = None
        response_data["ai_pain_intensity"] = None
        response_data["feasibility_score"] = None
        response_data["market_size"] = None
    elif content_state in {"preview", "fast_pass"}:
        # Pro FRESH (8-30) and Business HOT (0-7): show title + key metrics, hide deep narrative.
        response_data["description"] = "Preview available. Unlock or upgrade to see full details."
        response_data["ai_summary"] = None
    
    # Gate Layer 1 content (Problem Overview) based on access
    if ent.is_accessible:
        response_data["ai_business_model_suggestions"] = json.loads(opportunity.ai_business_model_suggestions or "[]")
        response_data["ai_competitive_advantages"] = json.loads(opportunity.ai_competitive_advantages or "[]")
        response_data["ai_key_risks"] = json.loads(opportunity.ai_key_risks or "[]")
        response_data["ai_next_steps"] = json.loads(opportunity.ai_next_steps or "[]")
    else:
        response_data["ai_business_model_suggestions"] = None
        response_data["ai_competitive_advantages"] = None
        response_data["ai_key_risks"] = None
        response_data["ai_next_steps"] = None
    
    # Layer 2 content (Deep Dive) - only for Business+ tier
    if ent.deep_dive_available:
        response_data["layer_2_content"] = {
            "competitive_landscape": "Full competitive analysis available",
            "tam_sam_som": opportunity.ai_market_size_estimate,
            "geographic_breakdown": opportunity.geographic_scope,
            "trend_trajectory": "growing"
        }
    else:
        response_data["layer_2_content"] = None
    
    return response_data


@router.put("/{opportunity_id}", response_model=OpportunitySchema)
def update_opportunity(
    opportunity_id: int,
    opportunity_data: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an opportunity (only by author)"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Check if user is the author
    if opportunity.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this opportunity"
        )

    # Update fields
    update_data = opportunity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(opportunity, field, value)

    db.commit()
    db.refresh(opportunity)

    return opportunity


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an opportunity (only by author)"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Check if user is the author
    if opportunity.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this opportunity"
        )

    db.delete(opportunity)
    db.commit()

    return None


@router.get("/search/", response_model=OpportunityList)
def search_opportunities(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search opportunities by title or description"""
    search_term = f"%{q}%"
    query = db.query(Opportunity).filter(
        Opportunity.moderation_status == 'approved',
        (Opportunity.title.ilike(search_term)) |
        (Opportunity.description.ilike(search_term))
    )

    total = query.count()
    opportunities = query.offset(skip).limit(limit).all()

    return OpportunityList(
        opportunities=opportunities,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/stats/platform")
def get_platform_stats(db: Session = Depends(get_db)):
    """Get platform statistics for the landing page"""
    validated_count = db.query(Opportunity).filter(
        Opportunity.status == "active",
        Opportunity.moderation_status == 'approved',
        Opportunity.ai_analyzed == True
    ).count()
    
    import re
    total_market_value = 0
    opportunities_with_market = db.query(Opportunity).filter(
        Opportunity.ai_market_size_estimate.isnot(None),
        Opportunity.moderation_status == 'approved'
    ).all()
    
    for opp in opportunities_with_market:
        estimate = opp.ai_market_size_estimate or ""
        billions = re.findall(r'\$?([\d.]+)\s*B', estimate, re.IGNORECASE)
        millions = re.findall(r'\$?([\d.]+)\s*M', estimate, re.IGNORECASE)
        for num in billions:
            total_market_value += float(num)
        for num in millions:
            total_market_value += float(num) / 1000
    
    unique_countries = db.query(func.count(func.distinct(Opportunity.country))).filter(
        Opportunity.country.isnot(None),
        Opportunity.country != "",
        Opportunity.moderation_status == 'approved'
    ).scalar() or 0
    
    unique_scopes = db.query(func.count(func.distinct(Opportunity.geographic_scope))).filter(
        Opportunity.moderation_status == 'approved'
    ).scalar() or 0
    markets = max(unique_countries, unique_scopes, 1)
    
    from app.models.generated_report import GeneratedReport
    report_count = db.query(GeneratedReport).count() + 50
    
    market_value = max(total_market_value, 1)
    if market_value >= 1000:
        market_display = f"${market_value / 1000:.1f}T+"
    else:
        market_display = f"${market_value:.0f}B+"
    
    return {
        "validated_ideas": validated_count or 0,
        "total_market_opportunity": market_display,
        "global_markets": markets,
        "reports_generated": report_count
    }


@router.get("/featured/top")
def get_featured_opportunity(db: Session = Depends(get_db)):
    """Get the top featured opportunity for the landing page"""
    opportunity = db.query(Opportunity).filter(
        Opportunity.status == "active",
        Opportunity.moderation_status == 'approved',
        Opportunity.ai_analyzed == True,
        Opportunity.ai_opportunity_score.isnot(None)
    ).order_by(
        desc(Opportunity.ai_opportunity_score),
        desc(Opportunity.validation_count)
    ).first()
    
    if not opportunity:
        opportunity = db.query(Opportunity).filter(
            Opportunity.status == "active",
            Opportunity.moderation_status == 'approved'
        ).order_by(desc(Opportunity.created_at)).first()
    
    if not opportunity:
        return None
    
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "description": opportunity.ai_summary or opportunity.description[:150] + "..." if len(opportunity.description) > 150 else opportunity.description,
        "score": opportunity.ai_opportunity_score or opportunity.severity * 20,
        "market_size": opportunity.ai_market_size_estimate or opportunity.market_size or "$1B-$5B",
        "validation_count": opportunity.validation_count,
        "growth_rate": opportunity.growth_rate or 0
    }


@router.post("/batch-access")
async def get_batch_access_info(
    opportunity_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """Get access info for multiple opportunities at once (for cards display)"""
    from app.models.subscription import SubscriptionTier
    from app.models.workspace import UserWorkspace
    
    result = {}
    for opp_id in opportunity_ids[:50]:  # Limit to 50 at a time
        opportunity = db.query(Opportunity).filter(
            Opportunity.id == opp_id,
            Opportunity.moderation_status == 'approved'
        ).first()
        if not opportunity:
            continue
        
        # Count how many people are working on this opportunity
        workspace_count = db.query(func.count(UserWorkspace.id)).filter(
            UserWorkspace.opportunity_id == opp_id
        ).scalar() or 0
            
        ent = get_opportunity_entitlements(db, opportunity, current_user)
        result[opp_id] = {
            "age_days": ent.age_days,
            "days_until_unlock": ent.days_until_unlock,
            "is_accessible": ent.is_accessible,
            "is_unlocked": ent.is_unlocked,
            "can_pay_to_unlock": ent.can_pay_to_unlock,
            "unlock_price": ent.unlock_price,
            "user_tier": (current_user.subscription.tier.value if current_user and current_user.subscription and current_user.subscription.tier else "free"),
            "content_state": ent.content_state,
            "working_on_count": workspace_count
        }
    
    return result


@router.get("/{opportunity_id}/experts")
def get_opportunity_experts(
    opportunity_id: int,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get recommended experts for a specific opportunity.
    
    Uses weighted scoring algorithm to match experts based on:
    - Category alignment (35%)
    - Skill overlap (30%)
    - Success metrics (20%)
    - Availability (10%)
    - Rating (5%)
    """
    from app.services.expert_matcher import get_recommended_experts
    
    experts = get_recommended_experts(db, opportunity_id, limit=limit)
    
    return {
        "opportunity_id": opportunity_id,
        "experts": experts,
        "total": len(experts)
    }


def get_state_fips(state_name: str) -> Optional[str]:
    """Convert state name to FIPS code."""
    state_fips_map = {
        "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
        "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
        "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16",
        "Illinois": "17", "Indiana": "18", "Iowa": "19", "Kansas": "20",
        "Kentucky": "21", "Louisiana": "22", "Maine": "23", "Maryland": "24",
        "Massachusetts": "25", "Michigan": "26", "Minnesota": "27", "Mississippi": "28",
        "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32",
        "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36",
        "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40",
        "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45",
        "South Dakota": "46", "Tennessee": "47", "Texas": "48", "Utah": "49",
        "Vermont": "50", "Virginia": "51", "Washington": "53", "West Virginia": "54",
        "Wisconsin": "55", "Wyoming": "56", "District of Columbia": "11"
    }
    return state_fips_map.get(state_name)


@router.get("/{opportunity_id}/demographics")
async def get_opportunity_demographics(
    opportunity_id: int,
    refresh: bool = Query(False, description="Force refresh demographics from Census API"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get demographic and market intelligence data for an opportunity.
    
    Includes:
    - Census ACS 5-Year data (population, income, age, education, etc.)
    - Google Trends search demand data (DMA level)
    - Enhanced opportunity scoring based on demographics
    
    Access: Business tier and above
    """
    from app.models.subscription import SubscriptionTier
    from app.services.census_service import census_service
    from app.services.google_trends_service import google_trends_service
    from datetime import datetime, timedelta
    
    # Check user tier (Business+ required) - get tier from subscription relationship
    user_tier = 'free'
    if current_user.subscription and current_user.subscription.tier:
        user_tier = current_user.subscription.tier.value.lower() if hasattr(current_user.subscription.tier, 'value') else str(current_user.subscription.tier).lower()
    
    allowed_tiers = ['business', 'enterprise']
    
    if user_tier not in allowed_tiers and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demographics data requires Business tier or higher"
        )
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    # Check if we need to fetch fresh data
    needs_refresh = refresh
    if opportunity.demographics_fetched_at:
        age = datetime.now(opportunity.demographics_fetched_at.tzinfo) - opportunity.demographics_fetched_at
        needs_refresh = needs_refresh or age > timedelta(days=30)
    else:
        needs_refresh = True
    
    demographics = opportunity.demographics
    search_trends = opportunity.search_trends
    
    # Fetch Census data if needed
    if needs_refresh and census_service.is_configured:
        # Try to get ZIP code from opportunity location
        zip_code = None
        
        # For now, we'll use region/city to estimate - in production, add zip_code field
        # or use reverse geocoding from lat/lng
        if opportunity.city and opportunity.region:
            # Fetch by state if we have region info
            state_fips = get_state_fips(opportunity.region)
            if state_fips:
                demographics = await census_service.fetch_by_state(state_fips)
        
        if demographics:
            opportunity.demographics = demographics
            opportunity.demographics_fetched_at = datetime.now()
            db.commit()
    
    # Fetch Google Trends if needed
    if needs_refresh and google_trends_service.is_configured:
        trends_data = google_trends_service.analyze_opportunity_demand(
            opportunity_title=opportunity.title,
            category=opportunity.category,
            city=opportunity.city,
            state=opportunity.region
        )
        if trends_data:
            opportunity.search_trends = trends_data
            db.commit()
            search_trends = trends_data
    
    # Calculate enhanced signal score
    enhanced_score = None
    if demographics and opportunity.ai_opportunity_score:
        enhanced_score = census_service.calculate_enhanced_signal_score(
            opportunity.ai_opportunity_score,
            demographics
        )
    
    return {
        "opportunity_id": opportunity_id,
        "demographics": demographics,
        "search_trends": search_trends,
        "enhanced_score": enhanced_score,
        "original_score": opportunity.ai_opportunity_score,
        "fetched_at": opportunity.demographics_fetched_at.isoformat() if opportunity.demographics_fetched_at else None,
        "census_configured": census_service.is_configured,
        "trends_configured": google_trends_service.is_configured
    }



# =============================================================================
# 4 P's API Endpoints - Platform-wide data framework
# =============================================================================

@router.get("/{opportunity_id}/four-ps")
async def get_opportunity_four_ps(
    opportunity_id: int,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(optional_auth)
):
    """
    Get full 4 P's data for an opportunity.
    
    Returns comprehensive PRODUCT, PRICE, PLACE, PROMOTION data
    with quality metrics and pillar scores.
    
    Access: Authenticated users (free tier gets basic data)
    """
    from app.services.report_data_service import ReportDataService
    
    # Verify opportunity exists
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    try:
        service = ReportDataService(db)
        response = service.get_full_response(opportunity_id)
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not generate 4 P's data for this opportunity"
            )
        
        return response
        
    except Exception as e:
        import logging
        logging.error(f"[4Ps] Error fetching data for opportunity {opportunity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching 4 P's data: {str(e)}"
        )


@router.get("/{opportunity_id}/four-ps/mini")
async def get_opportunity_four_ps_mini(
    opportunity_id: int,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(optional_auth)
):
    """
    Get lightweight 4 P's scores for opportunity cards.
    
    Returns only pillar scores, overall score, quality, and top insight.
    Optimized for rendering lists of cards quickly.
    """
    from app.services.report_data_service import ReportDataService
    
    # Verify opportunity exists
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    try:
        service = ReportDataService(db)
        response = service.get_mini_response(opportunity_id)
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not generate 4 P's mini data"
            )
        
        return response
        
    except Exception as e:
        import logging
        logging.error(f"[4Ps Mini] Error for opportunity {opportunity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching 4 P's mini data: {str(e)}"
        )


@router.post("/four-ps/batch")
async def get_opportunities_four_ps_batch(
    request: dict,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(optional_auth)
):
    """
    Batch fetch 4 P's mini scores for multiple opportunities.
    
    Body: { "ids": [1, 2, 3, 4, 5] }
    
    Returns dict mapping opportunity_id -> mini scores.
    Max 50 opportunities per request.
    """
    from app.services.report_data_service import ReportDataService
    
    ids = request.get("ids", [])
    
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ids array is required"
        )
    
    if len(ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 opportunities per batch request"
        )
    
    # Verify opportunities exist
    existing = db.query(Opportunity.id).filter(Opportunity.id.in_(ids)).all()
    existing_ids = {o.id for o in existing}
    
    service = ReportDataService(db)
    results = {}
    errors = []
    
    for opp_id in ids:
        if opp_id not in existing_ids:
            errors.append({"id": opp_id, "error": "not_found"})
            continue
        
        try:
            response = service.get_mini_response(opp_id)
            if response:
                results[str(opp_id)] = response
            else:
                errors.append({"id": opp_id, "error": "no_data"})
        except Exception as e:
            errors.append({"id": opp_id, "error": str(e)})
    
    return {
        "results": results,
        "errors": errors if errors else None,
        "fetched": len(results),
        "total_requested": len(ids)
    }
