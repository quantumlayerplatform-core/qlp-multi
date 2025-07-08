#\!/usr/bin/env python3
"""
Diagnose and fix Temporal Worker health issues in QuantumLayer Platform
"""

import subprocess
import json
import time
import sys
import os
from datetime import datetime


def run_command(cmd, capture=True):
    """Execute a command and return output"""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode


def get_container_logs(container_name, lines=100):
    """Get recent logs from a container"""
    stdout, stderr, rc = run_command(f"docker logs --tail {lines} {container_name}")
    return stdout + stderr


def inspect_container(container_name):
    """Get detailed container information"""
    stdout, stderr, rc = run_command(f"docker inspect {container_name}")
    if rc == 0:
        return json.loads(stdout)[0]
    return None


def check_service_connectivity(container_name, service_url):
    """Check if a container can reach a service"""
    cmd = f"docker exec {container_name} curl -s -o /dev/null -w '%{{http_code}}' {service_url} || echo 'Failed'"
    stdout, stderr, rc = run_command(cmd)
    return stdout.strip()


def main():
    print("🔍 Diagnosing Temporal Worker Health Issues")
    print("=" * 60)
    
    # Step 1: Check container status
    print("\n1. Checking container status...")
    container_info = inspect_container("qlp-temporal-worker")
    
    if not container_info:
        print("❌ Container 'qlp-temporal-worker' not found\!")
        return
    
    state = container_info["State"]
    health = state.get("Health", {})
    
    print(f"   Status: {state['Status']}")
    print(f"   Running: {state['Running']}")
    print(f"   Health Status: {health.get('Status', 'No health check')}")
    
    if health.get("Log"):
        print("\n   Recent health check results:")
        for log_entry in health["Log"][-3:]:
            print(f"   - Exit Code: {log_entry['ExitCode']}")
            print(f"     Output: {log_entry.get('Output', '').strip()}")
            print(f"     Time: {log_entry['Start']}")
    
    # Step 2: Check recent logs
    print("\n2. Checking recent logs...")
    logs = get_container_logs("qlp-temporal-worker", 50)
    
    # Look for common error patterns
    error_patterns = [
        "Connection refused",
        "Failed to connect",
        "ImportError",
        "ModuleNotFoundError",
        "AttributeError",
        "temporal",
        "Cannot connect",
        "timeout",
        "health check"
    ]
    
    print("\n   Key log entries:")
    for line in logs.split('\n')[-20:]:
        for pattern in error_patterns:
            if pattern.lower() in line.lower():
                print(f"   ⚠️  {line.strip()}")
                break
    
    # Step 3: Check service dependencies
    print("\n3. Checking service dependencies...")
    
    # Check Temporal connectivity from worker container
    temporal_status = check_service_connectivity("qlp-temporal-worker", "http://temporal:7233")
    print(f"   Temporal Server: {temporal_status}")
    
    # Check if Temporal is healthy
    temporal_health = check_service_connectivity("qlp-temporal", "http://localhost:7233")
    print(f"   Temporal Health (direct): {temporal_health}")
    
    # Step 4: Check environment variables
    print("\n4. Checking environment variables...")
    env_vars = container_info["Config"]["Env"]
    important_vars = ["TEMPORAL_HOST", "SERVICE_NAME", "PYTHONPATH"]
    
    for var in important_vars:
        for env in env_vars:
            if env.startswith(f"{var}="):
                print(f"   {env}")
    
    # Step 5: Attempt fixes
    print("\n5. Attempting fixes...")
    
    # Fix 1: Restart the worker
    print("   - Restarting temporal worker...")
    run_command("docker restart qlp-temporal-worker", capture=False)
    time.sleep(10)
    
    # Check status after restart
    container_info = inspect_container("qlp-temporal-worker")
    new_health = container_info["State"].get("Health", {})
    print(f"   Health after restart: {new_health.get('Status', 'Unknown')}")
    
    # Fix 2: If still unhealthy, check the health check command
    if new_health.get("Status") == "unhealthy":
        print("\n   - Checking health check configuration...")
        healthcheck = container_info["Config"].get("Healthcheck", {})
        if healthcheck:
            print(f"     Test command: {' '.join(healthcheck.get('Test', []))}")
            print(f"     Interval: {healthcheck.get('Interval', 0) / 1e9}s")
            print(f"     Timeout: {healthcheck.get('Timeout', 0) / 1e9}s")
            print(f"     Retries: {healthcheck.get('Retries', 0)}")
        
        # Try running the health check manually
        print("\n   - Running health check manually...")
        if healthcheck and healthcheck.get("Test"):
            test_cmd = ' '.join(healthcheck["Test"][1:])  # Skip 'CMD' part
            manual_check = f"docker exec qlp-temporal-worker {test_cmd}"
            stdout, stderr, rc = run_command(manual_check)
            print(f"     Exit code: {rc}")
            print(f"     Output: {stdout}")
            if stderr:
                print(f"     Error: {stderr}")
    
    # Step 6: Check if worker module exists
    print("\n6. Verifying worker module...")
    module_check = "docker exec qlp-temporal-worker python -c \"import src.orchestrator.worker_production; print('Module OK')\""
    stdout, stderr, rc = run_command(module_check)
    if rc == 0:
        print("   ✅ Worker module found and importable")
    else:
        print("   ❌ Worker module import failed:")
        print(f"      {stderr}")
    
    # Step 7: Final recommendations
    print("\n7. Recommendations:")
    
    if new_health.get("Status") == "healthy":
        print("   ✅ Worker is now healthy\!")
    else:
        print("   ⚠️  Worker is still unhealthy. Consider:")
        print("   - Checking the worker_production.py file for syntax errors")
        print("   - Verifying all required services are running")
        print("   - Reviewing the Dockerfile and docker-compose configuration")
        print("   - Running: docker-compose logs temporal-worker -f")
        print("   - Rebuilding the image: docker-compose build temporal-worker")
    
    # Step 8: Show current service status
    print("\n8. Current service status:")
    run_command("docker-compose ps", capture=False)


if __name__ == "__main__":
    main()
EOF < /dev/null