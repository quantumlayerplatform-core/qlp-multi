-- Usage Tracking and Quota Management Schema
-- Version: 002
-- Description: Tables for tracking resource usage and enforcing quotas

-- Resource type enum
CREATE TYPE resource_type AS ENUM (
    'api_calls',
    'code_generations',
    'storage_bytes',
    'compute_seconds',
    'vector_searches',
    'llm_tokens'
);

-- Quota period enum
CREATE TYPE quota_period AS ENUM ('minute', 'hour', 'day', 'month');

-- Usage events table for detailed tracking
CREATE TABLE usage_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    event_type resource_type NOT NULL,
    quantity DECIMAL(20, 4) NOT NULL DEFAULT 1,
    resource_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tenant quotas configuration
CREATE TABLE tenant_quotas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    resource_type resource_type NOT NULL,
    limit_value DECIMAL(20, 4) NOT NULL,
    period quota_period NOT NULL,
    reset_at TIMESTAMP WITH TIME ZONE,
    is_hard_limit BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, resource_type, period)
);

-- Usage summaries for quick lookups
CREATE TABLE usage_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    resource_type resource_type NOT NULL,
    period quota_period NOT NULL,
    count DECIMAL(20, 4) NOT NULL DEFAULT 0,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, resource_type, period, period_start)
);

-- Quota violations log
CREATE TABLE quota_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    resource_type resource_type NOT NULL,
    requested_amount DECIMAL(20, 4) NOT NULL,
    quota_limit DECIMAL(20, 4) NOT NULL,
    current_usage DECIMAL(20, 4) NOT NULL,
    violation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Plan limits template
CREATE TABLE plan_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan tenant_plan NOT NULL,
    resource_type resource_type NOT NULL,
    period quota_period NOT NULL,
    limit_value DECIMAL(20, 4) NOT NULL,
    is_hard_limit BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plan, resource_type, period)
);

-- Default plan limits
INSERT INTO plan_limits (plan, resource_type, period, limit_value, is_hard_limit) VALUES
-- Free plan limits
('free', 'api_calls', 'hour', 100, true),
('free', 'api_calls', 'day', 1000, true),
('free', 'code_generations', 'day', 50, true),
('free', 'code_generations', 'month', 500, true),
('free', 'storage_bytes', 'month', 1073741824, true), -- 1GB
('free', 'compute_seconds', 'day', 3600, true), -- 1 hour
('free', 'llm_tokens', 'day', 100000, true),

-- Team plan limits
('team', 'api_calls', 'hour', 1000, true),
('team', 'api_calls', 'day', 10000, true),
('team', 'code_generations', 'day', 500, true),
('team', 'code_generations', 'month', 10000, true),
('team', 'storage_bytes', 'month', 10737418240, true), -- 10GB
('team', 'compute_seconds', 'day', 36000, true), -- 10 hours
('team', 'llm_tokens', 'day', 1000000, true),

-- Enterprise plan limits (soft limits, can be exceeded with approval)
('enterprise', 'api_calls', 'hour', 10000, false),
('enterprise', 'api_calls', 'day', 100000, false),
('enterprise', 'code_generations', 'day', 5000, false),
('enterprise', 'code_generations', 'month', 100000, false),
('enterprise', 'storage_bytes', 'month', 107374182400, false), -- 100GB
('enterprise', 'compute_seconds', 'day', 360000, false), -- 100 hours
('enterprise', 'llm_tokens', 'day', 10000000, false);

