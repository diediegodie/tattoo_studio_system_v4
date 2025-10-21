#!/bin/bash
# Test script for verifying centralized DB session in migration scripts
# Usage: ./docs/final_prod_sec/test_migration_scripts.sh

set -e  # Exit on error

echo "=========================================="
echo "Migration Scripts - Centralized Session Test"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run test
run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -e "${YELLOW}Testing:${NC} $test_name"
    if eval "$command"; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        ((TESTS_PASSED++))
        echo ""
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        ((TESTS_FAILED++))
        echo ""
        return 1
    fi
}

# Ensure we're in the right directory
cd "$(dirname "$0")/../.."

echo "Step 1: Verify Docker environment is running"
echo "=============================================="
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Starting Docker environment...${NC}"
    docker compose up -d
    sleep 5
fi
echo -e "${GREEN}✅ Docker environment is running${NC}"
echo ""

echo "Step 2: Syntax Validation"
echo "=============================================="
run_test "Python syntax check" \
    "python3 -m py_compile backend/scripts/add_google_event_id_column.py backend/scripts/verify_migration_readiness.py backend/scripts/migrate_comissoes_nullable.py backend/scripts/migrate_financial_flow.py backend/scripts/migrate_cliente_nullable_production.py backend/scripts/test_centralized_session.py"

echo "Step 3: Centralized Session Test"
echo "=============================================="
run_test "Test centralized session configuration" \
    "docker compose run --rm app python backend/scripts/test_centralized_session.py"

echo "Step 4: Migration Script Execution Tests"
echo "=============================================="
run_test "Add google_event_id column script" \
    "docker compose run --rm app python backend/scripts/add_google_event_id_column.py"

echo "Step 5: Database Connection Verification"
echo "=============================================="
run_test "Check application_name in pg_stat_activity" \
    "docker compose exec -T db psql -U admin -d tattoo_studio -c \"SELECT application_name FROM pg_stat_activity WHERE application_name='tattoo_studio' LIMIT 1;\" | grep -q 'tattoo_studio'"

echo "Step 6: Connection Pool Statistics"
echo "=============================================="
echo -e "${YELLOW}Current connections in pg_stat_activity:${NC}"
docker compose exec -T db psql -U admin -d tattoo_studio -c \
    "SELECT datname, application_name, state, count(*) 
     FROM pg_stat_activity 
     WHERE application_name='tattoo_studio' 
     GROUP BY datname, application_name, state 
     ORDER BY datname, application_name, state;"
echo ""

echo "Step 7: Verify Migration Readiness Script"
echo "=============================================="
run_test "Verify migration readiness check" \
    "docker compose run --rm app python backend/scripts/verify_migration_readiness.py"

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review pg_stat_activity output above"
    echo "2. Confirm application_name='tattoo_studio' is present"
    echo "3. Verify connection pooling is active"
    echo "4. Deploy to staging for further validation"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo ""
    echo "Please review the errors above and fix before proceeding."
    exit 1
fi
