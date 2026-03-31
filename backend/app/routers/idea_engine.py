"""
Idea Generation and Validation Engine API

This router handles:
- Free idea generation/refinement using AI
- Paid idea validation with deep analysis
- Payment processing for validation service
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import logging

from anthropic import Anthropic

router = APIRouter()
logger = logging.getLogger(__name__)

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")

client = Anthropic(
    api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
    base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
)


class IdeaInput(BaseModel):
    idea: str
    category: Optional[str] = None


class GeneratedIdea(BaseModel):
    refined_idea: str
    title: str
    problem_statement: str
    target_audience: str
    unique_value_proposition: str
    category: str
    preview_score: int
    preview_insights: List[str]


class ValidationRequest(BaseModel):
    idea: str
    title: str
    category: str
    payment_intent_id: str


class ValidationResult(BaseModel):
    title: str
    category: str
    opportunity_score: int
    summary: str
    market_size_estimate: str
    competition_level: str
    urgency_level: str
    target_audience: str
    pain_intensity: int
    business_model_suggestions: List[str]
    competitive_advantages: List[str]
    key_risks: List[str]
    next_steps: List[str]
    market_trends: List[str]
    revenue_potential: str
    time_to_market: str
    validation_confidence: int


IDEA_GENERATION_PROMPT = """You are an expert business idea consultant for OppGrid, a platform that helps entrepreneurs discover and validate business opportunities.

A user has shared their business idea or problem. Your job is to:
1. Refine and clarify their idea into a compelling business opportunity
2. Identify the core problem being solved
3. Define the target audience
4. Create a unique value proposition
5. Suggest the best category for this opportunity
6. Provide a preview score (0-100) indicating potential viability
7. Give 3 preview insights to entice them to get full validation

Respond in valid JSON format only:
{
    "refined_idea": "<expanded, clear description of the business idea, 2-3 sentences>",
    "title": "<catchy 5-8 word title for this opportunity>",
    "problem_statement": "<clear articulation of the problem being solved>",
    "target_audience": "<specific description of who would benefit>",
    "unique_value_proposition": "<what makes this solution unique>",
    "category": "<one of: Technology, Health & Wellness, Finance, Education, Sustainability, Lifestyle, B2B Services, Consumer Products>",
    "preview_score": <int 0-100>,
    "preview_insights": [
        "<teaser insight 1 - partial info that hints at deeper analysis>",
        "<teaser insight 2>",
        "<teaser insight 3>"
    ]
}

Be encouraging but realistic. The preview should make them want to get the full validation."""


VALIDATION_PROMPT = """You are a senior market research analyst for OppGrid, providing comprehensive business opportunity validation.

Analyze this business idea thoroughly and provide actionable, data-driven insights. This is a PAID validation, so be extremely detailed and valuable.

Respond in valid JSON format only:
{
    "opportunity_score": <int 0-100>,
    "summary": "<compelling one-line summary of the opportunity, max 150 chars>",
    "market_size_estimate": "<specific range like $500M-$2B with justification>",
    "competition_level": "<low|medium|high with brief explanation>",
    "urgency_level": "<low|medium|high|critical - how time-sensitive is this opportunity>",
    "target_audience": "<detailed primary and secondary audience description>",
    "pain_intensity": <int 1-10>,
    "business_model_suggestions": [
        "<detailed business model 1 with revenue mechanics>",
        "<business model 2>",
        "<business model 3>"
    ],
    "competitive_advantages": [
        "<specific advantage 1>",
        "<specific advantage 2>",
        "<specific advantage 3>"
    ],
    "key_risks": [
        "<risk 1 with mitigation strategy>",
        "<risk 2 with mitigation strategy>",
        "<risk 3 with mitigation strategy>"
    ],
    "next_steps": [
        "<actionable step 1 with timeline>",
        "<actionable step 2 with timeline>",
        "<actionable step 3 with timeline>",
        "<actionable step 4 with timeline>",
        "<actionable step 5 with timeline>"
    ],
    "market_trends": [
        "<relevant trend 1 supporting this opportunity>",
        "<relevant trend 2>",
        "<relevant trend 3>"
    ],
    "revenue_potential": "<estimated first-year and 5-year revenue range>",
    "time_to_market": "<estimated time to launch MVP and full product>",
    "validation_confidence": <int 0-100, how confident are we in this analysis>
}

