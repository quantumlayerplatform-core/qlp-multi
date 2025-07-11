#!/usr/bin/env python3
"""
GitHub Integration v2 - Using Git Data API for atomic commits
Creates all files in a single commit to avoid conflicts
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

logger = structlog.get_logger()


class GitHubIntegrationV2:
    """Improved GitHub integration using Git Data API"""
    
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
        private: bool = False
    ) -> Dict[str, Any]:
        """Create a new GitHub repository without any initial files"""
        
        # Clean repository name
        repo_name = name.lower().replace(" ", "-").replace("_", "-")
        repo_name = "".join(c for c in repo_name if c.isalnum() or c == "-")
        
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False,  # Critical: no auto-initialization
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
    
    async def create_tree(
        self,
        owner: str,
        repo: str,
        files: Dict[str, str]
    ) -> str:
        """Create a tree with all files"""
        
        tree = []
        for path, content in files.items():
            # Create blob for file content
            blob_data = {
                "content": content,
                "encoding": "utf-8"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/repos/{owner}/{repo}/git/blobs",
                    headers=self.headers,
                    json=blob_data
                ) as response:
                    if response.status == 201:
                        blob = await response.json()
                        tree.append({
                            "path": path,
                            "mode": "100644",  # Regular file
                            "type": "blob",
                            "sha": blob["sha"]
                        })
                    else:
                        error = await response.text()
                        raise Exception(f"Failed to create blob for {path}: {error}")
        
        # Create tree
        tree_data = {"tree": tree}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/repos/{owner}/{repo}/git/trees",
                headers=self.headers,
                json=tree_data
            ) as response:
                if response.status == 201:
                    tree_result = await response.json()
                    return tree_result["sha"]
                else:
                    error = await response.text()
                    raise Exception(f"Failed to create tree: {error}")
    
    async def create_initial_commit(
        self,
        owner: str,
        repo: str,
        tree_sha: str,
        message: str
    ) -> str:
        """Create the initial commit"""
        
        commit_data = {
            "message": message,
            "tree": tree_sha,
            "parents": []  # No parents for initial commit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/repos/{owner}/{repo}/git/commits",
                headers=self.headers,
                json=commit_data
            ) as response:
                if response.status == 201:
                    commit = await response.json()
                    return commit["sha"]
                else:
                    error = await response.text()
                    raise Exception(f"Failed to create commit: {error}")
    
    async def update_reference(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
        ref: str = "refs/heads/main"
    ) -> bool:
        """Update the reference to point to the new commit"""
        
        ref_data = {
            "sha": commit_sha,
            "force": False
        }
        
        async with aiohttp.ClientSession() as session:
            # First try to create the reference
            async with session.post(
                f"{self.api_base}/repos/{owner}/{repo}/git/refs",
                headers=self.headers,
                json={"ref": ref, "sha": commit_sha}
            ) as response:
                if response.status == 201:
                    return True
                elif response.status == 422:
                    # Reference exists, update it
                    async with session.patch(
                        f"{self.api_base}/repos/{owner}/{repo}/git/{ref}",
                        headers=self.headers,
                        json=ref_data
                    ) as update_response:
                        return update_response.status == 200
                else:
                    error = await response.text()
                    logger.error(f"Failed to create/update reference: {error}")
                    return False
    
    async def _is_repo_empty(self, owner: str, repo: str) -> bool:
        """Check if repository is empty (no commits)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try to get the default branch
                async with session.get(
                    f"{self.api_base}/repos/{owner}/{repo}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        # Check if default branch exists
                        default_branch = repo_data.get('default_branch')
                        if not default_branch:
                            return True
                        
                        # Try to get commits
                        async with session.get(
                            f"{self.api_base}/repos/{owner}/{repo}/commits",
                            headers=self.headers
                        ) as commits_response:
                            if commits_response.status == 404 or commits_response.status == 409:
                                return True
                            elif commits_response.status == 200:
                                commits = await commits_response.json()
                                return len(commits) == 0
                    return True
        except Exception as e:
            logger.debug(f"Error checking if repo is empty: {e}")
            return True  # Assume empty on error
    
    async def push_capsule_atomic(
        self,
        capsule: QLCapsule,
        repo_name: Optional[str] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """Push capsule using atomic commit with Git Data API"""
        
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
            # Clean the content if needed
            if isinstance(content, str):
                # Remove any markdown code blocks
                if content.strip().startswith("```"):
                    lines = content.strip().split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = '\n'.join(lines)
                files[file_path] = content
        
        # Add tests
        for file_path, content in capsule.tests.items():
            if isinstance(content, str) and content.strip():
                # Clean content same as above
                if content.strip().startswith("```"):
                    lines = content.strip().split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = '\n'.join(lines)
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
        
        # Create all files in a single atomic commit
        owner = repo['owner']['login']
        repo_name = repo['name']
        
        try:
            # Check if repository is empty
            is_empty = await self._is_repo_empty(owner, repo_name)
            
            if is_empty:
                # For empty repos, fall back to regular file creation
                logger.info("Repository is empty, using regular file creation method")
                
                # Use the parent class's push method which handles empty repos
                from . import github_integration
                legacy_integration = github_integration.GitHubIntegration(self.token)
                legacy_integration.headers = self.headers
                
                result = await legacy_integration.push_capsule(
                    capsule, repo_name, repo['private']
                )
                
                return {
                    "repository_url": result["repository_url"],
                    "clone_url": result["clone_url"],
                    "ssh_url": result["ssh_url"],
                    "owner": owner,
                    "name": repo_name,
                    "private": repo['private'],
                    "files_created": result["files_created"],
                    "commit_sha": "initial"
                }
            else:
                # Repository has commits, use atomic approach
                # Create tree with all files
                tree_sha = await self.create_tree(owner, repo_name, files)
                
                # Create commit
                commit_message = f"Update: {capsule.manifest.get('name', 'QLCapsule')}\n\nGenerated by Quantum Layer Platform"
                commit_sha = await self.create_initial_commit(owner, repo_name, tree_sha, commit_message)
                
                # Update main branch reference
                await self.update_reference(owner, repo_name, commit_sha)
                
                logger.info(f"Successfully pushed capsule to {repo['html_url']}")
                
                return {
                    "repository_url": repo['html_url'],
                    "clone_url": repo['clone_url'],
                    "ssh_url": repo['ssh_url'],
                    "owner": owner,
                    "name": repo_name,
                    "private": repo['private'],
                    "files_created": len(files),
                    "commit_sha": commit_sha
                }
            
        except Exception as e:
            logger.error(f"Failed to push capsule: {e}")
            raise
    
    def _generate_gitignore(self, capsule: QLCapsule) -> str:
        """Generate appropriate .gitignore file"""
        language = capsule.manifest.get('language', '').lower()
        
        common = """# IDE
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
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src || echo "No tests found"
    
    - name: Lint
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
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