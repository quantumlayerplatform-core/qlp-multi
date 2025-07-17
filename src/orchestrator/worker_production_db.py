"""
Production Temporal Worker with Database Persistence
This is the production configuration with PostgreSQL storage enabled
"""

import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
from src.common.temporal_cloud import get_temporal_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all required activities and workflow
from src.orchestrator.worker_production import (
    # Workflow
    QLPWorkflow,
    # Activities
    decompose_request_activity,
    select_agent_tier_activity,
    execute_in_sandbox_activity,
    request_aitl_review_activity,
    llm_clean_code_activity,
    create_ql_capsule_activity,  # Import the original activity
    prepare_delivery_activity,  # Import the delivery preparation activity
    push_to_github_activity,  # Import the GitHub push activity
    monitor_github_actions_activity,  # Import the GitHub Actions monitoring activity
    save_workflow_checkpoint_activity,  # Import checkpoint activity
    load_workflow_checkpoint_activity,  # Import load checkpoint activity
    stream_workflow_results_activity,  # Import streaming activity
)

# Import original activities - we'll override them with enhanced versions below
from src.orchestrator.worker_production import (
    execute_task_activity as original_execute_task_activity,
    validate_result_activity as original_validate_result_activity
)

# Import enhanced activities with enterprise heartbeat management
from src.orchestrator.worker_production_enhanced import (
    execute_task_activity_enhanced
)

# Import marketing workflows and activities
try:
    from src.orchestrator.marketing_workflow import (
        MarketingWorkflow,
        ContentGenerationWorkflow,
        CampaignOptimizationWorkflow,
        generate_campaign_strategy,
        create_content_calendar,
        generate_content_piece,
        optimize_content_batch,
        collect_campaign_analytics,
        apply_campaign_optimizations,
        create_marketing_capsule
    )
    marketing_available = True
    logger.info("Marketing workflows and activities imported successfully")
except ImportError as e:
    marketing_available = False
    logger.warning(f"Marketing workflows not available: {e}")

# Import the database-enabled capsule activity as well
from src.orchestrator.activities.capsule_activities import create_ql_capsule_activity_with_db

# Create wrapper activities with the correct names
@activity.defn(name="execute_task_activity")
async def execute_task_activity(task: Dict[str, Any], tier: str, request_id: str, shared_context_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for enhanced execute task activity"""
    return await execute_task_activity_enhanced(task, tier, request_id, shared_context_dict)

@activity.defn(name="validate_result_activity")
async def validate_result_activity(result: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper that uses the original validate result activity"""
    return await original_validate_result_activity(result, task)


async def run_worker(task_queue: str = "qlp-production-queue"):
    """Run the production worker with database persistence"""
    
    # Connect to Temporal using the cloud-aware helper
    client = await get_temporal_client()
    
    # Build workflows list
    workflows = [QLPWorkflow]
    
    # Build activities list
    activities = [
        decompose_request_activity,
        select_agent_tier_activity,
        execute_task_activity,  # Now uses enhanced version with heartbeat management
        validate_result_activity,  # Now uses enhanced version with heartbeat management
        execute_in_sandbox_activity,
        request_aitl_review_activity,
        llm_clean_code_activity,
        create_ql_capsule_activity,  # Original activity from worker_production
        create_ql_capsule_activity_with_db,  # Database-enabled version
        prepare_delivery_activity,  # Delivery preparation activity
        push_to_github_activity,  # GitHub push activity
        monitor_github_actions_activity,  # GitHub Actions monitoring
        save_workflow_checkpoint_activity,  # Checkpoint saving
        load_workflow_checkpoint_activity,  # Checkpoint loading
        stream_workflow_results_activity,  # Results streaming
    ]
    
    # Add marketing workflows and activities if available
    if marketing_available:
        workflows.extend([
            MarketingWorkflow,
            ContentGenerationWorkflow,
            CampaignOptimizationWorkflow
        ])
        activities.extend([
            generate_campaign_strategy,
            create_content_calendar,
            generate_content_piece,
            optimize_content_batch,
            collect_campaign_analytics,
            apply_campaign_optimizations,
            create_marketing_capsule
        ])
        logger.info("Marketing workflows and activities added to worker")
    
    # Create worker with all workflows and activities
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
    )
    
    logger.info("Starting Production Temporal Worker with PostgreSQL persistence")
    logger.info(f"Connected to Temporal Cloud")
    logger.info(f"Task queue: {task_queue}")
    logger.info("✅ Database persistence enabled for capsule storage")
    
    # Run the worker
    await worker.run()


def main():
    """Main entry point"""
    import os
    
    # Get configuration from environment
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "qlp-production-queue")
    
    logger.info("=== Production Temporal Worker Starting ===")
    logger.info("Temporal: Using Cloud Configuration")
    logger.info(f"Task Queue: {task_queue}")
    logger.info("Database: PostgreSQL (qlp_db)")
    logger.info("=========================================")
    
    try:
        asyncio.run(run_worker(task_queue))
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    main()