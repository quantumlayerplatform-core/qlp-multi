# API v2 Migration Guide

This guide helps migrate existing QLP endpoints to the production-grade API v2 standard.

## Overview of Changes

### 1. **API Versioning**
- All endpoints moved under `/api/v2` prefix
- Version included in all responses
- Backward compatibility maintained

### 2. **Standardized Response Format**
All responses now follow the `ApiResponse` model:
```json
{
  "success": true,
  "version": "2.0.0",
  "timestamp": "2024-01-20T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {...},
  "errors": [],
  "warnings": [],
  "links": [...],
  "meta": {...}
}
```

### 3. **Authentication**
- Bearer token authentication (Clerk JWT)
- Role-based access control
- Permission-based authorization

### 4. **Rate Limiting**
- Default: 60 requests/minute
- Endpoint-specific limits
- Redis-backed distributed limiting

## Migration Examples

### Example 1: Simple Endpoint

**Before (v1):**
```python
@app.post("/execute")
async def execute_request(request: ExecutionRequest):
    workflow_id = await start_workflow(request)
    return {"workflow_id": workflow_id}
```

**After (v2):**
```python
@router.post("/execute")
@limiter.limit("30/minute")
async def execute_request(
    request: Request,
    execution_request: ExecutionRequest,
    user: Dict = Depends(get_current_user)
):
    await track_request(request, user)
    
    try:
        workflow_id = await start_workflow(execution_request)
        
        return ApiResponse(
            success=True,
            data={"workflow_id": workflow_id},
            links=[
                Link(
                    href=f"/api/v2/workflows/{workflow_id}",
                    rel="status",
                    method="GET"
                )
            ]
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            errors=[
                ErrorDetail(
                    code="EXECUTION_FAILED",
                    message=str(e),
                    severity=ErrorSeverity.high
                )
            ]
        )
```

### Example 2: List Endpoint with Pagination

**Before (v1):**
```python
@app.get("/capsules")
async def list_capsules():
    capsules = await get_all_capsules()
    return capsules
```

**After (v2):**
```python
@router.get("/capsules")
@limiter.limit("60/minute")
async def list_capsules(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    # Apply filters and pagination
    query = build_query(user["organization_id"], status)
    total = await count_capsules(query)
    capsules = await get_capsules(query, page, per_page)
    
    return ApiResponse(
        success=True,
        data=capsules,
        meta={
            "pagination": PaginationMeta(
                total=total,
                page=page,
                per_page=per_page,
                pages=(total + per_page - 1) // per_page,
                has_next=page * per_page < total,
                has_prev=page > 1
            )
        }
    )
```

### Example 3: Resource Creation

**Before (v1):**
```python
@app.post("/generate/capsule")
async def generate_capsule(request: GenerateRequest):
    capsule = await generate(request)
    return capsule
```

**After (v2):**
```python
@router.post("/capsules")
@limiter.limit("10/minute")
async def create_capsule(
    request: Request,
    response: Response,
    capsule_request: CreateCapsuleRequest,
    background_tasks: BackgroundTasks,
    user: Dict = Depends(get_current_user),
    x_request_id: Optional[str] = Header(None)
):
    # Idempotency check
    if x_request_id and await check_processed(x_request_id):
        return await get_cached_response(x_request_id)
    
    # Validate request
    validation_errors = validate_capsule_request(capsule_request, user)
    if validation_errors:
        return ApiResponse(
            success=False,
            errors=validation_errors
        )
    
    # Process
    if capsule_request.async_processing:
        job_id = str(uuid4())
        background_tasks.add_task(process_async, capsule_request, job_id)
        
        response.status_code = 202  # Accepted
        return ApiResponse(
            success=True,
            data={"job_id": job_id, "status": "queued"},
            links=[
                Link(
                    href=f"/api/v2/jobs/{job_id}",
                    rel="status",
                    method="GET"
                )
            ]
        )
    else:
        capsule = await generate_capsule_sync(capsule_request)
        
        # Set cache headers
        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["ETag"] = f'"{capsule.id}"'
        
        response.status_code = 201  # Created
        return ApiResponse(
            success=True,
            data=capsule,
            links=create_hateoas_links(capsule.id, request.base_url)
        )
```

## Step-by-Step Migration Process

### 1. Update Imports
```python
from src.api.v2.production_api import (
    ApiResponse, ErrorDetail, ErrorSeverity,
    PaginationMeta, Link, router
)
from src.common.auth import get_current_user_async as get_current_user
```

