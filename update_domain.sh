#!/bin/bash

# Domain Update Script: quantumlayer.com → quantumlayerplatform.com
# This script updates all occurrences of quantumlayer.com to quantumlayerplatform.com

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Domain Update Script${NC}"
echo -e "${GREEN}=====================${NC}"
echo "This script will update quantumlayer.com to quantumlayerplatform.com"
echo ""

# Create backup directory
BACKUP_DIR="domain_update_backup_$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}Creating backup directory: $BACKUP_DIR${NC}"
mkdir -p "$BACKUP_DIR"

# List of files to update
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

# Function to update a single file
update_file() {
    local file="$1"
    
    if [ -f "$file" ]; then
        echo -e "${YELLOW}Processing: $file${NC}"
        
        # Create backup
        cp "$file" "$BACKUP_DIR/$(basename "$file").bak"
        
        # Perform replacements
        # Use different delimiter for sed to avoid conflicts with URLs
        sed -i.tmp \
            -e 's|quantumlayer\.com|quantumlayerplatform.com|g' \
            -e 's|@quantumlayer\.com|@quantumlayerplatform.com|g' \
            "$file"
        
        # Remove temporary file created by sed
        rm -f "$file.tmp"
        
        echo -e "${GREEN}✓ Updated: $file${NC}"
    else
        echo -e "${RED}✗ File not found: $file${NC}"
    fi
}

# Function to show preview of changes
preview_changes() {
    local file="$1"
    
    if [ -f "$file" ]; then
        echo -e "\n${YELLOW}Preview for $file:${NC}"
        grep -n "quantumlayer\.com" "$file" 2>/dev/null || echo "No occurrences found"
    fi
}

# Ask for confirmation
echo ""
echo -e "${YELLOW}This will update all occurrences of:${NC}"
echo "  quantumlayer.com → quantumlayerplatform.com"
echo "  Including subdomains and email addresses"
echo ""
echo -e "${YELLOW}Files to be updated:${NC}"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        count=$(grep -c "quantumlayer\.com" "$file" 2>/dev/null || echo "0")
        if [ "$count" -gt 0 ]; then
            echo "  ✓ $file ($count occurrences)"
        fi
    fi
done

echo ""
read -p "Do you want to preview the changes first? (y/n): " preview_choice

if [[ $preview_choice =~ ^[Yy]$ ]]; then
    echo -e "\n${GREEN}Preview of changes:${NC}"
    for file in "${FILES[@]}"; do
        preview_changes "$file"
    done
    echo ""
    read -p "Continue with the update? (y/n): " continue_choice
    if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
        echo -e "${RED}Update cancelled.${NC}"
        exit 0
    fi
else
    read -p "Are you sure you want to proceed? (y/n): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo -e "${RED}Update cancelled.${NC}"
        exit 0
    fi
fi

# Perform the updates
echo -e "\n${GREEN}Starting updates...${NC}"
for file in "${FILES[@]}"; do
    update_file "$file"
done

# Update any additional .env files that might exist
echo -e "\n${YELLOW}Checking for additional .env files...${NC}"
for env_file in .env .env.local .env.development .env.staging; do
    if [ -f "$env_file" ] && grep -q "quantumlayer\.com" "$env_file" 2>/dev/null; then
        echo -e "${YELLOW}Found additional env file: $env_file${NC}"
        update_file "$env_file"
    fi
done

# Summary
echo -e "\n${GREEN}Update Summary:${NC}"
echo -e "${GREEN}===============${NC}"
echo "✓ Backup created in: $BACKUP_DIR"
echo "✓ All files have been updated"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review the changes using git diff"
echo "2. Test the application with the new domain"
echo "3. Update DNS records for the new domain"
echo "4. Update any external services (OAuth, webhooks, etc.)"
echo "5. Update SSL certificates for the new domain"
echo ""
echo -e "${YELLOW}To restore from backup:${NC}"
echo "cp $BACKUP_DIR/*.bak ."
echo ""
echo -e "${GREEN}Domain update completed successfully!${NC}"