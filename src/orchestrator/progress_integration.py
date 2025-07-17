#!/usr/bin/env python3
"""
Progress reporting integration for Temporal workflows and activities
Provides decorators and utilities for automatic progress tracking
"""

import functools
import time
import asyncio
import uuid
from datetime import datetime
from typing import Callable, Any, Dict, Optional
import structlog
from temporalio import activity, workflow

from src.common.progress_streaming import (
    create_progress_reporter,
    ProgressEvent,
    ProgressEventType,
    progress_manager
)

logger = structlog.get_logger(__name__)


def track_activity_progress(activity_name: str):
    """
    Decorator to automatically track activity progress
    
    Usage:
        @activity.defn
        @track_activity_progress("code_generation")
        async def generate_code_activity(params: Dict[str, Any]):
            # Activity implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(params: Dict[str, Any], *args, **kwargs):
            # Extract workflow ID from params
            workflow_id = params.get("workflow_id", "unknown")
            activity_id = params.get("activity_id", activity.info().activity_id)
            
            # Create progress reporter
            reporter = create_progress_reporter(
                workflow_id=workflow_id,
                activity_id=activity_id,
                source=activity_name
            )
            
            # Report activity started
            await reporter.report_activity_started(
                activity_name=activity_name,
                task_description=params.get("task", {}).get("description", "")
            )
            
            start_time = time.time()
            
            try:
                # Inject reporter into params for use within activity
                params["_progress_reporter"] = reporter
                
                # Execute the activity
                result = await func(params, *args, **kwargs)
                
                # Report completion
                duration = time.time() - start_time
                await reporter.report_activity_completed(
                    duration_seconds=duration,
                    result_summary=str(result)[:200] if result else None
                )
                
                return result
                
            except Exception as e:
                # Report failure
                duration = time.time() - start_time
                await reporter.report_activity_failed(
                    error=str(e),
                    duration_seconds=duration
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(params: Dict[str, Any], *args, **kwargs):
            # For sync activities (less common in our system)
            import asyncio
            return asyncio.run(async_wrapper(params, *args, **kwargs))
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class WorkflowProgressTracker:
    """
    Helper class for tracking workflow progress
    """
    
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.reporter = create_progress_reporter(
            workflow_id=workflow_id,
            source="workflow"
        )
    
    async def report_started(self, description: str, **kwargs):
        """Report workflow started"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.WORKFLOW_STARTED,
            timestamp=datetime.utcnow(),
            source="workflow",
            workflow_id=self.workflow_id,
            data={
                "description": description,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_completed(self, result: Any = None, **kwargs):
        """Report workflow completed"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.WORKFLOW_COMPLETED,
            timestamp=datetime.utcnow(),
            source="workflow",
            workflow_id=self.workflow_id,
            data={
                "result": str(result)[:500] if result else None,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_failed(self, error: str, **kwargs):
        """Report workflow failed"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.WORKFLOW_FAILED,
            timestamp=datetime.utcnow(),
            source="workflow",
            workflow_id=self.workflow_id,
            data={
                "error": error,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)
    
    async def report_status(self, status: str, message: str, **kwargs):
        """Report workflow status update"""
        event = ProgressEvent(
            id=str(uuid.uuid4()),
            type=ProgressEventType.STATUS_UPDATE,
            timestamp=datetime.utcnow(),
            source="workflow",
            workflow_id=self.workflow_id,
            data={
                "status": status,
                "message": message,
                **kwargs
            }
        )
        await progress_manager.publish_event(event)


# Example usage in activities
def example_activity_with_progress():
    """
    Example of how to use progress reporting within an activity
    """
    @activity.defn
    @track_activity_progress("example_processing")
    async def process_data_activity(params: Dict[str, Any]):
        # Get the injected progress reporter
        reporter = params.get("_progress_reporter")
        
        # Simulate processing with progress updates
        total_items = 100
        
        for i in range(total_items):
            # Do some work
            await asyncio.sleep(0.1)
            
            # Report progress every 10 items
            if i % 10 == 0 and reporter:
                progress = i / total_items
                await reporter.report_activity_progress(
                    progress=progress,
                    message=f"Processed {i}/{total_items} items",
                    items_processed=i,
                    items_total=total_items
                )
        
        return {"items_processed": total_items}


# Convenience functions for manual progress reporting
async def report_task_progress(
    workflow_id: str,
    task_id: str,
    progress: float,
    message: str = "",
    **kwargs
):
    """Report progress for a specific task"""
    event = ProgressEvent(
        id=str(uuid.uuid4()),
        type=ProgressEventType.TASK_PROGRESS,
        timestamp=datetime.utcnow(),
        source="task",
        workflow_id=workflow_id,
        task_id=task_id,
        data={
            "progress": progress,
            "message": message,
            **kwargs
        }
    )
    await progress_manager.publish_event(event)


async def report_metrics_update(
    workflow_id: str,
    metrics: Dict[str, Any],
    source: str = "metrics"
):
    """Report metrics update"""
    event = ProgressEvent(
        id=str(uuid.uuid4()),
        type=ProgressEventType.METRICS_UPDATE,
        timestamp=datetime.utcnow(),
        source=source,
        workflow_id=workflow_id,
        data=metrics
    )
    await progress_manager.publish_event(event)
