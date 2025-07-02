"""
Comprehensive error handling and retry logic for QLP
Provides production-ready error handling, circuit breakers, and retry strategies
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryError
)

logger = structlog.get_logger()


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ServiceError(Exception):
    """Base exception for service errors"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 service: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.severity = severity
        self.service = service
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class RetryableError(ServiceError):
    """Error that should trigger a retry"""
    pass


class NonRetryableError(ServiceError):
    """Error that should not trigger a retry"""
    pass


class CircuitBreakerError(ServiceError):
    """Error when circuit breaker is open"""
    def __init__(self, service: str, message: str = "Circuit breaker is open"):
        super().__init__(message, ErrorSeverity.HIGH, service)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    Prevents cascading failures by temporarily blocking requests to failing services
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        
        # Metrics
        self.call_count = 0
        self.failure_history = deque(maxlen=100)
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        self.call_count += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise CircuitBreakerError(self.name)
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        self.call_count += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise CircuitBreakerError(self.name)
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} closed after recovery")
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.failure_history.append({
            "timestamp": self.last_failure_time,
            "error": str(exception),
            "type": type(exception).__name__
        })
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning(f"Circuit breaker {self.name} reopened after failure in HALF_OPEN state")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "call_count": self.call_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recent_failures": list(self.failure_history)[-10:]  # Last 10 failures
        }


class ErrorHandler:
    """
    Centralized error handling with retry strategies and circuit breakers
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts = defaultdict(int)
        self.retry_counts = defaultdict(int)
        
    def get_circuit_breaker(
        self,
        service: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ) -> CircuitBreaker:
        """Get or create circuit breaker for a service"""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                name=service,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
        return self.circuit_breakers[service]
    
    def with_retry(
        self,
        *,
        max_attempts: int = 3,
        max_delay: int = 60,
        exponential_base: float = 2,
        exponential_max: int = 10,
        exceptions: Union[Type[Exception], tuple] = (RetryableError,),
        service: Optional[str] = None
    ):
        """
        Decorator for adding retry logic to functions
        
        Example:
            @error_handler.with_retry(max_attempts=3, service="openai")
            async def call_openai():
                ...
        """
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                retry_decorator = retry(
                    stop=stop_after_attempt(max_attempts),
                    wait=wait_exponential(multiplier=exponential_base, max=exponential_max),
                    retry=retry_if_exception_type(exceptions),
                    before_sleep=before_sleep_log(logger, structlog.INFO),
                    after=after_log(logger, structlog.INFO)
                )
                
                service_name = service or func.__name__
                self.retry_counts[service_name] += 1
                
                try:
                    return await retry_decorator(func)(*args, **kwargs)
                except RetryError as e:
                    self.error_counts[service_name] += 1
                    logger.error(f"Max retries exceeded for {service_name}", 
                               error=str(e.last_attempt.exception()))
                    raise e.last_attempt.exception()
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                retry_decorator = retry(
                    stop=stop_after_attempt(max_attempts),
                    wait=wait_exponential(multiplier=exponential_base, max=exponential_max),
                    retry=retry_if_exception_type(exceptions),
                    before_sleep=before_sleep_log(logger, structlog.INFO),
                    after=after_log(logger, structlog.INFO)
                )
                
                service_name = service or func.__name__
                self.retry_counts[service_name] += 1
                
                try:
                    return retry_decorator(func)(*args, **kwargs)
                except RetryError as e:
                    self.error_counts[service_name] += 1
                    logger.error(f"Max retries exceeded for {service_name}", 
                               error=str(e.last_attempt.exception()))
                    raise e.last_attempt.exception()
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def with_circuit_breaker(
        self,
        service: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Decorator for adding circuit breaker protection
        
        Example:
            @error_handler.with_circuit_breaker("external_api", failure_threshold=3)
            async def call_external_api():
                ...
        """
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                cb = self.get_circuit_breaker(
                    service, failure_threshold, recovery_timeout, expected_exception
                )
                return await cb.async_call(func, *args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                cb = self.get_circuit_breaker(
                    service, failure_threshold, recovery_timeout, expected_exception
                )
                return cb.call(func, *args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def handle_error(
        self,
        error: Exception,
        service: Optional[str] = None,
        context: Optional[Dict] = None,
        raise_after: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Central error handling with logging and metrics
        
        Returns error details dict if raise_after=False, otherwise raises
        """
        service_name = service or "unknown"
        self.error_counts[service_name] += 1
        
        error_details = {
            "service": service_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        # Determine severity
        if isinstance(error, ServiceError):
            severity = error.severity
            error_details["severity"] = severity
            error_details["details"] = error.details
        else:
            severity = ErrorSeverity.MEDIUM
            error_details["severity"] = severity
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", **error_details)
        elif severity == ErrorSeverity.HIGH:
            logger.error("High severity error", **error_details)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error", **error_details)
        else:
            logger.info("Low severity error", **error_details)
        
        if raise_after:
            raise error
        return error_details
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get error handling metrics"""
        return {
            "error_counts": dict(self.error_counts),
            "retry_counts": dict(self.retry_counts),
            "circuit_breakers": {
                name: cb.get_metrics() 
                for name, cb in self.circuit_breakers.items()
            }
        }


# Global error handler instance
error_handler = ErrorHandler()


# Convenience decorators
with_retry = error_handler.with_retry
with_circuit_breaker = error_handler.with_circuit_breaker


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Simple retry
    @with_retry(max_attempts=3, service="example_api")
    async def unreliable_api_call():
        import random
        if random.random() < 0.7:
            raise RetryableError("API temporarily unavailable")
        return "Success"
    
    # Example 2: Circuit breaker + retry
    @with_circuit_breaker("database", failure_threshold=3)
    @with_retry(max_attempts=2, service="database")
    async def database_query():
        # Simulate database operation
        pass
    
    # Example 3: Custom error handling
    async def process_request():
        try:
            result = await unreliable_api_call()
            return result
        except Exception as e:
            error_handler.handle_error(
                e,
                service="request_processor",
                context={"request_id": "123"},
                raise_after=False
            )
            return None