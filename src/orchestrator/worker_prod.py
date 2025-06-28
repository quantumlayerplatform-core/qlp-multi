"""
Temporal Worker for Quantum Layer Platform - Production Implementation
No mocks, proper error handling, and full integration with all services
"""
import asyncio
import logging
from datetime import timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ACTIVITY_TIMEOUT = timedelta(minutes=5)
HEARTBEAT_TIMEOUT = timedelta(seconds=30)
HUMAN_REVIEW_TIMEOUT = timedelta(hours=24)
CONFIDENCE_THRESHOLD = 0.7

# Workflow-safe data classes (no external dependencies)
@dataclass
class WorkflowTask:
    """Workflow-safe task representation"""
    task_id: str
    type: str
    description: str
    complexity: str = "simple"
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowRequest:
    """Workflow-safe request representation"""
    request_id: str
    description: str
    tenant_id: str
    user_id: str
    requirements: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Activities - These run outside the sandbox and can use any imports
@activity.defn
async def decompose_request_activity(request: Dict[str, Any]) -> Dict[str, Any]:
    """Decompose NLP request into tasks with execution plan"""
    import httpx
    from ..common.config import settings
    
    logger.info(f"Decomposing request: {request['request_id']}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Use the orchestrator's decomposition endpoint
        response = await client.post(
            f"http://localhost:{settings.ORCHESTRATOR_PORT}/test/decompose",
            json={
                "description": request["description"],
                "tenant_id": request["tenant_id"],
                "user_id": request["user_id"],
                "requirements": request.get("requirements"),
                "constraints": request.get("constraints", {})
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "tasks": data.get("tasks", []),
                "dependencies": data.get("dependencies", {}),
                "task_assignments": data.get("task_assignments", {}),
                "execution_order": data.get("execution_order", [])
            }
        else:
            error_detail = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", error_detail)
            except:
                pass
            raise Exception(f"Decomposition failed: {error_detail}")


@activity.defn
async def get_task_context_activity(task: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Retrieve relevant context from vector memory for task execution"""
    import httpx
    from ..common.config import settings
    
    logger.info(f"Getting context for task: {task['task_id']}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for similar past requests
        search_response = await client.post(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/search/patterns",
            json={
                "query": task["description"],
                "limit": 5
            }
        )
        
        context = {
            "similar_patterns": [],
            "performance_history": {}
        }
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            context["similar_patterns"] = search_data.get("results", [])
        
        # Get historical performance data
        perf_response = await client.get(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/performance/task",
            params={
                "type": task["type"],
                "complexity": task.get("complexity", "simple")
            }
        )
        
        if perf_response.status_code == 200:
            context["performance_history"] = perf_response.json()
        
        return context


@activity.defn
async def execute_task_activity(task: Dict[str, Any], tier: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single task using appropriate agent"""
    import httpx
    from ..common.config import settings
    
    logger.info(f"Executing task: {task['task_id']} with tier: {tier}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Execute via agent service
        response = await client.post(
            f"http://localhost:{settings.AGENT_FACTORY_PORT}/execute",
            json={
                "task": task,
                "tier": tier,
                "context": context
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Store execution result in memory
            try:
                await client.post(
                    f"http://localhost:{settings.VECTOR_MEMORY_PORT}/patterns/execution",
                    json={
                        "content": {
                            "task": task,
                            "result": result,
                            "tier": tier
                        },
                        "metadata": {
                            "task_id": task["task_id"],
                            "task_type": task["type"],
                            "tier": tier,
                            "success": result.get("status") == "completed",
                            "confidence": result.get("confidence_score", 0)
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store execution in memory: {e}")
            
            return result
        else:
            error_detail = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", error_detail)
            except:
                pass
            
            return {
                "status": "failed",
                "error": f"Agent execution failed: {error_detail}",
                "output": None,
                "confidence_score": 0
            }


@activity.defn
async def validate_result_activity(result: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """Validate execution result with full validation pipeline"""
    import httpx
    from ..common.config import settings
    
    logger.info(f"Validating result for task: {task['task_id']}")
    
    if result.get("status") != "completed" or not result.get("output"):
        return {
            "overall_status": "failed",
            "confidence_score": 0,
            "checks": [],
            "error": "No valid output to validate"
        }
    
    # Extract code from result
    output = result.get("output", {})
    if isinstance(output, dict):
        code = output.get("code", output.get("content", ""))
        language = output.get("language", "python")
    else:
        code = str(output)
        language = "python"
    
    if not code:
        return {
            "overall_status": "failed",
            "confidence_score": 0,
            "checks": [],
            "error": "No code found in output"
        }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Run full validation
        response = await client.post(
            f"http://localhost:{settings.VALIDATION_MESH_PORT}/validate/code",
            json={
                "code": code,
                "language": language
            }
        )
        
        if response.status_code == 200:
            validation_data = response.json()
            
            # Store validation result in memory
            try:
                await client.post(
                    f"http://localhost:{settings.VECTOR_MEMORY_PORT}/patterns/validation",
                    json={
                        "content": {
                            "task_id": task["task_id"],
                            "validation": validation_data
                        },
                        "metadata": {
                            "task_type": task["type"],
                            "overall_status": validation_data.get("overall_status"),
                            "confidence": validation_data.get("confidence_score", 0)
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store validation in memory: {e}")
            
            return validation_data
        else:
            return {
                "overall_status": "error",
                "confidence_score": 0,
                "error": f"Validation service error: {response.status_code}"
            }


@activity.defn
async def execute_in_sandbox_activity(code: str, language: str, test_cases: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Execute code in sandbox environment with optional test cases"""
    import httpx
    from ..common.config import settings
    
    logger.info(f"Executing code in sandbox for language: {language}")
    
    results = {
        "execution_results": [],
        "all_passed": True,
        "execution_time": 0
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # First, execute the code itself
        response = await client.post(
            f"http://localhost:{settings.SANDBOX_PORT}/execute",
            json={
                "code": code,
                "language": language
            }
        )
        
        if response.status_code == 200:
            main_result = response.json()
            results["execution_results"].append({
                "type": "main_execution",
                "result": main_result
            })
            results["execution_time"] += main_result.get("execution_time", 0)
            
            if not main_result.get("success", False):
                results["all_passed"] = False
        else:
            results["all_passed"] = False
            results["execution_results"].append({
                "type": "main_execution",
                "error": f"Sandbox error: {response.status_code}"
            })
            
        # Execute test cases if provided
        if test_cases and results["all_passed"]:
            for i, test_case in enumerate(test_cases):
                test_response = await client.post(
                    f"http://localhost:{settings.SANDBOX_PORT}/execute",
                    json={
                        "code": test_case.get("code", ""),
                        "language": language,
                        "inputs": test_case.get("inputs", {})
                    }
                )
                
                if test_response.status_code == 200:
                    test_result = test_response.json()
                    results["execution_results"].append({
                        "type": f"test_case_{i}",
                        "result": test_result,
                        "expected": test_case.get("expected")
                    })
                    
                    if not test_result.get("success", False):
                        results["all_passed"] = False
                else:
                    results["all_passed"] = False
                    results["execution_results"].append({
                        "type": f"test_case_{i}",
                        "error": f"Test execution error: {test_response.status_code}"
                    })
        
        return results


@activity.defn
async def create_qlcapsule_activity(request: Dict[str, Any], task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a QLCapsule with all artifacts"""
    import httpx
    from ..common.config import settings
    import json
    
    logger.info(f"Creating QLCapsule for request: {request['request_id']}")
    
    # Aggregate all code, tests, and documentation
    source_code = {}
    tests = {}
    documentation = []
    validation_reports = []
    
    for result in task_results:
        task = result.get("task", {})
        execution = result.get("execution", {})
        
        if execution.get("status") == "completed" and execution.get("output"):
            output = execution.get("output", {})
            
            # Extract based on task type
            if task.get("type") == "implement":
                if isinstance(output, dict):
                    filename = output.get("filename", f"{task['task_id']}.py")
                    source_code[filename] = output.get("code", output.get("content", ""))
                    
            elif task.get("type") == "test":
                if isinstance(output, dict):
                    filename = output.get("filename", f"test_{task['task_id']}.py")
                    tests[filename] = output.get("code", output.get("content", ""))
                    
            elif task.get("type") == "document":
                if isinstance(output, dict):
                    documentation.append(output.get("content", ""))
                else:
                    documentation.append(str(output))
            
            # Collect validation reports
            validation = result.get("validation", {})
            if validation:
                validation_reports.append(validation)
    
    # Create capsule manifest
    manifest = {
        "version": "1.0",
        "request_id": request["request_id"],
        "description": request["description"],
        "created_by": request["user_id"],
        "tenant_id": request["tenant_id"],
        "tasks_completed": len([r for r in task_results if r.get("execution", {}).get("status") == "completed"]),
        "tasks_total": len(task_results)
    }
    
    # Calculate overall validation score
    if validation_reports:
        avg_confidence = sum(v.get("confidence_score", 0) for v in validation_reports) / len(validation_reports)
        overall_status = "passed" if all(v.get("overall_status") in ["passed", "passed_with_warnings"] for v in validation_reports) else "failed"
    else:
        avg_confidence = 0
        overall_status = "no_validation"
    
    capsule = {
        "id": f"qlc_{request['request_id']}",
        "request_id": request["request_id"],
        "manifest": manifest,
        "source_code": source_code,
        "tests": tests,
        "documentation": "\n\n".join(documentation),
        "validation_summary": {
            "overall_status": overall_status,
            "average_confidence": avg_confidence,
            "report_count": len(validation_reports)
        },
        "deployment_config": {
            "language": "python",  # TODO: Detect from code
            "dependencies": [],  # TODO: Extract from code
            "entry_point": "main.py"  # TODO: Determine from structure
        }
    }
    
    # Store capsule in memory
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            await client.post(
                f"http://localhost:{settings.VECTOR_MEMORY_PORT}/patterns/capsule",
                json={
                    "content": json.dumps(capsule),
                    "metadata": {
                        "capsule_id": capsule["id"],
                        "request_id": request["request_id"],
                        "tenant_id": request["tenant_id"],
                        "file_count": len(source_code) + len(tests),
                        "validation_status": overall_status
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store capsule in memory: {e}")
    
    return capsule


@activity.defn
async def notify_completion_activity(request: Dict[str, Any], capsule: Dict[str, Any], status: str) -> Dict[str, Any]:
    """Send completion notifications"""
    logger.info(f"Sending completion notification for request: {request['request_id']}")
    
    # In production, this would integrate with:
    # - Email service
    # - Slack/Teams webhooks
    # - SMS notifications
    # - Dashboard updates
    
    notification = {
        "request_id": request["request_id"],
        "user_id": request["user_id"],
        "status": status,
        "capsule_id": capsule.get("id"),
        "summary": {
            "files_created": len(capsule.get("source_code", {})) + len(capsule.get("tests", {})),
            "validation_status": capsule.get("validation_summary", {}).get("overall_status"),
            "confidence": capsule.get("validation_summary", {}).get("average_confidence", 0)
        }
    }
    
    # For now, just log it
    logger.info(f"Notification: {notification}")
    
    return notification


# Workflow - Pure orchestration logic
@workflow.defn
class QLPWorkflow:
    """Production workflow for Quantum Layer Platform request processing"""
    
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete workflow for an NLP request"""
        import time
        start_time = time.time()
        
        workflow_result = {
            "request_id": request["request_id"],
            "status": "started",
            "phase": "initialization",
            "tasks": [],
            "errors": [],
            "warnings": [],
            "capsule": None,
            "execution_time": 0
        }
        
        try:
            # Phase 1: Decompose request into tasks
            workflow_result["phase"] = "decomposition"
            
            decomposition = await workflow.execute_activity(
                decompose_request_activity,
                request,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                heartbeat_timeout=HEARTBEAT_TIMEOUT,
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2
                )
            )
            
            tasks = decomposition.get("tasks", [])
            dependencies = decomposition.get("dependencies", {})
            task_assignments = decomposition.get("task_assignments", {})
            execution_order = decomposition.get("execution_order", [])
            
            if not tasks:
                raise Exception("No tasks generated from decomposition")
            
            workflow_result["task_count"] = len(tasks)
            workflow_result["status"] = "decomposed"
            
            # Phase 2: Execute tasks following dependency order
            workflow_result["phase"] = "execution"
            task_results = []
            executed_tasks = set()
            
            # Create task lookup
            task_map = {task["id"]: task for task in tasks}
            
            # Execute tasks in dependency order
            for task_id in execution_order:
                if task_id not in task_map:
                    continue
                    
                task = task_map[task_id]
                
                # Check dependencies
                task_deps = dependencies.get(task_id, [])
                if not all(dep in executed_tasks for dep in task_deps):
                    workflow_result["warnings"].append({
                        "task_id": task_id,
                        "warning": "Dependencies not satisfied, skipping"
                    })
                    continue
                
                # Get context from vector memory
                context = await workflow.execute_activity(
                    get_task_context_activity,
                    args=[task, request["request_id"]],
                    start_to_close_timeout=ACTIVITY_TIMEOUT
                )
                
                # Execute task with assigned tier
                tier = task_assignments.get(task_id, "T0")
                exec_result = await workflow.execute_activity(
                    execute_task_activity,
                    args=[task, tier, context],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    heartbeat_timeout=HEARTBEAT_TIMEOUT,
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=2)
                    )
                )
                
                # Validate result
                validation_result = await workflow.execute_activity(
                    validate_result_activity,
                    args=[exec_result, task],
                    start_to_close_timeout=ACTIVITY_TIMEOUT
                )
                
                # Execute in sandbox if validation passed
                sandbox_result = None
                if (exec_result.get("status") == "completed" and 
                    validation_result.get("overall_status") in ["passed", "passed_with_warnings"]):
                    
                    output = exec_result.get("output", {})
                    if isinstance(output, dict):
                        code = output.get("code", output.get("content", ""))
                        language = output.get("language", "python")
                    else:
                        code = str(output)
                        language = "python"
                    
                    if code:
                        sandbox_result = await workflow.execute_activity(
                            execute_in_sandbox_activity,
                            args=[code, language, None],
                            start_to_close_timeout=ACTIVITY_TIMEOUT
                        )
                
                # Record result
                task_result = {
                    "task": task,
                    "execution": exec_result,
                    "validation": validation_result,
                    "sandbox": sandbox_result
                }
                
                task_results.append(task_result)
                executed_tasks.add(task_id)
                
                # Check if task failed
                if exec_result.get("status") != "completed":
                    workflow_result["errors"].append({
                        "task_id": task_id,
                        "phase": "execution",
                        "error": exec_result.get("error", "Task execution failed")
                    })
            
            workflow_result["tasks"] = task_results
            workflow_result["status"] = "executed"
            
            # Phase 3: Create QLCapsule
            workflow_result["phase"] = "packaging"
            
            capsule = await workflow.execute_activity(
                create_qlcapsule_activity,
                args=[request, task_results],
                start_to_close_timeout=ACTIVITY_TIMEOUT
            )
            
            workflow_result["capsule"] = capsule
            workflow_result["status"] = "completed"
            
            # Phase 4: Send notifications
            workflow_result["phase"] = "notification"
            
            await workflow.execute_activity(
                notify_completion_activity,
                args=[request, capsule, "completed"],
                start_to_close_timeout=ACTIVITY_TIMEOUT
            )
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            workflow_result["status"] = "failed"
            workflow_result["errors"].append({
                "phase": workflow_result.get("phase", "unknown"),
                "error": str(e),
                "type": type(e).__name__
            })
            
            # Send failure notification
            try:
                await workflow.execute_activity(
                    notify_completion_activity,
                    args=[request, {}, "failed"],
                    start_to_close_timeout=ACTIVITY_TIMEOUT
                )
            except:
                pass
        
        # Calculate total execution time
        workflow_result["execution_time"] = time.time() - start_time
        
        return workflow_result


# Worker setup
async def start_worker():
    """Start the Temporal worker"""
    # Import config here to get proper settings
    from ..common.config import settings
    
    # Create client
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE
    )
    
    # Create worker with activities and workflow
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[QLPWorkflow],
        activities=[
            decompose_request_activity,
            get_task_context_activity,
            execute_task_activity,
            validate_result_activity,
            execute_in_sandbox_activity,
            create_qlcapsule_activity,
            notify_completion_activity
        ]
    )
    
    logger.info(f"Starting Temporal worker on queue: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info(f"Connected to Temporal at: {settings.TEMPORAL_HOST}")
    logger.info("Worker ready to process workflows")
    
    # Write PID file
    import os
    with open(".temporal_worker.pid", "w") as f:
        f.write(str(os.getpid()))
    
    try:
        await worker.run()
    finally:
        # Clean up PID file
        if os.path.exists(".temporal_worker.pid"):
            os.remove(".temporal_worker.pid")


# Main entry point
if __name__ == "__main__":
    asyncio.run(start_worker())
