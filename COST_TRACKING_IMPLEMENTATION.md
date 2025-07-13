# Proper Cost Tracking Implementation Guide

## Overview

The right way to implement cost tracking involves:
1. **Persistent Storage** - Store costs in PostgreSQL, not just in memory
2. **Real-time Tracking** - Track costs as they occur, not after the fact
3. **Proper Context Passing** - Ensure workflow/tenant context flows through all services
4. **API Authentication** - Secure cost data with proper authentication
5. **Monitoring & Alerts** - Set up cost alerts and monitoring

## 1. Database Schema for Cost Tracking

First, create proper database tables:

```sql
-- Create cost tracking tables
CREATE TABLE llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    task_id VARCHAR(255),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    input_cost_usd DECIMAL(10, 6) NOT NULL,
    output_cost_usd DECIMAL(10, 6) NOT NULL,
    total_cost_usd DECIMAL(10, 6) NOT NULL,
    latency_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX idx_llm_usage_workflow ON llm_usage(workflow_id);
CREATE INDEX idx_llm_usage_tenant ON llm_usage(tenant_id);
CREATE INDEX idx_llm_usage_created ON llm_usage(created_at);
CREATE INDEX idx_llm_usage_tenant_created ON llm_usage(tenant_id, created_at);

-- Create aggregated daily costs view
CREATE MATERIALIZED VIEW daily_llm_costs AS
SELECT 
    tenant_id,
    DATE(created_at) as usage_date,
    provider,
    model,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost_usd,
    AVG(latency_ms) as avg_latency_ms
FROM llm_usage
GROUP BY tenant_id, DATE(created_at), provider, model;

-- Refresh view daily
CREATE INDEX idx_daily_costs_tenant_date ON daily_llm_costs(tenant_id, usage_date);
```

## 2. Update Cost Calculator with Database Storage

```python
# src/common/cost_calculator.py - Add database storage

import asyncpg
from src.common.database import get_db_async

class PersistentCostCalculator(CostCalculator):
    """Cost calculator with PostgreSQL persistence"""
    
    async def track_llm_cost_async(
        self,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track LLM cost and persist to database"""
        
        # Calculate costs
        cost_data = self.calculate_llm_cost(
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            provider=provider
        )
        
        # Add additional fields
        cost_data.update({
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "task_id": task_id,
            "latency_ms": latency_ms,
            "metadata": metadata or {}
        })
        
        # Save to database
        async with get_db_async() as conn:
            await conn.execute("""
                INSERT INTO llm_usage (
                    workflow_id, tenant_id, user_id, task_id,
                    provider, model, input_tokens, output_tokens, total_tokens,
                    input_cost_usd, output_cost_usd, total_cost_usd,
                    latency_ms, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """, 
                workflow_id, tenant_id, user_id, task_id,
                provider, model, prompt_tokens, completion_tokens, 
                prompt_tokens + completion_tokens,
                Decimal(str(cost_data["input_cost_usd"])),
                Decimal(str(cost_data["output_cost_usd"])),
                Decimal(str(cost_data["total_cost_usd"])),
                latency_ms,
                json.dumps(metadata or {})
            )
        
        logger.info(
            "LLM cost tracked to database",
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            model=model,
            cost_usd=cost_data["total_cost_usd"]
        )
        
        return cost_data
```

## 3. Update LLM Client for Async Cost Tracking

```python
# src/agents/azure_llm_client.py - Update for async tracking

async def chat_completion(self, ...):
    # ... existing code ...
    
    # Track cost asynchronously without blocking
    if usage:
        # Fire and forget - don't wait for cost tracking
        asyncio.create_task(
            persistent_cost_calculator.track_llm_cost_async(
                model=response.model,
                provider=provider.value,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                workflow_id=kwargs.get("workflow_id"),
                tenant_id=kwargs.get("tenant_id"),
                user_id=kwargs.get("user_id"),
                task_id=kwargs.get("task_id"),
                latency_ms=int((time.time() - start_time) * 1000),
                metadata=kwargs.get("metadata", {})
            )
        )
```

## 4. Proper Context Propagation

