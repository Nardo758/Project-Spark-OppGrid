"""
AI Metering Service

Tracks AI usage per user and syncs with Stripe for usage-based billing.

Flow:
1. AI call made → record_usage() called with tokens/cost
2. Usage stored in user_ai_usage table
3. Periodic job syncs unbilled usage to Stripe meter
4. Stripe invoices user at billing period end
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


# Model cost per 1M tokens (mirrors ai_router.py but with additional models)
MODEL_COSTS = {
    # Anthropic
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    
    # OpenAI
    "gpt-5": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    
    # Google
    "gemini-pro": {"input": 0.5, "output": 1.5},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
}

# Default markup multiplier (OppGrid takes 50% margin)
DEFAULT_MARKUP = 1.5

# Tier-based token limits per month
TIER_TOKEN_LIMITS = {
    "free": 0,           # No AI access
    "starter": 100_000,  # 100K tokens
    "growth": 500_000,   # 500K tokens
    "pro": 2_000_000,    # 2M tokens
    "team": 5_000_000,   # 5M tokens
    "business": 20_000_000,  # 20M tokens
    "enterprise": 0,     # Unlimited (0 = no limit)
}


@dataclass
class UsageRecord:
    """Record of a single AI usage event."""
    user_id: int
    event_type: str
    model_provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    billed_amount_usd: float
    request_id: Optional[str] = None
    endpoint: Optional[str] = None


class AITeringService:
    """
    Handles AI usage metering and Stripe billing integration.
    
    Usage:
        service = AIMeteringService(db)
        
        # After an AI call
        service.record_usage(
            user_id=123,
            event_type="report",
            model_name="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=2000
        )
        
        # Get user's usage
        usage = service.get_user_usage(user_id=123)
        
        # Sync to Stripe (call periodically)
        service.sync_to_stripe()
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._stripe = None
    
    @property
    def stripe(self):
        """Lazy load Stripe client."""
        if self._stripe is None:
            from app.services.stripe_service import get_stripe_client
            try:
                self._stripe = get_stripe_client()
            except ValueError:
                logger.warning("Stripe not configured - billing disabled")
                self._stripe = False  # Mark as unavailable
        return self._stripe if self._stripe else None
    
    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD for token usage."""
        costs = MODEL_COSTS.get(model_name, {"input": 3.0, "output": 15.0})
        
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        
        return round(input_cost + output_cost, 6)
    
    def get_user_markup(self, user_id: int) -> float:
        """Get markup multiplier for a user (can be customized per tier/user)."""
        # For now, use default markup
        # Could look up user's subscription tier and apply different markups
        return DEFAULT_MARKUP
    
    def record_usage(
        self,
        user_id: int,
        event_type: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        model_provider: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost_override: Optional[float] = None
    ) -> UsageRecord:
        """
        Record an AI usage event.
        
        Args:
            user_id: User who made the request
            event_type: Type of usage (chat, report, analysis, etc.)
            model_name: Model used (e.g., claude-3-5-sonnet-20241022)
            input_tokens: Input token count
            output_tokens: Output token count
            model_provider: Provider name (auto-detected if not provided)
            request_id: Optional request ID for tracing
            endpoint: Optional API endpoint that triggered this
            cost_override: Override calculated cost (for special pricing)
        
        Returns:
            UsageRecord with all details including billed amount
        """
        from app.models.ai_usage import UserAIUsage
        
        # Auto-detect provider from model name
        if not model_provider:
            if "claude" in model_name.lower():
                model_provider = "anthropic"
            elif "gpt" in model_name.lower():
                model_provider = "openai"
            elif "deepseek" in model_name.lower():
                model_provider = "deepseek"
            elif "gemini" in model_name.lower():
                model_provider = "google"
            else:
                model_provider = "unknown"
        
        # Calculate cost
        cost_usd = cost_override if cost_override is not None else self.calculate_cost(
            model_name, input_tokens, output_tokens
        )
        
        # Apply markup
        markup = self.get_user_markup(user_id)
        billed_amount = round(cost_usd * markup, 6)
        
        # Create usage record
        usage = UserAIUsage(
            user_id=user_id,
            event_type=event_type,
            model_provider=model_provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
            markup_multiplier=markup,
            billed_amount_usd=billed_amount,
            request_id=request_id,
            endpoint=endpoint
        )
        
        self.db.add(usage)
        self.db.commit()
        
        logger.info(
            f"[AIMetering] User {user_id}: {event_type} on {model_name} "
            f"({input_tokens}+{output_tokens} tokens, ${billed_amount:.4f})"
        )
        
        return UsageRecord(
            user_id=user_id,
            event_type=event_type,
            model_provider=model_provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            billed_amount_usd=billed_amount,
            request_id=request_id,
            endpoint=endpoint
        )
    
    def get_user_usage(
        self,
        user_id: int,
        period: str = "current_month"
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a user.
        
        Args:
            user_id: User ID
            period: 'current_month', 'last_month', 'all_time', or 'today'
        
        Returns:
            Usage statistics including totals and breakdowns
        """
        from app.models.ai_usage import UserAIUsage
        
        # Determine date range
        now = datetime.utcnow()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "current_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "last_month":
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_date = (first_of_month - timedelta(days=1)).replace(day=1)
            now = first_of_month - timedelta(seconds=1)
        else:  # all_time
            start_date = datetime(2020, 1, 1)
        
        # Query usage
        query = self.db.query(UserAIUsage).filter(
            UserAIUsage.user_id == user_id,
            UserAIUsage.created_at >= start_date,
            UserAIUsage.created_at <= now
        )
        
        usage_records = query.all()
        
        if not usage_records:
            return {
                "user_id": user_id,
                "period": period,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_billed_usd": 0.0,
                "model_breakdown": {},
                "event_breakdown": {}
            }
        
        # Aggregate
        total_requests = len(usage_records)
        total_tokens = sum(r.total_tokens for r in usage_records)
        total_cost = sum(r.cost_usd for r in usage_records)
        total_billed = sum(r.billed_amount_usd for r in usage_records)
        
        # Breakdowns
        model_breakdown = {}
        event_breakdown = {}
        
        for r in usage_records:
            model_breakdown[r.model_name] = model_breakdown.get(r.model_name, 0) + r.total_tokens
            event_breakdown[r.event_type] = event_breakdown.get(r.event_type, 0) + r.total_tokens
        
        return {
            "user_id": user_id,
            "period": period,
            "period_start": start_date.isoformat(),
            "period_end": now.isoformat(),
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_input_tokens": sum(r.input_tokens for r in usage_records),
            "total_output_tokens": sum(r.output_tokens for r in usage_records),
            "total_cost_usd": round(total_cost, 4),
            "total_billed_usd": round(total_billed, 4),
            "model_breakdown": model_breakdown,
            "event_breakdown": event_breakdown
        }
    
    def check_quota(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user has remaining quota.
        
        Returns:
            {
                "allowed": bool,
                "remaining_tokens": int,
                "limit": int,
                "used": int,
                "percentage_used": float
            }
        """
        from app.models.user import User
        from app.models.ai_usage import AIUsageQuota
        
        # Get user's tier
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"allowed": False, "reason": "user_not_found"}
        
        tier = "free"
        if user.subscription and user.subscription.tier:
            tier = user.subscription.tier.value.lower()
        
        limit = TIER_TOKEN_LIMITS.get(tier, 0)
        
        # Check for custom quota
        quota = self.db.query(AIUsageQuota).filter(AIUsageQuota.user_id == user_id).first()
        if quota and quota.monthly_token_limit > 0:
            limit = quota.monthly_token_limit
        
        # Get current month usage
        usage = self.get_user_usage(user_id, period="current_month")
        used = usage["total_tokens"]
        
        # Unlimited for enterprise or limit=0
        if limit == 0 and tier == "enterprise":
            return {
                "allowed": True,
                "remaining_tokens": float('inf'),
                "limit": 0,
                "used": used,
                "percentage_used": 0,
                "tier": tier
            }
        
        # Check quota
        if limit == 0:  # Free tier with no access
            return {
                "allowed": False,
                "remaining_tokens": 0,
                "limit": 0,
                "used": used,
                "percentage_used": 100,
                "tier": tier,
                "reason": "no_ai_access"
            }
        
        remaining = max(0, limit - used)
        percentage = (used / limit * 100) if limit > 0 else 0
        
        # Check overage setting
        allow_overage = True
        if quota:
            allow_overage = quota.allow_overage == 1
        
        allowed = remaining > 0 or allow_overage
        
        return {
            "allowed": allowed,
            "remaining_tokens": remaining,
            "limit": limit,
            "used": used,
            "percentage_used": round(percentage, 1),
            "tier": tier,
            "allow_overage": allow_overage
        }
    
    def sync_to_stripe(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Sync unbilled usage to Stripe meter.
        
        This should be called periodically (e.g., every hour or at billing period end).
        Uses Stripe's Usage Records API for metered billing.
        
        Args:
            batch_size: Max records to sync per call
        
        Returns:
            Summary of sync operation
        """
        if not self.stripe:
            logger.warning("[AIMetering] Stripe not configured - skipping sync")
            return {"synced": 0, "error": "stripe_not_configured"}
        
        from app.models.ai_usage import UserAIUsage
        
        # Get unbilled usage records
        unbilled = self.db.query(UserAIUsage).filter(
            UserAIUsage.billed_to_stripe.is_(None),
            UserAIUsage.billed_amount_usd > 0
        ).limit(batch_size).all()
        
        if not unbilled:
            return {"synced": 0, "message": "no_unbilled_records"}
        
        synced = 0
        errors = []
        
        # Group by user for efficiency
        user_records = {}
        for record in unbilled:
            if record.user_id not in user_records:
                user_records[record.user_id] = []
            user_records[record.user_id].append(record)
        
        for user_id, records in user_records.items():
            try:
                # Get user's Stripe customer/subscription
                from app.models.user import User
                user = self.db.query(User).filter(User.id == user_id).first()
                
                if not user or not user.stripe_customer_id:
                    # Skip users without Stripe customer
                    for r in records:
                        r.billed_to_stripe = datetime.utcnow()
                        r.stripe_usage_record_id = "no_stripe_customer"
                    continue
                
                # Get subscription item ID for metered billing
                subscription_item_id = self._get_metered_subscription_item(user)
                
                if not subscription_item_id:
                    for r in records:
                        r.billed_to_stripe = datetime.utcnow()
                        r.stripe_usage_record_id = "no_metered_item"
                    continue
                
                # Calculate total tokens for this user
                total_tokens = sum(r.total_tokens for r in records)
                
                # Report usage to Stripe
                # Stripe meters usage in the unit you define (we use 1K tokens)
                usage_quantity = total_tokens // 1000  # Convert to 1K units
                
                if usage_quantity > 0:
                    usage_record = self.stripe.SubscriptionItem.create_usage_record(
                        subscription_item_id,
                        quantity=usage_quantity,
                        timestamp=int(datetime.utcnow().timestamp()),
                        action='increment'
                    )
                    
                    for r in records:
                        r.billed_to_stripe = datetime.utcnow()
                        r.stripe_usage_record_id = usage_record.id
                    
                    synced += len(records)
                    logger.info(f"[AIMetering] Synced {usage_quantity}K tokens for user {user_id}")
                
            except Exception as e:
                logger.error(f"[AIMetering] Failed to sync user {user_id}: {e}")
                errors.append({"user_id": user_id, "error": str(e)})
        
        self.db.commit()
        
        return {
            "synced": synced,
            "total_records": len(unbilled),
            "users_processed": len(user_records),
            "errors": errors
        }
    
    def _get_metered_subscription_item(self, user) -> Optional[str]:
        """Get the metered subscription item ID for a user."""
        if not user.stripe_subscription_id:
            return None
        
        try:
            subscription = self.stripe.Subscription.retrieve(user.stripe_subscription_id)
            
            # Find the metered price item (look for "ai_tokens" in metadata or price ID)
            for item in subscription.get("items", {}).get("data", []):
                price = item.get("price", {})
                
                # Check if this is the AI tokens metered price
                if price.get("recurring", {}).get("usage_type") == "metered":
                    # Check metadata or price ID pattern
                    if "ai" in price.get("id", "").lower() or \
                       "token" in price.get("id", "").lower() or \
                       price.get("metadata", {}).get("type") == "ai_tokens":
                        return item.get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"[AIMetering] Failed to get subscription item: {e}")
            return None
    
    def create_usage_summary(self, user_id: int, period_type: str = "monthly") -> Dict[str, Any]:
        """Create or update usage summary for a period."""
        from app.models.ai_usage import UserAIUsageSummary
        
        now = datetime.utcnow()
        
        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
        else:  # monthly
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Last day of month
            next_month = (period_start + timedelta(days=32)).replace(day=1)
            period_end = next_month - timedelta(seconds=1)
        
        # Get usage for period
        usage = self.get_user_usage(user_id, period="current_month" if period_type == "monthly" else "today")
        
        # Check if summary exists
        existing = self.db.query(UserAIUsageSummary).filter(
            UserAIUsageSummary.user_id == user_id,
            UserAIUsageSummary.period_type == period_type,
            UserAIUsageSummary.period_start == period_start
        ).first()
        
        if existing:
            # Update existing
            existing.total_requests = usage["total_requests"]
            existing.total_input_tokens = usage["total_input_tokens"]
            existing.total_output_tokens = usage["total_output_tokens"]
            existing.total_tokens = usage["total_tokens"]
            existing.total_cost_usd = usage["total_cost_usd"]
            existing.total_billed_usd = usage["total_billed_usd"]
            existing.model_breakdown = json.dumps(usage["model_breakdown"])
            existing.event_breakdown = json.dumps(usage["event_breakdown"])
            existing.updated_at = now
        else:
            # Create new
            summary = UserAIUsageSummary(
                user_id=user_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                total_requests=usage["total_requests"],
                total_input_tokens=usage["total_input_tokens"],
                total_output_tokens=usage["total_output_tokens"],
                total_tokens=usage["total_tokens"],
                total_cost_usd=usage["total_cost_usd"],
                total_billed_usd=usage["total_billed_usd"],
                model_breakdown=json.dumps(usage["model_breakdown"]),
                event_breakdown=json.dumps(usage["event_breakdown"])
            )
            self.db.add(summary)
        
        self.db.commit()
        return usage


# Convenience function
def get_ai_metering_service(db: Session) -> AITeringService:
    """Get an AI metering service instance."""
    return AITeringService(db)
