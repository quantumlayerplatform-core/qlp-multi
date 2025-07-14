#!/usr/bin/env python3
"""
Start Marketing Worker for Docker
Simple wrapper to ensure proper startup in Docker container
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app')

# Now import and run the marketing worker
from src.orchestrator.marketing_workflow import start_marketing_worker
import asyncio

if __name__ == "__main__":
    print("Starting Marketing Workflow Worker...")
    try:
        asyncio.run(start_marketing_worker())
    except Exception as e:
        print(f"Error starting marketing worker: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)