#!/bin/bash

# Quantum Layer Platform - Enterprise Worker Startup Script
# Starts the enterprise-grade Temporal worker with monitoring

set -e

echo "============================================="
echo "Starting Quantum Layer Enterprise Worker"
echo "============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Export enterprise configuration
export WORKFLOW_MAX_BATCH_SIZE=50
export WORKFLOW_MAX_CONCURRENT_ACTIVITIES=100
export WORKFLOW_MAX_CONCURRENT_WORKFLOWS=50
export ENABLE_DYNAMIC_SCALING=true
export CIRCUIT_BREAKER_ENABLED=true
export ENABLE_ADAPTIVE_TIMEOUTS=true
export ENABLE_METRICS=true
export ENABLE_DISTRIBUTED_TRACING=true
export ENTERPRISE_FEATURES_ENABLED=true

# Check if services are running
check_service() {
    local service=$1
    local port=$2
    if ! nc -z localhost $port 2>/dev/null; then
        echo "⚠️  Warning: $service is not running on port $port"
        return 1
    fi
    return 0
}

echo "Checking required services..."
services_ok=true

check_service "Temporal" 7233 || services_ok=false
check_service "PostgreSQL" 15432 || services_ok=false
check_service "Redis" 6379 || services_ok=false
check_service "Orchestrator" 8000 || services_ok=false
check_service "Agent Factory" 8001 || services_ok=false

if [ "$services_ok" = false ]; then
    echo ""
    echo "❌ Some required services are not running."
    echo "Please start them first with: ./start_all.sh"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Kill any existing worker processes
echo "Stopping any existing workers..."
pkill -f "worker_production_enterprise.py" 2>/dev/null || true
sleep 2

# Create logs directory if it doesn't exist
mkdir -p logs/enterprise

# Start the enterprise worker
echo ""
echo "Starting Enterprise Worker with configuration:"
echo "  - Max Batch Size: $WORKFLOW_MAX_BATCH_SIZE"
echo "  - Max Concurrent Activities: $WORKFLOW_MAX_CONCURRENT_ACTIVITIES"
echo "  - Max Concurrent Workflows: $WORKFLOW_MAX_CONCURRENT_WORKFLOWS"
echo "  - Dynamic Scaling: $ENABLE_DYNAMIC_SCALING"
echo "  - Circuit Breaker: $CIRCUIT_BREAKER_ENABLED"
echo "  - Adaptive Timeouts: $ENABLE_ADAPTIVE_TIMEOUTS"
echo "  - Metrics Collection: $ENABLE_METRICS"
echo ""

# Start worker with monitoring
python -u src/orchestrator/worker_production_enterprise.py 2>&1 | tee logs/enterprise/worker-$(date +%Y%m%d-%H%M%S).log &

WORKER_PID=$!
echo "Enterprise worker started with PID: $WORKER_PID"

# Function to handle shutdown
cleanup() {
    echo ""
    echo "Shutting down enterprise worker..."
    kill $WORKER_PID 2>/dev/null || true
    wait $WORKER_PID 2>/dev/null || true
    echo "Worker stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Monitor worker
echo ""
echo "============================================="
echo "Enterprise Worker is running"
echo "============================================="
echo ""
echo "Monitoring endpoints:"
echo "  - Temporal UI: http://localhost:8088"
echo "  - Metrics: http://localhost:8000/metrics"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the worker"
echo ""

# Keep script running
wait $WORKER_PID