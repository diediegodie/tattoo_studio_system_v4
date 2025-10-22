#!/bin/bash
# Quick verification script for production readiness checks
# Tests health endpoints, metrics, and static asset caching

set -e

BASE_URL="${BASE_URL:-http://localhost:5000}"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD}Quick Verification Script${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""

# Function to check HTTP status
check_endpoint() {
    local endpoint=$1
    local name=$2
    echo -e "${BOLD}Testing ${name}...${RESET}"
    
    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" == "200" ]; then
        echo -e "${GREEN}✅ PASS${RESET} - HTTP ${http_code}"
        echo "Response preview: ${body:0:100}..."
        echo ""
        return 0
    else
        echo -e "${RED}❌ FAIL${RESET} - HTTP ${http_code}"
        echo "Response: $body"
        echo ""
        return 1
    fi
}

# Function to check cache headers
check_cache_headers() {
    local endpoint=$1
    echo -e "${BOLD}Testing Cache-Control headers for ${endpoint}...${RESET}"
    
    headers=$(curl -I -s "${BASE_URL}${endpoint}")
    http_code=$(echo "$headers" | grep -i "HTTP/" | awk '{print $2}')
    cache_control=$(echo "$headers" | grep -i "Cache-Control:" || echo "")
    
    if [ "$http_code" == "200" ] && [ -n "$cache_control" ]; then
        echo -e "${GREEN}✅ PASS${RESET} - HTTP ${http_code}"
        echo "Cache-Control: ${cache_control}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ FAIL${RESET} - HTTP ${http_code}"
        if [ -z "$cache_control" ]; then
            echo "Cache-Control header NOT found"
        else
            echo "Cache-Control: ${cache_control}"
        fi
        echo ""
        return 1
    fi
}

# Wait for app to be ready
echo "Waiting for application to be ready..."
sleep 3

# Run checks
FAILED=0

check_endpoint "/health" "Health Check" || FAILED=$((FAILED+1))
check_endpoint "/metrics" "Prometheus Metrics" || FAILED=$((FAILED+1))
check_endpoint "/pool-metrics" "Pool Metrics" || FAILED=$((FAILED+1))
check_cache_headers "/assets/js/main.js" || FAILED=$((FAILED+1))

# Summary
echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD}Summary${RESET}"
echo -e "${BOLD}========================================${RESET}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks PASSED ✅${RESET}"
    exit 0
else
    echo -e "${RED}${FAILED} check(s) FAILED ❌${RESET}"
    exit 1
fi
