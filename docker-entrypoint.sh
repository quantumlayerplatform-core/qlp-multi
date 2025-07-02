#!/bin/bash
set -e

# Wait for dependencies
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service at $host:$port..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "$service is ready!"
}

# Wait for required services based on SERVICE_NAME
case "$SERVICE_NAME" in
    orchestrator)
        wait_for_service ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432} "PostgreSQL"
        wait_for_service ${REDIS_HOST:-redis} ${REDIS_PORT:-6379} "Redis"
        wait_for_service ${TEMPORAL_HOST:-temporal} ${TEMPORAL_PORT:-7233} "Temporal"
        PORT=${PORT:-8000}
        MODULE="src.orchestrator.main:app"
        ;;
    agent-factory)
        wait_for_service ${REDIS_HOST:-redis} ${REDIS_PORT:-6379} "Redis"
        PORT=${PORT:-8001}
        MODULE="src.agents.main:app"
        ;;
    validation-mesh)
        PORT=${PORT:-8002}
        MODULE="src.validation.main:app"
        ;;
    vector-memory)
        wait_for_service ${QDRANT_HOST:-qdrant} ${QDRANT_PORT:-6333} "Qdrant"
        PORT=${PORT:-8003}
        MODULE="src.memory.main:app"
        ;;
    execution-sandbox)
        PORT=${PORT:-8004}
        MODULE="src.sandbox.main:app"
        ;;
    temporal-worker)
        wait_for_service ${TEMPORAL_HOST:-temporal} ${TEMPORAL_PORT:-7233} "Temporal"
        echo "Starting Temporal worker..."
        exec python -m src.orchestrator.worker
        ;;
    *)
        echo "Unknown service: $SERVICE_NAME"
        exit 1
        ;;
esac

# Start the service
echo "Starting $SERVICE_NAME on port $PORT..."
exec python -m uvicorn $MODULE --host 0.0.0.0 --port $PORT