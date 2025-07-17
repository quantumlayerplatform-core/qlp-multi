"""
Client for Sandbox service
"""

from typing import Dict, Any, Optional
import httpx
from src.common.models import ExecutionResult
from fastapi.encoders import jsonable_encoder


class SandboxServiceClient:
    """Client for interacting with the Sandbox service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def execute(self, code: str, language: str, inputs: Optional[Dict[str, Any]] = None, 
                      runtime: str = "docker", **kwargs) -> ExecutionResult:
        """Execute code in sandbox
        
        Args:
            code: Code to execute
            language: Programming language
            inputs: Optional input data
            runtime: Execution runtime ('docker' or 'kata')
            **kwargs: Extra parameters for compatibility
        """
        response = await self.client.post(
            f"{self.base_url}/execute",
            json={
                "code": code,
                "language": language,
                "inputs": inputs or {},
                "runtime": runtime
            }
        )
        response.raise_for_status()
        
        # Convert sandbox response to common ExecutionResult format
        sandbox_result = response.json()
        return ExecutionResult(
            success=sandbox_result.get("status") == "success",
            output=sandbox_result.get("output", ""),
            error=sandbox_result.get("error"),
            execution_time=(sandbox_result.get("duration_ms", 0) / 1000.0) if sandbox_result.get("duration_ms") else 0.0,
            metadata={
                "execution_id": sandbox_result.get("execution_id"),
                "status": sandbox_result.get("status"),
                "exit_code": sandbox_result.get("exit_code"),
                "resource_usage": sandbox_result.get("resource_usage", {})
            }
        )
    
    async def get_languages(self) -> list:
        """Get supported languages"""
        response = await self.client.get(f"{self.base_url}/languages")
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
