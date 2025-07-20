#!/usr/bin/env python3
"""
OpenAPI documentation customization for production API
Provides rich documentation with examples, security schemes, and proper versioning.
"""

import os
from typing import List, Dict, Any
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

try:
    from .api_config import api_settings
except ImportError:
    # Fallback if running as standalone script
    from api_config import api_settings


def get_servers(request: Request = None) -> List[Dict[str, str]]:
    """Get server URLs based on environment configuration and request context"""
    servers = []
    
    # If we have a request object and auto-detect is enabled, try to detect current host
    if request and api_settings.AUTO_DETECT_HOST and api_settings.is_development and not api_settings.API_BASE_URL:
        scheme = request.url.scheme
        host = request.headers.get("host", request.url.netloc)
        # Remove any API path prefixes to get base URL
        base_url = f"{scheme}://{host}"
        servers.append({
            "url": base_url,
            "description": "Current server (auto-detected)"
        })
    
    if api_settings.API_BASE_URL:
        # If a custom URL is provided, use it as the primary server
        servers.append({
            "url": api_settings.API_BASE_URL,
            "description": f"Custom API URL ({api_settings.ENVIRONMENT})"
        })
    
    # Add environment-specific servers
    if api_settings.is_production:
        servers.extend([
            {
                "url": api_settings.PRODUCTION_API_URL,
                "description": "Production server"
            },
            {
                "url": api_settings.STAGING_API_URL,
                "description": "Staging server"
            }
        ])
    elif api_settings.is_staging:
        servers.extend([
            {
                "url": api_settings.STAGING_API_URL,
                "description": "Staging server"
            },
            {
                "url": api_settings.PRODUCTION_API_URL,
                "description": "Production server"
            }
        ])
    
    # Always add localhost for development/testing
    servers.append({
        "url": api_settings.LOCAL_API_URL,
        "description": "Local development server"
    })
    
    return servers


def get_allowed_origins() -> str:
    """Get allowed origins for CSP based on environment"""
    # Base allowed origins
    base_origins = [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://unpkg.com"
    ]
    
    # Add API URLs based on environment
    if api_settings.is_production:
        api_origins = [
            api_settings.PRODUCTION_API_URL,
            api_settings.STAGING_API_URL
        ]
    elif api_settings.is_staging:
        api_origins = [
            api_settings.STAGING_API_URL,
            api_settings.PRODUCTION_API_URL
        ]
    else:  # development
        api_origins = [
            "http://localhost:*",
            "http://127.0.0.1:*"
        ]
    
    # Add custom API URL if provided
    if api_settings.API_BASE_URL:
        api_origins.append(api_settings.API_BASE_URL)
    
    # Add any additional allowed origins from environment
    if api_settings.ADDITIONAL_ALLOWED_ORIGINS:
        additional_origins = api_settings.ADDITIONAL_ALLOWED_ORIGINS.split(",")
        api_origins.extend([origin.strip() for origin in additional_origins if origin.strip()])
    
    return " ".join(base_origins + api_origins)


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

- Documentation: https://docs.quantumlayerplatform.com
- Status: https://status.quantumlayerplatform.com
- Support: support@quantumlayerplatform.com
        """,
        routes=app.routes,
        tags=[
            {
                "name": "capsules-v2",
                "description": "Capsule management operations",
                "externalDocs": {
                    "description": "Capsule documentation",
                    "url": "https://docs.quantumlayerplatform.com/capsules"
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
        servers=get_servers(),
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
    async def custom_swagger_ui_html(request: Request):
        from fastapi.responses import HTMLResponse
        
        html_content = get_swagger_ui_html(
            openapi_url="/api/v2/openapi.json",
            title="QLP API v2 - Swagger UI",
            swagger_js_url=f"{api_settings.SWAGGER_CDN_URL}/swagger-ui-bundle.js",
            swagger_css_url=f"{api_settings.SWAGGER_CDN_URL}/swagger-ui.css",
            swagger_favicon_url="https://quantumlayerplatform.com/favicon.ico"
        )
        
        # Create custom response with proper CSP headers
        response = HTMLResponse(content=html_content.body.decode())
        allowed_origins = get_allowed_origins()
        response.headers["Content-Security-Policy"] = (
            f"default-src {allowed_origins}; "
            f"script-src {allowed_origins} 'unsafe-inline' 'unsafe-eval'; "
            f"style-src {allowed_origins} 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            f"font-src {allowed_origins} data:; "
            f"connect-src {allowed_origins};"
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        return response
    
    @app.get("/api/v2/redoc", include_in_schema=False)
    async def redoc_html():
        from fastapi.responses import HTMLResponse
        
        html_content = get_redoc_html(
            openapi_url="/api/v2/openapi.json",
            title="QLP API v2 - ReDoc",
            redoc_js_url=f"{api_settings.REDOC_CDN_URL}/bundles/redoc.standalone.js",
            redoc_favicon_url="https://quantumlayerplatform.com/favicon.ico"
        )
        
        # Create custom response with proper CSP headers
        response = HTMLResponse(content=html_content.body.decode())
        allowed_origins = get_allowed_origins()
        response.headers["Content-Security-Policy"] = (
            f"default-src {allowed_origins}; "
            f"script-src {allowed_origins} 'unsafe-inline' 'unsafe-eval'; "
            f"style-src {allowed_origins} 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            f"font-src {allowed_origins} data:; "
            f"connect-src {allowed_origins}; "
            "worker-src 'self' blob:;"  # ReDoc needs worker-src for blob: URLs
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        return response
    
    @app.get("/api/v2/openapi.json", include_in_schema=False)
    async def openapi_json():
        return custom_openapi(app)