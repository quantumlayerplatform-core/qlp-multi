"""
Workflow selector - choose appropriate workflow based on request complexity
"""

from typing import Dict, Any, Type
from temporalio import workflow

# Import workflows
from .worker_production import QLPWorkflow
from .enterprise_worker import EnterpriseQLPWorkflow


def get_workflow_class(request: Dict[str, Any]) -> Type[workflow.Workflow]:
    """
    Select appropriate workflow class based on request characteristics
    """
    
    # Check for enterprise indicators
    metadata = request.get("metadata", {})
    
    # Enterprise criteria
    is_enterprise = any([
        metadata.get("project_type") in ["enterprise_saas", "ecommerce_platform", "microservices"],
        metadata.get("priority") in ["critical", "high"],
        metadata.get("estimated_complexity") in ["very_high", "high"],
        "enterprise" in request.get("description", "").lower(),
        "microservice" in request.get("description", "").lower(),
        len(request.get("description", "")) > 1000,  # Long descriptions typically mean complex projects
    ])
    
    # Task count estimation (rough)
    description_length = len(request.get("description", ""))
    estimated_tasks = description_length // 100  # Rough estimate
    
    if is_enterprise or estimated_tasks > 10:
        return EnterpriseQLPWorkflow
    else:
        return QLPWorkflow


def get_workflow_timeout(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get appropriate timeouts based on request
    """
    from datetime import timedelta
    
    workflow_class = get_workflow_class(request)
    
    if workflow_class == EnterpriseQLPWorkflow:
        return {
            "workflow_execution_timeout": timedelta(hours=4),
            "workflow_run_timeout": timedelta(hours=3),
            "workflow_task_timeout": timedelta(minutes=15)
        }
    else:
        return {
            "workflow_execution_timeout": timedelta(hours=2),
            "workflow_run_timeout": timedelta(hours=1.5),
            "workflow_task_timeout": timedelta(minutes=10)
        }