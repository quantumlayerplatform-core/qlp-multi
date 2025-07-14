#!/bin/bash
# Script to integrate HAP into the QuantumLayer Platform

echo "🚀 Integrating HAP into QuantumLayer Platform"
echo "============================================="

# Check if running from correct directory
if [ ! -f "src/orchestrator/main.py" ]; then
    echo "❌ Error: Must run from qlp-dev root directory"
    exit 1
fi

# Function to apply a patch with error handling
apply_patch() {
    local patch_file=$1
    local target_file=$2
    local patch_name=$(basename $patch_file .patch)
    
    echo ""
    echo "📝 Applying patch: $patch_name"
    
    # Check if target file exists
    if [ ! -f "$target_file" ]; then
        echo "❌ Target file not found: $target_file"
        return 1
    fi
    
    # Create backup
    cp "$target_file" "${target_file}.bak"
    
    # Try to apply patch
    if patch -p1 --dry-run < "$patch_file" >/dev/null 2>&1; then
        patch -p1 < "$patch_file"
        echo "✅ Successfully applied $patch_name"
        return 0
    else
        echo "⚠️  Patch $patch_name cannot be applied automatically"
        echo "   Please review $patch_file and apply manually"
        return 1
    fi
}

# Create patches directory if it doesn't exist
if [ ! -d "integration_patches" ]; then
    echo "❌ Integration patches directory not found"
    echo "   Please ensure you have the HAP integration patches"
    exit 1
fi

# Step 1: Database setup
echo ""
echo "📊 Step 1: Setting up HAP database tables..."
if docker ps | grep -q qlp-postgres; then
    docker cp migrations/004_create_hap_tables.sql qlp-postgres:/tmp/ 2>/dev/null || {
        echo "⚠️  Migration file not found, skipping database setup"
    }
    
    docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /tmp/004_create_hap_tables.sql 2>/dev/null && {
        echo "✅ HAP tables created successfully"
    } || {
        echo "⚠️  Could not create HAP tables (may already exist)"
    }
else
    echo "⚠️  PostgreSQL not running, skipping database setup"
fi

# Step 2: Apply code patches
echo ""
echo "📝 Step 2: Applying code patches..."

# List of patches to apply
declare -A patches=(
    ["01_orchestrator_hap.patch"]="src/orchestrator/production_endpoints.py"
    ["02_worker_hap.patch"]="src/orchestrator/worker_production.py"
    ["03_agent_factory_hap.patch"]="src/agents/agent_factory.py"
    ["04_validation_hap.patch"]="src/validation/enhanced_validation_service.py"
    ["05_main_hap.patch"]="src/orchestrator/main.py"
    ["06_docker_compose_hap.patch"]="docker-compose.platform.yml"
)

patch_count=0
success_count=0

for patch in "${!patches[@]}"; do
    ((patch_count++))
    if apply_patch "integration_patches/$patch" "${patches[$patch]}"; then
        ((success_count++))
    fi
done

echo ""
echo "📊 Patch Summary: $success_count/$patch_count patches applied successfully"

# Step 3: Install Python dependencies
echo ""
echo "📦 Step 3: Checking Python dependencies..."
if ! python -c "import colorama" 2>/dev/null; then
    echo "Installing colorama for demos..."
    pip install colorama
fi

# Step 4: Rebuild services if patches were applied
if [ $success_count -gt 0 ]; then
    echo ""
    echo "🔨 Step 4: Rebuilding services..."
    echo "This will take a few minutes..."
    
    docker-compose -f docker-compose.platform.yml build orchestrator agent-factory validation-mesh
    
    echo ""
    echo "🔄 Restarting services..."
    docker-compose -f docker-compose.platform.yml restart orchestrator agent-factory validation-mesh
else
    echo ""
    echo "⚠️  No patches were applied, skipping rebuild"
fi

# Step 5: Verify integration
echo ""
echo "🔍 Step 5: Verifying HAP integration..."

# Check if HAP endpoints are available
sleep 5  # Give services time to restart
if curl -s http://localhost:8000/api/v2/hap/health >/dev/null 2>&1; then
    echo "✅ HAP endpoints are available"
else
    echo "⚠️  HAP endpoints not responding (services may still be starting)"
fi

# Final summary
echo ""
echo "🎉 HAP Integration Complete!"
echo ""
echo "Next steps:"
echo "1. Test HAP functionality:"
echo "   python demo_hap_system.py"
echo ""
echo "2. Run integration tests:"
echo "   python test_hap_platform_integration.py"
echo ""
echo "3. Monitor logs:"
echo "   tail -f logs/orchestrator.log | grep HAP"
echo ""
echo "4. Check API documentation:"
echo "   http://localhost:8000/docs#/HAP"
echo ""

if [ $success_count -lt $patch_count ]; then
    echo "⚠️  Some patches could not be applied automatically."
    echo "   Please review the patches in integration_patches/ and apply manually."
    echo "   Backup files created with .bak extension"
fi