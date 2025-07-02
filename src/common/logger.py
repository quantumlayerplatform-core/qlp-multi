"""
Unified logger configuration for QLP
Provides structured logging with multiple outputs and consistent formatting
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
import json
from functools import wraps
import asyncio

import structlog
from structlog.stdlib import LoggerFactory
from pythonjsonlogger import jsonlogger
from rich.console import Console
from rich.logging import RichHandler

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


# Configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")  # console, json, structured
LOG_DIR = os.getenv("LOG_DIR", "logs")
SERVICE_NAME = os.getenv("SERVICE_NAME", "qlp")
ENABLE_SENTRY = os.getenv("ENABLE_SENTRY", "false").lower() == "true"
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Create logs directory
Path(LOG_DIR).mkdir(exist_ok=True)


class QLPLogger:
    """Unified logger for all QLP services"""
    
    def __init__(
        self,
        service_name: str = None,
        log_level: str = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        enable_json_logging: bool = False,
        context: Dict[str, Any] = None
    ):
        self.service_name = service_name or SERVICE_NAME
        self.log_level = getattr(logging, (log_level or LOG_LEVEL).upper())
        self.context = context or {}
        
        # Configure structlog
        self._configure_structlog(
            enable_file_logging,
            enable_console_logging,
            enable_json_logging
        )
        
        # Initialize Sentry if enabled
        if ENABLE_SENTRY and SENTRY_DSN:
            self._init_sentry()
        
        # Get logger instance
        self.logger = structlog.get_logger(service_name=self.service_name)
        
    def _configure_structlog(
        self,
        enable_file: bool,
        enable_console: bool,
        enable_json: bool
    ):
        """Configure structlog with multiple outputs"""
        
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            self._add_context_processor,
        ]
        
        # Configure different output formats
        if LOG_FORMAT == "json" or enable_json:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=self.log_level,
        )
        
        # Remove default handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add handlers based on configuration
        handlers = []
        
        # Console handler with Rich formatting
        if enable_console:
            console_handler = RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=False,
                enable_link_path=True,
            )
            console_handler.setLevel(self.log_level)
            handlers.append(console_handler)
        
        # File handler with rotation
        if enable_file:
            from logging.handlers import RotatingFileHandler
            
            log_file = Path(LOG_DIR) / f"{self.service_name}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            
            # Use JSON formatter for file logs
            json_formatter = jsonlogger.JsonFormatter(
                "%(timestamp)s %(level)s %(name)s %(message)s",
                timestamp=True
            )
            file_handler.setFormatter(json_formatter)
            file_handler.setLevel(self.log_level)
            handlers.append(file_handler)
        
        # Add handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _add_context_processor(self, logger, method_name, event_dict):
        """Add context to all log messages"""
        event_dict.update(self.context)
        
        # Add request ID if available
        if hasattr(asyncio, 'current_task'):
            task = asyncio.current_task()
            if task and hasattr(task, 'request_id'):
                event_dict['request_id'] = task.request_id
        
        return event_dict
    
    def _init_sentry(self):
        """Initialize Sentry error tracking"""
        if not SENTRY_AVAILABLE:
            return
            
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("APP_VERSION", "unknown"),
        )
    
    def bind(self, **kwargs) -> 'QLPLogger':
        """Create a new logger with additional context"""
        new_context = {**self.context, **kwargs}
        new_logger = QLPLogger(
            service_name=self.service_name,
            log_level=logging.getLevelName(self.log_level),
            context=new_context
        )
        return new_logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, **kwargs)
    
    def log_request(self, method: str, path: str, status_code: int, duration: float, **kwargs):
        """Log HTTP request"""
        self.info(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            **kwargs
        )
    
    def log_llm_call(
        self,
        model: str,
        provider: str,
        tokens: Dict[str, int],
        latency: float,
        success: bool,
        **kwargs
    ):
        """Log LLM API call"""
        self.info(
            "llm_call",
            model=model,
            provider=provider,
            tokens=tokens,
            latency=latency,
            success=success,
            **kwargs
        )
    
    def log_task(
        self,
        task_id: str,
        task_type: str,
        status: str,
        duration: Optional[float] = None,
        **kwargs
    ):
        """Log task execution"""
        self.info(
            "task_execution",
            task_id=task_id,
            task_type=task_type,
            status=status,
            duration=duration,
            **kwargs
        )
    
    def log_metric(self, metric_name: str, value: Union[int, float], unit: str = "", **kwargs):
        """Log a metric value"""
        self.info(
            "metric",
            metric_name=metric_name,
            value=value,
            unit=unit,
            **kwargs
        )


# Decorators for function logging
def log_function(logger: QLPLogger = None, log_args: bool = True, log_result: bool = True):
    """Decorator to log function entry/exit"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_logger = logger or get_logger(func.__module__)
            
            # Log function entry
            log_data = {"function": func.__name__}
            if log_args:
                log_data["args"] = str(args)[:100]
                log_data["kwargs"] = str(kwargs)[:100]
            
            func_logger.debug("function_entry", **log_data)
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Log function exit
                exit_data = {
                    "function": func.__name__,
                    "duration": duration,
                    "status": "success"
                }
                if log_result:
                    exit_data["result"] = str(result)[:100]
                
                func_logger.debug("function_exit", **exit_data)
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                func_logger.error(
                    "function_error",
                    function=func.__name__,
                    duration=duration,
                    error=str(e),
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_logger = logger or get_logger(func.__module__)
            
            # Log function entry
            log_data = {"function": func.__name__}
            if log_args:
                log_data["args"] = str(args)[:100]
                log_data["kwargs"] = str(kwargs)[:100]
            
            func_logger.debug("function_entry", **log_data)
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Log function exit
                exit_data = {
                    "function": func.__name__,
                    "duration": duration,
                    "status": "success"
                }
                if log_result:
                    exit_data["result"] = str(result)[:100]
                
                func_logger.debug("function_exit", **exit_data)
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                func_logger.error(
                    "function_error",
                    function=func.__name__,
                    duration=duration,
                    error=str(e),
                    exc_info=True
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global logger instances cache
_loggers: Dict[str, QLPLogger] = {}


def get_logger(
    name: Optional[str] = None,
    service_name: Optional[str] = None,
    **kwargs
) -> QLPLogger:
    """
    Get or create a logger instance
    
    Args:
        name: Logger name (usually __name__)
        service_name: Service name for context
        **kwargs: Additional context
    
    Returns:
        QLPLogger instance
    """
    logger_name = name or "qlp"
    
    if logger_name not in _loggers:
        _loggers[logger_name] = QLPLogger(
            service_name=service_name or SERVICE_NAME,
            context=kwargs
        )
    
    return _loggers[logger_name]


# Convenience functions
def setup_logging(
    service_name: str,
    log_level: str = None,
    enable_json: bool = None
) -> QLPLogger:
    """
    Setup logging for a service
    
    Args:
        service_name: Name of the service
        log_level: Logging level
        enable_json: Enable JSON format
    
    Returns:
        Configured logger
    """
    global SERVICE_NAME, LOG_FORMAT
    
    SERVICE_NAME = service_name
    
    if enable_json is not None:
        LOG_FORMAT = "json" if enable_json else "console"
    
    # Clear existing loggers
    _loggers.clear()
    
    # Create and return new logger
    return get_logger(service_name=service_name)


# Example usage
if __name__ == "__main__":
    # Setup logger for a service
    logger = setup_logging("test-service", log_level="DEBUG")
    
    # Basic logging
    logger.info("Service started", version="1.0.0")
    
    # Log with context
    request_logger = logger.bind(request_id="123", user_id="456")
    request_logger.info("Processing request")
    
    # Log metrics
    logger.log_metric("request_count", 100, unit="requests/sec")
    
    # Log LLM call
    logger.log_llm_call(
        model="gpt-4",
        provider="azure_openai",
        tokens={"prompt": 100, "completion": 50},
        latency=1.23,
        success=True
    )
    
    # Use decorator
    @log_function(logger)
    async def example_function(x: int) -> int:
        return x * 2
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except Exception:
        logger.exception("An error occurred")