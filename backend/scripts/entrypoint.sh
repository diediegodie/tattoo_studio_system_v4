#!/bin/bash
# Security entrypoint script for Tattoo Studio System
# Prevents accidental use of production credentials in test mode

set -e

# Define production-like password patterns to detect
# Add more patterns as needed for your environment
PROD_PASSWORD_PATTERNS=(
    "admin123"
    "postgres123" 
    "tattoo_admin"
    "production"
    "prod_pass"
)

# Function to check if password looks like production
is_production_password() {
    local password="$1"
    
    # Check against known production patterns
    for pattern in "${PROD_PASSWORD_PATTERNS[@]}"; do
        if [[ "$password" == *"$pattern"* ]]; then
            return 0  # Found production pattern
        fi
    done
    
    # Check if password is too complex for test (likely production)
    # Production passwords typically have special chars and are longer
    if [[ ${#password} -gt 12 && "$password" == *[A-Z]* && "$password" == *[a-z]* && "$password" == *[0-9]* && "$password" == *[^a-zA-Z0-9]* ]]; then
        return 0  # Looks like production password
    fi
    
    return 1  # Probably safe test password
}

# Security check: abort if TESTING=true with production-like credentials
if [[ "$TESTING" == "true" || "$TESTING" == "1" ]]; then
    echo "🔍 Security check: Running in TEST mode"
    
    # Check POSTGRES_PASSWORD
    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        if is_production_password "$POSTGRES_PASSWORD"; then
            echo "❌ SECURITY ERROR: Cannot use production-like POSTGRES_PASSWORD in test mode!"
            echo "   TESTING=true detected with suspicious password pattern"
            echo "   Use simple test passwords like 'test', 'postgres', or 'test123'"
            echo "   Or use SQLite with DATABASE_URL=sqlite:///:memory:"
            exit 1
        fi
    fi
    
    # Check other sensitive environment variables
    if [[ -n "$JWT_SECRET_KEY" && "$JWT_SECRET_KEY" != *"dev"* && "$JWT_SECRET_KEY" != *"test"* ]]; then
        if is_production_password "$JWT_SECRET_KEY"; then
            echo "❌ SECURITY ERROR: Production-like JWT_SECRET_KEY detected in test mode!"
            echo "   Use a simple test key like 'dev-jwt-secret' or 'test-secret'"
            exit 1
        fi
    fi
    
    # Check Flask secret
    if [[ -n "$FLASK_SECRET_KEY" && "$FLASK_SECRET_KEY" != *"dev"* && "$FLASK_SECRET_KEY" != *"test"* ]]; then
        if is_production_password "$FLASK_SECRET_KEY"; then
            echo "❌ SECURITY ERROR: Production-like FLASK_SECRET_KEY detected in test mode!"
            echo "   Use a simple test key like 'dev-secret-change-me'"
            exit 1
        fi
    fi
    
    echo "✅ Security check passed: Test credentials look safe"
fi

# Show startup info
echo "🚀 Starting Tattoo Studio System..."
echo "   TESTING: ${TESTING:-false}"
echo "   FLASK_ENV: ${FLASK_ENV:-development}"
echo "   DATABASE: ${DATABASE_URL:-not set}"

# Execute the original command
exec "$@"