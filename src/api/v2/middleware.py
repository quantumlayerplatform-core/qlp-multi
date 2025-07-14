#!/usr/bin/env python3
"""
Production middleware for API v2
Handles cross-cutting concerns like request tracking, performance monitoring,
error handling, and security headers.
"""

import time
import uuid
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import structlog

from src.api.v2.production_api import ApiResponse, ErrorDetail, ErrorSeverity

logger = structlog.get_logger()


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track requests with unique IDs and timing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Track timing
        start_time = time.time()
        
        # Add request ID to logger context
        logger.bind(request_id=request_id)
        
        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            # Log response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=duration,
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content=ApiResponse(
                    success=False,
                    request_id=request_id,
                    errors=[
                        ErrorDetail(
                            code="INTERNAL_ERROR",
                            message="An internal error occurred",
                            severity=ErrorSeverity.critical
                        )
                    ]
                ).dict()
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    # Documentation endpoints that should skip this middleware
    DOC_ENDPOINTS = ["/docs", "/redoc", "/openapi.json", "/api/v2/docs", "/api/v2/redoc", "/api/v2/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a documentation endpoint - skip middleware if so
        is_doc_endpoint = any(request.url.path == endpoint for endpoint in self.DOC_ENDPOINTS)
        
        if is_doc_endpoint:
            # Skip security headers for doc endpoints - they handle their own
            return await call_next(request)
        
        response = await call_next(request)
        
        # Add security headers for non-doc endpoints
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        if request.url.path.startswith("/api"):
            # Strict CSP for API endpoints
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        else:
            # Default CSP for other endpoints
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self';"
            )
        
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Monitor API performance and collect metrics"""
    
    def __init__(self, app, alert_threshold: float = 5.0):
        super().__init__(app)
        self.alert_threshold = alert_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Track resource usage before request
        import psutil
        process = psutil.Process()
        cpu_before = process.cpu_percent()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        response = await call_next(request)
        
        # Calculate metrics
        duration = time.time() - start_time
        cpu_after = process.cpu_percent()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # Log performance metrics
        logger.info(
            "performance_metrics",
            path=request.url.path,
            method=request.method,
            duration=duration,
            cpu_usage=cpu_after - cpu_before,
            memory_delta=memory_after - memory_before,
            status_code=response.status_code
        )
        
        # Alert on slow requests
        if duration > self.alert_threshold:
            logger.warning(
                "slow_request_detected",
                path=request.url.path,
                duration=duration,
                threshold=self.alert_threshold
            )
        
        # Add Server-Timing header
        response.headers["Server-Timing"] = f"total;dur={duration*1000:.2f}"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling with proper formatting"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except ValueError as e:
            # Handle validation errors
            return JSONResponse(
                status_code=400,
                content=ApiResponse(
                    success=False,
                    request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
                    errors=[
                        ErrorDetail(
                            code="VALIDATION_ERROR",
                            message=str(e),
                            severity=ErrorSeverity.medium
                        )
                    ]
                ).dict()
            )
            
        except PermissionError as e:
            # Handle permission errors
            return JSONResponse(
                status_code=403,
                content=ApiResponse(
                    success=False,
                    request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
                    errors=[
                        ErrorDetail(
                            code="PERMISSION_DENIED",
                            message=str(e),
                            severity=ErrorSeverity.high
                        )
                    ]
                ).dict()
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(
                "unhandled_exception",
                error=str(e),
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content=ApiResponse(
                    success=False,
                    request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
                    errors=[
                        ErrorDetail(
                            code="INTERNAL_ERROR",
                            message="An unexpected error occurred",
                            severity=ErrorSeverity.critical
                        )
                    ]
                ).dict()
            )


class CompressionMiddleware(GZipMiddleware):
    """Enhanced compression middleware with size threshold"""
    
    def __init__(self, app, minimum_size: int = 1000, compresslevel: int = 6):
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)


def setup_middleware(app):
    """Configure all middleware for the application"""
    
    # Import metrics middleware
    try:
        from src.monitoring.metrics import MetricsMiddleware
        metrics_available = True
    except ImportError:
        logger.warning("Metrics middleware not available")
        metrics_available = False
    
    # Security: Trusted host validation
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*.quantumlayer.com",
            "localhost",
            "127.0.0.1",
            "orchestrator",  # Docker service name
            "agent-factory",
            "validation-mesh",
            "vector-memory",
            "execution-sandbox",
            "*"  # Allow all in development - remove in production
        ]
    )
    
    # Performance: Compression
    app.add_middleware(
        CompressionMiddleware,
        minimum_size=1000,
        compresslevel=6
    )
    
    # Security: CORS
    import os
    is_development = os.getenv("ENVIRONMENT", "development") == "development"
    
    allowed_origins = ["*"] if is_development else [
        "https://app.quantumlayer.com",
        "https://staging.quantumlayer.com",
        "http://localhost:3000"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time", "X-Total-Count"],
        max_age=86400  # 24 hours
    )
    
    # Monitoring: Metrics collection
    if metrics_available:
        app.add_middleware(MetricsMiddleware)
    
    # Monitoring: Performance tracking
    app.add_middleware(PerformanceMonitoringMiddleware, alert_threshold=5.0)
    
    # Security: Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Error handling
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Request tracking (should be last to track everything)
    app.add_middleware(RequestTrackingMiddleware)
    
    logger.info("Middleware configured successfully")