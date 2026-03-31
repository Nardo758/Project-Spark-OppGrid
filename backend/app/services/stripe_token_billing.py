"""
Stripe Token Billing Integration

Integrates with Stripe's LLM Token Billing feature for automatic:
- Token usage tracking via Stripe Meters
- Price syncing with AI providers
- Usage-based invoicing

Setup required in Stripe Dashboard:
1. Create meters for each model/event type
2. Attach meters to prices
3. Subscribe customers to metered prices
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Meter event names - must match meters created in Stripe Dashboard
METER_EVENTS = {
    # By model family
    "claude_opus": "ai_tokens_claude_opus",
    "claude_sonnet": "ai_tokens_claude_sonnet", 
    "claude_haiku": "ai_tokens_claude_haiku",
    "gpt4": "ai_tokens_gpt4",
    "gpt35": "ai_tokens_gpt35",
    # Generic fallback
    "tokens": "ai_tokens_generic",
}

# Model to meter mapping
MODEL_TO_METER = {
    "claude-opus-4-5": "claude_opus",
    "claude-3-opus-20240229": "claude_opus",
    "claude-sonnet-4-5": "claude_sonnet",
    "claude-sonnet-4-20250514": "claude_sonnet",
    "claude-3-5-sonnet-20241022": "claude_sonnet",
    "claude-haiku-4-5": "claude_haiku",
    "claude-3-5-haiku-20241022": "claude_haiku",
    "gpt-4": "gpt4",
    "gpt-4-turbo": "gpt4",
    "gpt-4-turbo-preview": "gpt4",
    "gpt-4o": "gpt4",
    "gpt-3.5-turbo": "gpt35",
}


class StripeTokenBilling:
    """
    Handles token usage billing via Stripe Meters.
    
    Usage:
        billing = StripeTokenBilling()
        
        # After an AI call
        billing.record_usage(
            customer_id="cus_xxx",
            model="claude-opus-4-5",
            input_tokens=1000,
            output_tokens=500
        )
    """
    
    def __init__(self):
        self._stripe = None
        self._enabled = None
    
    @property
    def stripe(self):
        """Lazy load Stripe client."""
        if self._stripe is None:
            from app.services.stripe_service import get_stripe_client
            try:
                self._stripe = get_stripe_client()
            except ValueError:
                logger.warning("Stripe not configured - token billing disabled")
                self._stripe = False
        return self._stripe if self._stripe else None
    
    @property
    def enabled(self) -> bool:
        """Check if token billing is enabled."""
        if self._enabled is None:
            # Check for env var or Stripe meters
            self._enabled = os.getenv("STRIPE_TOKEN_BILLING_ENABLED", "true").lower() == "true"
        return self._enabled and self.stripe is not None
    
    def get_meter_event_name(self, model: str) -> str:
        """Get the Stripe meter event name for a model."""
        meter_key = MODEL_TO_METER.get(model, "tokens")
        return METER_EVENTS.get(meter_key, METER_EVENTS["tokens"])
    
    def record_usage(
        self,
        customer_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        event_type: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Record token usage to Stripe Meter.
        
        Args:
            customer_id: Stripe customer ID (cus_xxx)
            model: Model name (e.g., claude-opus-4-5)
            input_tokens: Input token count
            output_tokens: Output token count
            event_type: Optional event type (chat, report, etc.)
            request_id: Optional request ID for deduplication
        
        Returns:
            Meter event object or None if billing disabled
        """
        if not self.enabled:
            logger.debug("Token billing disabled - skipping meter event")
            return None
        
        if not customer_id:
            logger.warning("No customer_id provided - skipping meter event")
            return None
        
        total_tokens = input_tokens + output_tokens
        if total_tokens <= 0:
            return None
        
        event_name = self.get_meter_event_name(model)
        identifier = request_id or f"{customer_id}_{model}_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create meter event
            meter_event = self.stripe.billing.MeterEvent.create(
                event_name=event_name,
                payload={
                    "stripe_customer_id": customer_id,
                    "value": str(total_tokens),
                    # Additional metadata
                    "model": model,
                    "input_tokens": str(input_tokens),
                    "output_tokens": str(output_tokens),
                    "event_type": event_type or "unknown",
                },
                identifier=identifier,
                timestamp=int(datetime.utcnow().timestamp())
            )
            
            logger.info(
                f"[StripeTokenBilling] Recorded {total_tokens} tokens for {customer_id} "
                f"(model={model}, event={event_name})"
            )
            
            return {
                "event_name": event_name,
                "identifier": identifier,
                "tokens": total_tokens,
                "customer_id": customer_id
            }
            
        except Exception as e:
            logger.error(f"[StripeTokenBilling] Failed to record meter event: {e}")
            return None
    
    def record_usage_by_user_id(
        self,
        user_id: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        db,
        event_type: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Record usage using internal user_id (looks up Stripe customer_id).
        
        Args:
            user_id: Internal user ID
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            db: Database session
            event_type: Optional event type
            request_id: Optional request ID
        
        Returns:
            Meter event result or None
        """
        from app.models.subscription import Subscription
        
        # Get Stripe customer ID from subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription or not subscription.stripe_customer_id:
            logger.debug(f"No Stripe customer for user {user_id} - skipping meter event")
            return None
        
        return self.record_usage(
            customer_id=subscription.stripe_customer_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            event_type=event_type,
            request_id=request_id
        )
    
    def list_meters(self) -> list:
        """List all billing meters in Stripe."""
        if not self.stripe:
            return []
        
        try:
            meters = self.stripe.billing.Meter.list(limit=100)
            return [
                {
                    "id": m.id,
                    "display_name": m.display_name,
                    "event_name": m.event_name,
                    "status": m.status,
                }
                for m in meters.data
            ]
        except Exception as e:
            logger.error(f"[StripeTokenBilling] Failed to list meters: {e}")
            return []
    
    def create_meter(
        self,
        display_name: str,
        event_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new billing meter in Stripe.
        
        Args:
            display_name: Human-readable name (e.g., "Claude Opus Tokens")
            event_name: Event name for API (e.g., "ai_tokens_claude_opus")
        
        Returns:
            Meter object or None
        """
        if not self.stripe:
            return None
        
        try:
            meter = self.stripe.billing.Meter.create(
                display_name=display_name,
                event_name=event_name,
                default_aggregation={"formula": "sum"},
                customer_mapping={
                    "type": "by_id",
                    "event_payload_key": "stripe_customer_id"
                },
                value_settings={
                    "event_payload_key": "value"
                }
            )
            
            logger.info(f"[StripeTokenBilling] Created meter: {meter.id} ({event_name})")
            
            return {
                "id": meter.id,
                "display_name": display_name,
                "event_name": event_name
            }
            
        except Exception as e:
            logger.error(f"[StripeTokenBilling] Failed to create meter: {e}")
            return None
    
    def get_customer_usage(
        self,
        customer_id: str,
        meter_event_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for a customer.
        
        Args:
            customer_id: Stripe customer ID
            meter_event_name: Optional specific meter to query
        
        Returns:
            Usage summary dict
        """
        if not self.stripe:
            return {"error": "Stripe not configured"}
        
        try:
            # Get all meters
            meters = self.stripe.billing.Meter.list(limit=100)
            
            usage_by_meter = {}
            for meter in meters.data:
                if meter_event_name and meter.event_name != meter_event_name:
                    continue
                
                # Get meter event summaries for this customer
                summaries = self.stripe.billing.MeterEventSummary.list(
                    customer=customer_id,
                    meter=meter.id,
                    limit=10
                )
                
                total_tokens = sum(
                    int(s.aggregated_value) for s in summaries.data
                )
                
                usage_by_meter[meter.event_name] = {
                    "meter_id": meter.id,
                    "display_name": meter.display_name,
                    "total_tokens": total_tokens,
                    "periods": len(summaries.data)
                }
            
            return {
                "customer_id": customer_id,
                "usage": usage_by_meter,
                "total_tokens": sum(u["total_tokens"] for u in usage_by_meter.values())
            }
            
        except Exception as e:
            logger.error(f"[StripeTokenBilling] Failed to get usage: {e}")
            return {"error": str(e)}
    
    def setup_default_meters(self) -> Dict[str, Any]:
        """
        Create default meters for all supported models.
        
        Run once during initial setup.
        """
        results = []
        
        meters_to_create = [
            ("Claude Opus Tokens", "ai_tokens_claude_opus"),
            ("Claude Sonnet Tokens", "ai_tokens_claude_sonnet"),
            ("Claude Haiku Tokens", "ai_tokens_claude_haiku"),
            ("GPT-4 Tokens", "ai_tokens_gpt4"),
            ("GPT-3.5 Tokens", "ai_tokens_gpt35"),
            ("Generic AI Tokens", "ai_tokens_generic"),
        ]
        
        for display_name, event_name in meters_to_create:
            result = self.create_meter(display_name, event_name)
            results.append({
                "display_name": display_name,
                "event_name": event_name,
                "success": result is not None,
                "meter_id": result.get("id") if result else None
            })
        
        return {
            "created": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "meters": results
        }


# Singleton instance
_token_billing: Optional[StripeTokenBilling] = None


def get_token_billing() -> StripeTokenBilling:
    """Get the singleton token billing instance."""
    global _token_billing
    if _token_billing is None:
        _token_billing = StripeTokenBilling()
    return _token_billing


def record_token_usage(
    user_id: int,
    model: str,
    input_tokens: int,
    output_tokens: int,
    db,
    event_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to record token usage.
    
    Call this after any AI API call.
    """
    billing = get_token_billing()
    return billing.record_usage_by_user_id(
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        db=db,
        event_type=event_type
    )
