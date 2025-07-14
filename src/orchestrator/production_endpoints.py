#!/usr/bin/env python3
"""
Production API Endpoints
Enterprise-grade endpoints with comprehensive error handling and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

from src.common.database import get_db
from src.common.models import ExecutionRequest, QLCapsule
from src.common.auth import get_current_user
from src.orchestrator.production_capsule_system import get_production_capsule_system
from src.orchestrator.production_github_integration import get_production_github_integration
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.moderation import check_content, CheckContext, Severity

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2", tags=["production"])


class ProductionCapsuleRequest(BaseModel):
    """Request model for production capsule generation"""
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    project_name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    requirements: Optional[str] = Field(None, description="Detailed requirements")
    language: str = Field("python", description="Primary programming language")
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional constraints")
    priority: str = Field("normal", description="Priority: low, normal, high, urgent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "enterprise-001",
                "user_id": "dev-team-alpha",
                "project_name": "Customer Analytics Dashboard",
                "description": "Build a real-time customer analytics dashboard with ML insights",
                "requirements": "Must support 10k concurrent users, integrate with Salesforce API",
                "language": "python",
                "constraints": {
                    "framework": "FastAPI",
                    "database": "PostgreSQL",
                    "deployment": "Kubernetes"
                },
                "priority": "high"
            }
        }


class ProductionGitHubPushRequest(BaseModel):
    """Request model for production GitHub push"""
    capsule_id: str = Field(..., description="Capsule ID to push")
    github_token: Optional[str] = Field(None, description="GitHub personal access token")
    repo_name: Optional[str] = Field(None, description="Custom repository name")
    private: bool = Field(False, description="Create private repository")
    branch: str = Field("main", description="Target branch")
    
    class Config:
        json_schema_extra = {
            "example": {
                "capsule_id": "cap-123e4567-e89b-12d3-a456-426614174000",
                "repo_name": "analytics-dashboard",
                "private": True,
                "branch": "main"
            }
        }


class CapsuleGenerationResponse(BaseModel):
    """Response model for capsule generation"""
    success: bool
    capsule_id: str
    status: str
    message: str
    metrics: Dict[str, Any]
    preview: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class GitHubPushResponse(BaseModel):
    """Response model for GitHub push"""
    success: bool
    repository_url: str
    clone_url: str
    ssh_url: str
    owner: str
    repo_name: str
    files_created: int
    commit_sha: str
    commit_url: str
    message: str
    metrics: Dict[str, Any]


@router.post("/capsule/generate", response_model=CapsuleGenerationResponse)
async def generate_production_capsule(
    request: ProductionCapsuleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Generate a production-ready capsule with enterprise-grade reliability
    
    This endpoint:
    - Validates the request thoroughly
    - Generates code using multiple AI agents
    - Runs comprehensive validation
    - Stores the capsule for future use
    - Provides detailed metrics and error reporting
    """
    try:
        # Create execution request
        exec_request = ExecutionRequest(
            id=f"{request.tenant_id}-{request.user_id}-{datetime.utcnow().timestamp()}",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            description=request.description,
            requirements=request.requirements,
            constraints={
                "language": request.language,
                **request.constraints
            }
        )
        
        # Get production system
        capsule_system = get_production_capsule_system()
        
        # Generate capsule
        logger.info(
            "Starting production capsule generation",
            request_id=exec_request.id,
            project=request.project_name,
            priority=request.priority
        )
        
        capsule = await capsule_system.generate_capsule(exec_request)
        
        # Prepare response
        response = CapsuleGenerationResponse(
            success=capsule.validation_report is not None and capsule.validation_report.confidence_score > 0.5,
            capsule_id=capsule.id,
            status="completed" if capsule.source_code else "failed",
            message=f"Capsule generated for project: {request.project_name}",
            metrics={
                "generation_time": capsule.metadata.get("generation_metrics", {}).get("duration_seconds", 0),
                "tasks_completed": capsule.metadata.get("generation_metrics", {}).get("tasks_completed", 0),
                "validation_score": capsule.validation_report.confidence_score if capsule.validation_report else 0.0,
                "files_generated": len(capsule.source_code) + len(capsule.tests),
                "retry_count": capsule.metadata.get("generation_metrics", {}).get("retry_count", 0)
            },
            preview={
                "source_files": list(capsule.source_code.keys())[:5],
                "test_files": list(capsule.tests.keys())[:5],
                "has_documentation": bool(capsule.documentation),
                "language": capsule.manifest.get("language", "unknown")
            },
            errors=capsule.metadata.get("generation_metrics", {}).get("errors", [])
        )
        
        # Log success metrics
        logger.info(
            "Production capsule generated successfully",
            capsule_id=capsule.id,
            files=len(capsule.source_code) + len(capsule.tests),
            validation_score=response.metrics["validation_score"]
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to generate production capsule",
            error=str(e),
            project=request.project_name
        )
        
        return CapsuleGenerationResponse(
            success=False,
            capsule_id="",
            status="error",
            message=f"Failed to generate capsule: {str(e)}",
            metrics={
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            errors=[{
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "type": type(e).__name__
            }]
        )


@router.post("/github/push", response_model=GitHubPushResponse)
async def push_capsule_to_github_production(
    request: ProductionGitHubPushRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Push a capsule to GitHub using production-grade atomic commits
    
    This endpoint:
    - Retrieves the capsule from storage
    - Validates the capsule content
    - Creates a GitHub repository (or uses existing)
    - Pushes all files in a single atomic commit
    - Handles errors gracefully with retry logic
    """
    try:
        # Get capsule from storage
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(request.capsule_id)
        
        if not capsule:
            raise HTTPException(
                status_code=404,
                detail=f"Capsule {request.capsule_id} not found"
            )
        
        # Get GitHub integration
        github = get_production_github_integration(request.github_token)
        
        # Push to GitHub
        logger.info(
            "Starting production GitHub push",
            capsule_id=request.capsule_id,
            repo_name=request.repo_name
        )
        
        result = await github.push_capsule(
            capsule=capsule,
            repo_name=request.repo_name,
            private=request.private,
            branch=request.branch
        )
        
        # Update capsule metadata
        capsule.metadata["github_url"] = result["repository_url"]
        capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
        capsule.metadata["github_commit_sha"] = result["commit_sha"]
        
        await storage.update_capsule_metadata(request.capsule_id, capsule.metadata)
        
        # Prepare response
        response = GitHubPushResponse(
            success=result["success"],
            repository_url=result["repository_url"],
            clone_url=result["clone_url"],
            ssh_url=result["ssh_url"],
            owner=result["owner"],
            repo_name=result["name"],
            files_created=result["files_created"],
            commit_sha=result["commit_sha"],
            commit_url=result["commit_url"],
            message=f"Successfully pushed capsule to GitHub: {result['repository_url']}",
            metrics=result["metrics"]
        )
        
        logger.info(
            "GitHub push completed successfully",
            repository=result["repository_url"],
            files=result["files_created"],
            commit=result["commit_sha"][:8]
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to push to GitHub",
            error=str(e),
            capsule_id=request.capsule_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push to GitHub: {str(e)}"
        )


@router.get("/capsule/{capsule_id}/status")
async def get_capsule_status(
    capsule_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Get detailed status of a capsule"""
    try:
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(capsule_id)
        
        if not capsule:
            raise HTTPException(
                status_code=404,
                detail=f"Capsule {capsule_id} not found"
            )
        
        # Calculate status
        has_code = bool(capsule.source_code)
        has_tests = bool(capsule.tests)
        has_docs = bool(capsule.documentation)
        validation_passed = (
            capsule.validation_report and 
            capsule.validation_report.confidence_score > 0.7
        )
        
        github_url = capsule.metadata.get("github_url")
        
        return {
            "capsule_id": capsule_id,
            "status": {
                "has_code": has_code,
                "has_tests": has_tests,
                "has_documentation": has_docs,
                "validation_passed": validation_passed,
                "is_pushed_to_github": bool(github_url)
            },
            "metrics": {
                "files": len(capsule.source_code) + len(capsule.tests),
                "validation_score": capsule.validation_report.confidence_score if capsule.validation_report else 0.0,
                "created_at": capsule.created_at
            },
            "github": {
                "url": github_url,
                "pushed_at": capsule.metadata.get("github_pushed_at"),
                "commit_sha": capsule.metadata.get("github_commit_sha")
            },
            "ready_for_deployment": has_code and has_tests and validation_passed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get capsule status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get capsule status: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Production system health check"""
    return {
        "status": "healthy",
        "service": "production-endpoints",
        "version": "2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "capsule_generation": "active",
            "github_integration": "active",
            "atomic_commits": "enabled",
            "retry_logic": "enabled",
            "monitoring": "enabled"
        }
    }