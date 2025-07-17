#!/usr/bin/env python3
"""
Enhanced pattern population script for Qdrant Cloud
Includes architectural patterns, best practices, and common solutions
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Any
import httpx
import json

# Enhanced patterns for better code generation
ARCHITECTURAL_PATTERNS = [
    {
        "pattern_name": "microservice_architecture",
        "description": "Modern microservice with health checks, metrics, and proper error handling",
        "code_template": '''
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import prometheus_client
import logging
from datetime import datetime

app = FastAPI(title="{service_name}", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics
REQUEST_COUNT = prometheus_client.Counter(
    'requests_total', 'Total requests', ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = prometheus_client.Histogram(
    'request_latency_seconds', 'Request latency'
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "timestamp": datetime.utcnow().isoformat()}}

@app.get("/metrics")
async def metrics():
    return prometheus_client.generate_latest()
''',
        "tags": ["microservice", "fastapi", "monitoring", "production"],
        "language": "python",
        "complexity": "medium"
    },
    {
        "pattern_name": "repository_pattern",
        "description": "Data access layer with repository pattern",
        "code_template": '''
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Abstract base repository"""
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        pass

class {entity_name}Repository(BaseRepository):
    """Repository for {entity_name} entity"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Creating {entity_name}: {{data}}")
        # Implementation here
        pass
''',
        "tags": ["repository", "data-access", "clean-architecture"],
        "language": "python",
        "complexity": "medium"
    },
    {
        "pattern_name": "event_driven_architecture",
        "description": "Event-driven service with message queue integration",
        "code_template": '''
import asyncio
import json
from typing import Dict, Any, Callable
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Base event class"""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = None
    correlation_id: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

class EventBus:
    """Simple event bus implementation"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {{}}
    
    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Subscribed handler to {{event_type}}")
    
    async def publish(self, event: Event):
        logger.info(f"Publishing event: {{event.event_type}}")
        
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Handler error: {{e}}")
''',
        "tags": ["event-driven", "messaging", "async", "scalable"],
        "language": "python",
        "complexity": "complex"
    },
    {
        "pattern_name": "circuit_breaker",
        "description": "Circuit breaker pattern for fault tolerance",
        "code_template": '''
import asyncio
import time
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 half_open_requests: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_count = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_count += 1
            if self.half_open_count >= self.half_open_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {{self.failure_count}} failures")
''',
        "tags": ["resilience", "fault-tolerance", "circuit-breaker", "production"],
        "language": "python",
        "complexity": "complex"
    }
]

CODING_BEST_PRACTICES = [
    {
        "practice_name": "comprehensive_error_handling",
        "description": "Production-grade error handling with logging and recovery",
        "example": '''
import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ApplicationError(Exception):
    """Base application error"""
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {{}}
        self.timestamp = datetime.utcnow()

class ValidationError(ApplicationError):
    """Validation error"""
    def __init__(self, message: str, field: str, value: Any):
        super().__init__(message, "VALIDATION_ERROR", {{"field": field, "value": value}})

def handle_errors(func):
    """Decorator for comprehensive error handling"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {{e.message}}", extra={{"error_details": e.details}})
            raise
        except ApplicationError as e:
            logger.error(f"Application error: {{e.message}}", extra={{"error_code": e.error_code}})
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {{str(e)}}", exc_info=True)
            # Log full traceback for debugging
            logger.debug(traceback.format_exc())
            raise ApplicationError("Internal server error", "INTERNAL_ERROR", {{"original_error": str(e)}})
    return wrapper
''',
        "tags": ["error-handling", "logging", "production", "best-practice"],
        "language": "python"
    },
    {
        "practice_name": "structured_logging",
        "description": "Structured logging for better observability",
        "example": '''
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class LogContext:
    """Context manager for structured logging"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.logger = logger.bind(**kwargs)
    
    def __enter__(self):
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error("Exception in context", 
                            exc_type=exc_type.__name__, 
                            exc_message=str(exc_val))

# Usage example
async def process_request(request_id: str, user_id: str, data: Dict[str, Any]):
    with LogContext(request_id=request_id, user_id=user_id) as log:
        log.info("Processing request", data_size=len(str(data)))
        
        try:
            # Process data
            result = await process_data(data)
            log.info("Request processed successfully", result_size=len(str(result)))
            return result
        except Exception as e:
            log.error("Request processing failed", error=str(e))
            raise
''',
        "tags": ["logging", "observability", "structured-logging", "monitoring"],
        "language": "python"
    },
    {
        "practice_name": "async_optimization",
        "description": "Optimized async patterns for performance",
        "example": '''
import asyncio
from typing import List, Dict, Any, TypeVar, Callable
import aiohttp
from functools import wraps
import time

T = TypeVar('T')

async def gather_with_concurrency(n: int, *tasks) -> List[Any]:
    """Limit concurrent async operations"""
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[sem_task(task) for task in tasks])

class AsyncBatcher:
    """Batch async operations for efficiency"""
    
    def __init__(self, batch_size: int = 10, wait_time: float = 0.1):
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.pending: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {{}}
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(lock=self.lock)
    
    async def add(self, key: str, operation: Callable) -> Any:
        async with self.condition:
            self.pending.append({{"key": key, "operation": operation}})
            
            if len(self.pending) >= self.batch_size:
                await self._process_batch()
            else:
                # Wait for batch to fill or timeout
                try:
                    await asyncio.wait_for(
                        self.condition.wait(), 
                        timeout=self.wait_time
                    )
                except asyncio.TimeoutError:
                    if self.pending:
                        await self._process_batch()
            
            return self.results.get(key)
    
    async def _process_batch(self):
        if not self.pending:
            return
        
        batch = self.pending[:self.batch_size]
        self.pending = self.pending[self.batch_size:]
        
        # Process batch concurrently
        results = await asyncio.gather(
            *[item["operation"]() for item in batch],
            return_exceptions=True
        )
        
        # Store results
        for item, result in zip(batch, results):
            self.results[item["key"]] = result
        
        self.condition.notify_all()

def measure_async_performance(func):
    """Decorator to measure async function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{{func.__name__}} completed in {{elapsed:.3f}}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{{func.__name__}} failed after {{elapsed:.3f}}s: {{e}}")
            raise
    return wrapper
