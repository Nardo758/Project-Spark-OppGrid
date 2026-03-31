from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
import logging

from app.db.database import get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.core.dependencies import get_current_user_optional
from app.services.unified_ai_service import (
    get_ai_service, 
    UnifiedAIService,
    RateLimitError,
    QuotaExceededError,
    TierAccessError
)

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    opportunity_id: Optional[int] = None
    conversation_history: Optional[List[ChatMessage]] = []
    category: Optional[str] = None  # Deep Dive category context
    bookmarked_insights: Optional[List[str]] = []  # User's bookmarked messages
    model_id: Optional[str] = None  # Allow user to select model

class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None

def get_opportunity_context(db: Session, opportunity_id: int) -> str:
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        return ""
    
    return f"""
OPPORTUNITY DETAILS:
- Title: {opportunity.title}
- Description: {opportunity.description}
- Category: {opportunity.category}
- Severity: {opportunity.severity}/5
- Market Size: {opportunity.market_size or 'Unknown'}
- Validation Count: {opportunity.validation_count}
- Growth Rate: {opportunity.growth_rate}%
- Geographic Scope: {opportunity.geographic_scope or 'Not specified'}
- Country: {opportunity.country or 'Not specified'}
- Region: {opportunity.region or 'Not specified'}
- City: {opportunity.city or 'Not specified'}
- Completion Status: {opportunity.completion_status or 'unsolved'}
"""

SYSTEM_PROMPT = """You are an AI research assistant for Katalyst, a platform that helps entrepreneurs discover validated business opportunities based on real consumer problems.

Your role is to help users analyze opportunities and provide actionable insights on:
- Market analysis and sizing
- Competitive landscape
- Go-to-market strategy
- Pricing recommendations
- MVP feature prioritization
- Geographic expansion strategy
- Risk assessment
- Business model validation

Always base your responses on the opportunity data provided. Be specific, actionable, and back up recommendations with reasoning. Use bullet points and clear formatting for readability.

When discussing geographic markets, consider:
- US National market: $8.4B, high competition, state-by-state regulations
- Southwest Region: $1.2B, +52% growth, best for launch due to business-friendly regulations
- Canada: $2.1B CAD, low competition but complex provincial regulations
- UK: £1.8B, high competition, requires trade certifications
- Australia: $1.4B AUD, low competition, emerging opportunity

Keep responses concise but thorough. If you don't have enough data, say so and suggest what additional research might help."""

CATEGORY_PROMPTS = {
    "market-validation": """Focus on MARKET VALIDATION analysis:
- Analyze the market demand signals and validation data
- Assess consumer pain point intensity and frequency
- Evaluate market timing and readiness
- Identify key validation metrics and their implications
- Highlight strongest validation signals""",
    
    "geographic": """Focus on GEOGRAPHIC DISTRIBUTION analysis:
- Compare regional market opportunities (US, Canada, UK, Australia)
- Recommend optimal launch location with reasoning
- Assess regional competition levels
- Consider regulatory environments by region
- Suggest geographic expansion strategy""",
    
    "problem-analysis": """Focus on PROBLEM ANALYSIS:
- Deep dive into the core problem and pain points
- Analyze problem severity and urgency
- Identify problem frequency and affected demographics
- Evaluate existing solutions and their gaps
- Quantify the cost of the problem to consumers""",
    
    "opportunity-sizing": """Focus on OPPORTUNITY SIZING:
- Calculate Total Addressable Market (TAM)
- Estimate Serviceable Addressable Market (SAM)
- Project Serviceable Obtainable Market (SOM)
- Analyze market growth trajectories
- Identify market share capture potential""",
    
    "solution-pathways": """Focus on SOLUTION PATHWAYS:
- Suggest potential solution approaches
- Evaluate build vs buy vs partner options
- Recommend MVP feature priorities
- Identify technology requirements
- Assess solution differentiation opportunities""",
    
    "executive": """Focus on EXECUTIVE SUMMARY:
- Provide a concise overview of the opportunity
- Highlight key metrics and validation data
- Summarize risks and mitigation strategies
- Recommend go/no-go decision factors
- Outline next steps for validation""",
    
    "financial": """Focus on FINANCIAL PROJECTIONS:
- Estimate unit economics (CAC, LTV, margins)
- Project revenue potential by year
- Analyze pricing strategy options
- Estimate startup costs and runway needs
- Calculate break-even timeline""",
    
    "execution": """Focus on EXECUTION PLAYBOOK:
- Create a 90-day launch plan
- Identify key milestones and metrics
- Recommend team composition
- Outline go-to-market strategy
- Define success criteria for each phase""",
    
    "data": """Focus on DATA & EVIDENCE:
- Present supporting data and research
- Cite relevant market studies
- Highlight consumer behavior trends
- Provide competitive intelligence
- Summarize validation methodology"""
}

