#!/usr/bin/env python3
"""Test QLP platform running on Kubernetes"""

import subprocess
import time
import requests
import signal
import sys

# Track port-forward processes
port_forwards = []

def cleanup(signum=None, frame=None):
    """Clean up port forwards on exit"""
    print("\nCleaning up port forwards...")
    for proc in port_forwards:
        proc.terminate()
    sys.exit(0)

# Set up signal handler
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def setup_port_forward(service, local_port, service_port, namespace="qlp"):
    """Set up kubectl port-forward"""
    cmd = f"kubectl port-forward svc/{service} {local_port}:{service_port} -n {namespace}"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    port_forwards.append(proc)
    time.sleep(2)  # Give it time to start
    return proc

def test_service_health(service_name, port):
    """Test service health endpoint"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('status', 'unknown')
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("🚀 QUANTUM LAYER PLATFORM - KUBERNETES TEST")
    print("=" * 60)
    
    # Services to test
    services = [
        ("orchestrator", 8000),
        ("agent-factory", 8001),
        ("validation-mesh", 8002),
        ("vector-memory", 8003),
        ("execution-sandbox", 8004),
    ]
    
    print("\n📡 Setting up port forwards...")
    for service, port in services:
        setup_port_forward(service, port, port)
        print(f"   ✓ {service} -> localhost:{port}")
    
    print("\n🏥 Testing service health endpoints...")
    print("-" * 60)
    
    all_healthy = True
    for service, port in services:
        success, status = test_service_health(service, port)
        if success:
            print(f"✅ {service}: {status}")
        else:
            print(f"❌ {service}: {status}")
            all_healthy = False
    
    if all_healthy:
        print("\n📦 Testing capsule generation...")
        print("-" * 60)
        
        # Test capsule generation
        request_data = {
            "request_id": "k8s-test-001",
            "tenant_id": "test",
            "user_id": "test",
            "project_name": "Kubernetes Test",
            "description": "Create a Python function that returns 'Hello from Kubernetes!'",
            "requirements": "Function should be named hello_k8s",
            "tech_stack": ["Python"]
        }
        
        try:
            response = requests.post(
                "http://localhost:8000/generate/capsule",
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Capsule generated successfully!")
                print(f"   Capsule ID: {result.get('capsule_id')}")
                print(f"   Files: {result.get('files_generated', 0)}")
                print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            else:
                print(f"❌ Generation failed (HTTP {response.status_code})")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Generation failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ Kubernetes deployment test complete!")
    print("\n📊 Platform Status:")
    print(f"   - Namespace: qlp")
    print(f"   - Services: {len(services)}")
    print(f"   - Health: {'All services operational' if all_healthy else 'Some services unhealthy'}")
    
    print("\n💡 To access the platform:")
    print("   - Keep this script running for port forwards")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Or use: kubectl port-forward svc/<service> <port>:<port> -n qlp")
    
    print("\nPress Ctrl+C to stop port forwards and exit...")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()