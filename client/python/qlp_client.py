"""
Quantum Layer Platform Python Client

Official Python client library for the QLP v2 API
"""

from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
from datetime import datetime
import httpx
import asyncio
import time
from urllib.parse import urljoin


@dataclass
class WorkflowResult:
    """Result from a workflow execution"""
    workflow_id: str
    request_id: str
    status: str
    message: str
    links: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class WorkflowStatus:
    """Status of a running workflow"""
    workflow_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]
    progress: Dict[str, Any]
    result_link: Optional[str] = None


@dataclass
class CapsuleResult:
    """Result containing generated code capsule"""
    capsule_id: str
    request_id: str
    status: str
    source_code: Dict[str, str]
    downloads: Dict[str, str]
    metadata: Dict[str, Any]


class QLPClient:
    """
    Python client for Quantum Layer Platform v2 API
    
    Example usage:
        client = QLPClient(api_key="your-api-key")
        
        # Generate code
        result = await client.generate(
            "Create a REST API for user management",
            mode="complete"
        )
        
        # Check status
        status = await client.get_status(result.workflow_id)
        
        # Get result when complete
        capsule = await client.get_result(result.workflow_id)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.quantumlayerplatform.com",
        timeout: float = 300.0
    ):
        """
        Initialize QLP client
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Initialize HTTP client
        headers = {
            "User-Agent": "QLP-Python-Client/2.0",
            "Content-Type": "application/json"
        }
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def generate(
        self,
        description: str,
        *,
        mode: Literal["basic", "complete", "robust"] = "complete",
        user_id: str = "user",
        tenant_id: str = "default",
        tier_override: Optional[str] = None,
        github: Optional[Dict[str, Any]] = None,
        delivery: Optional[Dict[str, Any]] = None,
        validation: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        requirements: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """
        Generate code from natural language description
        
        Args:
            description: Natural language description of what to build
            mode: Execution mode - basic (fast), complete (standard), robust (production)
            user_id: User identifier
            tenant_id: Tenant identifier
            tier_override: Override agent tier (T0, T1, T2, T3)
            github: GitHub integration options
            delivery: Delivery options
            validation: Validation options
            constraints: Language/framework constraints
            requirements: Additional requirements
            metadata: Additional metadata
            
        Returns:
            WorkflowResult with workflow ID and status links
        """
        
        # Build request payload
        payload = {
            "description": description,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "options": {
                "mode": mode,
                "metadata": metadata or {}
            }
        }
        
        # Add optional parameters
        if tier_override:
            payload["options"]["tier_override"] = tier_override
            
        if github:
            payload["options"]["github"] = github
            
        if delivery:
            payload["options"]["delivery"] = delivery
            
        if validation:
            payload["options"]["validation"] = validation
            
        if constraints:
            payload["constraints"] = constraints
            
        if requirements:
            payload["requirements"] = requirements
        
        # Make request
        url = urljoin(self.base_url, "/v2/execute")
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return WorkflowResult(**data)
    
    async def get_status(self, workflow_id: str) -> WorkflowStatus:
        """
        Get workflow status
        
        Args:
            workflow_id: Workflow ID from generate()
            
        Returns:
            WorkflowStatus with current state
        """
        url = urljoin(self.base_url, f"/v2/workflows/{workflow_id}")
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse timestamps
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
            
        return WorkflowStatus(**data)
    
    async def get_result(self, workflow_id: str) -> CapsuleResult:
        """
        Get workflow result (generated code capsule)
        
        Args:
            workflow_id: Workflow ID from generate()
            
        Returns:
            CapsuleResult with generated code and download links
        """
        url = urljoin(self.base_url, f"/v2/workflows/{workflow_id}/result")
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return CapsuleResult(**data)
    
    async def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Cancel a running workflow
        
        Args:
            workflow_id: Workflow ID to cancel
            
        Returns:
            Cancellation confirmation
        """
        url = urljoin(self.base_url, f"/v2/workflows/{workflow_id}/cancel")
        response = await self.client.post(url)
        response.raise_for_status()
        
        return response.json()
    
    async def download_capsule(
        self,
        capsule_id: str,
        format: Literal["zip", "tar", "targz"] = "zip"
    ) -> bytes:
        """
        Download capsule in specified format
        
        Args:
            capsule_id: Capsule ID from result
            format: Download format
            
        Returns:
            Capsule file contents as bytes
        """
        url = urljoin(
            self.base_url,
            f"/v2/capsules/{capsule_id}/download?format={format}"
        )
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.content
    
    async def wait_for_completion(
        self,
        workflow_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None
    ) -> CapsuleResult:
        """
        Wait for workflow to complete and return result
        
        Args:
            workflow_id: Workflow ID to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait (None for no timeout)
            
        Returns:
            CapsuleResult when workflow completes
            
        Raises:
            TimeoutError: If timeout is exceeded
            RuntimeError: If workflow fails
        """
        start_time = time.time()
        
        while True:
            status = await self.get_status(workflow_id)
            
            if status.status == "COMPLETED":
                return await self.get_result(workflow_id)
            elif status.status == "FAILED":
                raise RuntimeError(f"Workflow failed: {workflow_id}")
            elif status.status == "CANCELLED":
                raise RuntimeError(f"Workflow cancelled: {workflow_id}")
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Workflow did not complete within {timeout}s")
            
            # Wait before next check
            await asyncio.sleep(poll_interval)
    
    # Convenience methods for common use cases
    
    async def generate_and_wait(
        self,
        description: str,
        **kwargs
    ) -> CapsuleResult:
        """
        Generate code and wait for completion
        
        Convenience method that combines generate() and wait_for_completion()
        
        Args:
            description: Natural language description
            **kwargs: Additional arguments for generate()
            
        Returns:
            CapsuleResult with generated code
        """
        result = await self.generate(description, **kwargs)
        return await self.wait_for_completion(result.workflow_id)
    
    async def generate_basic(self, description: str, **kwargs) -> CapsuleResult:
        """Generate code with basic mode (fast, minimal validation)"""
        kwargs["mode"] = "basic"
        return await self.generate_and_wait(description, **kwargs)
    
    async def generate_complete(self, description: str, **kwargs) -> CapsuleResult:
        """Generate code with complete mode (standard validation and tests)"""
        kwargs["mode"] = "complete"
        return await self.generate_and_wait(description, **kwargs)
    
    async def generate_robust(self, description: str, **kwargs) -> CapsuleResult:
        """Generate code with robust mode (production-grade with full validation)"""
        kwargs["mode"] = "robust"
        return await self.generate_and_wait(description, **kwargs)
    
    async def generate_with_github(
        self,
        description: str,
        *,
        github_token: str,
        repo_name: str,
        private: bool = False,
        **kwargs
    ) -> CapsuleResult:
        """
        Generate code and push to GitHub
        
        Args:
            description: Natural language description
            github_token: GitHub personal access token
            repo_name: Repository name to create
            private: Whether to create private repository
            **kwargs: Additional arguments for generate()
            
        Returns:
            CapsuleResult with GitHub repository URL
        """
        kwargs["github"] = {
            "enabled": True,
            "token": github_token,
            "repo_name": repo_name,
            "private": private
        }
        return await self.generate_and_wait(description, **kwargs)


# Synchronous wrapper for ease of use
class QLPClientSync:
    """
    Synchronous wrapper for QLPClient
    
    Example:
        client = QLPClientSync(api_key="your-api-key")
        result = client.generate("Create a REST API")
        print(result.source_code)
    """
    
    def __init__(self, *args, **kwargs):
        self._async_client = QLPClient(*args, **kwargs)
        self._loop = None
    
    def _run(self, coro):
        """Run async coroutine in sync context"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop:
            # We're in an async context, create new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # No async loop, we can run directly
            return asyncio.run(coro)
    
    def generate(self, *args, **kwargs) -> WorkflowResult:
        """Synchronous version of generate()"""
        return self._run(self._async_client.generate(*args, **kwargs))
    
    def get_status(self, *args, **kwargs) -> WorkflowStatus:
        """Synchronous version of get_status()"""
        return self._run(self._async_client.get_status(*args, **kwargs))
    
    def get_result(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of get_result()"""
        return self._run(self._async_client.get_result(*args, **kwargs))
    
    def generate_and_wait(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of generate_and_wait()"""
        return self._run(self._async_client.generate_and_wait(*args, **kwargs))
    
    def generate_basic(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of generate_basic()"""
        return self._run(self._async_client.generate_basic(*args, **kwargs))
    
    def generate_complete(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of generate_complete()"""
        return self._run(self._async_client.generate_complete(*args, **kwargs))
    
    def generate_robust(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of generate_robust()"""
        return self._run(self._async_client.generate_robust(*args, **kwargs))
    
    def generate_with_github(self, *args, **kwargs) -> CapsuleResult:
        """Synchronous version of generate_with_github()"""
        return self._run(self._async_client.generate_with_github(*args, **kwargs))
    
    def close(self):
        """Close the client"""
        self._run(self._async_client.close())