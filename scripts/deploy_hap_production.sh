#!/bin/bash
# HAP Production Deployment Script
# This script automates the deployment of HAP to production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${DOCKER_REGISTRY:-your-registry}"
IMAGE_NAME="${IMAGE_NAME:-qlp-platform}"
VERSION="${VERSION:-v2.1.0-hap}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-docker-compose}"  # docker-compose or kubernetes

echo -e "${GREEN}Starting HAP Production Deployment${NC}"
echo "Registry: $REGISTRY"
echo "Image: $IMAGE_NAME"
echo "Version: $VERSION"
echo "Deployment Type: $DEPLOYMENT_TYPE"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to apply database migrations
apply_migrations() {
    echo -e "${YELLOW}Applying database migrations...${NC}"
    
    if [ "$DEPLOYMENT_TYPE" = "docker-compose" ]; then
        # Docker Compose deployment
        if docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /migrations/004_create_hap_tables_fixed.sql; then
            echo -e "${GREEN}✓ Database migrations applied successfully${NC}"
        else
            echo -e "${RED}✗ Failed to apply database migrations${NC}"
            exit 1
        fi
    elif [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        # Kubernetes deployment
        POD=$(kubectl get pods -l app=postgres -o jsonpath='{.items[0].metadata.name}')
        kubectl cp migrations/004_create_hap_tables_fixed.sql $POD:/tmp/
        if kubectl exec $POD -- psql -U qlp_user -d qlp_db -f /tmp/004_create_hap_tables_fixed.sql; then
            echo -e "${GREEN}✓ Database migrations applied successfully${NC}"
        else
            echo -e "${RED}✗ Failed to apply database migrations${NC}"
            exit 1
        fi
    else
        # Direct database connection
        if [ -z "$DATABASE_URL" ]; then
            echo -e "${RED}DATABASE_URL not set for direct database connection${NC}"
            exit 1
        fi
        if psql $DATABASE_URL -f migrations/004_create_hap_tables_fixed.sql; then
            echo -e "${GREEN}✓ Database migrations applied successfully${NC}"
        else
            echo -e "${RED}✗ Failed to apply database migrations${NC}"
            exit 1
        fi
    fi
}

# Function to build and push Docker images
build_and_push_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    
    # Build the image
    if docker build -t $REGISTRY/$IMAGE_NAME:$VERSION -t $REGISTRY/$IMAGE_NAME:latest .; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build Docker image${NC}"
        exit 1
    fi
    
    # Push to registry
    echo -e "${YELLOW}Pushing images to registry...${NC}"
    if docker push $REGISTRY/$IMAGE_NAME:$VERSION && docker push $REGISTRY/$IMAGE_NAME:latest; then
        echo -e "${GREEN}✓ Images pushed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to push images${NC}"
        exit 1
    fi
}

