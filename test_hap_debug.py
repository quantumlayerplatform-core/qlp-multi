#!/usr/bin/env python3
"""
Debug HAP issues with enterprise test
"""

import httpx
import json

# The exact request from enterprise test
request_data = {
    "description": """
    Build a comprehensive e-commerce platform backend with the following services:
    
    1. Product Catalog Service:
       - Product CRUD operations
       - Category management
       - Inventory tracking
       - Price management
       - Product search and filtering
    
    2. User Service:
       - User registration and authentication
       - Profile management
       - Address book
       - Preferences and settings
       - OAuth2 integration
    
    3. Order Service:
       - Shopping cart management
       - Order processing workflow
       - Order status tracking
       - Order history
       - Invoice generation
    
    4. Inventory Service:
       - Real-time inventory tracking
       - Stock level alerts
       - Warehouse management
       - Reorder point calculations
       - Inventory reports
    
    5. Payment Service:
       - Multiple payment gateway integration
       - Payment processing
       - Transaction logging
       - Refund processing
       - PCI compliance measures
    
    6. Search Service:
       - Full-text product search
       - Faceted search with filters
       - Search suggestions and autocomplete
       - Search analytics
       - Elasticsearch integration
    
    7. Reviews and Ratings Service:
       - Product reviews and ratings
       - Review moderation workflow
       - Helpful votes system
       - Review analytics
       - Customer Q&A section
    
    8. Recommendation Engine:
       - Personalized product recommendations
       - Related products
       - Frequently bought together
       - Trending products
       - Machine learning integration
    
    9. Analytics Dashboard:
       - Sales analytics and reporting
       - Customer behavior tracking
       - Inventory analytics
       - Performance metrics
       - Export functionality
    
    10. Admin API:
        - Product management interface
        - Order management dashboard
        - Customer management
        - Analytics and reporting
        - System configuration
    
    Technical specifications:
    - RESTful APIs with FastAPI
    - PostgreSQL database with optimized schemas
    - Redis for caching and sessions
    - Comprehensive test suites
    - Docker containerization
    - API documentation
    - Performance optimizations
    """,
    
    "requirements": """
    Build with these requirements:
    - Clean, maintainable code architecture
    - Comprehensive error handling
    - Unit and integration tests
    - Database migrations
    - API rate limiting
    - Caching strategies
    - Monitoring and logging
    """,
    
    "constraints": {
        "language": "python",
        "framework": "fastapi",
        "database": "postgresql",
        "cache": "redis",
        "testing": "pytest"
    },
    
    "metadata": {
        "project_type": "ecommerce_platform",
        "priority": "high",
        "complexity": "high"
    },
    
    "user_id": "enterprise_test_user",
    "tenant_id": "enterprise_test_tenant"
}

async def test_hap():
    """Test HAP with the enterprise request"""
    print("Testing HAP with enterprise e-commerce request...")
    print("-" * 60)
    
    # First, let's check HAP directly
    async with httpx.AsyncClient() as client:
        hap_request = {
            "content": request_data["description"],
            "context": "user_request",
            "tenant_id": request_data["tenant_id"],
            "user_id": request_data["user_id"]
        }
        
        # Check HAP service directly
        print("\n1. Testing HAP service directly...")
        try:
            response = await client.post(
                "http://localhost:8000/api/hap/check",
                json=hap_request
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Result: {json.dumps(result, indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error calling HAP: {e}")
        
        # Now test the execute endpoint
        print("\n2. Testing /execute endpoint...")
        try:
            response = await client.post(
                "http://localhost:8000/execute",
                json=request_data
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 202:
                print("Success! Workflow started")
                print(f"Response: {response.json()}")
            else:
                print(f"Failed!")
                print(f"Response: {response.text}")
                if response.status_code == 400:
                    error_data = response.json()
                    print(f"\nError details:")
                    print(f"  Error: {error_data.get('error')}")
                    print(f"  Detail: {error_data.get('detail')}")
                    print(f"  Severity: {error_data.get('severity')}")
                    print(f"  Threshold: {error_data.get('threshold')}")
        except Exception as e:
            print(f"Error calling execute: {e}")
        
        # Test with individual problematic words
        print("\n3. Testing individual words...")
        test_words = ["review moderation", "threat", "abuse", "harm", "Review moderation workflow"]
        
        for word in test_words:
            test_desc = f"Create a system for {word}"
            test_req = {
                "description": test_desc,
                "user_id": "test",
                "tenant_id": "test"
            }
            
            response = await client.post(
                "http://localhost:8000/execute",
                json=test_req
            )
            
            if response.status_code == 202:
                print(f"  ✓ '{word}' - PASSED")
            else:
                print(f"  ✗ '{word}' - BLOCKED")
                if response.status_code == 400:
                    error = response.json()
                    print(f"    Reason: {error.get('detail', 'Unknown')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_hap())