-- Indexes for performance
CREATE INDEX idx_usage_events_tenant_timestamp ON usage_events(tenant_id, timestamp DESC);
CREATE INDEX idx_usage_events_user_timestamp ON usage_events(user_id, timestamp DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_usage_events_resource_type ON usage_events(tenant_id, event_type, timestamp DESC);
CREATE INDEX idx_usage_events_workspace ON usage_events(workspace_id) WHERE workspace_id IS NOT NULL;

CREATE INDEX idx_tenant_quotas_lookup ON tenant_quotas(tenant_id, resource_type, period);
CREATE INDEX idx_usage_summaries_lookup ON usage_summaries(tenant_id, resource_type, period, period_start);
CREATE INDEX idx_quota_violations_tenant ON quota_violations(tenant_id, violation_timestamp DESC);

-- Partitioning for usage_events (monthly partitions)
-- Note: Requires PostgreSQL 11+ for declarative partitioning
CREATE TABLE usage_events_template (LIKE usage_events INCLUDING ALL) PARTITION BY RANGE (timestamp);

-- Function to automatically create monthly partitions
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + interval '1 month';
    partition_name := 'usage_events_' || to_char(start_date, 'YYYY_MM');
    
    -- Check if partition exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF usage_events FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to track usage event
CREATE OR REPLACE FUNCTION track_usage(
    p_tenant_id UUID,
    p_user_id UUID,
    p_event_type resource_type,
    p_quantity DECIMAL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS void AS $$
BEGIN
    -- Insert usage event
    INSERT INTO usage_events (tenant_id, user_id, event_type, quantity, metadata)
    VALUES (p_tenant_id, p_user_id, p_event_type, p_quantity, p_metadata);
    
    -- Update summaries (could be done async in production)
    PERFORM update_usage_summary(p_tenant_id, p_event_type, p_quantity);
END;
$$ LANGUAGE plpgsql;

-- Function to update usage summary
CREATE OR REPLACE FUNCTION update_usage_summary(
    p_tenant_id UUID,
    p_resource_type resource_type,
    p_quantity DECIMAL
)
RETURNS void AS $$
DECLARE
    v_period quota_period;
    v_period_start TIMESTAMP WITH TIME ZONE;
    v_period_end TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Update for each period type
    FOR v_period IN SELECT unnest(enum_range(NULL::quota_period))
    LOOP
        -- Calculate period boundaries
        CASE v_period
            WHEN 'minute' THEN
                v_period_start := date_trunc('minute', CURRENT_TIMESTAMP);
                v_period_end := v_period_start + interval '1 minute';
            WHEN 'hour' THEN
                v_period_start := date_trunc('hour', CURRENT_TIMESTAMP);
                v_period_end := v_period_start + interval '1 hour';
            WHEN 'day' THEN
                v_period_start := date_trunc('day', CURRENT_TIMESTAMP);
                v_period_end := v_period_start + interval '1 day';
            WHEN 'month' THEN
                v_period_start := date_trunc('month', CURRENT_TIMESTAMP);
                v_period_end := v_period_start + interval '1 month';
        END CASE;
        
        -- Upsert summary
        INSERT INTO usage_summaries (
            tenant_id, resource_type, period, count, period_start, period_end
        ) VALUES (
            p_tenant_id, p_resource_type, v_period, p_quantity, v_period_start, v_period_end
        )
        ON CONFLICT (tenant_id, resource_type, period, period_start)
        DO UPDATE SET
            count = usage_summaries.count + p_quantity,
            last_updated = CURRENT_TIMESTAMP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to check quota
CREATE OR REPLACE FUNCTION check_quota(
    p_tenant_id UUID,
    p_resource_type resource_type,
    p_requested_amount DECIMAL DEFAULT 1
)
RETURNS TABLE (
    allowed BOOLEAN,
    current_usage DECIMAL,
    limit_value DECIMAL,
    period quota_period
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(us.count, 0) + p_requested_amount <= tq.limit_value OR NOT tq.is_hard_limit,
        COALESCE(us.count, 0),
        tq.limit_value,
        tq.period
    FROM tenant_quotas tq
    LEFT JOIN usage_summaries us ON 
        us.tenant_id = tq.tenant_id AND
        us.resource_type = tq.resource_type AND
        us.period = tq.period AND
        CURRENT_TIMESTAMP BETWEEN us.period_start AND us.period_end
    WHERE tq.tenant_id = p_tenant_id
        AND tq.resource_type = p_resource_type
    ORDER BY 
        CASE tq.period 
            WHEN 'minute' THEN 1
            WHEN 'hour' THEN 2
            WHEN 'day' THEN 3
            WHEN 'month' THEN 4
        END;
END;
$$ LANGUAGE plpgsql;

-- Triggers
CREATE TRIGGER update_tenant_quotas_updated_at BEFORE UPDATE ON tenant_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE usage_events IS 'Detailed log of all resource usage events';
COMMENT ON TABLE tenant_quotas IS 'Configured quotas per tenant';
COMMENT ON TABLE usage_summaries IS 'Aggregated usage data for quick quota checks';
COMMENT ON TABLE quota_violations IS 'Log of quota limit violations for monitoring';
COMMENT ON TABLE plan_limits IS 'Template limits for each subscription plan';

COMMENT ON FUNCTION track_usage IS 'Track a usage event and update summaries';
COMMENT ON FUNCTION check_quota IS 'Check if a resource request would exceed quotas';