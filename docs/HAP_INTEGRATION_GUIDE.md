# HAP Integration Guide

## Quick Start

The HAP (Hate, Abuse, Profanity) system is now integrated into the QuantumLayer Platform. Here's how to use it:

### 1. Basic Content Checking

```python
from src.moderation import check_content, CheckContext

# Check user input
result = await check_content(
    content="User provided text",
    context=CheckContext.USER_REQUEST,
    user_id="user123",
    tenant_id="org456"
)

if result.severity >= Severity.HIGH:
    # Block the content
    raise ValueError(f"Content rejected: {result.explanation}")
```

### 2. Agent Integration

All agents can be wrapped with HAP filtering:

```python
from src.agents.hap_filtered_agent import create_hap_filtered_agent

# Wrap any agent with HAP filtering
safe_agent = create_hap_filtered_agent(
    base_agent=original_agent,
    strict_mode=True  # Block on medium severity
)

# Use as normal - filtering happens automatically
result = await safe_agent.execute(task)
```

### 3. API Endpoints

The HAP system exposes these endpoints:

- `POST /api/v2/hap/check` - Check single content
- `POST /api/v2/hap/check-batch` - Check multiple items
- `GET /api/v2/hap/violations` - Get violation history
- `GET /api/v2/hap/config` - Get current configuration
- `PUT /api/v2/hap/config` - Update configuration
- `GET /api/v2/hap/stats` - Get statistics
- `POST /api/v2/hap/report-false-positive` - Report false positives

### 4. Database Setup

Run the migration to create HAP tables:

```bash
# Run migration
docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /migrations/004_create_hap_tables.sql

# Verify tables
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "\dt hap_*"
```

## Integration Points

### 1. Orchestrator Integration

Update the orchestrator to check user requests:

```python
# In src/orchestrator/main.py or production_endpoints.py
from src.moderation import check_content, CheckContext, Severity

@router.post("/execute")
async def execute_request(request: ExecutionRequest):
    # Check content before processing
    hap_result = await check_content(
        content=request.description,
        context=CheckContext.USER_REQUEST,
        user_id=request.user_id,
        tenant_id=request.tenant_id
    )
    
    if hap_result.severity >= Severity.HIGH:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Content policy violation",
                "details": hap_result.explanation,
                "suggestions": hap_result.suggestions
            }
        )
    
    # Continue with normal processing...
```

### 2. Agent Factory Integration

Update agent factory to return HAP-filtered agents:

```python
# In src/agents/agent_factory.py
from src.agents.hap_filtered_agent import create_hap_filtered_agent

class AgentFactory:
    def create_agent(self, agent_type: str, **kwargs):
        # Create base agent as before
        base_agent = self._create_base_agent(agent_type, **kwargs)
        
        # Wrap with HAP filtering based on config
        if self.config.get("hap_enabled", True):
            strict_mode = self.config.get("hap_strict_mode", True)
            return create_hap_filtered_agent(base_agent, strict_mode)
        
        return base_agent
```

### 3. Validation Mesh Integration

Add HAP as a validation stage:

```python
# In src/validation/validation_service.py
from src.moderation import check_content, CheckContext, Severity

async def validate_output(self, output: str, task: Task):
    # Existing validation stages...
    
    # Stage 6: HAP validation
    hap_result = await check_content(
        content=output,
        context=CheckContext.AGENT_OUTPUT,
        user_id=task.metadata.get("user_id"),
        tenant_id=task.metadata.get("tenant_id")
    )
    
    if hap_result.severity >= Severity.MEDIUM:
        validation_results.append({
            "stage": "hap",
            "passed": False,
            "severity": hap_result.severity,
            "message": hap_result.explanation
        })
```

## Configuration

### Environment Variables

Add to your `.env`:

```bash
# HAP Configuration
HAP_ENABLED=true
HAP_STRICT_MODE=true
HAP_CACHE_TTL=86400
HAP_ML_MODELS_PATH=/models/hap
```

### Per-Tenant Configuration

Tenants can customize their HAP settings:

