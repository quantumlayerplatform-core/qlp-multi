# HAP Platform Integration - The Right Way

This guide shows how to properly integrate HAP into your existing QuantumLayer Platform architecture.

## Integration Strategy

We'll integrate HAP at 4 key points:
1. **Orchestrator** - Check incoming requests
2. **Agent Factory** - Wrap agents with HAP filtering  
3. **Validation Mesh** - Add HAP as validation stage
4. **API Layer** - Expose HAP endpoints

## Step 1: Update Orchestrator

### Add HAP to production_endpoints.py

```python
# src/orchestrator/production_endpoints.py
# Add imports at the top
from src.moderation import check_content, CheckContext, Severity

# Update the generate_capsule endpoint (around line 100)
@router.post("/generate", response_model=CapsuleGenerationResponse)
async def generate_capsule(
    request: ProductionCapsuleRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CapsuleGenerationResponse:
    """Generate production-ready capsule with enterprise features"""
    
    # HAP Check - Add this before processing
    hap_result = await check_content(
        content=f"{request.description} {request.requirements or ''}",
        context=CheckContext.USER_REQUEST,
        user_id=request.user_id,
        tenant_id=request.tenant_id
    )
    
    if hap_result.severity >= Severity.HIGH:
        return CapsuleGenerationResponse(
            success=False,
            capsule_id="",
            status="blocked",
            message=f"Content policy violation: {hap_result.explanation}",
            metrics={"hap_severity": hap_result.severity},
            errors=[{
                "type": "content_policy",
                "message": hap_result.explanation,
                "suggestions": hap_result.suggestions
            }]
        )
    
    # Log if content was flagged but allowed
    if hap_result.severity >= Severity.MEDIUM:
        logger.warning(
            "Content flagged but allowed",
            user_id=request.user_id,
            severity=hap_result.severity,
            categories=hap_result.categories
        )
    
    # Continue with existing logic...
```

### Update worker_production.py

```python
# src/orchestrator/worker_production.py
# Add HAP check in decompose_request activity (around line 200)

@activity.defn
async def decompose_request(request: ExecutionRequest) -> TaskDecomposition:
    """Decompose request into atomic tasks with HAP check"""
    
    # HAP check on request
    hap_result = await check_content(
        content=request.description,
        context=CheckContext.USER_REQUEST,
        user_id=request.user_id,
        tenant_id=request.tenant_id
    )
    
    if hap_result.severity >= Severity.HIGH:
        raise ValueError(f"Request blocked by content policy: {hap_result.explanation}")
    
    # Continue with existing decomposition logic...
```

## Step 2: Update Agent Factory

### Create HAP-aware agent factory

```python
# src/agents/hap_agent_factory.py
from src.agents.agent_factory import AgentFactory
from src.agents.hap_filtered_agent import create_hap_filtered_agent
from src.common.config import settings

class HAPAgentFactory(AgentFactory):
    """Agent factory with automatic HAP filtering"""
    
    def __init__(self):
        super().__init__()
        self.hap_enabled = settings.get("HAP_ENABLED", True)
        self.hap_strict_mode = settings.get("HAP_STRICT_MODE", True)
    
    async def create_agent(self, agent_type: str, **kwargs):
        """Create agent with HAP filtering"""
        # Create base agent using parent class
        base_agent = await super().create_agent(agent_type, **kwargs)
        
        # Wrap with HAP filtering if enabled
        if self.hap_enabled:
            return create_hap_filtered_agent(
                base_agent, 
                strict_mode=self.hap_strict_mode
            )
        
        return base_agent

# Update the global factory instance
agent_factory = HAPAgentFactory()
```

### Update agent service endpoint

```python
# src/agents/agent_service.py (or wherever your agent endpoints are)
# Update execute_task endpoint

@router.post("/execute")
async def execute_task(task: Task) -> TaskResult:
    """Execute task with HAP filtering"""
    # Get HAP-filtered agent
    agent = await agent_factory.create_agent(task.agent_type)
    
    # Execute (HAP filtering happens automatically)
    result = await agent.execute(task)
    
    # Additional HAP check on output if needed
    if result.status == "completed":
        output_check = await check_content(
            content=result.output,
            context=CheckContext.AGENT_OUTPUT,
            user_id=task.metadata.get("user_id"),
            tenant_id=task.metadata.get("tenant_id")
        )
        
        # Add HAP metadata to result
        result.metadata["hap_check"] = {
            "severity": output_check.severity,
            "filtered": output_check.severity >= Severity.MEDIUM
        }
    
    return result
```

