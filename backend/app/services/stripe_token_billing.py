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
    # Anthropic
    "claude_opus": "ai_tokens_claude_opus",
    "claude_sonnet": "ai_tokens_claude_sonnet", 
    "claude_haiku": "ai_tokens_claude_haiku",
    # OpenAI
    "gpt4": "ai_tokens_gpt4",
    "gpt4o": "ai_tokens_gpt4o",
    "gpt4o_mini": "ai_tokens_gpt4o_mini",
    "o1": "ai_tokens_o1",
    "o1_mini": "ai_tokens_o1_mini",
    "o3_mini": "ai_tokens_o3_mini",
    "gpt35": "ai_tokens_gpt35",
    # Google
    "gemini_pro": "ai_tokens_gemini_pro",
    "gemini_flash": "ai_tokens_gemini_flash",
    # DeepSeek
    "deepseek": "ai_tokens_deepseek",
    "deepseek_r1": "ai_tokens_deepseek_r1",
    # xAI
    "grok": "ai_tokens_grok",
    "grok3": "ai_tokens_grok3",
    # Generic fallback
    "tokens": "ai_tokens_generic",
}

# Model to meter mapping
MODEL_TO_METER = {
    # Anthropic
    "claude-opus-4-5": "claude_opus",
    "claude-3-opus-20240229": "claude_opus",
    "claude-sonnet-4-5": "claude_sonnet",
    "claude-sonnet-4-20250514": "claude_sonnet",
    "claude-3-5-sonnet-20241022": "claude_sonnet",
    "claude-haiku-4-5": "claude_haiku",
    "claude-3-5-haiku-20241022": "claude_haiku",
    # OpenAI
    "gpt-4": "gpt4",
    "gpt-4-turbo": "gpt4",
    "gpt-4-turbo-preview": "gpt4",
    "gpt-4o": "gpt4o",
    "gpt-4o-mini": "gpt4o_mini",
    "o1": "o1",
    "o1-mini": "o1_mini",
    "o3-mini": "o3_mini",
    "gpt-3.5-turbo": "gpt35",
    # Google
    "gemini-2.5-pro-preview-05-06": "gemini_pro",
    "gemini-2.5-flash-preview-05-20": "gemini_flash",
    "gemini-pro": "gemini_pro",
    # DeepSeek
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
    "deepseek-reasoner": "deepseek_r1",
    # xAI
    "grok-2-latest": "grok",
    "grok-3-latest": "grok3",
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
        
        # Always write to local usage tracking table
        try:
            from sqlalchemy import text
            cost_info = self.calculate_estimated_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                db=db,
                apply_markup=True,
            )
            db.execute(
                text("""
                    INSERT INTO user_ai_usage
                        (user_id, model_name, event_type, input_tokens, output_tokens, estimated_cost_usd, stripe_recorded)
                    VALUES (:uid, :model, :event, :inp, :out, :cost, :stripe)
                """),
                {
                    "uid": user_id,
                    "model": model,
                    "event": event_type,
                    "inp": input_tokens,
                    "out": output_tokens,
                    "cost": cost_info.get("total_cost_usd"),
                    "stripe": bool(subscription and subscription.stripe_customer_id),
                }
            )
            db.commit()
        except Exception as local_err:
            logger.warning(f"[TokenBilling] Local usage write failed: {local_err}")

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
    
    def calculate_estimated_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        db=None,
        apply_markup: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate the estimated cost for a token usage event.

        Uses pricing from ai_models table if db provided, otherwise falls
        back to static defaults. Applies billing_markup_percent from model config.

        Returns dict with input_cost, output_cost, total_cost (USD), and
        markup_percent applied.
        """
        # Default costs per 1M tokens (USD) — used when DB is unavailable
        DEFAULT_COSTS = {
            "claude-opus-4-5": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "o1": {"input": 15.0, "output": 60.0},
            "o3-mini": {"input": 1.1, "output": 4.4},
        }

        cost_per_m_input = 3.0
        cost_per_m_output = 15.0
        markup_percent = 0.0

        if db:
            try:
                from sqlalchemy import text
                row = db.execute(
                    text("SELECT cost_per_million_input, cost_per_million_output, billing_markup_percent FROM ai_models WHERE api_model_name = :m OR model_id = :m LIMIT 1"),
                    {"m": model}
                ).fetchone()
                if row:
                    cost_per_m_input = float(row[0])
                    cost_per_m_output = float(row[1])
                    markup_percent = float(row[2] or 0)
            except Exception as e:
                logger.warning(f"[TokenBilling] DB cost lookup failed: {e}")
                fallback = DEFAULT_COSTS.get(model, {})
                cost_per_m_input = fallback.get("input", cost_per_m_input)
                cost_per_m_output = fallback.get("output", cost_per_m_output)
        else:
            fallback = DEFAULT_COSTS.get(model, {})
            cost_per_m_input = fallback.get("input", cost_per_m_input)
            cost_per_m_output = fallback.get("output", cost_per_m_output)

        input_cost = (input_tokens / 1_000_000) * cost_per_m_input
        output_cost = (output_tokens / 1_000_000) * cost_per_m_output
        base_cost = input_cost + output_cost

        if apply_markup and markup_percent > 0:
            multiplier = 1 + (markup_percent / 100)
            total_cost = base_cost * multiplier
        else:
            total_cost = base_cost

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_per_million_input_usd": cost_per_m_input,
            "cost_per_million_output_usd": cost_per_m_output,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "base_cost_usd": round(base_cost, 6),
            "markup_percent": markup_percent,
            "total_cost_usd": round(total_cost, 6),
        }

    def get_invoice_preview(self, customer_id: str) -> Dict[str, Any]:
        """
        Preview the upcoming invoice for a Stripe customer.

        Uses Stripe's Invoice.upcoming() to show metered token charges
        alongside subscription items before the invoice is finalized.
        """
        if not self.stripe:
            return {"error": "Stripe not configured"}

        try:
            invoice = self.stripe.Invoice.upcoming(customer=customer_id)

            line_items = []
            for line in invoice.get("lines", {}).get("data", []):
                line_items.append({
                    "description": line.get("description", ""),
                    "amount_cents": line.get("amount", 0),
                    "amount_usd": round(line.get("amount", 0) / 100, 2),
                    "quantity": line.get("quantity"),
                    "period_start": line.get("period", {}).get("start"),
                    "period_end": line.get("period", {}).get("end"),
                    "type": line.get("type", ""),
                    "proration": line.get("proration", False),
                })

            return {
                "customer_id": customer_id,
                "period_end": invoice.get("period_end"),
                "subtotal_usd": round(invoice.get("subtotal", 0) / 100, 2),
                "tax_usd": round(invoice.get("tax", 0) / 100, 2),
                "total_usd": round(invoice.get("total", 0) / 100, 2),
                "currency": invoice.get("currency", "usd"),
                "line_items": line_items,
                "line_count": len(line_items),
            }

        except self.stripe.error.InvalidRequestError as e:
            # No upcoming invoice (e.g. no active subscription)
            if "No upcoming invoices" in str(e):
                return {"customer_id": customer_id, "total_usd": 0.0, "line_items": [], "message": "No upcoming invoice"}
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"[StripeTokenBilling] Invoice preview failed: {e}")
            return {"error": str(e)}

    def sync_price_to_stripe(
        self,
        model_id: str,
        display_name: str,
        cost_per_token_usd: float,
        meter_event_name: str,
        currency: str = "usd"
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update a metered Stripe Price for a model.

        This attaches a per-token price to a Stripe meter so that usage
        recorded via meter events is automatically included in invoices.

        Args:
            model_id: Internal model identifier
            display_name: Human-readable product name
            cost_per_token_usd: Price per token in USD (e.g. 0.000015 for $15/M)
            meter_event_name: Stripe meter event name to attach
            currency: Billing currency (default: usd)

        Returns:
            Stripe Price object dict or None on failure
        """
        if not self.stripe:
            return None

        try:
            # Cost is per token — Stripe uses integer cents, so we use unit_amount_decimal
            # for sub-cent precision
            unit_amount_decimal = str(round(cost_per_token_usd * 100, 10))  # USD → cents

            # Find or create the product
            products = self.stripe.Product.search(query=f'metadata["model_id"]:"{model_id}"', limit=1)
            if products.data:
                product = products.data[0]
            else:
                product = self.stripe.Product.create(
                    name=f"{display_name} Tokens",
                    metadata={"model_id": model_id, "source": "oppgrid"}
                )

            # Create the metered price
            price = self.stripe.Price.create(
                product=product.id,
                currency=currency,
                billing_scheme="per_unit",
                unit_amount_decimal=unit_amount_decimal,
                recurring={
                    "interval": "month",
                    "usage_type": "metered",
                    "meter": meter_event_name,
                },
                metadata={"model_id": model_id, "meter": meter_event_name}
            )

            logger.info(f"[StripeTokenBilling] Created price {price.id} for {model_id} @ {unit_amount_decimal}¢/token")

            return {
                "price_id": price.id,
                "product_id": product.id,
                "model_id": model_id,
                "unit_amount_decimal": unit_amount_decimal,
                "meter_event_name": meter_event_name,
            }

        except Exception as e:
            logger.error(f"[StripeTokenBilling] Failed to sync price for {model_id}: {e}")
            return None

    def setup_default_meters(self) -> Dict[str, Any]:
        """
        Create default meters for all supported models.
        
        Run once during initial setup.
        """
        results = []
        
        meters_to_create = [
            # Anthropic
            ("Claude Opus Tokens", "ai_tokens_claude_opus"),
            ("Claude Sonnet Tokens", "ai_tokens_claude_sonnet"),
            ("Claude Haiku Tokens", "ai_tokens_claude_haiku"),
            # OpenAI
            ("GPT-4 Tokens", "ai_tokens_gpt4"),
            ("GPT-4o Tokens", "ai_tokens_gpt4o"),
            ("GPT-4o Mini Tokens", "ai_tokens_gpt4o_mini"),
            ("o1 Tokens", "ai_tokens_o1"),
            ("o1 Mini Tokens", "ai_tokens_o1_mini"),
            ("o3 Mini Tokens", "ai_tokens_o3_mini"),
            ("GPT-3.5 Tokens", "ai_tokens_gpt35"),
            # Google
            ("Gemini Pro Tokens", "ai_tokens_gemini_pro"),
            ("Gemini Flash Tokens", "ai_tokens_gemini_flash"),
            # DeepSeek
            ("DeepSeek Tokens", "ai_tokens_deepseek"),
            ("DeepSeek R1 Tokens", "ai_tokens_deepseek_r1"),
            # xAI
            ("Grok Tokens", "ai_tokens_grok"),
            ("Grok 3 Tokens", "ai_tokens_grok3"),
            # Generic
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
