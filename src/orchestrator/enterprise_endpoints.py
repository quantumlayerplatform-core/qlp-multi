#!/usr/bin/env python3
"""
Enterprise-grade endpoints for Quantum Layer Platform
Combines intelligent capsule generation with enterprise structure
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from src.common.database import get_db
from src.common.auth import get_current_user
from src.common.models import ExecutionRequest, QLCapsule
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.orchestrator.intelligent_capsule_generator import IntelligentCapsuleGenerator
from src.orchestrator.enhanced_github_integration import EnhancedGitHubIntegration
from src.common.config import settings
from temporalio.client import Client

logger = structlog.get_logger()

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


class EnterpriseExecutionRequest(BaseModel):
    """Request for enterprise-grade code generation"""
    description: str = Field(..., description="What to build")
    tenant_id: str = Field(default="default", description="Tenant ID")
    user_id: str = Field(default="user", description="User ID")
    requirements: Optional[str] = Field(None, description="Detailed requirements")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Constraints")
    enterprise_features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "documentation": True,
            "testing": True,
            "ci_cd": True,
            "containerization": True,
            "monitoring": True,
            "security": True
        },
        description="Enterprise features to include"
    )
    auto_push_github: bool = Field(False, description="Automatically push to GitHub")
    github_token: Optional[str] = Field(None, description="GitHub token if auto-push enabled")
    repo_name: Optional[str] = Field(None, description="Custom repository name")
    private_repo: bool = Field(False, description="Create private repository")


class EnterpriseGenerationResponse(BaseModel):
    """Response for enterprise generation"""
    success: bool
    capsule_id: str
    workflow_id: Optional[str] = None
    github_url: Optional[str] = None
    message: str
    enterprise_features: Dict[str, bool]
    files_count: int
    structure_version: str = "2.0"


@router.post("/generate", response_model=EnterpriseGenerationResponse)
async def generate_enterprise_project(
    request: EnterpriseExecutionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Generate an enterprise-grade project with intelligent structure
    
    This endpoint:
    1. Uses Temporal workflow to generate base code
    2. Applies IntelligentCapsuleGenerator for enterprise structure
    3. Optionally pushes to GitHub with proper organization
    """
    
    try:
        # Create execution request for Temporal
        exec_request = ExecutionRequest(
            id=f"ent-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            description=request.description,
            requirements=request.requirements,
            constraints=request.constraints or {}
        )
        
        # Start Temporal workflow
        temporal_client = await Client.connect(settings.TEMPORAL_SERVER)
        workflow_id = f"enterprise-{exec_request.id}"
        
        logger.info(
            "Starting enterprise workflow",
            workflow_id=workflow_id,
            description=request.description
        )
        
        # Execute workflow
        handle = await temporal_client.start_workflow(
            "QLPWorkflow",
            exec_request.model_dump(),
            id=workflow_id,
            task_queue="qlp-queue"
        )
        
        # Wait for workflow to complete
        workflow_result = await handle.result()
        
        # Get the generated capsule
        storage = CapsuleStorageService(db)
        capsule_id = workflow_result.get("capsule_id")
        
        if not capsule_id:
            raise HTTPException(
                status_code=500,
                detail="Workflow completed but no capsule was generated"
            )
        
        capsule = await storage.get_capsule(capsule_id)
        if not capsule:
            raise HTTPException(
                status_code=404,
                detail=f"Generated capsule {capsule_id} not found"
            )
        
        # Apply enterprise transformation
        logger.info("Applying enterprise transformation", capsule_id=capsule_id)
        
        generator = IntelligentCapsuleGenerator()
        
        # Convert capsule to dict for processing
        base_capsule = {
            "capsule_id": capsule.id,
            "source_code": capsule.source_code,
            "tests": capsule.tests,
            "documentation": capsule.documentation,
            "metadata": capsule.metadata,
            "manifest": capsule.manifest
        }
        
        # Create context for enterprise generation
        context = {
            "description": request.description,
            "requirements": request.requirements,
            "language": capsule.manifest.get("language", "python"),
            "enterprise_features": request.enterprise_features
        }
        
        # Generate enterprise structure
        enterprise_capsule = await generator.generate_enterprise_capsule(
            base_capsule,
            context
        )
        
        # Update the capsule with enterprise structure
        capsule.source_code = enterprise_capsule["files"]
        capsule.metadata.update({
            "enterprise_grade": True,
            "structure_version": "2.0",
            "enterprise_features": request.enterprise_features,
            "project_metadata": enterprise_capsule.get("project_metadata", {})
        })
        
        # Save updated capsule
        await storage.update_capsule(capsule)
        
        github_url = None
        
        # Auto-push to GitHub if requested
        if request.auto_push_github:
            try:
                token = request.github_token or os.getenv("GITHUB_TOKEN")
                if not token:
                    logger.warning("GitHub auto-push requested but no token provided")
                else:
                    github = EnhancedGitHubIntegration(token)
                    
                    # Push with intelligent structure
                    result = await github.push_capsule_atomic(
                        capsule,
                        repo_name=request.repo_name,
                        private=request.private_repo,
                        use_intelligent_structure=False  # Already structured
                    )
                    
                    github_url = result["repository_url"]
                    
                    # Update capsule metadata
                    capsule.metadata["github_url"] = github_url
                    capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
                    await storage.update_capsule_metadata(capsule_id, capsule.metadata)
                    
            except Exception as e:
                logger.error(f"Failed to push to GitHub: {e}")
                # Don't fail the entire request
        
        # Count files
        files_count = len(enterprise_capsule.get("files", {}))
        
        return EnterpriseGenerationResponse(
            success=True,
            capsule_id=capsule_id,
            workflow_id=workflow_id,
            github_url=github_url,
            message="Successfully generated enterprise-grade project",
            enterprise_features=request.enterprise_features,
            files_count=files_count,
            structure_version="2.0"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate enterprise project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate enterprise project: {str(e)}"
        )


