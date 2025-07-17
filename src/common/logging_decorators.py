#!/usr/bin/env python3
"""
Logging decorators for automatic function/method logging
Provides consistent logging for operations, performance tracking, and error handling
"""

import time
import functools
import asyncio
from typing import Callable, Any, Optional, Dict, TypeVar, Union
import structlog
from src.common.structured_logging import log_operation, LogContext

logger = structlog.get_logger(__name__)

T = TypeVar('T')


def log_function(
    operation: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
    log_level: str = "info",
    sensitive_args: Optional[list[str]] = None
) -> Callable:
    """
    Decorator to automatically log function execution
    
    Args:
        operation: Operation name (defaults to function name)
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        log_level: Log level for successful execution
        sensitive_args: List of argument names to mask
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            
            # Prepare log data
            log_data = {"function": func.__name__}
            
            if include_args:
                # Mask sensitive arguments
                safe_kwargs = kwargs.copy()
                if sensitive_args:
                    for arg in sensitive_args:
                        if arg in safe_kwargs:
                            safe_kwargs[arg] = "***MASKED***"
                
                log_data["args"] = args
                log_data["kwargs"] = safe_kwargs
            
            # Log start
            logger.log(log_level, f"{op_name} started", **log_data)
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log success
                success_data = {
                    **log_data,
                    "duration": duration,
                    "success": True
                }
                
                if include_result:
                    success_data["result"] = result
                
                logger.log(log_level, f"{op_name} completed", **success_data)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                logger.error(
                    f"{op_name} failed",
                    **log_data,
                    duration=duration,
                    success=False,
                    error=e
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            
            # Prepare log data
            log_data = {"function": func.__name__}
            
            if include_args:
                # Mask sensitive arguments
                safe_kwargs = kwargs.copy()
                if sensitive_args:
                    for arg in sensitive_args:
                        if arg in safe_kwargs:
                            safe_kwargs[arg] = "***MASKED***"
                
                log_data["args"] = args
                log_data["kwargs"] = safe_kwargs
            
            # Log start
            logger.log(log_level, f"{op_name} started", **log_data)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log success
                success_data = {
                    **log_data,
                    "duration": duration,
                    "success": True
                }
                
                if include_result:
                    success_data["result"] = result
                
                logger.log(log_level, f"{op_name} completed", **success_data)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                logger.error(
                    f"{op_name} failed",
                    **log_data,
                    duration=duration,
                    success=False,
                    error=e
                )
                raise
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_class_methods(
    exclude: Optional[list[str]] = None,
    include_private: bool = False
) -> Callable:
    """
    Class decorator to automatically log all public methods
    
    Args:
        exclude: List of method names to exclude from logging
        include_private: Whether to log private methods (starting with _)
    """
    exclude = exclude or []
    
    def decorator(cls: type) -> type:
        for attr_name in dir(cls):
            # Skip special methods
            if attr_name.startswith("__") and attr_name.endswith("__"):
                continue
            
            # Skip private methods if not included
            if attr_name.startswith("_") and not include_private:
                continue
            
            # Skip excluded methods
            if attr_name in exclude:
                continue
            
            attr = getattr(cls, attr_name)
            if callable(attr):
                # Apply logging decorator
                setattr(
                    cls,
                    attr_name,
                    log_function(operation=f"{cls.__name__}.{attr_name}")(attr)
                )
        
        return cls
    
    return decorator


def measure_performance(
    threshold_ms: Optional[float] = None,
    alert_on_slow: bool = True
) -> Callable:
    """
    Decorator to measure and log function performance
    
    Args:
        threshold_ms: Threshold in milliseconds for slow execution warning
        alert_on_slow: Whether to log warning for slow execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                log_data = {
                    "function": func.__name__,
                    "duration_ms": round(elapsed_ms, 2),
                    "performance": "fast" if elapsed_ms < 100 else "normal" if elapsed_ms < 1000 else "slow"
                }
                
                if threshold_ms and elapsed_ms > threshold_ms and alert_on_slow:
                    logger.warning(
                        f"{func.__name__} exceeded performance threshold",
                        **log_data,
                        threshold_ms=threshold_ms
                    )
                else:
                    logger.debug(f"{func.__name__} performance", **log_data)
                
                return result
                
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    duration_ms=round(elapsed_ms, 2),
                    error=e
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                log_data = {
                    "function": func.__name__,
                    "duration_ms": round(elapsed_ms, 2),
                    "performance": "fast" if elapsed_ms < 100 else "normal" if elapsed_ms < 1000 else "slow"
                }
                
                if threshold_ms and elapsed_ms > threshold_ms and alert_on_slow:
                    logger.warning(
                        f"{func.__name__} exceeded performance threshold",
                        **log_data,
                        threshold_ms=threshold_ms
                    )
                else:
                    logger.debug(f"{func.__name__} performance", **log_data)
                
                return result
                
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    duration_ms=round(elapsed_ms, 2),
                    error=e
                )
                raise
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_with_logging(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry function execution with exponential backoff and logging
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if attempt > 0:
                        # Calculate backoff
                        wait_time = backoff_factor ** (attempt - 1)
                        logger.info(
                            f"Retrying {func.__name__}",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time
                        )
                        await asyncio.sleep(wait_time)
                    
                    # Try to execute
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded after retry",
                            attempt=attempt + 1
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} attempt failed",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after all retries",
                            max_attempts=max_attempts,
                            error=e
                        )
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if attempt > 0:
                        # Calculate backoff
                        wait_time = backoff_factor ** (attempt - 1)
                        logger.info(
                            f"Retrying {func.__name__}",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time
                        )
                        time.sleep(wait_time)
                    
                    # Try to execute
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded after retry",
                            attempt=attempt + 1
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} attempt failed",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after all retries",
                            max_attempts=max_attempts,
                            error=e
                        )
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_context(**context) -> Callable:
    """
    Decorator to add context to all logs within a function
    
    Args:
        **context: Context key-value pairs to add to logs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with LogContext(**context):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with LogContext(**context):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
