#!/usr/bin/env python3
"""
OpenAPI documentation customization for production API
Provides rich documentation with examples, security schemes, and proper versioning.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html


def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with enhanced documentation"""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Quantum Layer Platform API",
        version="2.0.0",
        description="""
# Quantum Layer Platform API v2

Enterprise-grade API for AI-powered software development automation.

## Features

- 🚀 **Automated Code Generation** - Generate complete applications from natural language
- 🧪 **Intelligent Testing** - Automatic test creation with high coverage
- 📦 **Capsule Management** - Portable, validated code packages
- 🔐 **Enterprise Security** - OAuth2, API keys, and role-based access
- 📊 **Real-time Analytics** - Performance metrics and usage tracking
- 🌐 **Multi-tenant** - Full isolation between organizations

## Authentication

The API supports multiple authentication methods:

1. **Bearer Token** (Recommended)
   ```
   Authorization: Bearer <your-token>
   ```

2. **API Key**
   ```
   X-API-Key: <your-api-key>
   ```

## Rate Limiting

- Default: 60 requests per minute per user
- Capsule creation: 10 requests per minute
- Export operations: 30 requests per minute

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Versioning

API version is included in the URL path: `/api/v2/`

Previous versions:
- v1: Deprecated (sunset date: 2024-12-31)

## Error Handling

All errors follow a consistent format:

```json
{
  "success": false,
  "errors": [
    {
      "code": "ERROR_CODE",
      "message": "Human readable message",
      "field": "field_name",
      "severity": "high"
    }
  ],
  "request_id": "uuid"
}
```

## Pagination

List endpoints support pagination:

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

Response includes pagination metadata:

```json
{
  "meta": {
    "pagination": {
      "total": 100,
      "page": 1,
      "per_page": 20,
      "pages": 5
    }
  }
}
```

## Webhooks

For async operations, provide a webhook URL:

```json
{
  "async_processing": true,
  "webhook_url": "https://your-domain.com/webhook"
}
```

## Support

- Documentation: https://docs.quantumlayer.com
- Status: https://status.quantumlayer.com
- Support: support@quantumlayer.com
        """,
        routes=app.routes,
        tags=[
            {
                "name": "capsules-v2",
                "description": "Capsule management operations",
                "externalDocs": {
                    "description": "Capsule documentation",
                    "url": "https://docs.quantumlayer.com/capsules"
                }
            },
            {
                "name": "health",
                "description": "Health and monitoring endpoints"
            },
            {
                "name": "auth",
                "description": "Authentication operations"
            }
        ],
        servers=[
            {
                "url": "https://api.quantumlayer.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.quantumlayer.com",
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ],
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token from Clerk authentication"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # Add examples
    openapi_schema["components"]["examples"] = {
        "CreateCapsuleExample": {
            "summary": "E-commerce API",
            "value": {
                "project_name": "E-commerce API",
                "description": "Build a RESTful API for an e-commerce platform with user management, product catalog, shopping cart, and order processing. Include authentication, payment integration, and admin dashboard.",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Stripe"],
                "requirements": "The API should handle high traffic, support multiple payment gateways, include inventory management, and provide real-time order tracking.",
                "constraints": {
                    "max_response_time": 200,
                    "min_test_coverage": 85,
                    "security_level": "high"
                }
            }
        },
        "CapsuleResponseExample": {
            "summary": "Successful capsule",
            "value": {
                "success": True,
                "data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "project_name": "E-commerce API",
                    "status": "completed",
                    "validation_score": 0.92,
                    "metrics": {
                        "files_generated": 47,
                        "test_coverage": 88.5,
                        "execution_time": 156.3
                    }
                }
            }
        }
    }
    
    # Add response examples to paths
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                # Add common responses
                if "responses" not in operation:
                    operation["responses"] = {}
                
                operation["responses"]["401"] = {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ApiResponse"},
                            "example": {
                                "success": False,
                                "errors": [{
                                    "code": "UNAUTHORIZED",
                                    "message": "Invalid or missing authentication token"
                                }]
                            }
                        }
                    }
                }
                
                operation["responses"]["429"] = {
                    "description": "Too Many Requests",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ApiResponse"},
                            "example": {
                                "success": False,
                                "errors": [{
                                    "code": "RATE_LIMIT_EXCEEDED",
                                    "message": "Rate limit exceeded. Please retry after 60 seconds"
                                }],
                                "meta": {"retry_after": 60}
                            }
                        }
                    }
                }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_documentation(app: FastAPI):
    """Setup custom documentation endpoints"""
    
    @app.get("/api/v2/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        from fastapi.responses import HTMLResponse
        
        html_content = get_swagger_ui_html(
            openapi_url="/api/v2/openapi.json",
            title="QLP API v2 - Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
            swagger_favicon_url="https://quantumlayer.com/favicon.ico"
        )
        
        # Create custom response with proper CSP headers
        response = HTMLResponse(content=html_content.body.decode())
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://unpkg.com; "
            "connect-src 'self' http://localhost:* https://api.quantumlayer.com;"
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        return response
    
    @app.get("/api/v2/redoc", include_in_schema=False)
    async def redoc_html():
        from fastapi.responses import HTMLResponse
        
        html_content = get_redoc_html(
            openapi_url="/api/v2/openapi.json",
            title="QLP API v2 - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://quantumlayer.com/favicon.ico"
        )
        
        # Create custom response with proper CSP headers
        response = HTMLResponse(content=html_content.body.decode())
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://unpkg.com; "
            "connect-src 'self' http://localhost:* https://api.quantumlayer.com; "
            "worker-src 'self' blob:;"  # ReDoc needs worker-src for blob: URLs
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        return response
    
    @app.get("/api/v2/openapi.json", include_in_schema=False)
    async def openapi_json():
        return custom_openapi(app)