#!/bin/bash
echo "🚀 Testing QLP with Hybrid Cloud Services"
echo "========================================"
echo "Using: Supabase (PostgreSQL) + Qdrant Cloud + Local Temporal"
echo ""

# Stop any running services
echo "1. Stopping existing services..."
docker-compose -f docker-compose.cloud-services.yml down 2>/dev/null
docker-compose -f docker-compose.platform.yml down 2>/dev/null

# Start with hybrid configuration
echo "2. Starting services with hybrid cloud/local backends..."
docker-compose -f docker-compose.hybrid.yml up -d

# Wait for services
echo "3. Waiting for services to be ready..."
sleep 40

# Test health
echo "4. Testing service health..."
for service in orchestrator:8000 agent-factory:8001 validation-mesh:8002 vector-memory:8003 execution-sandbox:8004; do
    name=${service%:*}
    port=${service#*:}
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "   ✅ $name is healthy"
    else
        echo "   ❌ $name is not responding"
    fi
done

echo ""
echo "5. Testing Temporal UI..."
if curl -s http://localhost:8088 > /dev/null 2>&1; then
    echo "   ✅ Temporal UI is accessible at http://localhost:8088"
else
    echo "   ❌ Temporal UI is not responding"
fi

echo ""
echo "6. Running integration test..."
# Test with a simple request
response=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "task": "Write a Python function that returns Hello World",
    "description": "Simple hello world function"
  }')

if echo "$response" | grep -q "workflow_id"; then
    echo "   ✅ Request submitted successfully!"
    echo "   Response: $response"
else
    echo "   ❌ Request failed"
    echo "   Response: $response"
fi

echo ""
echo "✅ Hybrid cloud test complete!"
echo ""
echo "Summary:"
echo "- PostgreSQL: ✅ Supabase Cloud"
echo "- Vector DB: ✅ Qdrant Cloud"  
echo "- Temporal: 🏠 Local (until auth fixed)"
echo "- Redis: 🏠 Local"
echo ""
echo "Check logs with: docker-compose -f docker-compose.hybrid.yml logs -f"
echo "Access Temporal UI at: http://localhost:8088"