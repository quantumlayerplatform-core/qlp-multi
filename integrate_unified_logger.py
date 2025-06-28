#!/usr/bin/env python3
"""
Example of how to integrate the unified logger into existing services
"""

import asyncio
from src.common.logger import get_logger, setup_logging

# Example 1: Update orchestrator service
def update_orchestrator_logging():
    """Example code to add to orchestrator/main.py"""
    print("\n# Add to src/orchestrator/main.py:")
    print("""
from src.common.logger import setup_logging

# At the beginning of the file, after imports
logger = setup_logging("orchestrator", log_level="INFO")

# In your endpoint handlers:
@app.post("/generate/robust-capsule")
async def generate_robust_capsule(request: RobustCapsuleRequest):
    # Create request-specific logger
    request_logger = logger.bind(
        request_id=str(uuid.uuid4()),
        user_prompt=request.prompt[:50],
        target_score=request.target_score
    )
    
    request_logger.info("Starting robust capsule generation")
    
    # Log LLM calls
    request_logger.log_llm_call(
        model="gpt-4-turbo-preview",
        provider="azure_openai",
        tokens={"prompt": 150, "completion": 500},
        latency=2.1,
        success=True
    )
    
    # Log task progress
    request_logger.log_task(
        task_id=task_id,
        task_type="capsule_generation",
        status="completed",
        duration=3.45
    )
""")

# Example 2: Update agent factory service
def update_agent_factory_logging():
    """Example code to add to agents/main.py"""
    print("\n\n# Add to src/agents/main.py:")
    print("""
from src.common.logger import setup_logging, log_function

# Setup service logger
logger = setup_logging("agent-factory", log_level="INFO")

# Decorate functions for automatic logging
@log_function(logger)
async def spawn_agent(agent_type: str, task: str):
    # Function automatically logs entry/exit
    agent = await create_agent(agent_type)
    result = await agent.execute(task)
    return result

# In your Azure LLM client:
class UnifiedLLMClient:
    def __init__(self):
        self.logger = get_logger("llm-client")
    
    async def chat_completion(self, **kwargs):
        start_time = time.time()
        try:
            response = await self._make_request(**kwargs)
            
            # Log successful LLM call
            self.logger.log_llm_call(
                model=kwargs.get("model"),
                provider=self._get_provider(kwargs.get("model")),
                tokens={
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                latency=time.time() - start_time,
                success=True,
                cache_hit=False
            )
            
            return response
        except Exception as e:
            self.logger.error("LLM call failed", 
                            model=kwargs.get("model"),
                            error=str(e),
                            exc_info=True)
            raise
""")

# Example 3: Environment-specific configuration
def show_environment_config():
    """Show how to configure logging via environment"""
    print("\n\n# Environment Configuration:")
    print("""
# For development (colorful console output):
export LOG_LEVEL=DEBUG
export LOG_FORMAT=console
export SERVICE_NAME=qlp-dev

# For production (JSON logs for log aggregation):
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export SERVICE_NAME=qlp-prod
export ENABLE_SENTRY=true
export SENTRY_DSN=your-sentry-dsn-here

# For testing (minimal output):
export LOG_LEVEL=WARNING
export LOG_FORMAT=console
export SERVICE_NAME=qlp-test
""")

# Example 4: Structured logging patterns
def show_structured_patterns():
    """Show common structured logging patterns"""
    print("\n\n# Common Structured Logging Patterns:")
    print("""
# 1. Request tracing across services
request_id = str(uuid.uuid4())
logger = logger.bind(request_id=request_id)

# Pass request_id to other services
headers = {"X-Request-ID": request_id}

# 2. Performance monitoring
with logger.bind(operation="database_query") as op_logger:
    start = time.time()
    result = await db.query(sql)
    op_logger.log_metric("query_duration", time.time() - start, unit="seconds")

# 3. Error context
try:
    result = await risky_operation()
except Exception as e:
    logger.error("Operation failed",
                operation="risky_operation",
                input_data=data[:100],  # Truncate sensitive data
                error_type=type(e).__name__,
                exc_info=True)

# 4. Batch operations
logger.info("Processing batch",
           batch_id=batch_id,
           total_items=len(items))

for i, item in enumerate(items):
    item_logger = logger.bind(
        batch_id=batch_id,
        item_index=i,
        item_id=item.id
    )
    item_logger.info("Processing item")
""")

# Example 5: Integration with monitoring
def show_monitoring_integration():
    """Show how to integrate with monitoring systems"""
    print("\n\n# Monitoring Integration:")
    print("""
# Prometheus metrics from logs
# Use a log aggregator like Loki or ELK to parse structured logs

# Example Grafana query for LLM metrics:
{service_name="agent-factory"} |= "llm_call" | json | latency > 2

# Example alert rule:
alert: HighLLMLatency
expr: avg_over_time({service_name="agent-factory"} |= "llm_call" | json | unwrap latency [5m]) > 3
for: 5m
labels:
  severity: warning
annotations:
  summary: "High LLM API latency detected"

# CloudWatch Insights query for AWS:
fields @timestamp, service_name, model, latency
| filter event_type = "llm_call"
| stats avg(latency) by model
""")

if __name__ == "__main__":
    print("🚀 Unified Logger Integration Guide")
    print("=" * 60)
    
    update_orchestrator_logging()
    update_agent_factory_logging()
    show_environment_config()
    show_structured_patterns()
    show_monitoring_integration()
    
    print("\n\n✅ Integration Steps:")
    print("1. Import the logger: from src.common.logger import get_logger, setup_logging")
    print("2. Initialize at service start: logger = setup_logging('service-name')")
    print("3. Use structured logging throughout your code")
    print("4. Configure via environment variables")
    print("5. Monitor logs with your preferred aggregation tool")