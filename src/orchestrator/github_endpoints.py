
#!/usr/bin/env python3
"""
GitHub API endpoints for pushing capsules to repositories
"""

import os
import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import structlog

from src.common.database import get_db
from src.common.auth import get_current_user
from src.orchestrator.github_integration import GitHubService
from src.orchestrator.github_integration_v2 import GitHubIntegrationV2
from src.orchestrator.enhanced_github_integration import EnhancedGitHubIntegration

logger = structlog.get_logger()


router = APIRouter(prefix="/api/github", tags=["github"])


class GitHubPushRequest(BaseModel):
    """Request to push capsule to GitHub"""
    capsule_id: str = Field(..., description="ID of the capsule to push")
    github_token: Optional[str] = Field(None, description="GitHub personal access token")
    repo_name: Optional[str] = Field(None, description="Custom repository name")
    private: bool = Field(False, description="Create private repository")


class EnhancedGitHubPushRequest(GitHubPushRequest):
    """Enhanced request model with structure options"""
    use_enterprise_structure: bool = Field(True, description="Use AI to create enterprise-grade structure")


class GitHubPushResponse(BaseModel):
    """Response after pushing to GitHub"""
    success: bool
    repository_url: str
    clone_url: str
    ssh_url: str
    owner: str
    repo_name: str
    files_created: int
    message: str


