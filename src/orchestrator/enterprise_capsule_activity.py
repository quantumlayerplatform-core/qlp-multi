"""
Enterprise Capsule Generation Activity
Temporal activity for generating enterprise-grade capsules using the CapsuleGeneratorAgent
"""

from typing import Dict, Any, List
from temporalio import activity
import structlog

logger = structlog.get_logger()


@activity.defn
async def create_enterprise_capsule_activity(
    request_id: str,
    tasks: List[Dict[str, Any]],
    results: List[Dict[str, Any]], 
    shared_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create an enterprise-grade capsule using the CapsuleGeneratorAgent.
    
    This activity:
    1. Uses the CapsuleGeneratorAgent to analyze project context
    2. Generates comprehensive documentation
    3. Creates CI/CD pipelines
    4. Adds best practices configurations
    5. Packages everything into a production-ready capsule
    """
    # Import inside activity to avoid Temporal sandbox restrictions
    from src.agents.capsule_generator_agent import CapsuleGeneratorAgent
    from src.common.models import Task, TaskStatus, QLCapsule
    from src.orchestrator.shared_context import SharedContext
    
    activity.logger.info(f"Creating enterprise capsule for request {request_id}")
    
    try:
        # Send heartbeat
        activity.heartbeat("Initializing enterprise capsule generation")
        
        # Initialize the CapsuleGeneratorAgent
        capsule_agent = CapsuleGeneratorAgent()
        
        # Convert shared context dict back to object
        shared_ctx = SharedContext(**shared_context)
        original_request = shared_ctx.original_request
        
        # Create a special task for the capsule generator
        capsule_task = Task(
            id=f"capsule-gen-{request_id}",
            type="enterprise_capsule_generation",
            description="Generate enterprise-grade capsule with full documentation and best practices",
            complexity="complex",
            status=TaskStatus.IN_PROGRESS,
            metadata={
                "request_id": request_id,
                "task_count": len(tasks),
                "result_count": len(results)
            }
        )
        
        # Send heartbeat
        activity.heartbeat("Analyzing project context")
        
        # Execute the capsule generation
        task_result = await capsule_agent.execute(
            task=capsule_task,
            context={
                "tasks": tasks,
                "results": results,
                "original_request": original_request,
                "shared_context": shared_context
            }
        )
        
        # Send heartbeat
        activity.heartbeat("Building enterprise capsule structure")
        
        if task_result.output_type == "error":
            activity.logger.error(f"Enterprise capsule generation failed: {task_result.output}")
            return {
                "success": False,
                "error": task_result.output.get("error", "Unknown error"),
                "metadata": task_result.metadata
            }
        
        # Extract the enterprise structure
        enterprise_output = task_result.output
        metadata = enterprise_output.get("metadata", {})
        structure = enterprise_output.get("structure", {})
        
        # Create the QLCapsule with enterprise structure
        capsule = QLCapsule(
            id=f"qlc-{request_id}",
            request_id=request_id,
            manifest={
                "version": "2.0",
                "type": "enterprise",
                "created_by": "CapsuleGeneratorAgent",
                "language": metadata.get("primary_language", "multi"),
                "frameworks": metadata.get("frameworks", []),
                "project_type": metadata.get("project_type", "general"),
                "architecture_pattern": metadata.get("architecture_pattern", "modular"),
                "deployment_targets": metadata.get("deployment_targets", []),
                "total_files": metadata.get("total_files", 0),
                "has_tests": metadata.get("has_tests", False),
                "has_docs": metadata.get("has_docs", False),
                "has_ci_cd": metadata.get("has_ci_cd", False)
            },
            source_code=structure.get("source_files", {}),
            tests=structure.get("test_files", {}),
            documentation=structure.get("documentation_files", {}).get("README.md", ""),
            deployment_config={
                "docker": structure.get("deployment_files", {}),
                "ci_cd": structure.get("ci_cd_files", {}),
                "configs": structure.get("config_files", {})
            },
            metadata={
                "enterprise_features": {
                    "documentation_files": list(structure.get("documentation_files", {}).keys()),
                    "config_files": list(structure.get("config_files", {}).keys()),
                    "ci_cd_files": list(structure.get("ci_cd_files", {}).keys()),
                    "deployment_files": list(structure.get("deployment_files", {}).keys()),
                    "script_files": list(structure.get("script_files", {}).keys())
                },
                "generation_metadata": metadata,
                "agent_confidence": task_result.confidence_score,
                "execution_time": task_result.execution_time
            }
        )
        
        # Send heartbeat
        activity.heartbeat("Storing enterprise capsule")
        
        # Store the capsule
        # NOTE: In production, this would save to PostgreSQL via the capsule storage service
        # For now, we'll return the capsule data
        
        activity.logger.info(
            f"Enterprise capsule created successfully",
            capsule_id=capsule.id,
            total_files=capsule.manifest.get("total_files", 0),
            languages=metadata.get("languages", []),
            has_tests=capsule.manifest.get("has_tests", False),
            has_docs=capsule.manifest.get("has_docs", False),
            has_ci_cd=capsule.manifest.get("has_ci_cd", False)
        )
        
        # Return complete file structure for storage
        all_files = {}
        
        # Add all files from different categories
        all_files.update(structure.get("source_files", {}))
        all_files.update(structure.get("test_files", {}))
        all_files.update(structure.get("documentation_files", {}))
        all_files.update(structure.get("deployment_files", {}))
        all_files.update(structure.get("ci_cd_files", {}))
        all_files.update(structure.get("config_files", {}))
        all_files.update(structure.get("script_files", {}))
        
        return {
            "success": True,
            "capsule_id": capsule.id,
            "capsule": capsule.model_dump(),
            "files": all_files,
            "metadata": {
                "is_enterprise": True,
                "total_files": len(all_files),
                "file_categories": {
                    "source": len(structure.get("source_files", {})),
                    "tests": len(structure.get("test_files", {})),
                    "docs": len(structure.get("documentation_files", {})),
                    "deployment": len(structure.get("deployment_files", {})),
                    "ci_cd": len(structure.get("ci_cd_files", {})),
                    "configs": len(structure.get("config_files", {})),
                    "scripts": len(structure.get("script_files", {}))
                },
                "project_info": metadata
            }
        }
        
    except Exception as e:
        activity.logger.error(f"Error creating enterprise capsule: {e}")
        return {
            "success": False,
            "error": str(e),
            "metadata": {
                "error_type": type(e).__name__,
                "request_id": request_id
            }
        }