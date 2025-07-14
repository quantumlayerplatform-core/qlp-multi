#!/bin/bash

# Start Marketing Temporal Worker

echo "Starting Marketing Temporal Worker..."

# Source virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Export necessary environment variables
export TEMPORAL_HOST="${TEMPORAL_HOST:-localhost:7233}"
export TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-default}"

# Check if Temporal is running
if ! nc -z localhost 7233 2>/dev/null; then
    echo "Warning: Temporal server not detected on localhost:7233"
    echo "Please ensure Temporal is running before starting the worker"
fi

# Start the marketing workflow worker
echo "Starting marketing workflow worker on task queue 'marketing-queue'..."
python -m src.orchestrator.marketing_workflow

# Keep the script running
wait