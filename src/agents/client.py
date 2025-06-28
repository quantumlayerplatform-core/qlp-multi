"""
Client for Agent Factory service
"""

from typing import Dict, Any
import httpx
from src.common.models import Task, TaskResult, AgentTier, AgentExecutionRequest, ExecutionResult
from fastapi.encoders import jsonable_encoder


class AgentFactoryClient:
    """Client for interacting with the Agent Factory service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def execute(self, request: AgentExecutionRequest) -> ExecutionResult:
        """Execute an agent request"""
        response = await self.client.post(
            f"{self.base_url}/execute",
            json=jsonable_encoder(request)
        )
        response.raise_for_status()
        return ExecutionResult(**response.json())
    
    async def execute_task(self, task: Task, tier: AgentTier, context: Dict[str, Any]) -> TaskResult:
        """Execute a task using an agent"""
        response = await self.client.post(
            f"{self.base_url}/execute",
            json={
                "task": jsonable_encoder(task),
                "tier": tier.value,
                "context": context
            }
        )
        response.raise_for_status()
        return TaskResult(**response.json())
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        response = await self.client.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