### 2. Move to Router
Replace `@app.post("/endpoint")` with `@router.post("/endpoint")`

### 3. Add Authentication
```python
user: Dict = Depends(get_current_user)
# or for optional auth:
user: Optional[Dict] = Depends(optional_auth())
```

### 4. Add Rate Limiting
```python
@limiter.limit("30/minute")  # Adjust based on endpoint
```

### 5. Standardize Response
```python
return ApiResponse(
    success=True,
    data=your_data,
    links=[...],  # Add HATEOAS links
    meta={...}    # Add metadata
)
```

### 6. Enhanced Error Handling
```python
try:
    # Your logic
except ValidationError as e:
    return ApiResponse(
        success=False,
        errors=[
            ErrorDetail(
                code="VALIDATION_ERROR",
                message=str(e),
                field=e.field,
                severity=ErrorSeverity.medium
            )
        ]
    )
except Exception as e:
    logger.error("Operation failed", error=str(e))
    return ApiResponse(
        success=False,
        errors=[
            ErrorDetail(
                code="INTERNAL_ERROR",
                message="An error occurred",
                severity=ErrorSeverity.high
            )
        ]
    )
```

### 7. Add Request Tracking
```python
await track_request(request, user)  # At start of endpoint
```

### 8. Implement Caching
```python
# For GET endpoints
response.headers["Cache-Control"] = "private, max-age=300"
response.headers["ETag"] = f'"{resource_id}"'

# Check If-None-Match
if if_none_match == etag:
    response.status_code = 304
    return None
```

## Common Patterns

### Async Processing
```python
if request.async_processing:
    job_id = str(uuid4())
    background_tasks.add_task(process_async, request, job_id)
    return ApiResponse(
        success=True,
        data={"job_id": job_id},
        links=[Link(href=f"/api/v2/jobs/{job_id}", rel="status")]
    )
```

### Pagination
```python
page: int = Query(1, ge=1)
per_page: int = Query(20, ge=1, le=100)
sort_by: str = Query("created_at")
sort_order: SortOrder = Query(SortOrder.desc)
```

### Filtering
```python
status: Optional[str] = Query(None)
created_after: Optional[datetime] = Query(None)
search: Optional[str] = Query(None)
```

### Batch Operations
```python
@router.post("/capsules/batch")
async def batch_create(
    requests: List[CreateCapsuleRequest],
    user: Dict = Depends(get_current_user)
):
    results = []
    for req in requests[:100]:  # Limit batch size
        result = await process_single(req)
        results.append(result)
    
    return ApiResponse(
        success=True,
        data=results,
        meta={"batch_size": len(results)}
    )
```

## Testing Your Migration

### 1. Unit Tests
```python
def test_endpoint_migration():
    response = client.post(
        "/api/v2/endpoint",
        headers={"Authorization": "Bearer test-token"},
        json={...}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert "data" in response.json()
    assert "links" in response.json()
```

### 2. Integration Tests
```python
async def test_with_real_auth():
    user = await get_test_user()
    token = await get_auth_token(user)
    
    response = await client.post(
        "/api/v2/endpoint",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
```

### 3. Load Tests
```python
# Test rate limiting
async def test_rate_limiting():
    for i in range(100):
        response = await client.get("/api/v2/endpoint")
        if response.status_code == 429:
            assert response.headers["Retry-After"]
            break
```

## Rollout Strategy

1. **Phase 1**: Implement v2 alongside v1
2. **Phase 2**: Update clients to use v2
3. **Phase 3**: Monitor and fix issues
4. **Phase 4**: Deprecate v1 endpoints
5. **Phase 5**: Remove v1 code

## Monitoring Migration

Track these metrics during migration:
- Request counts per version
- Error rates per version
- Response times
- Client adoption rate

```python
# Add version tracking
logger.info("api_request", version="v2", endpoint=endpoint, user_id=user["user_id"])
```

## Backward Compatibility

For gradual migration, maintain v1 endpoints with deprecation warnings:

```python
@app.post("/execute")
async def execute_v1(request: ExecutionRequest):
    logger.warning("Deprecated v1 endpoint used", endpoint="/execute")
    # Set deprecation header
    response.headers["X-API-Deprecation-Warning"] = "Use /api/v2/execute"
    response.headers["X-API-Deprecation-Date"] = "2024-12-31"
    
    # Forward to v2
    return await execute_v2(request)
```

## Getting Help

- API Documentation: `/api/v2/docs`
- Migration Support: `support@quantumlayerplatform.com`
- Status Page: `https://status.quantumlayerplatform.com`