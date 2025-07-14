#!/usr/bin/env python3
"""
Test the progress tracking fix for the CLI
"""

import subprocess
import sys
import time

def test_progress():
    """Test that progress updates properly during generation"""
    
    print("Testing QuantumLayer CLI progress tracking...")
    print("-" * 50)
    
    # Run a simple generation command
    cmd = [
        sys.executable, "run_cli.py", 
        "generate", 
        "Simple hello world program in Python",
        "--timeout", "10"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("\nWatch the progress bar - it should update beyond 10%")
    print("-" * 50)
    
    try:
        # Run the command
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ Command completed successfully!")
        else:
            print(f"\n❌ Command failed with return code: {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running test: {e}")

if __name__ == "__main__":
    test_progress()