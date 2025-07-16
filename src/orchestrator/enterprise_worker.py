"""
Enterprise-grade Temporal Worker for Quantum Layer Platform
Designed for unlimited scale, any language, any domain
"""
import asyncio
import logging
import json
import traceback
from datetime import timedelta, datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import time

# Import configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration lazily
_settings = None
def get_settings():
    global _settings
    if _settings is None:
        from common.config import Settings
        _settings = Settings()
    return _settings

settings = get_settings()

# Dynamic timeout configurations based on settings
ACTIVITY_TIMEOUT = timedelta(minutes=settings.WORKFLOW_ACTIVITY_TIMEOUT_MINUTES)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=settings.WORKFLOW_LONG_ACTIVITY_TIMEOUT_MINUTES)
HEARTBEAT_TIMEOUT = timedelta(minutes=settings.WORKFLOW_HEARTBEAT_TIMEOUT_MINUTES)
HEARTBEAT_INTERVAL = settings.WORKFLOW_HEARTBEAT_INTERVAL_SECONDS
MAX_WORKFLOW_DURATION = timedelta(hours=settings.WORKFLOW_MAX_DURATION_HOURS)
WORKFLOW_TASK_TIMEOUT = timedelta(minutes=10)

# Enterprise retry policy
ENTERPRISE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=settings.RETRY_INITIAL_INTERVAL_SECONDS),
    backoff_coefficient=settings.RETRY_BACKOFF_COEFFICIENT,
    maximum_interval=timedelta(minutes=settings.RETRY_MAX_INTERVAL_MINUTES),
    maximum_attempts=settings.RETRY_MAX_ATTEMPTS,
    non_retryable_error_types=["ValueError", "TypeError", "KeyError"]  # Don't retry logic errors
)

# Circuit breaker implementation
class CircuitBreaker:
    """Enterprise-grade circuit breaker for fault tolerance"""
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).seconds > self.recovery_timeout:
                self.state = "half-open"
                logger.info(f"Circuit breaker entering half-open state")
            else:
                raise Exception(f"Circuit breaker is open. Service unavailable.")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info(f"Circuit breaker closed after successful call")
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

# Global circuit breakers for services
agent_factory_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
)
validation_mesh_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
)
sandbox_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
)

