-- AI Models Registry Table
-- Allows dynamic model management from admin panel

CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model identification
    model_id VARCHAR(100) NOT NULL UNIQUE,  -- e.g., "gpt-4o", "claude-opus-4-5"
    display_name VARCHAR(200) NOT NULL,      -- e.g., "GPT-4o", "Claude Opus"
    provider VARCHAR(50) NOT NULL,           -- openai, anthropic, google, deepseek, xai
    
    -- API configuration
    api_model_name VARCHAR(200) NOT NULL,    -- Actual API model name
    api_base_url VARCHAR(500),               -- Override base URL if needed
    api_key_env_var VARCHAR(100),            -- Env var for API key (e.g., "OPENAI_API_KEY")
    
    -- Capabilities
    max_tokens INTEGER DEFAULT 4096,
    supports_system_prompt BOOLEAN DEFAULT true,
    supports_vision BOOLEAN DEFAULT false,
    supports_function_calling BOOLEAN DEFAULT false,
    supports_streaming BOOLEAN DEFAULT true,
    context_window INTEGER DEFAULT 128000,
    
    -- Pricing (per 1M tokens)
    cost_per_million_input DECIMAL(10,4) NOT NULL,
    cost_per_million_output DECIMAL(10,4) NOT NULL,
    
    -- Billing
    stripe_meter_event_name VARCHAR(100),    -- Stripe meter for this model
    billing_markup_percent DECIMAL(5,2) DEFAULT 0,  -- Markup for customer billing
    
    -- Routing
    task_types TEXT[],                       -- Task types this model handles
    priority INTEGER DEFAULT 50,             -- Higher = preferred when multiple match
    
    -- Tier restrictions
    min_tier VARCHAR(50) DEFAULT 'free',     -- Minimum subscription tier
    tier_token_limits JSONB DEFAULT '{}',    -- {"free": 0, "starter": 100000, "pro": 1000000}
    
    -- Status
    is_enabled BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,        -- Default model for unspecified requests
    
    -- Metadata
    description TEXT,
    release_date DATE,
    deprecation_date DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_ai_models_provider ON ai_models(provider);
CREATE INDEX idx_ai_models_enabled ON ai_models(is_enabled);
CREATE INDEX idx_ai_models_task_types ON ai_models USING GIN(task_types);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_ai_models_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ai_models_updated_at
    BEFORE UPDATE ON ai_models
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_models_timestamp();

-- Insert default models
INSERT INTO ai_models (model_id, display_name, provider, api_model_name, api_key_env_var, cost_per_million_input, cost_per_million_output, stripe_meter_event_name, task_types, priority, context_window, supports_vision, supports_function_calling, description) VALUES

-- Anthropic Models
('claude-opus-4', 'Claude Opus 4', 'anthropic', 'claude-opus-4-5', 'ANTHROPIC_API_KEY', 15.00, 75.00, 'ai_tokens_claude_opus', ARRAY['complex_reasoning', 'strategic_analysis', 'creative_writing'], 100, 200000, true, true, 'Most capable Claude model for complex tasks'),
('claude-sonnet-4', 'Claude Sonnet 4', 'anthropic', 'claude-sonnet-4-20250514', 'ANTHROPIC_API_KEY', 3.00, 15.00, 'ai_tokens_claude_sonnet', ARRAY['user_conversation', 'opportunity_analysis', 'general'], 80, 200000, true, true, 'Balanced performance and cost'),
('claude-haiku-4', 'Claude Haiku 4', 'anthropic', 'claude-3-5-haiku-20241022', 'ANTHROPIC_API_KEY', 0.25, 1.25, 'ai_tokens_claude_haiku', ARRAY['simple_classification', 'quick_tasks'], 60, 200000, false, true, 'Fast and cost-effective'),

