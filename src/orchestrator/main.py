"""
Meta-Orchestrator Service
Coordinates the entire system, decomposes requests, and manages execution flow.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import asyncio
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.common.models import (
    ExecutionRequest,
    ExecutionPlan,
    Task,
    TaskResult,
    AgentTier,
    ValidationReport,
    QLCapsule,
    HITLRequest,
    HITLResponse
)
from src.common.config import settings
from src.memory.client import VectorMemoryClient
from src.agents.client import AgentFactoryClient
from src.validation.client import ValidationMeshClient

logger = structlog.get_logger()

app = FastAPI(title="Quantum Layer Platform Meta-Orchestrator", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize clients
# Use Azure OpenAI if configured, otherwise fall back to OpenAI
if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
    from openai import AsyncAzureOpenAI
    openai_client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )
    logger.info(f"Azure OpenAI client initialized", endpoint=settings.AZURE_OPENAI_ENDPOINT)
else:
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    logger.info("OpenAI client initialized")
    
anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
logger.info("Anthropic client initialized")
memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
agent_client = AgentFactoryClient(settings.AGENT_FACTORY_URL)
validation_client = ValidationMeshClient(settings.VALIDATION_MESH_URL)

# In-memory storage for HITL requests (in production, use a database)
hitl_requests: Dict[str, Dict[str, Any]] = {}


@dataclass
class DecompositionResult:
    """Result of decomposing an NLP request into tasks"""
    tasks: List[Task]
    dependencies: Dict[str, List[str]]  # task_id -> [dependency_ids]
    metadata: Dict[str, Any]


class MetaOrchestrator:
    """Main orchestration engine for the platform"""
    
    def __init__(self):
        self.openai = openai_client
        self.anthropic = anthropic_client
        self.memory = memory_client
        self.agents = agent_client
        self.validation = validation_client
        
    async def decompose_request(self, request: ExecutionRequest) -> DecompositionResult:
        """Decompose NLP request into atomic tasks using LLM"""
        logger.info("Decomposing request", request_id=request.id)
        
        # Search for similar past requests
        similar_requests = await self.memory.search_similar_requests(
            request.description,
            limit=5
        )
        
        # Build context from past executions
        context = self._build_decomposition_context(similar_requests)
        
        # Use LLM to decompose
        system_prompt = """You are an expert at decomposing software development requests into atomic tasks.
Given a user request, break it down into specific, executable tasks.

Output a JSON structure with:
- tasks: array of task objects with fields:
  - id: string (unique identifier, e.g., "task-1", "task-2")
  - type: string (one of: code_generation, test_creation, documentation, validation, deployment)
  - description: string (clear description of what needs to be done)
  - estimated_complexity: string (one of: trivial, simple, medium, complex, meta)
- dependencies: object mapping task_id to array of dependency task_ids
- metadata: any additional context

IMPORTANT: All id and estimated_complexity values MUST be strings, not numbers!