```python
# src/orchestrator/shared_context.py - Add to SharedContext

class SharedContext:
    """Enhanced shared context with cost tracking info"""
    
    def __init__(self, request_id: str, tenant_id: str, user_id: str):
        self.request_id = request_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.workflow_id = None  # Set when workflow starts
        
    def to_cost_context(self) -> Dict[str, str]:
        """Get context for cost tracking"""
        return {
            "workflow_id": self.workflow_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id
        }
```

## 5. Update Worker to Pass Context

```python
# src/orchestrator/worker_production.py

async def execute_task_activity(
    task: Dict[str, Any], 
    tier: str, 
    request_id: str, 
    shared_context_dict: Dict[str, Any]
) -> Dict[str, Any]:
    # Extract cost context
    cost_context = {
        "workflow_id": shared_context_dict.get("workflow_id", request_id),
        "tenant_id": shared_context_dict.get("tenant_id"),
        "user_id": shared_context_dict.get("user_id"),
        "task_id": task.get("task_id")
    }
    
    # Pass to agent factory
    execution_input = {
        "task": task,
        "tier": tier,
        "context": context,
        "cost_context": cost_context,  # Add this
        "request_id": request_id
    }
```

## 6. Cost Reporting Service

```python
# src/common/cost_reporting.py

class CostReportingService:
    """Service for cost reporting from database"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def get_workflow_cost(self, workflow_id: str) -> Dict[str, Any]:
        """Get cost for a specific workflow"""
        async with asyncpg.connect(self.db_url) as conn:
            # Get all costs for workflow
            rows = await conn.fetch("""
                SELECT 
                    COUNT(*) as request_count,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(total_cost_usd) as total_cost_usd,
                    MIN(created_at) as first_request,
                    MAX(created_at) as last_request,
                    jsonb_agg(DISTINCT model) as models_used,
                    jsonb_agg(DISTINCT provider) as providers_used
                FROM llm_usage
                WHERE workflow_id = $1
            """, workflow_id)
            
            if not rows or rows[0]['request_count'] == 0:
                return None
            
            row = rows[0]
            
            # Get breakdown by model
            model_breakdown = await conn.fetch("""
                SELECT 
                    model,
                    provider,
                    COUNT(*) as count,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(total_cost_usd) as cost_usd
                FROM llm_usage
                WHERE workflow_id = $1
                GROUP BY model, provider
            """, workflow_id)
            
            return {
                "workflow_id": workflow_id,
                "total_requests": row['request_count'],
                "total_input_tokens": row['total_input_tokens'],
                "total_output_tokens": row['total_output_tokens'],
                "total_tokens": row['total_input_tokens'] + row['total_output_tokens'],
                "total_cost_usd": float(row['total_cost_usd']),
                "first_request": row['first_request'].isoformat(),
                "last_request": row['last_request'].isoformat(),
                "models_used": json.loads(row['models_used']),
                "providers_used": json.loads(row['providers_used']),
                "model_breakdown": {
                    f"{m['provider']}/{m['model']}": {
                        "count": m['count'],
                        "input_tokens": m['input_tokens'],
                        "output_tokens": m['output_tokens'],
                        "cost_usd": float(m['cost_usd'])
                    }
                    for m in model_breakdown
                }
            }
    
    async def get_tenant_costs(
        self, 
        tenant_id: str, 
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get costs for a tenant in date range"""
        async with asyncpg.connect(self.db_url) as conn:
            # Use materialized view for performance
            rows = await conn.fetch("""
                SELECT 
                    usage_date,
                    provider,
                    model,
                    request_count,
                    total_tokens,
                    total_cost_usd
                FROM daily_llm_costs
                WHERE tenant_id = $1 
                AND usage_date >= $2 
                AND usage_date <= $3
                ORDER BY usage_date
            """, tenant_id, start_date.date(), end_date.date())
            
            # Aggregate data
            total_cost = sum(row['total_cost_usd'] for row in rows)
            total_requests = sum(row['request_count'] for row in rows)
            
            # Daily breakdown
            daily_costs = {}
            for row in rows:
                date_str = row['usage_date'].isoformat()
                if date_str not in daily_costs:
                    daily_costs[date_str] = 0
                daily_costs[date_str] += float(row['total_cost_usd'])
            
            return {
                "tenant_id": tenant_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_requests": total_requests,
                "total_cost_usd": float(total_cost),
                "average_daily_cost": float(total_cost / max(len(daily_costs), 1)),
                "daily_breakdown": daily_costs,
                "projected_monthly_cost": float(total_cost / len(daily_costs) * 30) if daily_costs else 0
            }
```

