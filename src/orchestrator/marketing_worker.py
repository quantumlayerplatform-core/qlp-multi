"""
Dedicated Marketing Temporal Worker
Handles marketing workflows on a separate queue
"""

import asyncio
import logging
from datetime import timedelta
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

# Import marketing workflows and activities
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

async def run_marketing_worker(task_queue: str = "marketing-queue"):
    """Run the dedicated marketing worker"""
    
    # Connect to Temporal using the cloud-aware helper
    client = await get_temporal_client()
    
    # Create worker with marketing workflows and activities
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            MarketingWorkflow,
            ContentGenerationWorkflow,
            CampaignOptimizationWorkflow
        ],
        activities=[
            generate_campaign_strategy,
            create_content_calendar,
            generate_content_piece,
            optimize_content_batch,
            collect_campaign_analytics,
            apply_campaign_optimizations,
            create_marketing_capsule
        ],
    )
    
    logger.info(f"Starting Marketing Temporal Worker on queue: {task_queue}")
    logger.info("Registered marketing workflows: MarketingWorkflow, ContentGenerationWorkflow, CampaignOptimizationWorkflow")
    
    # Run the worker
    await worker.run()


def main():
    """Main entry point"""
    import os
    
    # Get configuration from environment
    temporal_host = os.getenv("TEMPORAL_SERVER", "temporal:7233")
    task_queue = os.getenv("MARKETING_TASK_QUEUE", "marketing-queue")
    
    logger.info("=== Marketing Temporal Worker Starting ===")
    logger.info(f"Temporal Server: {temporal_host}")
    logger.info(f"Task Queue: {task_queue}")
    logger.info("==========================================")
    
    asyncio.run(run_marketing_worker(temporal_host, task_queue))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Marketing worker shutdown requested")
    except Exception as e:
        logger.error(f"Marketing worker failed: {e}", exc_info=True)
        raise