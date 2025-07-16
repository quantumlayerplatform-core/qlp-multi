"""
OpenAPI customization for deprecated endpoints

Marks old endpoints as deprecated in the API documentation
"""

from typing import Dict, Any
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# List of deprecated endpoints
DEPRECATED_PATHS = [
    "/generate/capsule",
    "/generate/complete-with-github", 
    "/generate/complete-with-github-sync",
    "/generate/complete-pipeline",
    "/generate/robust-capsule",
    "/workflow/status/{workflow_id}",
    "/status/{workflow_id}",
    "/capsule/{capsule_id}",
    "/capsules/{capsule_id}/deliver"
]


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with deprecation notices"""
    
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add deprecation notices to paths
    for path, methods in openapi_schema.get("paths", {}).items():
        if any(deprecated_path in path for deprecated_path in DEPRECATED_PATHS):
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Mark as deprecated
                    operation["deprecated"] = True
                    
                    # Add deprecation notice to description
                    original_desc = operation.get("description", "")
                    deprecation_notice = (
                        "⚠️ **DEPRECATED**: This endpoint will be removed on 2025-07-01. "
                        f"Use the v2 API instead. See migration guide: "
                        "https://docs.qlp.com/api/migration\n\n"
                    )
                    
                    # Add specific alternatives
                    if "/generate/capsule" in path:
                        deprecation_notice += "**Alternative**: Use `POST /v2/execute` with `options.mode='basic'`\n\n"
                    elif "/generate/complete-with-github" in path:
                        deprecation_notice += "**Alternative**: Use `POST /v2/execute` with `options.github.enabled=true`\n\n"
                    elif "/generate/robust-capsule" in path:
                        deprecation_notice += "**Alternative**: Use `POST /v2/execute` with `options.mode='robust'`\n\n"
                    elif "/workflow/status" in path or "/status" in path:
                        deprecation_notice += "**Alternative**: Use `GET /v2/workflows/{workflow_id}`\n\n"
                    elif "/capsule" in path:
                        deprecation_notice += "**Alternative**: Use `GET /v2/workflows/{workflow_id}/result`\n\n"
                    
                    operation["description"] = deprecation_notice + original_desc
                    
                    # Add deprecation tags
                    if "tags" not in operation:
                        operation["tags"] = []
                    if "deprecated" not in operation["tags"]:
                        operation["tags"].append("deprecated")
                    
                    # Update summary
                    if "summary" in operation:
                        operation["summary"] = f"[DEPRECATED] {operation['summary']}"
    
    # Add v2 endpoints to featured section
    if "tags" not in openapi_schema:
        openapi_schema["tags"] = []
    
    # Add v2 tag at the top
    v2_tag = {
        "name": "Unified API v2",
        "description": (
            "🚀 **Recommended**: The new unified API provides a single endpoint "
            "for all code generation workflows. Use these endpoints for new integrations.\n\n"
            "**Key Benefits**:\n"
            "- Single endpoint with options-based configuration\n"
            "- Consistent response format\n"
            "- Better performance\n"
            "- Future-proof design\n\n"
            "See the [migration guide](https://docs.qlp.com/api/migration) for details."
        )
    }
    
    # Insert v2 tag at the beginning
    openapi_schema["tags"].insert(0, v2_tag)
    
    # Add deprecated tag
    deprecated_tag = {
        "name": "deprecated",
        "description": (
            "⚠️ These endpoints are deprecated and will be removed on 2025-07-01. "
            "Please migrate to the v2 API."
        )
    }
    openapi_schema["tags"].append(deprecated_tag)
    
    # Group v2 endpoints
    for path, methods in openapi_schema.get("paths", {}).items():
        if path.startswith("/v2/"):
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    if "tags" not in operation:
                        operation["tags"] = []
                    if "Unified API v2" not in operation["tags"]:
                        operation["tags"].insert(0, "Unified API v2")
    
    # Add example usage in the main description
    main_description = openapi_schema.get("info", {}).get("description", "")
    
    v2_examples = """

## 🚀 Quick Start with v2 API

### Basic Code Generation
```bash
curl -X POST https://api.qlp.com/v2/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "description": "Create a REST API for user management",
    "options": {
      "mode": "complete"
    }
  }'
```

### With GitHub Integration
```bash
curl -X POST https://api.qlp.com/v2/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "description": "Create an e-commerce platform",
    "options": {
      "mode": "robust",
      "github": {
        "enabled": true,
        "token": "your-github-token",
        "repo_name": "my-ecommerce-platform"
      }
    }
  }'
```

### Check Status
```bash
curl https://api.qlp.com/v2/workflows/{workflow_id}
```

---
"""
    
    openapi_schema["info"]["description"] = v2_examples + main_description
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def apply_openapi_customization(app: FastAPI):
    """Apply OpenAPI customization to the app"""
    app.openapi = lambda: custom_openapi(app)