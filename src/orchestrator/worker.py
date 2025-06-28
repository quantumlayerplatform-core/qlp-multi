"""
Temporal Worker for Quantum Layer Platform
Handles async workflow execution with state management
"""
import asyncio
import logging
from datetime import timedelta
from typing import Dict, List, Any, Optional
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

from ..common.models import (
    NLPRequest, Task, ExecutionPlan, ExecutionResult,
    AgentExecutionRequest, ValidationRequest
)
from ..agents.client import AgentFactoryClient
from ..validation.client import ValidationMeshClient
from ..memory.client import VectorMemoryClient
from ..sandbox.client import SandboxServiceClient
from ..common.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Activity timeout settings
ACTIVITY_TIMEOUT = timedelta(minutes=5)
HEARTBEAT_TIMEOUT = timedelta(seconds=30)

# Service clients
agent_client = AgentFactoryClient(base_url=f"http://localhost:{settings.AGENT_FACTORY_PORT}")
validation_client = ValidationMeshClient(base_url=f"http://localhost:{settings.VALIDATION_MESH_PORT}")
memory_client = VectorMemoryClient(base_url=f"http://localhost:{settings.VECTOR_MEMORY_PORT}")
sandbox_client = SandboxServiceClient(base_url=f"http://localhost:{settings.SANDBOX_PORT}")


# Activities - Individual steps that can be retried
@activity.defn
async def decompose_request_activity(request: NLPRequest) -> List[Task]:
    """Decompose NLP request into tasks"""
    logger.info(f"Decomposing request: {request.request_id}")
    # This would normally call the orchestrator's decomposition logic
    # For now, we'll create a simple task
    return [
        Task(
            task_id=f"{request.request_id}_task_1",
            type="code_generation",
            description=request.description,
            dependencies=[],
            context={"original_request": request.description}
        )
    ]


@activity.defn
async def execute_task_activity(task: Task, request_id: str) -> ExecutionResult:
    """Execute a single task using appropriate agent"""
    logger.info(f"Executing task: {task.task_id}")
    
    # Create agent execution request
    agent_request = AgentExecutionRequest(
        request_id=request_id,
        task=task,
        context=task.context or {}
    )
    
    try:
        # Execute via agent service
        result = await agent_client.execute(agent_request)
        
        # Store in memory for learning
        await memory_client.store_execution(request_id, task, result)
        
        return result
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        return ExecutionResult(
            success=False,
            output=None,
            error=str(e),
            execution_time=0,
            metadata={"error_type": type(e).__name__}
        )


@activity.defn
async def validate_result_activity(result: ExecutionResult, task: Task) -> ValidationRequest:
    """Validate execution result"""
    logger.info(f"Validating result for task: {task.task_id}")
    
    if not result.success or not result.output:
        return ValidationRequest(
            code="",
            language="python",
            validation_type="syntax",
            context={"error": "No code generated"}
        )
    
    # Extract code from result
    code = result.output.get("code", "") if isinstance(result.output, dict) else str(result.output)
    language = result.output.get("language", "python") if isinstance(result.output, dict) else "python"
    
    # Validate via validation service
    validation_result = await validation_client.validate_code(
        code=code,
        language=language,
        validators=["syntax", "style", "security", "types"]
    )
    
    return validation_result


@activity.defn
async def execute_in_sandbox_activity(code: str, language: str, inputs: Optional[Dict] = None) -> ExecutionResult:
    """Execute code in sandbox environment"""
    logger.info(f"Executing code in sandbox for language: {language}")
    
    try:
        result = await sandbox_client.execute(
            code=code,
            language=language,
            inputs=inputs or {}
        )
        return result
    except Exception as e:
        logger.error(f"Sandbox execution failed: {str(e)}")
        return ExecutionResult(
            success=False,
            output=None,
            error=str(e),
            execution_time=0,
            metadata={"sandbox_error": True}
        )


