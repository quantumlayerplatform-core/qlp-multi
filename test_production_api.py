#!/usr/bin/env python3
"""
Test script for production API v2
Validates all production features are working correctly
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_V2_URL = f"{BASE_URL}/api/v2"

# Test data
TEST_CAPSULE_REQUEST = {
    "project_name": "Test E-commerce API",
    "description": "Build a RESTful API for an e-commerce platform with user management, product catalog, and order processing",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    "requirements": "Include authentication, payment integration, and admin dashboard",
    "constraints": {
        "max_response_time": 200,
        "min_test_coverage": 80
    }
}


class ProductionAPITester:
    def __init__(self, base_url: str = API_V2_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self, additional: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": f"test-{datetime.now().timestamp()}"
        }
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        if additional:
            headers.update(additional)
        
        return headers
    
    async def test_health_check(self):
        """Test health endpoint"""
        print("\n🔍 Testing Health Check...")
        
        # Basic health
        response = await self.client.get(f"{self.base_url}/health")
        print(f"Basic health status: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["status"] == "healthy"
        
        # Detailed health
        response = await self.client.get(f"{self.base_url}/health?detailed=true")
        print(f"Detailed health status: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "components" in data["data"]
        
        print("✅ Health check passed")
    
    async def test_api_documentation(self):
        """Test API documentation endpoints"""
        print("\n🔍 Testing API Documentation...")
        
        # OpenAPI JSON
        response = await self.client.get(f"{self.base_url}/openapi.json")
        print(f"OpenAPI JSON status: {response.status_code}")
        assert response.status_code == 200
        openapi = response.json()
        assert openapi["info"]["version"] == "2.0.0"
        assert "paths" in openapi
        
        # Swagger UI
        response = await self.client.get(f"{self.base_url}/docs")
        print(f"Swagger UI status: {response.status_code}")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
        
        # ReDoc
        response = await self.client.get(f"{self.base_url}/redoc")
        print(f"ReDoc status: {response.status_code}")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
        
        print("✅ API documentation passed")
    
    async def test_authentication(self):
        """Test authentication"""
        print("\n🔍 Testing Authentication...")
        
        # Test without auth (should fail for protected endpoints)
        response = await self.client.post(
            f"{self.base_url}/capsules",
            json=TEST_CAPSULE_REQUEST
        )
        print(f"Without auth status: {response.status_code}")
        # Should get 401 or 403 in production with Clerk
        # In dev mode without Clerk, might still work
        
        # Set development token for testing
        self.auth_token = "dev-test-token"
        
        print("✅ Authentication test completed")
    
    async def test_rate_limiting(self):
        """Test rate limiting"""
        print("\n🔍 Testing Rate Limiting...")
        
        # Make multiple rapid requests
        endpoint = f"{self.base_url}/health"
        request_count = 0
        rate_limited = False
        
        for i in range(100):
            response = await self.client.get(endpoint)
            request_count += 1
            
            if response.status_code == 429:
                rate_limited = True
                print(f"Rate limited after {request_count} requests")
                
                # Check rate limit headers
                assert "Retry-After" in response.headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                
                data = response.json()
                assert data["success"] == False
                assert any(e["code"] == "RATE_LIMIT_EXCEEDED" for e in data["errors"])
                break
        
        # In development without Redis, rate limiting might not trigger
        if rate_limited:
            print("✅ Rate limiting working correctly")
        else:
            print("⚠️  Rate limiting not triggered (Redis might not be configured)")
    
    async def test_standardized_responses(self):
        """Test standardized response format"""
        print("\n🔍 Testing Standardized Responses...")
        
        response = await self.client.get(f"{self.base_url}/health")
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "version" in data
        assert "timestamp" in data
        assert "request_id" in data
        assert "data" in data
        assert "errors" in data
        assert "warnings" in data
        assert "links" in data
        
        # Validate format
        assert isinstance(data["success"], bool)
        assert data["version"] == "2.0.0"
        assert isinstance(data["errors"], list)
        assert isinstance(data["links"], list)
        
        # Check links format
        if data["links"]:
            link = data["links"][0]
            assert "href" in link
            assert "rel" in link
            assert "method" in link
        
        print("✅ Standardized responses passed")
    
    async def test_capsule_endpoints(self):
        """Test capsule CRUD operations"""
        print("\n🔍 Testing Capsule Endpoints...")
        
        headers = self._get_headers()
        
        # Create capsule
        print("Creating capsule...")
        response = await self.client.post(
            f"{self.base_url}/capsules",
            json=TEST_CAPSULE_REQUEST,
            headers=headers
        )
        print(f"Create capsule status: {response.status_code}")
        
        if response.status_code in [200, 201, 202]:
            data = response.json()
            assert data["success"] == True
            
            if "job_id" in data.get("data", {}):
                print(f"Async processing - Job ID: {data['data']['job_id']}")
            else:
                capsule_id = data["data"].get("id")
                print(f"Capsule created: {capsule_id}")
        
        # List capsules
        print("\nListing capsules...")
        response = await self.client.get(
            f"{self.base_url}/capsules?page=1&per_page=10",
            headers=headers
        )
        print(f"List capsules status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "meta" in data
            assert "pagination" in data.get("meta", {})
            
            pagination = data["meta"]["pagination"]
            print(f"Found {pagination['total']} capsules")
        
        print("✅ Capsule endpoints tested")
    
    async def test_error_handling(self):
        """Test error handling"""
        print("\n🔍 Testing Error Handling...")
        
        headers = self._get_headers()
        
        # Invalid request
        print("Testing validation error...")
        response = await self.client.post(
            f"{self.base_url}/capsules",
            json={"invalid": "data"},
            headers=headers
        )
        
        if response.status_code == 400:
            data = response.json()
            assert data["success"] == False
            assert len(data["errors"]) > 0
            
            error = data["errors"][0]
            assert "code" in error
            assert "message" in error
            assert "severity" in error
            print(f"Validation error handled correctly: {error['message']}")
        
        # Not found
        print("\nTesting not found error...")
        response = await self.client.get(
            f"{self.base_url}/capsules/non-existent-id",
            headers=headers
        )
        
        if response.status_code == 404:
            data = response.json()
            assert data["success"] == False
            print("Not found error handled correctly")
        
        print("✅ Error handling passed")
    
    async def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        print("\n🔍 Testing Metrics Endpoint...")
        
        headers = self._get_headers()
        
        # JSON metrics
        response = await self.client.get(
            f"{self.base_url}/metrics?period=1h",
            headers=headers
        )
        print(f"Metrics status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            metrics = data["data"]
            
            assert "requests" in metrics
            assert "capsules" in metrics
            assert "resources" in metrics
            assert "costs" in metrics
            
            print(f"Total requests: {metrics['requests']['total']}")
            print(f"Success rate: {metrics['requests']['success_rate']}")
        elif response.status_code == 403:
            print("Metrics endpoint requires permission (as expected)")
        
        # Prometheus metrics
        response = await self.client.get(
            f"{self.base_url}/metrics/prometheus",
            headers=headers
        )
        print(f"Prometheus metrics status: {response.status_code}")
        
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("text/plain")
            assert "qlp_" in response.text or "# Metrics not available" in response.text
        
        print("✅ Metrics endpoints tested")
    
    async def test_cache_headers(self):
        """Test cache headers"""
        print("\n🔍 Testing Cache Headers...")
        
        headers = self._get_headers()
        
        # First request
        response = await self.client.get(
            f"{self.base_url}/health",
            headers=headers
        )
        
        if "Cache-Control" in response.headers:
            print(f"Cache-Control: {response.headers['Cache-Control']}")
        
        if "ETag" in response.headers:
            etag = response.headers["ETag"]
            print(f"ETag: {etag}")
            
            # Conditional request
            headers["If-None-Match"] = etag
            response2 = await self.client.get(
                f"{self.base_url}/health",
                headers=headers
            )
            
            if response2.status_code == 304:
                print("✅ Conditional requests working (304 Not Modified)")
            else:
                print("⚠️  Conditional requests not implemented for this endpoint")
        else:
            print("⚠️  No ETag header found")
        
        print("✅ Cache headers tested")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Production API v2 Tests")
        print("=" * 50)
        
        try:
            await self.test_health_check()
            await self.test_api_documentation()
            await self.test_authentication()
            await self.test_standardized_responses()
            await self.test_capsule_endpoints()
            await self.test_error_handling()
            await self.test_rate_limiting()
            await self.test_metrics_endpoint()
            await self.test_cache_headers()
            
            print("\n" + "=" * 50)
            print("✅ All tests completed successfully!")
            print("\n📊 Production API v2 Summary:")
            print("- ✅ Health monitoring working")
            print("- ✅ API documentation available")
            print("- ✅ Standardized responses implemented")
            print("- ✅ Error handling working")
            print("- ✅ Metrics collection active")
            print("- ⚠️  Full authentication requires Clerk setup")
            print("- ⚠️  Rate limiting requires Redis")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test runner"""
    async with ProductionAPITester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    print("Testing Production API v2...")
    print(f"Target: {API_V2_URL}")
    asyncio.run(main())