@router.post("/push", response_model=GitHubPushResponse)
async def push_capsule_to_github_legacy(
    request: GitHubPushRequest,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Push a capsule to a new GitHub repository (legacy method)"""
    
    service = GitHubService(db)
    
    try:
        result = await service.push_capsule_to_github(
            capsule_id=request.capsule_id,
            token=request.github_token,
            repo_name=request.repo_name,
            private=request.private
        )
        
        return GitHubPushResponse(
            success=True,
            repository_url=result["repository_url"],
            clone_url=result["clone_url"],
            ssh_url=result["ssh_url"],
            owner=result["owner"],
            repo_name=result["name"],
            files_created=result["files_created"],
            message=f"Successfully pushed capsule to GitHub: {result['repository_url']}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push/v2", response_model=GitHubPushResponse)
async def push_capsule_to_github(
    request: GitHubPushRequest,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Push a capsule to GitHub using atomic commit (v2 - improved method)"""
    
    from src.orchestrator.capsule_storage import CapsuleStorageService
    
    try:
        # Use provided token or get from environment
        token = request.github_token
        if not token:
            import os
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise HTTPException(
                    status_code=400,
                    detail="GitHub token required. Provide in request or set GITHUB_TOKEN environment variable"
                )
        
        # Get capsule from storage
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(request.capsule_id)
        
        if not capsule:
            raise HTTPException(status_code=404, detail=f"Capsule {request.capsule_id} not found")
        
        # Initialize GitHub v2 client
        github = GitHubIntegrationV2(token)
        
        # Push using atomic commit
        result = await github.push_capsule_atomic(
            capsule=capsule,
            repo_name=request.repo_name,
            private=request.private
        )
        
        # Update capsule metadata with GitHub info
        capsule.metadata["github_url"] = result["repository_url"]
        capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
        await storage.update_capsule_metadata(request.capsule_id, capsule.metadata)
        
        return GitHubPushResponse(
            success=True,
            repository_url=result["repository_url"],
            clone_url=result["clone_url"],
            ssh_url=result["ssh_url"],
            owner=result["owner"],
            repo_name=result["name"],
            files_created=result["files_created"],
            message=f"Successfully pushed capsule to GitHub: {result['repository_url']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to push to GitHub: {str(e)}")


@router.post("/push/enterprise", response_model=GitHubPushResponse)
async def push_capsule_enterprise(
    request: EnhancedGitHubPushRequest,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Push a capsule to GitHub with AI-powered enterprise structure
    
    This endpoint:
    1. Uses LLM to analyze the capsule code
    2. Determines optimal folder structure based on project type
    3. Organizes files intelligently (src/, tests/, docs/, etc.)
    4. Adds comprehensive configuration files
    5. Creates proper CI/CD workflows
    """
    
    from src.orchestrator.capsule_storage import CapsuleStorageService
    
    try:
        # Get token
        token = request.github_token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise HTTPException(
                status_code=400,
                detail="GitHub token required. Provide in request or set GITHUB_TOKEN environment variable"
            )
        
        # Get capsule
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(request.capsule_id)
        
        if not capsule:
            raise HTTPException(status_code=404, detail=f"Capsule {request.capsule_id} not found")
        
        # Log the transformation
        logger.info(
            "Starting enterprise GitHub push",
            capsule_id=request.capsule_id,
            files_count=len(capsule.source_code),
            language=capsule.manifest.get('language', 'unknown')
        )
        
        # Initialize enhanced GitHub client
        github = EnhancedGitHubIntegration(token)
        
        # Push with intelligent structure
        result = await github.push_capsule_atomic(
            capsule=capsule,
            repo_name=request.repo_name,
            private=request.private,
            use_intelligent_structure=request.use_enterprise_structure
        )
        
        # Update capsule metadata
        capsule.metadata["github_url"] = result["repository_url"]
        capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
        capsule.metadata["github_structure"] = "enterprise" if request.use_enterprise_structure else "flat"
        await storage.update_capsule_metadata(request.capsule_id, capsule.metadata)
        
        return GitHubPushResponse(
            success=True,
            repository_url=result["repository_url"],
            clone_url=result["clone_url"],
            ssh_url=result["ssh_url"],
            owner=result["owner"],
            repo_name=result["name"],
            files_created=result["files_created"],
            message=f"Successfully created enterprise-grade repository: {result['repository_url']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to push to GitHub: {str(e)}")


@router.post("/push/atomic", response_model=GitHubPushResponse)
async def push_capsule_atomic(
    request: GitHubPushRequest,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Push a capsule to GitHub using Git Data API for atomic commits"""
    
    from src.orchestrator.capsule_storage import CapsuleStorageService
    import aiohttp
    import base64
    
    try:
        # Use provided token or get from environment
        token = request.github_token
        if not token:
            import os
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise HTTPException(
                    status_code=400,
                    detail="GitHub token required. Provide in request or set GITHUB_TOKEN environment variable"
                )
        
        # Get capsule from storage
        storage = CapsuleStorageService(db)
        capsule = await storage.get_capsule(request.capsule_id)
        
        if not capsule:
            raise HTTPException(status_code=404, detail=f"Capsule {request.capsule_id} not found")
        
        # Clean repository name
        repo_name = request.repo_name or f"qlp-capsule-{capsule.id[:8]}"
        repo_name = repo_name.lower().replace(" ", "-").replace("_", "-")
        repo_name = "".join(c for c in repo_name if c.isalnum() or c == "-")
        
        # GitHub API headers
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Create repository without auto-init
        async with aiohttp.ClientSession() as session:
            # Get user info
            async with session.get("https://api.github.com/user", headers=headers) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=401, detail="Invalid GitHub token")
                user_info = await resp.json()
                owner = user_info["login"]
            
            # Create repository
            repo_data = {
                "name": repo_name,
                "description": capsule.manifest.get("description", "Generated by Quantum Layer Platform"),
                "private": request.private,
                "auto_init": False
            }
            
            async with session.post("https://api.github.com/user/repos", headers=headers, json=repo_data) as resp:
                if resp.status == 201:
                    repo = await resp.json()
                elif resp.status == 422:
                    # Repository exists, get it
                    async with session.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers) as repo_resp:
                        if repo_resp.status == 200:
                            repo = await repo_resp.json()
                        else:
                            raise HTTPException(status_code=422, detail="Repository name already exists")
                else:
                    error = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Failed to create repository: {error}")
            
            # Prepare all files
            files = {}
            
            # Add source code
            for file_path, content in capsule.source_code.items():
                # Clean content
                if isinstance(content, dict) and "content" in content:
                    content = content["content"]
                if isinstance(content, str) and content.strip().startswith("```"):
                    lines = content.strip().split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = '\n'.join(lines)
                files[file_path] = content
            
            # Add tests
            for file_path, content in capsule.tests.items():
                if isinstance(content, dict) and "content" in content:
                    content = content["content"]
                if isinstance(content, str) and content.strip().startswith("```"):
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
            
            # Add manifest and metadata
            files["qlp-manifest.json"] = json.dumps(capsule.manifest, indent=2)
            files["qlp-metadata.json"] = json.dumps(capsule.metadata, indent=2)
            
            if capsule.deployment_config:
                files["qlp-deployment.json"] = json.dumps(capsule.deployment_config, indent=2)
            
            if capsule.validation_report:
                files["qlp-validation.json"] = json.dumps(capsule.validation_report.model_dump(), indent=2)
            
            # Create tree with all files
            tree = []
            for path, content in files.items():
                # Create blob
                blob_data = {"content": content, "encoding": "utf-8"}
                async with session.post(f"https://api.github.com/repos/{owner}/{repo_name}/git/blobs", 
                                       headers=headers, json=blob_data) as blob_resp:
                    if blob_resp.status == 201:
                        blob = await blob_resp.json()
                        tree.append({
                            "path": path,
                            "mode": "100644",
                            "type": "blob",
                            "sha": blob["sha"]
                        })
                    else:
                        error = await blob_resp.text()
                        logger.error(f"Failed to create blob for {path}: {error}")
            
            # Create tree
            tree_data = {"tree": tree}
            async with session.post(f"https://api.github.com/repos/{owner}/{repo_name}/git/trees", 
                                   headers=headers, json=tree_data) as tree_resp:
                if tree_resp.status == 201:
                    tree_result = await tree_resp.json()
                    tree_sha = tree_result["sha"]
                else:
                    error = await tree_resp.text()
                    raise HTTPException(status_code=500, detail=f"Failed to create tree: {error}")
            
            # Create commit
            commit_data = {
                "message": f"Initial commit: {capsule.manifest.get('name', 'QLCapsule')}\n\nGenerated by Quantum Layer Platform",
                "tree": tree_sha,
                "parents": []
            }
            
            async with session.post(f"https://api.github.com/repos/{owner}/{repo_name}/git/commits", 
                                   headers=headers, json=commit_data) as commit_resp:
                if commit_resp.status == 201:
                    commit = await commit_resp.json()
                    commit_sha = commit["sha"]
                else:
                    error = await commit_resp.text()
                    raise HTTPException(status_code=500, detail=f"Failed to create commit: {error}")
            
            # Update reference
            ref_data = {"sha": commit_sha, "force": False}
            
            # Try to create reference first
            async with session.post(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs", 
                                   headers=headers, json={"ref": "refs/heads/main", "sha": commit_sha}) as ref_resp:
                if ref_resp.status != 201:
                    # Reference exists, update it
                    async with session.patch(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs/heads/main", 
                                           headers=headers, json=ref_data) as update_resp:
                        if update_resp.status != 200:
                            error = await update_resp.text()
                            logger.error(f"Failed to update reference: {error}")
        
        # Update capsule metadata
        capsule.metadata["github_url"] = repo["html_url"]
        capsule.metadata["github_pushed_at"] = datetime.utcnow().isoformat()
        await storage.update_capsule_metadata(request.capsule_id, capsule.metadata)
        
        return GitHubPushResponse(
            success=True,
            repository_url=repo["html_url"],
            clone_url=repo["clone_url"],
            ssh_url=repo["ssh_url"],
            owner=owner,
            repo_name=repo_name,
            files_created=len(files),
            message=f"Successfully pushed capsule to GitHub: {repo['html_url']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to push to GitHub: {str(e)}")


