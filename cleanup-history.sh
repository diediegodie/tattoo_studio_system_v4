#!/bin/bash
# Git History Cleanup Script for tattoo_studio_system_v4
# WARNING: This script will rewrite git history. Run only after careful review.
# Date: October 10, 2025

set -e  # Exit on any error

echo "=========================================="
echo "Git History Cleanup - Sensitive Data Removal"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will rewrite git history!"
echo "⚠️  All commit hashes will change!"
echo "⚠️  Collaborators will need to re-clone!"
echo ""
read -p "Type 'YES' to continue: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Create backup branch
echo ""
echo "Step 1: Creating backup branch..."
git branch backup-before-secret-cleanup-$(date +%Y%m%d) || echo "Backup branch may already exist"

# Step 2: Verify git-filter-repo is installed
echo ""
echo "Step 2: Checking for git-filter-repo..."
if ! command -v git-filter-repo &> /dev/null; then
    echo "❌ git-filter-repo not found!"
    echo "Please install it first:"
    echo "  pip3 install git-filter-repo"
    echo "Or visit: https://github.com/newren/git-filter-repo"
    exit 1
fi
echo "✓ git-filter-repo is installed"

# Step 3: Remove sensitive files from history
echo ""
echo "Step 3: Removing sensitive files from git history..."
git filter-repo --force \
    --invert-paths \
    --path backend/backup_cliente_nullable_20250926_134042.dump \
    --path backups/pre_volume_recreate_20251010_120355.sql

# Step 4: Replace sensitive patterns in file contents
echo ""
echo "Step 4: Replacing sensitive patterns in commit history..."
if [ -f "replacements.txt" ]; then
    git filter-repo --force --replace-text replacements.txt
    echo "✓ Patterns replaced"
else
    echo "⚠️  replacements.txt not found, skipping pattern replacement"
fi

# Step 5: Clean up reflog and garbage collect
echo ""
echo "Step 5: Cleaning up git internals..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "=========================================="
echo "✓ History cleanup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review the changes with: git log --all --oneline | head -20"
echo "2. Verify sensitive data is gone (see verification commands below)"
echo "3. Re-add the remote: git remote add origin https://github.com/diediegodie/tattoo_studio_system_v4.git"
echo "4. Force push: git push --force --all"
echo "5. Force push tags: git push --force --tags"
echo ""
echo "IMPORTANT: Notify all collaborators to re-clone the repository!"
