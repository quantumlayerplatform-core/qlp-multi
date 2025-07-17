#!/usr/bin/env python3
"""
Client library for consuming progress streams
Provides easy-to-use clients for both WebSocket and SSE connections
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, AsyncIterator
import httpx
import websockets
from websockets.exceptions import WebSocketException
import structlog

logger = structlog.get_logger(__name__)


class ProgressWebSocketClient:
    """WebSocket client for receiving progress updates"""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.connection = None
        self.workflow_id = None
        self._running = False
    
    async def connect(self, workflow_id: str) -> None:
        """Connect to the progress WebSocket"""
        self.workflow_id = workflow_id
        url = f"{self.base_url}/ws/progress/{workflow_id}"
        
        logger.info("Connecting to progress WebSocket", url=url)
        self.connection = await websockets.connect(url)
        self._running = True
        logger.info("Connected to progress WebSocket")
    
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket"""
        self._running = False
        if self.connection:
            await self.connection.close()
            self.connection = None
        logger.info("Disconnected from progress WebSocket")
    
    async def listen(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Listen for progress events and call the callback"""
        if not self.connection:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            while self._running:
                try:
                    message = await self.connection.recv()
                    
                    # Handle ping/pong
                    if message == "ping":
                        await self.connection.send("pong")
                        continue
                    
                    # Parse and handle progress event
                    try:
                        event = json.loads(message)
                        await callback(event)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON received", message=message)
                        
                except WebSocketException as e:
                    logger.error("WebSocket error", error=e)
                    break
                    
        finally:
            await self.disconnect()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class ProgressSSEClient:
    """Server-Sent Events client for receiving progress updates"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=None)  # No timeout for SSE
    
    async def stream_events(
        self, 
        workflow_id: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream progress events using SSE"""
        url = f"{self.base_url}/progress/stream/{workflow_id}"
        params = {}
        if user_id:
            params["user_id"] = user_id
        if tenant_id:
            params["tenant_id"] = tenant_id
        
        logger.info("Starting SSE stream", url=url, params=params)
        
        async with self.client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            
            buffer = ""
            async for line in response.aiter_lines():
                buffer += line + "\n"
                
                # Check if we have a complete event
                if line == "" and buffer.strip():
                    # Parse the event
                    event_data = {}
                    event_id = None
                    event_type = None
                    
                    for event_line in buffer.strip().split("\n"):
                        if event_line.startswith("id:"):
                            event_id = event_line[3:].strip()
                        elif event_line.startswith("event:"):
                            event_type = event_line[6:].strip()
                        elif event_line.startswith("data:"):
                            try:
                                event_data = json.loads(event_line[5:].strip())
                            except json.JSONDecodeError:
                                logger.warning("Invalid JSON in SSE data", line=event_line)
                    
                    if event_data:
                        yield event_data
                    
                    buffer = ""
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class ProgressClient:
    """High-level client that can use either WebSocket or SSE"""
    
    def __init__(self, base_url: str = "http://localhost:8000", use_websocket: bool = True):
        self.base_url = base_url
        self.use_websocket = use_websocket
        self.events = []
        self._task = None
    
    async def track_workflow(
        self,
        workflow_id: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        store_events: bool = True
    ) -> None:
        """Track a workflow's progress"""
        
        async def handle_event(event: Dict[str, Any]):
            if store_events:
                self.events.append(event)
            
            # Log the event
            event_type = event.get("type", "unknown")
            logger.info(f"Progress event: {event_type}",
                       workflow_id=workflow_id,
                       event=event)
            
            # Call custom callback if provided
            if callback:
                await callback(event)
        
        if self.use_websocket:
            # Use WebSocket
            async with ProgressWebSocketClient(self.base_url) as client:
                await client.connect(workflow_id)
                await client.listen(handle_event)
        else:
            # Use SSE
            async with ProgressSSEClient(self.base_url) as client:
                async for event in client.stream_events(workflow_id):
                    await handle_event(event)
    
    def get_events(self) -> list[Dict[str, Any]]:
        """Get all stored events"""
        return self.events
    
    def get_events_by_type(self, event_type: str) -> list[Dict[str, Any]]:
        """Get events of a specific type"""
        return [e for e in self.events if e.get("type") == event_type]
    
    def get_latest_status(self) -> Optional[Dict[str, Any]]:
        """Get the latest status update"""
        status_events = self.get_events_by_type("status_update")
        return status_events[-1] if status_events else None
    
    def is_completed(self) -> bool:
        """Check if the workflow completed"""
        return any(e.get("type") == "workflow_completed" for e in self.events)
    
    def is_failed(self) -> bool:
        """Check if the workflow failed"""
        return any(e.get("type") == "workflow_failed" for e in self.events)


# Example usage
async def example_usage():
    """Example of how to use the progress client"""
    
    # Custom callback for handling events
    async def on_progress_event(event: Dict[str, Any]):
        event_type = event.get("type")
        data = event.get("data", {})
        
        if event_type == "activity_progress":
            progress = data.get("progress", 0)
            message = data.get("message", "")
            print(f"Progress: {progress*100:.1f}% - {message}")
        
        elif event_type == "activity_completed":
            print(f"Activity completed: {data.get('activity_name', 'unknown')}")
        
        elif event_type == "workflow_completed":
            print("Workflow completed successfully!")
            
        elif event_type == "workflow_failed":
            print(f"Workflow failed: {data.get('error', 'unknown error')}")
    
    # Track a workflow
    workflow_id = "example-workflow-123"
    client = ProgressClient(use_websocket=True)
    
    try:
        await client.track_workflow(
            workflow_id=workflow_id,
            callback=on_progress_event
        )
    except KeyboardInterrupt:
        print("\nStopped tracking workflow")
    
    # Print summary
    print(f"\nTotal events received: {len(client.get_events())}")
    print(f"Completed: {client.is_completed()}")
    print(f"Failed: {client.is_failed()}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())