## Step 3: Update Validation Mesh

### Add HAP validation stage

```python
# src/validation/enhanced_validation_service.py
# Add HAP as validation stage

class EnhancedValidationService:
    async def validate_comprehensive(
        self, 
        code: str, 
        language: str,
        context: Dict[str, Any]
    ) -> ValidationReport:
        """Run all validation stages including HAP"""
        
        stages = []
        
        # Existing stages...
        stages.extend(self.existing_stages)
        
        # Add HAP stage
        hap_stage = await self._validate_hap(code, context)
        stages.append(hap_stage)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(stages)
        
        return ValidationReport(
            stages=stages,
            overall_score=overall_score,
            passed=overall_score >= 0.7
        )
    
    async def _validate_hap(self, code: str, context: Dict[str, Any]) -> ValidationStage:
        """HAP content validation stage"""
        try:
            result = await check_content(
                content=code,
                context=CheckContext.AGENT_OUTPUT,
                user_id=context.get("user_id"),
                tenant_id=context.get("tenant_id")
            )
            
            # Calculate score based on severity
            severity_scores = {
                Severity.CLEAN: 1.0,
                Severity.LOW: 0.9,
                Severity.MEDIUM: 0.7,
                Severity.HIGH: 0.3,
                Severity.CRITICAL: 0.0
            }
            
            score = severity_scores.get(result.severity, 0.5)
            
            return ValidationStage(
                name="content_safety",
                passed=result.severity < Severity.HIGH,
                score=score,
                details={
                    "severity": result.severity,
                    "categories": [cat.value for cat in result.categories],
                    "explanation": result.explanation
                },
                suggestions=[result.suggestions] if result.suggestions else []
            )
            
        except Exception as e:
            logger.error(f"HAP validation failed: {e}")
            # Fail open - don't block on HAP errors
            return ValidationStage(
                name="content_safety",
                passed=True,
                score=1.0,
                details={"error": str(e)},
                suggestions=[]
            )
```

## Step 4: Add HAP API Routes

### Update main.py to include HAP routes

```python
# src/orchestrator/main.py
# Add HAP router import
from src.api.v2.hap_api import router as hap_router

# Add to app (around line where other routers are included)
app.include_router(hap_router)
```

## Step 5: Update Docker Compose

### Add HAP configuration

```yaml
# docker-compose.platform.yml
# Add to orchestrator environment
orchestrator:
  environment:
    - HAP_ENABLED=true
    - HAP_STRICT_MODE=true
    - HAP_CACHE_TTL=86400

# Add to agent-factory environment  
agent-factory:
  environment:
    - HAP_ENABLED=true
    - HAP_STRICT_MODE=true
```

## Step 6: Database Migration

Run the migration to create HAP tables:

```bash
# Copy migration to container
docker cp migrations/004_create_hap_tables.sql qlp-postgres:/tmp/

# Run migration
docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /tmp/004_create_hap_tables.sql

# Verify
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "\dt hap_*"
```

## Step 7: Update Shared Models

### Add HAP metadata to models

```python
# src/common/models.py
# Update TaskResult to include HAP info

class TaskResult(BaseModel):
    # Existing fields...
    
    # Add HAP metadata
    hap_check: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="HAP content check results"
    )
    content_filtered: bool = Field(
        default=False,
        description="Whether content was modified by HAP"
    )

# Update QLCapsule to track content safety
class QLCapsule(BaseModel):
    # Existing fields...
    
    # Add content safety score
    content_safety_score: Optional[float] = Field(
        default=None,
        description="Overall content safety score (0-1)"
    )
    hap_checks: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="HAP check results for all components"
    )
```

## Step 8: Monitoring Integration

### Add HAP metrics to monitoring

```python
# src/common/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# HAP metrics
hap_checks_total = Counter(
    'hap_checks_total',
    'Total HAP content checks',
    ['context', 'severity']
)

hap_violations_total = Counter(
    'hap_violations_total', 
    'Total HAP violations detected',
    ['category', 'severity']
)

hap_processing_time = Histogram(
    'hap_processing_seconds',
    'HAP check processing time',
    ['context']
)

hap_user_risk_score = Gauge(
    'hap_user_risk_score',
    'User risk score from HAP',
    ['tenant_id', 'user_id']
)
```

