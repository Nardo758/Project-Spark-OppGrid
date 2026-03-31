"""
Global AI Copilot API Router
Provides persistent cross-page AI assistant with context awareness.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
import os

from app.db.database import get_db
from app.models.user import User
from app.models.copilot import GlobalChatMessage, CopilotSuggestion
from app.models.opportunity import Opportunity
from app.models.watchlist import WatchlistItem, LifecycleState
from app.core.dependencies import get_current_user
from app.services.llm_ai_engine import get_anthropic_client

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])

COPILOT_SYSTEM_PROMPT = """You are OppGrid's AI Copilot - a persistent assistant that helps users discover, validate, and launch business opportunities.

You are context-aware and can see which page the user is on. Adapt your responses accordingly:

PAGE CONTEXTS:
- "feed" or "discover": Help discover opportunities, explain scoring, suggest filters
- "saved" or "watchlist": Help organize saved opportunities, suggest actions, explain lifecycle states
- "opportunity_detail": Provide deep analysis of the specific opportunity
- "hub" or "workspace": Guide through research, validation, planning, execution stages
- "consultant": Help with validation tools and research
- "profile": Help with account settings
- "experts" or "network": Help connect with experts

LIFECYCLE STATE GUIDANCE:
- DISCOVERED → SAVED: Encourage saving promising opportunities
- SAVED → ANALYZING: Guide toward research and validation
- ANALYZING → PLANNING: Help structure the business plan
- PLANNING → EXECUTING: Recommend tools and next steps
- EXECUTING → LAUNCHED: Support the launch process
- PAUSED: Help resume when ready
- ARCHIVED: Suggest reviewing lessons learned

4 P's MARKET INTELLIGENCE:
When 4 P's data is available, use it to give specific, actionable advice:

- PRODUCT (Demand): Pain intensity, trend direction, urgency level
  → High pain + rising trend = strong opportunity signal
  → Low scores = needs more validation research

- PRICE (Economics): Market size, median income, spending power
  → Large market + high income = premium positioning possible
  → Low scores = research pricing strategies

- PLACE (Location): Growth score, population growth, job market
  → High growth markets = easier customer acquisition
  → Low scores = consider market expansion strategy

- PROMOTION (Competition): Competition level, competitor count, advantages
  → Low competition = first-mover advantage
  → High competition = focus on differentiation

When a pillar is weak (< 50 score), proactively suggest:
- Research tasks to strengthen that area
- Reports to generate for deeper analysis
- Questions to validate with potential customers

Be concise, actionable, and encouraging. Use bullet points for clarity.
Reference specific 4 P's metrics when available to make advice concrete."""


class ChatRequest(BaseModel):
    message: str
    page_context: Optional[str] = None
    opportunity_id: Optional[int] = None

    @property
    def sanitized_message(self) -> str:
        return self.message.strip()[:4000] if self.message else ""


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    page_context: Optional[str]
    opportunity_id: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    response: str
    chat_history: List[ChatMessageResponse]


class SuggestionResponse(BaseModel):
    id: int
    suggestion_type: str
    content: str
    page_context: Optional[str]
    opportunity_id: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


