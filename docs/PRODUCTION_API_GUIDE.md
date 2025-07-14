# Production-Grade API Implementation Guide

## Overview

The new API v2 implementation provides enterprise-grade features that were missing from the original FastAPI endpoints. This guide shows how to integrate and use these features.

## Key Improvements

### 1. **API Versioning**
- Proper versioning with `/api/v2` prefix
- Version included in all responses
- Backward compatibility support

### 2. **Authentication & Security**
```python
# All endpoints now require authentication
user = Depends(get_current_user)

# Role-based access control
admin = Depends(require_role(["admin"]))

# Permission-based access
user = Depends(require_permission(["capsule:read"]))
```

### 3. **Request Validation**
```python
class CreateCapsuleRequest(BaseModel):
    project_name: constr(min_length=1, max_length=100)
    tech_stack: List[constr(min_length=1, max_length=50)]
    
    @validator('tech_stack')
    def validate_tech_stack(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 technologies allowed")
        return v
```

### 4. **Rate Limiting**
```python
@limiter.limit("60/minute")  # Default rate limit
@limiter.limit("10/minute")  # Specific endpoint limit
```

### 5. **Standardized Responses**
```json
{
  "success": true,
  "version": "2.0.0",
  "timestamp": "2024-01-20T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {...},
  "errors": [],
  "warnings": [],
  "links": [
    {
      "href": "/api/v2/capsules/123",
      "rel": "self",
      "method": "GET"
    }
  ],
  "meta": {
    "pagination": {...}
  }
}
```

### 6. **Pagination**
```python
# Request
GET /api/v2/capsules?page=2&per_page=50&sort_by=created_at&sort_order=desc

# Response includes
"meta": {
  "pagination": {
    "total": 500,
    "page": 2,
    "per_page": 50,
    "pages": 10,
    "has_next": true,
    "has_prev": true
  }
}
```

### 7. **Async Processing**
```python
# Request
{
  "async_processing": true,
  "webhook_url": "https://your-domain.com/webhook"
}

# Response
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### 8. **Streaming Support**
```python
@router.post("/capsules/{capsule_id}/export")
async def export_capsule():
    async def generate():
        yield chunk
    
    return StreamingResponse(generate())
```

### 9. **Comprehensive Error Handling**
```python
{
  "success": false,
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Project name is required",
      "field": "project_name",
      "severity": "high"
    }
  ]
}
```

### 10. **Health & Metrics Endpoints**
```python
GET /api/v2/health?detailed=true
GET /api/v2/metrics?period=24h
```

## Integration Steps

### 1. Update Main Application

```python
# src/orchestrator/main.py

from src.api.v2.production_api import include_v2_router
from src.api.v2.middleware import setup_middleware
from src.api.v2.openapi import setup_documentation

# Configure middleware
setup_middleware(app)

# Include v2 router
include_v2_router(app)

# Setup custom documentation
setup_documentation(app)
app.openapi = lambda: custom_openapi(app)
```

### 2. Update Authentication

Replace the placeholder auth with Clerk:

```python
# src/common/clerk_auth.py
# Use the Clerk authentication implementation
```

### 3. Configure Rate Limiting

```python
# Add Redis for distributed rate limiting
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL
)
```

### 4. Add Monitoring

```python
# Integrate with your monitoring solution
from opentelemetry import trace
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
```

### 5. Configure Environment

```env
# .env
API_VERSION=2.0.0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=60/minute
ENABLE_SWAGGER_UI=true
ENABLE_REDOC=true
TRUSTED_HOSTS=*.quantumlayer.com,localhost
CORS_ORIGINS=https://app.quantumlayer.com
```

## Migration from v1

### Before (v1):
```python
@app.post("/execute")
async def execute_request(request: ExecutionRequest):
    # No auth, no validation, simple response
    return {"workflow_id": "123"}
```

### After (v2):
```python
@router.post("/capsules")
@limiter.limit("10/minute")
async def create_capsule(
    request: CreateCapsuleRequest,
    user: Dict = Depends(get_current_user)
):
    # Full validation, auth, rate limiting
    return ApiResponse(
        success=True,
        data=CapsuleResponse(...),
        links=[...],
        meta={...}
    )
```

## Testing

### Unit Tests
```python
def test_create_capsule():
    response = client.post(
        "/api/v2/capsules",
        headers={"Authorization": "Bearer test-token"},
        json={
            "project_name": "Test Project",
            "description": "Test description",
            "tech_stack": ["Python"]
        }
    )
    assert response.status_code == 201
    assert response.json()["success"] == True
```

### Load Testing
```bash
# Using k6
k6 run --vus 100 --duration 30s load-test.js
```

### Security Testing
```bash
# OWASP ZAP API scan
zap-api-scan.py -t https://api.quantumlayer.com/api/v2/openapi.json
```

## Performance Optimizations

1. **Connection Pooling**
   - Database: 20 connections min, 100 max
   - Redis: 50 connections
   - HTTP clients: Keep-alive enabled

2. **Caching**
   - Response caching with ETags
   - Redis caching for frequent queries
   - CDN for static assets

3. **Async Processing**
   - Background tasks for heavy operations
   - Webhook notifications
   - Job status polling

## Security Best Practices

1. **Authentication**
   - JWT tokens with short expiry
   - API keys for service accounts
   - OAuth2 for third-party integrations

2. **Authorization**
   - Role-based access control (RBAC)
   - Resource-level permissions
   - Tenant isolation

3. **Input Validation**
   - Strict type checking
   - Length constraints
   - Pattern validation
   - SQL injection prevention

4. **Rate Limiting**
   - Per-user limits
   - Per-endpoint limits
   - Distributed rate limiting

5. **Security Headers**
   - CORS properly configured
   - CSP for API responses
   - HSTS enabled
   - X-Frame-Options: DENY

## Monitoring & Observability

1. **Logging**
   - Structured logging with context
   - Request/response logging
   - Error tracking with Sentry

2. **Metrics**
   - Request rate
   - Response time (p50, p95, p99)
   - Error rate
   - Resource usage

3. **Tracing**
   - Distributed tracing with OpenTelemetry
   - Request flow visualization
   - Performance bottleneck identification

4. **Alerting**
   - High error rate
   - Slow response times
   - Rate limit violations
   - Security incidents

## Deployment Considerations

1. **Auto-scaling**
   - Scale based on CPU/memory
   - Scale based on request queue
   - Minimum 3 replicas for HA

2. **Health Checks**
   - Liveness probe: `/api/v2/health`
   - Readiness probe: `/api/v2/health?detailed=true`
   - Startup probe for slow starts

3. **Graceful Shutdown**
   - Complete in-flight requests
   - Stop accepting new requests
   - Close database connections

4. **Blue-Green Deployment**
   - Zero-downtime deployments
   - Instant rollback capability
   - A/B testing support

This production-grade API implementation provides the enterprise features expected from a modern SaaS platform, including proper versioning, authentication, validation, error handling, and monitoring.