## Testing the Integration

### 1. Unit Tests

```python
# tests/test_hap_integration.py
import pytest
from src.moderation import check_content, Severity

@pytest.mark.asyncio
async def test_orchestrator_blocks_inappropriate_content():
    """Test that orchestrator blocks high severity content"""
    request = ProductionCapsuleRequest(
        tenant_id="test",
        user_id="test_user",
        project_name="Test",
        description="Build this stupid f***ing system",
        language="python"
    )
    
    response = await generate_capsule(request)
    
    assert response.success is False
    assert response.status == "blocked"
    assert "content policy" in response.message.lower()

@pytest.mark.asyncio
async def test_agent_filters_output():
    """Test that agents filter inappropriate output"""
    task = Task(
        task_id="test-1",
        description="Generate code",
        agent_type=AgentType.DEVELOPER
    )
    
    agent = await agent_factory.create_agent(AgentType.DEVELOPER)
    result = await agent.execute(task)
    
    # Check that content was filtered if needed
    if result.hap_check and result.hap_check["severity"] >= "medium":
        assert result.content_filtered is True
```

### 2. Integration Tests

```bash
# Test with running platform
python test_hap_platform_integration.py

# Monitor logs
tail -f logs/orchestrator.log | grep HAP
```

### 3. Load Testing

```python
# tests/test_hap_performance.py
async def test_hap_performance():
    """Ensure HAP doesn't impact performance significantly"""
    import time
    
    # Test without HAP
    os.environ["HAP_ENABLED"] = "false"
    start = time.time()
    for _ in range(100):
        await execute_request(clean_request)
    no_hap_time = time.time() - start
    
    # Test with HAP
    os.environ["HAP_ENABLED"] = "true"
    start = time.time()
    for _ in range(100):
        await execute_request(clean_request)
    with_hap_time = time.time() - start
    
    # HAP should add less than 10% overhead
    overhead = (with_hap_time - no_hap_time) / no_hap_time
    assert overhead < 0.1
```

## Configuration Options

### Environment Variables

```bash
# Global HAP settings
HAP_ENABLED=true                    # Enable/disable HAP globally
HAP_STRICT_MODE=true               # Strict (block medium) vs lenient (block high only)
HAP_CACHE_TTL=86400               # Cache TTL in seconds
HAP_BATCH_SIZE=50                  # Max batch size for processing
HAP_TIMEOUT=5000                   # Timeout for HAP checks in ms

# Per-service settings
ORCHESTRATOR_HAP_ENABLED=true      # Override for orchestrator
AGENT_HAP_ENABLED=true             # Override for agents
VALIDATION_HAP_ENABLED=true        # Override for validation
```

### Runtime Configuration

```python
# Configure per-tenant via API
PUT /api/v2/hap/config
{
    "sensitivity": "moderate",
    "categories": {
        "profanity": false,  # Allow mild profanity for this tenant
        "violence": true
    },
    "whitelist": ["kill process", "force push"]
}
```

## Rollout Strategy

1. **Phase 1: Shadow Mode** (1 week)
   - Enable HAP but don't block
   - Log all detections
   - Analyze false positive rate

2. **Phase 2: Selective Enforcement** (1 week)
   - Block only CRITICAL severity
   - Monitor user feedback
   - Tune detection rules

3. **Phase 3: Full Enforcement** (ongoing)
   - Enable strict mode
   - Block HIGH and above
   - Continuous monitoring

## Monitoring Dashboard

Create Grafana dashboard with:
- HAP check rate by context
- Violation rate by category
- User risk score distribution
- Processing time percentiles
- False positive reports
- Top violating users/tenants

## Troubleshooting

### Common Issues

1. **Performance Impact**
   - Enable caching: Ensure Redis is running
   - Use batch API for multiple checks
   - Consider async processing for non-critical paths

2. **False Positives**
   - Add technical terms to whitelist
   - Adjust sensitivity per tenant
   - Report false positives for model tuning

3. **Integration Errors**
   - Check service logs for HAP errors
   - Verify database migrations ran
   - Ensure Redis connectivity

This integration approach ensures HAP is properly embedded throughout your platform while maintaining performance and reliability.