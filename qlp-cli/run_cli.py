#!/usr/bin/env python3
"""
Direct CLI runner for testing without installation
"""

import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the CLI
from qlp_cli.main import cli

if __name__ == "__main__":
    cli()