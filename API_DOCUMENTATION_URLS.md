# QLP API Documentation URLs

## Working Documentation Endpoints

The OpenAPI documentation for each service is available at the following URLs:

### 1. Meta-Orchestrator Service (Port 8000)
- **Swagger UI**: http://localhost:8000/api/v2/docs
- **ReDoc**: http://localhost:8000/api/v2/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v2/openapi.json

Note: The orchestrator uses custom documentation URLs under `/api/v2/` instead of the default `/docs` endpoint.

### 2. Agent Factory Service (Port 8001)
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

### 3. Validation Mesh Service (Port 8002)
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **OpenAPI JSON**: http://localhost:8002/openapi.json

### 4. Vector Memory Service (Port 8003)
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json

### 5. Execution Sandbox Service (Port 8004)
- **Swagger UI**: http://localhost:8004/docs
- **ReDoc**: http://localhost:8004/redoc
- **OpenAPI JSON**: http://localhost:8004/openapi.json

## Why the Orchestrator Uses Different URLs

The orchestrator service has custom documentation endpoints because:
1. It implements a production-grade API v2 with enhanced documentation
2. The custom documentation includes:
   - Rich API descriptions with examples
   - Authentication schemes (Bearer token, API key)
   - Rate limiting information
   - Pagination details
   - Webhook support documentation
   - Custom security headers

## Accessing Documentation via Nginx

When accessing through nginx (port 80), note that:
- `/docs` redirects to the orchestrator, but won't work because the orchestrator disabled the default `/docs`
- To fix this, nginx configuration should be updated to proxy to `/api/v2/docs` instead

## Quick Test Commands

```bash
# Test all documentation endpoints
curl -I http://localhost:8000/api/v2/docs      # Orchestrator
curl -I http://localhost:8001/docs             # Agent Factory
curl -I http://localhost:8002/docs             # Validation Mesh
curl -I http://localhost:8003/docs             # Vector Memory
curl -I http://localhost:8004/docs             # Execution Sandbox
```

## Environment Variables

The documentation endpoints are always enabled in development. There are no environment variables that disable the documentation in the current configuration.