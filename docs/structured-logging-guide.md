# Structured Logging Guide for QLP Services

This guide explains how to use the new structured logging system across all QLP services.

## Overview

The structured logging system provides:
- Consistent JSON-formatted logs across all services
- Automatic request tracking with correlation IDs
- Performance metrics and monitoring
- Context propagation throughout request lifecycle
- Sensitive data masking
- Integration with observability platforms

## Basic Setup

### 1. Service Initialization

In your service's main.py:

```python
import os
from src.common.structured_logging import setup_logging, LogContext
from src.common.logging_middleware import setup_request_logging
from src.common.logging_decorators import log_function, measure_performance

# Setup structured logging
logger = setup_logging(
    service_name="your-service-name",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("ENVIRONMENT", "development") == "production"
)

# Setup FastAPI with request logging
app = FastAPI(title="Your Service")
setup_request_logging(app, "your-service-name")
```

### 2. Logging with Context

Use LogContext to add contextual information:

```python
async def process_request(request_id: str, user_id: str):
    with LogContext(request_id=request_id, user_id=user_id):
        logger.info("Processing request")
        # All logs within this context will include request_id and user_id
        await do_something()
```

### 3. Function Decorators

#### Log Function Execution

```python
@log_function(operation="create_capsule", include_args=True)
async def create_capsule(capsule_data: dict) -> QLCapsule:
    # Function execution will be automatically logged
    return capsule
```

#### Measure Performance

```python
@measure_performance(threshold_ms=5000)  # Alert if > 5 seconds
async def expensive_operation():
    # Performance will be tracked
    await complex_calculation()
```

#### Retry with Logging

```python
@retry_with_logging(max_attempts=3, backoff_factor=2.0)
async def flaky_external_call():
    # Retries will be logged with backoff
    response = await external_api.call()
    return response
```

## Logging Best Practices

### 1. Use Structured Fields

**Good:**
```python
logger.info("Task completed",
           task_id=task.id,
           duration=elapsed_time,
           status="success")
```

**Bad:**
```python
logger.info(f"Task {task.id} completed in {elapsed_time}s")
```

### 2. Log at Appropriate Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Critical problems that have caused the application to fail

### 3. Include Relevant Context

```python
logger.error("Failed to process task",
            error=e,
            task_id=task.id,
            retry_count=retries,
            next_action="will_retry")
```

### 4. Use Helper Functions

```python
# Log API requests
log_api_request(
    method="POST",
    path="/api/execute",
    status_code=200,
    duration=0.123
)

# Log operations
log_operation(
    operation="database_query",
    duration=0.045,
    success=True,
    rows_returned=42
)

# Log workflow activities
log_workflow_activity(
    activity_name="code_generation",
    activity_type="llm_call",
    status="completed",
    tokens_used=1500
)
```

## Integration Examples

### 1. Temporal Workflow Logging

```python
@activity.defn
async def generate_code_activity(params: Dict[str, Any]):
    task = params["task"]
    
    with LogContext(task_id=task.id, workflow_id=params.get("workflow_id")):
        logger.info("Starting code generation activity")
        
        try:
            result = await generate_code(task)
            log_workflow_activity(
                activity_name="generate_code",
                activity_type="code_generation",
                status="completed",
                lines_generated=len(result.split("\n"))
            )
            return result
        except Exception as e:
            log_workflow_activity(
                activity_name="generate_code",
                activity_type="code_generation",
                status="failed",
                error=str(e)
            )
            raise
```

### 2. Database Operations

```python
@log_function(operation="store_capsule")
@measure_performance(threshold_ms=1000)
async def store_capsule(capsule: QLCapsule):
    with LogContext(capsule_id=capsule.id):
        logger.info("Storing capsule in database",
                   file_count=capsule.manifest.get("files", {}).get("count", 0))
        
        try:
            await db.execute(insert_query, capsule.dict())
            logger.info("Capsule stored successfully")
        except Exception as e:
            logger.error("Failed to store capsule", error=e)
            raise
```

### 3. External API Calls

```python
@retry_with_logging(max_attempts=3, exceptions=(httpx.HTTPError,))
@measure_performance()
async def call_external_api(endpoint: str, data: dict):
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        
        logger.info("Calling external API",
                   endpoint=endpoint,
                   data_size=len(json.dumps(data)))
        
        response = await client.post(endpoint, json=data)
        
        log_api_request(
            method="POST",
            path=endpoint,
            status_code=response.status_code,
            duration=time.time() - start_time,
            response_size=len(response.content)
        )
        
        return response.json()
```

## Environment Variables

Configure logging behavior with environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Environment (determines JSON output)
ENVIRONMENT=production

# Service name (auto-set by setup_logging)
SERVICE_NAME=orchestrator
```

## Viewing Logs

### Development (Console Output)

In development, logs are human-readable:
```
2024-07-17 10:23:45 [INFO] orchestrator: Processing request
    request_id: abc-123
    user_id: user-456
    duration_ms: 1234
```

### Production (JSON Output)

In production, logs are JSON for easy parsing:
```json
{
  "timestamp": "2024-07-17T10:23:45.123Z",
  "level": "INFO",
  "service": "orchestrator",
  "message": "Processing request",
  "request_id": "abc-123",
  "user_id": "user-456",
  "duration_ms": 1234,
  "environment": "production",
  "pod_name": "orchestrator-7f8b9c-xyz"
}
```

## Monitoring and Alerting

The structured logs can be:
1. Shipped to Azure Monitor / Application Insights
2. Queried with Azure Log Analytics
3. Used to create dashboards in Grafana
4. Trigger alerts based on patterns

### Example Kusto Query

```kusto
container_logs
| where service == "orchestrator"
| where level == "ERROR"
| where timestamp > ago(1h)
| summarize error_count = count() by operation, error_type
| order by error_count desc
```

## Troubleshooting

### Common Issues

1. **Missing context in logs**
   - Ensure you're using LogContext or decorators
   - Check that context variables are being set

2. **Performance overhead**
   - Use appropriate log levels
   - Avoid logging large objects
   - Consider sampling for high-volume operations

3. **Sensitive data in logs**
   - The SensitiveDataProcessor automatically masks common fields
   - Add custom fields to SENSITIVE_FIELDS if needed

## Migration Guide

To migrate existing services:

1. Replace `import logging` with structured logging imports
2. Replace `logging.getLogger()` with `setup_logging()`
3. Update log statements to use structured fields
4. Add decorators to key functions
5. Test in development before deploying

### Before:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing task {task_id}")
```

### After:
```python
from src.common.structured_logging import setup_logging
logger = setup_logging("my-service")

logger.info("Processing task", task_id=task_id)
```
