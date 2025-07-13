-- Migration: Create cost tracking tables
-- Version: 003
-- Description: Add tables for tracking LLM usage costs

-- Create llm_usage table
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    task_id VARCHAR(255),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    input_cost_usd DECIMAL(10, 6) NOT NULL,
    output_cost_usd DECIMAL(10, 6) NOT NULL,
    total_cost_usd DECIMAL(10, 6) GENERATED ALWAYS AS (input_cost_usd + output_cost_usd) STORED,
    latency_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_llm_usage_workflow ON llm_usage(workflow_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant ON llm_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_user ON llm_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant_created ON llm_usage(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider_model ON llm_usage(provider, model);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_llm_usage_updated_at BEFORE UPDATE
    ON llm_usage FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create aggregated daily costs view
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_llm_costs AS
SELECT 
    tenant_id,
    DATE(created_at AT TIME ZONE 'UTC') as usage_date,
    provider,
    model,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost_usd,
    AVG(latency_ms) as avg_latency_ms,
    MAX(created_at) as last_updated
FROM llm_usage
GROUP BY tenant_id, DATE(created_at AT TIME ZONE 'UTC'), provider, model;

-- Create indexes on materialized view
CREATE INDEX IF NOT EXISTS idx_daily_costs_tenant_date ON daily_llm_costs(tenant_id, usage_date);
CREATE INDEX IF NOT EXISTS idx_daily_costs_usage_date ON daily_llm_costs(usage_date);

-- Create monthly aggregation view
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_llm_costs AS
SELECT 
    tenant_id,
    DATE_TRUNC('month', created_at AT TIME ZONE 'UTC') as usage_month,
    provider,
    COUNT(DISTINCT workflow_id) as unique_workflows,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_cost_usd) as total_cost_usd,
    AVG(latency_ms) as avg_latency_ms
FROM llm_usage
GROUP BY tenant_id, DATE_TRUNC('month', created_at AT TIME ZONE 'UTC'), provider;

-- Create index on monthly view
CREATE INDEX IF NOT EXISTS idx_monthly_costs_tenant_month ON monthly_llm_costs(tenant_id, usage_month);

-- Create cost alerts table
CREATE TABLE IF NOT EXISTS cost_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'daily_threshold', 'monthly_threshold', 'anomaly'
    threshold_value DECIMAL(10, 2),
    actual_value DECIMAL(10, 2),
    alert_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_cost_alerts_tenant ON cost_alerts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cost_alerts_created ON cost_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_cost_alerts_unack ON cost_alerts(tenant_id, acknowledged_at) WHERE acknowledged_at IS NULL;

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_cost_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_llm_costs;
    REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_llm_costs;
END;
$$ LANGUAGE plpgsql;

-- Add comment
COMMENT ON TABLE llm_usage IS 'Tracks all LLM API usage and associated costs';
COMMENT ON MATERIALIZED VIEW daily_llm_costs IS 'Daily aggregated costs by tenant, provider, and model';
COMMENT ON MATERIALIZED VIEW monthly_llm_costs IS 'Monthly aggregated costs by tenant and provider';