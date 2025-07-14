#!/usr/bin/env python3
"""Debug temporal connection issue in marketing API"""

import asyncio
from fastapi import FastAPI
from temporalio.client import Client
import uvicorn

app = FastAPI()

@app.get("/test1")
async def test1():
    """Direct connection test"""
    try:
        client = await Client.connect("temporal:7233")
        return {"status": "success", "message": "Direct connection works"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/test2")
async def test2():
    """Connection with settings"""
    try:
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        return {"status": "success", "message": "Settings connection works"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/test3")
async def test3():
    """Test with marketing imports"""
    try:
        from src.agents.marketing.orchestrator import MarketingOrchestrator
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        return {"status": "success", "message": "Marketing imports + connection works"}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)