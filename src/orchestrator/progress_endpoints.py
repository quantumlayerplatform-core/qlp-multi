#!/usr/bin/env python3
"""
Progress streaming endpoints for the orchestrator service
Provides WebSocket and SSE endpoints for real-time workflow updates
"""

from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import StreamingResponse
import structlog

from src.common.progress_streaming import (
    progress_manager,
    ProgressEvent,
    ProgressEventType,
    create_progress_reporter
)
from src.common.structured_logging import LogContext

logger = structlog.get_logger(__name__)


async def websocket_progress_endpoint(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for streaming workflow progress
    
    Connect with: ws://localhost:8000/ws/progress/{workflow_id}
    """
    with LogContext(workflow_id=workflow_id, connection_type="websocket"):
        try:
            # Connect the websocket
            await progress_manager.connect_websocket(websocket, workflow_id)
            logger.info("WebSocket client connected for progress updates")
            
            # Keep the connection open
            while True:
                # Wait for client messages (like ping/pong)
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error("WebSocket error", error=e)
        finally:
            await progress_manager.disconnect_websocket(websocket, workflow_id)


async def sse_progress_endpoint(
    workflow_id: str,
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None)
):
    """
    Server-Sent Events endpoint for streaming workflow progress
    
    Connect with: GET /progress/stream/{workflow_id}
    """
    with LogContext(workflow_id=workflow_id, user_id=user_id, tenant_id=tenant_id):
        logger.info("SSE client connected for progress updates")
        
        # Create the event stream
        event_stream = progress_manager.create_sse_stream(workflow_id)
        
        return StreamingResponse(
            event_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )


async def get_progress_metrics():
    """
    Get metrics about the progress streaming system
    """
    metrics = progress_manager.get_metrics()
    return {
        "status": "healthy",
        "metrics": metrics
    }


def register_progress_endpoints(app):
    """
    Register progress streaming endpoints with the FastAPI app
    """
    # WebSocket endpoint
    app.websocket("/ws/progress/{workflow_id}")(websocket_progress_endpoint)
    
    # SSE endpoint
    app.get("/progress/stream/{workflow_id}")(sse_progress_endpoint)
    
    # Metrics endpoint
    app.get("/progress/metrics")(get_progress_metrics)
    
    # Startup/shutdown events
    @app.on_event("startup")
    async def start_progress_manager():
        await progress_manager.start()
        logger.info("Progress streaming manager started")
    
    @app.on_event("shutdown")
    async def stop_progress_manager():
        await progress_manager.stop()
        logger.info("Progress streaming manager stopped")
