#!/usr/bin/env python3
"""
Test Temporal Cloud connection with API key authentication
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from src.common.temporal_cloud import get_temporal_client
import structlog

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

async def test_temporal_connection():
    """Test connection to Temporal Cloud"""
    logger.info("Starting Temporal Cloud connection test")
    
    # Log environment variables (without exposing sensitive data)
    temporal_server = os.getenv('TEMPORAL_SERVER', 'Not set')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'Not set')
    api_key_set = bool(os.getenv('TEMPORAL_CLOUD_API_KEY'))
    
    logger.info("Environment configuration",
                temporal_server=temporal_server,
                temporal_namespace=temporal_namespace,
                api_key_configured=api_key_set)
    
    if not api_key_set:
        logger.error("TEMPORAL_CLOUD_API_KEY not set in environment")
        return False
    
    try:
        # Attempt to connect using the helper function
        logger.info("Attempting to connect to Temporal Cloud...")
        client = await get_temporal_client()
        
        # Test the connection by listing workflows (should return empty if no workflows)
        logger.info("Testing connection by listing workflows...")
        
        # Create a workflow query
        workflows = []
        async for workflow in client.list_workflows():
            workflows.append(workflow.id)
            if len(workflows) >= 5:  # Just get first 5 for testing
                break
        
        logger.info(f"Successfully connected! Found {len(workflows)} workflows")
        if workflows:
            logger.info(f"Sample workflow IDs: {workflows[:5]}")
        
        # Get namespace info
        logger.info("Connection test successful!", 
                   namespace=temporal_namespace,
                   server=temporal_server)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to Temporal Cloud: {e}")
        logger.exception("Detailed error:")
        return False

async def test_workflow_execution():
    """Test creating a simple workflow execution"""
    try:
        from temporalio import workflow
        from temporalio.worker import Worker
        
        @workflow.defn
        class TestWorkflow:
            @workflow.run
            async def run(self) -> str:
                return "Hello from Temporal Cloud!"
        
        client = await get_temporal_client()
        
        # Try to start a test workflow
        logger.info("Attempting to start a test workflow...")
        
        handle = await client.start_workflow(
            TestWorkflow.run,
            id=f"test-cloud-connection-{os.getpid()}",
            task_queue="test-queue"
        )
        
        logger.info(f"Started workflow with ID: {handle.id}")
        
        # Note: We won't wait for result as we don't have a worker running
        logger.info("Workflow started successfully (not waiting for completion)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start test workflow: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Temporal Cloud Connection Test")
    logger.info("=" * 60)
    
    # Test 1: Basic connection
    connection_ok = await test_temporal_connection()
    
    if connection_ok:
        logger.info("✅ Basic connection test PASSED")
        
        # Test 2: Try to start a workflow
        logger.info("\nTesting workflow creation...")
        workflow_ok = await test_workflow_execution()
        
        if workflow_ok:
            logger.info("✅ Workflow creation test PASSED")
        else:
            logger.warning("⚠️  Workflow creation test FAILED (this might be expected)")
    else:
        logger.error("❌ Basic connection test FAILED")
        logger.error("Please check your Temporal Cloud credentials:")
        logger.error("1. TEMPORAL_SERVER should be set to us-west-2.aws.api.temporal.io:7233")
        logger.error("2. TEMPORAL_NAMESPACE should be set to qlp-beta.f6bob")
        logger.error("3. TEMPORAL_CLOUD_API_KEY should contain your API key")
        sys.exit(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())