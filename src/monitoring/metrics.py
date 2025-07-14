#!/usr/bin/env python3
"""
Production metrics and monitoring for QLP
Integrates with Prometheus, OpenTelemetry, and custom dashboards
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from functools import wraps
import time
import asyncio
from contextlib import asynccontextmanager

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import structlog

from src.common.config import settings

logger = structlog.get_logger()

# ===========================================
# PROMETHEUS METRICS
# ===========================================

# Request metrics
http_requests_total = Counter(
    'qlp_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'qlp_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Capsule metrics
capsules_created = Counter(
    'qlp_capsules_created_total',
    'Total number of capsules created',
    ['tenant_id', 'status']
)

capsule_generation_duration = Histogram(
    'qlp_capsule_generation_duration_seconds',
    'Capsule generation duration in seconds',
    ['tenant_id', 'complexity']
)

capsule_validation_score = Histogram(
    'qlp_capsule_validation_score',
    'Capsule validation scores',
    ['tenant_id'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)
)

# LLM metrics
llm_requests = Counter(
    'qlp_llm_requests_total',
    'Total number of LLM API calls',
    ['provider', 'model', 'tier']
)

llm_tokens_used = Counter(
    'qlp_llm_tokens_used_total',
    'Total number of tokens used',
    ['provider', 'model', 'type']  # type: prompt/completion
)

llm_request_duration = Histogram(
    'qlp_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider', 'model']
)

llm_errors = Counter(
    'qlp_llm_errors_total',
    'Total number of LLM errors',
    ['provider', 'model', 'error_type']
)

# System metrics
active_workflows = Gauge(
    'qlp_active_workflows',
    'Number of active Temporal workflows'
)

task_queue_size = Gauge(
    'qlp_task_queue_size',
    'Size of task queue',
    ['queue_name']
)

cache_hits = Counter(
    'qlp_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'qlp_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# Business metrics
revenue_processed = Counter(
    'qlp_revenue_processed_total',
    'Total revenue processed in cents',
    ['tenant_id', 'plan_type']
)

api_credits_consumed = Counter(
    'qlp_api_credits_consumed_total',
    'Total API credits consumed',
    ['tenant_id', 'operation']
)

# Service info
service_info = Info(
    'qlp_service_info',
    'Service version and deployment information'
)

# ===========================================
# OPENTELEMETRY SETUP
# ===========================================

def setup_opentelemetry():
    """Configure OpenTelemetry tracing and metrics"""
    
    if not settings.OTEL_TRACES_ENABLED:
        return
    
    # Setup tracing
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()
    
    # Configure OTLP exporter for traces
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True
    )
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Setup metrics
    if settings.OTEL_METRICS_ENABLED:
        metric_reader = PeriodicExportingMetricReader(
            exporter=OTLPMetricExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True
            ),
            export_interval_millis=10000  # 10 seconds
        )
        
        metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
    
    # Auto-instrument libraries
    FastAPIInstrumentor.instrument(tracer_provider=tracer_provider)
    HTTPXClientInstrumentor.instrument(tracer_provider=tracer_provider)
    SQLAlchemyInstrumentor.instrument()
    
    logger.info("OpenTelemetry configured successfully")


# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create OTEL metrics
otel_request_counter = meter.create_counter(
    name="http_server_requests",
    description="Number of HTTP requests",
    unit="1"
)

otel_request_duration = meter.create_histogram(
    name="http_server_duration",
    description="HTTP request duration",
    unit="ms"
)

# ===========================================
# DECORATORS & UTILITIES
# ===========================================

def track_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Track HTTP request metrics"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    # OpenTelemetry metrics
    otel_request_counter.add(
        1,
        {"method": method, "endpoint": endpoint, "status": str(status_code)}
    )
    otel_request_duration.record(
        duration * 1000,  # Convert to milliseconds
        {"method": method, "endpoint": endpoint}
    )


def track_llm_metrics(
    provider: str,
    model: str,
    tier: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration: float,
    error: Optional[str] = None
):
    """Track LLM usage metrics"""
    if error:
        llm_errors.labels(provider=provider, model=model, error_type=error).inc()
    else:
        llm_requests.labels(provider=provider, model=model, tier=tier).inc()
        llm_tokens_used.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
        llm_tokens_used.labels(provider=provider, model=model, type="completion").inc(completion_tokens)
        llm_request_duration.labels(provider=provider, model=model).observe(duration)


def track_capsule_metrics(
    tenant_id: str,
    status: str,
    duration: float,
    validation_score: Optional[float] = None,
    complexity: str = "medium"
):
    """Track capsule generation metrics"""
    capsules_created.labels(tenant_id=tenant_id, status=status).inc()
    
    if status == "completed":
        capsule_generation_duration.labels(
            tenant_id=tenant_id,
            complexity=complexity
        ).observe(duration)
        
        if validation_score is not None:
            capsule_validation_score.labels(tenant_id=tenant_id).observe(validation_score)


def track_cache_access(cache_type: str, hit: bool):
    """Track cache hit/miss"""
    if hit:
        cache_hits.labels(cache_type=cache_type).inc()
    else:
        cache_misses.labels(cache_type=cache_type).inc()


def track_business_metrics(
    tenant_id: str,
    operation: str,
    credits: int,
    revenue_cents: Optional[int] = None,
    plan_type: Optional[str] = None
):
    """Track business metrics"""
    api_credits_consumed.labels(tenant_id=tenant_id, operation=operation).inc(credits)
    
    if revenue_cents and plan_type:
        revenue_processed.labels(tenant_id=tenant_id, plan_type=plan_type).inc(revenue_cents)


# ===========================================
# ASYNC CONTEXT MANAGERS
# ===========================================

@asynccontextmanager
async def track_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Track any operation with timing and tracing"""
    start_time = time.time()
    
    # Start OpenTelemetry span
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.set_status(
                trace.Status(trace.StatusCode.ERROR, str(e))
            )
            span.record_exception(e)
            raise
        finally:
            duration = time.time() - start_time
            span.set_attribute("duration_seconds", duration)


