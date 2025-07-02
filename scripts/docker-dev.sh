#!/bin/bash
set -e

echo "🚀 Starting Quantum Layer Platform with Docker Compose..."

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo "⚠️  .env.docker not found. Creating from .env..."
    cp .env .env.docker
    echo ""
    echo "Please update .env.docker with your Azure OpenAI credentials"
    echo "Then run this script again."
    exit 1
fi

# Export environment variables
export $(cat .env.docker | grep -v '^#' | xargs)

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose -f docker-compose.platform.yml pull

# Start infrastructure services first
echo "🏗️  Starting infrastructure services..."
docker-compose -f docker-compose.platform.yml up -d postgres redis qdrant temporal

# Wait for services to be ready
echo "⏳ Waiting for infrastructure services..."
sleep 30

# Initialize database
echo "🗄️  Initializing database..."
docker-compose -f docker-compose.platform.yml run --rm orchestrator python init_database.py

# Start all services
echo "🚀 Starting all services..."
docker-compose -f docker-compose.platform.yml up -d

# Show logs
echo ""
echo "✅ Platform is starting up!"
echo ""
echo "📊 Service URLs:"
echo "  - Orchestrator API: http://localhost:8000"
echo "  - Agent Factory API: http://localhost:8001"
echo "  - Validation Mesh API: http://localhost:8002"
echo "  - Vector Memory API: http://localhost:8003"
echo "  - Execution Sandbox API: http://localhost:8004"
echo "  - Temporal UI: http://localhost:8088"
echo "  - pgAdmin: http://localhost:5050"
echo ""
echo "📝 API Documentation: http://localhost:8000/docs"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose -f docker-compose.platform.yml logs -f"
echo "  - Stop platform: docker-compose -f docker-compose.platform.yml down"
echo "  - Clean up: docker-compose -f docker-compose.platform.yml down -v"
echo ""
echo "🧪 Test the platform:"
echo "  python test_azure_complete.py"