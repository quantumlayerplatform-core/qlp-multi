#!/usr/bin/env python3
"""
Start Temporal worker for QLP
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.orchestrator.worker import start_worker

if __name__ == "__main__":
    print("Starting Temporal worker...")
    asyncio.run(start_worker())