"""
Schemas for Agent API endpoints
"""
from pydantic import BaseModel, HttpUrl, Field, validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class WebhookSubscribeRequest(BaseModel):
    """Request body for POST /api/v1/agents/webhooks/subscribe"""
    
    webhook_url: str = Field(
        ...,
        description="HTTPS endpoint that will receive webhook events",
        example="https://agent.example.com/webhook"
    )
    
    events: List[str] = Field(
        default=["opportunity.new"],
        description="Events to subscribe to: opportunity.new, trend.updated, market.changed"
    )
    
    vertical: Optional[str] = Field(
        None,
        description="Optional filter by vertical/industry (e.g., 'coffee', 'retail')"
    )
    
    city: Optional[str] = Field(
        None,
        description="Optional filter by city (e.g., 'Austin')"
    )
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        """Validate webhook_url is HTTPS"""
        if not v.startswith('https://'):
            raise ValueError('webhook_url must use HTTPS protocol')
        return v
    
    @validator('events')
    def validate_events(cls, v):
        """Validate events are in the whitelist"""
        valid_events = {"opportunity.new", "trend.updated", "market.changed"}
        for event in v:
            if event not in valid_events:
                raise ValueError(f'Invalid event "{event}". Valid events: {", ".join(valid_events)}')
        if not v:
            raise ValueError('At least one event must be subscribed to')
        return list(set(v))  # Remove duplicates


class WebhookSubscribeResponse(BaseModel):
    """Response for POST /api/v1/agents/webhooks/subscribe"""
    
    subscription_id: str = Field(
        ...,
        description="Unique identifier for this webhook subscription"
    )
    
    status: str = Field(
        default="active",
        description="Status of the subscription (active, pending, failed)"
    )
    
    events_subscribed: List[str] = Field(
        ...,
        description="Events that will be delivered to this webhook"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when subscription was created"
    )
    
    webhook_url_masked: str = Field(
        ...,
        description="Masked webhook URL (first 8 + last 8 chars visible)",
        example="https://ag***.com/webhook"
    )
    
    filters: Optional[dict] = Field(
        None,
        description="Applied filters (vertical, city)"
    )


class WebhookEventPayload(BaseModel):
    """Payload sent to webhook endpoints"""
    
    event_type: str = Field(
        ...,
        description="Type of event: opportunity.new, trend.updated, market.changed"
    )
    
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp when event occurred"
    )
    
    data: dict = Field(
        ...,
        description="Event-specific data"
    )
    
    metadata: dict = Field(
        ...,
        description="Request metadata (agent_id, api_version, request_id)"
    )


class WebhookSubscriptionListResponse(BaseModel):
    """Response for GET /api/v1/agents/webhooks"""
    
    subscriptions: List[WebhookSubscribeResponse]
    total: int
    
    
class WebhookSubscriptionDeleteResponse(BaseModel):
    """Response for DELETE /api/v1/agents/webhooks/{subscription_id}"""
    
    subscription_id: str
    status: str = "deleted"
    message: str
