"""
Stub services for testing the orchestration flow
"""

from fastapi import FastAPI
from typing import Dict, Any, List
import random
from datetime import datetime
import uvicorn

# Vector Memory Stub
memory_app = FastAPI(title="Vector Memory Stub")

@memory_app.post("/search/requests")
async def search_requests(body: Dict[str, Any]):
    return [
        {
            "description": "Similar request example",
            "tasks": ["task1", "task2"],
            "success_rate": 0.95
        }
    ]

@memory_app.post("/search/code")
async def search_code(body: Dict[str, Any]):
    return [
        {
            "description": "Similar code pattern",
            "code": "def example(): pass",
            "usage_count": 10
        }
    ]

@memory_app.post("/store/decomposition")
async def store_decomposition(body: Dict[str, Any]):
    return {"status": "stored"}

@memory_app.get("/performance/task")
async def get_task_performance(type: str, complexity: str):
    return {
        "optimal_tier": "T1",
        "success_rate": 0.9,
        "avg_time": 30
    }

@memory_app.post("/store/capsule")
async def store_capsule(body: Dict[str, Any]):
    return {"status": "stored"}

@memory_app.post("/store/metrics")
async def store_metrics(body: Dict[str, Any]):
    return {"status": "stored"}

@memory_app.get("/health")
async def memory_health():
    return {"status": "healthy", "service": "vector-memory-stub"}

# Validation Mesh Stub
validation_app = FastAPI(title="Validation Mesh Stub")

@validation_app.post("/validate")
async def validate_execution(body: Dict[str, Any]):
    return {
        "id": "val-123",
        "execution_id": "exec-123",
        "overall_status": "passed",
        "checks": [
            {
                "name": "syntax_check",
                "type": "static_analysis",
                "status": "passed",
                "message": "No syntax errors found"
            },
            {
                "name": "security_check",
                "type": "security",
                "status": "passed",
                "message": "No security vulnerabilities detected"
            }
        ],
        "confidence_score": 0.95,
        "requires_human_review": False,
        "created_at": datetime.utcnow().isoformat()
    }

@validation_app.get("/health")
async def validation_health():
    return {"status": "healthy", "service": "validation-mesh-stub"}

# Run both stubs
if __name__ == "__main__":
    import threading
    
    # Run memory stub
    memory_thread = threading.Thread(
        target=lambda: uvicorn.run(memory_app, host="0.0.0.0", port=8003)
    )
    memory_thread.daemon = True
    memory_thread.start()
    
    # Run validation stub
    uvicorn.run(validation_app, host="0.0.0.0", port=8002)
