#!/bin/bash

# Create backup directory
BACKUP_DIR="domain_update_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Files to update
FILES=(
    "API_URL_FIX_SUMMARY.md"
    "docs/ADVANCED_FEATURES_GUIDE.md"
    "docs/API_MIGRATION_GUIDE.md"
    "docs/API_V2_MIGRATION_GUIDE.md"
    "docs/PRODUCTION_API_GUIDE.md"
    "docs/PRODUCTION_DEPLOYMENT_GUIDE.md"
    "get_clerk_token.md"
    "client/python/README.md"
    "client/javascript/README.md"
    "src/api/v2/api_config.py"
    "src/api/v2/openapi.py"
    "src/api/v2/middleware.py"
    "src/common/clerk_auth.py"
    "client/python/qlp_client.py"
    "client/python/setup.py"
    "client/javascript/src/index.ts"
    "test_cost_with_clerk.py"
    "test_cost_auth_production.py"
    "src/api/v2/API_CONFIG_README.md"
    ".env.api.example"
    ".env.production"
)

# Copy files to backup
echo "Backing up files..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "  Backed up: $file"
    fi
done

# Update domains
echo -e "\nUpdating domains..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        # Update all variations
        sed -i.bak 's/quantumlayer\.com/quantumlayerplatform.com/g' "$file"
        rm -f "${file}.bak"
        echo "  Updated: $file"
    fi
done

echo -e "\n✅ Domain update complete!"
echo "Backup created in: $BACKUP_DIR"
echo -e "\nNext steps:"
echo "1. Update your .env file with new domain"
echo "2. Restart services: docker-compose restart"
echo "3. Update external services (DNS, SSL, OAuth)"