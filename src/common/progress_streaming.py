#!/usr/bin/env python3
"""
Progress streaming implementation for real-time updates
Provides WebSocket and SSE (Server-Sent Events) support for streaming progress
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator, Callable
from enum import Enum
import structlog
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from collections import defaultdict
from dataclasses import dataclass, asdict
import weakref

logger = structlog.get_logger(__name__)


class ProgressEventType(Enum):
    """Types of progress events"""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    ACTIVITY_STARTED = "activity_started"
    ACTIVITY_PROGRESS = "activity_progress"
    ACTIVITY_COMPLETED = "activity_completed"
    ACTIVITY_FAILED = "activity_failed"
    
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    LOG_MESSAGE = "log_message"
    METRICS_UPDATE = "metrics_update"
    STATUS_UPDATE = "status_update"


@dataclass
class ProgressEvent:
    """Progress event data structure"""
    id: str
    type: ProgressEventType
    timestamp: datetime
    source: str  # Service or component name
    data: Dict[str, Any]
    workflow_id: Optional[str] = None
    activity_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['type'] = self.type.value
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format"""
        data = json.dumps(self.to_dict())
        return f"id: {self.id}\nevent: {self.type.value}\ndata: {data}\n\n"


class ProgressStreamManager:
    """Manages progress streaming connections and event distribution"""
    
    def __init__(self):
        # Store active connections by workflow ID
        self._websocket_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self._sse_queues: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        
        # Store recent events for late joiners (last 100 events per workflow)
        self._event_history: Dict[str, List[ProgressEvent]] = defaultdict(list)
        self._history_limit = 100
        
        # Metrics
        self._connection_count = 0
        self._event_count = 0
        
        # Cleanup task
        self._cleanup_task = None
    
    async def start(self):
        """Start the manager and cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        logger.info("Progress stream manager started")
    
    async def stop(self):
        """Stop the manager and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for workflow_id in list(self._websocket_connections.keys()):
            await self._close_workflow_connections(workflow_id)
        
        logger.info("Progress stream manager stopped")
    
    async def _cleanup_inactive_connections(self):
        """Periodically clean up inactive connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Clean up closed WebSocket connections
                for workflow_id, connections in list(self._websocket_connections.items()):
                    active_connections = []
                    for ws in connections:
                        try:
                            # Send ping to check if connection is alive
                            await ws.send_json({"type": "ping"})
                            active_connections.append(ws)
                        except:
                            logger.debug("Removing inactive WebSocket connection",
                                       workflow_id=workflow_id)
                    
                    if active_connections:
                        self._websocket_connections[workflow_id] = active_connections
                    else:
                        del self._websocket_connections[workflow_id]
                
                # Clean up old event history (older than 1 hour)
                cutoff_time = datetime.utcnow().timestamp() - 3600
                for workflow_id, events in list(self._event_history.items()):
                    self._event_history[workflow_id] = [
                        e for e in events 
                        if e.timestamp.timestamp() > cutoff_time
                    ]
                    if not self._event_history[workflow_id]:
                        del self._event_history[workflow_id]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup task", error=e)
    
    async def connect_websocket(self, websocket: WebSocket, workflow_id: str) -> None:
        """Connect a WebSocket client for workflow updates"""
        await websocket.accept()
        self._websocket_connections[workflow_id].append(websocket)
        self._connection_count += 1
        
        logger.info("WebSocket connected",
                   workflow_id=workflow_id,
                   total_connections=self._connection_count)
        
        # Send history to new connection
        if workflow_id in self._event_history:
            for event in self._event_history[workflow_id]:
                try:
                    await websocket.send_json(event.to_dict())
                except:
                    break
    
    async def disconnect_websocket(self, websocket: WebSocket, workflow_id: str) -> None:
        """Disconnect a WebSocket client"""
        if workflow_id in self._websocket_connections:
            if websocket in self._websocket_connections[workflow_id]:
                self._websocket_connections[workflow_id].remove(websocket)
                self._connection_count -= 1
                
                if not self._websocket_connections[workflow_id]:
                    del self._websocket_connections[workflow_id]
        
        logger.info("WebSocket disconnected",
                   workflow_id=workflow_id,
                   remaining_connections=self._connection_count)
    
    def create_sse_stream(self, workflow_id: str) -> AsyncGenerator[str, None]:
        """Create an SSE stream for workflow updates"""
        queue = asyncio.Queue()
        self._sse_queues[workflow_id].append(queue)
        
        async def stream_generator():
            try:
                # Send history first
                if workflow_id in self._event_history:
                    for event in self._event_history[workflow_id]:
                        yield event.to_sse()
                
                # Stream new events
                while True:
                    event = await queue.get()
                    if event is None:  # Sentinel to close stream
                        break
                    yield event.to_sse()
                    
            finally:
                if workflow_id in self._sse_queues:
                    if queue in self._sse_queues[workflow_id]:
                        self._sse_queues[workflow_id].remove(queue)
                    if not self._sse_queues[workflow_id]:
                        del self._sse_queues[workflow_id]
        
        return stream_generator()
    
    async def publish_event(self, event: ProgressEvent) -> None:
        """Publish a progress event to all subscribers"""
        self._event_count += 1
        
        # Add to history
        if event.workflow_id:
            history = self._event_history[event.workflow_id]
            history.append(event)
            # Keep only recent events
            if len(history) > self._history_limit:
                self._event_history[event.workflow_id] = history[-self._history_limit:]
        
        # Send to WebSocket connections
        if event.workflow_id in self._websocket_connections:
            disconnected = []
            for ws in self._websocket_connections[event.workflow_id]:
                try:
                    await ws.send_json(event.to_dict())
                except:
                    disconnected.append(ws)
            
            # Remove disconnected clients
            for ws in disconnected:
                await self.disconnect_websocket(ws, event.workflow_id)
        
        # Send to SSE queues
        if event.workflow_id in self._sse_queues:
            for queue in self._sse_queues[event.workflow_id]:
                try:
                    await queue.put(event)
                except:
                    pass
        
        # Log high-level events
        if event.type in [ProgressEventType.WORKFLOW_COMPLETED, 
                         ProgressEventType.WORKFLOW_FAILED]:
            logger.info("Workflow event published",
                       event_type=event.type.value,
                       workflow_id=event.workflow_id,
                       subscribers=len(self._websocket_connections.get(event.workflow_id, [])))
    
    async def _close_workflow_connections(self, workflow_id: str) -> None:
        """Close all connections for a workflow"""
        # Close WebSockets
        if workflow_id in self._websocket_connections:
            for ws in self._websocket_connections[workflow_id]:
                try:
                    await ws.close()
                except:
                    pass
            del self._websocket_connections[workflow_id]
        
        # Close SSE streams
        if workflow_id in self._sse_queues:
            for queue in self._sse_queues[workflow_id]:
                await queue.put(None)  # Sentinel to close
            del self._sse_queues[workflow_id]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get streaming metrics"""
        return {
            "active_connections": self._connection_count,
            "total_events_published": self._event_count,
            "workflows_tracked": len(self._event_history),
            "websocket_connections_by_workflow": {
                wf_id: len(conns) 
                for wf_id, conns in self._websocket_connections.items()
            },
            "sse_streams_by_workflow": {
                wf_id: len(queues) 
                for wf_id, queues in self._sse_queues.items()
            }
        }


