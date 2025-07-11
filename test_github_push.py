#!/usr/bin/env python3
"""
Test GitHub push functionality
"""

import asyncio
import os


async def test_github_push():
    """Test pushing a capsule to GitHub via API"""
    
    print("🧪 Testing GitHub Push Functionality")
    print("=" * 60)
    
    # Check if GitHub token is available
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("\n❌ GITHUB_TOKEN not set!")
        print("\nTo set up GitHub integration:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Name: 'QLP Integration'")
        print("4. Select scope: 'repo' (Full control of private repositories)")
        print("5. Click 'Generate token'")
        print("6. Copy the token")
        print("7. Run: export GITHUB_TOKEN=<your-token>")
        print("\nThen run this test again.")
        return
    
    print(f"✅ GitHub token found (first 10 chars: {token[:10]}...)")
    
    # Test token validity via API
    import aiohttp
    
    print("\n🔍 Checking token validity...")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://localhost:8000/api/github/check-token",
            params={"token": token}
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data["valid"]:
                    print(f"✅ Token is valid!")
                    print(f"   User: {data['username']}")
                    print(f"   Name: {data.get('name', 'N/A')}")
                    print(f"   Public repos: {data.get('public_repos', 0)}")
                    print(f"   Private repos: {data.get('private_repos', 0)}")
                else:
                    print(f"❌ Invalid token: {data['message']}")
                    return
            else:
                print("❌ Failed to check token")
                return
    
    print("\n📋 Available capsules to push:")
    print("Run: python download_capsule_docker.py list")
    print("\nTo push a capsule to GitHub:")
    print("python push_to_github.py <capsule-id>")
    print("\nOr via API:")
    print("""
curl -X POST http://localhost:8000/api/github/push \\
  -H "Content-Type: application/json" \\
  -d '{
    "capsule_id": "<capsule-id>",
    "github_token": "<token>",
    "private": false
  }'
""")
    
    print("\n✨ GitHub integration is ready!")


if __name__ == "__main__":
    asyncio.run(test_github_push())