```python
# Update configuration
PUT /api/v2/hap/config
{
    "sensitivity": "moderate",  # strict, moderate, lenient
    "categories": {
        "hate_speech": true,
        "abuse": true,
        "profanity": false,  # Allow mild profanity
        "violence": true,
        "self_harm": true,
        "sexual": true,
        "spam": false
    },
    "custom_rules": [
        {
            "name": "competitor_mention",
            "pattern": "CompetitorName",
            "category": "spam",
            "severity": "medium"
        }
    ],
    "whitelist": [
        "kill process",  # Technical terms
        "force push",
        "attack vector"
    ]
}
```

## Monitoring

### Metrics to Track

1. **Violation Rate**: Percentage of content flagged
2. **Category Distribution**: Which categories are most common
3. **False Positive Rate**: User-reported false positives
4. **Processing Latency**: HAP check performance
5. **User Risk Scores**: Users with repeated violations

### Dashboard Queries

```sql
-- Daily violation summary
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_checks,
    SUM(CASE WHEN severity != 'clean' THEN 1 ELSE 0 END) as violations,
    AVG(confidence) as avg_confidence
FROM hap_violations
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Top violating users
SELECT 
    user_id,
    risk_score,
    total_violations,
    critical_violations,
    last_violation_at
FROM hap_user_risk_scores
WHERE tenant_id = 'your_tenant'
ORDER BY risk_score DESC
LIMIT 10;

-- Category trends
SELECT 
    unnest(categories) as category,
    COUNT(*) as count
FROM hap_violations
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY category
ORDER BY count DESC;
```

## Testing

### Run HAP Tests

```bash
# Test the HAP system
python test_hap_system.py

# Test with actual services running
./start.sh  # Start all services
python test_hap_integration.py
```

### Test Different Scenarios

1. **Clean Content**: Should pass through
2. **Mild Profanity**: Flagged but allowed (unless strict mode)
3. **Hate Speech**: Always blocked
4. **Technical Terms**: Should not trigger false positives
5. **Agent Outputs**: Should be filtered/regenerated

## Performance Optimization

### 1. Caching
- Clean content is cached for 24 hours
- Violations cached for 1 hour
- Redis-based for fast lookups

### 2. Batch Processing
- Use `/check-batch` endpoint for multiple items
- Processes up to 100 items in parallel

### 3. Async Processing
- All checks are async
- Non-blocking integration with services

## Troubleshooting

### Common Issues

1. **HAP Service Not Initialized**
   ```python
   # Ensure initialization
   if not hap_service.initialized:
       await hap_service.initialize()
   ```

2. **Database Connection Issues**
   - Check DATABASE_URL in environment
   - Verify PostgreSQL is running
   - Run migrations

3. **High False Positive Rate**
   - Adjust sensitivity settings
   - Add technical terms to whitelist
   - Report false positives for tuning

4. **Performance Issues**
   - Check Redis connection
   - Monitor cache hit rate
   - Consider batch processing

## Security Considerations

1. **Content Logging**: Only hashes are stored, not actual content
2. **User Privacy**: Violations are tenant-isolated
3. **Admin Access**: Required for viewing statistics and high-risk users
4. **Audit Trail**: All configuration changes are logged

## Next Steps

1. **Deploy ML Models**: Add transformer-based detection for better accuracy
2. **Multi-language Support**: Extend beyond English
3. **Custom Categories**: Allow tenants to define custom violation types
4. **Automated Responses**: Generate safe alternatives automatically
5. **Integration with UI**: Add moderation dashboard

## API Examples

### Check Content
```bash
curl -X POST http://localhost:8000/api/v2/hap/check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please review this code",
    "context": "user_request"
  }'
```

### Get Violations
```bash
curl http://localhost:8000/api/v2/hap/violations?days=7 \
  -H "Authorization: Bearer $TOKEN"
```

### Update Config
```bash
curl -X PUT http://localhost:8000/api/v2/hap/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sensitivity": "strict",
    "categories": {
      "profanity": true,
      "spam": false
    }
  }'
```