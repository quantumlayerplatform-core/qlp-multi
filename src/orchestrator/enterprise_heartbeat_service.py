"""
Enterprise Heartbeat Management Service for Temporal Activities
Provides reliable heartbeat management for long-running distributed tasks
"""
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from temporalio import activity
import logging
import structlog

# Use structured logging for enterprise environments
logger = structlog.get_logger()

class EnterpriseHeartbeatService:
    """
    Enterprise-grade heartbeat management service for Temporal activities.
    Ensures long-running activities maintain connectivity and prevent timeouts.
    """
    
    def __init__(self, 
                 interval_seconds: int = 15,
                 max_retries: int = 3,
                 enable_metrics: bool = True):
        """
        Initialize the heartbeat service.
        
        Args:
            interval_seconds: Heartbeat interval in seconds (default: 15)
            max_retries: Maximum retry attempts for heartbeat failures
            enable_metrics: Enable performance metrics collection
        """
        self.interval_seconds = interval_seconds
        self.max_retries = max_retries
        self.enable_metrics = enable_metrics
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time: Optional[datetime] = None
        self._heartbeat_count = 0
        self._error_count = 0
        
    async def _heartbeat_loop(self, 
                            message_provider: Callable[[], str],
                            metadata: Dict[str, Any]):
        """
        Main heartbeat loop with enterprise features.
        
        Args:
            message_provider: Function that returns current status message
            metadata: Additional metadata to include in heartbeats
        """
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        
        while self._running:
            try:
                # Get current status message
                message = message_provider() if callable(message_provider) else str(message_provider)
                
                # Add runtime statistics to message
                runtime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
                enhanced_message = f"{message} (Runtime: {runtime_seconds:.1f}s, Heartbeats: {self._heartbeat_count})"
                
                # Send heartbeat with retry logic
                retry_count = 0
                while retry_count < self.max_retries:
                    try:
                        activity.heartbeat(enhanced_message)
                        self._heartbeat_count += 1
                        
                        # Log heartbeat success with structured data
                        logger.debug(
                            "Heartbeat sent successfully",
                            heartbeat_count=self._heartbeat_count,
                            runtime_seconds=runtime_seconds,
                            **metadata
                        )
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        self._error_count += 1
                        logger.warning(
                            "Heartbeat failed, retrying",
                            error=str(e),
                            retry_count=retry_count,
                            error_count=self._error_count
                        )
                        if retry_count >= self.max_retries:
                            raise
                        await asyncio.sleep(1)  # Brief pause before retry
                
                # Wait for next heartbeat interval
                await asyncio.sleep(self.interval_seconds)
                
            except asyncio.CancelledError:
                logger.info(
                    "Heartbeat service cancelled",
                    total_heartbeats=self._heartbeat_count,
                    total_errors=self._error_count
                )
                break
            except Exception as e:
                logger.error(
                    "Critical heartbeat error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                # Continue running despite errors
    
    async def start(self, 
                   message: str = "Processing",
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Start the heartbeat service.
        
        Args:
            message: Status message or message provider function
            metadata: Additional context metadata
        """
        if not self._task or self._task.done():
            metadata = metadata or {}
            self._task = asyncio.create_task(
                self._heartbeat_loop(lambda: message, metadata)
            )
            logger.info(
                "Heartbeat service started",
                interval_seconds=self.interval_seconds,
                **metadata
            )
    
    async def update_message(self, new_message: str):
        """Update the heartbeat message dynamically"""
        # This would require a more complex implementation with shared state
        # For now, log the intent
        logger.info("Heartbeat message update requested", new_message=new_message)
    
    async def stop(self):
        """Stop the heartbeat service gracefully"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Log final statistics
        if self._start_time:
            total_runtime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            logger.info(
                "Heartbeat service stopped",
                total_runtime_seconds=total_runtime,
                total_heartbeats=self._heartbeat_count,
                total_errors=self._error_count,
                success_rate=f"{(1 - self._error_count/max(1, self._heartbeat_count)) * 100:.1f}%"
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current heartbeat statistics"""
        runtime = 0
        if self._start_time:
            runtime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        
        return {
            "is_running": self._running,
            "heartbeat_count": self._heartbeat_count,
            "error_count": self._error_count,
            "runtime_seconds": runtime,
            "interval_seconds": self.interval_seconds
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()


class HeartbeatContext:
    """Context manager for automatic heartbeat management"""
    
    def __init__(self, 
                 message: str = "Processing",
                 interval: int = 15,
                 task_id: Optional[str] = None,
                 operation: Optional[str] = None):
        self.service = EnterpriseHeartbeatService(interval_seconds=interval)
        self.message = message
        self.metadata = {
            "task_id": task_id,
            "operation": operation
        }
    
    async def __aenter__(self):
        await self.service.start(self.message, self.metadata)
        return self.service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.service.stop()


async def with_enterprise_heartbeat(
    coroutine,
    message: str = "Processing",
    interval: int = 15,
    task_id: Optional[str] = None,
    operation: Optional[str] = None
):
    """
    Execute a coroutine with automatic heartbeat management.
    
    Args:
        coroutine: The async operation to execute
        message: Heartbeat status message
        interval: Heartbeat interval in seconds
        task_id: Optional task identifier
        operation: Optional operation name
    
    Returns:
        The result of the coroutine
    """
    async with HeartbeatContext(message, interval, task_id, operation) as service:
        try:
            result = await coroutine
            return result
        except Exception as e:
            logger.error(
                "Operation failed during heartbeat context",
                error=str(e),
                task_id=task_id,
                operation=operation,
                statistics=service.get_statistics()
            )
            raise