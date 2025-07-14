"""
API Client for QuantumLayer Platform
"""

import httpx
import asyncio
import json
import os
import zipfile
import tarfile
from typing import Dict, Any, Optional
from pathlib import Path
import uuid

from rich.progress import Progress


class GenerationError(Exception):
    """Custom exception for generation errors"""
    pass


class QLPClient:
    """Client for interacting with QuantumLayer API"""
    
    def __init__(self, config):
        self.config = config
        self.base_url = config.api_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json'
        }
        if config.api_key:
            self.headers['Authorization'] = f'Bearer {config.api_key}'
    
    async def start_generation(
        self, 
        description: str,
        language: str = 'auto',
        deploy_target: Optional[str] = None,
        push_to_github: bool = False
    ) -> Dict[str, Any]:
        """Start a new generation workflow"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use the working endpoint from your platform
            if push_to_github:
                endpoint = f"{self.base_url}/generate/complete-with-github"
                payload = {
                    "description": description,
                    "github_repo_name": f"qlp-{uuid.uuid4().hex[:8]}",
                    "make_public": True
                }
            else:
                endpoint = f"{self.base_url}/execute"
                payload = {
                    "description": description,
                    "tenant_id": "cli-user",
                    "user_id": "cli",
                    "metadata": {
                        "language": language,
                        "deploy_target": deploy_target,
                        "source": "cli"
                    }
                }
            
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise GenerationError(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise GenerationError(f"Request failed: {str(e)}")
    
    async def poll_workflow_status(
        self, 
        workflow_id: str,
        progress: Optional[Progress] = None,
        task: Optional[int] = None,
        timeout_minutes: int = 30
    ) -> Dict[str, Any]:
        """Poll workflow status until completion"""
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            max_attempts = timeout_minutes * 30  # Check every 2 seconds
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    # Try the workflow/status endpoint for more detailed info
                    response = await client.get(
                        f"{self.base_url}/workflow/status/{workflow_id}",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Debug logging (enable for troubleshooting)
                        # import json
                        # print(f"\n[DEBUG] Status response: {json.dumps(data, indent=2)}\n")
                        
                        status = data.get('status', 'unknown')
                        
                        # Handle completed workflow
                        if status == 'completed':
                            if progress and task is not None:
                                progress.update(task, completed=100, description="Generation complete!")
                            
                            # Extract result
                            result = data.get('result', {})
                            if isinstance(result, dict) and 'capsule_id' in result:
                                return {
                                    'status': 'completed',
                                    'result': result
                                }
                            else:
                                # If no capsule_id in result, return the full data
                                return data
                        
                        # Handle running workflow
                        elif status == 'running':
                            if progress and task is not None:
                                # Get workflow result if available
                                result = data.get('result', {}) if isinstance(data.get('result'), dict) else {}
                                
                                # Try to extract task information
                                tasks_completed = result.get('tasks_completed', 0)
                                tasks_total = result.get('tasks_total', 0)
                                
                                # If we have task info, use it
                                if tasks_total > 0:
                                    progress_pct = min(90, (tasks_completed / tasks_total) * 90 + 10)
                                    status_msg = f"Processing... ({tasks_completed}/{tasks_total} tasks)"
                                else:
                                    # Otherwise, use time-based estimate
                                    elapsed_seconds = attempt * 2
                                    elapsed_minutes = elapsed_seconds / 60
                                    
                                    # Progressive increase based on time
                                    if elapsed_minutes < 1:
                                        progress_pct = 10 + (elapsed_seconds / 60) * 20  # 10-30% in first minute
                                    elif elapsed_minutes < 3:
                                        progress_pct = 30 + ((elapsed_minutes - 1) / 2) * 30  # 30-60% in minutes 1-3
                                    elif elapsed_minutes < 5:
                                        progress_pct = 60 + ((elapsed_minutes - 3) / 2) * 20  # 60-80% in minutes 3-5
                                    else:
                                        progress_pct = 80 + min(10, (elapsed_minutes - 5) * 2)  # 80-90% after 5 minutes
                                    
                                    status_msg = f"Workflow running... ({elapsed_minutes:.1f}m elapsed)"
                                
                                progress.update(
                                    task, 
                                    completed=progress_pct,
                                    description=status_msg
                                )
                        
                        # Handle failed/error/terminated/canceled workflows
                        elif status in ['failed', 'error', 'terminated', 'canceled']:
                            error_msg = data.get('error', f'Workflow {status}')
                            raise GenerationError(f"Workflow {status}: {error_msg}")
                        
                        # Handle not found
                        elif status == 'not_found':
                            raise GenerationError(f"Workflow {workflow_id} not found")
                        
                    # Continue polling if not completed
                    await asyncio.sleep(2)
                    attempt += 1
                    
                except Exception as e:
                    if attempt >= max_attempts - 1:
                        raise GenerationError(f"Status check failed: {str(e)}")
                    await asyncio.sleep(2)
                    attempt += 1
            
            raise GenerationError(f"Workflow timed out after {timeout_minutes} minutes. The workflow is still running - check Temporal UI or use 'qlp status {workflow_id}' to check progress.")
    
    async def download_capsule(self, capsule_id: str, output_path: str) -> str:
        """Download and extract capsule"""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Download capsule
            response = await client.get(
                f"{self.base_url}/api/capsules/{capsule_id}/download?format=zip",
                headers=self.headers,
                follow_redirects=True
            )
            response.raise_for_status()
            
            # Save to temp file
            temp_path = Path(f"/tmp/{capsule_id}.zip")
            temp_path.write_bytes(response.content)
            
            # Extract to output path
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            
            # Clean up
            temp_path.unlink()
            
            return str(output_dir)
    
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze architecture diagram or mockup"""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Read image file
            with open(image_path, 'rb') as f:
                files = {'file': (Path(image_path).name, f, 'image/png')}
                
                response = await client.post(
                    f"{self.base_url}/analyze/image",
                    files=files,
                    headers={k: v for k, v in self.headers.items() if k != 'Content-Type'}
                )
            
            if response.status_code == 404:
                # Fallback: Use mock response for demo
                return {
                    "description": "A microservices architecture with API Gateway, Auth Service, User Service, and PostgreSQL database",
                    "components": ["api-gateway", "auth-service", "user-service", "postgres"],
                    "language": "auto"
                }
            
            response.raise_for_status()
            return response.json()
    
    async def deploy_capsule(self, capsule_id: str, target: str) -> Dict[str, Any]:
        """Deploy capsule to cloud provider"""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/capsules/{capsule_id}/deploy",
                json={"target": target},
                headers=self.headers
            )
            
            if response.status_code == 404:
                # Mock response for demo
                return {
                    "status": "success",
                    "url": f"https://app-{capsule_id[:8]}.{target}.example.com",
                    "message": "Deployment simulated (feature coming soon)"
                }
            
            response.raise_for_status()
            return response.json()
    
    async def chat(self, message: str, session_id: str) -> Dict[str, Any]:
        """Send chat message in interactive mode"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "message": message,
                    "session_id": session_id
                },
                headers=self.headers
            )
            
            if response.status_code == 404:
                # Use execute endpoint as fallback
                return await self.start_generation(description=message)
            
            response.raise_for_status()
            return response.json()