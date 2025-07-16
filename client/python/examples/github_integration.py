#!/usr/bin/env python3
"""
GitHub integration example for QLP Python Client
"""

from qlp_client import QLPClientSync
import os


def main():
    # Initialize client
    api_key = os.getenv("QLP_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not api_key or not github_token:
        print("Please set QLP_API_KEY and GITHUB_TOKEN environment variables")
        return
    
    base_url = os.getenv("QLP_API_URL", "http://localhost:8000")
    client = QLPClientSync(api_key=api_key, base_url=base_url)
    
    print("QLP Python Client - GitHub Integration Example")
    print("=" * 50)
    
    # Generate and push to GitHub
    print("\nGenerating code and pushing to GitHub...")
    
    try:
        result = client.generate_with_github(
            description="""
            Create a Python package for data validation with:
            - Email validation
            - Phone number validation
            - Credit card validation
            - Date format validation
            - Comprehensive unit tests
            - README with examples
            """,
            github_token=github_token,
            repo_name="python-validators",
            private=False  # Create public repository
        )
        
        print(f"✓ Success!")
        print(f"  Capsule ID: {result.capsule_id}")
        print(f"  Files generated: {len(result.source_code)}")
        
        # GitHub information is in metadata
        if "github_url" in result.metadata:
            print(f"  GitHub Repository: {result.metadata['github_url']}")
            print(f"  Clone with: git clone {result.metadata['github_url']}.git")
        
        # Show generated files
        print("\n  Generated files:")
        for filename in sorted(result.source_code.keys()):
            print(f"    - {filename}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        
    # Example with more options
    print("\n\nGenerating enterprise application with GitHub...")
    
    try:
        result = client.generate_and_wait(
            description="Create a microservices-based inventory management system",
            mode="robust",  # Production-grade
            github={
                "enabled": True,
                "token": github_token,
                "repo_name": "inventory-microservices",
                "private": True,  # Private repository
                "create_pr": False,  # Direct push to main
                "enterprise_structure": True  # Use enterprise folder structure
            },
            constraints={
                "language": "python",
                "framework": "fastapi",
                "database": "postgresql",
                "containerized": True
            }
        )
        
        print(f"✓ Enterprise application generated!")
        print(f"  Repository: {result.metadata.get('github_url', 'Check GitHub')}")
        print(f"  Architecture: Microservices")
        print(f"  Features: {', '.join(result.metadata.get('features', []))}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    client.close()
    print("\n\nDone! Check your GitHub account for the new repositories.")


if __name__ == "__main__":
    main()