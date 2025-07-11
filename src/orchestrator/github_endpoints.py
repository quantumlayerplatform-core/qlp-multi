#!/usr/bin/env python3
"""
GitHub API endpoints for pushing capsules to repositories
"""

import os
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.orchestrator.github_integration import GitHubService


router = APIRouter(prefix="/api/github", tags=["github"])


class GitHubPushRequest(BaseModel):
    """Request to push capsule to GitHub"""
    capsule_id: str = Field(..., description="ID of the capsule to push")
    github_token: Optional[str] = Field(None, description="GitHub personal access token")
    repo_name: Optional[str] = Field(None, description="Custom repository name")
    private: bool = Field(False, description="Create private repository")


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
async def push_capsule_to_github(
    request: GitHubPushRequest,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    """Push a capsule to a new GitHub repository"""
    
    service = GitHubService(db)
    
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
        
        # Push to GitHub
        result = await service.push_capsule_to_github(
            capsule_id=request.capsule_id,
            token=token,
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
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
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