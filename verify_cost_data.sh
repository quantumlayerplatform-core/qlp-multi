#!/bin/bash
# Verify cost tracking data directly in PostgreSQL

echo "🔍 Cost Tracking Data Verification"
echo "=================================="

# Today's costs by model
echo -e "\n📊 Today's Costs by Model:"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    provider,
    model,
    COUNT(*) as requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_cost_usd) as total_cost_usd
FROM llm_usage
WHERE created_at >= CURRENT_DATE
GROUP BY provider, model
ORDER BY total_cost_usd DESC;"

# Last 7 days costs by tenant
echo -e "\n👥 Last 7 Days Costs by Tenant:"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    tenant_id,
    COUNT(DISTINCT workflow_id) as workflows,
    COUNT(*) as total_requests,
    SUM(total_cost_usd) as total_cost_usd
FROM llm_usage
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY tenant_id
ORDER BY total_cost_usd DESC;"

# Recent workflows with costs
echo -e "\n🔄 Recent Workflows (Last 10):"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    workflow_id,
    tenant_id,
    COUNT(*) as llm_calls,
    SUM(total_cost_usd) as total_cost,
    MAX(created_at) as last_activity
FROM llm_usage
GROUP BY workflow_id, tenant_id
ORDER BY last_activity DESC
LIMIT 10;"

# Hourly cost trend for today
echo -e "\n📈 Hourly Cost Trend (Today):"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as requests,
    SUM(total_cost_usd) as hourly_cost
FROM llm_usage
WHERE created_at >= CURRENT_DATE
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour;"

# Cost by user (if tracked)
echo -e "\n👤 Costs by User:"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    user_id,
    COUNT(*) as requests,
    SUM(total_cost_usd) as total_cost
FROM llm_usage
WHERE user_id IS NOT NULL
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY user_id
ORDER BY total_cost DESC
LIMIT 10;"

# Total statistics
echo -e "\n📊 Overall Statistics:"
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
SELECT 
    COUNT(DISTINCT tenant_id) as total_tenants,
    COUNT(DISTINCT workflow_id) as total_workflows,
    COUNT(*) as total_requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_cost_usd) as total_cost_usd,
    AVG(total_cost_usd) as avg_cost_per_request
FROM llm_usage;"