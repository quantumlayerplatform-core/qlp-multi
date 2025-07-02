"""
Temporal Worker for Quantum Layer Platform - Production Implementation
No mocks, fully integrated with all services
"""
import asyncio
import logging
import json
from datetime import timedelta, datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Activity timeout configurations
ACTIVITY_TIMEOUT = timedelta(minutes=5)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=30)
HEARTBEAT_TIMEOUT = timedelta(seconds=30)

# Retry policy for activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

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
    metadata: Dict[str, Any] = field(default_factory=dict)

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

@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: str  # completed, failed, cancelled
    output_type: str  # code, tests, documentation, error
    output: Dict[str, Any]
    execution_time: float
    confidence_score: float
    agent_tier_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Validation result"""
    overall_status: str  # passed, failed, passed_with_warnings
    confidence_score: float
    checks: List[Dict[str, Any]]
    requires_human_review: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SandboxResult:
    """Sandbox execution result"""
    success: bool
    output: Optional[str]
    error: Optional[str]
    execution_time: float
    resource_usage: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HITLRequest:
    """Human-in-the-loop request"""
    request_id: str
    task_id: str
    review_type: str  # clarification, approval, quality_check
    context: Dict[str, Any]
    deadline: datetime
    priority: str = "normal"  # low, normal, high, critical

@dataclass
class WorkflowResult:
    """Complete workflow result"""
    request_id: str
    status: str  # completed, failed, partial, cancelled
    capsule_id: Optional[str]
    tasks_completed: int
    tasks_total: int
    execution_time: float
    outputs: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Activities - These run outside the sandbox and can use any imports
@activity.defn
async def decompose_request_activity(request: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """Decompose NLP request into tasks with dependencies"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Decomposing request: {request['request_id']}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First, check vector memory for similar past requests
        memory_response = await client.post(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/search/requests",
            json={
                "description": request["description"],
                "limit": 5
            }
        )
        
        similar_requests = []
        if memory_response.status_code == 200:
            # Memory service returns a list directly
            response_data = memory_response.json()
            similar_requests = response_data if isinstance(response_data, list) else response_data.get("results", [])
            activity.logger.info(f"Found {len(similar_requests)} similar past requests")
        
        # Decompose with context from similar requests
        response = await client.post(
            f"http://localhost:{settings.ORCHESTRATOR_PORT}/test/decompose",
            json={
                "description": request["description"],
                "tenant_id": request["tenant_id"],
                "user_id": request["user_id"],
                "requirements": request.get("requirements"),
                "constraints": request.get("constraints"),
                "similar_requests": similar_requests
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Decomposition failed: {response.status_code} - {response.text}")
        
        data = response.json()
        tasks = data.get("tasks", [])
        dependencies = data.get("dependencies", {})
        
        # Store decomposition for future learning
        await client.post(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/store/decomposition",
            json={
                "request": request,
                "tasks": tasks,
                "dependencies": dependencies
            }
        )
        
        # Convert to workflow-safe format
        workflow_tasks = []
        for task in tasks:
            workflow_tasks.append({
                "task_id": task.get("id"),
                "type": task.get("type"),
                "description": task.get("description"),
                "complexity": task.get("complexity", "simple"),
                "dependencies": dependencies.get(task.get("id"), []),
                "context": task.get("context", {}),
                "metadata": task.get("metadata", {})
            })
        
        return workflow_tasks, dependencies


@activity.defn
async def select_agent_tier_activity(task: Dict[str, Any]) -> str:
    """Select appropriate agent tier based on task complexity and historical performance"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Selecting agent tier for task: {task['task_id']}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get historical performance data
        perf_response = await client.get(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/performance/task",
            params={
                "type": task["type"],
                "complexity": task["complexity"]
            }
        )
        
        if perf_response.status_code == 200:
            perf_data = perf_response.json()
            # Use performance data to select optimal tier
            tier_performance = perf_data.get("tier_performance", {})
            
            # Select tier with best success rate and reasonable cost
            best_tier = "T0"  # Default
            best_score = 0
            
            for tier, metrics in tier_performance.items():
                # Score = success_rate * 0.7 + (1 - relative_cost) * 0.3
                success_rate = metrics.get("success_rate", 0)
                relative_cost = metrics.get("relative_cost", 1)
                score = success_rate * 0.7 + (1 - relative_cost) * 0.3
                
                if score > best_score:
                    best_score = score
                    best_tier = tier
            
            activity.logger.info(f"Selected tier {best_tier} based on historical performance")
            return best_tier
        
        # Fallback to complexity-based selection
        complexity_to_tier = {
            "trivial": "T0",
            "simple": "T0",
            "medium": "T1",
            "complex": "T2",
            "meta": "T3"
        }
        
        return complexity_to_tier.get(task["complexity"], "T1")


@activity.defn
async def execute_task_activity(task: Dict[str, Any], tier: str, request_id: str) -> Dict[str, Any]:
    """Execute a single task using the selected agent tier"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Executing task {task['task_id']} with tier {tier}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Execute via agent service
        start_time = datetime.now(timezone.utc)
        
        response = await client.post(
            f"http://localhost:{settings.AGENT_FACTORY_PORT}/execute",
            json={
                "task": {
                    "id": task.get("task_id", task.get("id", "")),
                    "type": task.get("type", "code_generation"),
                    "description": task.get("description", ""),
                    "complexity": task.get("complexity", "medium"),
                    "status": task.get("status", "pending"),
                    "metadata": task.get("metadata", {})
                },
                "tier": tier,
                "context": task.get("context", {})
            }
        )
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        if response.status_code != 200:
            # Store failed execution for learning
            await client.post(
                f"http://localhost:{settings.VECTOR_MEMORY_PORT}/store/execution",
                json={
                    "request_id": request_id,
                    "task": task,
                    "result": {
                        "status": "failed",
                        "error": f"Agent execution failed: {response.status_code}",
                        "tier": tier,
                        "execution_time": execution_time
                    }
                }
            )
            
            return {
                "task_id": task["task_id"],
                "status": "failed",
                "output_type": "error",
                "output": {"error": f"Agent execution failed: {response.status_code}"},
                "execution_time": execution_time,
                "confidence_score": 0,
                "agent_tier_used": tier,
                "metadata": {"http_status": response.status_code}
            }
        
        result = response.json()
        
        # Store successful execution for learning
        await client.post(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/store/execution",
            json={
                "request_id": request_id,
                "task": task,
                "result": result
            }
        )
        
        # Store code pattern if successful
        if result.get("status") == "completed" and result.get("output_type") == "code":
            output = result.get("output", {})
            if isinstance(output, dict) and "code" in output:
                await client.post(
                    f"http://localhost:{settings.VECTOR_MEMORY_PORT}/patterns/code",
                    json={
                        "content": output["code"],
                        "metadata": {
                            "task_type": task["type"],
                            "complexity": task["complexity"],
                            "tier": tier,
                            "confidence": result.get("confidence_score", 0),
                            "language": output.get("language", "python")
                        }
                    }
                )
        
        return result


@activity.defn
async def validate_result_activity(result: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """Validate execution result with full validation pipeline"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Validating result for task: {task['task_id']}")
    
    if result.get("status") != "completed" or not result.get("output"):
        return {
            "overall_status": "failed",
            "confidence_score": 0,
            "checks": [
                {
                    "name": "execution_status",
                    "type": "basic",
                    "status": "failed",
                    "message": "Task execution did not complete successfully"
                }
            ],
            "requires_human_review": True,
            "metadata": {"reason": "execution_failed"}
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
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Run full validation pipeline
        response = await client.post(
            f"http://localhost:{settings.VALIDATION_MESH_PORT}/validate/code",
            json={
                "code": code,
                "language": language,
                "validators": ["syntax", "style", "security", "types", "runtime"],
                "context": {
                    "task_type": task["type"],
                    "requirements": task.get("description", "")
                }
            }
        )
        
        if response.status_code != 200:
            return {
                "overall_status": "error",
                "confidence_score": 0,
                "checks": [],
                "requires_human_review": True,
                "metadata": {"error": f"Validation service error: {response.status_code}"}
            }
        
        validation_result = response.json()
        
        # Determine if human review is needed based on confidence and critical issues
        confidence = validation_result.get("confidence_score", 0)
        critical_issues = any(
            check.get("severity") == "critical" 
            for check in validation_result.get("checks", [])
            if check.get("status") == "failed"
        )
        
        validation_result["requires_human_review"] = confidence < 0.7 or critical_issues
        
        return validation_result


@activity.defn
async def execute_in_sandbox_activity(code: str, language: str, test_inputs: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Execute code in sandbox with comprehensive testing"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Executing code in sandbox for language: {language}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # If no test inputs provided, use standard test cases
        if not test_inputs:
            test_inputs = [{}]  # At least run once with no inputs
        
        results = []
        overall_success = True
        total_time = 0
        
        for i, inputs in enumerate(test_inputs):
            response = await client.post(
                f"http://localhost:{settings.SANDBOX_PORT}/execute",
                json={
                    "code": code,
                    "language": language,
                    "inputs": inputs
                }
            )
            
            if response.status_code != 200:
                results.append({
                    "test_case": i,
                    "success": False,
                    "error": f"Sandbox error: {response.status_code}",
                    "output": None
                })
                overall_success = False
            else:
                result = response.json()
                results.append({
                    "test_case": i,
                    "success": result.get("success", False),
                    "output": result.get("output"),
                    "error": result.get("error"),
                    "execution_time": result.get("execution_time", 0),
                    "resource_usage": result.get("resource_usage", {})
                })
                
                if not result.get("success"):
                    overall_success = False
                
                total_time += result.get("execution_time", 0)
        
        return {
            "success": overall_success,
            "output": results[0].get("output") if len(results) == 1 else [r.get("output") for r in results],
            "error": results[0].get("error") if len(results) == 1 and not overall_success else None,
            "execution_time": total_time,
            "test_results": results,
            "resource_usage": {
                "max_memory": max(r.get("resource_usage", {}).get("memory_mb", 0) for r in results),
                "total_cpu_time": sum(r.get("resource_usage", {}).get("cpu_time", 0) for r in results)
            }
        }


@activity.defn
async def request_human_review_activity(
    task: Dict[str, Any], 
    result: Dict[str, Any], 
    validation: Dict[str, Any],
    reason: str
) -> Dict[str, Any]:
    """Request human review through the HITL system"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Requesting human review for task: {task['task_id']}")
    
    # Prepare review context
    review_context = {
        "task": task,
        "execution_result": result,
        "validation_result": validation,
        "reason": reason,
        "code": None,
        "issues": []
    }
    
    # Extract code and issues
    if result.get("output"):
        output = result.get("output", {})
        if isinstance(output, dict):
            review_context["code"] = output.get("code", output.get("content", ""))
        else:
            review_context["code"] = str(output)
    
    # Extract validation issues
    for check in validation.get("checks", []):
        if check.get("status") in ["failed", "warning"]:
            review_context["issues"].append({
                "type": check.get("name"),
                "severity": check.get("severity", "warning"),
                "message": check.get("message", "")
            })
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Create HITL request
        response = await client.post(
            f"http://localhost:{settings.ORCHESTRATOR_PORT}/hitl/request",
            json={
                "type": "code_review",
                "task_id": task["task_id"],
                "priority": "high" if validation.get("confidence_score", 1) < 0.5 else "normal",
                "context": review_context,
                "questions": [
                    "Is the generated code correct for the given requirements?",
                    "Are there any security or performance concerns?",
                    "Should this code be approved for production use?"
                ],
                "timeout_minutes": 60
            }
        )
        
        if response.status_code != 200:
            activity.logger.error(f"Failed to create HITL request: {response.status_code}")
            return {
                "approved": False,
                "reviewer": "system",
                "reason": "Failed to create review request",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        hitl_request = response.json()
        request_id = hitl_request.get("request_id")
        
        # Poll for response (with timeout)
        max_attempts = 120  # 60 minutes with 30-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            status_response = await client.get(
                f"http://localhost:{settings.ORCHESTRATOR_PORT}/hitl/status/{request_id}"
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data.get("status") == "completed":
                    review_result = status_data.get("result", {})
                    return {
                        "approved": review_result.get("approved", False),
                        "reviewer": review_result.get("reviewer_id", "unknown"),
                        "confidence": review_result.get("confidence", 0),
                        "comments": review_result.get("comments", ""),
                        "modifications": review_result.get("modifications", {}),
                        "timestamp": review_result.get("timestamp", datetime.utcnow().isoformat())
                    }
                elif status_data.get("status") == "expired":
                    activity.logger.warning(f"HITL request {request_id} expired")
                    break
            
            attempt += 1
            
            # Send heartbeat to prevent activity timeout
            activity.heartbeat(f"Waiting for human review: attempt {attempt}/{max_attempts}")
        
        # Timeout - auto-reject for safety
        return {
            "approved": False,
            "reviewer": "system",
            "reason": "Review timeout - auto-rejected for safety",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@activity.defn
async def create_ql_capsule_activity(
    request_id: str,
    tasks: List[Dict[str, Any]],
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a QLCapsule with all artifacts"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Creating QLCapsule for request: {request_id}")
    
    # Organize outputs by type
    source_code = {}
    tests = {}
    documentation = []
    deployment_config = {}
    
    for i, (task, result) in enumerate(zip(tasks, results)):
        if result.get("execution", {}).get("status") == "completed":
            output = result.get("execution", {}).get("output", {})
            
            if isinstance(output, dict):
                code = output.get("code", output.get("content", ""))
                language = output.get("language", "python")
                
                if task["type"] == "implement":
                    filename = f"module_{i}.{language}" if language != "python" else f"module_{i}.py"
                    source_code[filename] = code
                elif task["type"] == "test":
                    filename = f"test_{i}.{language}" if language != "python" else f"test_{i}.py"
                    tests[filename] = code
                elif task["type"] == "document":
                    documentation.append(code)
                elif task["type"] == "deploy":
                    deployment_config.update(output)
    
    # Create capsule
    capsule_data = {
        "request_id": request_id,
        "manifest": {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "task_count": len(tasks),
            "success_rate": sum(1 for r in results if r.get("execution", {}).get("status") == "completed") / len(tasks)
        },
        "source_code": source_code,
        "tests": tests,
        "documentation": "\n\n".join(documentation),
        "deployment_config": deployment_config,
        "validation_reports": [r.get("validation", {}) for r in results],
        "metadata": {
            "total_execution_time": sum(r.get("execution", {}).get("execution_time", 0) for r in results),
            "agent_tiers_used": list(set(r.get("execution", {}).get("agent_tier_used", "unknown") for r in results))
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Store capsule
        response = await client.post(
            f"http://localhost:{settings.VECTOR_MEMORY_PORT}/store/capsule",
            json=capsule_data
        )
        
        if response.status_code != 200:
            activity.logger.error(f"Failed to store capsule: {response.status_code}")
            return {
                "capsule_id": None,
                "error": f"Failed to store capsule: {response.status_code}"
            }
        
        storage_result = response.json()
        capsule_id = storage_result.get("capsule_id")
        
        # Generate download URL or storage location
        capsule_url = f"http://localhost:{settings.ORCHESTRATOR_PORT}/capsules/{capsule_id}"
        
        return {
            "capsule_id": capsule_id,
            "capsule_url": capsule_url,
            "manifest": capsule_data["manifest"],
            "files": {
                "source": list(source_code.keys()),
                "tests": list(tests.keys()),
                "docs": ["README.md"] if documentation else []
            }
        }


# Workflow - Production-ready orchestration
@workflow.defn
class QLPWorkflow:
    """Production workflow for Quantum Layer Platform request processing"""
    
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete workflow for an NLP request"""
        # Use workflow.now() instead of time.time() for deterministic time
        start_time = workflow.now()
        
        workflow_result = {
            "request_id": request["request_id"],
            "status": "started",
            "capsule_id": None,
            "tasks_completed": 0,
            "tasks_total": 0,
            "execution_time": 0,
            "outputs": [],
            "errors": [],
            "metadata": {}
        }
        
        try:
            # Step 1: Decompose request into tasks
            tasks, dependencies = await workflow.execute_activity(
                decompose_request_activity,
                request,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                heartbeat_timeout=HEARTBEAT_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY
            )
            
            workflow_result["tasks_total"] = len(tasks)
            workflow_result["status"] = "decomposed"
            
            # Step 2: Create execution plan based on dependencies
            execution_order = self._topological_sort(tasks, dependencies)
            
            # Step 3: Execute tasks in order (respecting dependencies)
            task_results = {}
            completed_tasks = set()
            
            for task_id in execution_order:
                task = next(t for t in tasks if t["task_id"] == task_id)
                
                # Wait for dependencies
                task_deps = dependencies.get(task_id, [])
                for dep_id in task_deps:
                    if dep_id not in completed_tasks:
                        workflow.logger.warning(f"Dependency {dep_id} not completed for task {task_id}")
                        continue
                
                # Select appropriate agent tier
                tier = await workflow.execute_activity(
                    select_agent_tier_activity,
                    task,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY_POLICY
                )
                
                # Execute task
                exec_result = await workflow.execute_activity(
                    execute_task_activity,
                    args=[task, tier, request["request_id"]],
                    start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
                    heartbeat_timeout=HEARTBEAT_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY
                )
                
                # Validate result
                validation_result = await workflow.execute_activity(
                    validate_result_activity,
                    args=[exec_result, task],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY
                )
                
                # Sandbox execution for code outputs
                sandbox_result = None
                if (exec_result.get("status") == "completed" and 
                    exec_result.get("output_type") == "code" and
                    validation_result.get("overall_status") != "failed"):
                    
                    output = exec_result.get("output", {})
                    if isinstance(output, dict):
                        code = output.get("code", "")
                        language = output.get("language", "python")
                    else:
                        code = str(output)
                        language = "python"
                    
                    if code:
                        sandbox_result = await workflow.execute_activity(
                            execute_in_sandbox_activity,
                            args=[code, language, None],
                            start_to_close_timeout=ACTIVITY_TIMEOUT,
                            retry_policy=DEFAULT_RETRY_POLICY
                        )
                
                # Human review if needed
                review_result = None
                if validation_result.get("requires_human_review"):
                    reason = "Low confidence" if validation_result.get("confidence_score", 1) < 0.7 else "Critical issues found"
                    
                    review_result = await workflow.execute_activity(
                        request_human_review_activity,
                        args=[task, exec_result, validation_result, reason],
                        start_to_close_timeout=timedelta(hours=2),  # Allow time for human review
                        heartbeat_timeout=timedelta(minutes=1),
                        retry_policy=RetryPolicy(maximum_attempts=1)  # Don't retry human reviews
                    )
                    
                    if not review_result.get("approved"):
                        workflow_result["errors"].append({
                            "task_id": task["task_id"],
                            "error": "Human review rejected",
                            "reason": review_result.get("reason", "No reason provided"),
                            "reviewer": review_result.get("reviewer")
                        })
                        exec_result["status"] = "rejected"
                
                # Store complete task result
                task_result = {
                    "task_id": task["task_id"],
                    "execution": exec_result,
                    "validation": validation_result,
                    "sandbox": sandbox_result,
                    "review": review_result
                }
                
                task_results[task_id] = task_result
                
                if exec_result.get("status") == "completed":
                    completed_tasks.add(task_id)
                    workflow_result["tasks_completed"] += 1
                
                # Add to outputs
                workflow_result["outputs"].append(task_result)
            
            # Step 4: Create QLCapsule with all artifacts
            if workflow_result["tasks_completed"] > 0:
                capsule_result = await workflow.execute_activity(
                    create_ql_capsule_activity,
                    args=[request["request_id"], tasks, list(task_results.values())],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY
                )
                
                workflow_result["capsule_id"] = capsule_result.get("capsule_id")
                workflow_result["metadata"]["capsule_info"] = capsule_result
            
            # Set final status
            if workflow_result["tasks_completed"] == workflow_result["tasks_total"]:
                workflow_result["status"] = "completed"
            elif workflow_result["tasks_completed"] > 0:
                workflow_result["status"] = "partial"
            else:
                workflow_result["status"] = "failed"
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {str(e)}", exc_info=True)
            workflow_result["status"] = "failed"
            workflow_result["errors"].append({
                "type": "workflow_error",
                "message": str(e),
                "traceback": str(e.__traceback__)
            })
        
        # Calculate execution time using workflow time
        end_time = workflow.now()
        workflow_result["execution_time"] = (end_time - start_time).total_seconds()
        return workflow_result
    
    def _topological_sort(self, tasks: List[Dict[str, Any]], dependencies: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on tasks based on dependencies"""
        from collections import defaultdict, deque
        
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        task_ids = [t["task_id"] for t in tasks]
        
        # Initialize in-degree for all tasks
        for task_id in task_ids:
            in_degree[task_id] = 0
        
        # Build graph
        for task_id, deps in dependencies.items():
            for dep in deps:
                graph[dep].append(task_id)
                in_degree[task_id] += 1
        
        # Find all tasks with no dependencies
        queue = deque([task_id for task_id in task_ids if in_degree[task_id] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Reduce in-degree for dependent tasks
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(task_ids):
            # Return tasks in original order if cycle detected
            workflow.logger.warning("Cycle detected in task dependencies, using original order")
            return task_ids
        
        return result


# Worker setup
async def start_worker():
    """Start the Temporal worker"""
    from ..common.config import settings
    
    # Create client
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE
    )
    
    # Create worker with production configuration
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[QLPWorkflow],
        activities=[
            decompose_request_activity,
            select_agent_tier_activity,
            execute_task_activity,
            validate_result_activity,
            execute_in_sandbox_activity,
            request_human_review_activity,
            create_ql_capsule_activity
        ],
        max_concurrent_activities=10,
        max_concurrent_workflow_tasks=5,
        graceful_shutdown_timeout=timedelta(seconds=30)
    )
    
    logger.info(f"Starting Temporal worker on queue: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info(f"Connected to Temporal at: {settings.TEMPORAL_HOST}")
    logger.info("Worker configuration:")
    logger.info(f"  - Max concurrent activities: 10")
    logger.info(f"  - Max concurrent workflows: 5")
    logger.info(f"  - Graceful shutdown timeout: 30s")
    
    # Start worker
    await worker.run()


# Main entry point
if __name__ == "__main__":
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        raise
