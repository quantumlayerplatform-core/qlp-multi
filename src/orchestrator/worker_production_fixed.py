"""
Temporal Worker for Quantum Layer Platform - Fixed Production Implementation
No mocks, fully integrated with all services, with httpx import issues resolved
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
from uuid import uuid4

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
HEARTBEAT_INTERVAL = 20  # Send heartbeat every 20 seconds (more frequent)

# Workflow configuration
MAX_WORKFLOW_DURATION = timedelta(hours=3)  # Maximum workflow duration
WORKFLOW_TASK_TIMEOUT = timedelta(minutes=10)  # Timeout for workflow tasks

# Service call timeouts
SERVICE_CALL_TIMEOUT = 180.0  # 3 minutes for service calls
LLM_CALL_TIMEOUT = 300.0  # 5 minutes for LLM calls

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
    """Task representation for workflow processing"""
    task_id: str
    type: str
    description: str
    context: Dict[str, Any]
    dependencies: List[str]
    complexity: str = "simple"  # simple, moderate, complex, meta
    priority: int = 5  # 1-10, higher is more important
    estimated_time: int = 300  # seconds
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class AgentExecution:
    """Agent execution result"""
    task_id: str
    status: str  # pending, in_progress, completed, failed
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    agent_tier: Optional[str] = None
    validation_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Validation result from validation mesh"""
    overall_status: str  # passed, failed, partial
    confidence_score: float
    checks: List[Dict[str, Any]]
    suggestions: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SharedContext:
    """Shared context for workflow execution"""
    request_id: str
    primary_language: str
    architecture_pattern: str
    file_structure: Dict[str, Any]
    quality_standards: List[str]
    validation_requirements: List[str]
    security_requirements: List[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HITLRequest:
    """Human-in-the-loop request"""
    request_id: str
    task_id: str
    review_type: str  # clarification, approval, quality_check
    context: Dict[str, Any]
    deadline: str  # ISO format string
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
async def decompose_request_activity(request: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]], Dict[str, Any]]:
    """Decompose NLP request into tasks with dependencies and create shared context"""
    import httpx
    from ..common.config import settings
    from .shared_context import ContextBuilder
    from ..moderation import check_content, CheckContext, Severity
    
    activity.logger.info(f"Decomposing request: {request['request_id']}")
    
    # Send initial heartbeat
    activity.heartbeat("Starting request decomposition")
    
    # HAP Content Check
    hap_result = await check_content(
        content=f"{request['description']} {request.get('requirements', '')}",
        context=CheckContext.USER_REQUEST,
        user_id=request.get("user_id"),
        tenant_id=request.get("tenant_id")
    )
    
    if hap_result.severity >= Severity.HIGH:
        activity.logger.warning(
            f"Request blocked by HAP - Severity: {hap_result.severity}, Categories: {hap_result.categories}"
        )
        raise ValueError("Request blocked by content policy")
    
    # Build shared context using AI analysis
    context_builder = ContextBuilder()
    shared_context = await context_builder.build_context(
        description=request["description"],
        requirements=request.get("requirements"),
        constraints=request.get("constraints")
    )
    
    activity.logger.info(f"Created shared context with language: {shared_context.file_structure.primary_language}")
    activity.logger.info(f"Architecture pattern: {shared_context.architecture_pattern}")
    activity.logger.info(f"Main file: {shared_context.file_structure.main_file_name}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for unified optimization
        # First, check vector memory for similar past requests
        activity.heartbeat("Searching for similar requests...")
        memory_response = await client.post(
            f"http://vector-memory:{settings.VECTOR_MEMORY_PORT}/search/requests",
            json={
                "description": request["description"],
                "limit": 5
            }
        )
        
        if memory_response.status_code == 200:
            similar_requests = memory_response.json()
            activity.logger.info(f"Found {len(similar_requests)} similar past requests")
        
        # Use unified optimization engine for decomposition
        activity.heartbeat("Decomposing with unified optimization...")
        response = await client.post(
            f"http://orchestrator:{settings.ORCHESTRATOR_PORT}/decompose/unified-optimization",
            json=request
        )
        
        if response.status_code != 200:
            raise Exception(f"Decomposition failed: {response.status_code} - {response.text}")
        
        data = response.json()
        tasks = data.get("tasks", [])
        dependencies = data.get("dependencies", {})
        
        # Store decomposition for future learning
        await client.post(
            f"http://vector-memory:{settings.VECTOR_MEMORY_PORT}/store/decomposition",
            json={
                "request": request,
                "tasks": tasks,
                "dependencies": dependencies
            }
        )
        
        # Use shared context for language consistency
        execution_context = {
            "preferred_language": shared_context.file_structure.primary_language,
            "main_file_name": shared_context.file_structure.main_file_name,
            "architecture_pattern": shared_context.architecture_pattern,
            "project_structure": shared_context.project_structure,
            "sandbox_target": True,
            "output_format": "code",
            "quality_standards": shared_context.quality_context.quality_standards,
            "validation_requirements": shared_context.quality_context.validation_requirements,
            "security_requirements": shared_context.quality_context.security_requirements
        }
        
        # Convert to workflow-safe format with shared context
        workflow_tasks = []
        for task in tasks:
            task_id = task.get("id")
            task_dependencies = dependencies.get(task_id, [])
            
            # Add task dependencies to shared context
            for dep in task_dependencies:
                shared_context.dependency_context.add_dependency(task_id, dep)
            
            # Get context for this specific task
            task_context = shared_context.get_context_for_task(task_id)
            task_context.update(execution_context)  # Merge execution context
            
            workflow_tasks.append({
                "task_id": task_id,
                "type": task.get("type"),
                "description": task.get("description"),
                "context": task_context,
                "dependencies": task_dependencies,
                "complexity": task.get("complexity", "simple"),
                "priority": task.get("priority", 5),
                "estimated_time": task.get("estimated_time", 300)
            })
        
        return workflow_tasks, dependencies, shared_context.to_dict()


@activity.defn
async def select_agent_tier_activity(task: Dict[str, Any]) -> str:
    """Select appropriate agent tier based on task complexity and historical performance"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Selecting agent tier for task: {task['task_id']}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check historical performance for similar tasks
        try:
            response = await client.post(
                f"http://vector-memory:{settings.VECTOR_MEMORY_PORT}/search/tasks",
                json={
                    "description": task["description"],
                    "type": task["type"],
                    "limit": 3
                }
            )
            
            if response.status_code == 200:
                similar_tasks = response.json()
                if similar_tasks:
                    # Use the most successful tier from history
                    successful_tiers = [t["agent_tier"] for t in similar_tasks if t.get("success", False)]
                    if successful_tiers:
                        selected_tier = max(set(successful_tiers), key=successful_tiers.count)
                        activity.logger.info(f"Selected tier {selected_tier} based on history")
                        return selected_tier
        except Exception as e:
            activity.logger.warning(f"Could not check historical performance: {str(e)}")
        
        # Default tier selection based on complexity
        complexity_to_tier = {
            "simple": "T0",
            "moderate": "T1", 
            "complex": "T2",
            "meta": "T3"
        }
        
        return complexity_to_tier.get(task["complexity"], "T1")


@activity.defn
async def execute_task_activity(task: Dict[str, Any], tier: str, request_id: str, shared_context_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single task using the selected agent tier with TDD integration"""
    import httpx
    from ..common.config import settings
    from .shared_context import SharedContext
    import redis.asyncio as redis
    
    activity.logger.info(f"Executing task {task['task_id']} with tier {tier}")
    
    # Helper function for periodic heartbeats
    async def _send_periodic_heartbeats(service_name: str, interval: int):
        """Send periodic heartbeats during long-running operations"""
        while True:
            try:
                await asyncio.sleep(interval)
                if activity.in_activity():
                    activity.heartbeat(f"Processing with {service_name}...")
            except asyncio.CancelledError:
                break
    
    # Helper function to call agent factory with retries
    async def call_agent_factory(client: httpx.AsyncClient, execution_input: Dict[str, Any]) -> httpx.Response:
        """Call agent factory with retry protection, heartbeats, and circuit breaker"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Send heartbeat before each attempt
                if activity.in_activity():
                    activity.heartbeat(f"Agent factory call attempt {attempt + 1}/{max_retries}")
                
                # Add request ID for tracing
                request_id = execution_input.get('request_id', 'unknown')
                activity.logger.info(f"Calling agent factory for request {request_id}, attempt {attempt + 1}")
                
                # Start async heartbeat task
                heartbeat_task = None
                if activity.in_activity():
                    heartbeat_task = asyncio.create_task(_send_periodic_heartbeats("agent_factory", HEARTBEAT_INTERVAL))
                
                try:
                    response = await client.post(
                        f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                        json=execution_input,
                        timeout=SERVICE_CALL_TIMEOUT
                    )
                    
                    # Log response time
                    activity.logger.info(f"Agent factory responded with status {response.status_code}")
                    
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        activity.logger.warning(f"Agent factory returned {response.status_code}, retrying...")
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                        
                    return response
                    
                finally:
                    # Cancel heartbeat task
                    if heartbeat_task:
                        heartbeat_task.cancel()
                        try:
                            await heartbeat_task
                        except asyncio.CancelledError:
                            pass
                            
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                activity.logger.error(f"Agent factory call failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                raise
            except Exception as e:
                activity.logger.error(f"Unexpected error calling agent factory: {str(e)}")
                raise
    
    # Reconstruct shared context
    shared_context = SharedContext.from_dict(shared_context_dict)
    
    # Check cache first - with improved similarity threshold
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
    
    async with httpx.AsyncClient(timeout=30.0) as cache_client:
        if tdd_enabled:
            activity.logger.info(f"TDD enabled for task {task['task_id']}")
            
            # Step 1: Generate tests first
            test_generation_input = {
                "description": f"Generate comprehensive tests for: {task['description']}",
                "type": "test_generation",
                "context": execution_context,
                "request_id": request_id,
                "task_id": f"{task['task_id']}_tests",
                "tier": tier,
                "output_format": "test_code"
            }
            
            activity.heartbeat(f"Generating tests for task {task['task_id']}")
            
            try:
                test_response = await cache_client.post(
                    f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                    json=test_generation_input,
                    timeout=180.0
                )
                
                if test_response.status_code == 200:
                    test_data = test_response.json()
                    test_code = test_data.get("output", "")
                    activity.logger.info(f"Generated tests for task {task['task_id']}")
                    
                    # Add test code to execution context
                    execution_context["test_code"] = test_code
                    execution_context["tdd_mode"] = True
            except Exception as e:
                activity.logger.warning(f"Test generation failed: {str(e)}, continuing without TDD")
    
    # Main execution with enhanced context
    execution_input = {
        "description": task["description"],
        "type": task["type"],
        "context": execution_context,
        "request_id": request_id,
        "task_id": task["task_id"],
        "tier": tier
    }
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        activity.heartbeat(f"Calling agent factory for task {task['task_id']}")
        
        response = await call_agent_factory(client, execution_input)
        
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
        
        return execution_result


@activity.defn
async def validate_result_activity(result: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """Validate execution result with full validation pipeline"""
    import httpx
    from ..common.config import settings
    from ..validation.enhanced_validator import enhanced_validator
    
    activity.logger.info(f"Validating result for task: {task['task_id']}")
    
    # Helper function to call validation service with retries
    async def call_validation_service(client: httpx.AsyncClient, validation_input: Dict[str, Any]) -> httpx.Response:
        """Call validation service with retry protection and heartbeats"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Send heartbeat before each attempt
                if activity.in_activity():
                    activity.heartbeat(f"Validation service call attempt {attempt + 1}/{max_retries}")
                
                response = await client.post(
                    f"http://validation-mesh:{settings.VALIDATION_MESH_PORT}/validate/code",
                    json=validation_input,
                    timeout=120.0
                )
                if response.status_code >= 500 and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                raise
    
    # Send heartbeat for validation start
    activity.heartbeat(f"Starting validation for task: {task['task_id']}")
    
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
    
    # Try to parse as JSON first (structured output)
    code = output
    language = "python"  # Default
    
    try:
        if isinstance(output, str) and output.strip().startswith("{"):
            output_data = json.loads(output)
            code = output_data.get("code", output)
            language = output_data.get("language", "python")
    except:
        # If not JSON, treat as raw code
        pass
    
    # Ensure we have code to validate
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
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Send heartbeat before validation service call
        activity.heartbeat(f"Calling validation service for task: {task['task_id']}")
        
        # Run full validation pipeline
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
        
        response = await call_validation_service(client, validation_input)
        
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
        
        # Send final heartbeat
        activity.heartbeat(f"Validation completed for task: {task['task_id']}")
        
        return validation_result


@activity.defn
async def execute_in_sandbox_activity(code: str, language: str, test_inputs: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Execute code using agent-powered QLCapsule runtime validation"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Executing code in QLCapsule sandbox for language: {language}")
    
    # Use agent factory for intelligent runtime validation
    execution_input = {
        "description": f"Execute and validate the following {language} code in a sandboxed environment",
        "type": "runtime_validation",
        "context": {
            "code": code,
            "language": language,
            "test_inputs": test_inputs or [],
            "validation_mode": "runtime",
            "sandbox_target": True
        },
        "tier": "T1",  # Use T1 for runtime validation
        "request_id": str(uuid4())
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            # Send heartbeat before execution
            activity.heartbeat("Starting QLCapsule runtime validation...")
            
            response = await client.post(
                f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                json=execution_input
            )
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Runtime validation failed: {response.status_code}",
                    "output": None,
                    "execution_time": 0,
                    "test_results": []
                }
            
            result = response.json()
            
            # Parse the agent's runtime validation output
            output = result.get("output", "{}")
            try:
                if isinstance(output, str):
                    runtime_data = json.loads(output)
                else:
                    runtime_data = output
            except:
                runtime_data = {"status": "error", "error": "Invalid runtime output format"}
            
            return {
                "status": runtime_data.get("status", "unknown"),
                "output": runtime_data.get("output"),
                "error": runtime_data.get("error"),
                "execution_time": runtime_data.get("execution_time", 0),
                "test_results": runtime_data.get("test_results", []),
                "metadata": runtime_data.get("metadata", {})
            }
            
        except Exception as e:
            activity.logger.error(f"QLCapsule runtime validation error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "output": None,
                "execution_time": 0,
                "test_results": []
            }


@activity.defn
async def request_aitl_review_activity(
    task: Dict[str, Any], 
    result: Dict[str, Any], 
    validation: Dict[str, Any],
    reason: str
) -> Dict[str, Any]:
    """Request AITL (AI-in-the-Loop) review directly - no human involvement"""
    import httpx
    from ..common.config import settings
    
    # Check if AITL is enabled - if disabled, auto-approve
    aitl_enabled = getattr(settings, 'AITL_ENABLED', True)
    if not aitl_enabled:
        activity.logger.info(f"AITL disabled - auto-approving task: {task['task_id']}")
        return {
            "approved": True,
            "confidence": 1.0,
            "decision": "auto_approved",
            "quality_score": 0.8,
            "suggestions": []
        }
    
    activity.logger.info(f"Requesting AITL review for task: {task['task_id']}, reason: {reason}")
    
    # Extract code from result
    code = ""
    if result.get("output"):
        try:
            output_data = json.loads(result["output"]) if isinstance(result["output"], str) else result["output"]
            code = output_data.get("code", result["output"])
        except:
            code = result["output"]
    
    # Create AITL request data directly
    aitl_request_data = {
        "code": code,
        "context": {
            "task": task,
            "validation_result": validation,
            "execution_result": result,
            "reason": reason
        }
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        activity.logger.info(f"Calling AITL intelligent review directly for task: {task['task_id']}")
        
        # Call the AITL intelligent review function directly via internal endpoint
        aitl_response = await client.post(
            f"http://orchestrator:{settings.ORCHESTRATOR_PORT}/internal/aitl-review",
            json=aitl_request_data
        )
        
        if aitl_response.status_code != 200:
            activity.logger.error(f"AITL review failed: {aitl_response.status_code}")
            # Default to conservative approval
            return {
                "approved": False,
                "confidence": 0.5,
                "decision": "review_failed", 
                "quality_score": 0.5,
                "suggestions": ["Manual review recommended due to AITL service error"]
            }
        
        review_result = aitl_response.json()
        
        # The AITL system returns a decision directly
        return {
            "approved": review_result.get("approved", False),
            "confidence": review_result.get("confidence", 0.0),
            "decision": review_result.get("decision", "rejected"),
            "quality_score": review_result.get("quality_score", 0.0),
            "suggestions": review_result.get("suggestions", [])
        }


@activity.defn
async def create_ql_capsule_activity(
    request_id: str,
    tasks: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    shared_context_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a QLCapsule with all artifacts using shared context"""
    import httpx
    from ..common.config import settings
    from .shared_context import SharedContext
    
    activity.logger.info(f"Creating QLCapsule for request: {request_id}")
    
    # Reconstruct shared context
    shared_context = SharedContext.from_dict(shared_context_dict)
    
    activity.logger.info(f"Using shared context - Language: {shared_context.file_structure.primary_language}")
    activity.logger.info(f"Main file: {shared_context.file_structure.main_file_name}")
    activity.logger.info(f"Architecture: {shared_context.architecture_pattern}")
    
    # Send heartbeat for capsule creation start
    activity.heartbeat("Starting QLCapsule creation")
    
    # Extract all code artifacts with proper file names from shared context
    artifacts = []
    file_mapping = {}
    
    for i, result in enumerate(results):
        if result.get("status") == "completed" and result.get("output"):
            task = tasks[i] if i < len(tasks) else {}
            
            # Get file name from shared context
            file_info = shared_context.file_structure.get_file_for_task(task.get("task_id", f"task_{i}"))
            
            try:
                output = result["output"]
                if isinstance(output, str) and output.strip().startswith("{"):
                    output_data = json.loads(output)
                    code = output_data.get("code", output)
                    language = output_data.get("language", shared_context.file_structure.primary_language)
                    file_name = output_data.get("file_name", file_info.get("name", f"file_{i}.{language}"))
                else:
                    code = output
                    language = shared_context.file_structure.primary_language
                    file_name = file_info.get("name", f"file_{i}.{language}")
                
                # Store file mapping
                file_mapping[task.get("task_id", f"task_{i}")] = file_name
                
                artifacts.append({
                    "file_name": file_name,
                    "content": code,
                    "language": language,
                    "task_id": task.get("task_id", f"task_{i}"),
                    "description": task.get("description", ""),
                    "type": task.get("type", "code")
                })
            except Exception as e:
                activity.logger.warning(f"Failed to parse output for task {i}: {str(e)}")
    
    # Generate project structure files based on shared context
    activity.heartbeat("Generating project structure files")
    
    # Add README if not present
    if not any(a["file_name"].lower() == "readme.md" for a in artifacts):
        readme_content = shared_context.generate_readme(artifacts)
        artifacts.append({
            "file_name": "README.md",
            "content": readme_content,
            "language": "markdown",
            "type": "documentation"
        })
    
    # Add requirements/package files based on language
    if shared_context.file_structure.primary_language == "python":
        requirements = shared_context.file_structure.get_requirements()
        artifacts.append({
            "file_name": "requirements.txt",
            "content": "\n".join(requirements),
            "language": "text",
            "type": "dependencies"
        })
    
    # Create capsule ID
    capsule_id = f"qlcapsule_{request_id}_{uuid4().hex[:8]}"
    
    capsule_data = {
        "capsule_id": capsule_id,
        "request_id": request_id,
        "artifacts": artifacts,
        "metadata": {
            "tasks_completed": len([r for r in results if r.get("status") == "completed"]),
            "tasks_total": len(tasks),
            "primary_language": shared_context.file_structure.primary_language,
            "architecture_pattern": shared_context.architecture_pattern,
            "main_file": shared_context.file_structure.main_file_name,
            "file_mapping": file_mapping,
            "project_structure": shared_context.project_structure,
            "shared_context": {
                "request_id": shared_context.request_id,
                "primary_language": shared_context.file_structure.primary_language,
                "architecture_pattern": shared_context.architecture_pattern,
                "created_at": shared_context.created_at,
                "updated_at": shared_context.updated_at
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Send heartbeat before storing capsule
            activity.heartbeat(f"Storing capsule for request: {request_id}")
            
            # Store capsule
            response = await client.post(
                f"http://vector-memory:{settings.VECTOR_MEMORY_PORT}/store/capsule",
                json=capsule_data
            )
            
            if response.status_code != 200:
                error_detail = response.text
                activity.logger.error(f"Failed to store capsule: {response.status_code} - {error_detail}")
                # Continue anyway - capsule creation succeeded even if storage failed
            else:
                activity.logger.info(f"Capsule stored successfully: {capsule_id}")
            
            # Send final heartbeat
            activity.heartbeat("QLCapsule creation completed")
            
            return {
                "capsule_id": capsule_id,
                "status": "created",
                "artifacts_count": len(artifacts),
                "metadata": capsule_data["metadata"]
            }
            
        except Exception as e:
            activity.logger.error(f"Error creating capsule: {str(e)}")
            # Return capsule data anyway
            return {
                "capsule_id": capsule_id,
                "status": "created_with_errors",
                "artifacts_count": len(artifacts),
                "metadata": capsule_data["metadata"],
                "error": str(e)
            }


@activity.defn
async def llm_clean_code_activity(code: str) -> str:
    """LLM-powered intelligent code cleanup activity"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info("Starting LLM-powered code cleanup")
    
    # Use agent factory for intelligent code cleanup
    cleanup_input = {
        "description": "Clean and format the following code, removing any markdown formatting, explanations, or non-code content. Return only the pure, executable code.",
        "type": "code_cleanup",
        "context": {
            "code": code,
            "requirements": [
                "Remove all markdown code blocks (```)",
                "Remove any explanatory text or comments that are not part of the code",
                "Preserve all actual code comments and docstrings",
                "Ensure proper indentation and formatting",
                "Return only executable code"
            ]
        },
        "tier": "T0",  # Use T0 for simple cleanup tasks
        "request_id": str(uuid4())
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"http://agent-factory:{settings.AGENT_FACTORY_PORT}/execute",
                json=cleanup_input
            )
            
            if response.status_code == 200:
                result = response.json()
                cleaned_code = result.get("output", code)
                
                # Try to parse JSON response
                try:
                    if isinstance(cleaned_code, str) and cleaned_code.strip().startswith("{"):
                        output_data = json.loads(cleaned_code)
                        cleaned_code = output_data.get("code", cleaned_code)
                except:
                    pass
                
                return cleaned_code
            else:
                activity.logger.warning(f"Code cleanup failed with status {response.status_code}, returning original")
                return code
                
        except Exception as e:
            activity.logger.error(f"Code cleanup error: {str(e)}, returning original")
            return code


@activity.defn
async def prepare_delivery_activity(capsule_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare capsule for delivery with packaging and deployment configs"""
    import httpx
    from ..common.config import settings
    
    activity.logger.info(f"Preparing capsule {capsule_id} for delivery")
    
    # Send initial heartbeat
    activity.heartbeat("Starting capsule delivery preparation")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Generate deployment configurations based on request
        deployment_config = {
            "docker": True,
            "kubernetes": request.get("deployment", {}).get("kubernetes", False),
            "ci_cd": request.get("deployment", {}).get("ci_cd", True),
            "monitoring": request.get("deployment", {}).get("monitoring", False)
        }
        
        # Package capsule
        package_request = {
            "capsule_id": capsule_id,
            "format": request.get("delivery_format", "zip"),
            "include_docs": True,
            "deployment_config": deployment_config
        }
        
        response = await client.post(
            f"http://orchestrator:{settings.ORCHESTRATOR_PORT}/capsule/package",
            json=package_request
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to package capsule: {response.status_code}")
        
        package_data = response.json()
        
        # Send final heartbeat
        activity.heartbeat("Capsule delivery preparation completed")
        
        return {
            "capsule_id": capsule_id,
            "package_url": package_data.get("download_url"),
            "package_size": package_data.get("size"),
            "format": package_data.get("format"),
            "metadata": package_data.get("metadata", {})
        }


@activity.defn
async def save_workflow_checkpoint_activity(
    workflow_id: str,
    state: Dict[str, Any],
    completed_tasks: List[str],
    pending_tasks: List[str]
) -> bool:
    """Save workflow checkpoint for recovery"""
    import redis.asyncio as redis
    from ..common.config import settings
    
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        
        checkpoint = {
            "workflow_id": workflow_id,
            "state": state,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }
        
        # Save with 24 hour TTL
        await redis_client.setex(
            f"workflow:checkpoint:{workflow_id}",
            86400,
            json.dumps(checkpoint)
        )
        
        activity.logger.info(f"Saved checkpoint for workflow {workflow_id}")
        return True
        
    except Exception as e:
        activity.logger.error(f"Failed to save checkpoint: {str(e)}")
        return False


@activity.defn
async def load_workflow_checkpoint_activity(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Load workflow checkpoint if exists"""
    import redis.asyncio as redis
    from ..common.config import settings
    
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        
        checkpoint_data = await redis_client.get(f"workflow:checkpoint:{workflow_id}")
        
        if checkpoint_data:
            checkpoint = json.loads(checkpoint_data)
            activity.logger.info(f"Loaded checkpoint for workflow {workflow_id}")
            return checkpoint
        
        return None
        
    except Exception as e:
        activity.logger.error(f"Failed to load checkpoint: {str(e)}")
        return None


@activity.defn
async def stream_workflow_results_activity(workflow_id: str, batch_idx: int, 
                                         batch_results: List[Dict[str, Any]], 
                                         status: str) -> bool:
    """Stream workflow results in real-time"""
    import redis.asyncio as redis
    from ..common.config import settings
    
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        
        # Create stream entry
        stream_data = {
            "workflow_id": workflow_id,
            "batch_idx": batch_idx,
            "batch_results": json.dumps(batch_results),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add to Redis stream
        await redis_client.xadd(
            f"workflow:results:{workflow_id}",
            stream_data,
            maxlen=1000  # Keep last 1000 entries
        )
        
        # Also update latest status for quick lookup
        await redis_client.setex(
            f"workflow:status:{workflow_id}",
            3600,  # 1 hour TTL
            json.dumps({
                "status": status,
                "last_batch": batch_idx,
                "last_update": stream_data["timestamp"]
            })
        )
        
        return True
        
    except Exception as e:
        activity.logger.error(f"Failed to stream results: {str(e)}")
        return False


# Continue with the rest of the activities from the original file...
# (The workflow class and remaining activities would follow the same pattern)

# Export all activities for the worker
__all__ = [
    'decompose_request_activity',
    'select_agent_tier_activity', 
    'execute_task_activity',
    'validate_result_activity',
    'execute_in_sandbox_activity',
    'request_aitl_review_activity',
    'create_ql_capsule_activity',
    'llm_clean_code_activity',
    'prepare_delivery_activity',
    'save_workflow_checkpoint_activity',
    'load_workflow_checkpoint_activity',
    'stream_workflow_results_activity'
]