#!/usr/bin/env python3
"""
Simple service starter for QLP platform
"""

import os
import sys
import subprocess
import time
import signal
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Service configuration
SERVICES = [
    {
        "name": "Orchestrator",
        "module": "src.orchestrator.main:app",
        "port": 8000,
        "env": {}
    },
    {
        "name": "Agent Factory",
        "module": "src.agents.main:app",
        "port": 8001,
        "env": {}
    },
    {
        "name": "Validation Mesh",
        "module": "src.validation.main:app",
        "port": 8002,
        "env": {}
    },
    {
        "name": "Vector Memory",
        "module": "src.memory.main:app",
        "port": 8003,
        "env": {}
    },
    {
        "name": "Execution Sandbox",
        "module": "src.sandbox.main:app",
        "port": 8004,
        "env": {}
    }
]

processes = []

def signal_handler(sig, frame):
    print("\n🛑 Stopping all services...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def check_port(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('', port))
        sock.close()
        return True
    except:
        return False

def start_service(service):
    """Start a single service"""
    env = os.environ.copy()
    env.update(service['env'])
    env['PYTHONPATH'] = str(project_root)
    
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        service['module'],
        "--host", "0.0.0.0",
        "--port", str(service['port']),
        "--reload"
    ]
    
    print(f"🚀 Starting {service['name']} on port {service['port']}...")
    
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    return proc

def main():
    print("🔧 Quantum Layer Platform - Service Starter")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Error: Python 3.11+ is required")
        sys.exit(1)
    
    # Load .env file if exists
    env_file = project_root / '.env'
    if env_file.exists():
        print("📋 Loading environment variables from .env")
        from dotenv import load_dotenv
        load_dotenv()
    
    # Check ports
    print("\n🔍 Checking port availability...")
    for service in SERVICES:
        if not check_port(service['port']):
            print(f"❌ Port {service['port']} is already in use ({service['name']})")
            print("   Run 'pkill -f uvicorn' to stop existing services")
            sys.exit(1)
    
    print("✅ All ports are available")
    
    # Start services
    print("\n🚀 Starting services...")
    for service in SERVICES:
        proc = start_service(service)
        processes.append(proc)
        time.sleep(2)  # Give each service time to start
    
    print("\n✅ All services started!")
    print("\n📊 Service URLs:")
    for service in SERVICES:
        print(f"   - {service['name']}: http://localhost:{service['port']}/docs")
    
    print("\n💡 Press Ctrl+C to stop all services")
    
    # Monitor services
    try:
        while True:
            time.sleep(1)
            # Check if any service has crashed
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"\n❌ {SERVICES[i]['name']} crashed!")
                    # Print last few lines of output
                    stdout, stderr = proc.communicate()
                    if stderr:
                        print(f"Error output:\n{stderr[-500:]}")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()