# Resource monitor for dynamic scaling
class ResourceMonitor:
    """Monitor system resources for dynamic scaling"""
    @staticmethod
    def get_system_metrics():
        """Get current system resource usage"""
        import psutil  # Import inside method to avoid workflow restrictions
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "active_connections": len(psutil.net_connections()),
            "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
        }
    
    @staticmethod
    def calculate_optimal_batch_size():
        """Calculate optimal batch size based on system resources"""
        if not settings.ENABLE_DYNAMIC_SCALING:
            return settings.WORKFLOW_MAX_BATCH_SIZE
            
        metrics = ResourceMonitor.get_system_metrics()
        cpu = metrics["cpu_percent"]
        memory = metrics["memory_percent"]
        
        # Scale down if resources are constrained
        if cpu > settings.CPU_THRESHOLD_HIGH or memory > settings.MEMORY_THRESHOLD_HIGH:
            return max(settings.MIN_BATCH_SIZE, settings.WORKFLOW_MAX_BATCH_SIZE // 4)
        # Scale up if resources are available
        elif cpu < settings.CPU_THRESHOLD_LOW and memory < settings.MEMORY_THRESHOLD_LOW:
            return min(settings.MAX_BATCH_SIZE, settings.WORKFLOW_MAX_BATCH_SIZE * 2)
        # Normal operation
        else:
            return settings.WORKFLOW_MAX_BATCH_SIZE

# Metrics collector
class MetricsCollector:
    """Collect and export metrics for monitoring"""
    def __init__(self):
        self.metrics = {
            "tasks_started": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "total_execution_time": 0,
            "active_workflows": 0,
            "active_activities": 0
        }
        self.start_time = datetime.utcnow()
        
    def record_task_start(self):
        self.metrics["tasks_started"] += 1
        
    def record_task_completion(self, execution_time: float):
        self.metrics["tasks_completed"] += 1
        self.metrics["total_execution_time"] += execution_time
        
    def record_task_failure(self):
        self.metrics["tasks_failed"] += 1
        
    def record_task_retry(self):
        self.metrics["tasks_retried"] += 1
        
    def get_metrics_summary(self):
        """Get current metrics summary"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        return {
            **self.metrics,
            "uptime_seconds": uptime,
            "success_rate": self.metrics["tasks_completed"] / max(self.metrics["tasks_started"], 1),
            "average_execution_time": self.metrics["total_execution_time"] / max(self.metrics["tasks_completed"], 1),
            "system_metrics": ResourceMonitor.get_system_metrics()
        }

# Global metrics collector
metrics = MetricsCollector()

# Enhanced data classes for enterprise features
@dataclass
class WorkflowTask:
    """Enhanced workflow task with priority and metadata"""
    task_id: str
    type: str
    description: str
    complexity: str = "simple"
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = field(default=5)  # 1-10, higher is more important
    estimated_duration: Optional[int] = None  # Estimated duration in seconds
    retry_count: int = field(default=0)
    language: Optional[str] = None  # Target programming language
    
@dataclass
class TaskResult:
    """Enhanced task result with detailed metrics"""
    task_id: str
    status: str  # completed, failed, cancelled, timeout
    output_type: str  # code, tests, documentation, error
    output: Dict[str, Any]
    execution_time: float
    confidence_score: float
    agent_tier_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = field(default=0)
    error_details: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)

# Adaptive timeout calculator
def calculate_adaptive_timeout(task: WorkflowTask) -> timedelta:
    """Calculate timeout based on task complexity and type"""
    if not settings.ENABLE_ADAPTIVE_TIMEOUTS:
        return ACTIVITY_TIMEOUT
        
    base_timeouts = {
        "simple": 5,
        "medium": 15,
        "complex": 45,
        "very_complex": 120
    }
    
    # Get base timeout
    base_minutes = base_timeouts.get(task.complexity, 30)
    
    # Apply multipliers based on task type
    type_multipliers = {
        "implementation": 1.5,
        "testing": 1.2,
        "documentation": 0.8,
        "refactoring": 2.0,
        "optimization": 2.5,
        "architecture": 1.8
    }
    
    multiplier = type_multipliers.get(task.type, 1.0)
    
    # Consider estimated duration if provided
    if task.estimated_duration:
        estimated_minutes = task.estimated_duration / 60
        base_minutes = max(base_minutes, estimated_minutes * 1.2)  # Add 20% buffer
    
    # Apply retry penalty
    if task.retry_count > 0:
        base_minutes *= (1 + 0.5 * task.retry_count)  # 50% increase per retry
    
    final_minutes = int(base_minutes * multiplier)
    return timedelta(minutes=min(final_minutes, 180))  # Cap at 3 hours

# Enterprise-grade activity implementations
@activity.defn
async def analyze_requirements_activity(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze requirements and decompose into tasks with language detection"""
    import httpx  # Import inside activity to avoid workflow restrictions
    
    request_id = request_data.get("request_id", str(uuid4()))
    activity_info = activity.info()
    
    logger.info(f"Starting requirements analysis for request {request_id}")
    metrics.record_task_start()
    start_time = time.time()
    
    async def heartbeat_sender():
        """Send regular heartbeats"""
        while True:
            try:
                activity.heartbeat({"status": "analyzing", "progress": "in_progress"})
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
    
    heartbeat_task = asyncio.create_task(heartbeat_sender())
    
    try:
        # Initialize HTTP client with enterprise timeout
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            # Call orchestrator's decomposition endpoint
            response = await client.post(
                f"{settings.ORCHESTRATOR_URL}/decompose/unified-optimization",
                json={
                    "description": request_data.get("description"),
                    "requirements": request_data.get("requirements", {}),
                    "constraints": request_data.get("constraints", {}),
                    "metadata": {
                        "request_id": request_id,
                        "tenant_id": request_data.get("tenant_id"),
                        "user_id": request_data.get("user_id"),
                        "detect_language": settings.DETECT_LANGUAGE_FROM_REQUIREMENTS,
                        "supported_languages": settings.SUPPORTED_LANGUAGES
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Decomposition failed: {response.text}")
            
            result = response.json()
            
            # Extract detected language if available
            detected_language = result.get("metadata", {}).get("detected_language", "python")
            
            # Convert to WorkflowTask objects with enhanced metadata
            tasks = []
            for idx, task_data in enumerate(result.get("tasks", [])):
                task = WorkflowTask(
                    task_id=task_data.get("task_id", f"task-{idx+1}"),
                    type=task_data.get("type", "implementation"),
                    description=task_data.get("description", ""),
                    complexity=task_data.get("complexity", "medium"),
                    dependencies=task_data.get("dependencies", []),
                    context=task_data.get("context", {}),
                    metadata=task_data.get("metadata", {}),
                    priority=task_data.get("priority", 5),
                    estimated_duration=task_data.get("estimated_duration"),
                    language=task_data.get("language", detected_language)
                )
                tasks.append(task)
            
            execution_time = time.time() - start_time
            metrics.record_task_completion(execution_time)
            
            logger.info(f"Requirements analysis completed. Generated {len(tasks)} tasks in {execution_time:.2f}s")
            
            return {
                "tasks": [asdict(t) for t in tasks],
                "metadata": result.get("metadata", {}),
                "detected_language": detected_language,
                "execution_time": execution_time
            }
            
    except Exception as e:
        metrics.record_task_failure()
        logger.error(f"Requirements analysis failed: {str(e)}")
        raise
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

@activity.defn
async def execute_task_activity(task_data: Dict[str, Any], tier: str, request_id: str, 
                               shared_context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single task with enhanced error handling and monitoring"""
    import httpx  # Import inside activity to avoid workflow restrictions
    
    task = WorkflowTask(**task_data)
    activity_info = activity.info()
    
    logger.info(f"Executing task {task.task_id} with tier {tier}")
    metrics.record_task_start()
    start_time = time.time()
    
    # Send heartbeats
    async def heartbeat_sender():
        while True:
            try:
                heartbeat_data = {
                    "task_id": task.task_id,
                    "status": "executing",
                    "tier": tier,
                    "progress": "in_progress"
                }
                activity.heartbeat(heartbeat_data)
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
    
    heartbeat_task = asyncio.create_task(heartbeat_sender())
    
    try:
        # Calculate adaptive timeout
        timeout = calculate_adaptive_timeout(task)
        logger.info(f"Using adaptive timeout of {timeout.total_seconds()}s for task {task.task_id}")
        
        # Prepare execution input with language context
        execution_input = {
            "task_id": task.task_id,
            "description": task.description,
            "type": task.type,
            "context": {
                **task.context,
                **shared_context,
                "language": task.language,
                "supported_languages": settings.SUPPORTED_LANGUAGES
            },
            "metadata": {
                **task.metadata,
                "request_id": request_id,
                "tier": tier,
                "retry_count": task.retry_count,
                "priority": task.priority
            }
        }
        
        # Execute with circuit breaker
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout.total_seconds())) as client:
            response = await agent_factory_breaker.call(
                client.post,
                f"{settings.AGENT_FACTORY_URL}/execute",
                json={
                    "agent_tier": tier,
                    "execution_input": execution_input
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Agent execution failed: {response.text}")
            
            result = response.json()
            
            execution_time = time.time() - start_time
            metrics.record_task_completion(execution_time)
            
            # Create enhanced task result
            task_result = TaskResult(
                task_id=task.task_id,
                status="completed",
                output_type=result.get("output_type", "code"),
                output=result.get("output", {}),
                execution_time=execution_time,
                confidence_score=result.get("confidence_score", 0.8),
                agent_tier_used=tier,
                metadata={
                    **result.get("metadata", {}),
                    "language": task.language,
                    "resource_usage": ResourceMonitor.get_system_metrics()
                },
                retry_count=task.retry_count
            )
            
            logger.info(f"Task {task.task_id} completed successfully in {execution_time:.2f}s")
            return asdict(task_result)
            
    except asyncio.TimeoutError:
        metrics.record_task_failure()
        logger.error(f"Task {task.task_id} timed out after {timeout.total_seconds()}s")
        return asdict(TaskResult(
            task_id=task.task_id,
            status="timeout",
            output_type="error",
            output={"error": f"Task timed out after {timeout.total_seconds()}s"},
            execution_time=time.time() - start_time,
            confidence_score=0,
            agent_tier_used=tier,
            error_details=f"Timeout after {timeout.total_seconds()}s",
            retry_count=task.retry_count
        ))
    except Exception as e:
        metrics.record_task_failure()
        logger.error(f"Task {task.task_id} failed: {str(e)}\n{traceback.format_exc()}")
        return asdict(TaskResult(
            task_id=task.task_id,
            status="failed",
            output_type="error",
            output={"error": str(e)},
            execution_time=time.time() - start_time,
            confidence_score=0,
            agent_tier_used=tier,
            error_details=str(e),
            retry_count=task.retry_count
        ))
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

@activity.defn
async def validate_output_activity(task_result: Dict[str, Any], validation_level: str) -> Dict[str, Any]:
    """Validate task output with circuit breaker protection"""
    import httpx  # Import inside activity to avoid workflow restrictions
    
    task_id = task_result.get("task_id")
    logger.info(f"Validating output for task {task_id} with level {validation_level}")
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await validation_mesh_breaker.call(
                client.post,
                f"{settings.VALIDATION_MESH_URL}/validate",
                json={
                    "code": task_result.get("output", {}).get("code", ""),
                    "language": task_result.get("metadata", {}).get("language", "python"),
                    "task_type": task_result.get("output_type", "code"),
                    "validation_level": validation_level,
                    "metadata": task_result.get("metadata", {})
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Validation failed: {response.text}")
            
            return response.json()
            
    except Exception as e:
        logger.error(f"Validation failed for task {task_id}: {str(e)}")
        # Return a default validation result on failure
        return {
            "overall_status": "failed",
            "confidence_score": 0,
            "checks": [],
            "requires_human_review": True,
            "error": str(e)
        }

@activity.defn
async def create_capsule_activity(outputs: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Create an enterprise-grade capsule from task outputs"""
    import httpx  # Import inside activity to avoid workflow restrictions
    
    logger.info(f"Creating capsule for {len(outputs)} outputs")
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(
                f"{settings.ORCHESTRATOR_URL}/generate/robust-capsule",
                json={
                    "outputs": outputs,
                    "metadata": metadata,
                    "capsule_type": "enterprise",
                    "include_tests": True,
                    "include_documentation": True,
                    "include_ci_cd": True,
                    "language": metadata.get("detected_language", "python")
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Capsule creation failed: {response.text}")
            
            return response.json()
            
    except Exception as e:
        logger.error(f"Capsule creation failed: {str(e)}")
        raise

@activity.defn
async def push_to_github_activity(capsule_id: str, repo_config: Dict[str, Any]) -> Dict[str, Any]:
    """Push capsule to GitHub with enterprise structure"""
    import httpx  # Import inside activity to avoid workflow restrictions
    
    logger.info(f"Pushing capsule {capsule_id} to GitHub")
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(
                f"{settings.ORCHESTRATOR_URL}/api/enterprise/github-push",
                json={
                    "capsule_id": capsule_id,
                    **repo_config
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"GitHub push failed: {response.text}")
            
            return response.json()
            
    except Exception as e:
        logger.error(f"GitHub push failed: {str(e)}")
        raise

# Enterprise Workflow Implementation
@workflow.defn
class QuantumLayerEnterpriseWorkflow:
    """Enterprise-grade workflow with unlimited scale and fault tolerance"""
    
    def __init__(self):
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.shared_context: Dict[str, Any] = {}
        
    @workflow.run
    async def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the enterprise workflow"""
        workflow_start_time = workflow.now()
        request_id = request.get("request_id", str(uuid4()))
        
        workflow.logger.info(f"Starting enterprise workflow for request {request_id}")
        
        try:
            # Step 1: Analyze requirements and decompose into tasks
            decomposition_result = await workflow.execute_activity(
                analyze_requirements_activity,
                request,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=ENTERPRISE_RETRY_POLICY
            )
            
            tasks = decomposition_result["tasks"]
            detected_language = decomposition_result.get("detected_language", "python")
            self.shared_context = {
                "language": detected_language,
                "project_type": decomposition_result.get("metadata", {}).get("project_type", "application"),
                "framework": decomposition_result.get("metadata", {}).get("framework"),
                "requirements": request.get("requirements", {})
            }
            
            workflow.logger.info(f"Decomposed into {len(tasks)} tasks. Detected language: {detected_language}")
            
            # Step 2: Build dependency graph and execution plan
            dependency_graph = self._build_dependency_graph(tasks)
            execution_batches = self._create_parallel_execution_batches(tasks, dependency_graph)
            
            workflow.logger.info(f"Created {len(execution_batches)} execution batches")
            
            # Step 3: Execute tasks in parallel batches
            all_results = []
            for batch_idx, batch in enumerate(execution_batches):
                workflow.logger.info(f"Executing batch {batch_idx + 1}/{len(execution_batches)} with {len(batch)} tasks")
                
                # Get optimal batch size based on system resources
                optimal_batch_size = ResourceMonitor.calculate_optimal_batch_size()
                
                # Split large batches if needed
                sub_batches = [batch[i:i + optimal_batch_size] for i in range(0, len(batch), optimal_batch_size)]
                
                for sub_batch in sub_batches:
                    batch_results = await self._execute_task_batch(sub_batch, request_id)
                    all_results.extend(batch_results)
                    
                    # Update shared context with results
                    for result in batch_results:
                        if result["status"] == "completed":
                            self._update_shared_context(result)
            
            # Step 4: Create enterprise capsule
            capsule_result = await workflow.execute_activity(
                create_capsule_activity,
                args=[all_results, {
                    "request_id": request_id,
                    "language": detected_language,
                    "shared_context": self.shared_context,
                    "tenant_id": request.get("tenant_id"),
                    "user_id": request.get("user_id")
                }],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=ENTERPRISE_RETRY_POLICY
            )
            
            capsule_id = capsule_result.get("capsule_id")
            workflow.logger.info(f"Created capsule {capsule_id}")
            
            # Step 5: Push to GitHub if requested
            github_result = None
            if request.get("push_to_github", False):
                github_result = await workflow.execute_activity(
                    push_to_github_activity,
                    args=[capsule_id, {
                        "repo_name": request.get("repo_name", f"qlp-{request_id[:8]}"),
                        "repo_description": request.get("description", "Generated by Quantum Layer Platform"),
                        "private": request.get("private_repo", False),
                        "branch": request.get("branch", settings.GITHUB_DEFAULT_BRANCH)
                    }],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=ENTERPRISE_RETRY_POLICY
                )
            
            # Calculate final metrics
            execution_time = (workflow.now() - workflow_start_time).total_seconds()
            success_count = len([r for r in all_results if r["status"] == "completed"])
            
            return {
                "request_id": request_id,
                "status": "completed",
                "capsule_id": capsule_id,
                "tasks_total": len(tasks),
                "tasks_completed": success_count,
                "success_rate": success_count / len(tasks) if tasks else 0,
                "execution_time": execution_time,
                "detected_language": detected_language,
                "outputs": all_results,
                "github": github_result,
                "metrics": metrics.get_metrics_summary(),
                "metadata": {
                    "shared_context": self.shared_context,
                    "system_metrics": ResourceMonitor.get_system_metrics()
                }
            }
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {str(e)}\n{traceback.format_exc()}")
            raise
    
    def _build_dependency_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependency graph from tasks"""
        graph = {}
        for task in tasks:
            task_id = task["task_id"]
            dependencies = task.get("dependencies", [])
            graph[task_id] = dependencies
        return graph
    
    def _create_parallel_execution_batches(self, tasks: List[Dict[str, Any]], 
                                         dependency_graph: Dict[str, List[str]]) -> List[List[Dict[str, Any]]]:
        """Create optimized execution batches considering dependencies and priorities"""
        batches = []
        remaining_tasks = {task["task_id"]: task for task in tasks}
        
        while remaining_tasks:
            # Find tasks with no pending dependencies
            ready_tasks = []
            for task_id, task in remaining_tasks.items():
                dependencies = dependency_graph.get(task_id, [])
                if all(dep in self.completed_tasks for dep in dependencies):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # Handle circular dependencies
                workflow.logger.warning("Circular dependency detected, forcing execution")
                ready_tasks = list(remaining_tasks.values())[:1]
            
            # Sort by priority (higher first)
            ready_tasks.sort(key=lambda t: t.get("priority", 5), reverse=True)
            
            # Create batch
            batch = ready_tasks
            batches.append(batch)
            
            # Mark as completed for dependency resolution
            for task in batch:
                self.completed_tasks.add(task["task_id"])
                del remaining_tasks[task["task_id"]]
        
        return batches
    
    async def _execute_task_batch(self, batch: List[Dict[str, Any]], request_id: str) -> List[Dict[str, Any]]:
        """Execute a batch of tasks in parallel with intelligent retry"""
        activities = []
        
        for task in batch:
            # Determine tier based on complexity
            tier = self._determine_tier(task)
            
            # Create activity with retry
            activity_future = workflow.execute_activity(
                execute_task_activity,
                args=[task, tier, request_id, self.shared_context],
                start_to_close_timeout=calculate_adaptive_timeout(WorkflowTask(**task)),
                retry_policy=ENTERPRISE_RETRY_POLICY,
                heartbeat_timeout=HEARTBEAT_TIMEOUT
            )
            activities.append((task, activity_future))
        
        # Wait for all activities with individual error handling
        results = []
        for task, future in activities:
            try:
                result = await future
                
                # Validate if successful
                if result["status"] == "completed":
                    validation_result = await workflow.execute_activity(
                        validate_output_activity,
                        args=[result, "comprehensive"],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=ENTERPRISE_RETRY_POLICY
                    )
                    result["validation"] = validation_result
                
                results.append(result)
                self.task_results[task["task_id"]] = result
                
            except Exception as e:
                workflow.logger.error(f"Task {task['task_id']} failed: {str(e)}")
                # Record failure but continue with other tasks
                failed_result = {
                    "task_id": task["task_id"],
                    "status": "failed",
                    "output_type": "error",
                    "output": {"error": str(e)},
                    "execution_time": 0,
                    "confidence_score": 0,
                    "agent_tier_used": "unknown",
                    "error_details": str(e)
                }
                results.append(failed_result)
                self.failed_tasks.add(task["task_id"])
        
        return results
    
    def _determine_tier(self, task: Dict[str, Any]) -> str:
        """Intelligently determine agent tier based on task complexity and type"""
        complexity = task.get("complexity", "medium")
        task_type = task.get("type", "implementation")
        priority = task.get("priority", 5)
        
        # High priority tasks get better tiers
        if priority >= 8:
            return "T2"
        
        # Map complexity and type to tiers
        if complexity == "simple":
            return "T0"
        elif complexity == "medium":
            return "T1"
        elif complexity == "complex":
            return "T2"
        elif complexity == "very_complex":
            return "T3"
        
        # Default based on type
        type_tier_map = {
            "documentation": "T0",
            "testing": "T1",
            "implementation": "T1",
            "refactoring": "T2",
            "architecture": "T2",
            "optimization": "T3"
        }
        
        return type_tier_map.get(task_type, "T1")
    
    def _update_shared_context(self, result: Dict[str, Any]):
        """Update shared context with task results"""
        # Extract useful information from completed tasks
        if result.get("output_type") == "code":
            output = result.get("output", {})
            if "imports" in output:
                self.shared_context.setdefault("common_imports", set()).update(output["imports"])
            if "functions" in output:
                self.shared_context.setdefault("defined_functions", []).extend(output["functions"])
            if "classes" in output:
                self.shared_context.setdefault("defined_classes", []).extend(output["classes"])

# Create and start the enterprise worker
async def main():
    """Start the enterprise Temporal worker"""
    logger.info("Starting Quantum Layer Enterprise Worker")
    
    # Create Temporal client
    client = await Client.connect(settings.TEMPORAL_SERVER)
    
    # Create worker with enterprise configuration
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[QuantumLayerEnterpriseWorkflow],
        activities=[
            analyze_requirements_activity,
            execute_task_activity,
            validate_output_activity,
            create_capsule_activity,
            push_to_github_activity
        ],
        max_concurrent_activities=settings.WORKFLOW_MAX_CONCURRENT_ACTIVITIES,
        max_concurrent_workflow_tasks=settings.WORKFLOW_MAX_CONCURRENT_WORKFLOWS,
        graceful_shutdown_timeout=timedelta(seconds=30)
    )
    
    # Log startup configuration
    logger.info(f"Worker Configuration:")
    logger.info(f"  Max Concurrent Activities: {settings.WORKFLOW_MAX_CONCURRENT_ACTIVITIES}")
    logger.info(f"  Max Concurrent Workflows: {settings.WORKFLOW_MAX_CONCURRENT_WORKFLOWS}")
    logger.info(f"  Max Batch Size: {settings.WORKFLOW_MAX_BATCH_SIZE}")
    logger.info(f"  Dynamic Scaling: {settings.ENABLE_DYNAMIC_SCALING}")
    logger.info(f"  Circuit Breaker: {settings.CIRCUIT_BREAKER_ENABLED}")
    logger.info(f"  Adaptive Timeouts: {settings.ENABLE_ADAPTIVE_TIMEOUTS}")
    
    # Start metrics reporting
    async def report_metrics():
        while True:
            await asyncio.sleep(60)  # Report every minute
            summary = metrics.get_metrics_summary()
            logger.info(f"Metrics Summary: {json.dumps(summary, indent=2)}")
    
    metrics_task = asyncio.create_task(report_metrics())
    
    try:
        logger.info("Enterprise worker started successfully")
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
    finally:
        metrics_task.cancel()
        logger.info("Worker stopped")

if __name__ == "__main__":
    asyncio.run(main())