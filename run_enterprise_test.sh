#!/bin/bash

# Script to run enterprise test with proper environment

echo "🚀 Running Enterprise SaaS Platform Test"
echo "========================================"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Check if services are running
echo ""
echo "Checking services..."
services_running=true

for port in 8000 8001 8002 8003 8004; do
    if ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "❌ Service on port $port is not running"
        services_running=false
    fi
done

if [ "$services_running" = false ]; then
    echo ""
    echo "⚠️  Some services are not running. Starting all services..."
    echo ""
    
    # Try to start services
    if [ -f "./start_all.sh" ]; then
        ./start_all.sh
        echo ""
        echo "Waiting 30 seconds for services to initialize..."
        sleep 30
    else
        echo "❌ Cannot find start_all.sh script"
        exit 1
    fi
fi

echo ""
echo "✅ All services are running. Starting enterprise test..."
echo ""

# Run the test
python test_enterprise_improvements.py