"""
Unified API Endpoints for Quantum Layer Platform

This module implements the consolidated endpoint strategy to replace
the proliferation of redundant endpoints.
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
import warnings

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from temporalio.client import Client
import structlog

from src.common.models import ExecutionRequest
from src.common.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/v2", tags=["Unified API"])


class ExecutionOptions(BaseModel):
    """Options for controlling execution behavior"""
    
    mode: Literal["basic", "complete", "robust"] = Field(
        default="complete",
        description="Execution mode: basic (fast), complete (standard), robust (production-grade)"
    )
    
    tier_override: Optional[str] = Field(
        default=None,
        description="Override agent tier selection (T0, T1, T2, T3)"
    )
    
    github: Optional[Dict[str, Any]] = Field(
        default=None,
        description="GitHub integration options"
    )
    
    delivery: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Delivery options for the generated capsule"
    )
    
    validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation options"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class UnifiedExecutionRequest(BaseModel):
    """Unified request model for all code generation workflows"""
    
    description: str = Field(
        ...,
        description="Natural language description of what to build"
    )
    
    user_id: str = Field(
        default="user",
        description="User identifier"
    )
    
    tenant_id: str = Field(
        default="default",
        description="Tenant identifier for multi-tenancy"
    )
    
    options: ExecutionOptions = Field(
        default_factory=ExecutionOptions,
        description="Execution options"
    )
    
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Constraints like language, framework, etc."
    )
    
    requirements: Optional[str] = Field(
        default=None,
        description="Additional requirements or specifications"
    )


class UnifiedResponse(BaseModel):
    """Unified response for execution requests"""
    
    workflow_id: str
    request_id: str
    status: str
    message: str
    links: Dict[str, str]
    metadata: Dict[str, Any]


@router.post("/execute", response_model=UnifiedResponse)
async def unified_execute(
    request: UnifiedExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Unified endpoint for all code generation workflows.
    
    This replaces:
    - /execute
    - /generate/capsule  
    - /generate/complete-with-github
    - /generate/complete-pipeline
    - /generate/robust-capsule
    
    Use the 'options' parameter to control behavior.
    """
    
    # Generate request ID
    request_id = str(uuid4())
    
    # Build workflow request
    workflow_request = {
        "request_id": request_id,
        "description": request.description,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "metadata": {
            **request.options.metadata,
            "api_version": "v2",
            "execution_mode": request.options.mode
        }
    }
    
    # Add tier override if specified
    if request.options.tier_override:
        workflow_request["tier_override"] = request.options.tier_override
    
    # Add constraints if specified
    if request.constraints:
        workflow_request["constraints"] = request.constraints
    
    # Add requirements if specified
    if request.requirements:
        workflow_request["requirements"] = request.requirements
    
    # Configure based on mode
    if request.options.mode == "basic":
        # Basic mode - minimal validation, fast execution
        workflow_request["metadata"]["skip_extended_validation"] = True
        workflow_request["metadata"]["skip_security_scan"] = True
        
    elif request.options.mode == "robust":
        # Robust mode - full validation, production features
        workflow_request["metadata"]["enable_production_features"] = True
        workflow_request["metadata"]["enable_comprehensive_tests"] = True
        workflow_request["metadata"]["enable_documentation"] = True
    
    # Configure GitHub integration
    if request.options.github:
        github_opts = request.options.github
        workflow_request["metadata"].update({
            "push_to_github": github_opts.get("enabled", False),
            "github_token": github_opts.get("token"),
            "github_repo_name": github_opts.get("repo_name"),
            "github_private": github_opts.get("private", False),
            "github_create_pr": github_opts.get("create_pr", False),
            "github_enterprise": github_opts.get("enterprise_structure", True)
        })
    
    # Configure delivery options
    if request.options.delivery:
        delivery_opts = request.options.delivery
        workflow_request["metadata"].update({
            "delivery_format": delivery_opts.get("format", "zip"),
            "delivery_stream": delivery_opts.get("stream", False),
            "delivery_method": delivery_opts.get("method", "download")
        })
    
    # Configure validation options
    if request.options.validation:
        val_opts = request.options.validation
        workflow_request["metadata"].update({
            "validation_strict": val_opts.get("strict", True),
            "validation_security": val_opts.get("security", True),
            "validation_performance": val_opts.get("performance", False)
        })
    
    try:
        # Initialize Temporal client
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        
        # Determine workflow based on mode and options
        workflow_name = "QLPWorkflow"
        workflow_id = f"qlp-v2-{request.options.mode}-{request_id}"
        
        # Start workflow
        handle = await temporal_client.start_workflow(
            workflow_name,
            workflow_request,
            id=workflow_id,
            task_queue="qlp-main"
        )
        
        logger.info(
            "Started unified workflow",
            workflow_id=workflow_id,
            mode=request.options.mode,
            github_enabled=bool(request.options.github),
            user_id=request.user_id
        )
        
        # Build response with useful links
        base_url = settings.API_BASE_URL or "http://localhost:8000"
        
        response = UnifiedResponse(
            workflow_id=workflow_id,
            request_id=request_id,
            status="submitted",
            message=f"Workflow started in {request.options.mode} mode",
            links={
                "status": f"{base_url}/v2/workflows/{workflow_id}",
                "cancel": f"{base_url}/v2/workflows/{workflow_id}/cancel",
                "result": f"{base_url}/v2/workflows/{workflow_id}/result"
            },
            metadata={
                "mode": request.options.mode,
                "estimated_duration": _estimate_duration(request.options.mode),
                "features": _get_enabled_features(request.options)
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to start unified workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow status (replaces multiple status endpoints)"""
    
    try:
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Get status
        description = await handle.describe()
        
        # Build status response
        status = {
            "workflow_id": workflow_id,
            "status": description.status.name,
            "started_at": description.start_time.isoformat() if description.start_time else None,
            "completed_at": description.close_time.isoformat() if description.close_time else None,
            "execution_time": None,
            "progress": _extract_progress(description)
        }
        
        # Calculate execution time
        if description.start_time:
            if description.close_time:
                status["execution_time"] = (
                    description.close_time - description.start_time
                ).total_seconds()
            else:
                status["execution_time"] = (
                    datetime.utcnow() - description.start_time
                ).total_seconds()
        
        # Add result link if completed
        if description.status.name in ["COMPLETED", "FAILED"]:
            base_url = settings.API_BASE_URL or "http://localhost:8000"
            status["result_link"] = f"{base_url}/v2/workflows/{workflow_id}/result"
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}"
        )


@router.get("/workflows/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """Get workflow result (replaces capsule retrieval)"""
    
    try:
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Get result
        result = await handle.result()
        
        # Format result based on type
        if isinstance(result, dict) and "capsule_id" in result:
            # Add download links
            base_url = settings.API_BASE_URL or "http://localhost:8000"
            result["downloads"] = {
                "zip": f"{base_url}/v2/capsules/{result['capsule_id']}/download?format=zip",
                "tar": f"{base_url}/v2/capsules/{result['capsule_id']}/download?format=tar",
                "targz": f"{base_url}/v2/capsules/{result['capsule_id']}/download?format=targz"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get workflow result: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Result not found for workflow: {workflow_id}"
        )


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow"""
    
    try:
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        await handle.cancel()
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow cancellation requested"
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


# Deprecation endpoints that redirect to unified API
@router.post("/execute", deprecated=True, include_in_schema=False)
async def deprecated_execute(request: ExecutionRequest):
    """
    DEPRECATED: Use /v2/execute instead.
    This endpoint will be removed in v3.0.
    """
    warnings.warn(
        "POST /execute is deprecated. Use POST /v2/execute instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert to unified request
    unified_request = UnifiedExecutionRequest(
        description=request.description,
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        options=ExecutionOptions(mode="complete")
    )
    
    return await unified_execute(unified_request, BackgroundTasks())


def _estimate_duration(mode: str) -> str:
    """Estimate execution duration based on mode"""
    durations = {
        "basic": "1-2 minutes",
        "complete": "3-5 minutes", 
        "robust": "5-10 minutes"
    }
    return durations.get(mode, "3-5 minutes")


def _get_enabled_features(options: ExecutionOptions) -> list:
    """Get list of enabled features based on options"""
    features = []
    
    if options.mode == "robust":
        features.extend([
            "production_validation",
            "comprehensive_tests",
            "documentation",
            "security_scan"
        ])
    elif options.mode == "complete":
        features.extend([
            "standard_validation",
            "unit_tests"
        ])
    
    if options.github:
        features.append("github_integration")
    
    if options.delivery:
        features.append("custom_delivery")
    
    return features


def _extract_progress(description) -> Dict[str, Any]:
    """Extract progress information from workflow description"""
    # This would parse workflow memo or custom search attributes
    # For now, return basic progress
    if description.status.name == "RUNNING":
        return {
            "percentage": 50,
            "current_step": "processing",
            "message": "Workflow in progress"
        }
    elif description.status.name == "COMPLETED":
        return {
            "percentage": 100,
            "current_step": "completed",
            "message": "Workflow completed successfully"
        }
    else:
        return {
            "percentage": 0,
            "current_step": description.status.name.lower(),
            "message": f"Workflow {description.status.name}"
        }