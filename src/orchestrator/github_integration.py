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
        
        # Create files in parallel with rate limiting
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def create_with_limit(path: str, content: str):
            async with semaphore:
                return await self.create_file(owner, repo, path, content, message, branch)
        
        tasks = [
            create_with_limit(path, content)
            for path, content in files.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(f"Errors creating files: {errors}")
        
        return [r for r in results if not isinstance(r, Exception)]
    
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
        repo = await self.create_repository(repo_name, description, private)
        
        # Prepare all files
        files = {}
        
        # Add source code
        for file_path, content in capsule.source_code.items():
            files[file_path] = content
        
        # Add tests
        for file_path, content in capsule.tests.items():
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
        await self.create_multiple_files(
            owner,
            repo_name,
            files,
            commit_message
        )
        
        logger.info(f"Successfully pushed capsule to {repo['html_url']}")
        
        return {
            "repository_url": repo['html_url'],
            "clone_url": repo['clone_url'],
            "ssh_url": repo['ssh_url'],
            "owner": owner,
            "name": repo_name,
            "private": repo['private'],
            "files_created": len(files)
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
        capsule_data = await self.storage.get_capsule(capsule_id)
        if not capsule_data:
            raise ValueError(f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        
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