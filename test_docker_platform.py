#!/usr/bin/env python3
"""Test the containerized QLP platform"""

import requests
import json
import time

def test_health():
    """Test all service health endpoints"""
    print("🏥 Testing service health endpoints...")
    print("=" * 60)
    
    services = [
        ("Orchestrator", "http://localhost:8000/health"),
        ("Agent Factory", "http://localhost:8001/health"),
        ("Validation Mesh", "http://localhost:8002/health"),
        ("Vector Memory", "http://localhost:8003/health"),
        ("Execution Sandbox", "http://localhost:8004/health"),
    ]
    
    all_healthy = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name}: {data.get('status', 'healthy')}")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: {str(e)}")
            all_healthy = False
    
    return all_healthy

def test_capsule_generation():
    """Test capsule generation with Azure OpenAI"""
    print("\n📦 Testing capsule generation...")
    print("=" * 60)
    
    request_data = {
        "request_id": "docker-test-001",
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "project_name": "Docker Platform Test",
        "description": "Create a simple Python function that returns 'Hello from Docker!'",
        "requirements": "Create a function named 'hello_docker' that returns the string 'Hello from Docker!'",
        "tech_stack": ["Python"],
        "target_environment": "docker"
    }
    
    try:
        print("📤 Sending capsule generation request...")
        response = requests.post(
            "http://localhost:8000/generate/capsule",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Capsule generated successfully!")
            print(f"   Capsule ID: {result.get('capsule_id')}")
            print(f"   Files: {result.get('file_count', 0)}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            
            # Show generated files from source_code
            if result.get('source_code'):
                print("\n📄 Generated files:")
                for file_path, content in result['source_code'].items():
                    print(f"\n   {file_path}:")
                    print("   " + "-" * 40)
                    for line in content.split('\n')[:10]:  # Show first 10 lines
                        print(f"   {line}")
                    if len(content.split('\n')) > 10:
                        print("   ...")
            
            return True, result.get('capsule_id')
        else:
            print(f"❌ Generation failed (HTTP {response.status_code})")
            print(f"   Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        return False, None

def test_capsule_export(capsule_id):
    """Test capsule export functionality"""
    print("\n📥 Testing capsule export...")
    print("=" * 60)
    
    if not capsule_id:
        print("⚠️  No capsule ID available, skipping export test")
        return False
    
    export_formats = ["ZIP", "TAR"]
    
    for format in export_formats:
        try:
            print(f"\n🗜️  Testing {format} export...")
            response = requests.post(
                f"http://localhost:8000/capsule/{capsule_id}/export/{format}",
                timeout=30
            )
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                print(f"✅ {format} export successful")
                print(f"   Content-Type: {content_type}")
                print(f"   Size: {content_length} bytes")
            else:
                print(f"❌ {format} export failed (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ {format} export failed: {str(e)}")
    
    return True

def test_temporal_ui():
    """Check if Temporal UI is accessible"""
    print("\n🕐 Testing Temporal UI...")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:8088", timeout=5)
        if response.status_code == 200:
            print("✅ Temporal UI is accessible at http://localhost:8088")
        else:
            print(f"⚠️  Temporal UI returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Temporal UI not accessible: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 QUANTUM LAYER PLATFORM - DOCKER INTEGRATION TEST")
    print("=" * 60)
    print("Testing containerized platform deployment...")
    
    # Test health
    health_ok = test_health()
    
    if health_ok:
        # Test capsule generation
        generation_ok, capsule_id = test_capsule_generation()
        
        if generation_ok:
            # Test export
            test_capsule_export(capsule_id)
    
    # Test Temporal UI
    test_temporal_ui()
    
    print("\n" + "=" * 60)
    if health_ok:
        print("✅ Platform is operational!")
        print("\n📊 Available endpoints:")
        print("   - API Documentation: http://localhost:8000/docs")
        print("   - Temporal UI: http://localhost:8088")
        print("   - Health Check: http://localhost:8000/health")
    else:
        print("⚠️  Some services are not healthy")
        print("   Run 'docker compose ps' to check service status")

if __name__ == "__main__":
    main()