-- OpenAI Models
('gpt-4o', 'GPT-4o', 'openai', 'gpt-4o', 'OPENAI_API_KEY', 2.50, 10.00, 'ai_tokens_gpt4o', ARRAY['user_conversation', 'general', 'vision'], 85, 128000, true, true, 'OpenAI flagship multimodal model'),
('gpt-4o-mini', 'GPT-4o Mini', 'openai', 'gpt-4o-mini', 'OPENAI_API_KEY', 0.15, 0.60, 'ai_tokens_gpt4o_mini', ARRAY['simple_tasks', 'quick_responses'], 65, 128000, true, true, 'Fast and affordable'),
('o1', 'o1', 'openai', 'o1', 'OPENAI_API_KEY', 15.00, 60.00, 'ai_tokens_o1', ARRAY['complex_reasoning', 'math', 'coding'], 95, 200000, true, false, 'Advanced reasoning model'),
('o1-mini', 'o1 Mini', 'openai', 'o1-mini', 'OPENAI_API_KEY', 3.00, 12.00, 'ai_tokens_o1_mini', ARRAY['reasoning', 'coding'], 75, 128000, false, false, 'Efficient reasoning model'),
('o3-mini', 'o3 Mini', 'openai', 'o3-mini', 'OPENAI_API_KEY', 1.10, 4.40, 'ai_tokens_o3_mini', ARRAY['reasoning', 'coding', 'analysis'], 78, 200000, false, false, 'Latest efficient reasoning'),

-- Google Models  
('gemini-2.5-pro', 'Gemini 2.5 Pro', 'google', 'gemini-2.5-pro-preview-05-06', 'GOOGLE_API_KEY', 1.25, 10.00, 'ai_tokens_gemini_pro', ARRAY['general', 'web_search', 'data_summarization'], 82, 1000000, true, true, 'Google flagship with 1M context'),
('gemini-2.5-flash', 'Gemini 2.5 Flash', 'google', 'gemini-2.5-flash-preview-05-20', 'GOOGLE_API_KEY', 0.15, 0.60, 'ai_tokens_gemini_flash', ARRAY['quick_tasks', 'simple_classification'], 70, 1000000, true, true, 'Ultra-fast and cheap'),

-- DeepSeek Models
('deepseek-chat', 'DeepSeek Chat', 'deepseek', 'deepseek-chat', 'DEEPSEEK_API_KEY', 0.14, 0.28, 'ai_tokens_deepseek', ARRAY['code_generation', 'general'], 72, 128000, false, true, 'Excellent code model, very affordable'),
('deepseek-r1', 'DeepSeek R1', 'deepseek', 'deepseek-reasoner', 'DEEPSEEK_API_KEY', 0.55, 2.19, 'ai_tokens_deepseek_r1', ARRAY['complex_reasoning', 'math', 'coding'], 88, 128000, false, false, 'Open-source reasoning model'),

-- xAI Models
('grok-2', 'Grok 2', 'xai', 'grok-2-latest', 'XAI_API_KEY', 2.00, 10.00, 'ai_tokens_grok', ARRAY['social_analysis', 'trend_detection', 'general'], 76, 131072, true, true, 'xAI model with real-time knowledge'),
('grok-3', 'Grok 3', 'xai', 'grok-3-latest', 'XAI_API_KEY', 3.00, 15.00, 'ai_tokens_grok3', ARRAY['complex_reasoning', 'social_analysis'], 90, 131072, true, true, 'Latest xAI flagship')

ON CONFLICT (model_id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    api_model_name = EXCLUDED.api_model_name,
    cost_per_million_input = EXCLUDED.cost_per_million_input,
    cost_per_million_output = EXCLUDED.cost_per_million_output,
    updated_at = NOW();

-- Set Claude Sonnet as default
UPDATE ai_models SET is_default = true WHERE model_id = 'claude-sonnet-4';

-- Create pricing tiers table
CREATE TABLE IF NOT EXISTS ai_pricing_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    monthly_token_limit BIGINT,              -- NULL = unlimited
    daily_token_limit BIGINT,
    requests_per_minute INTEGER DEFAULT 60,
    markup_percent DECIMAL(5,2) DEFAULT 0,   -- Additional markup for this tier
    allowed_models TEXT[],                   -- NULL = all models
    priority_queue BOOLEAN DEFAULT false,    -- Priority API access
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO ai_pricing_tiers (tier_name, display_name, monthly_token_limit, daily_token_limit, requests_per_minute, allowed_models) VALUES
('free', 'Free', 50000, 10000, 10, ARRAY['gpt-4o-mini', 'gemini-2.5-flash', 'claude-haiku-4']),
('starter', 'Starter', 500000, 100000, 30, ARRAY['gpt-4o-mini', 'gpt-4o', 'gemini-2.5-flash', 'gemini-2.5-pro', 'claude-haiku-4', 'claude-sonnet-4', 'deepseek-chat']),
('growth', 'Growth', 2000000, 500000, 60, NULL),  -- All models
('pro', 'Pro', 10000000, 2000000, 120, NULL),
('enterprise', 'Enterprise', NULL, NULL, 300, NULL)  -- Unlimited
ON CONFLICT (tier_name) DO NOTHING;
