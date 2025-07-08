#!/usr/bin/env python3
"""
Production-Grade Monitoring and Observability System
Comprehensive monitoring, metrics, and alerting for enterprise deployments
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from collections import defaultdict, deque
import structlog
import time

from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

logger = structlog.get_logger()


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"    # Service down, immediate action required
    HIGH = "high"           # Major functionality impacted
    MEDIUM = "medium"       # Performance degraded
    LOW = "low"            # Minor issues
    INFO = "info"          # Informational


class MetricType(str, Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Alert:
    """Alert definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    threshold: float
    duration: int  # seconds
    tags: Dict[str, str] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False


@dataclass
class SLATarget:
    """SLA target definition"""
    name: str
    target_percentage: float  # e.g., 99.9 for 99.9% uptime
    measurement_window: int   # seconds
    description: str


class ProductionMetrics:
    """Production-grade metrics collection system"""
    
    def __init__(self):
        # Prometheus metrics registry
        self.registry = CollectorRegistry()
        
        # Business metrics
        self.code_generation_requests = Counter(
            'code_generation_requests_total',
            'Total code generation requests',
            ['tenant_id', 'production_tier', 'status'],
            registry=self.registry
        )
        
        self.code_generation_duration = Histogram(
            'code_generation_duration_seconds',
            'Code generation duration',
            ['production_tier', 'complexity'],
            registry=self.registry
        )
        
        self.validation_checks = Counter(
            'validation_checks_total',
            'Total validation checks performed',
            ['check_type', 'status'],
            registry=self.registry
        )
        
        self.test_executions = Counter(
            'test_executions_total',
            'Total test executions',
            ['test_type', 'status'],
            registry=self.registry
        )
        
        self.quality_scores = Histogram(
            'quality_scores',
            'Quality scores distribution',
            ['metric_type'],
            registry=self.registry
        )
        
        # System metrics
        self.active_agents = Gauge(
            'active_agents_current',
            'Currently active agents',
            ['agent_type'],
            registry=self.registry
        )
        
        self.ensemble_size = Histogram(
            'ensemble_size',
            'Ensemble size distribution',
            ['voting_strategy'],
            registry=self.registry
        )
        
        self.confidence_scores = Histogram(
            'confidence_scores',
            'Confidence scores distribution',
            ['production_tier'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_rate = Counter(
            'errors_total',
            'Total errors',
            ['service', 'error_type'],
            registry=self.registry
        )
        
        self.circuit_breaker_states = Gauge(
            'circuit_breaker_state',
            'Circuit breaker states (0=closed, 1=open, 2=half-open)',
            ['service', 'circuit_name'],
            registry=self.registry
        )
        
        # Performance metrics
        self.response_times = Summary(
            'response_time_seconds',
            'Response time summary',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['service'],
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['service'],
            registry=self.registry
        )
        
        # SLA metrics
        self.sla_compliance = Gauge(
            'sla_compliance_percentage',
            'SLA compliance percentage',
            ['sla_name'],
            registry=self.registry
        )
        
        # OpenTelemetry setup
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)
        
        # Add Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=14268,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
        
        # Meter for OpenTelemetry metrics
        self.meter_provider = MeterProvider()
        metrics.set_meter_provider(self.meter_provider)
        self.meter = metrics.get_meter(__name__)
    
    def record_code_generation(
        self,
        tenant_id: str,
        production_tier: str,
        status: str,
        duration: float,
        complexity: str = "medium"
    ):
        """Record code generation metrics"""
        self.code_generation_requests.labels(
            tenant_id=tenant_id,
            production_tier=production_tier,
            status=status
        ).inc()
        
        self.code_generation_duration.labels(
            production_tier=production_tier,
            complexity=complexity
        ).observe(duration)
    
    def record_validation_check(self, check_type: str, status: str):
        """Record validation check metrics"""
        self.validation_checks.labels(
            check_type=check_type,
            status=status
        ).inc()
    
    def record_test_execution(self, test_type: str, status: str):
        """Record test execution metrics"""
        self.test_executions.labels(
            test_type=test_type,
            status=status
        ).inc()
    
    def record_quality_score(self, metric_type: str, score: float):
        """Record quality score metrics"""
        self.quality_scores.labels(metric_type=metric_type).observe(score)
    
    def update_active_agents(self, agent_type: str, count: int):
        """Update active agents count"""
        self.active_agents.labels(agent_type=agent_type).set(count)
    
    def record_ensemble_size(self, voting_strategy: str, size: int):
        """Record ensemble size"""
        self.ensemble_size.labels(voting_strategy=voting_strategy).observe(size)
    
    def record_confidence_score(self, production_tier: str, score: float):
        """Record confidence score"""
        self.confidence_scores.labels(production_tier=production_tier).observe(score)
    
    def record_error(self, service: str, error_type: str):
        """Record error occurrence"""
        self.error_rate.labels(service=service, error_type=error_type).inc()
    
    def update_circuit_breaker_state(self, service: str, circuit_name: str, state: int):
        """Update circuit breaker state"""
        self.circuit_breaker_states.labels(
            service=service,
            circuit_name=circuit_name
        ).set(state)
    
    def record_response_time(self, endpoint: str, method: str, duration: float):
        """Record API response time"""
        self.response_times.labels(endpoint=endpoint, method=method).observe(duration)
    
    def update_resource_usage(self, service: str, memory_bytes: int, cpu_percent: float):
        """Update resource usage metrics"""
        self.memory_usage.labels(service=service).set(memory_bytes)
        self.cpu_usage.labels(service=service).set(cpu_percent)
    
    def update_sla_compliance(self, sla_name: str, compliance_percentage: float):
        """Update SLA compliance metrics"""
        self.sla_compliance.labels(sla_name=sla_name).set(compliance_percentage)
    
    def get_metrics_output(self) -> str:
        """Get Prometheus metrics output"""
        return generate_latest(self.registry).decode('utf-8')


class AlertManager:
    """Production-grade alerting system"""
    
    def __init__(self, metrics: ProductionMetrics):
        self.metrics = metrics
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Alert rules
        self.alert_rules = self._define_alert_rules()
        
        # SLA targets
        self.sla_targets = self._define_sla_targets()
        
        # Alert evaluation loop
        self._evaluation_running = False
    
    def _define_alert_rules(self) -> List[Dict[str, Any]]:
        """Define alert rules for the platform"""
        return [
            {
                "name": "High Error Rate",
                "description": "Error rate exceeds threshold",
                "severity": AlertSeverity.CRITICAL,
                "condition": "error_rate_5m > 0.05",  # 5% error rate
                "threshold": 0.05,
                "duration": 300,  # 5 minutes
                "tags": {"component": "system"},
                "notification_channels": ["slack", "email", "pagerduty"]
            },
            {
                "name": "Low Code Quality",
                "description": "Average code quality below threshold",
                "severity": AlertSeverity.HIGH,
                "condition": "avg_quality_score_10m < 0.7",
                "threshold": 0.7,
                "duration": 600,  # 10 minutes
                "tags": {"component": "quality"},
                "notification_channels": ["slack", "email"]
            },
            {
                "name": "High Response Time",
                "description": "API response time exceeds threshold",
                "severity": AlertSeverity.MEDIUM,
                "condition": "p95_response_time_5m > 5.0",  # 5 seconds
                "threshold": 5.0,
                "duration": 300,
                "tags": {"component": "performance"},
                "notification_channels": ["slack"]
            },
            {
                "name": "Low Test Coverage",
                "description": "Test coverage below target",
                "severity": AlertSeverity.MEDIUM,
                "condition": "avg_test_coverage_15m < 0.8",  # 80%
                "threshold": 0.8,
                "duration": 900,  # 15 minutes
                "tags": {"component": "testing"},
                "notification_channels": ["slack"]
            },
            {
                "name": "Circuit Breaker Open",
                "description": "Circuit breaker is open",
                "severity": AlertSeverity.HIGH,
                "condition": "circuit_breaker_state == 1",
                "threshold": 1,
                "duration": 60,  # 1 minute
                "tags": {"component": "reliability"},
                "notification_channels": ["slack", "email"]
            },
            {
                "name": "Memory Usage High",
                "description": "Memory usage exceeds threshold",
                "severity": AlertSeverity.MEDIUM,
                "condition": "memory_usage_bytes > 8GB",
                "threshold": 8 * 1024 * 1024 * 1024,  # 8GB
                "duration": 300,
                "tags": {"component": "resources"},
                "notification_channels": ["slack"]
            },
            {
                "name": "SLA Breach",
                "description": "SLA compliance below target",
                "severity": AlertSeverity.CRITICAL,
                "condition": "sla_compliance < target",
                "threshold": 99.0,  # Will be overridden by SLA target
                "duration": 300,
                "tags": {"component": "sla"},
                "notification_channels": ["slack", "email", "pagerduty"]
            }
        ]
    
    def _define_sla_targets(self) -> List[SLATarget]:
        """Define SLA targets for the platform"""
        return [
            SLATarget(
                name="Platform Availability",
                target_percentage=99.9,
                measurement_window=86400,  # 24 hours
                description="Overall platform uptime"
            ),
            SLATarget(
                name="Code Generation Success Rate",
                target_percentage=95.0,
                measurement_window=3600,  # 1 hour
                description="Successful code generations"
            ),
            SLATarget(
                name="API Response Time P95",
                target_percentage=95.0,  # 95% under 2 seconds
                measurement_window=1800,  # 30 minutes
                description="95th percentile response time under 2 seconds"
            ),
            SLATarget(
                name="Quality Score Target",
                target_percentage=90.0,  # 90% of generations above quality threshold
                measurement_window=7200,  # 2 hours
                description="Percentage of high-quality code generations"
            )
        ]
    
    async def start_monitoring(self):
        """Start the alert monitoring loop"""
        if self._evaluation_running:
            return
        
        self._evaluation_running = True
        logger.info("Starting alert monitoring")
        
        while self._evaluation_running:
            try:
                await self._evaluate_alerts()
                await self._evaluate_slas()
                await asyncio.sleep(30)  # Evaluate every 30 seconds
            except Exception as e:
                logger.error("Alert evaluation failed", error=str(e))
                await asyncio.sleep(60)  # Back off on error
    
    async def stop_monitoring(self):
        """Stop the alert monitoring loop"""
        self._evaluation_running = False
        logger.info("Stopping alert monitoring")
    
    async def _evaluate_alerts(self):
        """Evaluate alert conditions"""
        
        # Get current metrics (this would integrate with actual metrics collection)
        current_metrics = await self._collect_current_metrics()
        
        for rule in self.alert_rules:
            alert_id = f"{rule['name'].replace(' ', '_').lower()}"
            
            # Evaluate condition (simplified - real implementation would parse conditions)
            condition_met = await self._evaluate_condition(rule, current_metrics)
            
            if condition_met:
                if alert_id not in self.active_alerts:
                    # Create new alert
                    alert = Alert(
                        id=alert_id,
                        name=rule["name"],
                        description=rule["description"],
                        severity=rule["severity"],
                        condition=rule["condition"],
                        threshold=rule["threshold"],
                        duration=rule["duration"],
                        tags=rule.get("tags", {}),
                        notification_channels=rule.get("notification_channels", [])
                    )
                    
                    self.active_alerts[alert_id] = alert
                    await self._send_alert_notification(alert, "FIRING")
                    
                    logger.warning(
                        "Alert fired",
                        alert_name=alert.name,
                        severity=alert.severity,
                        condition=alert.condition
                    )
            else:
                if alert_id in self.active_alerts:
                    # Resolve alert
                    alert = self.active_alerts[alert_id]
                    alert.resolved_at = datetime.utcnow()
                    
                    await self._send_alert_notification(alert, "RESOLVED")
                    
                    # Move to history
                    self.alert_history.append(alert)
                    del self.active_alerts[alert_id]
                    
                    logger.info(
                        "Alert resolved",
                        alert_name=alert.name,
                        duration=(alert.resolved_at - alert.created_at).total_seconds()
                    )
    
    async def _evaluate_slas(self):
        """Evaluate SLA compliance"""
        
        for sla in self.sla_targets:
            compliance = await self._calculate_sla_compliance(sla)
            
            # Update SLA compliance metric
            self.metrics.update_sla_compliance(sla.name, compliance)
            
            # Check for SLA breach
            if compliance < sla.target_percentage:
                alert_id = f"sla_breach_{sla.name.replace(' ', '_').lower()}"
                
                if alert_id not in self.active_alerts:
                    alert = Alert(
                        id=alert_id,
                        name=f"SLA Breach: {sla.name}",
                        description=f"SLA compliance {compliance:.2f}% below target {sla.target_percentage}%",
                        severity=AlertSeverity.CRITICAL,
                        condition=f"{sla.name} < {sla.target_percentage}%",
                        threshold=sla.target_percentage,
                        duration=300,
                        tags={"component": "sla", "sla_name": sla.name},
                        notification_channels=["slack", "email", "pagerduty"]
                    )
                    
                    self.active_alerts[alert_id] = alert
                    await self._send_alert_notification(alert, "FIRING")
    
    async def _collect_current_metrics(self) -> Dict[str, float]:
        """Collect current metric values (simplified implementation)"""
        
        # This would integrate with actual metrics collection
        # For now, return mock values
        return {
            "error_rate_5m": 0.02,
            "avg_quality_score_10m": 0.85,
            "p95_response_time_5m": 2.5,
            "avg_test_coverage_15m": 0.82,
            "memory_usage_bytes": 6 * 1024 * 1024 * 1024,  # 6GB
            "circuit_breaker_state": 0
        }
    
    async def _evaluate_condition(
        self, 
        rule: Dict[str, Any], 
        metrics: Dict[str, float]
    ) -> bool:
        """Evaluate alert condition (simplified implementation)"""
        
        condition = rule["condition"]
        threshold = rule["threshold"]
        
        # Simple condition evaluation
        if "error_rate_5m >" in condition:
            return metrics.get("error_rate_5m", 0) > threshold
        elif "avg_quality_score_10m <" in condition:
            return metrics.get("avg_quality_score_10m", 1.0) < threshold
        elif "p95_response_time_5m >" in condition:
            return metrics.get("p95_response_time_5m", 0) > threshold
        elif "avg_test_coverage_15m <" in condition:
            return metrics.get("avg_test_coverage_15m", 1.0) < threshold
        elif "circuit_breaker_state ==" in condition:
            return metrics.get("circuit_breaker_state", 0) == threshold
        elif "memory_usage_bytes >" in condition:
            return metrics.get("memory_usage_bytes", 0) > threshold
        
        return False
    
    async def _calculate_sla_compliance(self, sla: SLATarget) -> float:
        """Calculate SLA compliance percentage"""
        
        # This would calculate actual compliance from metrics
        # For now, return mock values
        mock_compliance = {
            "Platform Availability": 99.95,
            "Code Generation Success Rate": 96.2,
            "API Response Time P95": 94.8,
            "Quality Score Target": 91.5
        }
        
        return mock_compliance.get(sla.name, 100.0)
    
    async def _send_alert_notification(self, alert: Alert, status: str):
        """Send alert notification to configured channels"""
        
        for channel in alert.notification_channels:
            if channel in self.notification_handlers:
                try:
                    await self.notification_handlers[channel](alert, status)
                except Exception as e:
                    logger.error(
                        "Failed to send alert notification",
                        channel=channel,
                        alert_name=alert.name,
                        error=str(e)
                    )
    
    def register_notification_handler(
        self, 
        channel: str, 
        handler: Callable[[Alert, str], None]
    ):
        """Register a notification handler for a channel"""
        self.notification_handlers[channel] = handler
    
    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history 
            if alert.created_at >= cutoff_time
        ]
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an active alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(
                "Alert acknowledged",
                alert_id=alert_id,
                user=user
            )
            return True
        return False


