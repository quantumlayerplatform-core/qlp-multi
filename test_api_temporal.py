#!/usr/bin/env python3
"""Test API temporal connection issue"""

import asyncio
import sys
sys.path.insert(0, '/app')

from fastapi import FastAPI
from temporalio.client import Client
import uvicorn

# Try importing marketing API to see if it causes issues
from src.api.v2.marketing_api import router

app = FastAPI()

# Include the marketing router
app.include_router(router)

# Add a test endpoint
@app.get("/test-connection")
async def test_connection():
    """Test temporal connection"""
    from src.common.config import settings
    try:
        client = await Client.connect(settings.TEMPORAL_SERVER)
        return {"status": "success", "server": settings.TEMPORAL_SERVER}
    except Exception as e:
        return {"status": "error", "error": str(e), "server": settings.TEMPORAL_SERVER}

if __name__ == "__main__":
    print("Starting test server on port 9998...")
    uvicorn.run(app, host="0.0.0.0", port=9998)