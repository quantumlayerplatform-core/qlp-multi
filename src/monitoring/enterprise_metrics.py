"""
Enterprise-grade monitoring and observability for QLP
Supports Prometheus, Grafana, Jaeger, and custom dashboards
"""
import time
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
import json
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from opentelemetry import trace, metrics as otel_metrics
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode
import httpx

logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
resource = Resource.create({"service.name": "quantum-layer-platform"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Prometheus metrics registry
registry = CollectorRegistry()

# Workflow metrics
workflow_started = Counter('qlp_workflow_started_total', 'Total workflows started', 
                          ['tenant_id', 'workflow_type'], registry=registry)
workflow_completed = Counter('qlp_workflow_completed_total', 'Total workflows completed', 
                            ['tenant_id', 'workflow_type', 'status'], registry=registry)
workflow_duration = Histogram('qlp_workflow_duration_seconds', 'Workflow execution duration',
                             ['tenant_id', 'workflow_type'], registry=registry)
active_workflows = Gauge('qlp_active_workflows', 'Currently active workflows',
                        ['tenant_id'], registry=registry)

# Task metrics
task_started = Counter('qlp_task_started_total', 'Total tasks started',
                      ['task_type', 'complexity', 'tier'], registry=registry)
task_completed = Counter('qlp_task_completed_total', 'Total tasks completed',
                        ['task_type', 'complexity', 'tier', 'status'], registry=registry)
task_duration = Histogram('qlp_task_duration_seconds', 'Task execution duration',
                         ['task_type', 'complexity', 'tier'], buckets=[1, 5, 10, 30, 60, 120, 300], 
                         registry=registry)
task_retries = Counter('qlp_task_retries_total', 'Total task retries',
                      ['task_type', 'reason'], registry=registry)

# Agent metrics
agent_requests = Counter('qlp_agent_requests_total', 'Total agent requests',
                        ['tier', 'provider', 'model'], registry=registry)
agent_tokens = Counter('qlp_agent_tokens_total', 'Total tokens used',
                      ['tier', 'provider', 'model', 'token_type'], registry=registry)
agent_latency = Histogram('qlp_agent_latency_seconds', 'Agent response latency',
                         ['tier', 'provider', 'model'], buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
                         registry=registry)
agent_errors = Counter('qlp_agent_errors_total', 'Total agent errors',
                      ['tier', 'provider', 'error_type'], registry=registry)

# Service metrics
service_requests = Counter('qlp_service_requests_total', 'Total service requests',
                          ['service', 'endpoint', 'method'], registry=registry)
service_latency = Histogram('qlp_service_latency_seconds', 'Service response latency',
                           ['service', 'endpoint'], buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
                           registry=registry)
service_errors = Counter('qlp_service_errors_total', 'Total service errors',
                        ['service', 'endpoint', 'error_code'], registry=registry)

# Resource metrics
cpu_usage = Gauge('qlp_cpu_usage_percent', 'CPU usage percentage', registry=registry)
memory_usage = Gauge('qlp_memory_usage_percent', 'Memory usage percentage', registry=registry)
disk_usage = Gauge('qlp_disk_usage_percent', 'Disk usage percentage', registry=registry)
active_connections = Gauge('qlp_active_connections', 'Active network connections', registry=registry)

# Capsule metrics
capsules_created = Counter('qlp_capsules_created_total', 'Total capsules created',
                          ['language', 'project_type'], registry=registry)
capsule_size = Histogram('qlp_capsule_size_bytes', 'Capsule size in bytes',
                        ['language', 'project_type'], buckets=[1e3, 1e4, 1e5, 1e6, 1e7],
                        registry=registry)
github_pushes = Counter('qlp_github_pushes_total', 'Total GitHub pushes',
                       ['status', 'repo_type'], registry=registry)

# System info
system_info = Info('qlp_system', 'System information', registry=registry)
system_info.info({
    'version': '1.0.0',
    'python_version': '3.11',
    'platform': 'cloud-native'
})

@dataclass
class MetricEvent:
    """Represents a metric event"""
    timestamp: datetime
    metric_type: str
    metric_name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_connections: int
    active_workflows: int
    active_tasks: int
    success_rate: float
    average_latency: float
    error_rate: float

class MetricsCollector:
    """Collects and aggregates metrics"""
    def __init__(self, export_interval: int = 60):
        self.export_interval = export_interval
        self.events = deque(maxlen=10000)  # Keep last 10k events
        self.performance_history = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.error_counts = defaultdict(int)
        self.latency_buckets = defaultdict(list)
        self._running = False
        self._export_task = None
        
    async def start(self):
        """Start metrics collection"""
        self._running = True
        self._export_task = asyncio.create_task(self._export_loop())
        logger.info("Metrics collector started")
        
    async def stop(self):
        """Stop metrics collection"""
        self._running = False
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")
    
    async def _export_loop(self):
        """Export metrics periodically"""
        while self._running:
            try:
                await self._collect_system_metrics()
                await self._export_metrics()
                await asyncio.sleep(self.export_interval)
            except Exception as e:
                logger.error(f"Error in metrics export: {str(e)}")
                await asyncio.sleep(10)
    
    async def _collect_system_metrics(self):
        """Collect system resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        connections = len(psutil.net_connections())
        
        # Update Prometheus gauges
        cpu_usage.set(cpu_percent)
        memory_usage.set(memory.percent)
        disk_usage.set(disk.percent)
        active_connections.set(connections)
        
        # Create performance snapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            network_connections=connections,
            active_workflows=active_workflows._value.get(('all',), 0),
            active_tasks=len([e for e in self.events if e.metric_type == 'task' and 
                            e.metric_name == 'started' and 
                            (datetime.utcnow() - e.timestamp).seconds < 300]),
            success_rate=self._calculate_success_rate(),
            average_latency=self._calculate_average_latency(),
            error_rate=self._calculate_error_rate()
        )
        
        self.performance_history.append(snapshot)
    
    def _calculate_success_rate(self) -> float:
        """Calculate recent success rate"""
        recent_events = [e for e in self.events if 
                        (datetime.utcnow() - e.timestamp).seconds < 300]
        
        completed = sum(1 for e in recent_events if 
                       e.metric_name == 'completed' and 
                       e.labels.get('status') == 'success')
        total = sum(1 for e in recent_events if e.metric_name == 'completed')
        
        return completed / max(total, 1)
    
    def _calculate_average_latency(self) -> float:
        """Calculate average latency"""
        if not self.latency_buckets:
            return 0
        
        all_latencies = []
        for latencies in self.latency_buckets.values():
            all_latencies.extend(latencies[-100:])  # Last 100 per service
        
        return sum(all_latencies) / max(len(all_latencies), 1)
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        recent_events = [e for e in self.events if 
                        (datetime.utcnow() - e.timestamp).seconds < 300]
        
        errors = sum(1 for e in recent_events if 'error' in e.metric_name)
        total = sum(1 for e in recent_events if e.metric_type in ['task', 'service'])
        
        return errors / max(total, 1)
    
    async def _export_metrics(self):
        """Export metrics to configured backends"""
        # Log summary
        if self.performance_history:
            latest = self.performance_history[-1]
            logger.info(f"Performance: CPU={latest.cpu_percent:.1f}%, "
                       f"Memory={latest.memory_percent:.1f}%, "
                       f"Success Rate={latest.success_rate:.2%}, "
                       f"Error Rate={latest.error_rate:.2%}")
    
    def record_event(self, event: MetricEvent):
        """Record a metric event"""
        self.events.append(event)
        
        # Update error counts
        if 'error' in event.metric_name:
            error_key = f"{event.metric_type}:{event.labels.get('error_type', 'unknown')}"
            self.error_counts[error_key] += 1
        
        # Update latency buckets
        if 'latency' in event.metric_name:
            service_key = event.labels.get('service', 'unknown')
            self.latency_buckets[service_key].append(event.value)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        if not self.performance_history:
            return {}
        
        latest = self.performance_history[-1]
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        return {
            "current_performance": asdict(latest),
            "performance_trend": [asdict(p) for p in self.performance_history 
                                if p.timestamp > hour_ago],
            "error_summary": dict(self.error_counts),
            "top_errors": sorted(self.error_counts.items(), 
                               key=lambda x: x[1], reverse=True)[:10],
            "service_latencies": {k: sum(v[-100:]) / len(v[-100:]) 
                                for k, v in self.latency_buckets.items() if v},
            "active_services": self._get_active_services(),
            "prometheus_metrics": generate_latest(registry).decode('utf-8')
        }
    
    def _get_active_services(self) -> List[Dict[str, Any]]:
        """Get list of active services with health status"""
        services = ['orchestrator', 'agent-factory', 'validation-mesh', 
                   'vector-memory', 'sandbox']
        
        active = []
        for service in services:
            recent_events = [e for e in self.events if 
                           e.labels.get('service') == service and
                           (datetime.utcnow() - e.timestamp).seconds < 60]
            
            if recent_events:
                errors = sum(1 for e in recent_events if 'error' in e.metric_name)
                total = len(recent_events)
                
                active.append({
                    'name': service,
                    'status': 'healthy' if errors / max(total, 1) < 0.1 else 'degraded',
                    'request_count': total,
                    'error_rate': errors / max(total, 1),
                    'last_seen': max(e.timestamp for e in recent_events)
                })
        
        return active

# Global metrics collector
metrics_collector = MetricsCollector()

class MetricsContext:
    """Context manager for recording metrics"""
    def __init__(self, metric_type: str, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.metric_type = metric_type
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None
        self.span = None
        
    def __enter__(self):
        self.start_time = time.time()
        
        # Start OpenTelemetry span
        self.span = tracer.start_span(f"{self.metric_type}.{self.metric_name}")
        for key, value in self.labels.items():
            self.span.set_attribute(key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # Complete span
        if self.span:
            if exc_type:
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self.span.record_exception(exc_val)
            else:
                self.span.set_status(Status(StatusCode.OK))
            self.span.end()
        
        # Record metrics
        event = MetricEvent(
            timestamp=datetime.utcnow(),
            metric_type=self.metric_type,
            metric_name=self.metric_name + ('_error' if exc_type else '_completed'),
            value=duration,
            labels=self.labels,
            metadata={'error': str(exc_val) if exc_val else None}
        )
        metrics_collector.record_event(event)
        
        # Update Prometheus metrics
        if self.metric_type == 'workflow':
            if exc_type:
                workflow_completed.labels(
                    tenant_id=self.labels.get('tenant_id', 'unknown'),
                    workflow_type=self.labels.get('workflow_type', 'unknown'),
                    status='failed'
                ).inc()
            else:
                workflow_completed.labels(
                    tenant_id=self.labels.get('tenant_id', 'unknown'),
                    workflow_type=self.labels.get('workflow_type', 'unknown'),
                    status='success'
                ).inc()
                workflow_duration.labels(
                    tenant_id=self.labels.get('tenant_id', 'unknown'),
                    workflow_type=self.labels.get('workflow_type', 'unknown')
                ).observe(duration)
        
        elif self.metric_type == 'task':
            if not exc_type:
                task_duration.labels(
                    task_type=self.labels.get('task_type', 'unknown'),
                    complexity=self.labels.get('complexity', 'unknown'),
                    tier=self.labels.get('tier', 'unknown')
                ).observe(duration)

# Decorators for easy metric recording
def track_workflow(workflow_type: str, tenant_id: str = 'default'):
    """Decorator to track workflow execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            labels = {'workflow_type': workflow_type, 'tenant_id': tenant_id}
            
            workflow_started.labels(tenant_id=tenant_id, workflow_type=workflow_type).inc()
            active_workflows.labels(tenant_id=tenant_id).inc()
            
            try:
                with MetricsContext('workflow', 'execution', labels):
                    result = await func(*args, **kwargs)
                    return result
            finally:
                active_workflows.labels(tenant_id=tenant_id).dec()
        
        return wrapper
    return decorator

def track_task(task_type: str, complexity: str = 'medium', tier: str = 'T1'):
    """Decorator to track task execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            labels = {
                'task_type': task_type,
                'complexity': complexity,
                'tier': tier
            }
            
            task_started.labels(
                task_type=task_type,
                complexity=complexity,
                tier=tier
            ).inc()
            
            with MetricsContext('task', 'execution', labels):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def track_service_call(service: str, endpoint: str, method: str = 'POST'):
    """Decorator to track service calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            labels = {
                'service': service,
                'endpoint': endpoint,
                'method': method
            }
            
            service_requests.labels(
                service=service,
                endpoint=endpoint,
                method=method
            ).inc()
            
            start_time = time.time()
            
            try:
                with MetricsContext('service', 'call', labels):
                    result = await func(*args, **kwargs)
                    
                    service_latency.labels(
                        service=service,
                        endpoint=endpoint
                    ).observe(time.time() - start_time)
                    
                    return result
            except Exception as e:
                service_errors.labels(
                    service=service,
                    endpoint=endpoint,
                    error_code=type(e).__name__
                ).inc()
                raise
        
        return wrapper
    return decorator

def track_agent_call(tier: str, provider: str, model: str):
    """Decorator to track agent/LLM calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            labels = {
                'tier': tier,
                'provider': provider,
                'model': model
            }
            
            agent_requests.labels(
                tier=tier,
                provider=provider,
                model=model
            ).inc()
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                agent_latency.labels(
                    tier=tier,
                    provider=provider,
                    model=model
                ).observe(time.time() - start_time)
                
                # Track token usage if available
                if isinstance(result, dict):
                    if 'prompt_tokens' in result:
                        agent_tokens.labels(
                            tier=tier,
                            provider=provider,
                            model=model,
                            token_type='prompt'
                        ).inc(result['prompt_tokens'])
                    
                    if 'completion_tokens' in result:
                        agent_tokens.labels(
                            tier=tier,
                            provider=provider,
                            model=model,
                            token_type='completion'
                        ).inc(result['completion_tokens'])
                
                return result
            except Exception as e:
                agent_errors.labels(
                    tier=tier,
                    provider=provider,
                    error_type=type(e).__name__
                ).inc()
                raise
        
        return wrapper
    return decorator

# Health check endpoint data
async def get_health_metrics() -> Dict[str, Any]:
    """Get health metrics for monitoring endpoints"""
    dashboard_data = metrics_collector.get_dashboard_data()
    current_perf = dashboard_data.get('current_performance', {})
    
    return {
        'status': 'healthy' if current_perf.get('error_rate', 0) < 0.1 else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'metrics': {
            'cpu_usage': current_perf.get('cpu_percent', 0),
            'memory_usage': current_perf.get('memory_percent', 0),
            'active_workflows': current_perf.get('active_workflows', 0),
            'active_tasks': current_perf.get('active_tasks', 0),
            'success_rate': current_perf.get('success_rate', 0),
            'error_rate': current_perf.get('error_rate', 0),
            'average_latency': current_perf.get('average_latency', 0)
        },
        'services': dashboard_data.get('active_services', [])
    }

# Initialize Jaeger exporter if configured
def setup_tracing(jaeger_endpoint: Optional[str] = None):
    """Setup distributed tracing with Jaeger"""
    if jaeger_endpoint:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_endpoint.split(':')[0],
            agent_port=int(jaeger_endpoint.split(':')[1]) if ':' in jaeger_endpoint else 6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        logger.info(f"Jaeger tracing enabled: {jaeger_endpoint}")

# Utility functions for creating custom metrics
def record_capsule_created(language: str, project_type: str, size_bytes: int):
    """Record capsule creation"""
    capsules_created.labels(language=language, project_type=project_type).inc()
    capsule_size.labels(language=language, project_type=project_type).observe(size_bytes)

def record_github_push(status: str, repo_type: str = 'public'):
    """Record GitHub push"""
    github_pushes.labels(status=status, repo_type=repo_type).inc()

def record_task_retry(task_type: str, reason: str):
    """Record task retry"""
    task_retries.labels(task_type=task_type, reason=reason).inc()

# Start metrics collection on import
asyncio.create_task(metrics_collector.start())