"""
Enhanced Production Worker with Enterprise-Grade Heartbeat Management
Temporal Worker for Quantum Layer Platform
"""
import asyncio
import logging
import json
import time
from datetime import timedelta, datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
from uuid import uuid4

# Import our enterprise heartbeat service
from .enterprise_heartbeat_service import EnterpriseHeartbeatService, with_enterprise_heartbeat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Activity timeout configurations - Production-grade settings
ACTIVITY_TIMEOUT = timedelta(minutes=30)  # Increased for enterprise workloads
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=120)  # 2 hours for complex enterprise workflows
HEARTBEAT_TIMEOUT = timedelta(minutes=15)  # Longer heartbeat timeout for stability
HEARTBEAT_INTERVAL = 15  # Send heartbeat every 15 seconds

# Workflow configuration
MAX_WORKFLOW_DURATION = timedelta(hours=3)  # Maximum workflow duration
WORKFLOW_TASK_TIMEOUT = timedelta(minutes=10)  # Timeout for workflow tasks

# Service call timeouts
SERVICE_CALL_TIMEOUT = 600.0  # 10 minutes for service calls (enterprise scale)
LLM_CALL_TIMEOUT = 300.0  # 5 minutes for LLM calls

# Import data classes from original worker
from .worker_production import (
    WorkflowTask, AgentExecution, ValidationResult, SharedContext,
    HITLRequest, WorkflowResult, DEFAULT_RETRY_POLICY
)

