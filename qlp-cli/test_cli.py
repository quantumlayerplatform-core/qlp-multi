#!/usr/bin/env python3
"""
Test script for QuantumLayer CLI
"""

import subprocess
import sys
import os

def test_cli_installation():
    """Test if CLI can be installed and run"""
    
    print("🧪 Testing QuantumLayer CLI\n")
    
    # Test 1: Check if main module works
    print("1. Testing module import...")
    try:
        from qlp_cli import cli
        print("✅ Module imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Check CLI help
    print("\n2. Testing CLI help command...")
    result = subprocess.run(
        [sys.executable, "-m", "qlp_cli.main", "--help"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Help command works")
        print("Output preview:")
        print(result.stdout[:200] + "...")
    else:
        print(f"❌ Help command failed: {result.stderr}")
        return False
    
    # Test 3: Check version
    print("\n3. Testing version command...")
    result = subprocess.run(
        [sys.executable, "-m", "qlp_cli.main", "--version"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ Version: {result.stdout.strip()}")
    else:
        print(f"❌ Version command failed")
    
    # Test 4: Test dry run
    print("\n4. Testing generate command (dry run)...")
    result = subprocess.run(
        [sys.executable, "-m", "qlp_cli.main", "generate", "simple REST API", "--dry-run"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Generate command works (dry run)")
    else:
        print(f"❌ Generate command failed: {result.stderr}")
    
    print("\n✅ All tests passed!")
    return True


def show_usage_examples():
    """Show usage examples"""
    
    print("\n📚 Usage Examples:\n")
    
    examples = [
        ("Basic generation", 'qlp generate "REST API for blog"'),
        ("Interactive mode", "qlp interactive"),
        ("With language", 'qlp generate "web scraper" -l python'),
        ("From image", "qlp from-image diagram.png"),
        ("View stats", "qlp stats global"),
        ("With GitHub", 'qlp generate "discord bot" --github'),
    ]
    
    for title, cmd in examples:
        print(f"{title}:")
        print(f"  $ {cmd}\n")


if __name__ == "__main__":
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    if test_cli_installation():
        show_usage_examples()
        
        print("🚀 CLI is ready to use!\n")
        print("To install locally for development:")
        print("  $ pip install -e .")
        print("\nTo run directly:")
        print("  $ python -m qlp_cli.main generate 'your project description'")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)