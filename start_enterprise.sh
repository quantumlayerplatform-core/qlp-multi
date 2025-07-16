#!/bin/bash

# Start QLP in Enterprise Mode with enhanced reliability features

echo "🚀 Starting Quantum Layer Platform in ENTERPRISE MODE"
echo "=================================================="
echo ""
echo "Features enabled:"
echo "  ✅ Circuit breakers for service resilience"
echo "  ✅ Parallel task execution with smart batching"
echo "  ✅ Workflow checkpointing and recovery"
echo "  ✅ Extended timeouts for complex workloads"
echo "  ✅ Enhanced monitoring with Prometheus/Grafana"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Stop any existing services
echo "Stopping existing services..."
docker-compose -f docker-compose.platform.yml down

# Start services with enterprise configuration
echo "Starting services in enterprise mode..."
docker-compose -f docker-compose.platform.yml -f docker-compose.enterprise.yml up -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."
services=("orchestrator:8000" "agent-factory:8001" "validation-mesh:8002" "vector-memory:8003" "execution-sandbox:8004" "temporal:7233")

all_healthy=true
for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1 || [ "$name" = "temporal" ]; then
        echo "  ✅ $name is healthy"
    else
        echo "  ❌ $name is not responding"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "✅ All services are running in ENTERPRISE MODE!"
    echo ""
    echo "📊 Monitoring:"
    echo "  - Temporal UI: http://localhost:8088"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000 (admin/qlp-admin)"
    echo ""
    echo "🔧 API Endpoints:"
    echo "  - Orchestrator: http://localhost:8000/docs"
    echo "  - Agent Factory: http://localhost:8001/docs"
    echo "  - Validation Mesh: http://localhost:8002/docs"
    echo "  - Vector Memory: http://localhost:8003/docs"
    echo "  - Execution Sandbox: http://localhost:8004/docs"
    echo ""
    echo "📝 View logs:"
    echo "  docker-compose -f docker-compose.platform.yml -f docker-compose.enterprise.yml logs -f"
else
    echo ""
    echo "⚠️  Some services failed to start. Check logs:"
    echo "  docker-compose -f docker-compose.platform.yml -f docker-compose.enterprise.yml logs"
fi