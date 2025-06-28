"""
Client for Validation Mesh service
"""

from typing import Dict, Any
import httpx
from src.common.models import TaskResult, ValidationReport
from fastapi.encoders import jsonable_encoder


class ValidationMeshClient:
    """Client for interacting with the Validation Mesh service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def validate_execution(self, results: Dict[str, TaskResult]) -> ValidationReport:
        """Validate execution results"""
        response = await self.client.post(
            f"{self.base_url}/validate",
            json={"results": {k: jsonable_encoder(v) for k, v in results.items()}}
        )
        response.raise_for_status()
        return ValidationReport(**response.json())
    
    async def validate_code(self, code: str, language: str = "python", validators: list = None) -> Dict[str, Any]:
        """Validate a specific piece of code"""
        payload = {"code": code, "language": language}
        if validators:
            payload["validators"] = validators
        response = await self.client.post(
            f"{self.base_url}/validate/code",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
