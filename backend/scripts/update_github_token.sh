#!/usr/bin/env bash
#
# Automated Service Token Regeneration and GitHub Secret Update
#
# This script:
# 1. Prompts for JWT_SECRET_KEY (secure, no echo)
# 2. Generates a new service account JWT token
# 3. Updates GitHub Secret EXTRATO_API_TOKEN
#
# Security: No secrets are logged or printed to console
#
# Usage:
#   bash backend/scripts/update_github_token.sh
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Repository configuration
REPO_OWNER="diediegodie"
REPO_NAME="tattoo_studio_system_v4"

# Detect script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
TOKEN_SCRIPT="$SCRIPT_DIR/generate_service_token.py"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Service Token Regeneration & GitHub Secret Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Validate prerequisites
echo "📋 Validating prerequisites..."

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Error: Python virtual environment not found at: $VENV_PYTHON${NC}"
    echo "   Please create the virtual environment first."
    exit 1
fi

if [ ! -f "$TOKEN_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Token generation script not found at: $TOKEN_SCRIPT${NC}"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ Error: GitHub CLI (gh) is not installed${NC}"
    echo "   Install it from: https://cli.github.com/"
    exit 1
fi

# Check GitHub CLI authentication
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI is not authenticated${NC}"
    echo "   Running: gh auth login"
    echo ""
    gh auth login
fi

echo -e "${GREEN}✓${NC} All prerequisites validated"
echo ""

# Step 2: Prompt for JWT_SECRET_KEY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔑 Secret Input Required"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Please paste the JWT_SECRET_KEY value from your Render environment."
echo "This will be used to sign the new service account token."
echo ""
echo -e "${YELLOW}⚠️  Input will be hidden (secure mode)${NC}"
echo ""

# Read secret without echoing
read -s -p "JWT_SECRET_KEY: " JWT_SECRET_KEY
echo ""
echo ""

# Validate input
if [ -z "$JWT_SECRET_KEY" ]; then
    echo -e "${RED}❌ Error: JWT_SECRET_KEY cannot be empty${NC}"
    exit 1
fi

if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo -e "${RED}❌ Error: JWT_SECRET_KEY must be at least 32 characters${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Secret key received and validated"
echo ""

# Step 3: Generate new service token
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔨 Generating Service Token"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Export JWT_SECRET_KEY for the python subprocess
export JWT_SECRET_KEY

# Generate token and extract only the JWT string
# Suppress stderr to avoid app initialization logs
echo "🔄 Running token generation script..."
NEW_TOKEN=$("$VENV_PYTHON" "$TOKEN_SCRIPT" 2>/dev/null | grep -Eo '^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')

# Validate token extraction
if [ -z "$NEW_TOKEN" ]; then
    echo -e "${RED}❌ Error: Failed to generate or extract JWT token${NC}"
    echo "   Check that the secret key is correct and the script runs successfully."
    exit 1
fi

# Validate token format (should have 3 parts separated by dots)
TOKEN_PARTS=$(echo "$NEW_TOKEN" | tr '.' '\n' | wc -l)
if [ "$TOKEN_PARTS" -ne 3 ]; then
    echo -e "${RED}❌ Error: Invalid JWT token format${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Service token generated successfully"
echo -e "   Token format: [header].[payload].[signature] (${#NEW_TOKEN} chars)"
echo ""

# Step 4: Update GitHub Secret
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Updating GitHub Secret"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔄 Updating EXTRATO_API_TOKEN in $REPO_OWNER/$REPO_NAME..."

# Update secret using stdin (more secure than command line arg)
if echo "$NEW_TOKEN" | gh secret set EXTRATO_API_TOKEN --repo "$REPO_OWNER/$REPO_NAME" 2>&1; then
    echo ""
    echo -e "${GREEN}✅ GitHub secret EXTRATO_API_TOKEN updated successfully${NC}"
else
    echo ""
    echo -e "${RED}❌ Error: Failed to update GitHub secret${NC}"
    echo "   Check your GitHub CLI permissions and repository access."
    exit 1
fi

# Clean up environment
unset JWT_SECRET_KEY
unset NEW_TOKEN

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Process Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. GitHub Actions workflows can now use the updated token"
echo "  2. Test the workflow: .github/workflows/monthly_extrato_backup.yml"
echo "  3. Manual trigger: gh workflow run monthly_extrato_backup.yml"
echo ""
echo "🔒 Security notes:"
echo "  • Token has admin privileges"
echo "  • Expires in ~2 years (check token generation script output)"
echo "  • Rotate before expiration"
echo ""