class PerformanceMonitor:
    """Performance monitoring and profiling"""
    
    def __init__(self, metrics: ProductionMetrics):
        self.metrics = metrics
        self.performance_history = defaultdict(lambda: deque(maxlen=1000))
    
    def record_operation_performance(
        self,
        operation: str,
        duration: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record operation performance metrics"""
        
        # Record in performance history
        self.performance_history[operation].append({
            "timestamp": datetime.utcnow(),
            "duration": duration,
            "success": success,
            "metadata": metadata or {}
        })
        
        # Update Prometheus metrics
        status = "success" if success else "failure"
        self.metrics.record_response_time(operation, "POST", duration)
        
        if not success:
            self.metrics.record_error("orchestrator", "operation_failure")
    
    def get_performance_stats(
        self, 
        operation: str, 
        time_window: int = 3600
    ) -> Dict[str, Any]:
        """Get performance statistics for an operation"""
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
        recent_records = [
            record for record in self.performance_history[operation]
            if record["timestamp"] >= cutoff_time
        ]
        
        if not recent_records:
            return {"error": "No data available"}
        
        durations = [r["duration"] for r in recent_records]
        success_count = sum(1 for r in recent_records if r["success"])
        
        return {
            "operation": operation,
            "time_window_seconds": time_window,
            "total_operations": len(recent_records),
            "success_rate": success_count / len(recent_records),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p50_duration": sorted(durations)[len(durations) // 2],
            "p95_duration": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
            "p99_duration": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
        }


class DistributedTracing:
    """Distributed tracing for request correlation"""
    
    def __init__(self, tracer):
        self.tracer = tracer
    
    def create_span(self, operation_name: str, parent_span=None):
        """Create a new tracing span"""
        if parent_span:
            return self.tracer.start_span(operation_name, child_of=parent_span)
        else:
            return self.tracer.start_span(operation_name)
    
    def add_span_attributes(self, span, attributes: Dict[str, Any]):
        """Add attributes to a span"""
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
    
    def record_span_event(self, span, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Record an event in a span"""
        span.add_event(event_name, attributes or {})
    
    def finish_span(self, span, status: Optional[StatusCode] = None, error: Optional[Exception] = None):
        """Finish a span with optional status and error"""
        if status:
            span.set_status(Status(status))
        
        if error:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
        
        span.end()


# Example notification handlers
async def slack_notification_handler(alert: Alert, status: str):
    """Example Slack notification handler"""
    logger.info(
        "Slack notification",
        alert_name=alert.name,
        status=status,
        severity=alert.severity
    )
    # Implement actual Slack webhook call


async def email_notification_handler(alert: Alert, status: str):
    """Example email notification handler"""
    logger.info(
        "Email notification",
        alert_name=alert.name,
        status=status,
        severity=alert.severity
    )
    # Implement actual email sending


async def pagerduty_notification_handler(alert: Alert, status: str):
    """Example PagerDuty notification handler"""
    logger.info(
        "PagerDuty notification",
        alert_name=alert.name,
        status=status,
        severity=alert.severity
    )
    # Implement actual PagerDuty API call


# Production monitoring system factory
class ProductionMonitoringSystem:
    """Complete production monitoring system"""
    
    def __init__(self):
        self.metrics = ProductionMetrics()
        self.alert_manager = AlertManager(self.metrics)
        self.performance_monitor = PerformanceMonitor(self.metrics)
        self.tracing = DistributedTracing(self.metrics.tracer)
        
        # Register notification handlers
        self.alert_manager.register_notification_handler("slack", slack_notification_handler)
        self.alert_manager.register_notification_handler("email", email_notification_handler)
        self.alert_manager.register_notification_handler("pagerduty", pagerduty_notification_handler)
    
    async def start(self):
        """Start the monitoring system"""
        await self.alert_manager.start_monitoring()
        logger.info("Production monitoring system started")
    
    async def stop(self):
        """Stop the monitoring system"""
        await self.alert_manager.stop_monitoring()
        logger.info("Production monitoring system stopped")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        return {
            "status": "degraded" if critical_alerts else "healthy" if active_alerts else "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": len(active_alerts),
            "critical_alerts": len(critical_alerts),
            "components": {
                "metrics_collection": "healthy",
                "alerting": "healthy",
                "tracing": "healthy"
            }
        }


# Export main components
__all__ = [
    "ProductionMonitoringSystem",
    "ProductionMetrics", 
    "AlertManager",
    "PerformanceMonitor",
    "DistributedTracing",
    "Alert",
    "AlertSeverity",
    "SLATarget"
]