"""
OppGrid Opportunity Access Service — v2.1

Tracks and enforces monthly opportunity access allowances with overage billing.

Key behaviours:
- One row per (user_id, opportunity_id, billing_month) — re-access in the same
  month is FREE (increments access_count, does not charge again).
- Hard cap per tier (from TierConfig.get_monthly_cap).
- Access beyond the cap requires explicit ``confirm_overage=True``; without it
  the service returns a 402-payload dict indicating confirmation is needed.
- Overage is invoiced immediately via Stripe InvoiceItem at $30/opp.
- All DB writes are best-effort; failures are logged but do not block the caller.
"""
import logging
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.opportunity_access import OpportunityAccess
from app.models.tier_config import TierConfig

logger = logging.getLogger(__name__)


class OpportunityAccessService:
    """Enforce monthly opportunity caps with $30/opp Stripe overage billing."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_billing_month(self) -> date:
        """Return the first day of the current calendar month."""
        today = date.today()
        return date(today.year, today.month, 1)

    def get_usage(self, db: Session, user_id: int, tier: str) -> dict:
        """
        Return the current-month usage summary for *user_id*.

        Returns a dict matching the spec ``usage`` object:
            billing_month, included_cap, included_used, included_remaining,
            overage_count, overage_cost, total_accessed
        """
        billing_month = self.get_billing_month()
        cap = TierConfig.get_monthly_cap(tier)

        total = (
            db.query(func.count(OpportunityAccess.id))
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.billing_month == billing_month,
            )
            .scalar()
        ) or 0

        included_used = (
            db.query(func.count(OpportunityAccess.id))
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.billing_month == billing_month,
                OpportunityAccess.is_included == True,
            )
            .scalar()
        ) or 0

        overage_count = total - included_used

        return {
            "billing_month": billing_month.isoformat(),
            "included_cap": cap,
            "included_used": included_used,
            "included_remaining": max(0, cap - included_used),
            "overage_count": overage_count,
            "overage_cost": float(overage_count * 30.00),
            "total_accessed": total,
        }

    def check_and_record_access(
        self,
        db: Session,
        user_id: int,
        tier: str,
        opportunity_id: int,
        api_key_id: Optional[str] = None,
        access_type: str = "api",
        confirm_overage: bool = False,
        stripe_customer_id: Optional[str] = None,
    ) -> dict:
        """
        Gate and record access to one opportunity.

        Returns one of three dict shapes:

        1. Already accessed this month (free re-access)::
               {"allowed": True, "is_new_access": False, "charged": 0}

        2. New access within allowance or confirmed overage::
               {"allowed": True, "is_new_access": True, "is_included": bool,
                "charged": float, "remaining": int}

        3. Overage cap hit and ``confirm_overage`` is False::
               {"allowed": False,
                "requires_overage_confirmation": True,
                "overage_cost": 30.00,
                "usage": <usage dict>}
        """
        billing_month = self.get_billing_month()
        cap = TierConfig.get_monthly_cap(tier)
        overage_rate = TierConfig.get_overage_rate(tier)

        # ---- 1. Already accessed this month? (free re-access) -----------
        existing = (
            db.query(OpportunityAccess)
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.opportunity_id == opportunity_id,
                OpportunityAccess.billing_month == billing_month,
            )
            .first()
        )

        if existing:
            try:
                existing.last_accessed_at = datetime.utcnow()
                existing.access_count += 1
                db.commit()
            except Exception as exc:
                logger.warning("Failed to update access_count: %s", exc)
                db.rollback()
            return {"allowed": True, "is_new_access": False, "charged": 0}

        # ---- 2. Count current usage to decide included vs overage -------
        current_usage = (
            db.query(func.count(OpportunityAccess.id))
            .filter(
                OpportunityAccess.user_id == user_id,
                OpportunityAccess.billing_month == billing_month,
            )
            .scalar()
        ) or 0

        is_included = current_usage < cap

        # ---- 3. Overage confirmation gate --------------------------------
        if not is_included and not confirm_overage:
            return {
                "allowed": False,
                "requires_overage_confirmation": True,
                "overage_cost": float(overage_rate),
                "usage": self.get_usage(db, user_id, tier),
            }

        # ---- 4. Record the access ----------------------------------------
        overage_charged = 0.0 if is_included else float(overage_rate)
        api_key_uuid = None
        if api_key_id:
            try:
                api_key_uuid = uuid.UUID(str(api_key_id))
            except (ValueError, AttributeError):
                api_key_uuid = None

        access = OpportunityAccess(
            id=uuid.uuid4(),
            user_id=user_id,
            api_key_id=api_key_uuid,
            opportunity_id=opportunity_id,
            access_type=access_type,
            billing_month=billing_month,
            is_included=is_included,
            overage_charged=overage_charged,
        )
        db.add(access)

        # ---- 5. Stripe overage invoice item ------------------------------
        stripe_item_id = None
        stripe_billing_failed = False

        if overage_charged > 0:
            if not stripe_customer_id:
                # No Stripe customer: overage granted but unbilled. Mark the
                # record with a sentinel so it can be recovered later.
                access.stripe_invoice_item_id = "PENDING_NO_CUSTOMER"
                logger.error(
                    "Overage granted without Stripe customer for user %s "
                    "opportunity %s — no stripe_customer_id available",
                    user_id, opportunity_id,
                )
                stripe_billing_failed = True
            else:
                stripe_item_id = self._create_stripe_invoice_item(
                    stripe_customer_id=stripe_customer_id,
                    amount_usd=overage_charged,
                    opportunity_id=opportunity_id,
                )
                if stripe_item_id:
                    access.stripe_invoice_item_id = stripe_item_id
                else:
                    # Stripe call failed: mark for async recovery, log at ERROR.
                    access.stripe_invoice_item_id = "PENDING_STRIPE_RETRY"
                    stripe_billing_failed = True
                    logger.error(
                        "Stripe InvoiceItem creation FAILED for user %s "
                        "opportunity %s (customer %s) — access granted, "
                        "record marked PENDING_STRIPE_RETRY for recovery",
                        user_id, opportunity_id, stripe_customer_id,
                    )

        try:
            db.commit()
        except Exception as exc:
            logger.error("Failed to commit opportunity_access record: %s", exc)
            db.rollback()

        return {
            "allowed": True,
            "is_new_access": True,
            "is_included": is_included,
            "charged": overage_charged,
            "remaining": max(0, cap - current_usage - 1),
            "stripe_billing_failed": stripe_billing_failed,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_stripe_invoice_item(
        self,
        stripe_customer_id: str,
        amount_usd: float,
        opportunity_id: int,
    ) -> Optional[str]:
        """
        Create a Stripe InvoiceItem for an overage charge.

        Returns the Stripe item ID on success, or None on failure.
        Failures are logged but never propagate to the caller.
        """
        try:
            import stripe  # type: ignore
            item = stripe.InvoiceItem.create(
                customer=stripe_customer_id,
                amount=int(amount_usd * 100),
                currency="usd",
                description=f"Opportunity access overage — ID {opportunity_id}",
            )
            return item.id
        except Exception as exc:
            logger.warning(
                "Stripe InvoiceItem creation failed for customer %s: %s",
                stripe_customer_id,
                exc,
            )
            return None
