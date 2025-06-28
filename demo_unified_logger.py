#!/usr/bin/env python3
"""
Demo script to showcase the unified logger functionality
"""

import asyncio
import time
from datetime import datetime

# Import the unified logger
from src.common.logger import get_logger, setup_logging, log_function

# Setup logging for demo service
logger = setup_logging("demo-service", log_level="DEBUG")


@log_function(logger)
async def process_request(request_id: str, user_id: str):
    """Example async function with automatic logging"""
    # Simulate some processing
    await asyncio.sleep(0.1)
    
    # Return a result
    return {"status": "success", "processed_id": request_id}


@log_function(logger)
def calculate_metrics(data: list) -> dict:
    """Example sync function with automatic logging"""
    return {
        "count": len(data),
        "sum": sum(data),
        "avg": sum(data) / len(data) if data else 0
    }


async def main():
    """Main demo function"""
    print("\n🎉 QLP Unified Logger Demo\n")
    print("=" * 60)
    
    # 1. Basic logging
    print("\n1️⃣ Basic Logging:")
    logger.info("Demo service started", version="1.0.0", environment="development")
    logger.debug("Debug message - only visible in DEBUG mode")
    logger.warning("This is a warning message", threshold_exceeded=True)
    
    # 2. Contextual logging
    print("\n2️⃣ Contextual Logging:")
    request_logger = logger.bind(request_id="req-123", user_id="user-456")
    request_logger.info("Processing user request", action="login")
    request_logger.info("Request completed", duration=0.234)
    
    # 3. Structured logging
    print("\n3️⃣ Structured Logging:")
    logger.log_request(
        method="POST",
        path="/api/generate",
        status_code=200,
        duration=1.234,
        request_size=1024,
        response_size=2048
    )
    
    # 4. LLM call logging
    print("\n4️⃣ LLM Call Logging:")
    logger.log_llm_call(
        model="gpt-4-turbo-preview",
        provider="azure_openai",
        tokens={"prompt": 150, "completion": 250, "total": 400},
        latency=2.345,
        success=True,
        cache_hit=False
    )
    
    # 5. Task execution logging
    print("\n5️⃣ Task Execution Logging:")
    task_id = f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    logger.log_task(
        task_id=task_id,
        task_type="code_generation",
        status="started"
    )
    
    # Simulate task execution
    await asyncio.sleep(0.5)
    
    logger.log_task(
        task_id=task_id,
        task_type="code_generation",
        status="completed",
        duration=0.523,
        lines_generated=150
    )
    
    # 6. Metrics logging
    print("\n6️⃣ Metrics Logging:")
    logger.log_metric("api_requests", 1250, unit="requests/min")
    logger.log_metric("memory_usage", 85.5, unit="percent")
    logger.log_metric("active_agents", 15, unit="agents")
    
    # 7. Function decorators
    print("\n7️⃣ Function Decorators (automatic entry/exit logging):")
    
    # Call async function with decorator
    result = await process_request("req-789", "user-123")
    logger.info("Async function result", result=result)
    
    # Call sync function with decorator
    metrics = calculate_metrics([10, 20, 30, 40, 50])
    logger.info("Sync function result", metrics=metrics)
    
    # 8. Error handling
    print("\n8️⃣ Error Handling:")
    try:
        # Simulate an error
        raise ValueError("Simulated error for demo purposes")
    except Exception as e:
        logger.exception("An error occurred during processing", 
                        error_type=type(e).__name__,
                        request_id="req-error-123")
    
    # 9. Performance tracking
    print("\n9️⃣ Performance Tracking:")
    start_time = time.time()
    
    # Simulate some work
    await asyncio.sleep(0.1)
    
    elapsed = time.time() - start_time
    logger.info("Operation completed", 
               operation="data_processing",
               duration=elapsed,
               records_processed=1000,
               throughput=1000/elapsed)
    
    print("\n" + "=" * 60)
    print("\n✅ Demo completed! Check the following locations:")
    print(f"   • Console output above (with colors)")
    print(f"   • Log file: logs/demo-service.log (JSON format)")
    print(f"   • Try running with LOG_FORMAT=json for JSON console output")
    print("\n💡 Tips:")
    print("   • Set LOG_LEVEL=DEBUG to see debug messages")
    print("   • Set ENABLE_SENTRY=true with SENTRY_DSN for error tracking")
    print("   • Import logger in any module: from src.common.logger import get_logger")


if __name__ == "__main__":
    asyncio.run(main())