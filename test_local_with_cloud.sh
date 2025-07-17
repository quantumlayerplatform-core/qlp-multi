#\!/bin/bash
echo "🚀 Testing QLP with Cloud Services"
echo "================================="

# Backup current env
echo "1. Backing up current .env..."
cp .env .env.local-backup 2>/dev/null || true

# Use cloud env
echo "2. Switching to cloud configuration..."
cp .env.cloud .env

# Stop any running services
echo "3. Stopping existing services..."
docker-compose -f docker-compose.platform.yml down

# Start with cloud services
echo "4. Starting services with cloud backends..."
docker-compose -f docker-compose.cloud-services.yml up -d

# Wait for services
echo "5. Waiting for services to be ready..."
sleep 30

# Test health
echo "6. Testing service health..."
for service in orchestrator:8000 agent-factory:8001 validation-mesh:8002 vector-memory:8003 execution-sandbox:8004; do
    name=${service%:*}
    port=${service#*:}
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "   ✅ $name is healthy"
    else
        echo "   ❌ $name is not responding"
    fi
done

echo ""
echo "7. Running integration test..."
# Test with a simple request
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a Python function that returns Hello World"}'

echo ""
echo ""
echo "✅ Cloud services test complete\!"
echo "Check logs with: docker-compose -f docker-compose.cloud-services.yml logs -f"
