#!/bin/bash

# Apply API URL fixes to the running QLP environment

echo "🔧 Applying API URL fixes to QLP environment..."

# Function to check if services are running
check_services() {
    echo "📋 Checking service status..."
    docker ps | grep -E "qlp-orchestrator|qlp-nginx" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Services are running"
        return 0
    else
        echo "❌ Services are not running"
        return 1
    fi
}

# Function to update environment variables
update_env() {
    echo "📝 Updating environment variables..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        echo "❌ .env file not found"
        return 1
    fi
    
    # Add API configuration if not present
    if ! grep -q "API_BASE_URL" .env; then
        echo "" >> .env
        echo "# API Configuration" >> .env
        echo "API_BASE_URL=" >> .env
        echo "ENVIRONMENT=development" >> .env
        echo "AUTO_DETECT_HOST=true" >> .env
        echo "ADDITIONAL_ALLOWED_ORIGINS=" >> .env
        echo "✅ Added API configuration to .env"
    else
        echo "✅ API configuration already exists in .env"
    fi
}

# Function to update nginx configuration
update_nginx() {
    echo "📝 Updating nginx configuration..."
    
    # Check if nginx-fixed.conf exists
    if [ ! -f nginx-fixed.conf ]; then
        echo "❌ nginx-fixed.conf not found"
        return 1
    fi
    
    # Update docker-compose to use nginx-fixed.conf
    if grep -q "./nginx.conf:/etc/nginx/nginx.conf" docker-compose.platform.yml; then
        echo "🔄 Updating docker-compose.platform.yml to use nginx-fixed.conf..."
        sed -i.bak 's|./nginx.conf:/etc/nginx/nginx.conf|./nginx-fixed.conf:/etc/nginx/nginx.conf|g' docker-compose.platform.yml
        echo "✅ Updated docker-compose.platform.yml"
    else
        echo "✅ docker-compose.platform.yml already configured correctly"
    fi
}

# Function to restart services
restart_services() {
    echo "🔄 Restarting services..."
    
    # Restart nginx to apply new configuration
    echo "  - Restarting nginx..."
    docker-compose -f docker-compose.platform.yml restart nginx
    
    # Optionally restart orchestrator if env changes require it
    echo "  - Restarting orchestrator..."
    docker-compose -f docker-compose.platform.yml restart orchestrator
    
    echo "✅ Services restarted"
}

# Function to verify the fixes
verify_fixes() {
    echo "🔍 Verifying fixes..."
    
    # Wait for services to be ready
    echo "  - Waiting for services to be ready..."
    sleep 10
    
    # Test API v2 endpoints
    echo "  - Testing API v2 docs endpoint..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v2/docs)
    if [ "$response" == "200" ]; then
        echo "  ✅ API v2 docs endpoint is working (HTTP $response)"
    else
        echo "  ❌ API v2 docs endpoint failed (HTTP $response)"
    fi
    
    # Test OpenAPI JSON endpoint
    echo "  - Testing OpenAPI JSON endpoint..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v2/openapi.json)
    if [ "$response" == "200" ]; then
        echo "  ✅ OpenAPI JSON endpoint is working (HTTP $response)"
    else
        echo "  ❌ OpenAPI JSON endpoint failed (HTTP $response)"
    fi
    
    # Test direct orchestrator access
    echo "  - Testing direct orchestrator access..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v2/docs)
    if [ "$response" == "200" ]; then
        echo "  ✅ Direct orchestrator access is working (HTTP $response)"
    else
        echo "  ❌ Direct orchestrator access failed (HTTP $response)"
    fi
}

# Main execution
main() {
    echo "🚀 Starting API URL fix application..."
    echo ""
    
    # Check if we're in the right directory
    if [ ! -f docker-compose.platform.yml ]; then
        echo "❌ Error: docker-compose.platform.yml not found. Please run this script from the qlp-multi directory."
        exit 1
    fi
    
    # Check if services are running
    if ! check_services; then
        echo "❌ Services are not running. Please start them first with: docker-compose -f docker-compose.platform.yml up -d"
        exit 1
    fi
    
    echo ""
    
    # Update environment
    update_env
    echo ""
    
    # Update nginx configuration
    update_nginx
    echo ""
    
    # Restart services
    restart_services
    echo ""
    
    # Verify fixes
    verify_fixes
    echo ""
    
    echo "✅ API URL fixes applied successfully!"
    echo ""
    echo "📌 You can now access:"
    echo "  - Swagger UI: http://localhost/api/v2/docs"
    echo "  - ReDoc: http://localhost/api/v2/redoc"
    echo "  - OpenAPI JSON: http://localhost/api/v2/openapi.json"
    echo ""
    echo "🔧 If you need to customize the API base URL, set API_BASE_URL in your .env file"
}

# Run main function
main