#!/usr/bin/env python3
"""
Basic usage examples for QLP Python Client
"""

from qlp_client import QLPClientSync
import os
import json


def main():
    # Initialize client (use environment variable for API key)
    api_key = os.getenv("QLP_API_KEY")
    if not api_key:
        print("Please set QLP_API_KEY environment variable")
        return
    
    # For local testing, use localhost
    base_url = os.getenv("QLP_API_URL", "http://localhost:8000")
    
    client = QLPClientSync(api_key=api_key, base_url=base_url)
    
    print("QLP Python Client - Basic Examples")
    print("=" * 50)
    
    # Example 1: Simple function generation
    print("\n1. Generating a simple function...")
    try:
        result = client.generate_basic(
            "Create a Python function to calculate the factorial of a number"
        )
        
        print(f"✓ Generated successfully!")
        print(f"  Capsule ID: {result.capsule_id}")
        print(f"  Files generated: {len(result.source_code)}")
        
        # Show generated code
        for filename, code in result.source_code.items():
            print(f"\n  {filename}:")
            print("  " + "-" * 40)
            print("  " + code.replace("\n", "\n  "))
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 2: Complete API generation
    print("\n\n2. Generating a complete REST API...")
    try:
        result = client.generate_complete(
            "Create a REST API for a todo list application with CRUD operations",
            constraints={
                "language": "python",
                "framework": "fastapi"
            }
        )
        
        print(f"✓ Generated successfully!")
        print(f"  Capsule ID: {result.capsule_id}")
        print(f"  Files generated: {len(result.source_code)}")
        print(f"  Download links:")
        for format, url in result.downloads.items():
            print(f"    - {format}: {url}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 3: Check workflow status
    print("\n\n3. Monitoring workflow progress...")
    try:
        # Start a workflow
        workflow = client.generate(
            "Create a Python script for web scraping",
            mode="complete"
        )
        
        print(f"  Workflow started: {workflow.workflow_id}")
        
        # Check status periodically
        import time
        for i in range(5):
            status = client.get_status(workflow.workflow_id)
            print(f"  Status: {status.status} - {status.progress.get('message', '')}")
            
            if status.status in ["COMPLETED", "FAILED"]:
                break
                
            time.sleep(2)
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Clean up
    client.close()
    
    print("\n\nDone! See the generated code above.")


if __name__ == "__main__":
    main()