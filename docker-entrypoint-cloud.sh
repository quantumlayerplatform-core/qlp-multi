#!/bin/bash
set -e

# Wait for dependencies
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service at $host:$port..."
    while ! python -c "import socket; sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); result = sock.connect_ex(('$host', $port)); sock.close(); exit(result)" 2>/dev/null; do
        sleep 1
    done
    echo "$service is ready!"
}

# Check if we're using cloud services
if [ -n "$SUPABASE_DATABASE_URL" ] || [ -n "$DATABASE_URL" ]; then
    echo "Using cloud PostgreSQL (Supabase), skipping local PostgreSQL wait..."
    SKIP_POSTGRES_WAIT=true
fi

if [ -n "$QDRANT_CLOUD_URL" ]; then
    echo "Using Qdrant Cloud, skipping local Qdrant wait..."
    SKIP_QDRANT_WAIT=true
fi

if [ -n "$TEMPORAL_CLOUD_ENDPOINT" ]; then
    echo "Using Temporal Cloud, skipping local Temporal wait..."
    SKIP_TEMPORAL_WAIT=true
fi

# Wait for required services based on SERVICE_NAME
case "$SERVICE_NAME" in
    orchestrator)
        if [ "$SKIP_POSTGRES_WAIT" != "true" ]; then
            wait_for_service ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432} "PostgreSQL"
        fi
        wait_for_service ${REDIS_HOST:-redis} ${REDIS_PORT:-6379} "Redis"
        if [ "$SKIP_TEMPORAL_WAIT" != "true" ]; then
            wait_for_service ${TEMPORAL_HOST:-temporal} ${TEMPORAL_PORT:-7233} "Temporal"
        fi
        
        # Start temporal worker as background process
        echo "Starting integrated temporal worker..."
        python -m src.orchestrator.worker_production_db > /app/logs/temporal-worker.log 2>&1 &
        
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
        if [ "$SKIP_QDRANT_WAIT" != "true" ]; then
            wait_for_service ${QDRANT_HOST:-qdrant} ${QDRANT_PORT:-6333} "Qdrant"
        fi
        PORT=${PORT:-8003}
        MODULE="src.memory.main:app"
        ;;
    execution-sandbox)
        PORT=${PORT:-8004}
        MODULE="src.sandbox.main:app"
        ;;
    temporal-worker)
        # Parse TEMPORAL_HOST to extract hostname and port
        if [ "$SKIP_TEMPORAL_WAIT" != "true" ]; then
            TEMPORAL_HOST_VAR=${TEMPORAL_HOST:-temporal:7233}
            if [[ "$TEMPORAL_HOST_VAR" == *":"* ]]; then
                TEMPORAL_HOSTNAME=$(echo "$TEMPORAL_HOST_VAR" | cut -d':' -f1)
                TEMPORAL_PORT_VAR=$(echo "$TEMPORAL_HOST_VAR" | cut -d':' -f2)
            else
                TEMPORAL_HOSTNAME="$TEMPORAL_HOST_VAR"
                TEMPORAL_PORT_VAR=${TEMPORAL_PORT:-7233}
            fi
            wait_for_service "$TEMPORAL_HOSTNAME" "$TEMPORAL_PORT_VAR" "Temporal"
        fi
        if [ "$SKIP_POSTGRES_WAIT" != "true" ]; then
            wait_for_service ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432} "PostgreSQL"
        fi
        wait_for_service ${REDIS_HOST:-redis} ${REDIS_PORT:-6379} "Redis"
        
        # Check if enterprise mode is enabled
        if [ "$ENTERPRISE_MODE" = "true" ]; then
            echo "Starting ENTERPRISE Temporal worker with advanced reliability features..."
            echo "Features: Circuit breakers, parallel batching, checkpointing"
            exec python -m src.orchestrator.enterprise_worker
        else
            echo "Starting Standard Temporal worker with PostgreSQL persistence..."
            exec python -m src.orchestrator.worker_production_db
        fi
        ;;
    marketing-worker)
        # Parse TEMPORAL_HOST to extract hostname and port
        if [ "$SKIP_TEMPORAL_WAIT" != "true" ]; then
            TEMPORAL_HOST_VAR=${TEMPORAL_HOST:-temporal:7233}
            if [[ "$TEMPORAL_HOST_VAR" == *":"* ]]; then
                TEMPORAL_HOSTNAME=$(echo "$TEMPORAL_HOST_VAR" | cut -d':' -f1)
                TEMPORAL_PORT_VAR=$(echo "$TEMPORAL_HOST_VAR" | cut -d':' -f2)
            else
                TEMPORAL_HOSTNAME="$TEMPORAL_HOST_VAR"
                TEMPORAL_PORT_VAR=${TEMPORAL_PORT:-7233}
            fi
            wait_for_service "$TEMPORAL_HOSTNAME" "$TEMPORAL_PORT_VAR" "Temporal"
        fi
        echo "Starting Marketing Temporal worker..."
        exec python -m src.orchestrator.marketing_worker
        ;;
    *)
        echo "Unknown service: $SERVICE_NAME"
        exit 1
        ;;
esac

# Start the service
echo "Starting $SERVICE_NAME on port $PORT..."
exec python -m uvicorn $MODULE --host 0.0.0.0 --port $PORT