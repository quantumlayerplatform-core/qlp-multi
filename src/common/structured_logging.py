#!/usr/bin/env python3
"""
Structured logging configuration for QLP platform
Provides consistent logging across all services with proper context and observability
"""

import logging
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar
import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder
from structlog.types import Processor
import os

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
workflow_id_var: ContextVar[Optional[str]] = ContextVar('workflow_id', default=None)
capsule_id_var: ContextVar[Optional[str]] = ContextVar('capsule_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)

class ContextProcessor:
    """Add context variables to log entries"""
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Add context variables if they exist
        if request_id := request_id_var.get():
            event_dict['request_id'] = request_id
        if workflow_id := workflow_id_var.get():
            event_dict['workflow_id'] = workflow_id
        if capsule_id := capsule_id_var.get():
            event_dict['capsule_id'] = capsule_id
        if user_id := user_id_var.get():
            event_dict['user_id'] = user_id
        if tenant_id := tenant_id_var.get():
            event_dict['tenant_id'] = tenant_id
            
        # Add service information
        event_dict['service'] = os.getenv('SERVICE_NAME', 'unknown')
        event_dict['environment'] = os.getenv('ENVIRONMENT', 'development')
        event_dict['pod_name'] = os.getenv('HOSTNAME', 'local')
        
        return event_dict

class ErrorDetailsProcessor:
    """Add detailed error information to log entries"""
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        if 'error' in event_dict and isinstance(event_dict['error'], Exception):
            error = event_dict['error']
            event_dict['error_type'] = type(error).__name__
            event_dict['error_message'] = str(error)
            event_dict['error_traceback'] = traceback.format_exception(
                type(error), error, error.__traceback__
            )
        return event_dict

class PerformanceProcessor:
    """Add performance metrics to log entries"""
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Add timing information if available
        if 'duration' in event_dict:
            duration = event_dict['duration']
            if isinstance(duration, (int, float)):
                event_dict['duration_ms'] = int(duration * 1000)
                event_dict['duration_seconds'] = round(duration, 3)
                
                # Add performance classification
                if duration < 0.1:
                    event_dict['performance'] = 'fast'
                elif duration < 1:
                    event_dict['performance'] = 'normal'
                elif duration < 5:
                    event_dict['performance'] = 'slow'
                else:
                    event_dict['performance'] = 'very_slow'
                    
        return event_dict

class SensitiveDataProcessor:
    """Remove or mask sensitive data from log entries"""
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'credit_card', 'ssn', 'email', 'phone'
    }
    
    def _mask_value(self, value: Any) -> Any:
        """Mask sensitive values"""
        if isinstance(value, str) and len(value) > 4:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
        return '***MASKED***'
    
    def _process_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively process dictionary to mask sensitive data"""
        result = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                result[key] = self._mask_value(value)
            elif isinstance(value, dict):
                result[key] = self._process_dict(value)
            elif isinstance(value, list):
                result[key] = [self._process_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return self._process_dict(event_dict)

def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    json_output: bool = True,
    include_caller_info: bool = True
) -> structlog.BoundLogger:
    """
    Setup structured logging for a service
    
    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_output: Whether to output JSON formatted logs
        include_caller_info: Whether to include file/line information
    
    Returns:
        Configured logger instance
    """
    # Set service name in environment for context processor
    os.environ['SERVICE_NAME'] = service_name
    
    # Configure processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        ContextProcessor(),
        ErrorDetailsProcessor(),
        PerformanceProcessor(),
        SensitiveDataProcessor(),
    ]
    
    # Add caller information if requested
    if include_caller_info:
        processors.append(
            CallsiteParameterAdder(
                [CallsiteParameter.FILENAME, CallsiteParameter.LINENO, CallsiteParameter.FUNC_NAME]
            )
        )
    
    # Add final renderer
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set Python logging level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Return logger instance
    return structlog.get_logger(service_name)

class LogContext:
    """Context manager for adding temporary log context"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.logger = None
        self.old_values = {}
    
    def __enter__(self):
        # Save old context values and set new ones
        for key, value in self.context.items():
            if key == 'request_id':
                self.old_values[key] = request_id_var.get()
                request_id_var.set(value)
            elif key == 'workflow_id':
                self.old_values[key] = workflow_id_var.get()
                workflow_id_var.set(value)
            elif key == 'capsule_id':
                self.old_values[key] = capsule_id_var.get()
                capsule_id_var.set(value)
            elif key == 'user_id':
                self.old_values[key] = user_id_var.get()
                user_id_var.set(value)
            elif key == 'tenant_id':
                self.old_values[key] = tenant_id_var.get()
                tenant_id_var.set(value)
        
        self.logger = structlog.get_logger()
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context values
        for key, old_value in self.old_values.items():
            if key == 'request_id':
                request_id_var.set(old_value)
            elif key == 'workflow_id':
                workflow_id_var.set(old_value)
            elif key == 'capsule_id':
                capsule_id_var.set(old_value)
            elif key == 'user_id':
                user_id_var.set(old_value)
            elif key == 'tenant_id':
                tenant_id_var.set(old_value)
        
        # Log any exceptions
        if exc_type:
            self.logger.error(
                "Exception in context",
                error=exc_val,
                exc_type=exc_type.__name__
            )

def log_operation(
    operation: str,
    duration: Optional[float] = None,
    success: bool = True,
    **kwargs
) -> None:
    """
    Log an operation with standard fields
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        success: Whether operation succeeded
        **kwargs: Additional fields to log
    """
    logger = structlog.get_logger()
    
    log_data = {
        'operation': operation,
        'success': success,
        **kwargs
    }
    
    if duration is not None:
        log_data['duration'] = duration
    
    if success:
        logger.info(f"{operation} completed", **log_data)
    else:
        logger.error(f"{operation} failed", **log_data)

def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **kwargs
) -> None:
    """
    Log an API request with standard fields
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional fields to log
    """
    logger = structlog.get_logger()
    
    log_data = {
        'http_method': method,
        'http_path': path,
        'http_status': status_code,
        'duration': duration,
        'http_success': 200 <= status_code < 400,
        **kwargs
    }
    
    if status_code >= 500:
        logger.error("API request error", **log_data)
    elif status_code >= 400:
        logger.warning("API request client error", **log_data)
    else:
        logger.info("API request completed", **log_data)

def log_workflow_activity(
    activity_name: str,
    activity_type: str,
    status: str,
    **kwargs
) -> None:
    """
    Log a Temporal workflow activity
    
    Args:
        activity_name: Name of the activity
        activity_type: Type of activity (e.g., 'code_generation', 'validation')
        status: Activity status (e.g., 'started', 'completed', 'failed')
        **kwargs: Additional fields to log
    """
    logger = structlog.get_logger()
    
    log_data = {
        'activity_name': activity_name,
        'activity_type': activity_type,
        'activity_status': status,
        **kwargs
    }
    
    if status == 'failed':
        logger.error(f"Activity {activity_name} failed", **log_data)
    else:
        logger.info(f"Activity {activity_name} {status}", **log_data)

# Convenience function for getting logger
def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance
    
    Args:
        name: Optional logger name
    
    Returns:
        Logger instance
    """
    return structlog.get_logger(name) if name else structlog.get_logger()