@router.post("/transform/{capsule_id}", response_model=EnterpriseGenerationResponse)
async def transform_to_enterprise(
    capsule_id: str,
    request: Dict[str, Any],
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Transform an existing capsule to enterprise-grade structure
    
    This is useful when you already have a capsule and want to:
    1. Add enterprise features (CI/CD, documentation, etc.)
    2. Reorganize into proper folder structure
    3. Add production-ready configurations
    """
    
    try:
        # Get the existing capsule
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(capsule_id)
        
        if not capsule:
            raise HTTPException(
                status_code=404,
                detail=f"Capsule {capsule_id} not found"
            )
        
        # Apply enterprise transformation
        logger.info("Transforming capsule to enterprise grade", capsule_id=capsule_id)
        
        generator = IntelligentCapsuleGenerator()
        
        # Convert capsule to dict
        base_capsule = {
            "capsule_id": capsule.id,
            "source_code": capsule.source_code,
            "tests": capsule.tests,
            "documentation": capsule.documentation,
            "metadata": capsule.metadata,
            "manifest": capsule.manifest
        }
        
        # Create context
        context = {
            "description": capsule.manifest.get("description", ""),
            "language": capsule.manifest.get("language", "python"),
            "enterprise_features": request.get("enterprise_features", {
                "documentation": True,
                "testing": True,
                "ci_cd": True,
                "containerization": True,
                "monitoring": True,
                "security": True
            })
        }
        
        # Generate enterprise structure
        enterprise_capsule = await generator.generate_enterprise_capsule(
            base_capsule,
            context
        )
        
        # Create new capsule with enterprise structure
        new_capsule_id = f"ent-{capsule.id}"
        new_capsule = QLCapsule(
            id=new_capsule_id,
            manifest={
                **capsule.manifest,
                "name": f"{capsule.manifest.get('name', 'Project')} Enterprise",
                "structure_version": "2.0"
            },
            metadata={
                **capsule.metadata,
                "original_capsule_id": capsule_id,
                "enterprise_grade": True,
                "transformed_at": datetime.utcnow().isoformat(),
                "project_metadata": enterprise_capsule.get("project_metadata", {})
            }
        )
        
        # Set the enterprise files
        new_capsule.source_code = enterprise_capsule["files"]
        new_capsule.tests = {}  # Tests are now in the files structure
        new_capsule.documentation = enterprise_capsule["files"].get("README.md", "")
        new_capsule.validation_report = capsule.validation_report
        
        # Save the new capsule
        await storage.store_capsule(new_capsule)
        
        return EnterpriseGenerationResponse(
            success=True,
            capsule_id=new_capsule_id,
            workflow_id=None,
            github_url=None,
            message=f"Successfully transformed capsule to enterprise grade",
            enterprise_features=context["enterprise_features"],
            files_count=len(enterprise_capsule.get("files", {})),
            structure_version="2.0"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to transform capsule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transform capsule: {str(e)}"
        )


@router.get("/status/{capsule_id}")
async def get_enterprise_status(
    capsule_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Get status of an enterprise capsule"""
    
    storage = CapsuleStorageService(db)
    capsule = await storage.get_capsule(capsule_id)
    
    if not capsule:
        raise HTTPException(
            status_code=404,
            detail=f"Capsule {capsule_id} not found"
        )
    
    # Check if it's enterprise grade
    is_enterprise = capsule.metadata.get("enterprise_grade", False)
    
    # Count files by type
    file_types = {}
    for filepath in capsule.source_code.keys():
        if filepath.startswith(".github/"):
            file_types["ci_cd"] = file_types.get("ci_cd", 0) + 1
        elif filepath.startswith("docs/"):
            file_types["documentation"] = file_types.get("documentation", 0) + 1
        elif filepath.startswith("tests/"):
            file_types["tests"] = file_types.get("tests", 0) + 1
        elif filepath.endswith(("Dockerfile", "docker-compose.yml")):
            file_types["containerization"] = file_types.get("containerization", 0) + 1
        else:
            file_types["source"] = file_types.get("source", 0) + 1
    
    return {
        "capsule_id": capsule_id,
        "is_enterprise_grade": is_enterprise,
        "structure_version": capsule.metadata.get("structure_version", "1.0"),
        "file_count": len(capsule.source_code),
        "file_types": file_types,
        "enterprise_features": capsule.metadata.get("enterprise_features", {}),
        "project_metadata": capsule.metadata.get("project_metadata", {}),
        "github_url": capsule.metadata.get("github_url"),
        "created_at": capsule.metadata.get("created_at"),
        "transformed_at": capsule.metadata.get("transformed_at")
    }