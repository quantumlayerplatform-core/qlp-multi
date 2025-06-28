#!/bin/bash

echo "🚀 Starting Quantum Layer Platform..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

# Export environment variables from .env file
if [ -f .env ]; then
    echo "📋 Loading environment variables..."
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found!"
    exit 1
fi

# Set Python path to the project root
export PYTHONPATH=/Users/satish/qlp-projects/qlp-multi:$PYTHONPATH

# Stop any existing services
echo "🧹 Cleaning up existing services..."
./stop_platform.sh 2>/dev/null || true

# Create directories
mkdir -p logs

echo ""
echo "🚀 Starting services..."

# Start services from project root using module syntax
# Start Vector Memory Service
echo "Starting Vector Memory Service..."
nohup python -m uvicorn src.memory.main:app --host 0.0.0.0 --port 8003 --reload > logs/memory.log 2>&1 &
MEMORY_PID=$!
echo "  PID: $MEMORY_PID"

# Start Validation Mesh
echo "Starting Validation Mesh..."
nohup python -m uvicorn src.validation.main:app --host 0.0.0.0 --port 8002 --reload > logs/validation.log 2>&1 &
VALIDATION_PID=$!
echo "  PID: $VALIDATION_PID"

# Start Orchestrator
echo "Starting Orchestrator..."
nohup python -m uvicorn src.orchestrator.main:app --host 0.0.0.0 --port 8000 --reload > logs/orchestrator.log 2>&1 &
ORCH_PID=$!
echo "  PID: $ORCH_PID"

# Start Agent Factory
echo "Starting Agent Factory..."
nohup python -m uvicorn src.agents.main:app --host 0.0.0.0 --port 8001 --reload > logs/agents.log 2>&1 &
AGENT_PID=$!
echo "  PID: $AGENT_PID"

# Start Execution Sandbox
echo "Starting Execution Sandbox..."
nohup python -m uvicorn src.sandbox.main:app --host 0.0.0.0 --port 8004 --reload > logs/sandbox.log 2>&1 &
SANDBOX_PID=$!
echo "  PID: $SANDBOX_PID"

# Save PIDs
echo $MEMORY_PID > logs/memory.pid
echo $VALIDATION_PID > logs/validation.pid
echo $ORCH_PID > logs/orchestrator.pid
echo $AGENT_PID > logs/agents.pid
echo $SANDBOX_PID > logs/sandbox.pid

# Wait for services to start
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check services
echo ""
echo "🏥 Checking service health..."

check_health() {
    local name=$1
    local port=$2
    local url="http://localhost:$port/health"
    
    echo -n "$name: "
    
    if curl -s $url > /dev/null 2>&1; then
        echo "✅ Healthy"
        curl -s $url | python -m json.tool | grep -E '"status"' || true
    else
        echo "❌ Not responding"
        echo "  Last log entries:"
        tail -5 logs/$(echo $name | tr '[:upper:]' '[:lower:]' | awk '{print $1}').log 2>/dev/null | sed 's/^/    /'
    fi
}

check_health "Vector Memory" 8003
echo ""
check_health "Validation Mesh" 8002
echo ""
check_health "Orchestrator" 8000
echo ""
check_health "Agent Factory" 8001
echo ""
check_health "Execution Sandbox" 8004

echo ""
echo "📊 Service URLs:"
echo "  - Orchestrator: http://localhost:8000/docs"
echo "  - Agent Factory: http://localhost:8001/docs"
echo "  - Validation Mesh: http://localhost:8002/docs"
echo "  - Vector Memory: http://localhost:8003/docs"
echo "  - Execution Sandbox: http://localhost:8004/docs"
echo ""
echo "📋 View logs: tail -f logs/*.log"
echo "🛑 To stop: ./stop_platform.sh"
echo ""
echo "📝 Test the system:"
echo 'curl -X POST http://localhost:8000/execute \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{'
echo '    "tenant_id": "default",'
echo '    "user_id": "test",'
echo '    "description": "Write a hello world function in Python"'
echo '  }'"'"''