def get_opportunity_context(db: Session, opportunity_id: int) -> dict:
    """Get opportunity details for AI context."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        return {}
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "description": opportunity.description,
        "category": opportunity.category,
        "score": opportunity.score,
        "ai_problem_statement": opportunity.ai_problem_statement,
        "ai_market_size_estimate": opportunity.ai_market_size_estimate,
    }


def get_four_ps_context(db: Session, opportunity_id: int) -> dict:
    """Get 4 P's market intelligence for AI context."""
    try:
        from app.services.report_data_service import ReportDataService
        service = ReportDataService(db)
        response = service.get_full_response(opportunity_id)
        
        if not response:
            return {}
        
        # Extract key insights for the copilot
        scores = response.get("scores", {})
        quality = response.get("data_quality", {})
        product = response.get("product", {})
        price = response.get("price", {})
        place = response.get("place", {})
        promotion = response.get("promotion", {})
        
        return {
            "scores": scores,
            "overall_score": response.get("overall", 0),
            "weakest_pillar": quality.get("weakest_pillar"),
            "data_quality": round(quality.get("completeness", 0) * 100),
            "recommendations": quality.get("recommended_actions", [])[:3],
            "key_insights": {
                "product": {
                    "pain_intensity": product.get("pain_intensity"),
                    "trend_direction": product.get("google_trends_direction"),
                    "urgency": product.get("urgency_level"),
                },
                "price": {
                    "market_size": price.get("market_size_estimate"),
                    "median_income": price.get("median_income"),
                },
                "place": {
                    "growth_score": place.get("growth_score"),
                    "growth_category": place.get("growth_category"),
                    "population": place.get("population"),
                },
                "promotion": {
                    "competition_level": promotion.get("competition_level"),
                    "competitor_count": promotion.get("competitor_count"),
                }
            }
        }
    except Exception as e:
        import logging
        logging.error(f"[Copilot] Error fetching 4 P's context: {e}")
        return {}


def get_user_lifecycle_context(db: Session, user_id: int, opportunity_id: Optional[int] = None) -> dict:
    """Get user's lifecycle state for an opportunity."""
    if not opportunity_id:
        return {}
    watchlist_item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id,
        WatchlistItem.opportunity_id == opportunity_id
    ).first()
    if not watchlist_item:
        return {"saved": False}
    return {
        "saved": True,
        "lifecycle_state": watchlist_item.lifecycle_state.value if watchlist_item.lifecycle_state else "saved",
        "state_changed_at": watchlist_item.state_changed_at.isoformat() if watchlist_item.state_changed_at else None
    }


@router.post("/chat", response_model=ChatResponse)
async def chat_with_copilot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chat with the persistent AI Copilot."""
    message = request.sanitized_message
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    recent_messages = db.query(GlobalChatMessage).filter(
        GlobalChatMessage.user_id == current_user.id
    ).order_by(desc(GlobalChatMessage.created_at)).limit(20).all()
    
    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_messages)
    ]

    context_parts = [f"Current page: {request.page_context or 'unknown'}"]
    
    if request.opportunity_id:
        opp_context = get_opportunity_context(db, request.opportunity_id)
        if opp_context:
            context_parts.append(f"\nOpportunity in context:\n- Title: {opp_context.get('title')}\n- Category: {opp_context.get('category')}\n- Score: {opp_context.get('score')}\n- Problem: {opp_context.get('ai_problem_statement', 'Not analyzed')[:200]}")
        
        # Add 4 P's market intelligence context
        four_ps = get_four_ps_context(db, request.opportunity_id)
        if four_ps and four_ps.get("scores"):
            scores = four_ps["scores"]
            insights = four_ps.get("key_insights", {})
            
            # Format values safely
            product_i = insights.get("product", {})
            price_i = insights.get("price", {})
            place_i = insights.get("place", {})
            promo_i = insights.get("promotion", {})
            
            income = price_i.get("median_income")
            income_str = f"${income:,}" if income else "N/A"
            pop = place_i.get("population")
            pop_str = f"{pop:,}" if pop else "N/A"
            weakest = four_ps.get("weakest_pillar")
            weakest_str = weakest.upper() if weakest else "N/A"
            
            four_ps_context = f"""
