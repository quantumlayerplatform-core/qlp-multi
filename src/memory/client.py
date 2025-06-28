"""
Client for Vector Memory service
"""

from typing import Dict, Any, List, Optional
import httpx
from src.common.models import QLCapsule, AgentMetrics, Task, ExecutionResult
from fastapi.encoders import jsonable_encoder


class VectorMemoryClient:
    """Client for interacting with the Vector Memory service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_similar_requests(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar past requests"""
        response = await self.client.post(
            f"{self.base_url}/search/requests",
            json={"description": description, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    
    async def search_code_patterns(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar code patterns"""
        response = await self.client.post(
            f"{self.base_url}/search/code",
            json={"query": query, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    
    async def store_execution(self, request_id: str, task: Task, result: ExecutionResult):
        """Store task execution for learning"""
        response = await self.client.post(
            f"{self.base_url}/store/execution",
            json={
                "request_id": request_id,
                "task": jsonable_encoder(task),
                "result": jsonable_encoder(result)
            }
        )
        response.raise_for_status()
    
    async def store_decomposition(self, request, tasks, dependencies):
        """Store request decomposition for future learning"""
        response = await self.client.post(
            f"{self.base_url}/store/decomposition",
            json={
                "request": jsonable_encoder(request),
                "tasks": [jsonable_encoder(t) for t in tasks],
                "dependencies": dependencies
            }
        )
        response.raise_for_status()
    
    async def get_task_performance(self, task_type: str, complexity: str) -> Optional[Dict[str, Any]]:
        """Get historical performance data for task type"""
        response = await self.client.get(
            f"{self.base_url}/performance/task",
            params={"type": task_type, "complexity": complexity}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    async def store_capsule(self, capsule: QLCapsule):
        """Store a QLCapsule"""
        response = await self.client.post(
            f"{self.base_url}/store/capsule",
            json=jsonable_encoder(capsule)
        )
        response.raise_for_status()
    
    async def store_agent_metrics(self, metrics: AgentMetrics):
        """Store agent performance metrics"""
        response = await self.client.post(
            f"{self.base_url}/store/metrics",
            json=jsonable_encoder(metrics)
        )
        response.raise_for_status()
    
    async def store_execution_pattern(self, pattern_data: Dict[str, Any]):
        """Store execution pattern for ensemble learning"""
        response = await self.client.post(
            f"{self.base_url}/patterns/execution",
            json=pattern_data
        )
        response.raise_for_status()
    
    async def search_patterns(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for code patterns in vector memory
        
        This method searches for similar patterns based on the query text.
        Used by pattern-based generation strategy.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/search/patterns",
                json={"query": query, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # If endpoint not implemented, fall back to code patterns
            if e.response.status_code == 404:
                return await self.search_code_patterns(query, limit)
            raise
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
