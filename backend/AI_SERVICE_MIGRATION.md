# AI Service Migration Guide

## Overview

OppGrid now has a **Unified AI Service** (`unified_ai_service.py`) that centralizes all AI operations with:

- **Dynamic model registry** (database-driven, managed via Admin panel)
- **Multi-provider support** (Anthropic, OpenAI, Google, DeepSeek, xAI)
- **Usage tracking & billing** via Stripe meters
- **Tier-based access control** (free/starter/growth/pro/enterprise)
- **Rate limiting** (per-minute limits by tier)
- **Token quotas** (monthly limits by tier)
- **BYOK support** (Bring Your Own Key)

## Migration Status

### ✅ Migrated
- `ai_chat.py` — AI chat endpoint
- `idea_engine.py` — Idea generation

### 🔄 Needs Migration
- `ai_cofounder.py` — AI co-founder feature
- `ai_report_generator.py` — Report generation
- `ai_orchestrator.py` — Orchestration layer
- `copilot.py` — AI copilot
- `idea_validations.py` — Idea validation
- `opportunity_processor.py` — Opportunity processing
- `signal_to_opportunity.py` — Signal conversion
- `cached_ai_service.py` — Cached AI calls
- `ai_provider_service.py` — Provider abstraction

### 📌 Keep As-Is (Internal/Admin)
- `llm_ai_engine.py` — Low-level engine (used by unified service)
- `ai_router.py` — Legacy router (deprecated, use registry)

## How to Migrate a Service

### Before (Direct API calls)
```python
from app.services.llm_ai_engine import get_anthropic_client

client = get_anthropic_client()
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    system="You are a helpful assistant",
    messages=[{"role": "user", "content": prompt}]
)
result = response.content[0].text
```

### After (Unified Service)
```python
from app.services.unified_ai_service import get_ai_service

# In async endpoint:
ai = get_ai_service(db, user=current_user)
result = await ai.complete(
    prompt=prompt,
    system_prompt="You are a helpful assistant",
    task_type="general",  # Routes to best model
    max_tokens=1024
)
content = result["content"]
tokens_used = result["tokens"]["input"] + result["tokens"]["output"]
cost = result["cost_usd"]
```

### For Sync Functions
```python
from app.services.unified_ai_service import complete_sync

# Simple sync call (no user tracking)
content = complete_sync(
    db=db,
    prompt=prompt,
    system_prompt="You are a helpful assistant"
)
```

## Task Types for Routing

The unified service routes requests to optimal models based on task type:

| Task Type | Recommended Model | Description |
|-----------|------------------|-------------|
| `general` | Sonnet | General purpose |
| `user_conversation` | Sonnet | Chat/conversation |
| `complex_reasoning` | Opus/o1 | Deep analysis |
| `strategic_analysis` | Opus | Business strategy |
| `simple_classification` | Haiku/Flash | Fast categorization |
| `coding` | DeepSeek/o1-mini | Code generation |
| `quick_tasks` | Flash/4o-mini | Fast responses |

## Exception Handling

```python
from app.services.unified_ai_service import (
    get_ai_service,
    RateLimitError,
    QuotaExceededError,
    TierAccessError,
    AICallError
)

try:
    result = await ai.complete(prompt=prompt)
except RateLimitError:
    raise HTTPException(429, "Rate limit exceeded")
except QuotaExceededError:
    raise HTTPException(402, "Token quota exceeded")
except TierAccessError as e:
    raise HTTPException(403, str(e))
except AICallError as e:
    raise HTTPException(500, f"AI error: {e}")
```

## Database Requirements

Run the migration to create required tables:
```bash
psql $DATABASE_URL < migrations/ai_models_table.sql
```

This creates:
- `ai_models` — Model configurations
- `ai_pricing_tiers` — Tier limits and access
- `user_ai_usage` — Usage tracking (if not exists)

## Admin Panel

Manage models at: **Admin → AI Models**

Features:
- Add/edit/delete models
- Enable/disable models
- Set default model
- Configure pricing per model
- View Stripe meters
- Cost estimator

## Environment Variables

Required API keys (set in Replit Secrets):
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
DEEPSEEK_API_KEY=sk-...
XAI_API_KEY=xai-...
STRIPE_SECRET_KEY=sk_live_...
```

## Questions?

Check the unified service source: `backend/app/services/unified_ai_service.py`
