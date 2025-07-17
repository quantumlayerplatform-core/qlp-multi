#!/usr/bin/env python3
"""
FastAPI middleware for structured logging
Automatically logs all requests with context and performance metrics
"""

import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from src.common.structured_logging import (
    request_id_var, user_id_var, tenant_id_var,
    log_api_request, LogContext
)

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request logging
    """
    
    def __init__(self, app: ASGIApp, service_name: str = "unknown"):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID if not provided
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        
        # Extract user and tenant from headers or auth
        user_id = request.headers.get("X-User-ID")
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if user_id:
            user_id_var.set(user_id)
        if tenant_id:
            tenant_id_var.set(tenant_id)
        
        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            http_method=request.method,
            http_path=str(request.url.path),
            http_query=str(request.url.query) if request.url.query else None,
            http_headers_count=len(request.headers),
            service=self.service_name
        )
        
        # Process request
        response = None
        error = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            logger.error(
                "Request processing error",
                error=e,
                http_method=request.method,
                http_path=str(request.url.path)
            )
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            if response:
                log_api_request(
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration=duration,
                    service=self.service_name,
                    response_headers_count=len(response.headers)
                )
                
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id
            
            # Clear context variables
            request_id_var.set(None)
            user_id_var.set(None)
            tenant_id_var.set(None)
        
        return response


class LoggingRoute(APIRoute):
    """
    Custom route class that logs endpoint execution
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def logging_route_handler(request: Request) -> Response:
            # Extract context from request state if available
            context = {}
            if hasattr(request.state, "request_id"):
                context["request_id"] = request.state.request_id
            if hasattr(request.state, "user_id"):
                context["user_id"] = request.state.user_id
            if hasattr(request.state, "tenant_id"):
                context["tenant_id"] = request.state.tenant_id
            
            # Log with context
            with LogContext(**context) as log:
                log.info(
                    "Endpoint called",
                    endpoint=self.endpoint.__name__,
                    path=self.path,
                    methods=list(self.methods)
                )
                
                try:
                    response = await original_route_handler(request)
                    log.info(
                        "Endpoint completed",
                        endpoint=self.endpoint.__name__,
                        status="success"
                    )
                    return response
                except Exception as e:
                    log.error(
                        "Endpoint failed",
                        endpoint=self.endpoint.__name__,
                        error=e
                    )
                    raise
        
        return logging_route_handler


def setup_request_logging(app, service_name: str):
    """
    Setup request logging for a FastAPI app
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
    """
    # Add logging middleware
    app.add_middleware(LoggingMiddleware, service_name=service_name)
    
    # Log application startup
    @app.on_event("startup")
    async def log_startup():
        logger.info(
            "Service started",
            service=service_name,
            version=getattr(app, "version", "unknown")
        )
    
    # Log application shutdown
    @app.on_event("shutdown")
    async def log_shutdown():
        logger.info(
            "Service shutting down",
            service=service_name
        )
    
    # Add health check endpoint with logging
    @app.get("/health")
    async def health_check():
        logger.debug("Health check requested")
        return {
            "status": "healthy",
            "service": service_name,
            "timestamp": time.time()
        }
