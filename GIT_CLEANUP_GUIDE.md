# Git History Cleanup Guide
## Removing Sensitive Data Before GitHub Push

---

## 📋 Overview

This repository contains sensitive data in its git history that must be removed before pushing to GitHub. This guide provides step-by-step commands to safely rewrite history.

---

## ⚠️ CRITICAL WARNINGS

1. **History rewriting changes all commit hashes**
2. **All collaborators must re-clone after this operation**
3. **Any secrets found in removed files should be considered compromised**
4. **Create backups before proceeding**
5. **Do NOT modify .env files in your working tree - they remain unchanged**

---

## 🔍 What Was Found

### Files to Remove:
- `backend/backup_cliente_nullable_20250926_134042.dump`
- `backups/pre_volume_recreate_20251010_120355.sql`

### Patterns to Redact:
- Database URLs with credentials
- API keys (Google, Jotform)
- Flask secret keys
- Password strings

---

## 📝 Step-by-Step Commands

### **Step 1: Create Backup**

```bash
cd /home/diego/documentos/github/projetos/tattoo_studio_system_v4

# Create backup branch
git branch backup-before-secret-cleanup-20251010

# Optional: Create a complete backup outside git
cd ..
cp -r tattoo_studio_system_v4 tattoo_studio_system_v4.backup
cd tattoo_studio_system_v4
```

---

### **Step 2: Install git-filter-repo (if not installed)**

```bash
# Check if already installed
git-filter-repo --version

# If not installed, install via pip
pip3 install git-filter-repo

# Or on Ubuntu/Debian
sudo apt-get install git-filter-repo

# Or download directly
curl -o git-filter-repo https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo
chmod +x git-filter-repo
sudo mv git-filter-repo /usr/local/bin/
```

---

### **Step 3: Remove Sensitive Files from History**

```bash
# Remove specific files from all commits
git filter-repo --force \
    --invert-paths \
    --path backend/backup_cliente_nullable_20250926_134042.dump \
    --path backups/pre_volume_recreate_20251010_120355.sql
```

---

### **Step 4: Replace Sensitive Patterns (Optional but Recommended)**

```bash
# The replacements.txt file is already created
# Review it to ensure it matches your needs (DO NOT add real secrets to it!)

# Apply pattern replacements
git filter-repo --force --replace-text replacements.txt
```

---

### **Step 5: Clean Up Git Internals**

```bash
# Expire all reflog entries
git reflog expire --expire=now --all

# Aggressive garbage collection
git gc --prune=now --aggressive
```

---

### **Step 6: Update .gitignore and Commit Changes**

```bash
# The .gitignore has already been updated
# Stage the changes
git add .gitignore docs/SECURITY_CLEANUP.md

# Commit the security improvements
git commit -m "security: Remove sensitive data from history and improve .gitignore

- Removed database backup files from history
- Added comprehensive .gitignore rules for sensitive files
- Documented security cleanup process
- All secrets should be rotated as a precaution"
```

---

### **Step 7: Re-add Remote and Force Push**

```bash
# Re-add the remote (git-filter-repo removes it)
git remote add origin https://github.com/diediegodie/tattoo_studio_system_v4.git

# Force push all branches
git push --force --all

# Force push all tags
git push --force --tags
```

---

## ✅ Verification Steps

### Verify Files Are Gone:

```bash
# Check if sensitive files still exist in history
git log --all --full-history -- backend/backup_cliente_nullable_20250926_134042.dump
git log --all --full-history -- backups/pre_volume_recreate_20251010_120355.sql

# Should return nothing if successful
```

### Search for Sensitive Patterns:

```bash
# Search for database credentials
git log --all -p | grep -i "postgresql://" | head -5

# Search for API keys
git log --all -p | grep -i "JOTFORM_API_KEY" | head -5
git log --all -p | grep -i "GOOGLE_CLIENT_SECRET" | head -5

# If these return nothing, the cleanup was successful
```

### Verify on Fresh Clone:

```bash
# Clone in a temporary location
cd /tmp
git clone https://github.com/diediegodie/tattoo_studio_system_v4.git test-clone
cd test-clone

# Search for sensitive patterns
git log --all -p | grep -i "password" | head -5
git grep -i "postgresql://" $(git rev-list --all)

# Clean up
cd ..
rm -rf test-clone
```

---

## 🔄 Alternative Method: Using BFG Repo-Cleaner

If git-filter-repo doesn't work, use BFG as a fallback:

```bash
# Download BFG
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# Remove files
java -jar bfg-1.14.0.jar --delete-files "*.dump" .
java -jar bfg-1.14.0.jar --delete-files "*.sql" .

# Replace patterns
java -jar bfg-1.14.0.jar --replace-text replacements.txt .

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force --all
git push --force --tags
```

---

## 👥 For Collaborators

If you have an existing clone of this repository:

```bash
# Save any uncommitted work
git stash

# Remove your local copy
cd ..
rm -rf tattoo_studio_system_v4

# Fresh clone
git clone https://github.com/diediegodie/tattoo_studio_system_v4.git
cd tattoo_studio_system_v4

# Restore work if needed
git stash pop
```

---

## 🔐 Security Rotation Checklist

After removing sensitive data from history, rotate these secrets:

- [ ] **Database passwords** (PostgreSQL)
- [ ] **Google OAuth credentials**
  - Client ID
  - Client Secret
- [ ] **Jotform API key**
- [ ] **Google Calendar API key**
- [ ] **Flask secret key**
- [ ] Any credentials in removed backup files
- [ ] Review and rotate any other API tokens

Store new secrets in:
1. Local `.env` file (git-ignored)
2. Secure vault (Azure Key Vault, AWS Secrets Manager, etc.)
3. Environment variables on production servers

---

## 📊 Quick Reference Commands

```bash
# Backup
git branch backup-before-secret-cleanup-$(date +%Y%m%d)

# Remove files
git filter-repo --force --invert-paths --path <file-to-remove>

# Replace patterns
git filter-repo --force --replace-text replacements.txt

# Clean up
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Push
git remote add origin <url>
git push --force --all
git push --force --tags

# Verify
git log --all --full-history -- <removed-file>
```

---

## 🆘 Troubleshooting

### "fatal: not a valid object name"
This is normal after history rewrite. Ignore it.

### "remote: Permission denied"
Ensure you have push access to the GitHub repository.

### "refusing to merge unrelated histories"
Expected after force push. Collaborators should re-clone, not pull.

### Want to undo?
Restore from backup branch:
```bash
git reset --hard backup-before-secret-cleanup-20251010
```

---

## 📞 Need Help?

- **git-filter-repo docs**: https://github.com/newren/git-filter-repo
- **BFG docs**: https://rtyley.github.io/bfg-repo-cleaner/
- **GitHub removing sensitive data**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

---

**Last Updated:** October 10, 2025
