from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class OpportunityBase(BaseModel):
    title: str
    description: str
    category: str
    subcategory: Optional[str] = None
    severity: int
    market_size: Optional[str] = None
    is_anonymous: bool = False

    # Realm Type (Physical/Digital/Both)
    realm_type: str = "both"

    # Geographic Information
    geographic_scope: str = "online"  # local, regional, national, international, online
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    severity: Optional[int] = None
    market_size: Optional[str] = None
    status: Optional[str] = None
    realm_type: Optional[str] = None

    # Geographic Information
    geographic_scope: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None

    # Completion Tracking
    completion_status: Optional[str] = None
    solution_description: Optional[str] = None


class Opportunity(OpportunityBase):
    id: int
    validation_count: int = 0
    growth_rate: float = 0.0
    author_id: Optional[int] = None
    status: str = "active"

    # Completion Tracking
    completion_status: str = "open"
    solution_description: Optional[str] = None
    solved_at: Optional[datetime] = None
    solved_by: Optional[str] = None

    # Feasibility
    feasibility_score: Optional[float] = None
    duplicate_of: Optional[int] = None

    # AI Analysis Fields
    ai_analyzed: bool = False
    ai_analyzed_at: Optional[datetime] = None
    ai_opportunity_score: Optional[int] = None
    ai_summary: Optional[str] = None
    ai_market_size_estimate: Optional[str] = None
    ai_competition_level: Optional[str] = None
    ai_urgency_level: Optional[str] = None
    ai_target_audience: Optional[str] = None
    ai_pain_intensity: Optional[int] = None
    
    # AI-generated content
    ai_generated_title: Optional[str] = None
    ai_problem_statement: Optional[str] = None

    # Source tracking
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    raw_source_data: Optional[str] = None

    # Card enrichment — Group 2 (Spec 1 / macro scanner)
    confidence_tier: Optional[str] = Field(
        None, description="GOLDMINE | VALIDATED | WEAK_SIGNAL (populated by SignalToOpportunity)"
    )
    contributing_sources: Optional[Dict[str, Any]] = Field(
        None, description="Per-source signal counts: {reddit: 3, yelp: 1, total_sources: 2, total_signals: 4}"
    )
    macro_context: Optional[Dict[str, Any]] = Field(
        None, description="Compact macro backdrop: {unemployment_delta_90d, population_5y_delta, median_income, trend_direction}"
    )

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OpportunityList(BaseModel):
    opportunities: list[Opportunity]
    total: int
    page: int
    page_size: int


class FreshnessBadge(BaseModel):
    """Freshness badge based on opportunity age"""
    icon: str
    label: str
    color: str
    tier_required: str
    description: str


class OpportunityAccessInfo(BaseModel):
    """Access information for an opportunity based on user's tier"""
    age_days: int
    freshness_badge: FreshnessBadge
    is_accessible: bool
    is_unlocked: bool
    unlock_method: Optional[str] = None
    days_until_unlock: int
    can_pay_to_unlock: bool
    unlock_price: Optional[int] = None
    user_tier: Optional[str] = None
    # Guidance for frontend rendering; derived from entitlements rules.
    # full | preview | placeholder | locked | pay_per_unlock | fast_pass
    content_state: Optional[str] = None


class OpportunityGatedResponse(Opportunity):
    """Response with gated AI fields based on subscription"""
    is_unlocked: bool = False
    is_authenticated: bool = False
    
    # Time-decay access information
    access_info: Optional[OpportunityAccessInfo] = None
    
    # Gated AI fields - hidden unless unlocked (Layer 1)
    ai_business_model_suggestions: Optional[list] = None
    ai_competitive_advantages: Optional[list] = None
    ai_key_risks: Optional[list] = None
    ai_next_steps: Optional[list] = None
    
    # Layer 2 content (Business+ only, or Pro with paid add-on)
    deep_dive_available: bool = False
    can_buy_deep_dive: bool = False  # Pro tier can buy for $49
    deep_dive_price: Optional[int] = None  # Price in cents (4900 = $49)
    layer_2_content: Optional[dict] = None
    
    # Layer 3 content (Business with limits, Enterprise unlimited)
    execution_package_available: bool = False