Example:
{
  "tasks": [
    {
      "id": "task-1",
      "type": "code_generation",
      "description": "Create main function",
      "estimated_complexity": "simple"
    }
  ],
  "dependencies": {},
  "metadata": {}
}"""
        
        # Use deployment name for Azure OpenAI, model name for OpenAI
        model = settings.AZURE_OPENAI_DEPLOYMENT_NAME if settings.AZURE_OPENAI_ENDPOINT else "gpt-3.5-turbo"
        
        response = await self.openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.description}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            timeout=45.0  # Add explicit timeout
        )
        
        decomposition = json.loads(response.choices[0].message.content)
        
        # Convert to Task objects
        tasks = []
        for task_data in decomposition["tasks"]:
            # Ensure ID is a string
            task_id = task_data.get("id", str(uuid4()))
            if not isinstance(task_id, str):
                task_id = str(task_id)
            
            # Ensure complexity is a string
            complexity = task_data.get("estimated_complexity", "medium")
            if not isinstance(complexity, str):
                complexity = str(complexity)
            
            task = Task(
                id=task_id,
                type=task_data["type"],
                description=task_data["description"],
                complexity=complexity,
                metadata=task_data.get("metadata", {})
            )
            tasks.append(task)
        
        # Store decomposition for future learning
        try:
            await self.memory.store_decomposition(request, tasks, decomposition["dependencies"])
        except Exception as e:
            logger.warning("Failed to store decomposition", error=str(e))
        
        return DecompositionResult(
            tasks=tasks,
            dependencies=decomposition["dependencies"],
            metadata=decomposition.get("metadata", {})
        )
    
    def _build_decomposition_context(self, similar_requests: List[Dict]) -> List[Dict]:
        """Build context from similar past requests"""
        context = []
        for req in similar_requests:
            context.append({
                "request": req["description"],
                "tasks": req["tasks"],
                "success_rate": req.get("success_rate", "unknown")
            })
        return context
    
    async def create_execution_plan(self, decomposition: DecompositionResult) -> ExecutionPlan:
        """Create an optimized execution plan from decomposed tasks"""
        logger.info("Creating execution plan", task_count=len(decomposition.tasks))
        
        # Analyze task complexity and assign agent tiers
        task_assignments = {}
        for task in decomposition.tasks:
            tier = await self._determine_agent_tier(task)
            task_assignments[task.id] = tier
        
        # Optimize execution order based on dependencies
        execution_order = self._topological_sort(
            decomposition.tasks,
            decomposition.dependencies
        )
        
        # Create plan
        plan = ExecutionPlan(
            id=str(uuid4()),
            request_id="",  # Will be set by caller
            tasks=decomposition.tasks,
            dependencies=decomposition.dependencies,
            execution_order=execution_order,
            task_assignments=task_assignments,
            estimated_duration=self._estimate_duration(decomposition.tasks),
            metadata=decomposition.metadata
        )
        
        return plan
    
    async def _determine_agent_tier(self, task: Task) -> AgentTier:
        """Determine optimal agent tier for a task"""
        # Check historical performance
        past_performance = await self.memory.get_task_performance(
            task_type=task.type,
            complexity=task.complexity
        )
        
        if past_performance:
            # Use the tier with best success rate
            return past_performance["optimal_tier"]
        
        # Default mapping based on complexity
        complexity_to_tier = {
            "trivial": AgentTier.T0,
            "simple": AgentTier.T0,
            "medium": AgentTier.T1,
            "complex": AgentTier.T2,
            "meta": AgentTier.T3
        }
        
        return complexity_to_tier.get(task.complexity, AgentTier.T1)
    
    def _topological_sort(self, tasks: List[Task], dependencies: Dict[str, List[str]]) -> List[str]:
        """Topological sort for task execution order"""
        # Build adjacency list
        graph = {task.id: [] for task in tasks}
        in_degree = {task.id: 0 for task in tasks}
        
        for task_id, deps in dependencies.items():
            for dep in deps:
                graph[dep].append(task_id)
                in_degree[task_id] += 1
        
        # Kahn's algorithm
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(tasks):
            raise ValueError("Circular dependency detected in task graph")
        
        return result
    
    def _estimate_duration(self, tasks: List[Task]) -> int:
        """Estimate total execution duration in seconds"""
        # Simple estimation based on task count and complexity
        complexity_weights = {
            "trivial": 10,
            "simple": 30,
            "medium": 120,
            "complex": 300,
            "meta": 600
        }
        
        total = 0
        for task in tasks:
            total += complexity_weights.get(task.complexity, 60)
        
        return total


# Temporal Workflow Definition
@workflow.defn
class QLPExecutionWorkflow:
    """Main execution workflow for QLP"""
    
    @workflow.run
    async def run(self, request: ExecutionRequest) -> QLCapsule:
        """Execute the complete workflow"""
        # Initialize orchestrator
        orchestrator = MetaOrchestrator()
        
        # Step 1: Decompose request
        decomposition = await workflow.execute_activity(
            decompose_request_activity,
            request,
            start_to_close_timeout=datetime.timedelta(minutes=5)
        )
        
        # Step 2: Create execution plan
        plan = await workflow.execute_activity(
            create_plan_activity,
            decomposition,
            start_to_close_timeout=datetime.timedelta(minutes=2)
        )
        
        # Step 3: Get human approval if needed
        if plan.estimated_duration > 300:  # 5 minutes
            approval = await workflow.wait_for_signal("human_approval")
            if not approval:
                raise Exception("Execution plan rejected by user")
        
        # Step 4: Execute tasks
        results = {}
        for task_id in plan.execution_order:
            task = next(t for t in plan.tasks if t.id == task_id)
            
            # Wait for dependencies
            deps_ready = all(dep in results for dep in plan.dependencies.get(task_id, []))
            if not deps_ready:
                await workflow.wait_condition(
                    lambda: all(dep in results for dep in plan.dependencies.get(task_id, []))
                )
            
            # Execute task
            result = await workflow.execute_activity(
                execute_task_activity,
                {
                    "task": task,
                    "tier": plan.task_assignments[task_id],
                    "context": {dep: results[dep] for dep in plan.dependencies.get(task_id, [])}
                },
                start_to_close_timeout=datetime.timedelta(minutes=30)
            )
            
            results[task_id] = result
        
        # Step 5: Validate results
        validation_report = await workflow.execute_activity(
            validate_results_activity,
            results,
            start_to_close_timeout=datetime.timedelta(minutes=10)
        )
        
        # Step 6: Package into QLCapsule
        capsule = await workflow.execute_activity(
            create_capsule_activity,
            {
                "request": request,
                "plan": plan,
                "results": results,
                "validation": validation_report
            },
            start_to_close_timeout=datetime.timedelta(minutes=5)
        )
        
        return capsule


# Activity implementations
@activity.defn
async def decompose_request_activity(request: ExecutionRequest) -> DecompositionResult:
    orchestrator = MetaOrchestrator()
    return await orchestrator.decompose_request(request)


@activity.defn
async def create_plan_activity(decomposition: DecompositionResult) -> ExecutionPlan:
    orchestrator = MetaOrchestrator()
    return await orchestrator.create_execution_plan(decomposition)


@activity.defn
async def execute_task_activity(params: Dict[str, Any]) -> TaskResult:
    # Delegate to agent factory
    result = await agent_client.execute_task(
        task=params["task"],
        tier=params["tier"],
        context=params["context"]
    )
    return result


@activity.defn
async def validate_results_activity(results: Dict[str, TaskResult]) -> ValidationReport:
    # Delegate to validation mesh
    report = await validation_client.validate_execution(results)
    return report


@activity.defn
async def create_capsule_activity(params: Dict[str, Any]) -> QLCapsule:
    # Check if we should use enhanced capsule generation
    use_enhanced = params.get("use_enhanced", True)
    
    if use_enhanced:
        try:
            # Use the enhanced capsule generator
            from src.orchestrator.enhanced_capsule import EnhancedCapsuleGenerator
            generator = EnhancedCapsuleGenerator()
            
            # Convert params to request format
            request = params["request"]
            capsule = await generator.generate_capsule(request, use_advanced=True)
            
            # Update with execution results
            capsule.validation_report = params["validation"]
            capsule.metadata.update({
                "execution_duration": _calculate_duration(params),
                "agent_tiers_used": list(set(params["plan"].task_assignments.values()))
            })
            
        except Exception as e:
            logger.warning(f"Enhanced capsule generation failed: {e}, falling back to basic")
            use_enhanced = False
    
    if not use_enhanced:
        # Fallback to basic capsule generation
        capsule = QLCapsule(
            id=str(uuid4()),
            request_id=params["request"].id,
            source_code=_extract_source_code(params["results"]),
            tests=_extract_tests(params["results"]),
            documentation=_generate_documentation(params),
            validation_report=params["validation"],
            deployment_config=_generate_deployment_config(params),
            metadata={
                "created_at": datetime.utcnow().isoformat(),
                "execution_duration": _calculate_duration(params),
                "agent_tiers_used": list(set(params["plan"].task_assignments.values()))
            }
        )
    
    # Store capsule
    await memory_client.store_capsule(capsule)
    
    return capsule


def _extract_source_code(results: Dict[str, TaskResult]) -> Dict[str, str]:
    """Extract source code from task results"""
    code_files = {}
    for task_id, result in results.items():
        if result.output_type == "code":
            code_files.update(result.output)
    return code_files


def _extract_tests(results: Dict[str, TaskResult]) -> Dict[str, str]:
    """Extract test files from task results"""
    test_files = {}
    for task_id, result in results.items():
        if result.output_type == "tests":
            test_files.update(result.output)
    return test_files


def _generate_documentation(params: Dict[str, Any]) -> str:
    """Generate comprehensive documentation"""
    # This would use an LLM to generate docs based on the code
    return "# Generated Documentation\n\nTODO: Implement documentation generation"


def _generate_deployment_config(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate deployment configuration"""
    return {
        "kubernetes": {
            "manifests": [],
            "helm_values": {}
        },
        "terraform": {
            "modules": []
        }
    }


