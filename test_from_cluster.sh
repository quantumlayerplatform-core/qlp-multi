#!/bin/bash
# Script to test from inside the Kubernetes cluster
# This simulates what your worker actually does

echo "🚀 Testing from inside Kubernetes cluster"
echo "=============================================="

# Run a test pod inside the cluster to check services
kubectl run debug-test --rm -i --tty \
  --image=curlimages/curl:latest \
  --namespace=qlp-production \
  --restart=Never \
  -- sh -c "
echo '1️⃣ Testing orchestrator health...'
curl -s http://qlp-orchestrator:8000/health || echo 'Health check failed'

echo -e '\n2️⃣ Testing vector-memory health...'
curl -s http://vector-memory-svc:8003/health || echo 'Vector memory health check failed'

echo -e '\n3️⃣ Testing decompose endpoint...'
curl -X POST http://qlp-orchestrator:8000/decompose/unified-optimization \
  -H 'Content-Type: application/json' \
  -d '{\"description\": \"test\", \"similar_requests\": []}' \
  -w 'HTTP Status: %{http_code}\n' || echo 'Decompose test failed'

echo -e '\n4️⃣ Testing vector memory search (simulating worker)...'
curl -X POST http://vector-memory-svc:8003/search/requests \
  -H 'Content-Type: application/json' \
  -d '{\"description\": \"test\", \"limit\": 1}' \
  -w 'HTTP Status: %{http_code}\n' || echo 'Vector search failed'
"
