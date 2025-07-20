#!/bin/bash

# Verify API URLs are working correctly

echo "🔍 Verifying QLP API URLs..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local url=$1
    local description=$2
    
    printf "Testing %-50s" "$description:"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" == "200" ] || [ "$response" == "301" ] || [ "$response" == "302" ]; then
        echo -e "${GREEN}✅ OK (HTTP $response)${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL (HTTP $response)${NC}"
        return 1
    fi
}

# Function to test API servers in OpenAPI
test_openapi_servers() {
    echo ""
    echo "📋 Checking OpenAPI server configuration..."
    
    # Get OpenAPI JSON
    openapi_json=$(curl -s http://localhost/api/v2/openapi.json 2>/dev/null)
    
    if [ -z "$openapi_json" ]; then
        echo -e "${RED}❌ Failed to fetch OpenAPI JSON${NC}"
        return 1
    fi
    
    # Extract servers using Python (more reliable than bash parsing)
    servers=$(echo "$openapi_json" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    servers = data.get('servers', [])
    for server in servers:
        print(f'{server.get(\"url\", \"\")}|{server.get(\"description\", \"\")}')
except:
    pass
" 2>/dev/null)
    
    if [ -z "$servers" ]; then
        echo -e "${YELLOW}⚠️  No servers found in OpenAPI configuration${NC}"
    else
        echo "Found servers in OpenAPI:"
        echo "$servers" | while IFS='|' read -r url desc; do
            if [ -n "$url" ]; then
                echo "  - $url ($desc)"
            fi
        done
    fi
}

# Main tests
echo "🌐 Testing via Nginx (port 80)..."
echo "================================"
test_endpoint "http://localhost/health" "Health check"
test_endpoint "http://localhost/api/v2/docs" "API v2 Swagger UI"
test_endpoint "http://localhost/api/v2/redoc" "API v2 ReDoc"
test_endpoint "http://localhost/api/v2/openapi.json" "API v2 OpenAPI JSON"
test_endpoint "http://localhost/api/v2/health" "API v2 Health"
test_endpoint "http://localhost/docs" "Docs redirect"

echo ""
echo "🔌 Testing Direct Service Access..."
echo "==================================="
test_endpoint "http://localhost:8000/api/v2/docs" "Orchestrator API v2 docs"
test_endpoint "http://localhost:8000/api/v2/openapi.json" "Orchestrator OpenAPI JSON"
test_endpoint "http://localhost:8000/health" "Orchestrator health"
test_endpoint "http://localhost:8001/health" "Agent Factory health"
test_endpoint "http://localhost:8002/health" "Validation Mesh health"
test_endpoint "http://localhost:8003/health" "Vector Memory health"
test_endpoint "http://localhost:8004/health" "Execution Sandbox health"

echo ""
echo "🔧 Testing Legacy Endpoints..."
echo "=============================="
test_endpoint "http://localhost/execute" "Execute endpoint"
test_endpoint "http://localhost/api/v1/orchestrator/health" "Legacy v1 health"

# Test OpenAPI servers
test_openapi_servers

echo ""
echo "📊 Summary"
echo "========="
echo "If all tests show ✅, your API URLs are configured correctly."
echo "If you see ❌, check the service logs with: docker logs <container-name>"
echo ""
echo "🔍 Quick debugging commands:"
echo "  - Check nginx logs: docker logs qlp-nginx"
echo "  - Check orchestrator logs: docker logs qlp-orchestrator"
echo "  - Inspect nginx config: docker exec qlp-nginx cat /etc/nginx/nginx.conf"
echo "  - Test from inside container: docker exec qlp-orchestrator curl http://localhost:8000/health"