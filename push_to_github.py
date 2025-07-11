#!/usr/bin/env python3
"""
Push QLCapsule to GitHub
Creates a new repository and pushes all capsule contents
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.append('.')

from src.orchestrator.github_integration import GitHubIntegration
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.common.models import QLCapsule
from src.common.database import get_db


async def push_capsule_to_github(
    capsule_id: str,
    token: Optional[str] = None,
    repo_name: Optional[str] = None,
    private: bool = False
):
    """Push a capsule to GitHub"""
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get capsule from database
        storage = CapsuleStorageService(db)
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            print(f"❌ Capsule {capsule_id} not found")
            return
        
        capsule = QLCapsule(**capsule_data)
        
        # Get GitHub token
        github_token = token or os.getenv("GITHUB_TOKEN")
        if not github_token:
            print("❌ GitHub token required!")
            print("   Set GITHUB_TOKEN environment variable or use --token flag")
            print("\nTo create a GitHub token:")
            print("1. Go to https://github.com/settings/tokens")
            print("2. Click 'Generate new token (classic)'")
            print("3. Select 'repo' scope")
            print("4. Copy the token and set: export GITHUB_TOKEN=your_token")
            return
        
        # Initialize GitHub integration
        github = GitHubIntegration(github_token)
        
        print(f"\n🚀 Pushing capsule to GitHub...")
        print(f"   Capsule ID: {capsule_id}")
        print(f"   Name: {capsule.manifest.get('name', 'Unnamed')}")
        print(f"   Private: {'Yes' if private else 'No'}")
        
        # Push to GitHub
        result = await github.push_capsule(capsule, repo_name, private)
        
        print(f"\n✅ Successfully pushed to GitHub!")
        print(f"   Repository: {result['repository_url']}")
        print(f"   Clone URL: {result['clone_url']}")
        print(f"   Files created: {result['files_created']}")
        
        print("\n📋 Next steps:")
        print(f"   1. Clone: git clone {result['clone_url']}")
        print(f"   2. Navigate: cd {result['name']}")
        print(f"   3. Install: pip install -r requirements.txt")
        print(f"   4. Run tests: pytest")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None
    finally:
        db.close()


async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Push QLCapsule to GitHub")
    parser.add_argument("capsule_id", help="ID of the capsule to push")
    parser.add_argument("--token", "-t", help="GitHub personal access token")
    parser.add_argument("--name", "-n", help="Custom repository name")
    parser.add_argument("--private", "-p", action="store_true", help="Create private repository")
    
    args = parser.parse_args()
    
    await push_capsule_to_github(
        args.capsule_id,
        args.token,
        args.name,
        args.private
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())