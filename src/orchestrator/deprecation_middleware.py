"""
Deprecation middleware for API v1 endpoints

Adds deprecation warnings and headers to old endpoints
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import warnings
import json
from datetime import datetime

# Map of deprecated endpoints to their alternatives
DEPRECATED_ENDPOINTS = {
    "/generate/capsule": {
        "alternative": "/v2/execute with options.mode='basic'",
        "sunset_date": "2025-07-01"
    },
    "/generate/complete-with-github": {
        "alternative": "/v2/execute with options.github.enabled=true",
        "sunset_date": "2025-07-01"
    },
    "/generate/complete-with-github-sync": {
        "alternative": "/v2/execute with options.github.enabled=true",
        "sunset_date": "2025-07-01"
    },
    "/generate/complete-pipeline": {
        "alternative": "/v2/execute with options.mode='complete'",
        "sunset_date": "2025-07-01"
    },
    "/generate/robust-capsule": {
        "alternative": "/v2/execute with options.mode='robust'",
        "sunset_date": "2025-07-01"
    },
    "/workflow/status": {
        "alternative": "/v2/workflows/{workflow_id}",
        "sunset_date": "2025-07-01"
    },
    "/status": {
        "alternative": "/v2/workflows/{workflow_id}",
        "sunset_date": "2025-07-01"
    }
}


async def deprecation_middleware(request: Request, call_next: Callable) -> Response:
    """Add deprecation warnings to old endpoints"""
    
    # Check if this is a deprecated endpoint
    path = request.url.path
    
    # Remove path parameters for matching
    base_path = path
    for pattern in ["/{workflow_id}", "/{capsule_id}", "/{request_id}"]:
        if pattern in path:
            base_path = path.split(pattern)[0]
    
    if base_path in DEPRECATED_ENDPOINTS:
        # Log deprecation warning
        warnings.warn(
            f"Endpoint {base_path} is deprecated. "
            f"Use {DEPRECATED_ENDPOINTS[base_path]['alternative']} instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Process request
        response = await call_next(request)
        
        # Add deprecation headers
        sunset_date = DEPRECATED_ENDPOINTS[base_path]['sunset_date']
        response.headers["X-Deprecated"] = "true"
        response.headers["X-Alternative"] = DEPRECATED_ENDPOINTS[base_path]['alternative']
        response.headers["X-Sunset-Date"] = sunset_date
        response.headers["Warning"] = f'299 - "Deprecated endpoint. Will be removed on {sunset_date}"'
        
        # If JSON response, add deprecation notice
        if response.headers.get("content-type", "").startswith("application/json"):
            # This is a bit hacky but works for adding deprecation notices
            original_body = b""
            async for chunk in response.body_iterator:
                original_body += chunk
            
            try:
                data = json.loads(original_body)
                if isinstance(data, dict):
                    data["_deprecation_notice"] = {
                        "message": f"This endpoint is deprecated and will be removed on {sunset_date}",
                        "alternative": DEPRECATED_ENDPOINTS[base_path]['alternative'],
                        "docs": "https://docs.qlp.com/api/migration"
                    }
                    
                    return JSONResponse(
                        content=data,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
            except:
                # If we can't parse/modify, return original
                pass
        
        return response
    
    # Not deprecated, process normally
    return await call_next(request)


def add_endpoint_deprecation(endpoint: str, alternative: str, sunset_date: str = "2025-07-01"):
    """Add a new endpoint to deprecation list"""
    DEPRECATED_ENDPOINTS[endpoint] = {
        "alternative": alternative,
        "sunset_date": sunset_date
    }


def create_deprecation_decorator(alternative: str, sunset_date: str = "2025-07-01"):
    """Create a decorator for deprecated endpoints"""
    
    def deprecation_decorator(func):
        async def wrapper(*args, **kwargs):
            # Issue warning
            warnings.warn(
                f"This endpoint is deprecated. Use {alternative} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            
            # Call original function
            result = await func(*args, **kwargs)
            
            # Add deprecation info to response if dict
            if isinstance(result, dict):
                result["_deprecation_notice"] = {
                    "message": f"This endpoint is deprecated and will be removed on {sunset_date}",
                    "alternative": alternative,
                    "docs": "https://docs.qlp.com/api/migration"
                }
            
            return result
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = f"DEPRECATED: {func.__doc__ or ''}\n\nUse {alternative} instead."
        
        return wrapper
    
    return deprecation_decorator