4 P's Market Intelligence:
- PRODUCT Score: {scores.get('product', 'N/A')}/100 (Pain: {product_i.get('pain_intensity', 'N/A')}/10, Trend: {product_i.get('trend_direction', 'unknown')})
- PRICE Score: {scores.get('price', 'N/A')}/100 (Market Size: {price_i.get('market_size', 'N/A')}, Income: {income_str})
- PLACE Score: {scores.get('place', 'N/A')}/100 (Growth: {place_i.get('growth_category', 'N/A')}, Pop: {pop_str})
- PROMOTION Score: {scores.get('promotion', 'N/A')}/100 (Competition: {promo_i.get('competition_level', 'N/A')})
- Overall: {four_ps.get('overall_score', 'N/A')}/100 | Data Quality: {four_ps.get('data_quality', 'N/A')}%
- Weakest Pillar: {weakest_str}"""
            
            if four_ps.get("recommendations"):
                four_ps_context += f"\n- Recommendations: {'; '.join(four_ps['recommendations'][:2])}"
            
            context_parts.append(four_ps_context)
        
        lifecycle = get_user_lifecycle_context(db, current_user.id, request.opportunity_id)
        if lifecycle.get("saved"):
            context_parts.append(f"\nUser's lifecycle state: {lifecycle.get('lifecycle_state', 'saved')}")

    context_message = "\n".join(context_parts)
    
    system_prompt = f"{COPILOT_SYSTEM_PROMPT}\n\n--- CURRENT CONTEXT ---\n{context_message}"

    messages = chat_history + [{"role": "user", "content": message}]

    try:
        client = get_anthropic_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        ai_response = response.content[0].text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    user_msg = GlobalChatMessage(
        user_id=current_user.id,
        role="user",
        content=message,
        page_context=request.page_context,
        opportunity_id=request.opportunity_id
    )
    db.add(user_msg)

    assistant_msg = GlobalChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
        page_context=request.page_context,
        opportunity_id=request.opportunity_id
    )
    db.add(assistant_msg)
    
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    all_messages = db.query(GlobalChatMessage).filter(
        GlobalChatMessage.user_id == current_user.id
    ).order_by(GlobalChatMessage.created_at).limit(50).all()

    return ChatResponse(
        response=ai_response,
        chat_history=[
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                page_context=msg.page_context,
                opportunity_id=msg.opportunity_id,
                created_at=msg.created_at.isoformat()
            )
            for msg in all_messages
        ]
    )


@router.get("/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get copilot chat history."""
    messages = db.query(GlobalChatMessage).filter(
        GlobalChatMessage.user_id == current_user.id
    ).order_by(GlobalChatMessage.created_at).limit(limit).all()

    return [
        ChatMessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            page_context=msg.page_context,
            opportunity_id=msg.opportunity_id,
            created_at=msg.created_at.isoformat()
        )
        for msg in messages
    ]


@router.delete("/history")
async def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear copilot chat history."""
    db.query(GlobalChatMessage).filter(
        GlobalChatMessage.user_id == current_user.id
    ).delete()
    db.commit()
    return {"message": "Chat history cleared"}


@router.get("/suggestions", response_model=List[SuggestionResponse])
async def get_suggestions(
    page_context: Optional[str] = None,
    opportunity_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get proactive AI suggestions for the current context."""
    query = db.query(CopilotSuggestion).filter(
        CopilotSuggestion.user_id == current_user.id,
        CopilotSuggestion.is_dismissed == False
    )
    
    if page_context:
        query = query.filter(CopilotSuggestion.page_context == page_context)
    if opportunity_id:
        query = query.filter(CopilotSuggestion.opportunity_id == opportunity_id)
    
    suggestions = query.order_by(desc(CopilotSuggestion.created_at)).limit(5).all()

    return [
        SuggestionResponse(
            id=s.id,
            suggestion_type=s.suggestion_type,
            content=s.content,
            page_context=s.page_context,
            opportunity_id=s.opportunity_id,
            created_at=s.created_at.isoformat()
        )
        for s in suggestions
    ]


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dismiss a suggestion."""
    suggestion = db.query(CopilotSuggestion).filter(
        CopilotSuggestion.id == suggestion_id,
        CopilotSuggestion.user_id == current_user.id
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion.is_dismissed = True
    db.commit()
    
    return {"message": "Suggestion dismissed"}


@router.post("/suggest-tags")
async def suggest_tags_for_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI-suggested tags for an opportunity."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    prompt = f"""Suggest 3-5 short tags (1-2 words each) for this business opportunity:

Title: {opportunity.title}
Category: {opportunity.category}
Description: {opportunity.description[:500] if opportunity.description else 'N/A'}

Return only the tags as a comma-separated list, no explanations. Examples: "high-growth, local-service, recurring-revenue, low-barrier"
"""

    try:
        client = get_anthropic_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        tags_text = response.content[0].text.strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        return {"tags": tags[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
