#!/usr/bin/env python3
"""Debug Temporal connection issue in FastAPI context"""

import asyncio
import sys
import os
sys.path.insert(0, '/app' if os.path.exists('/app') else '.')

from fastapi import FastAPI
from temporalio.client import Client
import uvicorn
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Test connection during startup"""
    try:
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        logger.info(f"✅ Startup: Connected to {settings.TEMPORAL_SERVER}")
    except Exception as e:
        logger.error(f"❌ Startup: Failed to connect: {e}")

@app.get("/test1")
async def test_simple():
    """Simple connection test"""
    try:
        client = await Client.connect("temporal:7233")
        return {"status": "success", "method": "direct"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/test2")
async def test_with_settings():
    """Connection with settings"""
    try:
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        return {"status": "success", "method": "settings", "server": settings.TEMPORAL_SERVER}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/test3")
async def test_after_imports():
    """Connection after marketing imports"""
    try:
        # Import marketing modules
        from src.agents.marketing.orchestrator import MarketingOrchestrator
        orchestrator = MarketingOrchestrator()
        
        # Try connection
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        return {"status": "success", "method": "after_imports"}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}

@app.get("/test4") 
async def test_marketing_api_pattern():
    """Test exact pattern from marketing API"""
    try:
        from src.common.config import settings
        logger.info(f"Connecting to {settings.TEMPORAL_SERVER}")
        
        # This is the exact pattern from marketing API
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        # No need to close the client
        return {"status": "success", "method": "marketing_api_pattern"}
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return {"status": "error", "error": str(e), "type": type(e).__name__}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9997)