''',
        "tags": ["async", "performance", "optimization", "concurrency"],
        "language": "python"
    }
]

TEST_PATTERNS = [
    {
        "pattern_name": "comprehensive_test_suite",
        "description": "Complete test suite with unit, integration, and performance tests",
        "code_template": '''
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import time
from typing import Any
import httpx

# Fixtures
@pytest.fixture
def mock_database():
    """Mock database for testing"""
    db = Mock()
    db.query = AsyncMock(return_value=[])
    db.insert = AsyncMock(return_value={{"id": "test-id"}})
    return db

@pytest.fixture
async def test_client():
    """Test client for API testing"""
    from app import app
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Unit Tests
class Test{entity_name}Service:
    """Unit tests for {entity_name} service"""
    
    @pytest.mark.asyncio
    async def test_create_{entity_name}(self, mock_database):
        # Arrange
        service = {entity_name}Service(mock_database)
        data = {{"name": "test", "value": 123}}
        
        # Act
        result = await service.create(data)
        
        # Assert
        assert result["id"] == "test-id"
        mock_database.insert.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_database):
        # Arrange
        mock_database.query.side_effect = Exception("Database error")
        service = {entity_name}Service(mock_database)
        
        # Act & Assert
        with pytest.raises(ServiceError) as exc_info:
            await service.get_by_id("test-id")
        
        assert "Database error" in str(exc_info.value)

# Integration Tests
@pytest.mark.integration
class TestAPI:
    """Integration tests for API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_endpoint(self, test_client):
        # Arrange
        payload = {{"name": "test", "value": 123}}
        
        # Act
        response = await test_client.post("/api/items", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test"
    
    @pytest.mark.asyncio
    async def test_error_response(self, test_client):
        # Act
        response = await test_client.get("/api/items/non-existent")
        
        # Assert
        assert response.status_code == 404
        error = response.json()
        assert "error" in error

# Performance Tests
@pytest.mark.performance
class TestPerformance:
    """Performance tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client):
        # Arrange
        num_requests = 100
        
        # Act
        start_time = time.time()
        tasks = [test_client.get("/api/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Assert
        assert all(r.status_code == 200 for r in responses)
        assert elapsed < 5.0  # Should handle 100 requests in under 5 seconds
        
        # Calculate requests per second
        rps = num_requests / elapsed
        print(f"Performance: {{rps:.2f}} requests/second")
''',
        "tags": ["testing", "pytest", "unit-test", "integration-test", "performance-test"],
        "language": "python",
        "complexity": "complex"
    }
]

async def populate_enhanced_patterns():
    """Populate Qdrant with enhanced patterns"""
    
    vector_memory_url = os.getenv("VECTOR_MEMORY_URL", "http://localhost:8003")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🚀 Populating enhanced patterns...")
        
        # Store architectural patterns
        for pattern in ARCHITECTURAL_PATTERNS:
            try:
                response = await client.post(
                    f"{vector_memory_url}/patterns/code",
                    json={
                        "content": pattern["code_template"],
                        "metadata": {
                            "pattern_name": pattern["pattern_name"],
                            "description": pattern["description"],
                            "tags": pattern["tags"],
                            "language": pattern["language"],
                            "complexity": pattern["complexity"],
                            "pattern_type": "architectural",
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }
                )
                if response.status_code == 200:
                    print(f"✅ Stored pattern: {pattern['pattern_name']}")
                else:
                    print(f"❌ Failed to store {pattern['pattern_name']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error storing {pattern['pattern_name']}: {e}")
        
        # Store best practices
        for practice in CODING_BEST_PRACTICES:
            try:
                response = await client.post(
                    f"{vector_memory_url}/patterns/code",
                    json={
                        "content": practice["example"],
                        "metadata": {
                            "pattern_name": practice["practice_name"],
                            "description": practice["description"],
                            "tags": practice["tags"],
                            "language": practice["language"],
                            "pattern_type": "best_practice",
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }
                )
                if response.status_code == 200:
                    print(f"✅ Stored practice: {practice['practice_name']}")
            except Exception as e:
                print(f"❌ Error storing {practice['practice_name']}: {e}")
        
        # Store test patterns
        for test_pattern in TEST_PATTERNS:
            try:
                response = await client.post(
                    f"{vector_memory_url}/patterns/code",
                    json={
                        "content": test_pattern["code_template"],
                        "metadata": {
                            "pattern_name": test_pattern["pattern_name"],
                            "description": test_pattern["description"],
                            "tags": test_pattern["tags"],
                            "language": test_pattern["language"],
                            "complexity": test_pattern["complexity"],
                            "pattern_type": "testing",
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }
                )
                if response.status_code == 200:
                    print(f"✅ Stored test pattern: {test_pattern['pattern_name']}")
            except Exception as e:
                print(f"❌ Error storing {test_pattern['pattern_name']}: {e}")
        
        print("\n✨ Pattern population completed!")

if __name__ == "__main__":
    asyncio.run(populate_enhanced_patterns())