"""
Temporal Cloud connection helper with API key authentication
"""
import os
from temporalio.client import Client, TLSConfig
import structlog

logger = structlog.get_logger()

async def get_temporal_client():
    """
    Get Temporal client with cloud support using API key authentication
    Based on official Temporal Cloud documentation
    """
    temporal_server = os.getenv('TEMPORAL_SERVER', 'temporal:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    
    # Check if we're using Temporal Cloud
    if 'tmprl.cloud' in temporal_server or 'temporal.io' in temporal_server:
        api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
        
        if not api_key:
            raise ValueError("TEMPORAL_CLOUD_API_KEY is required for Temporal Cloud")
        
        logger.info(f"Connecting to Temporal Cloud: {temporal_server}")
        logger.info(f"Namespace: {temporal_namespace}")
        
        try:
            # Connect with API key parameter (SDK 1.14.1+)
            client = await Client.connect(
                temporal_server,
                namespace=temporal_namespace,
                api_key=api_key,
                tls=True
            )
            logger.info("Successfully connected to Temporal Cloud")
        except Exception as e:
            logger.error(f"Failed to connect to Temporal Cloud: {e}")
            raise
    else:
        # Local Temporal server
        logger.info(f"Connecting to local Temporal: {temporal_server}")
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace
        )
    
    return client

# For backward compatibility
async def create_temporal_client(server: str = None, namespace: str = None):
    """
    Create Temporal client with optional overrides
    """
    if server:
        os.environ['TEMPORAL_SERVER'] = server
    if namespace:
        os.environ['TEMPORAL_NAMESPACE'] = namespace
    
    return await get_temporal_client()