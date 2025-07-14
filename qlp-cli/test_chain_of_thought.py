#!/usr/bin/env python3
"""
Test the Chain of Thought reasoning display
"""

import subprocess
import sys

def test_chain_of_thought():
    """Test chain of thought with dry run"""
    
    print("Testing Chain of Thought reasoning display...")
    print("=" * 60)
    
    # Test with API example
    subprocess.run([
        sys.executable, "-m", "qlp_cli.main", 
        "generate", 
        "REST API for task management with authentication",
        "--show-reasoning",
        "--dry-run"
    ])

if __name__ == "__main__":
    test_chain_of_thought()