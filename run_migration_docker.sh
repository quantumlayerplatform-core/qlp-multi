#!/bin/bash

echo "💰 Running Cost Tracking Migration in Docker"
echo "=========================================="

# Run the migration directly in the PostgreSQL container
docker exec qlp-postgres psql -U qlp_user -d qlp_db << 'EOF'

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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_llm_usage_workflow ON llm_usage(workflow_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant ON llm_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);

-- Create cost alerts table
CREATE TABLE IF NOT EXISTS cost_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    threshold_value DECIMAL(10, 2),
    actual_value DECIMAL(10, 2),
    alert_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255)
);

-- Check tables were created
\dt llm_usage
\dt cost_alerts

-- Show llm_usage structure
\d llm_usage

EOF

echo ""
echo "✅ Migration complete! Check output above for any errors."