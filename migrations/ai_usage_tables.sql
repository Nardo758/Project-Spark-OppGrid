-- AI Usage Tracking Tables for Stripe LLM Metering
-- Run this migration to enable usage-based billing for AI features

-- Main usage tracking table (per-request)
CREATE TABLE IF NOT EXISTS user_ai_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Request details
    event_type VARCHAR(50) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    
    -- Token counts
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Cost tracking (in USD)
    cost_usd FLOAT NOT NULL DEFAULT 0.0,
    markup_multiplier FLOAT NOT NULL DEFAULT 1.5,
    billed_amount_usd FLOAT NOT NULL DEFAULT 0.0,
    
    -- Stripe billing
    stripe_usage_record_id VARCHAR(100),
    billed_to_stripe TIMESTAMP,
    
    -- Metadata
    request_id VARCHAR(100),
    endpoint VARCHAR(200),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS ix_user_ai_usage_user_id ON user_ai_usage(user_id);
CREATE INDEX IF NOT EXISTS ix_user_ai_usage_created_at ON user_ai_usage(created_at);
CREATE INDEX IF NOT EXISTS ix_user_ai_usage_user_created ON user_ai_usage(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_user_ai_usage_billing ON user_ai_usage(user_id, billed_to_stripe);

-- Aggregated usage summaries (daily/monthly)
CREATE TABLE IF NOT EXISTS user_ai_usage_summary (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Period
    period_type VARCHAR(10) NOT NULL,  -- 'daily' or 'monthly'
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Aggregated stats
    total_requests INTEGER NOT NULL DEFAULT 0,
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Cost totals
    total_cost_usd FLOAT NOT NULL DEFAULT 0.0,
    total_billed_usd FLOAT NOT NULL DEFAULT 0.0,
    
    -- Model breakdown (JSON)
    model_breakdown TEXT,
    event_breakdown TEXT,
    
    -- Stripe billing
    stripe_invoice_id VARCHAR(100),
    invoiced_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_usage_summary_user_period ON user_ai_usage_summary(user_id, period_type, period_start);

-- Per-user quotas and limits
CREATE TABLE IF NOT EXISTS ai_usage_quotas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    
    -- Monthly token limits (0 = unlimited for enterprise)
    monthly_token_limit INTEGER NOT NULL DEFAULT 0,
    
    -- Current period usage
    current_period_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Overage handling
    allow_overage INTEGER DEFAULT 1,  -- 1 = yes, 0 = hard stop
    overage_rate_per_1k FLOAT DEFAULT 0.01,  -- $/1K tokens for overage
    
    -- Rate limiting
    requests_per_minute INTEGER DEFAULT 60,
    tokens_per_minute INTEGER DEFAULT 100000,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default quota settings per tier (for reference)
COMMENT ON TABLE ai_usage_quotas IS 'Default monthly limits:
- free: 0 (no access)
- starter: 100,000 tokens
- growth: 500,000 tokens
- pro: 2,000,000 tokens
- team: 5,000,000 tokens
- business: 20,000,000 tokens
- enterprise: unlimited (0)';