## 7. Update API Endpoints to Use Database

```python
# src/api/v2/production_api.py

# Initialize cost reporting service
cost_service = CostReportingService(settings.DATABASE_URL)

@router.get("/costs")
async def get_costs(
    request: Request,
    workflow_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get costs from database"""
    try:
        tenant_id = user.get("organization_id") or user.get("tenant_id")
        
        if workflow_id:
            # Get workflow costs
            report = await cost_service.get_workflow_cost(workflow_id)
            
            # Verify tenant owns this workflow
            if report and report.get("tenant_id") != tenant_id:
                raise HTTPException(403, "Access denied")
        else:
            # Get tenant costs
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            report = await cost_service.get_tenant_costs(
                tenant_id, start_date, end_date
            )
        
        return ApiResponse(
            success=True,
            data=report,
            meta={"currency": "USD"}
        )
```

## 8. Cost Monitoring & Alerts

```python
# src/monitoring/cost_alerts.py

class CostAlertService:
    """Monitor costs and send alerts"""
    
    async def check_cost_thresholds(self):
        """Check if any tenants exceed thresholds"""
        async with asyncpg.connect(self.db_url) as conn:
            # Check daily thresholds
            alerts = await conn.fetch("""
                SELECT 
                    tenant_id,
                    SUM(total_cost_usd) as daily_cost
                FROM llm_usage
                WHERE created_at >= CURRENT_DATE
                GROUP BY tenant_id
                HAVING SUM(total_cost_usd) > 100  -- $100 daily threshold
            """)
            
            for alert in alerts:
                await self.send_alert(
                    tenant_id=alert['tenant_id'],
                    alert_type="daily_threshold",
                    cost=float(alert['daily_cost'])
                )
```

## 9. Testing Cost Tracking

```python
# test_cost_tracking_integration.py

async def test_cost_tracking():
    """Test complete cost tracking flow"""
    
    # 1. Execute a workflow
    response = await client.post("/execute", json={
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": "Test task"
    })
    
    workflow_id = response.json()["workflow_id"]
    
    # 2. Wait for completion
    await wait_for_workflow(workflow_id)
    
    # 3. Check costs are tracked
    cost_response = await client.get(
        f"/api/v2/costs?workflow_id={workflow_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert cost_response.status_code == 200
    data = cost_response.json()["data"]
    assert data["total_cost_usd"] > 0
    assert data["total_requests"] > 0
    
    # 4. Verify database records
    async with asyncpg.connect(DATABASE_URL) as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM llm_usage WHERE workflow_id = $1",
            workflow_id
        )
        assert count > 0
```

## 10. Production Deployment Checklist

- [ ] Run database migrations to create cost tables
- [ ] Update environment variables with database connection
- [ ] Deploy updated services with cost tracking
- [ ] Set up cost monitoring dashboards in Grafana
- [ ] Configure cost alert thresholds
- [ ] Test end-to-end cost tracking
- [ ] Set up daily cost report emails
- [ ] Create cost optimization recommendations

## Key Benefits of This Approach

1. **Persistent Storage** - Costs survive service restarts
2. **Performance** - Async tracking doesn't slow down LLM calls
3. **Scalability** - Database queries scale better than in-memory
4. **Security** - Proper tenant isolation and access control
5. **Analytics** - Rich cost analysis and reporting capabilities
6. **Monitoring** - Real-time alerts for cost overruns

## Next Steps

1. Create and run database migrations
2. Update services to use persistent cost tracking
3. Add cost dashboards to monitoring stack
4. Set up automated cost reports
5. Implement cost optimization recommendations