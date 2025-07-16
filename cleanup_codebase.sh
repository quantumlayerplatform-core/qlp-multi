#!/bin/bash

# QLP Codebase Cleanup Script
# This script helps clean up zombie and stale files identified in CLEANUP_REPORT.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== QLP Codebase Cleanup Script ===${NC}"
echo -e "${YELLOW}This script will help clean up zombie and stale files.${NC}"
echo -e "${YELLOW}Please review each action before confirming.${NC}\n"

# Function to ask for confirmation
confirm() {
    read -p "$1 [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# 1. Update .gitignore
echo -e "\n${GREEN}Step 1: Updating .gitignore${NC}"
if confirm "Add common ignore patterns to .gitignore?"; then
    cat >> .gitignore << 'EOF'

# OS Files
.DS_Store
Thumbs.db

# IDE Files
.idea/
.vscode/
*.swp
*.swo
*~

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/

# Logs
*.log
logs/

# Generated files
generated/
qlp-cli/generated/
workflow_id.txt
test_capsule.zip
unnamed_capsule_*/

# Test outputs
test-results/
coverage/
.coverage
htmlcov/
.pytest_cache/

# Environment
.env.local
.env.*.local

# Temporary files
*.tmp
*.temp
*.bak
*.old
EOF
    echo -e "${GREEN}✓ .gitignore updated${NC}"
else
    echo -e "${YELLOW}⚠ Skipped .gitignore update${NC}"
fi

# 2. Remove tracked files that should be ignored
echo -e "\n${GREEN}Step 2: Removing tracked files that should be ignored${NC}"
if confirm "Remove tracked files that should be in .gitignore?"; then
    # Remove OS/IDE files
    git rm -r --cached .idea/ 2>/dev/null || true
    git rm --cached .DS_Store 2>/dev/null || true
    
    # Remove temporary files
    git rm --cached workflow_id.txt 2>/dev/null || true
    git rm --cached test_capsule.zip 2>/dev/null || true
    git rm --cached enhanced_platform.log 2>/dev/null || true
    
    echo -e "${GREEN}✓ Removed tracked ignored files${NC}"
else
    echo -e "${YELLOW}⚠ Skipped removing tracked files${NC}"
fi

# 3. Check duplicate worker files
echo -e "\n${GREEN}Step 3: Checking duplicate worker files${NC}"
echo -e "${YELLOW}Found the following worker files:${NC}"
ls -lh src/orchestrator/worker*.py | awk '{print "  " $9 " (" $5 ")"}'

echo -e "\n${YELLOW}Active workers:${NC}"
echo "  - worker_production.py (main production worker)"
echo "  - worker_production_db.py (database wrapper)"
echo "  - enterprise_worker.py (enterprise features)"

echo -e "\n${YELLOW}Potentially unused workers:${NC}"
echo "  - worker.py"
echo "  - worker_prod.py"
echo "  - worker_production_enhanced.py"
echo "  - worker_production_fixed.py"

if confirm "Remove unused worker files?"; then
    git rm src/orchestrator/worker.py 2>/dev/null || echo "  worker.py already removed or not tracked"
    git rm src/orchestrator/worker_prod.py 2>/dev/null || echo "  worker_prod.py already removed or not tracked"
    git rm src/orchestrator/worker_production_enhanced.py 2>/dev/null || echo "  worker_production_enhanced.py already removed or not tracked"
    git rm src/orchestrator/worker_production_fixed.py 2>/dev/null || echo "  worker_production_fixed.py already removed or not tracked"
    echo -e "${GREEN}✓ Removed unused worker files${NC}"
else
    echo -e "${YELLOW}⚠ Skipped removing worker files${NC}"
fi

# 4. Complete deletion of removed files
echo -e "\n${GREEN}Step 4: Completing deletion of removed files${NC}"
if git status --porcelain | grep -q "^D.*enhanced_confidence_scorer.py"; then
    if confirm "Complete deletion of src/agents/enhanced_confidence_scorer.py?"; then
        git rm src/agents/enhanced_confidence_scorer.py
        echo -e "${GREEN}✓ Completed file deletion${NC}"
    fi
else
    echo -e "${BLUE}ℹ No pending deletions found${NC}"
fi

# 5. Organize test files
echo -e "\n${GREEN}Step 5: Organizing test files${NC}"
echo -e "${YELLOW}Found $(ls test_*.py 2>/dev/null | wc -l) test files in root directory${NC}"

if confirm "Create organized test directory structure?"; then
    mkdir -p tests/{unit,integration,e2e,performance,scripts}
    echo -e "${GREEN}✓ Created test directory structure${NC}"
    
    echo -e "\n${YELLOW}You can now manually move test files to appropriate directories:${NC}"
    echo "  - Unit tests → tests/unit/"
    echo "  - Integration tests → tests/integration/"
    echo "  - End-to-end tests → tests/e2e/"
    echo "  - Performance tests → tests/performance/"
    echo "  - Test scripts → tests/scripts/"
else
    echo -e "${YELLOW}⚠ Skipped test organization${NC}"
fi

# 6. Check for other cleanup opportunities
echo -e "\n${GREEN}Step 6: Other cleanup opportunities${NC}"

# Count similar files
echo -e "\n${YELLOW}GitHub integration files:${NC}"
ls -1 src/orchestrator/*github*.py 2>/dev/null | grep -v __pycache__ || true

echo -e "\n${YELLOW}Capsule-related files:${NC}"
ls -1 src/orchestrator/*capsule*.py 2>/dev/null | grep -v __pycache__ || true

echo -e "\n${YELLOW}Shell scripts in root:${NC}"
ls -1 *.sh 2>/dev/null | head -10

# 7. Summary
echo -e "\n${BLUE}=== Cleanup Summary ===${NC}"
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review the changes with: git status"
echo "2. Manually move test files to organized directories"
echo "3. Consider consolidating similar modules (GitHub, capsule, validation)"
echo "4. Commit the cleanup changes"
echo -e "\n${YELLOW}To commit cleanup changes:${NC}"
echo "  git add .gitignore"
echo "  git commit -m \"chore: Clean up zombie files and update .gitignore\""

# Check if there are generated directories
if [ -d "generated" ] || [ -d "qlp-cli/generated" ]; then
    echo -e "\n${YELLOW}Note: Generated directories still exist.${NC}"
    echo "Consider removing them with:"
    echo "  rm -rf generated/ qlp-cli/generated/"
fi

echo -e "\n${GREEN}✓ Cleanup script completed!${NC}"