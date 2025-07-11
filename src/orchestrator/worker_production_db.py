"""
Production Temporal Worker with Database Persistence
This is the production configuration with PostgreSQL storage enabled
"""

import asyncio
import logging
from datetime import timedelta
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

# Import all required activities and workflow
from src.orchestrator.worker_production import (
    # Workflow
    QLPWorkflow,
    # Activities
    decompose_request_activity,
    select_agent_tier_activity,
    execute_task_activity,
    validate_result_activity,
    test_in_sandbox_activity,
    hitl_review_activity,
    aitl_review_activity,
    prepare_delivery_activity,
    # We'll override create_ql_capsule_activity with the DB version
)

# Import the database-enabled capsule activity with proper name
from src.orchestrator.activities.capsule_activities import create_ql_capsule_activity_with_db

# Alias for workflow compatibility
create_ql_capsule_activity = create_ql_capsule_activity_with_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_worker(temporal_host: str = "temporal:7233", task_queue: str = "qlp-main"):
    """Run the production worker with database persistence"""
    
    # Connect to Temporal
    client = await Client.connect(temporal_host)
    
    # Create worker with all activities including database-enabled capsule creation
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[QLPWorkflow],
        activities=[
            decompose_request_activity,
            select_agent_tier_activity,
            execute_task_activity,
            validate_result_activity,
            test_in_sandbox_activity,
            hitl_review_activity,
            create_ql_capsule_activity,  # Database-enabled version (aliased above)
            aitl_review_activity,
            prepare_delivery_activity
        ],
    )
    
    logger.info("Starting Production Temporal Worker with PostgreSQL persistence")
    logger.info(f"Connected to Temporal at: {temporal_host}")
    logger.info(f"Task queue: {task_queue}")
    logger.info("✅ Database persistence enabled for capsule storage")
    
    # Run the worker
    await worker.run()


def main():
    """Main entry point"""
    import os
    
    # Get configuration from environment
    temporal_host = os.getenv("TEMPORAL_SERVER", "temporal:7233")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "qlp-main")
    
    logger.info("=== Production Temporal Worker Starting ===")
    logger.info(f"Temporal Server: {temporal_host}")
    logger.info(f"Task Queue: {task_queue}")
    logger.info("Database: PostgreSQL (qlp_db)")
    logger.info("=========================================")
    
    try:
        asyncio.run(run_worker(temporal_host, task_queue))
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    main()