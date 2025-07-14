#!/bin/bash
# Setup script for HAP integration

echo "🚀 Setting up HAP (Hate, Abuse, Profanity) Detection System"
echo "==========================================================="

# Check if services are running
if ! docker ps | grep -q qlp-postgres; then
    echo "❌ PostgreSQL is not running. Please start services first: ./start.sh"
    exit 1
fi

echo "✅ Services are running"

# Run database migration
echo ""
echo "📊 Creating HAP database tables..."
docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /migrations/004_create_hap_tables.sql 2>/dev/null || {
    # If the above fails, try copying the file first
    docker cp migrations/004_create_hap_tables.sql qlp-postgres:/tmp/
    docker exec qlp-postgres psql -U qlp_user -d qlp_db -f /tmp/004_create_hap_tables.sql
}

# Verify tables were created
echo ""
echo "🔍 Verifying HAP tables..."
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "\dt hap_*" | grep -E "hap_violations|hap_user_risk_scores"

if [ $? -eq 0 ]; then
    echo "✅ HAP tables created successfully"
else
    echo "❌ Failed to create HAP tables"
    exit 1
fi

# Install colorama for demos if not present
echo ""
echo "📦 Checking Python dependencies..."
if ! python -c "import colorama" 2>/dev/null; then
    echo "Installing colorama for colored output..."
    pip install colorama
fi

echo ""
echo "✨ HAP System Setup Complete!"
echo ""
echo "To see HAP in action:"
echo ""
echo "1. Run the interactive demo:"
echo "   python demo_hap_system.py"
echo ""
echo "2. Run the standalone tests:"
echo "   python test_hap_system.py"
echo ""
echo "3. Test with your running platform:"
echo "   python test_hap_platform_integration.py"
echo ""
echo "Note: For full platform integration, you'll need to update your"
echo "orchestrator and agent services to import and use the HAP modules."
echo "See docs/HAP_INTEGRATION_GUIDE.md for details."