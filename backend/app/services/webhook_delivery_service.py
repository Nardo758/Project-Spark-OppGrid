"""
Webhook Delivery Service

Handles async delivery of webhook events with retry logic, exponential backoff, and failure tracking.
"""
import asyncio
import logging
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.database import SessionLocal
from app.models.agent_webhook_subscription import AgentWebhookSubscription
from app.schemas.agent_api import WebhookEventPayload

logger = logging.getLogger(__name__)

# Webhook delivery configuration
WEBHOOK_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 5  # Initial backoff for exponential retry
MAX_BACKOFF_SECONDS = 300  # Max wait between retries (5 minutes)


def _mask_url(url: str) -> str:
    """Mask webhook URL for display: keep first 8 + last 8 chars"""
    if len(url) <= 16:
        return url
    return f"{url[:8]}***{url[-8:]}"


def _hash_url(url: str) -> str:
    """Create SHA-256 hash of webhook URL"""
    return hashlib.sha256(url.encode()).hexdigest()


def get_backoff_seconds(failure_count: int) -> int:
    """Calculate exponential backoff seconds: min(5 * 2^failures, 300)"""
    backoff = INITIAL_BACKOFF_SECONDS * (2 ** failure_count)
    return min(backoff, MAX_BACKOFF_SECONDS)


async def deliver_webhook_async(
    subscription: AgentWebhookSubscription,
    event_type: str,
    data: Dict[str, Any],
    agent_id: str = "agent_default",
    request_id: Optional[str] = None,
) -> bool:
    """
    Attempt to deliver a webhook event with retry logic.
    
    Returns True if successful, False if permanently failed.
    """
    if request_id is None:
        request_id = str(uuid4())
    
    payload = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "metadata": {
            "agent_id": agent_id,
            "api_version": "v1",
            "request_id": request_id,
            "subscription_id": str(subscription.subscription_id),
        }
    }
    
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    subscription.webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-OppGrid-Event": event_type,
                        "X-OppGrid-Delivery": str(uuid4()),
                    }
                )
                
                if response.status_code == 200:
                    # Success! Update subscription tracking
                    db = SessionLocal()
                    try:
                        sub = db.query(AgentWebhookSubscription).filter(
                            AgentWebhookSubscription.subscription_id == subscription.subscription_id
                        ).first()
                        if sub:
                            sub.last_triggered_at = datetime.now(timezone.utc)
                            sub.failure_count = 0
                            sub.last_error = None
                            db.add(sub)
                            db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update subscription success: {e}")
                        db.rollback()
                    finally:
                        db.close()
                    
                    logger.info(f"✓ Webhook delivered to {_mask_url(subscription.webhook_url)}: {event_type}")
                    return True
                else:
                    logger.warning(
                        f"Webhook returned {response.status_code} for {_mask_url(subscription.webhook_url)}"
                    )
                    raise Exception(f"HTTP {response.status_code}")
        
        except asyncio.TimeoutError as e:
            logger.warning(f"Webhook timeout (attempt {attempt + 1}/{MAX_RETRIES}): {_mask_url(subscription.webhook_url)}")
            error_msg = "Request timeout"
        except Exception as e:
            logger.warning(f"Webhook delivery failed (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            error_msg = str(e)
        
        attempt += 1
        
        if attempt < MAX_RETRIES:
            wait_seconds = get_backoff_seconds(attempt - 1)
            logger.info(f"Retrying webhook in {wait_seconds}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(wait_seconds)
    
    # Permanently failed after MAX_RETRIES
    db = SessionLocal()
    try:
        sub = db.query(AgentWebhookSubscription).filter(
            AgentWebhookSubscription.subscription_id == subscription.subscription_id
        ).first()
        if sub:
            sub.failure_count += 1
            sub.last_failure_at = datetime.now(timezone.utc)
            sub.last_error = error_msg
            
            # Mark as inactive if too many failures
            if sub.failure_count >= 10:
                sub.active = False
                logger.error(f"Webhook marked inactive due to repeated failures: {_mask_url(subscription.webhook_url)}")
            
            db.add(sub)
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update subscription failure: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.error(f"✗ Webhook permanently failed: {_mask_url(subscription.webhook_url)}")
    return False


async def emit_webhook_event(
    event_type: str,
    data: Dict[str, Any],
    vertical_filter: Optional[str] = None,
    city_filter: Optional[str] = None,
    agent_id: str = "agent_default",
) -> Dict[str, int]:
    """
    Emit a webhook event to all matching active subscriptions.
    
    Filters subscriptions by:
    - Event type subscription
    - Optional vertical filter
    - Optional city filter
    
    Returns dict with delivery stats: {attempted, succeeded, failed}
    """
    db = SessionLocal()
    
    try:
        # Query matching subscriptions
        query = db.query(AgentWebhookSubscription).filter(
            and_(
                AgentWebhookSubscription.active == True,
            )
        )
        
        # Filter by subscribed events
        # Note: PostgreSQL JSONB array contains operator would be better
        # For now, we'll filter in Python
        subscriptions = query.all()
        
        matching = []
        for sub in subscriptions:
            # Check if subscribed to this event type
            events = sub.events or []
            if event_type not in events:
                continue
            
            # Apply vertical filter if specified in event
            if vertical_filter and sub.vertical_filter:
                if sub.vertical_filter.lower() != vertical_filter.lower():
                    continue
            
            # Apply city filter if specified in event
            if city_filter and sub.city_filter:
                if sub.city_filter.lower() != city_filter.lower():
                    continue
            
            matching.append(sub)
        
        logger.info(f"Emitting {event_type} event to {len(matching)} subscriptions")
        
        # Create async tasks for all deliveries
        tasks = [
            deliver_webhook_async(sub, event_type, data, agent_id)
            for sub in matching
        ]
        
        # Run all deliveries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        succeeded = sum(1 for r in results if r)
        failed = len(results) - succeeded
        
        return {
            "attempted": len(results),
            "succeeded": succeeded,
            "failed": failed,
        }
    
    finally:
        db.close()


def emit_webhook_event_sync(
    event_type: str,
    data: Dict[str, Any],
    vertical_filter: Optional[str] = None,
    city_filter: Optional[str] = None,
    agent_id: str = "agent_default",
) -> None:
    """
    Synchronous wrapper for emit_webhook_event.
    Schedules webhook deliveries in the background.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Schedule the coroutine without waiting
    loop.create_task(
        emit_webhook_event(
            event_type=event_type,
            data=data,
            vertical_filter=vertical_filter,
            city_filter=city_filter,
            agent_id=agent_id,
        )
    )


async def webhook_delivery_job(db: Session) -> Dict[str, Any]:
    """
    Background job to check for pending webhook deliveries.
    
    This could be expanded to:
    - Process a webhook delivery queue table
    - Handle retry scheduling
    - Track delivery rates
    
    For now, it's a placeholder for future webhook queue integration.
    """
    logger.info("Webhook delivery job running")
    
    # Check for inactive subscriptions that need cleanup
    try:
        inactive_subs = db.query(AgentWebhookSubscription).filter(
            AgentWebhookSubscription.active == False
        ).count()
        
        return {
            "status": "ok",
            "inactive_subscriptions": inactive_subs,
        }
    except Exception as e:
        logger.error(f"Webhook delivery job failed: {e}")
        return {"status": "error", "error": str(e)}
