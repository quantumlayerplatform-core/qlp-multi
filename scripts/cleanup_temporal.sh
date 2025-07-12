#!/bin/bash

echo "🧹 Temporal Workflow Cleanup Script"
echo "===================================="

# Function to check if Temporal is accessible
check_temporal() {
    docker exec qlp-temporal temporal --address temporal:7233 workflow list -q 'ExecutionStatus="Running"' > /dev/null 2>&1
    return $?
}

# Check if Temporal is running
if ! check_temporal; then
    echo "❌ Cannot connect to Temporal. Make sure the container is running."
    exit 1
fi

# List running workflows
echo -e "\n📋 Checking for running workflows..."
RUNNING_WORKFLOWS=$(docker exec qlp-temporal temporal --address temporal:7233 workflow list -q 'ExecutionStatus="Running"' | tail -n +2)

if [ -z "$RUNNING_WORKFLOWS" ]; then
    echo "✅ No running workflows found."
    exit 0
fi

# Count workflows
WORKFLOW_COUNT=$(echo "$RUNNING_WORKFLOWS" | wc -l)
echo "Found $WORKFLOW_COUNT running workflow(s):"
echo "$RUNNING_WORKFLOWS"

# Check for stuck workflows (running > 1 hour)
echo -e "\n🔍 Checking for stuck workflows (running > 1 hour)..."
CURRENT_TIME=$(date +%s)
STUCK_WORKFLOWS=""

while IFS= read -r line; do
    if [ ! -z "$line" ]; then
        WORKFLOW_ID=$(echo "$line" | awk '{print $2}')
        START_TIME=$(echo "$line" | awk '{print $4, $5, $6}')
        
        # Show workflow info
        echo -e "\nWorkflow: $WORKFLOW_ID"
        echo "Started: $START_TIME"
        
        # Add to stuck list (for now, we'll consider all GitHub workflows as potentially stuck)
        if [[ $WORKFLOW_ID == qlp-github-* ]]; then
            echo "⚠️  GitHub workflow - may be stuck"
            STUCK_WORKFLOWS="$STUCK_WORKFLOWS $WORKFLOW_ID"
        fi
    fi
done <<< "$RUNNING_WORKFLOWS"

# Offer to terminate stuck workflows
if [ ! -z "$STUCK_WORKFLOWS" ]; then
    echo -e "\n⚠️  Found potentially stuck workflows."
    echo "Do you want to terminate them? (y/n)"
    read -r RESPONSE
    
    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        for WF_ID in $STUCK_WORKFLOWS; do
            echo "Terminating $WF_ID..."
            docker exec qlp-temporal temporal --address temporal:7233 workflow terminate -w "$WF_ID"
        done
        echo "✅ Workflows terminated."
    else
        echo "ℹ️  No workflows terminated."
    fi
else
    echo -e "\n✅ No stuck workflows detected."
fi

echo -e "\n===================================="
echo "Cleanup complete!"