# Function to update deployment
update_deployment() {
    echo -e "${YELLOW}Updating deployment...${NC}"
    
    if [ "$DEPLOYMENT_TYPE" = "docker-compose" ]; then
        # Create production override file
        cat > docker-compose.production.override.yml <<EOF
version: '3.8'

services:
  orchestrator:
    image: $REGISTRY/$IMAGE_NAME:$VERSION
    environment:
      HAP_ENABLED: "true"
      HAP_CACHE_TTL: "3600"
      HAP_LOG_VIOLATIONS: "true"
      HAP_BLOCK_SEVERITY: "HIGH"
      HAP_ML_ENABLED: "false"
      HAP_LLM_CHECKS: "false"
      HAP_MAX_CACHE_SIZE: "10000"
      HAP_BATCH_SIZE: "100"
      HAP_TIMEOUT_MS: "500"
EOF
        
        # Deploy with rolling update
        echo -e "${YELLOW}Performing rolling update...${NC}"
        docker-compose -f docker-compose.platform.yml -f docker-compose.production.override.yml up -d --no-deps --scale orchestrator=2 orchestrator
        sleep 30  # Wait for new instance to be healthy
        docker-compose -f docker-compose.platform.yml -f docker-compose.production.override.yml up -d --no-deps orchestrator
        
    elif [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        # Update Kubernetes deployment
        kubectl set image deployment/qlp-orchestrator orchestrator=$REGISTRY/$IMAGE_NAME:$VERSION
        
        # Update ConfigMap with HAP settings
        kubectl create configmap hap-config \
            --from-literal=HAP_ENABLED=true \
            --from-literal=HAP_CACHE_TTL=3600 \
            --from-literal=HAP_LOG_VIOLATIONS=true \
            --from-literal=HAP_BLOCK_SEVERITY=HIGH \
            --dry-run=client -o yaml | kubectl apply -f -
        
        # Wait for rollout
        kubectl rollout status deployment/qlp-orchestrator
    fi
    
    echo -e "${GREEN}✓ Deployment updated successfully${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}Verifying deployment...${NC}"
    
    # Wait a bit for services to start
    sleep 10
    
    # Check health endpoint
    if [ "$DEPLOYMENT_TYPE" = "docker-compose" ]; then
        HEALTH_URL="http://localhost:8000/health"
    else
        HEALTH_URL="https://api.your-domain.com/health"
    fi
    
    if curl -f -s $HEALTH_URL > /dev/null; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        exit 1
    fi
    
    # Test HAP endpoint
    echo -e "${YELLOW}Testing HAP functionality...${NC}"
    HAP_RESPONSE=$(curl -s -X POST ${HEALTH_URL%/health}/api/v2/hap/check \
        -H "Content-Type: application/json" \
        -d '{"content": "test content", "context": "user_request"}')
    
    if echo "$HAP_RESPONSE" | grep -q "severity"; then
        echo -e "${GREEN}✓ HAP endpoint working${NC}"
    else
        echo -e "${RED}✗ HAP endpoint not responding correctly${NC}"
        echo "Response: $HAP_RESPONSE"
    fi
    
    # Check violation logging
    echo -e "${YELLOW}Testing violation logging...${NC}"
    curl -s -X POST ${HEALTH_URL%/health}/execute \
        -H "Content-Type: application/json" \
        -d '{
            "tenant_id": "test",
            "user_id": "deployment_test",
            "description": "Test with inappropriate content for deployment verification"
        }' > /dev/null
    
    echo -e "${GREEN}✓ Deployment verification complete${NC}"
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${YELLOW}Setting up monitoring...${NC}"
    
    # Create monitoring queries file
    cat > hap_monitoring_queries.sql <<EOF
-- HAP Monitoring Queries
-- Run these periodically to monitor HAP system health

-- Violations in last hour
SELECT severity, count(*) as count
FROM hap_violations 
WHERE created_at > now() - interval '1 hour'
GROUP BY severity
ORDER BY severity;

-- Cache hit rate (run in Redis)
-- INFO stats

-- Average processing time
SELECT 
    date_trunc('minute', created_at) as minute,
    avg(processing_time_ms) as avg_ms,
    max(processing_time_ms) as max_ms
FROM hap_violations
WHERE created_at > now() - interval '10 minutes'
GROUP BY minute
ORDER BY minute DESC;

-- High risk users
SELECT * FROM hap_high_risk_users LIMIT 10;
EOF
    
    echo -e "${GREEN}✓ Monitoring queries created in hap_monitoring_queries.sql${NC}"
}

# Main deployment flow
main() {
    echo -e "${GREEN}=== HAP Production Deployment ===${NC}"
    
    # Pre-flight checks
    if [ "$DEPLOYMENT_TYPE" = "docker-compose" ] && ! command_exists docker-compose; then
        echo -e "${RED}docker-compose not found${NC}"
        exit 1
    fi
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ] && ! command_exists kubectl; then
        echo -e "${RED}kubectl not found${NC}"
        exit 1
    fi
    
    # Deployment steps
    read -p "Apply database migrations? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apply_migrations
    fi
    
    read -p "Build and push Docker images? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_and_push_images
    fi
    
    read -p "Update deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        update_deployment
    fi
    
    read -p "Verify deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        verify_deployment
    fi
    
    setup_monitoring
    
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Monitor logs: docker logs -f qlp-orchestrator | grep -i hap"
    echo "2. Check metrics using queries in hap_monitoring_queries.sql"
    echo "3. Review violations in database"
    echo "4. Adjust HAP_BLOCK_SEVERITY if needed"
}

# Run main function
main