def _calculate_duration(params: Dict[str, Any]) -> float:
    """Calculate total execution duration"""
    # Implementation would track actual timings
    return 0.0


# FastAPI endpoints
@app.post("/execute", response_model=Dict[str, str])
async def execute_request(request: ExecutionRequest):
    """Submit a new execution request"""
    try:
        # Initialize Temporal client
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        
        # Start workflow
        handle = await temporal_client.start_workflow(
            "QLPWorkflow",
            {
                "request_id": request.id,
                "description": request.description,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "requirements": request.requirements,
                "constraints": request.constraints,
                "metadata": request.metadata
            },
            id=f"qlp-execution-{request.id}",
            task_queue="qlp-main"
        )
        
        return {
            "workflow_id": handle.id,
            "status": "submitted",
            "message": "Execution workflow started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start execution", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{workflow_id}")
async def get_status(workflow_id: str):
    """Get workflow execution status"""
    try:
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        description = await handle.describe()
        
        return {
            "workflow_id": workflow_id,
            "status": description.status.name,
            "start_time": description.start_time,
            "close_time": description.close_time
        }
        
    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve/{workflow_id}")
async def approve_execution(workflow_id: str):
    """Approve a workflow execution plan"""
    try:
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        await handle.signal("human_approval", True)
        
        return {"status": "approved"}
        
    except Exception as e:
        logger.error("Failed to approve", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "meta-orchestrator"}


@app.post("/test/decompose")
async def test_decomposition(request: ExecutionRequest):
    """Test endpoint for request decomposition without Temporal"""
    try:
        orchestrator = MetaOrchestrator()
        
        # Decompose the request
        decomposition = await orchestrator.decompose_request(request)
        
        # Create execution plan
        plan = await orchestrator.create_execution_plan(decomposition)
        plan.request_id = request.id
        
        # Convert to JSON-serializable format
        response_data = {
            "request_id": request.id,
            "tasks": [jsonable_encoder(t) for t in decomposition.tasks],
            "dependencies": decomposition.dependencies,
            "execution_order": plan.execution_order,
            "task_assignments": {k: v.value for k, v in plan.task_assignments.items()},
            "estimated_duration": plan.estimated_duration,
            "plan": jsonable_encoder(plan)
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error("Test decomposition failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# HITL (Human-in-the-Loop) endpoints
@app.post("/hitl/request")
async def create_hitl_request(request: Dict[str, Any]):
    """Create a new HITL request"""
    try:
        request_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        hitl_data = {
            "request_id": request_id,
            "type": request.get("type", "review"),
            "task_id": request.get("task_id"),
            "priority": request.get("priority", "normal"),
            "context": request.get("context", {}),
            "questions": request.get("questions", []),
            "timeout_minutes": request.get("timeout_minutes", 60),
            "status": "pending",
            "created_at": timestamp,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=request.get("timeout_minutes", 60))).isoformat()
        }
        
        # Store in memory (in production, use a database)
        hitl_requests[request_id] = hitl_data
        
        # In production, this would:
        # 1. Store in database
        # 2. Send notification to reviewers
        # 3. Create audit trail
        
        logger.info("Created HITL request", request_id=request_id, type=hitl_data["type"])
        
        return {"request_id": request_id, "status": "created"}
        
    except Exception as e:
        logger.error("Failed to create HITL request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hitl/status/{request_id}")
async def get_hitl_status(request_id: str):
    """Get status of a HITL request"""
    if request_id not in hitl_requests:
        raise HTTPException(status_code=404, detail="HITL request not found")
    
    request_data = hitl_requests[request_id]
    
    # Check if expired
    if datetime.utcnow().isoformat() > request_data["expires_at"]:
        request_data["status"] = "expired"
    
    return {
        "request_id": request_id,
        "status": request_data["status"],
        "type": request_data["type"],
        "created_at": request_data["created_at"],
        "expires_at": request_data["expires_at"],
        "result": request_data.get("result")
    }


@app.post("/hitl/respond/{request_id}")
async def respond_to_hitl(request_id: str, response: HITLResponse):
    """Submit a response to a HITL request"""
    if request_id not in hitl_requests:
        raise HTTPException(status_code=404, detail="HITL request not found")
    
    request_data = hitl_requests[request_id]
    
    # Check if already completed or expired
    if request_data["status"] in ["completed", "expired"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot respond to {request_data['status']} request"
        )
    
    # Update request with response
    request_data["status"] = "completed"
    request_data["result"] = {
        "approved": response.response.get("approved", False),
        "reviewer_id": response.user_id,
        "confidence": response.confidence,
        "comments": response.response.get("comments", ""),
        "modifications": response.response.get("modifications", {}),
        "timestamp": response.responded_at.isoformat()
    }
    
    logger.info(
        "HITL request completed", 
        request_id=request_id, 
        approved=request_data["result"]["approved"]
    )
    
    return {"status": "response_recorded"}


@app.get("/hitl/pending")
async def get_pending_hitl_requests(priority: Optional[str] = None):
    """Get all pending HITL requests"""
    pending = []
    
    for request_id, data in hitl_requests.items():
        # Check if expired
        if datetime.utcnow().isoformat() > data["expires_at"]:
            data["status"] = "expired"
            continue
        
        if data["status"] == "pending":
            if priority is None or data["priority"] == priority:
                pending.append({
                    "request_id": request_id,
                    "type": data["type"],
                    "priority": data["priority"],
                    "created_at": data["created_at"],
                    "expires_at": data["expires_at"],
                    "context": data.get("context", {})
                })
    
    # Sort by priority and creation time
    priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    pending.sort(
        key=lambda x: (priority_order.get(x["priority"], 2), x["created_at"])
    )
    
    return {"pending_requests": pending, "count": len(pending)}


@app.post("/generate/capsule")
async def generate_enhanced_capsule(request: ExecutionRequest):
    """Generate an enhanced QLCapsule with complete project structure"""
    try:
        from src.orchestrator.enhanced_capsule import EnhancedCapsuleGenerator, save_capsule_to_disk
        
        generator = EnhancedCapsuleGenerator()
        
        logger.info(f"Generating enhanced QLCapsule for request: {request.id}")
        
        # Generate the capsule
        capsule = await generator.generate_capsule(request, use_advanced=True)
        
        # Optionally save to disk
        save_to_disk = request.metadata.get("save_to_disk", False)
        output_path = None
        
        if save_to_disk:
            output_path = save_capsule_to_disk(capsule)
            logger.info(f"Saved capsule to disk: {output_path}")
        
        # Convert to JSON-serializable format
        response_data = {
            "capsule_id": capsule.id,
            "request_id": capsule.request_id,
            "files_generated": len(capsule.source_code) + len(capsule.tests),
            "confidence_score": capsule.metadata.get("confidence_score", 0),
            "languages": capsule.metadata.get("languages", []),
            "manifest": capsule.manifest,
            "output_path": output_path,
            "preview": {
                "source_files": list(capsule.source_code.keys())[:5],  # First 5 files
                "test_files": list(capsule.tests.keys())[:5],
                "documentation_preview": capsule.documentation[:500] + "..." if len(capsule.documentation) > 500 else capsule.documentation
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"Enhanced capsule generation failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/capsule/{capsule_id}")
async def get_capsule_details(capsule_id: str):
    """Get details of a generated QLCapsule"""
    try:
        # In production, retrieve from storage
        # For now, return a placeholder
        return {
            "capsule_id": capsule_id,
            "status": "generated",
            "message": "Capsule details would be retrieved from storage"
        }
        
    except Exception as e:
        logger.error(f"Failed to get capsule details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/robust-capsule")
async def generate_robust_capsule(request: ExecutionRequest):
    """Generate a robust QLCapsule with iterative refinement to ensure quality"""
    try:
        from src.orchestrator.enhanced_capsule import save_capsule_to_disk
        from src.orchestrator.robust_capsule_generator import RobustCapsuleGenerator
        
        # Set target score from metadata
        target_score = request.metadata.get("target_score", 0.85) if request.metadata else 0.85
        
        # Create robust generator
        robust_generator = RobustCapsuleGenerator(
            target_score=target_score,
            max_iterations=5
        )
        
        logger.info(
            f"Generating robust QLCapsule for request: {request.id}",
            target_score=target_score
        )
        
        # Generate the capsule with iterative refinement
        capsule = await robust_generator.generate_robust_capsule(request)
        
        # The capsule already has validation results from the refinement process
        validation_results = capsule.metadata.get('final_validation', {})
        
        # Optionally save to disk
        save_to_disk = request.metadata.get("save_to_disk", False) if request.metadata else False
        output_path = None
        
        if save_to_disk:
            output_path = save_capsule_to_disk(capsule)
            logger.info(f"Saved robust capsule to disk: {output_path}")
        
        # Prepare response
        response_data = {
            "capsule_id": capsule.id,
            "request_id": capsule.request_id,
            "robust_generation": True,
            "refinement_iterations": capsule.metadata.get("refinement_iterations", 1),
            "validation": {
                "passed": validation_results.get('passed', False),
                "score": validation_results.get('score', 0),
                "production_ready": validation_results.get('passed', False) and validation_results.get('score', 0) >= 0.8,
                "issues": capsule.metadata.get('final_scores', {}).get('issues', [])[:5],
                "recommendations": ["Capsule meets quality targets"] if validation_results.get('passed', False) else ["Further refinement needed"]
            },
            "files_generated": len(capsule.source_code) + len(capsule.tests),
            "confidence_score": capsule.metadata.get("confidence_score", 0),
            "languages": capsule.metadata.get("languages", []),
            "output_path": output_path,
            "preview": {
                "source_files": list(capsule.source_code.keys())[:5],
                "test_files": list(capsule.tests.keys())[:5],
                "has_dockerfile": any("dockerfile" in k.lower() for k in capsule.source_code),
                "has_ci_cd": any(".github" in k or "gitlab" in k for k in capsule.source_code),
                "has_tests": bool(capsule.tests)
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Robust capsule generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Worker setup
async def run_worker():
    """Run Temporal worker"""
    client = await Client.connect(settings.TEMPORAL_SERVER)
    
    worker = Worker(
        client,
        task_queue="qlp-main",
        workflows=[QLPExecutionWorkflow],
        activities=[
            decompose_request_activity,
            create_plan_activity,
            execute_task_activity,
            validate_results_activity,
            create_capsule_activity
        ]
    )
    
    await worker.run()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
