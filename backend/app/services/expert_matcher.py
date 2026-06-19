"""
Expert Matcher Service

Matches ExpertProfiles to opportunities using a weighted scoring algorithm
with optional AI-powered insights for personalized match reasons.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.expert_collaboration import ExpertProfile, ExpertCategory
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

CATEGORY_WEIGHT = 0.30
SPECIALIZATION_WEIGHT = 0.25
INDUSTRY_WEIGHT = 0.20
SUCCESS_WEIGHT = 0.15
AVAILABILITY_WEIGHT = 0.05
RATING_WEIGHT = 0.05

CATEGORY_INDUSTRY_MAP = {
    "Technology & Software": ["technology", "software", "saas", "fintech", "ai"],
    "Healthcare": ["healthcare", "biotech", "digital_health", "medical"],
    "Food & Dining": ["restaurant", "food", "hospitality", "consumer"],
    "Real Estate": ["real_estate", "property", "construction", "housing"],
    "Transportation": ["logistics", "transportation", "mobility", "supply_chain"],
    "Education": ["education", "edtech", "training", "learning"],
    "Finance & Banking": ["fintech", "banking", "payments", "financial_services"],
    "Retail & E-commerce": ["e-commerce", "retail", "marketplace", "consumer"],
    "Money & Finance": ["fintech", "payments", "banking", "investment"],
    "Home Services": ["home_services", "consumer", "local_services"],
    "Childcare": ["education", "family", "consumer"],
    "Entertainment": ["media", "entertainment", "consumer", "content"],
}

CATEGORY_EXPERT_TYPE_MAP = {
    "Technology & Software": [ExpertCategory.TECHNICAL_ADVISOR, ExpertCategory.BUSINESS_CONSULTANT],
    "Healthcare": [ExpertCategory.INDUSTRY_SPECIALIST, ExpertCategory.LEGAL_COMPLIANCE],
    "Food & Dining": [ExpertCategory.BUSINESS_CONSULTANT, ExpertCategory.GROWTH_MARKETING],
    "Real Estate": [ExpertCategory.FINANCIAL_ADVISOR, ExpertCategory.INDUSTRY_SPECIALIST],
    "Transportation": [ExpertCategory.BUSINESS_CONSULTANT, ExpertCategory.TECHNICAL_ADVISOR],
    "Education": [ExpertCategory.INDUSTRY_SPECIALIST, ExpertCategory.GROWTH_MARKETING],
    "Finance & Banking": [ExpertCategory.FINANCIAL_ADVISOR, ExpertCategory.LEGAL_COMPLIANCE],
    "Retail & E-commerce": [ExpertCategory.GROWTH_MARKETING, ExpertCategory.BUSINESS_CONSULTANT],
    "Money & Finance": [ExpertCategory.FINANCIAL_ADVISOR, ExpertCategory.BUSINESS_CONSULTANT],
    "Home Services": [ExpertCategory.BUSINESS_CONSULTANT, ExpertCategory.GROWTH_MARKETING],
    "Childcare": [ExpertCategory.BUSINESS_CONSULTANT, ExpertCategory.INDUSTRY_SPECIALIST],
    "Entertainment": [ExpertCategory.GROWTH_MARKETING, ExpertCategory.BUSINESS_CONSULTANT],
}


def parse_json_field(field_value: Optional[str]) -> List[str]:
    """Safely parse a JSON text field to a list."""
    if not field_value:
        return []
    try:
        result = json.loads(field_value)
        if isinstance(result, list):
            return [str(item).lower() for item in result]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def calculate_category_score(expert: ExpertProfile, opportunity: Opportunity) -> float:
    """Calculate category alignment score (0-1)."""
    opp_category = (opportunity.category or "").strip()
    
    if not expert.primary_category:
        return 0.3
    
    recommended_types = CATEGORY_EXPERT_TYPE_MAP.get(opp_category, [])
    
    if expert.primary_category in recommended_types:
        if expert.primary_category == recommended_types[0]:
            return 1.0
        return 0.85
    
    if expert.primary_category in [ExpertCategory.BUSINESS_CONSULTANT, ExpertCategory.FINANCIAL_ADVISOR]:
        return 0.5
    
    return 0.3


def calculate_specialization_score(expert: ExpertProfile, opportunity: Opportunity) -> float:
    """Calculate specialization overlap score (0-1)."""
    expert_specs = parse_json_field(expert.specializations)
    
    if not expert_specs:
        return 0.3
    
    opp_title = (opportunity.title or "").lower()
    opp_desc = (opportunity.description or "").lower()[:500]
    opp_text = f"{opp_title} {opp_desc}"
    
    matches = 0
    for spec in expert_specs:
        spec_lower = spec.lower()
        if spec_lower in opp_text or any(word in spec_lower for word in opp_text.split()[:20]):
            matches += 1
    
    if matches == 0:
        return 0.2
    
    return min(1.0, 0.4 + (matches * 0.2))


def calculate_industry_score(expert: ExpertProfile, opportunity: Opportunity) -> float:
    """Calculate industry match score (0-1)."""
    expert_industries = parse_json_field(expert.industries)
    opp_category = (opportunity.category or "").strip()
    
    if not expert_industries:
        return 0.3
    
    relevant_industries = CATEGORY_INDUSTRY_MAP.get(opp_category, [])
    
    for industry in expert_industries:
        industry_lower = industry.lower().replace(" ", "_")
        if industry_lower in relevant_industries:
            return 1.0
        for rel in relevant_industries:
            if rel in industry_lower or industry_lower in rel:
                return 0.8
    
    return 0.2


def calculate_success_score(expert: ExpertProfile) -> float:
    """Calculate success metrics score (0-1)."""
    completed = expert.projects_completed or 0
    
    project_score = min(1.0, completed / 30)
    
    return project_score


def calculate_availability_score(expert: ExpertProfile) -> float:
    """Calculate availability score (0-1)."""
    if not expert.is_accepting_clients:
        return 0.2
    
    hours = expert.availability_hours_per_week or 0
    if hours >= 20:
        return 1.0
    if hours >= 10:
        return 0.8
    if hours >= 5:
        return 0.6
    
    return 0.4


def calculate_rating_score(expert: ExpertProfile) -> float:
    """Calculate rating score (0-1)."""
    rating = expert.avg_rating or 0
    reviews = expert.total_reviews or 0
    
    if reviews < 3:
        return 0.5
    
    return min(1.0, rating / 5.0)


def calculate_match_score(expert: ExpertProfile, opportunity: Opportunity) -> float:
    """
    Calculate weighted match score for an expert-opportunity pair.
    
    Weights:
    - Category alignment: 30%
    - Specialization overlap: 25%
    - Industry match: 20%
    - Success metrics: 15%
    - Availability: 5%
    - Rating: 5%
    """
    category_score = calculate_category_score(expert, opportunity)
    specialization_score = calculate_specialization_score(expert, opportunity)
    industry_score = calculate_industry_score(expert, opportunity)
    success_score = calculate_success_score(expert)
    availability_score = calculate_availability_score(expert)
    rating_score = calculate_rating_score(expert)
    
    total_score = (
        (category_score * CATEGORY_WEIGHT) +
        (specialization_score * SPECIALIZATION_WEIGHT) +
        (industry_score * INDUSTRY_WEIGHT) +
        (success_score * SUCCESS_WEIGHT) +
        (availability_score * AVAILABILITY_WEIGHT) +
        (rating_score * RATING_WEIGHT)
    )
    
    return round(total_score * 100, 1)


def get_match_reason(expert: ExpertProfile, opportunity: Opportunity, score: float) -> str:
    """Generate a human-readable reason for the match."""
    reasons = []
    
    if expert.primary_category:
        category_name = expert.primary_category.value.replace("_", " ").title()
        opp_category = opportunity.category or "this opportunity"
        
        recommended_types = CATEGORY_EXPERT_TYPE_MAP.get(opportunity.category, [])
        if expert.primary_category in recommended_types:
            reasons.append(f"{category_name} expertise ideal for {opp_category}")
    
    expert_industries = parse_json_field(expert.industries)
    if expert_industries:
        relevant_industries = CATEGORY_INDUSTRY_MAP.get(opportunity.category, [])
        for industry in expert_industries:
            industry_lower = industry.lower().replace(" ", "_")
            if any(rel in industry_lower or industry_lower in rel for rel in relevant_industries):
                reasons.append(f"Industry experience in {industry}")
                break
    
    if expert.projects_completed and expert.projects_completed > 20:
        reasons.append(f"{expert.projects_completed} completed projects")
    
    if expert.avg_rating and expert.avg_rating >= 4.5:
        reasons.append(f"{expert.avg_rating:.1f}★ rating")
    
    if not reasons:
        if score >= 70:
            reasons.append("Strong expertise match")
        elif score >= 50:
            reasons.append("Good fit for this opportunity")
        else:
            reasons.append("Available expert")
    
    return " • ".join(reasons[:2])


def serialize_expert_for_match(expert: ExpertProfile, opportunity: Opportunity) -> dict:
    """Serialize expert profile for match response."""
    score = calculate_match_score(expert, opportunity)
    user = expert.user if expert.user else None
    
    return {
        "id": expert.id,
        "user_id": expert.user_id,
        "name": user.name if user else None,
        "avatar_url": user.avatar_url if user else None,
        "title": expert.title,
        "location": expert.location,
        "primary_category": expert.primary_category.value.lower() if expert.primary_category else None,
        "specializations": parse_json_field(expert.specializations),
        "industries": parse_json_field(expert.industries),
        "years_experience": expert.years_experience,
        "portfolio_highlights": expert.portfolio_highlights,
        "hourly_rate_cents": expert.hourly_rate_cents,
        "project_rate_min_cents": expert.project_rate_min_cents,
        "project_rate_max_cents": expert.project_rate_max_cents,
        "retainer_rate_cents": expert.retainer_rate_cents,
        "response_time": expert.response_time,
        "is_verified": expert.is_verified,
        "is_accepting_clients": expert.is_accepting_clients,
        "avg_rating": expert.avg_rating,
        "total_reviews": expert.total_reviews,
        "projects_completed": expert.projects_completed,
        "match_score": score,
        "match_reason": get_match_reason(expert, opportunity, score),
    }


def get_recommended_experts(
    db: Session,
    opportunity_id: int,
    limit: int = 5,
    min_score: float = 30.0
) -> List[dict]:
    """
    Get recommended expert profiles for an opportunity.
    
    Returns a list of expert dicts with match scores, sorted by relevance.
    """
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        logger.warning(f"Opportunity {opportunity_id} not found")
        return []
    
    experts = db.query(ExpertProfile).filter(
        ExpertProfile.is_verified == True,
        ExpertProfile.is_accepting_clients == True,
        or_(
            ExpertProfile.external_source != "sample",
            ExpertProfile.external_source.is_(None)
        )
    ).all()
    
    if not experts:
        logger.info("No verified expert profiles found")
        return []
    
    scored_experts = []
    for expert in experts:
        result = serialize_expert_for_match(expert, opportunity)
        if result["match_score"] >= min_score:
            scored_experts.append(result)
    
    scored_experts.sort(key=lambda x: x["match_score"], reverse=True)
    
    return scored_experts[:limit]


async def get_ai_enhanced_matches(
    db: Session,
    opportunity_id: int,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Get AI-enhanced expert matches with personalized recommendations.
    
    Uses the AI orchestrator to provide deeper insights about why
    each expert is a good match for the specific opportunity.
    """
    from .ai_orchestrator import ai_orchestrator, AITaskType
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        return {"experts": [], "ai_insights": None}
    
    base_matches = get_recommended_experts(db, opportunity_id, limit=limit * 2, min_score=25.0)
    
    if not base_matches:
        return {"experts": [], "ai_insights": "No matching experts found for this opportunity."}
    
    try:
        ai_data = {
            "opportunity": {
                "title": opportunity.title,
                "category": opportunity.category,
                "description": opportunity.description[:500] if opportunity.description else "",
                "market_size": opportunity.market_size,
            },
            "expert_candidates": [
                {
                    "name": e["name"],
                    "title": e["title"],
                    "category": e["primary_category"],
                    "specializations": e["specializations"][:3],
                    "industries": e["industries"][:3],
                    "match_score": e["match_score"],
                }
                for e in base_matches[:5]
            ]
        }
        
        ai_result = await ai_orchestrator.process_request(AITaskType.EXPERT_MATCHING, ai_data)
        
        ai_insights = ai_result.get("claude_phase", {}).get("result", {}).get("response", None)
        
    except Exception as e:
        logger.warning(f"AI enhancement failed, using base matches: {e}")
        ai_insights = None
    
    return {
        "experts": base_matches[:limit],
        "ai_insights": ai_insights,
        "opportunity_category": opportunity.category,
        "total_matches": len(base_matches),
    }
