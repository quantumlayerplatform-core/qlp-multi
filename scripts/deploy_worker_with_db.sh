#!/bin/bash
# Deploy Production Worker with Database Persistence

echo "🚀 Deploying Production Worker with PostgreSQL Persistence"
echo "=========================================================="

# Check if Docker Compose is running
if ! docker-compose -f docker-compose.platform.yml ps | grep -q "Up"; then
    echo "❌ Docker Compose services are not running. Please start them first."
    exit 1
fi

echo "📦 Building new temporal-worker image..."
docker-compose -f docker-compose.platform.yml build temporal-worker

echo "🔄 Stopping current temporal-worker..."
docker-compose -f docker-compose.platform.yml stop temporal-worker

echo "🗑️  Removing old temporal-worker container..."
docker-compose -f docker-compose.platform.yml rm -f temporal-worker

echo "🚀 Starting new temporal-worker with database persistence..."
docker-compose -f docker-compose.platform.yml up -d temporal-worker

echo "⏳ Waiting for worker to be healthy..."
sleep 10

# Check worker health
if docker-compose -f docker-compose.platform.yml ps temporal-worker | grep -q "healthy"; then
    echo "✅ Worker deployed successfully with database persistence!"
    echo ""
    echo "📊 Worker Status:"
    docker-compose -f docker-compose.platform.yml ps temporal-worker
    echo ""
    echo "📝 Recent Logs:"
    docker-compose -f docker-compose.platform.yml logs --tail=20 temporal-worker | grep -E "(Database|PostgreSQL|capsule.*saved)"
else
    echo "❌ Worker health check failed. Check logs:"
    docker-compose -f docker-compose.platform.yml logs --tail=50 temporal-worker
    exit 1
fi

echo ""
echo "✨ Production worker deployed with PostgreSQL persistence enabled!"
echo "🔍 To monitor: docker-compose -f docker-compose.platform.yml logs -f temporal-worker"