CATEGORY_SUGGESTIONS = {
    "market-validation": [
        "What validation signals are strongest?",
        "How does this compare to similar validated opportunities?",
        "What additional validation would strengthen the case?",
        "Who are the early adopters most likely to pay?"
    ],
    "geographic": [
        "Which city should I launch in first?",
        "What are the regulatory considerations by region?",
        "How do customer acquisition costs vary by geography?",
        "What's the expansion timeline recommendation?"
    ],
    "problem-analysis": [
        "How severe is this problem compared to alternatives?",
        "What workarounds are people currently using?",
        "Who experiences this problem most intensely?",
        "What triggers the need for a solution?"
    ],
    "opportunity-sizing": [
        "What market share is realistic in year one?",
        "How fast is this market growing?",
        "What's the revenue per customer potential?",
        "Are there adjacent markets to expand into?"
    ],
    "solution-pathways": [
        "What's the minimum viable product?",
        "Should I build, buy, or partner?",
        "What technology stack do you recommend?",
        "How can I differentiate from competitors?"
    ],
    "executive": [
        "Give me a 2-minute pitch summary",
        "What are the top 3 risks I should address?",
        "What would make you NOT pursue this?",
        "How does this rank among similar opportunities?"
    ],
    "financial": [
        "What pricing model works best?",
        "How much should I raise to get started?",
        "What are the key unit economics?",
        "When would this become profitable?"
    ],
    "execution": [
        "What should I do in the first 30 days?",
        "What team do I need to hire first?",
        "What partnerships should I pursue?",
        "How do I measure success early on?"
    ],
    "data": [
        "What data supports the market size estimate?",
        "Show me the competitive landscape data",
        "What trends are driving this opportunity?",
        "How reliable is the validation data?"
    ]
}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest, 
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    try:
        # Get AI service with user context
        ai = get_ai_service(db, user=current_user)
        
        opportunity_context = ""
        if request.opportunity_id:
            opportunity_context = get_opportunity_context(db, request.opportunity_id)
        
        # Build category-specific system prompt
        system_prompt = SYSTEM_PROMPT
        if request.category and request.category in CATEGORY_PROMPTS:
            system_prompt += f"\n\n{CATEGORY_PROMPTS[request.category]}"
        
        # Include bookmarked insights for context
        if request.bookmarked_insights and len(request.bookmarked_insights) > 0:
            bookmarks_context = "\n\nUser's bookmarked insights from this session:\n" + "\n".join(f"- {b}" for b in request.bookmarked_insights[:5])
            system_prompt += bookmarks_context
        
        # Build conversation context
        conversation_context = ""
        if request.conversation_history:
            for msg in request.conversation_history[-6:]:  # Last 6 messages for context
                role_label = "User" if msg.role == "user" else "Assistant"
                conversation_context += f"\n{role_label}: {msg.content}"
        
        user_content = request.message
        if opportunity_context and not request.conversation_history:
            user_content = f"{opportunity_context}\n\nUser Question: {request.message}"
        elif conversation_context:
            user_content = f"Conversation so far:{conversation_context}\n\nUser: {request.message}"
        
        # Make the AI call
        result = await ai.complete(
            prompt=user_content,
            system_prompt=system_prompt,
            task_type="user_conversation",
            model_id=request.model_id,
            max_tokens=1024
        )
        
        ai_response = result["content"]
        
        # Get category-specific suggestions or defaults
        suggestions = []
        if len(request.conversation_history or []) <= 2:
            if request.category and request.category in CATEGORY_SUGGESTIONS:
                suggestions = CATEGORY_SUGGESTIONS[request.category]
            else:
                suggestions = [
                    "What are the biggest risks with this business model?",
                    "Where should I launch this geographically?",
                    "How would you recommend pricing the product?",
                    "What should the MVP feature set look like?"
                ]
        
        return ChatResponse(
            response=ai_response,
            suggestions=suggestions,
            model_used=result.get("model_id"),
            tokens_used=result["tokens"]["input"] + result["tokens"]["output"]
        )
        
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except QuotaExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except TierAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat error: {str(e)}"
        )

@router.get("/suggestions/{opportunity_id}")
async def get_initial_suggestions(opportunity_id: int, db: Session = Depends(get_db)):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return {
        "greeting": f"Hi! I'm your AI research assistant. I can help you explore the '{opportunity.title}' opportunity in depth.",
        "suggestions": [
            "What are the biggest risks with this business model?",
            "Where should I launch this geographically?",
            "How would you recommend pricing the product?",
            "What should the MVP feature set look like?",
            "Who are the main competitors?",
            "What's the ideal customer profile?"
        ]
    }

@router.get("/models")
async def get_available_models(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """Get models available to the current user based on their tier."""
    from app.services.ai_model_registry import AIModelRegistry
    
    registry = AIModelRegistry(db)
    all_models = registry.get_all_models()
    
    # Determine user tier
    user_tier = "free"
    if current_user:
        if hasattr(current_user, "subscription") and current_user.subscription:
            user_tier = current_user.subscription.tier or "free"
    
    # Filter by tier access
    tier_order = ["free", "starter", "growth", "pro", "enterprise"]
    try:
        user_level = tier_order.index(user_tier.lower())
    except ValueError:
        user_level = 0
    
    available_models = []
    for model in all_models:
        min_tier = (model.get("min_tier") or "free").lower()
        try:
            required_level = tier_order.index(min_tier)
        except ValueError:
            required_level = 0
        
        if user_level >= required_level:
            available_models.append({
                "model_id": model["model_id"],
                "display_name": model["display_name"],
                "provider": model["provider"],
                "description": model.get("description"),
                "is_default": model.get("is_default", False)
            })
    
    return {
        "models": available_models,
        "user_tier": user_tier,
        "default_model": next((m["model_id"] for m in available_models if m["is_default"]), None)
    }
