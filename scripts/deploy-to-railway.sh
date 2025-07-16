#!/bin/bash

# Deploy QLP to Railway - Step by Step Guide
# This script helps deploy all QLP services to Railway

set -e

echo "🚂 QLP Railway Deployment Script"
echo "==============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}Railway CLI not found. Installing...${NC}"
    npm install -g @railway/cli
fi

# Function to deploy a service
deploy_service() {
    local service_name=$1
    local port=$2
    
    echo -e "\n${BLUE}Deploying ${service_name}...${NC}"
    
    # Create service-specific Dockerfile if needed
    if [ "$service_name" == "temporal-worker" ]; then
        # Temporal worker doesn't need a port
        railway up --service $service_name
    else
        # Set port for the service
        railway variables set PORT=$port --service $service_name
        railway up --service $service_name
    fi
    
    echo -e "${GREEN}✓ ${service_name} deployed${NC}"
}

# Step 1: Login to Railway
echo -e "${BLUE}Step 1: Login to Railway${NC}"
railway login

# Step 2: Create new project or link existing
echo -e "\n${BLUE}Step 2: Initialize Railway Project${NC}"
echo "Do you want to create a new project or link to existing? (new/existing)"
read -r project_choice

if [ "$project_choice" == "new" ]; then
    railway init
else
    echo "Please select your existing project from the Railway dashboard"
    railway link
fi

# Step 3: Add databases
echo -e "\n${BLUE}Step 3: Add Databases${NC}"
echo "Adding PostgreSQL..."
railway add postgresql

echo "Adding Redis..."
railway add redis

# Step 4: Set up environment variables
echo -e "\n${BLUE}Step 4: Setting up Environment Variables${NC}"
echo -e "${YELLOW}Please copy the contents of .env.railway.example to your Railway dashboard${NC}"
echo "Press enter when you've added the environment variables..."
read -r

# Step 5: Deploy services
echo -e "\n${BLUE}Step 5: Deploying Services${NC}"

# Deploy each service
services=(
    "orchestrator:8000"
    "agent-factory:8001"
    "validation-mesh:8002"
    "vector-memory:8003"
    "execution-sandbox:8004"
    "temporal-worker:0"
)

for service_info in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_info"
    deploy_service $service $port
done

# Step 6: Set up domains
echo -e "\n${BLUE}Step 6: Setting up Domains${NC}"
echo "Railway will provide domains like:"
echo "- orchestrator.up.railway.app"
echo "- agent-factory.up.railway.app"
echo "etc."
echo ""
echo "You can also add custom domains in the Railway dashboard"

# Step 7: Verify deployment
echo -e "\n${BLUE}Step 7: Verifying Deployment${NC}"
railway status

# Step 8: View logs
echo -e "\n${BLUE}Step 8: View Logs${NC}"
echo "To view logs for any service, use:"
echo "railway logs --service orchestrator"

# Step 9: Open dashboard
echo -e "\n${BLUE}Step 9: Opening Dashboard${NC}"
railway open

echo -e "\n${GREEN}🎉 Deployment Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Check the Railway dashboard for service URLs"
echo "2. Update your frontend to use the Railway URLs"
echo "3. Monitor usage and costs in the Railway dashboard"
echo "4. Set up GitHub integration for automatic deployments"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "- View logs: railway logs --service <service-name>"
echo "- Run commands: railway run --service <service-name> <command>"
echo "- Open console: railway shell --service <service-name>"
echo "- View status: railway status"
echo ""
echo -e "${BLUE}Cost Optimization Tips:${NC}"
echo "1. Enable sleep mode for development environments"
echo "2. Use Railway's cron jobs for scheduled tasks"
echo "3. Monitor resource usage and adjust limits"
echo "4. Consider moving databases to Supabase (free with credits)"