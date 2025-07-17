#!/bin/bash
set -e

echo "🚀 Quick Cloud Services Test & Migration"
echo "========================================"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test Python environment
if ! python3 -c "import psycopg2" 2>/dev/null; then
    echo -e "${YELLOW}Installing required Python packages...${NC}"
    pip install psycopg2-binary qdrant-client python-dotenv requests
fi

# Run the test
echo -e "\n${GREEN}Testing cloud connections...${NC}"
python3 test_cloud_services.py

# Backup local data
echo -e "\n${GREEN}Backing up local data...${NC}"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
if docker ps | grep -q qlp-postgres; then
    echo "Backing up PostgreSQL..."
    docker exec qlp-postgres pg_dump -U qlp_user qlp_db > $BACKUP_DIR/postgres_backup.sql
    echo -e "${GREEN}✓${NC} PostgreSQL backup saved"
fi

# Show next steps
echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Copy .env to .env.backup for safety:"
echo "   cp .env .env.backup"
echo ""
echo "2. Use cloud services configuration:"
echo "   cp .env.cloud .env"
echo ""
echo "3. Stop current services:"
echo "   docker-compose -f docker-compose.platform.yml down"
echo ""
echo "4. Start with cloud services:"
echo "   docker-compose -f docker-compose.cloud-services.yml up -d"
echo ""
echo "5. Test the services:"
echo "   curl http://localhost:8000/health"
echo ""
echo -e "${YELLOW}Note: Keep your local services running until you verify cloud services work!${NC}"