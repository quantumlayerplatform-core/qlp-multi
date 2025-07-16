"""
Enterprise-grade error handling and fault tolerance
"""
import logging
import traceback
from typing import Optional, Callable, Any, List, Dict, Type
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from enum import Enum
import httpx

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better classification"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    RESOURCE = "resource"

class EnterpriseError(Exception):
    """Base exception class with enhanced metadata"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 retry_after: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.retry_after = retry_after
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()

class CircuitBreakerError(EnterpriseError):
    """Circuit breaker is open"""
    def __init__(self, service: str, recovery_time: int):
        super().__init__(
            f"Circuit breaker open for {service}. Recovery in {recovery_time}s",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            retry_after=recovery_time
        )

class RateLimitError(EnterpriseError):
    """Rate limit exceeded"""
    def __init__(self, service: str, retry_after: int):
        super().__init__(
            f"Rate limit exceeded for {service}",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.RATE_LIMIT,
            retry_after=retry_after
        )

class ValidationError(EnterpriseError):
    """Validation failed"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            details={"field": field, "value": value}
        )

class TimeoutError(EnterpriseError):
    """Operation timed out"""
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.TIMEOUT,
            details={"operation": operation, "timeout": timeout_seconds}
        )

class RetryableError(EnterpriseError):
    """Error that can be retried"""
    def __init__(self, message: str, max_retries: int = 3):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            details={"max_retries": max_retries}
        )

class EnhancedCircuitBreaker:
    """
    Enhanced circuit breaker with half-open state and metrics
    """
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exceptions: List[Type[Exception]] = None,
                 success_threshold: int = 3):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions or [Exception]
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._on_success()
        else:
            self._on_failure()
        return False
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._on_success()
        else:
            self._on_failure()
        return False
    
    def _on_success(self):
        """Handle successful call"""
        self.total_calls += 1
        self.total_successes += 1
        
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._change_state("closed")
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} closed after {self.success_threshold} successes")
    
    def _on_failure(self):
        """Handle failed call"""
        self.total_calls += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self._change_state("open")
            logger.error(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
        elif self.state == "half-open":
            self._change_state("open")
            self.success_count = 0
            logger.warning(f"Circuit breaker {self.name} reopened due to failure in half-open state")
    
    def _change_state(self, new_state: str):
        """Change circuit breaker state"""
        old_state = self.state
        self.state = new_state
        self.state_changes.append({
            "from": old_state,
            "to": new_state,
            "timestamp": datetime.utcnow(),
            "failures": self.failure_count,
            "successes": self.success_count
        })
    
    def is_open(self) -> bool:
        """Check if circuit breaker should allow calls"""
        if self.state == "closed":
            return False
            
        if self.state == "open":
            if self.last_failure_time:
                recovery_deadline = self.last_failure_time + timedelta(seconds=self.recovery_timeout)
                if datetime.utcnow() >= recovery_deadline:
                    self._change_state("half-open")
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} entering half-open state")
                    return False
            return True
            
        # half-open state allows calls
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.is_open():
            recovery_time = self.recovery_timeout - (datetime.utcnow() - self.last_failure_time).seconds
            raise CircuitBreakerError(self.name, recovery_time)
        
        try:
            with self:
                return func(*args, **kwargs)
        except tuple(self.expected_exceptions):
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if self.is_open():
            recovery_time = self.recovery_timeout - (datetime.utcnow() - self.last_failure_time).seconds
            raise CircuitBreakerError(self.name, recovery_time)
        
        try:
            async with self:
                return await func(*args, **kwargs)
        except tuple(self.expected_exceptions):
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            "name": self.name,
            "state": self.state,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": self.total_failures / max(self.total_calls, 1),
            "current_failures": self.failure_count,
            "current_successes": self.success_count,
            "state_changes": len(self.state_changes),
            "last_state_change": self.state_changes[-1] if self.state_changes else None
        }

