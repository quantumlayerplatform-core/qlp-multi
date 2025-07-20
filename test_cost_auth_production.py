#!/usr/bin/env python3
"""
Production-ready authentication testing for cost tracking endpoints
Uses Clerk for authentication
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, Optional

# For production Clerk integration
try:
    from clerk_backend_api import Clerk
    from clerk_backend_api.models import operations
    CLERK_SDK_AVAILABLE = True
except ImportError:
    CLERK_SDK_AVAILABLE = False
    print("⚠️  Clerk SDK not installed. Install with: pip install clerk-backend-api")

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

class ClerkAuthTester:
    """Production-ready Clerk authentication tester"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        if CLERK_SDK_AVAILABLE:
            self.clerk = Clerk(bearer_auth=secret_key)
        else:
            self.clerk = None
            
    def create_test_user(self) -> Optional[Dict]:
        """Create a test user in Clerk"""
        if not self.clerk:
            print("❌ Clerk SDK not available")
            return None
            
        try:
            # Create user
            request = operations.CreateUserRequestBody(
                email_address=["test@quantumlayerplatform.com"],
                first_name="Test",
                last_name="User",
                password="TestPassword123!",
                public_metadata={
                    "role": "developer",
                    "test_user": True
                }
            )
            
            response = self.clerk.users.create(request)
            if response.user:
                print(f"✅ Created test user: {response.user.id}")
                return {
                    "user_id": response.user.id,
                    "email": response.user.email_addresses[0].email_address
                }
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return None
    
    def create_session_token(self, user_id: str) -> Optional[str]:
        """Create a session token for the user"""
        if not self.clerk:
            return None
            
        try:
            # Create a session
            response = self.clerk.sessions.create(
                operations.CreateSessionRequestBody(
                    user_id=user_id,
                    expires_in_seconds=3600  # 1 hour
                )
            )
            
            if response.session:
                # Get the session token
                token_response = self.clerk.sessions.get_token(
                    session_id=response.session.id,
                    template="default"
                )
                
                if token_response.jwt:
                    print(f"✅ Created session token")
                    return token_response.jwt
                    
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return None
    
    def cleanup_test_user(self, user_id: str):
        """Clean up test user after testing"""
        if not self.clerk:
            return
            
        try:
            self.clerk.users.delete(user_id=user_id)
            print(f"✅ Cleaned up test user: {user_id}")
        except Exception as e:
            print(f"⚠️  Failed to cleanup user: {e}")


def test_with_real_clerk_auth():
    """Test cost endpoints with real Clerk authentication"""
    print("🔐 Production Authentication Test with Clerk")
    print("=" * 60)
    
    if not CLERK_SECRET_KEY:
        print("❌ CLERK_SECRET_KEY not set in environment")
        print("   Set it with: export CLERK_SECRET_KEY='your-secret-key'")
        return
    
    # Initialize Clerk
    auth_tester = ClerkAuthTester(CLERK_SECRET_KEY)
    
    # Create test user
    print("\n1️⃣ Creating test user in Clerk...")
    test_user = auth_tester.create_test_user()
    if not test_user:
        return
    
    try:
        # Create session token
        print("\n2️⃣ Creating session token...")
        token = auth_tester.create_session_token(test_user["user_id"])
        if not token:
            return
        
        # Test the endpoints
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n3️⃣ Testing Cost Estimation Endpoint...")
        estimate_response = requests.get(
            f"{BASE_URL}/api/v2/costs/estimate",
            params={
                "complexity": "medium",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
            },
            headers=headers
        )
        
        print(f"   Status: {estimate_response.status_code}")
        if estimate_response.status_code == 200:
            estimate = estimate_response.json()
            if estimate.get("success"):
                print("   ✅ Cost estimation successful!")
                estimates = estimate["data"]["model_estimates"]
                for model, info in estimates.items():
                    print(f"      {model}: ${info['estimated_cost_usd']:.4f}")
        
        print("\n4️⃣ Testing Cost Report Endpoint...")
        cost_response = requests.get(
            f"{BASE_URL}/api/v2/costs",
            params={"period_days": 7},
            headers=headers
        )
        
        print(f"   Status: {cost_response.status_code}")
        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            if cost_data.get("success"):
                print("   ✅ Cost report retrieved!")
                report = cost_data.get("data", {})
                print(f"      Total cost: ${report.get('total_cost_usd', 0):.6f}")
        
        print("\n5️⃣ Testing Metrics Endpoint...")
        metrics_response = requests.get(
            f"{BASE_URL}/api/v2/metrics",
            headers=headers
        )
        
        print(f"   Status: {metrics_response.status_code}")
        if metrics_response.status_code == 403:
            print("   ⚠️  User needs 'metrics:read' permission")
        elif metrics_response.status_code == 200:
            print("   ✅ Metrics retrieved!")
            
    finally:
        # Cleanup
        print("\n6️⃣ Cleaning up test user...")
        auth_tester.cleanup_test_user(test_user["user_id"])


