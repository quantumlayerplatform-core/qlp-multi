"""
Azure OpenAI Performance Monitoring
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import redis.asyncio as redis

from src.agents.azure_llm_client import llm_client
from src.agents.azure_llm_optimized import optimized_azure_client

logger = structlog.get_logger()

# Prometheus metrics
request_counter = Counter(
    'azure_openai_requests_total',
    'Total number of Azure OpenAI requests',
    ['model', 'status']
)

request_duration = Histogram(
    'azure_openai_request_duration_seconds',
    'Azure OpenAI request duration',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

token_usage = Counter(
    'azure_openai_tokens_total',
    'Total tokens used',
    ['model', 'type']  # type: prompt, completion, total
)

cache_hit_rate = Gauge(
    'azure_openai_cache_hit_rate',
    'Cache hit rate for Azure OpenAI requests'
)

error_rate = Gauge(
    'azure_openai_error_rate',
    'Error rate for Azure OpenAI requests'
)

concurrent_requests = Gauge(
    'azure_openai_concurrent_requests',
    'Number of concurrent requests'
)


class AzureOpenAIMonitor:
    """Monitor Azure OpenAI usage and performance"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or "redis://localhost:6379/2"
        self.redis_client = None
        self.metrics_buffer = []
        self.alert_thresholds = {
            "error_rate": 0.05,
            "p99_latency": 5.0,
            "token_usage_per_minute": 100000
        }
        
    async def initialize(self):
        """Initialize monitoring components"""
        self.redis_client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Azure monitor initialized")
        
    async def track_request(
        self,
        model: str,
        latency: float,
        tokens: Dict[str, int],
        success: bool,
        cached: bool = False
    ):
        """Track a single request"""
        status = "success" if success else "error"
        
        # Update Prometheus metrics
        request_counter.labels(model=model, status=status).inc()
        request_duration.labels(model=model).observe(latency)
        
        if tokens:
            token_usage.labels(model=model, type="prompt").inc(tokens.get("prompt_tokens", 0))
            token_usage.labels(model=model, type="completion").inc(tokens.get("completion_tokens", 0))
            token_usage.labels(model=model, type="total").inc(tokens.get("total_tokens", 0))
        
        # Store in Redis for time-series analysis
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "latency": latency,
            "tokens": tokens,
            "success": success,
            "cached": cached
        }
        
        await self.redis_client.lpush(
            f"azure_metrics:{model}",
            json.dumps(metric)
        )
        
        # Trim to keep only last hour of data
        await self.redis_client.ltrim(
            f"azure_metrics:{model}",
            0,
            3600  # Assuming ~1 request per second max
        )
        
    async def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        summary = {
            "models": {},
            "total_requests": 0,
            "total_errors": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "average_latency": 0
        }
        
        # Get metrics from unified client
        client_metrics = llm_client.get_metrics()
        
        # Get metrics from optimized client if available
        if hasattr(optimized_azure_client, 'get_metrics'):
            opt_metrics = await optimized_azure_client.get_metrics()
            cache_hit_rate.set(opt_metrics.get("cache_hit_rate", 0))
        
        # Aggregate metrics from Redis
        models = ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
        total_latency = 0
        request_count = 0
        
        for model in models:
            model_metrics = await self._get_model_metrics(model, cutoff_time)
            if model_metrics["requests"] > 0:
                summary["models"][model] = model_metrics
                summary["total_requests"] += model_metrics["requests"]
                summary["total_errors"] += model_metrics["errors"]
                summary["total_tokens"] += model_metrics["total_tokens"]
                summary["cache_hits"] += model_metrics["cache_hits"]
                total_latency += model_metrics["total_latency"]
                request_count += model_metrics["requests"]
        
        # Calculate averages
        if request_count > 0:
            summary["average_latency"] = total_latency / request_count
            summary["error_rate"] = summary["total_errors"] / request_count
            summary["cache_hit_rate"] = summary["cache_hits"] / request_count
            
            # Update Prometheus gauges
            error_rate.set(summary["error_rate"])
        
        return summary
    
    async def _get_model_metrics(self, model: str, cutoff_time: datetime) -> Dict[str, Any]:
        """Get metrics for a specific model"""
        metrics = {
            "requests": 0,
            "errors": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "total_latency": 0,
            "p50_latency": 0,
            "p99_latency": 0
        }
        
        # Get recent metrics from Redis
        raw_metrics = await self.redis_client.lrange(f"azure_metrics:{model}", 0, -1)
        latencies = []
        
        for raw in raw_metrics:
            try:
                metric = json.loads(raw)
                metric_time = datetime.fromisoformat(metric["timestamp"])
                
                if metric_time >= cutoff_time:
                    metrics["requests"] += 1
                    if not metric["success"]:
                        metrics["errors"] += 1
                    if metric.get("cached", False):
                        metrics["cache_hits"] += 1
                    
                    tokens = metric.get("tokens", {})
                    metrics["total_tokens"] += tokens.get("total_tokens", 0)
                    
                    latency = metric["latency"]
                    metrics["total_latency"] += latency
                    latencies.append(latency)
                    
            except Exception as e:
                logger.warning(f"Failed to parse metric: {e}")
        
        # Calculate percentiles
        if latencies:
            latencies.sort()
            metrics["p50_latency"] = latencies[len(latencies) // 2]
            metrics["p99_latency"] = latencies[int(len(latencies) * 0.99)]
        
        return metrics
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        summary = await self.get_metrics_summary(minutes=5)
        
        # Check error rate
        if summary.get("error_rate", 0) > self.alert_thresholds["error_rate"]:
            alerts.append({
                "severity": "critical",
                "type": "high_error_rate",
                "value": summary["error_rate"],
                "threshold": self.alert_thresholds["error_rate"],
                "message": f"Error rate {summary['error_rate']:.2%} exceeds threshold"
            })
        
        # Check latency for each model
        for model, metrics in summary.get("models", {}).items():
            if metrics.get("p99_latency", 0) > self.alert_thresholds["p99_latency"]:
                alerts.append({
                    "severity": "warning",
                    "type": "high_latency",
                    "model": model,
                    "value": metrics["p99_latency"],
                    "threshold": self.alert_thresholds["p99_latency"],
                    "message": f"P99 latency for {model} is {metrics['p99_latency']:.2f}s"
                })
        
        # Check token usage
        tokens_per_minute = summary.get("total_tokens", 0) / 5  # 5-minute window
        if tokens_per_minute > self.alert_thresholds["token_usage_per_minute"]:
            alerts.append({
                "severity": "warning",
                "type": "high_token_usage",
                "value": tokens_per_minute,
                "threshold": self.alert_thresholds["token_usage_per_minute"],
                "message": f"Token usage {tokens_per_minute:.0f}/min exceeds threshold"
            })
        
        return alerts
    
    async def generate_report(self) -> str:
        """Generate performance report"""
        summary = await self.get_metrics_summary(minutes=60)
        alerts = await self.check_alerts()
        
        report = f"""
Azure OpenAI Performance Report
===============================
Generated: {datetime.utcnow().isoformat()}

Overall Metrics (Last Hour):
- Total Requests: {summary['total_requests']:,}
- Error Rate: {summary.get('error_rate', 0):.2%}
- Cache Hit Rate: {summary.get('cache_hit_rate', 0):.2%}
- Average Latency: {summary.get('average_latency', 0):.2f}s
- Total Tokens Used: {summary['total_tokens']:,}

Model-Specific Metrics:
"""
        
        for model, metrics in summary.get("models", {}).items():
            report += f"""
{model}:
  - Requests: {metrics['requests']:,}
  - Errors: {metrics['errors']}
  - P50 Latency: {metrics['p50_latency']:.2f}s
  - P99 Latency: {metrics['p99_latency']:.2f}s
  - Tokens Used: {metrics['total_tokens']:,}
"""
        
        if alerts:
            report += "\nActive Alerts:\n"
            for alert in alerts:
                report += f"- [{alert['severity'].upper()}] {alert['message']}\n"
        else:
            report += "\nNo active alerts.\n"
        
        return report
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()


async def start_monitoring_server(port: int = 9090):
    """Start Prometheus metrics server"""
    start_http_server(port)
    logger.info(f"Prometheus metrics server started on port {port}")
    
    monitor = AzureOpenAIMonitor()
    await monitor.initialize()
    
    # Periodic metrics collection
    while True:
        try:
            summary = await monitor.get_metrics_summary()
            alerts = await monitor.check_alerts()
            
            if alerts:
                for alert in alerts:
                    logger.warning(f"Alert triggered", **alert)
            
            # Log summary every 5 minutes
            logger.info("Azure OpenAI metrics", **summary)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        
        await asyncio.sleep(300)  # 5 minutes


if __name__ == "__main__":
    # Run monitoring server
    asyncio.run(start_monitoring_server())