@activity.defn
async def human_review_activity(task: Task, result: ExecutionResult, validation: Any) -> Dict[str, Any]:
    """Trigger human review for low confidence results"""
    logger.info(f"Human review triggered for task: {task.task_id}")
    
    # In production, this would:
    # 1. Send notification to human reviewer
    # 2. Wait for approval/rejection
    # 3. Return review result
    
    # For now, auto-approve with mock review
    return {
        "approved": True,
        "confidence": 0.85,
        "reviewer": "system_mock",
        "comments": "Auto-approved for development"
    }


# Workflow - Orchestrates the entire execution
@workflow.defn
class QLPWorkflow:
    """Main workflow for Quantum Layer Platform request processing"""
    
    @workflow.run
    async def run(self, request: NLPRequest) -> Dict[str, Any]:
        """Execute the complete workflow for an NLP request"""
        workflow_result = {
            "request_id": request.request_id,
            "status": "started",
            "tasks": [],
            "errors": [],
            "execution_time": 0
        }
        
        try:
            # Step 1: Decompose request into tasks
            tasks = await workflow.execute_activity(
                decompose_request_activity,
                request,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                heartbeat_timeout=HEARTBEAT_TIMEOUT
            )
            
            workflow_result["status"] = "decomposed"
            workflow_result["task_count"] = len(tasks)
            
            # Step 2: Execute tasks (can be parallelized based on dependencies)
            task_results = []
            for task in tasks:
                # Execute task
                exec_result = await workflow.execute_activity(
                    execute_task_activity,
                    args=[task, request.request_id],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    heartbeat_timeout=HEARTBEAT_TIMEOUT
                )
                
                # Validate result
                validation_result = await workflow.execute_activity(
                    validate_result_activity,
                    args=[exec_result, task],
                    start_to_close_timeout=ACTIVITY_TIMEOUT
                )
                
                # Check if human review needed
                confidence = validation_result.get("confidence", 1.0) if isinstance(validation_result, dict) else 0.9
                if confidence < settings.HUMAN_REVIEW_THRESHOLD:
                    review_result = await workflow.execute_activity(
                        human_review_activity,
                        args=[task, exec_result, validation_result],
                        start_to_close_timeout=timedelta(hours=24)  # Long timeout for human review
                    )
                    
                    if not review_result["approved"]:
                        workflow_result["errors"].append({
                            "task_id": task.task_id,
                            "error": "Human review rejected",
                            "review": review_result
                        })
                        continue
                
                # Execute in sandbox if validation passed
                if exec_result.success and exec_result.output:
                    code = exec_result.output.get("code", "") if isinstance(exec_result.output, dict) else ""
                    language = exec_result.output.get("language", "python") if isinstance(exec_result.output, dict) else "python"
                    
                    if code:
                        sandbox_result = await workflow.execute_activity(
                            execute_in_sandbox_activity,
                            args=[code, language, None],
                            start_to_close_timeout=ACTIVITY_TIMEOUT
                        )
                        
                        task_results.append({
                            "task_id": task.task_id,
                            "execution": exec_result.dict() if hasattr(exec_result, 'dict') else exec_result,
                            "validation": validation_result,
                            "sandbox": sandbox_result.dict() if hasattr(sandbox_result, 'dict') else sandbox_result
                        })
                
            workflow_result["tasks"] = task_results
            workflow_result["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            workflow_result["status"] = "failed"
            workflow_result["errors"].append({
                "type": "workflow_error",
                "message": str(e)
            })
        
        return workflow_result


# Worker setup
async def start_worker():
    """Start the Temporal worker"""
    # Create client
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[QLPWorkflow],
        activities=[
            decompose_request_activity,
            execute_task_activity,
            validate_result_activity,
            execute_in_sandbox_activity,
            human_review_activity
        ]
    )
    
    logger.info(f"Starting Temporal worker on queue: {settings.TEMPORAL_TASK_QUEUE}")
    await worker.run()


# Main entry point
if __name__ == "__main__":
    asyncio.run(start_worker())
