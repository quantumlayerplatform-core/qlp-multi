# Cost Tracking Guide for Quantum Layer Platform

## Overview

The platform now includes comprehensive cost tracking for all LLM usage across different providers (OpenAI, Azure OpenAI, Anthropic, Groq).

## How Cost Tracking Works

### 1. Automatic Tracking
Every LLM call made through the platform is automatically tracked with:
- Model used
- Input/output tokens
- Provider (OpenAI, Azure, etc.)
- Cost in USD
- Associated workflow, tenant, and user IDs

### 2. Cost Calculation
Costs are calculated based on current pricing (as of 2024):
- **GPT-4 Turbo**: $10/1M input, $30/1M output tokens
- **GPT-3.5 Turbo**: $0.50/1M input, $1.50/1M output tokens
- **Claude 3 Opus**: $15/1M input, $75/1M output tokens
- **Llama 3 (Groq)**: $0.59/1M input, $0.79/1M output tokens

### 3. Integration Points

#### Azure LLM Client
```python
# Automatically tracks costs when calling LLM
response = await llm_client.chat_completion(
    messages=[...],
    model="gpt-4-turbo",
    workflow_id=workflow_id,  # Links cost to workflow
    tenant_id=tenant_id,      # Links to tenant
    user_id=user_id           # Links to user
)

# Response includes cost data
print(f"Cost: ${response['cost']['total_cost_usd']:.6f}")
```

#### Production API v2
```bash
# Get cost estimate before execution
curl "http://localhost:8000/api/v2/costs/estimate?complexity=medium&tech_stack=Python&tech_stack=FastAPI"

# Get actual costs for a workflow
curl "http://localhost:8000/api/v2/costs?workflow_id=qlp-execution-xyz"

# Get tenant costs for last 30 days
curl "http://localhost:8000/api/v2/costs?period_days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Endpoints

### 1. Cost Estimation
**GET** `/api/v2/costs/estimate`

Estimate the cost of generating a capsule based on complexity.

Parameters:
- `complexity`: trivial, simple, medium, complex, very_complex
- `tech_stack`: List of technologies (affects complexity)

Response:
```json
{
  "success": true,
  "data": {
    "complexity": "medium",
    "tech_stack": ["Python", "FastAPI"],
    "estimated_input_tokens": 10000,
    "estimated_output_tokens": 25000,
    "model_estimates": {
      "gpt-3.5-turbo": {
        "estimated_cost_usd": 0.0425,
        "estimated_tokens": 35000
      },
      "gpt-4-turbo": {
        "estimated_cost_usd": 0.85,
        "estimated_tokens": 35000
      }
    },
    "recommended_model": "gpt-4-turbo"
  }
}
```

### 2. Cost Report
**GET** `/api/v2/costs`

Get actual costs for your organization or a specific workflow.

Parameters:
- `workflow_id` (optional): Get costs for specific workflow
- `period_days` (optional): Number of days to look back (default: 30)

Response:
```json
{
  "success": true,
  "data": {
    "tenant_id": "org_123",
    "period_days": 30,
    "total_requests": 156,
    "total_cost_usd": 12.45,
    "average_daily_cost": 0.42,
    "daily_breakdown": {
      "2024-01-20": 0.85,
      "2024-01-21": 0.62
    },
    "projected_monthly_cost": 12.60
  }
}
```

### 3. Metrics with Costs
**GET** `/api/v2/metrics`

The metrics endpoint now includes cost data:
```json
{
  "costs": {
    "llm_tokens": 1567890,
    "compute_hours": 45.2,
    "storage_gb": 128.5,
    "estimated_cost": 234.56,
    "total_llm_cost_usd": 15.67
  }
}
```

## Cost Optimization Tips

1. **Use Appropriate Tiers**
   - T0 (Simple tasks): Uses cheaper models like GPT-3.5
   - T1 (Medium tasks): Uses GPT-4 mini
   - T2/T3 (Complex tasks): Uses GPT-4 or Claude

2. **Set Complexity Correctly**
   - Accurate complexity helps estimate costs
   - Overestimating complexity wastes tokens

3. **Monitor Usage**
   - Check daily costs: `/api/v2/costs`
   - Set up alerts for cost thresholds
   - Review model usage patterns

4. **Use Caching**
   - Platform caches similar requests
   - Reduces redundant LLM calls

## Example: Tracking Costs in Your Application

```python
# When creating a capsule
response = requests.post("/api/v2/capsules", json={
    "project_name": "My Project",
    "description": "Build an API",
    "tech_stack": ["Python"],
    "metadata": {"complexity": "medium"}
})

# The response includes cost estimate
cost_estimate = response.json()["meta"]["estimated_cost"]

# After execution, get actual costs
workflow_id = response.json()["data"]["workflow_id"]
cost_report = requests.get(f"/api/v2/costs?workflow_id={workflow_id}")
actual_cost = cost_report.json()["data"]["total_cost_usd"]

print(f"Estimated: ${cost_estimate}")
print(f"Actual: ${actual_cost}")
```

## Cost Data Storage

Cost data is stored in:
1. **In-memory**: Recent costs for fast access
2. **PostgreSQL**: Historical data for reporting
3. **Metrics**: Aggregated for monitoring

## Future Enhancements

1. **Budget Alerts**: Set spending limits
2. **Cost Allocation**: Tag costs by project/department
3. **Optimization Suggestions**: AI-powered cost reduction
4. **Detailed Reports**: Export to CSV/Excel
5. **Multi-currency Support**: Show costs in different currencies

## Troubleshooting

If costs aren't being tracked:
1. Check that workflow_id is being passed to LLM calls
2. Verify tenant_id is set in the context
3. Check logs for cost calculation errors
4. Ensure Redis is running for rate limiting

## Contact

For questions about cost tracking or billing, contact your platform administrator.