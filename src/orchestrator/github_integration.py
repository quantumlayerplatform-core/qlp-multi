#!/usr/bin/env python3
"""
GitHub Integration for QLCapsules
Automatically create repositories and push capsule contents
"""

import os
import base64
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import asyncio
from pathlib import Path
import structlog

from src.common.models import QLCapsule
from src.orchestrator.capsule_storage import CapsuleStorageService

logger = structlog.get_logger()


class GitHubIntegration:
    """Handles GitHub repository creation and code pushing"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable.")
        
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def create_repository(
        self,
        name: str,
        description: str,
        private: bool = False,
        auto_init: bool = False
    ) -> Dict[str, Any]:
        """Create a new GitHub repository"""
        
        # Clean repository name
        repo_name = name.lower().replace(" ", "-").replace("_", "-")
        repo_name = "".join(c for c in repo_name if c.isalnum() or c == "-")
        
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/user/repos",
                headers=self.headers,
                json=data
            ) as response:
                if response.status == 201:
                    repo_data = await response.json()
                    logger.info(f"Created repository: {repo_data['full_name']}")
                    return repo_data
                elif response.status == 422:
                    # Repository already exists
                    error_data = await response.json()
                    if "already exists" in str(error_data):
                        # Get existing repo
                        user = await self.get_authenticated_user()
                        return await self.get_repository(user['login'], repo_name)
                    raise Exception(f"Failed to create repository: {error_data}")
                else:
                    error = await response.text()
                    raise Exception(f"Failed to create repository: {error}")
    
    async def get_authenticated_user(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/user",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception("Failed to get user information")
    
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/repos/{owner}/{repo}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Repository {owner}/{repo} not found")
    
    async def create_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a file in the repository"""
        
        # Encode content to base64
        encoded_content = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.api_base}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                json=data
            ) as response:
                if response.status in [201, 200]:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to create file {path}: {error}")
    
    async def create_multiple_files(
        self,
        owner: str,
        repo: str,
        files: Dict[str, str],
        message: str,
        branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """Create multiple files in the repository"""
        results = []
        
        # Sort files to ensure parent directories are created first
        # This is important for paths like .github/workflows/ci.yml
        sorted_files = []
        for path in sorted(files.keys()):
            # For paths with directories, ensure we process them in order
            if '/' in path:
                # Ensure parent directories by adding placeholder files if needed
                parts = path.split('/')
                for i in range(1, len(parts)):
                    parent_path = '/'.join(parts[:i]) + '/.gitkeep'
                    if parent_path not in files and not any(f[0].startswith('/'.join(parts[:i]) + '/') for f in sorted_files):
                        sorted_files.append((parent_path, ''))
            sorted_files.append((path, files[path]))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for path, content in sorted_files:
            if path not in seen:
                seen.add(path)
                unique_files.append((path, content))
        
        # Create files in order with rate limiting
        semaphore = asyncio.Semaphore(3)  # Reduce concurrent requests to avoid rate limits
        
        async def create_with_limit(path: str, content: str):
            async with semaphore:
                try:
                    # Skip .gitkeep files if other files will be created in the directory
                    if path.endswith('/.gitkeep') and any(f[0].startswith(path.rsplit('/', 1)[0] + '/') and not f[0].endswith('/.gitkeep') for f in unique_files):
                        logger.debug(f"Skipping {path} as directory will contain other files")
                        return {"path": path, "success": True, "result": {"skipped": True}}
                    
                    result = await self.create_file(owner, repo, path, content, message, branch)
                    logger.info(f"Successfully created file: {path}")
                    return {"path": path, "success": True, "result": result}
                except Exception as e:
                    logger.error(f"Failed to create file {path}: {str(e)}")
                    return {"path": path, "success": False, "error": str(e)}
        
        # Create files sequentially for directories, parallel for others
        results = []
        for path, content in unique_files:
            result = await create_with_limit(path, content)
            results.append(result)
            # Small delay to avoid rate limiting
            if '/' in path:
                await asyncio.sleep(0.1)
        
        # Check for errors
        failed_files = [r for r in results if not r.get("success", False)]
        successful_files = [r for r in results if r.get("success", False)]
        
        if failed_files:
            logger.error(f"Failed to create {len(failed_files)} files:")
            for failed in failed_files:
                logger.error(f"  - {failed['path']}: {failed.get('error', 'Unknown error')}")
        
        logger.info(f"Successfully created {len(successful_files)} out of {len(files)} files")
        
        # Return only successful results for backward compatibility, excluding skipped files
        return [r["result"] for r in results if r.get("success", False) and not r.get("result", {}).get("skipped", False)]
    
    async def push_capsule(
        self,
        capsule: QLCapsule,
        repo_name: Optional[str] = None,
        private: bool = False,
        create_pull_request: bool = False
    ) -> Dict[str, Any]:
        """Push an entire capsule to GitHub"""
        
        # Generate repository name from capsule
        if not repo_name:
            manifest = capsule.manifest
            name = manifest.get('name', f'qlp-capsule-{capsule.id[:8]}')
            repo_name = name.lower().replace(" ", "-")
        
        # Create repository
        description = capsule.manifest.get('description', 'Generated by Quantum Layer Platform')
        repo = await self.create_repository(repo_name, description, private, auto_init=False)
        
        # Prepare all files
        files = {}
        
        # Add source code
        for file_path, content in capsule.source_code.items():
            # Handle double-encoded content
            if isinstance(content, str) and content.startswith("{") and "content" in content:
                try:
                    # Parse the JSON-like structure
                    import ast
                    parsed = ast.literal_eval(content)
                    actual_content = parsed.get('content', content)
                    # Remove markdown code blocks if present
                    if actual_content.startswith('```'):
                        lines = actual_content.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]  # Remove first line
                        if lines and lines[-1].strip() == '```':
                            lines = lines[:-1]  # Remove last line
                        actual_content = '\n'.join(lines)
                    files[file_path] = actual_content
                    logger.debug(f"Parsed wrapped content for {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to parse wrapped content for {file_path}: {e}")
                    files[file_path] = content
            else:
                files[file_path] = content
        
        # Add tests
        for file_path, content in capsule.tests.items():
            # Handle double-encoded content (same as source code)
            if isinstance(content, str) and content.startswith("{") and "content" in content:
                try:
                    # Parse the JSON-like structure
                    import ast
                    parsed = ast.literal_eval(content)
                    actual_content = parsed.get('content', content)
                    # Remove markdown code blocks if present
                    if actual_content.startswith('```'):
                        lines = actual_content.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]  # Remove first line
                        if lines and lines[-1].strip() == '```':
                            lines = lines[:-1]  # Remove last line
                        actual_content = '\n'.join(lines)
                    files[file_path] = actual_content
                except Exception as e:
                    logger.warning(f"Failed to parse wrapped content for {file_path}: {e}")
                    files[file_path] = content
            else:
                files[file_path] = content
        
        # Add documentation
        if capsule.documentation:
            files["README.md"] = capsule.documentation
        
        # Add manifest
        files["qlp-manifest.json"] = json.dumps(capsule.manifest, indent=2)
        
        # Add metadata
        files["qlp-metadata.json"] = json.dumps(capsule.metadata, indent=2)
        
        # Add deployment config if exists
        if capsule.deployment_config:
            files["qlp-deployment.json"] = json.dumps(capsule.deployment_config, indent=2)
        
        # Add validation report if exists
        if capsule.validation_report:
            files["qlp-validation.json"] = json.dumps(
                capsule.validation_report.model_dump(), 
                indent=2
            )
        
        # Add .gitignore
        files[".gitignore"] = self._generate_gitignore(capsule)
        
        # Add GitHub Actions workflow
        files[".github/workflows/ci.yml"] = self._generate_github_actions(capsule)
        
        # Push all files
        commit_message = f"Initial commit: {capsule.manifest.get('name', 'QLCapsule')}\n\nGenerated by Quantum Layer Platform"
        
        owner = repo['owner']['login']
        repo_name = repo['name']
        
        # Create files
        created_files = await self.create_multiple_files(
            owner,
            repo_name,
            files,
            commit_message
        )
        
        # Check if all files were created
        if len(created_files) < len(files):
            logger.warning(
                f"Only {len(created_files)} out of {len(files)} files were created. "
                f"Check logs for details."
            )
        
        logger.info(f"Successfully pushed capsule to {repo['html_url']}")
        
        return {
            "repository_url": repo['html_url'],
            "clone_url": repo['clone_url'],
            "ssh_url": repo['ssh_url'],
            "owner": owner,
            "name": repo_name,
            "private": repo['private'],
            "files_created": len(created_files)  # Return actual count of created files
        }
    
    def _generate_gitignore(self, capsule: QLCapsule) -> str:
        """Generate appropriate .gitignore file"""
        language = capsule.manifest.get('language', '').lower()
        
        common = """
# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
.env.*.local

# Logs
logs/
*.log
"""
        
        if language == 'python':
            return common + """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
"""
        elif language in ['javascript', 'typescript']:
            return common + """
# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
dist/
build/
.next/
out/
"""
        else:
            return common
    
    def _generate_github_actions(self, capsule: QLCapsule) -> str:
        """Generate GitHub Actions workflow"""
        language = capsule.manifest.get('language', '').lower()
        
        if language == 'python':
            return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src
    
    - name: Lint
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
"""
        elif language in ['javascript', 'typescript']:
            return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Use Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test
    
    - name: Build
      run: npm run build
"""
        else:
            return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build
      run: echo "Add build steps here"
    
    - name: Test
      run: echo "Add test steps here"
"""


class GitHubService:
    """Service for GitHub operations integrated with QLP"""
    
    def __init__(self, db):
        self.db = db
        self.storage = CapsuleStorageService(db)
        self.github = None
    
    def initialize_github(self, token: Optional[str] = None):
        """Initialize GitHub client"""
        self.github = GitHubIntegration(token)
    
    async def push_capsule_to_github(
        self,
        capsule_id: str,
        token: Optional[str] = None,
        repo_name: Optional[str] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """Push a capsule from database to GitHub"""
        
        # Get capsule from database
        capsule = await self.storage.get_capsule(capsule_id)
        if not capsule:
            raise ValueError(f"Capsule {capsule_id} not found")
        
        # Initialize GitHub if needed
        if not self.github:
            self.initialize_github(token)
        
        # Push to GitHub
        result = await self.github.push_capsule(capsule, repo_name, private)
        
        # Store GitHub URL in capsule metadata
        capsule.metadata["github_url"] = result["repository_url"]
        capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
        
        # Update capsule in database
        await self.storage.update_capsule_metadata(capsule_id, capsule.metadata)
        
        return result