@router.get("/check-token")
async def check_github_token(
    token: Optional[str] = Query(None, description="GitHub token to check"),
    user=Depends(get_current_user)
):
    """Check if GitHub token is valid"""
    
    if not token:
        import os
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return {
                "valid": False,
                "message": "No GitHub token provided or found in environment"
            }
    
    try:
        from src.orchestrator.github_integration import GitHubIntegration
        github = GitHubIntegration(token)
        user_info = await github.get_authenticated_user()
        
        return {
            "valid": True,
            "username": user_info["login"],
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "public_repos": user_info.get("public_repos"),
            "private_repos": user_info.get("private_repos"),
            "message": f"Token is valid for user: {user_info['login']}"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Invalid token: {str(e)}"
        }


@router.post("/push-and-deploy")
async def push_and_deploy_capsule(
    request: GitHubPushRequest,
    deploy_to: str = Query("github-pages", description="Deployment target: github-pages, vercel, netlify"),
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Push capsule to GitHub and set up deployment"""
    
    # First push to GitHub
    service = GitHubService(db)
    
    try:
        token = request.github_token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub token required")
        
        # Push to GitHub
        result = await service.push_capsule_to_github(
            capsule_id=request.capsule_id,
            token=token,
            repo_name=request.repo_name,
            private=request.private
        )
        
        # Set up deployment based on target
        deployment_info = {}
        
        if deploy_to == "github-pages" and not request.private:
            # Enable GitHub Pages
            from src.orchestrator.github_integration import GitHubIntegration
            github = GitHubIntegration(token)
            
            # Add GitHub Pages workflow
            pages_workflow = """name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Pages
        uses: actions/configure-pages@v3
        
      - name: Build
        run: |
          # Add build steps here
          echo "Building..."
          
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v2
        with:
          path: './dist'
          
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v2
"""
            
            await github.create_file(
                result["owner"],
                result["name"],
                ".github/workflows/pages.yml",
                pages_workflow,
                "Add GitHub Pages deployment"
            )
            
            deployment_info = {
                "type": "github-pages",
                "url": f"https://{result['owner']}.github.io/{result['name']}/"
            }
        
        elif deploy_to == "vercel":
            # Add Vercel configuration
            vercel_config = {
                "version": 2,
                "builds": [
                    {
                        "src": "package.json",
                        "use": "@vercel/node"
                    }
                ],
                "routes": [
                    {
                        "src": "/(.*)",
                        "dest": "/"
                    }
                ]
            }
            
            github = GitHubIntegration(token)
            await github.create_file(
                result["owner"],
                result["name"],
                "vercel.json",
                json.dumps(vercel_config, indent=2),
                "Add Vercel configuration"
            )
            
            deployment_info = {
                "type": "vercel",
                "instructions": "Connect this repository to Vercel at https://vercel.com/new"
            }
        
        return {
            "success": True,
            "github": result,
            "deployment": deployment_info,
            "message": f"Pushed to GitHub and configured for {deploy_to} deployment"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))