# Global instance
progress_manager = ProgressStreamManager()


class ProgressReporter:
    """Helper class for reporting progress from activities and tasks"""
    
    def __init__(self, 
                 workflow_id: str,
                 activity_id: Optional[str] = None,
                 source: str = "unknown"):
        self.workflow_id = workflow_id
        self.activity_id = activity_id
        self.source = source
    
    async def report_activity_started(self, activity_name: str, **kwargs):
        """Report activity started"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.ACTIVITY_STARTED,
            timestamp=datetime.utcnow(),
            source=self.source,
            workflow_id=self.workflow_id,
            activity_id=self.activity_id,
            data={
                "activity_name": activity_name,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_activity_progress(self, progress: float, message: str = "", **kwargs):
        """Report activity progress (0.0 to 1.0)"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.ACTIVITY_PROGRESS,
            timestamp=datetime.utcnow(),
            source=self.source,
            workflow_id=self.workflow_id,
            activity_id=self.activity_id,
            data={
                "progress": min(max(progress, 0.0), 1.0),
                "message": message,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_activity_completed(self, result: Any = None, **kwargs):
        """Report activity completed"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.ACTIVITY_COMPLETED,
            timestamp=datetime.utcnow(),
            source=self.source,
            workflow_id=self.workflow_id,
            activity_id=self.activity_id,
            data={
                "result": str(result) if result else None,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_activity_failed(self, error: str, **kwargs):
        """Report activity failed"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.ACTIVITY_FAILED,
            timestamp=datetime.utcnow(),
            source=self.source,
            workflow_id=self.workflow_id,
            activity_id=self.activity_id,
            data={
                "error": error,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_log(self, level: str, message: str, **kwargs):
        """Report a log message"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.LOG_MESSAGE,
            timestamp=datetime.utcnow(),
            source=self.source,
            workflow_id=self.workflow_id,
            activity_id=self.activity_id,
            data={
                "level": level,
                "message": message,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)


def create_progress_reporter(workflow_id: str, 
                           activity_id: Optional[str] = None,
                           source: str = "unknown") -> ProgressReporter:
    """Create a progress reporter for an activity"""
    return ProgressReporter(workflow_id, activity_id, source)