class RetryStrategy:
    """
    Intelligent retry strategy with exponential backoff and jitter
    """
    def __init__(self,
                 max_attempts: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt"""
        delay = min(self.initial_delay * (self.exponential_base ** (attempt - 1)), self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if operation should be retried"""
        if attempt >= self.max_attempts:
            return False
        
        # Don't retry validation errors
        if isinstance(exception, ValidationError):
            return False
        
        # Don't retry if circuit breaker is open
        if isinstance(exception, CircuitBreakerError):
            return False
        
        # Check for explicit retry instructions
        if isinstance(exception, EnterpriseError):
            if exception.category == ErrorCategory.VALIDATION:
                return False
            if exception.severity == ErrorSeverity.CRITICAL:
                return False
        
        # Retry network and timeout errors
        if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        
        # Retry retryable errors
        if isinstance(exception, RetryableError):
            return True
        
        # Default: retry on generic exceptions
        return isinstance(exception, Exception)

def with_retry(retry_strategy: Optional[RetryStrategy] = None, 
               service: Optional[str] = None,
               max_attempts: Optional[int] = None,
               exceptions: Optional[tuple] = None,
               **kwargs):
    """
    Decorator for adding retry logic to functions
    Supports both old and new calling conventions
    """
    # Handle legacy parameters
    if max_attempts is not None and retry_strategy is None:
        retry_strategy = RetryStrategy(max_attempts=max_attempts)
    elif retry_strategy is None:
        retry_strategy = RetryStrategy()
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, retry_strategy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not retry_strategy.should_retry(attempt, e):
                        logger.error(f"Non-retryable error in {service or func.__name__}: {str(e)}")
                        raise
                    
                    if attempt < retry_strategy.max_attempts:
                        delay = retry_strategy.calculate_delay(attempt)
                        logger.warning(f"Attempt {attempt} failed for {service or func.__name__}, "
                                     f"retrying in {delay:.2f}s: {str(e)}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {retry_strategy.max_attempts} attempts failed for "
                                   f"{service or func.__name__}: {str(e)}")
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, retry_strategy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not retry_strategy.should_retry(attempt, e):
                        logger.error(f"Non-retryable error in {service or func.__name__}: {str(e)}")
                        raise
                    
                    if attempt < retry_strategy.max_attempts:
                        delay = retry_strategy.calculate_delay(attempt)
                        logger.warning(f"Attempt {attempt} failed for {service or func.__name__}, "
                                     f"retrying in {delay:.2f}s: {str(e)}")
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(f"All {retry_strategy.max_attempts} attempts failed for "
                                   f"{service or func.__name__}: {str(e)}")
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def with_circuit_breaker(service_or_breaker, failure_threshold: int = 5, 
                        recovery_timeout: int = 60, **kwargs):
    """
    Decorator for adding circuit breaker protection to functions
    Can be used with a breaker instance or service name
    """
    # Handle both old and new calling conventions
    if isinstance(service_or_breaker, str):
        # Create a breaker if called with service name
        breaker = get_circuit_breaker(service_or_breaker)
        if failure_threshold != 5 or recovery_timeout != 60:
            # Create custom breaker with specified params
            breaker = EnhancedCircuitBreaker(
                service_or_breaker, 
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
    else:
        breaker = service_or_breaker
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.async_call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

class ErrorAggregator:
    """
    Aggregate errors for batch operations
    """
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        
    def add_error(self, task_id: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Add an error to the aggregator"""
        error_info = {
            "task_id": task_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow(),
            "context": context or {}
        }
        
        if isinstance(error, EnterpriseError):
            error_info.update({
                "severity": error.severity.value,
                "category": error.category.value,
                "retry_after": error.retry_after,
                "details": error.details
            })
        
        self.errors.append(error_info)
        self.error_counts[error_info["error_type"]] = self.error_counts.get(error_info["error_type"], 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        return {
            "total_errors": len(self.errors),
            "error_types": self.error_counts,
            "errors_by_severity": self._group_by_severity(),
            "errors_by_category": self._group_by_category(),
            "recent_errors": self.errors[-10:] if self.errors else []
        }
    
    def _group_by_severity(self) -> Dict[str, int]:
        """Group errors by severity"""
        severity_counts = {}
        for error in self.errors:
            severity = error.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        return severity_counts
    
    def _group_by_category(self) -> Dict[str, int]:
        """Group errors by category"""
        category_counts = {}
        for error in self.errors:
            category = error.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts
    
    def should_escalate(self) -> bool:
        """Determine if errors should be escalated"""
        # Escalate if too many errors
        if len(self.errors) > 10:
            return True
        
        # Escalate if critical errors
        critical_count = sum(1 for e in self.errors if e.get("severity") == ErrorSeverity.CRITICAL.value)
        if critical_count > 0:
            return True
        
        # Escalate if high error rate for specific types
        for error_type, count in self.error_counts.items():
            if count > 5:
                return True
        
        return False

# Global circuit breakers for services
CIRCUIT_BREAKERS = {
    "agent-factory": EnhancedCircuitBreaker("agent-factory", failure_threshold=5, recovery_timeout=60),
    "validation-mesh": EnhancedCircuitBreaker("validation-mesh", failure_threshold=5, recovery_timeout=60),
    "sandbox": EnhancedCircuitBreaker("sandbox", failure_threshold=3, recovery_timeout=30),
    "vector-memory": EnhancedCircuitBreaker("vector-memory", failure_threshold=10, recovery_timeout=120),
    "github": EnhancedCircuitBreaker("github", failure_threshold=3, recovery_timeout=60)
}

def get_circuit_breaker(service: str) -> EnhancedCircuitBreaker:
    """Get circuit breaker for a service"""
    return CIRCUIT_BREAKERS.get(service, EnhancedCircuitBreaker(service))

def get_all_circuit_breaker_metrics() -> Dict[str, Any]:
    """Get metrics for all circuit breakers"""
    return {name: breaker.get_metrics() for name, breaker in CIRCUIT_BREAKERS.items()}

# Backward compatibility classes
class NonRetryableError(ValidationError):
    """Legacy non-retryable error"""
    pass

class QLPError(EnterpriseError):
    """Legacy QLP error for compatibility"""
    pass

def handle_errors(func):
    """Legacy error handling decorator"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class ErrorHandler:
    """Legacy error handler for compatibility"""
    def handle_error(self, error: Exception, service: str = "unknown", 
                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle error and return details"""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "service": service,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc()
        }
        
        # Log the error
        logger.error(f"Error in {service}: {str(error)}", extra=error_details)
        
        # Determine if retryable
        if isinstance(error, (ValidationError, NonRetryableError)):
            error_details["retryable"] = False
        elif isinstance(error, RetryableError):
            error_details["retryable"] = True
        else:
            # Default: most errors are retryable
            error_details["retryable"] = True
        
        return error_details

# Global error handler instance
error_handler = ErrorHandler()

# Legacy alias for backward compatibility
CircuitBreaker = EnhancedCircuitBreaker