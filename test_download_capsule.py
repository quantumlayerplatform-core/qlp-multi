#!/usr/bin/env python3
"""
Test the capsule download functionality
"""

import asyncio
import sys
sys.path.append('.')

from download_capsule import CapsuleDownloader


async def main():
    """Test capsule download features"""
    downloader = CapsuleDownloader()
    
    print("🧪 Testing Capsule Download Functionality")
    print("=" * 60)
    
    # List capsules
    print("\n1. Listing available capsules...")
    try:
        await downloader.list_capsules(limit=5)
    except Exception as e:
        print(f"❌ Error listing capsules: {str(e)}")
        print("   Make sure the database is running and contains capsules")
        return
    
    # Get a capsule ID for testing
    print("\n2. To download a capsule, run:")
    print("   python download_capsule.py download <capsule-id>")
    print("\n3. To inspect a capsule, run:")
    print("   python download_capsule.py inspect <capsule-id>")
    print("\n4. To extract a specific file, run:")
    print("   python download_capsule.py extract <capsule-id> main.py")
    
    print("\n📚 Full documentation available in docs/CAPSULE_DOWNLOAD_GUIDE.md")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())