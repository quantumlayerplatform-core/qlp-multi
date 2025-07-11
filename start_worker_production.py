#!/usr/bin/env python3
"""
Start Production Temporal Worker with Database Persistence
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the production worker
from src.orchestrator.worker_production_db import main

if __name__ == "__main__":
    main()