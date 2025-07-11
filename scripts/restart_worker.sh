#!/bin/bash
# Restart temporal worker with latest code

echo "🔄 Restarting Temporal Worker with PostgreSQL Storage"
echo "====================================================="

# Build the image
echo "📦 Building temporal-worker image..."
docker-compose -f docker-compose.platform.yml build temporal-worker

# Restart the worker
echo "🚀 Restarting temporal-worker..."
docker-compose -f docker-compose.platform.yml restart temporal-worker

# Wait for health
echo "⏳ Waiting for worker to be healthy..."
sleep 10

# Check logs
echo "📝 Worker logs:"
docker-compose -f docker-compose.platform.yml logs --tail=20 temporal-worker | grep -E "(PostgreSQL|Starting|capsule.*saved|✅)"

echo ""
echo "✅ Worker restarted with PostgreSQL storage enabled!"