def test_with_manual_token():
    """Test with a manually obtained Clerk token"""
    print("\n📝 Manual Token Testing")
    print("=" * 60)
    
    token = input("Paste your Clerk session token (or press Enter to skip): ").strip()
    if not token:
        print("Skipped manual token testing")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test cost endpoint
    print("\nTesting cost endpoint with your token...")
    response = requests.get(
        f"{BASE_URL}/api/v2/costs",
        params={"period_days": 1},
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Success! You're authenticated.")
        if data.get("data"):
            report = data["data"]
            print(f"Total requests: {report.get('total_requests', 0)}")
            print(f"Total cost: ${report.get('total_cost_usd', 0):.6f}")
    else:
        print(f"❌ Error: {response.text}")


def show_production_setup_guide():
    """Show how to set up Clerk in production"""
    print("\n📚 Production Setup Guide")
    print("=" * 60)
    print("""
1. CLERK DASHBOARD SETUP:
   - Go to https://dashboard.clerk.com
   - Create an application
   - Get your SECRET KEY from API Keys section
   - Configure allowed callback URLs

2. ENVIRONMENT SETUP:
   export CLERK_SECRET_KEY="sk_test_..."
   export CLERK_PUBLISHABLE_KEY="pk_test_..."
   export CLERK_JWKS_URL="https://your-app.clerk.accounts.dev/.well-known/jwks.json"

3. INSTALL CLERK SDK:
   pip install clerk-backend-api

4. FRONTEND INTEGRATION (React):
   npm install @clerk/clerk-react

   // App.jsx
   import { ClerkProvider } from '@clerk/clerk-react';
   
   <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
     <App />
   </ClerkProvider>

   // Component using auth
   import { useAuth } from '@clerk/clerk-react';
   
   function CostDashboard() {
     const { getToken } = useAuth();
     
     const fetchCosts = async () => {
       const token = await getToken();
       const response = await fetch('/api/v2/costs', {
         headers: {
           'Authorization': `Bearer ${token}`
         }
       });
       const data = await response.json();
       // Use cost data
     };
   }

5. BACKEND MIDDLEWARE:
   The backend already has Clerk integration in:
   - src/common/clerk_auth.py
   - Uses get_current_user dependency for protected endpoints

6. USER PERMISSIONS:
   Set user metadata in Clerk dashboard:
   {
     "permissions": ["costs:read", "metrics:read"],
     "organization_id": "org_123",
     "role": "developer"
   }

7. TESTING WITH CURL:
   # Get token from Clerk dashboard or SDK
   curl -H "Authorization: Bearer YOUR_TOKEN" \\
        http://localhost:8000/api/v2/costs

8. MONITORING:
   - Check Clerk dashboard for authentication logs
   - Monitor failed auth attempts
   - Set up webhooks for user events
    """)


def show_quick_test_options():
    """Show quick testing options"""
    print("\n🚀 Quick Test Options")
    print("=" * 60)
    print("""
OPTION 1 - Use Clerk Dashboard:
1. Go to https://dashboard.clerk.com
2. Navigate to your app → Users
3. Create a test user
4. Click "Impersonate user" to get a token
5. Use the token in the manual test above

OPTION 2 - Use Clerk CLI:
1. Install: npm install -g @clerk/clerk-cli
2. Login: clerk login
3. Create session: clerk sessions create --user-id USER_ID
4. Get token: clerk sessions get-token SESSION_ID

OPTION 3 - Use Frontend App:
1. Create a simple React app with Clerk
2. Login as a user
3. Use browser DevTools to get the token from network requests
4. Look for Authorization header in API calls

OPTION 4 - Direct Database Query (No Auth):
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
  SELECT tenant_id, model, SUM(total_cost_usd) as cost 
  FROM llm_usage 
  WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
  GROUP BY tenant_id, model
  ORDER BY cost DESC;"
    """)


if __name__ == "__main__":
    print("🔐 PRODUCTION AUTHENTICATION TESTING")
    print("=" * 60)
    
    # Check if we can do automated testing
    if CLERK_SDK_AVAILABLE and CLERK_SECRET_KEY:
        test_with_real_clerk_auth()
    else:
        print("⚠️  Automated testing not available.")
        print("   Either Clerk SDK is not installed or CLERK_SECRET_KEY is not set.")
    
    # Manual token testing
    test_with_manual_token()
    
    # Show guides
    show_production_setup_guide()
    show_quick_test_options()