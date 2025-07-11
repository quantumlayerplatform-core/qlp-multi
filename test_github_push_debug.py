#!/usr/bin/env python3
"""
Debug GitHub push issue - analyze capsule contents
"""

import requests
import json

def debug_capsule_push():
    capsule_id = "2b2ced40-9b02-48d0-a7f3-eb8b65f6c5c7"
    
    # Get capsule details
    response = requests.get(f"http://localhost:8000/capsules/{capsule_id}")
    
    if response.status_code != 200:
        print(f"❌ Failed to get capsule: {response.status_code}")
        print(response.text)
        return
        
    capsule = response.json()
    
    print(f"✅ Retrieved capsule {capsule_id}")
    print("\n📁 Source Code Files:")
    
    source_code = capsule.get("source_code", {})
    if source_code:
        for file_path, content in source_code.items():
            if isinstance(content, str):
                print(f"  - {file_path}: {len(content)} chars")
                # Check if content looks like it's wrapped
                if content.strip().startswith("{'content':"):
                    print(f"    ⚠️ Content appears to be wrapped in dict string!")
            else:
                print(f"  - {file_path}: DICT type (unexpected)")
    else:
        print("  ❌ No source code files found!")
        
    print("\n🧪 Test Files:")
    tests = capsule.get("tests", {})
    if tests:
        for file_path, content in tests.items():
            if isinstance(content, str):
                print(f"  - {file_path}: {len(content)} chars")
                if content.strip().startswith("{'content':"):
                    print(f"    ⚠️ Content appears to be wrapped in dict string!")
            else:
                print(f"  - {file_path}: DICT type (unexpected)")
    else:
        print("  ❌ No test files found!")
        
    # List all expected files that should be in GitHub
    print("\n📤 Files that should be pushed to GitHub:")
    expected_files = []
    
    # Add all source and test files
    expected_files.extend(source_code.keys())
    expected_files.extend(tests.keys())
    
    # Add metadata files
    if capsule.get("documentation"):
        expected_files.append("README.md")
    expected_files.extend([
        "qlp-manifest.json",
        "qlp-metadata.json",
        ".gitignore"
    ])
    
    if capsule.get("deployment_config"):
        expected_files.append("qlp-deployment.json")
        
    if capsule.get("validation_report"):
        expected_files.append("qlp-validation.json")
        
    print(f"  Total: {len(expected_files)} files")
    for f in sorted(expected_files):
        print(f"  - {f}")
        
    # Check actual GitHub repo
    print("\n🔍 Checking actual GitHub repository...")
    github_url = capsule.get("metadata", {}).get("github_url")
    if github_url:
        # Extract owner and repo from URL
        parts = github_url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
            
            gh_response = requests.get(api_url)
            if gh_response.status_code == 200:
                files = gh_response.json()
                print(f"  Found {len(files)} files in GitHub:")
                for f in files:
                    print(f"  - {f['name']}")
            else:
                print(f"  ❌ Failed to check GitHub: {gh_response.status_code}")
    
    print("\n🔧 Analyzing the issue...")
    print("The problem appears to be that the capsule has 6 files (2 source + 4 tests)")
    print("but only some are being pushed to GitHub.")
    print("\nPossible causes:")
    print("1. Content extraction issue - files might be wrapped in dict strings")
    print("2. GitHub API errors for certain files")
    print("3. File content validation failing silently")

if __name__ == "__main__":
    debug_capsule_push()