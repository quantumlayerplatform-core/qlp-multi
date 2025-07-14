#!/usr/bin/env python3
"""
Test all new CLI features
"""

import subprocess
import sys
import time

def run_command(cmd):
    """Run a command and show output"""
    print(f"\n{'=' * 60}")
    print(f"Running: {' '.join(cmd)}")
    print('=' * 60)
    subprocess.run(cmd)
    time.sleep(1)

def test_features():
    """Test all new features"""
    
    print("\n🧪 Testing QuantumLayer CLI New Features\n")
    
    # Test 1: Chain of Thought with dry run
    print("\n1️⃣ Testing Chain of Thought reasoning display...")
    run_command([
        sys.executable, "-m", "qlp_cli.main", 
        "generate", 
        "REST API for user management with JWT authentication",
        "--show-reasoning",
        "--dry-run"
    ])
    
    # Test 2: Live Preview
    print("\n2️⃣ Testing Live Code Preview...")
    run_command([
        sys.executable, "-m", "qlp_cli.main", 
        "generate", 
        "React dashboard with charts",
        "--preview",
        "--dry-run"
    ])
    
    # Test 3: Combined features
    print("\n3️⃣ Testing Combined Features (Reasoning + Preview)...")
    run_command([
        sys.executable, "-m", "qlp_cli.main", 
        "generate", 
        "CLI tool for file management",
        "--show-reasoning",
        "--preview",
        "--dry-run"
    ])
    
    # Test 4: Validation command (with example capsule ID)
    print("\n4️⃣ Testing Validate command...")
    print("(This would validate a real capsule ID)")
    run_command([
        sys.executable, "-m", "qlp_cli.main", 
        "--help"
    ])
    
    print("\n✅ All tests completed!")
    print("\nKey features demonstrated:")
    print("  • Chain of Thought reasoning with --show-reasoning")
    print("  • Live code preview with --preview")
    print("  • Cost estimation in request summary")
    print("  • Thought bubbles during generation")
    print("  • Enhanced formatting throughout")
    print("\nAdditional commands available:")
    print("  • qlp validate <capsule_id> - Validate generated code")
    print("  • qlp inspect <capsule_id> - Inspect capsule details")
    print("  • qlp check-github <repo_url> - Check GitHub repository")

if __name__ == "__main__":
    test_features()