# ===========================================
# METRIC EXPORTERS
# ===========================================

async def export_metrics() -> str:
    """Export Prometheus metrics"""
    # Update dynamic gauges
    # In production, these would query actual values
    active_workflows.set(42)  # Mock value
    task_queue_size.labels(queue_name="main").set(15)
    task_queue_size.labels(queue_name="priority").set(3)
    
    # Update service info
    service_info.info({
        'version': settings.API_VERSION,
        'environment': settings.ENVIRONMENT,
        'commit_sha': os.getenv('GIT_COMMIT_SHA', 'unknown'),
        'deployment_time': datetime.now(timezone.utc).isoformat()
    })
    
    return generate_latest()


class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_uptime(self) -> float:
        """Get service uptime in seconds"""
        return time.time() - self.start_time
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics"""
        return {
            "uptime_seconds": self.get_uptime(),
            "active_connections": 0,  # Would query actual connections
            "memory_usage_mb": self._get_memory_usage(),
            "cpu_usage_percent": self._get_cpu_usage(),
            "error_rate": self._calculate_error_rate(),
            "avg_response_time_ms": self._calculate_avg_response_time()
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        import psutil
        return psutil.cpu_percent(interval=0.1)
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate from Prometheus metrics"""
        # In production, query Prometheus or calculate from counters
        return 0.02  # Mock 2% error rate
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time"""
        # In production, calculate from histogram
        return 145.6  # Mock 145.6ms


# Global metrics collector
metrics_collector = MetricsCollector()

# ===========================================
# MIDDLEWARE INTEGRATION
# ===========================================

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import os


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Extract path template (not the actual path with IDs)
        path_template = request.url.path
        for route in request.app.routes:
            match, _ = route.path_regex.match(path_template)
            if match:
                path_template = route.path
                break
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Track metrics
            track_request_metrics(
                method=request.method,
                endpoint=path_template,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Track error metrics
            track_request_metrics(
                method=request.method,
                endpoint=path_template,
                status_code=500,
                duration=duration
            )
            
            raise


# Initialize OpenTelemetry on module load
setup_opentelemetry()