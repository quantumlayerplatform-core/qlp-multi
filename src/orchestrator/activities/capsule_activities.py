"""
Production Capsule Activities with Database Persistence
Handles capsule creation and storage in PostgreSQL
"""

from typing import Dict, Any, List
from datetime import datetime
from uuid import uuid4
from temporalio import activity
import structlog

from src.common.models import QLCapsule, ExecutionRequest
from src.common.database import get_db
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.orchestrator.shared_context import SharedContext

logger = structlog.get_logger()


@activity.defn
async def create_ql_capsule_activity_with_db(
    request_id: str,
    tasks: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    shared_context_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a QLCapsule and persist it to PostgreSQL database.
    This is the production version that ensures all capsules are saved.
    """
    import httpx
    from src.common.config import settings
    
    activity.logger.info(f"Creating QLCapsule for request: {request_id}")
    
    # Reconstruct shared context
    shared_context = SharedContext.from_dict(shared_context_dict)
    
    activity.logger.info(f"Using shared context - Language: {shared_context.file_structure.primary_language}")
    activity.logger.info(f"Main file: {shared_context.file_structure.main_file_name}")
    activity.logger.info(f"Architecture: {shared_context.architecture_pattern}")
    
    # Send heartbeat for long-running activity
    activity.heartbeat(f"Starting capsule creation for request: {request_id}")
    
    # Extract execution context
    execution_context = {}
    if tasks:
        execution_context = tasks[0].get("context", {})
    
    # Use shared context for consistent file structure
    preferred_language = shared_context.file_structure.primary_language
    main_file_name = shared_context.file_structure.main_file_name
    
    # Organize outputs by type
    source_code = {}
    tests = {}
    documentation = []
    
    for i, (task, result) in enumerate(zip(tasks, results)):
        execution_data = result if "status" in result else result.get("execution", {})
        
        if execution_data.get("status") == "completed":
            output = execution_data.get("output", {})
            output_type = execution_data.get("output_type", "")
            
            # Extract content
            if isinstance(output, dict) and "content" in output:
                content = output["content"]
                # Clean up nested content structure if needed
                if isinstance(content, str) and content.startswith("{'content':"):
                    try:
                        import json
                        json_str = content.replace("'", '"')
                        parsed = json.loads(json_str)
                        content = parsed.get("content", content)
                    except:
                        pass
            else:
                content = output if isinstance(output, str) else str(output)
            
            # Store based on task type
            if output_type == "code" and content and content.strip():
                # Remove markdown code blocks
                if content.startswith("```"):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                
                # Determine file name
                if "test" in task.get("description", "").lower():
                    file_name = f"test_{main_file_name}" if not main_file_name.startswith("test_") else main_file_name
                    tests[file_name] = content
                else:
                    file_name = f"module_{i}.py" if i > 0 else main_file_name
                    source_code[file_name] = content
            
            elif output_type == "documentation":
                documentation.append(content)
    
    # Send heartbeat before database operations
    activity.heartbeat(f"Saving capsule to database for request: {request_id}")
    
    # Create QLCapsule object
    capsule_data = {
        "id": request_id,
        "request_id": request_id,
        "manifest": {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "language": preferred_language,
            "architecture": shared_context.architecture_pattern,
            "task_count": len(tasks),
            "success_rate": sum(1 for r in results if r.get("status") == "completed") / len(results) if results else 0
        },
        "source_code": source_code,
        "tests": tests,
        "documentation": "\n\n".join(documentation) if documentation else f"# {request_id}\n\nGenerated code capsule",
        "deployment_config": {
            "language": preferred_language,
            "framework": shared_context.file_structure.framework,
            "dependencies": shared_context.file_structure.common_imports
        },
        "metadata": {
            "shared_context": shared_context_dict,
            "tasks_count": len(tasks),
            "successful_tasks": sum(1 for r in results if r.get("status") == "completed"),
            "languages": [preferred_language],
            "execution_context": execution_context
        }
    }
    
    # Create QLCapsule instance
    capsule = QLCapsule(**capsule_data)
    
    # Primary storage: PostgreSQL database
    database_saved = False
    try:
        # Create database session
        db = next(get_db())
        storage_service = CapsuleStorageService(db)
        
        # Create ExecutionRequest for storage service
        execution_request = ExecutionRequest(
            id=request_id,
            tenant_id=execution_context.get("tenant_id", "default"),
            user_id=execution_context.get("user_id", "system"),
            description=execution_context.get("original_request", "Generated capsule"),
            requirements="",
            constraints={}
        )
        
        # Store capsule in PostgreSQL
        stored_capsule_id = await storage_service.store_capsule(
            capsule=capsule,
            request=execution_request,
            overwrite=True
        )
        
        database_saved = True
        activity.logger.info(f"✅ Capsule saved to PostgreSQL with ID: {stored_capsule_id}")
        
    except Exception as e:
        activity.logger.error(f"Failed to save capsule to PostgreSQL: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()
    
    # Secondary storage: Vector memory for search capabilities
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://vector-memory:{settings.VECTOR_MEMORY_PORT}/store/capsule",
                json=capsule.model_dump()
            )
            
            if response.status_code == 200:
                activity.logger.info("✅ Capsule also stored in vector memory for search")
            else:
                activity.logger.warning(f"Failed to store in vector memory: {response.status_code}")
                
    except Exception as e:
        activity.logger.warning(f"Failed to store in vector memory: {str(e)}")
    
    # Return capsule information
    return {
        "capsule_id": str(capsule.id),
        "manifest": capsule.manifest,
        "files": {
            "source": list(capsule.source_code.keys()),
            "tests": list(capsule.tests.keys()),
            "docs": ["README.md"] if capsule.documentation else []
        },
        "metadata": capsule.metadata,
        "database_saved": database_saved,
        "storage_locations": ["postgresql"] + (["vector_memory"] if database_saved else [])
    }


def _is_test_code(code: str) -> bool:
    """Check if code is test code based on content analysis"""
    if not code:
        return False
    
    code_lower = code.lower()
    
    test_indicators = [
        # Python
        "import pytest", "from pytest", "import unittest", "from unittest",
        "def test_", "class test", "unittest.main", "pytest.main",
        # JavaScript/TypeScript  
        "import { expect }", "from 'chai'", "from 'mocha'", "describe(", "it(", "test(",
        # Java
        "import org.junit", "@test", "@before", "@after",
        # Go
        "import \"testing\"", "func test", "t.error", "t.fail"
    ]
    
    return any(indicator in code_lower for indicator in test_indicators)


def _is_documentation(code: str) -> bool:
    """Check if content is primarily documentation"""
    if not code:
        return False
    
    code_lower = code.lower()
    doc_indicators = [
        "# documentation", "# readme", "## ", "### ", 
        "readme", "documentation", "getting started", "installation",
        "usage", "examples", "api reference"
    ]
    
    return any(indicator in code_lower for indicator in doc_indicators)