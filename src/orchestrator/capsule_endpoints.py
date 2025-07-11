"""
Capsule generation endpoints with PostgreSQL storage
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.common.database import get_db
from src.common.models import QLCapsule, ExecutionRequest
from src.orchestrator.capsule_storage import CapsuleStorageService
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/capsules", tags=["capsules"])


class CapsuleGenerationRequest(BaseModel):
    """Request model for capsule generation"""
    request_id: str
    tenant_id: str
    user_id: str
    project_name: str
    description: str
    requirements: Optional[str] = ""
    tech_stack: List[str] = ["Python"]
    complexity: str = "medium"


@router.post("/generate")
async def generate_capsule_with_db(
    request: CapsuleGenerationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Generate a capsule and save it to PostgreSQL"""
    
    try:
        # Create execution request
        exec_request = ExecutionRequest(
            id=request.request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            description=request.description,
            requirements=request.requirements,
            constraints={"tech_stack": request.tech_stack}
        )
        
        # Create sample capsule (in production, this would come from the workflow)
        from datetime import datetime
        from uuid import uuid4
        
        capsule = QLCapsule(
            id=str(uuid4()),
            request_id=request.request_id,
            manifest={
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "project_name": request.project_name,
                "language": request.tech_stack[0] if request.tech_stack else "Python"
            },
            source_code={
                "main.py": f"# {request.project_name}\\n\\ndef main():\\n    print('Hello from {request.project_name}')\\n\\nif __name__ == '__main__':\\n    main()"
            },
            tests={
                "test_main.py": "import unittest\\nfrom main import main\\n\\nclass TestMain(unittest.TestCase):\\n    def test_main(self):\\n        # Test implementation\\n        pass"
            },
            documentation=f"# {request.project_name}\\n\\n{request.description}\\n\\n## Requirements\\n{request.requirements}",
            deployment_config={
                "language": request.tech_stack[0] if request.tech_stack else "Python",
                "dependencies": []
            },
            metadata={
                "complexity": request.complexity,
                "tech_stack": request.tech_stack
            }
        )
        
        # Save to PostgreSQL
        storage_service = CapsuleStorageService(db)
        capsule_id = await storage_service.store_capsule(
            capsule=capsule,
            request=exec_request,
            overwrite=True
        )
        
        logger.info(f"Capsule generated and saved to PostgreSQL", capsule_id=capsule_id)
        
        return {
            "success": True,
            "capsule_id": capsule_id,
            "request_id": request.request_id,
            "database_saved": True,
            "message": "Capsule generated and saved to PostgreSQL"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate capsule", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate capsule: {str(e)}")


@router.get("/{capsule_id}")
async def get_capsule_from_db(
    capsule_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve a capsule from PostgreSQL"""
    
    try:
        storage_service = CapsuleStorageService(db)
        capsule = await storage_service.get_capsule(capsule_id)
        
        if not capsule:
            raise HTTPException(status_code=404, detail="Capsule not found")
        
        return {
            "capsule_id": str(capsule.id),
            "request_id": capsule.request_id,
            "manifest": capsule.manifest,
            "source_code": capsule.source_code,
            "tests": capsule.tests,
            "documentation": capsule.documentation,
            "metadata": capsule.metadata,
            "created_at": capsule.created_at if hasattr(capsule, 'created_at') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve capsule", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve capsule: {str(e)}")


@router.get("/user/{tenant_id}/{user_id}")
async def list_user_capsules(
    tenant_id: str,
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List capsules for a user from PostgreSQL"""
    
    try:
        storage_service = CapsuleStorageService(db)
        capsules = await storage_service.list_capsules(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit
        )
        
        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "capsules": capsules,
            "count": len(capsules)
        }
        
    except Exception as e:
        logger.error(f"Failed to list capsules", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list capsules: {str(e)}")