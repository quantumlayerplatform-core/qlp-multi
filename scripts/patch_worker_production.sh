#!/bin/bash
# Patch the running temporal worker to use database persistence

echo "🔧 Patching Temporal Worker for PostgreSQL Persistence"
echo "====================================================="

# Check if container is running
if ! docker ps | grep -q qlp-temporal-worker; then
    echo "❌ Temporal worker container is not running"
    exit 1
fi

echo "📝 Creating patch file in container..."
docker exec qlp-temporal-worker bash -c 'cat > /tmp/worker_patch.py << "EOF"
import sys
sys.path.insert(0, "/app")

# Import the database-enabled activity
from src.orchestrator.activities.capsule_activities import create_ql_capsule_activity_with_db

# Patch the worker_production module
import src.orchestrator.worker_production as wp
wp.create_ql_capsule_activity = create_ql_capsule_activity_with_db

# Update the activities list
for i, activity in enumerate(wp.activities):
    if hasattr(activity, "__name__") and activity.__name__ == "create_ql_capsule_activity":
        wp.activities[i] = create_ql_capsule_activity_with_db
        break

print("✅ Worker patched for PostgreSQL storage")

# Continue with normal execution
if __name__ == "__main__":
    from src.orchestrator.worker_production import main
    main()
EOF'

echo "🔄 Restarting worker with patch..."
docker exec qlp-temporal-worker pkill -f "python -m src.orchestrator.worker_production"
sleep 2

# Start the patched worker
docker exec -d qlp-temporal-worker python /tmp/worker_patch.py

echo "⏳ Waiting for worker to start..."
sleep 5

echo "✅ Worker patched and running with PostgreSQL persistence!"
echo ""
echo "📊 Check logs with: docker logs -f qlp-temporal-worker"