Scoring guidelines:
- 80-100: Exceptional opportunity - clear pain, large market, low competition
- 60-79: Strong opportunity - validated pain, good market potential  
- 40-59: Moderate opportunity - needs refinement, competitive market
- 20-39: Weak opportunity - unclear pain or saturated market
- 0-19: Poor opportunity - not recommended to pursue"""


@router.post("/generate", response_model=GeneratedIdea)
async def generate_idea(input_data: IdeaInput):
    """
    FREE: Generate and refine a business idea using AI.
    Returns a structured opportunity with preview insights.
    """
    if not input_data.idea or len(input_data.idea.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a more detailed idea (at least 10 characters)"
        )
    
    try:
        user_prompt = f"""User's business idea or problem:
{input_data.idea}

{f"Preferred category: {input_data.category}" if input_data.category else ""}

Analyze and refine this into a structured business opportunity."""

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=IDEA_GENERATION_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response_text = response.content[0].text
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx <= start_idx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse AI response"
            )
        
        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)
        
        return GeneratedIdea(
            refined_idea=result.get("refined_idea", ""),
            title=result.get("title", ""),
            problem_statement=result.get("problem_statement", ""),
            target_audience=result.get("target_audience", ""),
            unique_value_proposition=result.get("unique_value_proposition", ""),
            category=result.get("category", "Technology"),
            preview_score=result.get("preview_score", 50),
            preview_insights=result.get("preview_insights", [])
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process AI response"
        )
    except Exception as e:
        logger.error(f"Idea generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/validate", response_model=ValidationResult, include_in_schema=False)
async def validate_idea(request: ValidationRequest):
    """
    PAID: Comprehensive idea validation with deep market analysis.
    Requires payment verification (payment_intent_id).
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Deprecated. Use the persisted Idea Validation API: POST /api/v1/idea-validations/{id}/run",
    )
    if not request.idea or len(request.idea.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a detailed idea for validation"
        )
    
    if not request.payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required for validation service"
        )
    
    try:
        from app.services.stripe_service import get_stripe_client
        stripe = get_stripe_client()
        
        payment_intent = stripe.PaymentIntent.retrieve(request.payment_intent_id)
        
        if payment_intent.status != "succeeded":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment not completed. Status: {payment_intent.status}"
            )
        
        if payment_intent.metadata.get("service") != "idea_validation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment intent for this service"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to verify payment"
        )
    
    try:
        user_prompt = f"""Validate this business opportunity:

TITLE: {request.title}
CATEGORY: {request.category}

IDEA DESCRIPTION:
{request.idea}

Provide a comprehensive, actionable validation analysis."""

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=VALIDATION_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response_text = response.content[0].text
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx <= start_idx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse validation response"
            )
        
        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)
        
        return ValidationResult(
            title=request.title,
            category=request.category,
            opportunity_score=result.get("opportunity_score", 50),
            summary=result.get("summary", ""),
            market_size_estimate=result.get("market_size_estimate", "Unknown"),
            competition_level=result.get("competition_level", "medium"),
            urgency_level=result.get("urgency_level", "medium"),
            target_audience=result.get("target_audience", ""),
            pain_intensity=result.get("pain_intensity", 5),
            business_model_suggestions=result.get("business_model_suggestions", []),
            competitive_advantages=result.get("competitive_advantages", []),
            key_risks=result.get("key_risks", []),
            next_steps=result.get("next_steps", []),
            market_trends=result.get("market_trends", []),
            revenue_potential=result.get("revenue_potential", "Unknown"),
            time_to_market=result.get("time_to_market", "Unknown"),
            validation_confidence=result.get("validation_confidence", 70)
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Validation JSON decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process validation response"
        )
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class PaymentIntentRequest(BaseModel):
    amount: int = 999


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


@router.post("/create-payment-intent", response_model=PaymentIntentResponse, include_in_schema=False)
async def create_payment_intent(request: PaymentIntentRequest):
    """
    Create a Stripe payment intent for validation service.
    Amount is in cents (default: $9.99 = 999 cents)
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Deprecated. Use the persisted Idea Validation API: POST /api/v1/idea-validations/create-payment-intent",
    )
    try:
        from app.services.stripe_service import get_stripe_client
        
        stripe = get_stripe_client()
        
        intent = stripe.PaymentIntent.create(
            amount=request.amount,
            currency="usd",
            metadata={
                "service": "idea_validation",
                "product": "OppGrid Idea Validation"
            }
        )
        
        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id
        )
        
    except ValueError as e:
        logger.error(f"Stripe not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured. Please contact support."
        )
    except Exception as e:
        logger.error(f"Payment intent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment intent"
        )


@router.get("/stripe-key")
async def get_stripe_publishable_key():
    """Get Stripe publishable key for frontend"""
    try:
        from app.services.stripe_service import get_stripe_credentials
        
        _, publishable_key = get_stripe_credentials()
        
        if not publishable_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe not configured"
            )
        
        return {"publishable_key": publishable_key}
        
    except Exception as e:
        logger.error(f"Get Stripe key error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment configuration"
        )
