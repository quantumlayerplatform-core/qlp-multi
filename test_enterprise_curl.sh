#!/bin/bash

# Enterprise test using curl commands
# Shows performance improvements with real-time monitoring

echo "🚀 Quantum Layer Platform - Enterprise Test with CURL"
echo "===================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Base URL
BASE_URL="http://localhost:8000"

# Function to monitor workflow
monitor_workflow() {
    local workflow_id=$1
    local start_time=$2
    
    echo -e "\n${BLUE}📊 Monitoring workflow: $workflow_id${NC}"
    echo "--------------------------------------------"
    
    local last_completed=0
    local status="running"
    
    while [ "$status" != "completed" ] && [ "$status" != "failed" ]; do
        # Get status
        response=$(curl -s "$BASE_URL/workflow/status/$workflow_id")
        
        if [ $? -eq 0 ]; then
            status=$(echo "$response" | jq -r '.status // "unknown"')
            tasks_completed=$(echo "$response" | jq -r '.tasks_completed // 0')
            tasks_total=$(echo "$response" | jq -r '.tasks_total // 0')
            
            # Show progress if changed
            if [ "$tasks_completed" -gt "$last_completed" ]; then
                current_time=$(date +%s)
                elapsed=$((current_time - start_time))
                
                echo -e "${GREEN}✓${NC} Progress: $tasks_completed/$tasks_total tasks completed ($(awk "BEGIN {printf \"%.1f\", $tasks_completed/$tasks_total*100}")%) - ${elapsed}s elapsed"
                
                # Show recently completed tasks
                outputs=$(echo "$response" | jq -r '.outputs[]?.task_id // empty' 2>/dev/null | tail -n 3)
                if [ ! -z "$outputs" ]; then
                    echo "$outputs" | while read -r task; do
                        echo "  └─ Completed: $task"
                    done
                fi
                
                last_completed=$tasks_completed
            fi
        fi
        
        sleep 3
    done
    
    # Final status
    current_time=$(date +%s)
    total_elapsed=$((current_time - start_time))
    
    echo ""
    if [ "$status" = "completed" ]; then
        echo -e "${GREEN}✅ Workflow completed successfully!${NC}"
        echo -e "   Total time: ${total_elapsed} seconds ($(awk "BEGIN {printf \"%.1f\", $total_elapsed/60}") minutes)"
        
        # Get final details
        capsule_id=$(echo "$response" | jq -r '.capsule_id // "none"')
        if [ "$capsule_id" != "none" ] && [ "$capsule_id" != "null" ]; then
            echo -e "   ${YELLOW}📦 Capsule ID: $capsule_id${NC}"
        fi
        
        # Performance analysis
        echo -e "\n${BLUE}📈 Performance Analysis:${NC}"
        
        # Check for cached tasks
        cached_count=$(echo "$response" | jq '[.outputs[]?.execution.metadata.cached // false] | map(select(. == true)) | length' 2>/dev/null || echo "0")
        echo "   • Cached tasks: $cached_count"
        
        # Calculate speedup
        if [ "$tasks_total" -gt 0 ]; then
            # Estimate sequential time (30s per task average)
            sequential_estimate=$((tasks_total * 30))
            speedup=$(awk "BEGIN {printf \"%.1f\", $sequential_estimate/$total_elapsed}")
            time_saved=$((sequential_estimate - total_elapsed))
            
            echo "   • Sequential estimate: ${sequential_estimate}s"
            echo "   • Parallel execution: ${total_elapsed}s"
            echo -e "   • ${GREEN}Speedup: ${speedup}x faster${NC}"
            echo -e "   • ${GREEN}Time saved: ${time_saved}s ($(awk "BEGIN {printf \"%.1f\", $time_saved/60}") minutes)${NC}"
        fi
        
    else
        echo -e "${RED}❌ Workflow failed!${NC}"
        echo "   Status: $status"
        errors=$(echo "$response" | jq -r '.errors[]? // empty' 2>/dev/null | head -n 3)
        if [ ! -z "$errors" ]; then
            echo "   Errors:"
            echo "$errors" | while read -r error; do
                echo "     • $error"
            done
        fi
    fi
    
    echo ""
}

# Main test
echo -e "${YELLOW}📋 Test Case: Enterprise E-Commerce Platform${NC}"
echo "Testing parallel execution, caching, and priority ordering"
echo ""

# Create request JSON
cat > /tmp/enterprise_request.json << 'EOF'
{
  "tenant_id": "test-enterprise",
  "user_id": "test-user-001",
  "description": "Create a production-ready REST API for an online bookstore with the following features: 1) Book catalog with CRUD operations, search, and filtering by genre, author, price 2) User authentication with JWT tokens and role-based access (admin, customer) 3) Shopping cart functionality with add, remove, update quantity 4) Order processing with status tracking 5) Customer reviews and ratings system 6) Inventory management with stock tracking 7) Recommendation engine for similar books 8) Admin dashboard API for managing books, orders, and users. Use Python FastAPI with PostgreSQL database, include comprehensive error handling, input validation, and unit tests for all endpoints.",
  "requirements": "Production-ready code with proper error handling, validation, and tests",
  "constraints": {
    "language": "python",
    "framework": "fastapi",
    "database": "postgresql",
    "include_tests": true
  },
  "metadata": {
    "project_type": "ecommerce_api",
    "priority": "high"
  }
}
EOF

echo -e "${BLUE}📤 Submitting enterprise request...${NC}"
echo "Request: Online bookstore platform with 8 major components"
echo ""

# Start timer
start_time=$(date +%s)

# Submit request
response=$(curl -s -X POST "$BASE_URL/execute" \
  -H "Content-Type: application/json" \
  -d @/tmp/enterprise_request.json)

# Check response
if [ $? -eq 0 ]; then
    workflow_id=$(echo "$response" | jq -r '.workflow_id // empty')
    
    if [ ! -z "$workflow_id" ] && [ "$workflow_id" != "null" ]; then
        echo -e "${GREEN}✅ Workflow started successfully${NC}"
        echo "   Workflow ID: $workflow_id"
        
        # Monitor the workflow
        monitor_workflow "$workflow_id" "$start_time"
        
        # Show how to download results
        echo -e "${BLUE}📥 To download the generated code:${NC}"
        echo "   curl -X GET $BASE_URL/workflow/status/$workflow_id"
        echo ""
        
    else
        echo -e "${RED}❌ Failed to start workflow${NC}"
        echo "Response: $response"
        
        # Try to parse error
        error=$(echo "$response" | jq -r '.error // .detail // "Unknown error"' 2>/dev/null || echo "$response")
        echo "Error: $error"
    fi
else
    echo -e "${RED}❌ Failed to connect to orchestrator${NC}"
    echo "Make sure services are running: ./start_all.sh"
fi

# Cleanup
rm -f /tmp/enterprise_request.json

echo ""
echo "Test complete!"