@activity.defn
async def execute_task_activity_enhanced(
    task: Dict[str, Any], 
    tier: str, 
    request_id: str, 
    shared_context_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhanced execute task activity with enterprise-grade heartbeat management.
    """
    import httpx
    from ..common.config import settings
    from .shared_context import SharedContext
    import redis.asyncio as redis
    import time
    
    activity.logger.info(f"Executing task {task['task_id']} with tier {tier}")
    
    # Initialize heartbeat service
    heartbeat_service = EnterpriseHeartbeatService(
        interval_seconds=HEARTBEAT_INTERVAL,
        max_retries=3,
        enable_metrics=True
    )
    
    try:
        # Start heartbeat service
        await heartbeat_service.start(
            message=f"Executing task {task['task_id']}",
            metadata={
                "task_id": task['task_id'],
                "tier": tier,
                "request_id": request_id,
                "task_type": task.get('type'),
                "complexity": task.get('complexity', 'simple')
            }
        )
        
        # Reconstruct shared context
        shared_context = SharedContext.from_dict(shared_context_dict)
        
        # Check cache first with heartbeat
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True
            )
            
            # Create cache key based on task description and type
            cache_key = f"task_result:{task['type']}:{hash(task['description'])}"
            cached_result = await redis_client.get(cache_key)
            
            if cached_result:
                activity.logger.info(f"Cache hit for task {task['task_id']}")
                cached_data = json.loads(cached_result)
                
                # Validate cache is still relevant (< 24 hours old)
                if cached_data.get('timestamp', 0) > time.time() - 86400:
                    await heartbeat_service.update_message("Using cached result")
                    return cached_data['result']
        except Exception as e:
            activity.logger.warning(f"Cache check failed: {str(e)}")
        
        # Enhanced execution context from shared context
        execution_context = task.get("context", {})
        execution_context.update({
            "request_id": request_id,
            "task_id": task["task_id"],
            "tier": tier,
            "preferred_language": shared_context.file_structure.primary_language,
            "main_file_name": shared_context.file_structure.main_file_name,
            "architecture_pattern": shared_context.architecture_pattern
        })
        
        # Check if this is TDD-enabled task
        tdd_enabled = (
            task.get("type") in ["implementation", "feature", "algorithm"] and 
            task.get("complexity") in ["moderate", "complex", "meta"]
        )
        
        # TDD Phase with heartbeat
        if tdd_enabled:
            await heartbeat_service.update_message(f"Generating tests for {task['task_id']}")
            
            async with httpx.AsyncClient(timeout=180.0) as test_client:
                test_generation_input = {
                    "task": {
                        "description": f"Generate comprehensive tests for: {task['description']}",
                        "type": "test_generation",
                        "task_id": f"{task['task_id']}_tests",
                        "complexity": task.get("complexity", "simple"),
                        "context": task.get("context", {}),
                        "dependencies": []
                    },
                    "tier": tier,
                    "context": execution_context,
                    "timeout": 180
                }
                
                try:
                    # Execute test generation with heartbeat context
                    test_response = await with_enterprise_heartbeat(
                        test_client.post(
                            f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                            json=test_generation_input
                        ),
                        message=f"Generating tests for {task['task_id']}",
                        interval=10,
                        task_id=task['task_id'],
                        operation="test_generation"
                    )
                    
                    if test_response.status_code == 200:
                        test_data = test_response.json()
                        test_code = test_data.get("output", "")
                        activity.logger.info(f"Generated tests for task {task['task_id']}")
                        execution_context["test_code"] = test_code
                        execution_context["tdd_mode"] = True
                except Exception as e:
                    activity.logger.warning(f"Test generation failed: {str(e)}, continuing without TDD")
        
        # Main execution with enhanced context and heartbeat
        await heartbeat_service.update_message(f"Executing main task {task['task_id']}")
        
        # Match the original worker's format exactly
        execution_input = {
            "task": {
                "id": task.get("task_id", task.get("id", "")),
                "type": task.get("type", "code_generation"),
                "description": task.get("description", ""),
                "complexity": task.get("complexity", "medium"),
                "status": task.get("status", "pending"),
                "metadata": task.get("metadata", {}),
                "meta": task.get("meta", {})  # Include structured metadata
            },
            "tier": tier,
            "context": execution_context,
            "preferred_language": shared_context.file_structure.primary_language,
            "shared_context": shared_context_dict,
            "request_id": request_id,
            "user_id": shared_context.user_id,
            "tenant_id": shared_context.tenant_id
        }
        
        # Log the request for debugging
        activity.logger.info(f"Sending to agent factory: {json.dumps(execution_input, indent=2)}")
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=SERVICE_CALL_TIMEOUT) as client:
            # Execute with enterprise heartbeat management
            response = await with_enterprise_heartbeat(
                execute_agent_call(client, execution_input, settings),
                message=f"Agent processing task {task['task_id']}",
                interval=10,
                task_id=task['task_id'],
                operation="agent_execution"
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", error_detail)
                except:
                    pass
                
                return {
                    "task_id": task["task_id"],
                    "status": "failed",
                    "error": f"Agent returned {response.status_code}: {error_detail}",
                    "execution_time": time.time() - start_time,
                    "agent_tier": tier
                }
            
            result_data = response.json()
            
            # Cache successful results
            if result_data.get("status") == "completed":
                await heartbeat_service.update_message("Caching successful result")
                try:
                    cache_value = json.dumps({
                        'result': result_data,
                        'timestamp': time.time()
                    })
                    await redis_client.setex(
                        cache_key,
                        86400,  # 24 hour TTL
                        cache_value
                    )
                except Exception as e:
                    activity.logger.warning(f"Failed to cache result: {str(e)}")
            
            execution_result = {
                "task_id": task["task_id"],
                "status": result_data.get("status", "completed"),
                "output": result_data.get("output"),
                "error": result_data.get("error"),
                "execution_time": time.time() - start_time,
                "agent_tier": tier,
                "metadata": result_data.get("metadata", {})
            }
            
            # If TDD mode, include test results
            if tdd_enabled and "test_code" in execution_context:
                execution_result["metadata"]["tdd_mode"] = True
                execution_result["metadata"]["test_code"] = execution_context["test_code"]
            
            # Include heartbeat statistics
            execution_result["metadata"]["heartbeat_stats"] = heartbeat_service.get_statistics()
            
            return execution_result
            
    finally:
        # Always stop heartbeat service
        await heartbeat_service.stop()


async def execute_agent_call(client: Any, execution_input: Dict[str, Any], settings: Any) -> Any:
    """
    Execute agent factory call with retry logic.
    This is separated to work with the heartbeat context manager.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = await client.post(
                f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                json=execution_input,
                timeout=SERVICE_CALL_TIMEOUT
            )
            
            if response.status_code >= 500 and attempt < max_retries - 1:
                activity.logger.warning(f"Agent factory returned {response.status_code}, retrying...")
                await asyncio.sleep(retry_delay * (2 ** attempt))
                continue
                
            return response
            
        except Exception as e:
            # Check if it's a timeout or connection error
            if "TimeoutException" in str(type(e)) or "ConnectError" in str(type(e)):
                activity.logger.error(f"Agent factory call failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
            else:
                activity.logger.error(f"Unexpected error calling agent factory: {str(e)}")
            raise


@activity.defn
async def validate_result_activity_enhanced(result: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced validation with heartbeat management.
    """
    import httpx
    from ..common.config import settings
    from ..validation.enhanced_validator import enhanced_validator
    
    activity.logger.info(f"Validating result for task: {task['task_id']}")
    
    # Initialize heartbeat service
    heartbeat_service = EnterpriseHeartbeatService(interval_seconds=10)
    
    try:
        await heartbeat_service.start(
            f"Validating task {task['task_id']}",
            {"task_id": task['task_id'], "task_type": task.get('type')}
        )
        
        if result.get("status") != "completed" or not result.get("output"):
            return {
                "overall_status": "failed",
                "confidence_score": 0,
                "checks": [
                    {
                        "name": "execution_status",
                        "type": "basic",
                        "status": "failed",
                        "message": f"Execution failed: {result.get('error', 'No output')}"
                    }
                ],
                "requires_human_review": True,
                "metadata": {"reason": "execution_failed"}
            }
        
        # Extract code and language from result
        output = result.get("output", "")
        code = ""
        language = "python"  # Default
        
        # Log the output type for debugging
        activity.logger.info(f"Output type: {type(output).__name__}, length: {len(str(output))}")
        
        # Handle different output formats
        if isinstance(output, dict):
            # Direct dict format
            code = output.get("code", "")
            language = output.get("language", "python")
        elif isinstance(output, str):
            # Could be JSON string or direct code
            if output.strip().startswith("{"):
                try:
                    output_data = json.loads(output)
                    code = output_data.get("code", output)
                    language = output_data.get("language", "python")
                except:
                    # If JSON parsing fails, treat as direct code
                    code = output
            else:
                # Direct code string
                code = output
        
        # If code is still a JSON string, try to parse it
        if isinstance(code, str) and code.strip().startswith("{"):
            try:
                code_data = json.loads(code)
                if isinstance(code_data, dict) and "code" in code_data:
                    code = code_data["code"]
            except:
                pass
        
        if not code or not isinstance(code, str):
            return {
                "overall_status": "failed", 
                "confidence_score": 0,
                "checks": [
                    {
                        "name": "code_extraction",
                        "type": "basic",
                        "status": "failed",
                        "message": "No code found in execution output"
                    }
                ],
                "requires_human_review": True,
                "metadata": {"reason": "no_code"}
            }
        
        await heartbeat_service.update_message("Calling validation service")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            validation_input = {
                "code": code,
                "language": language,
                "task_description": task["description"],
                "requirements": task.get("context", {}).get("requirements", []),
                "context": {
                    "task_id": task["task_id"],
                    "task_type": task["type"],
                    "complexity": task.get("complexity", "simple")
                }
            }
            
            # Call validation with heartbeat
            response = await with_enterprise_heartbeat(
                client.post(
                    f"http://validation-mesh:{settings.VALIDATION_MESH_PORT}/validate/code",
                    json=validation_input
                ),
                message=f"Validating code for {task['task_id']}",
                interval=10,
                task_id=task['task_id'],
                operation="code_validation"
            )
            
            if response.status_code != 200:
                return {
                    "overall_status": "error",
                    "confidence_score": 0,
                    "checks": [
                        {
                            "name": "validation_service",
                            "type": "service",
                            "status": "error",
                            "message": f"Validation service error: {response.status_code}"
                        }
                    ],
                    "requires_human_review": True,
                    "metadata": {"service_error": response.text}
                }
            
            validation_result = response.json()
            
            # Determine if AITL review is needed based on confidence
            confidence = validation_result.get("confidence_score", 0)
            requires_review = (
                confidence < 0.8 or 
                validation_result.get("overall_status") != "passed" or
                task.get("complexity") in ["complex", "meta"]
            )
            
            validation_result["requires_human_review"] = requires_review
            validation_result["metadata"] = validation_result.get("metadata", {})
            validation_result["metadata"]["heartbeat_stats"] = heartbeat_service.get_statistics()
            
            return validation_result
            
    finally:
        await heartbeat_service.stop()


# Export enhanced activities
__all__ = [
    'execute_task_activity_enhanced',
    'validate_result_activity_enhanced'
]