#!/bin/bash
# Test script to verify the workflow curl command works locally

set -e

echo "======================================"
echo "  Workflow API Test Script"
echo "======================================"
echo ""

# Check if secrets file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found"
    echo "Create .env with:"
    echo "  EXTRATO_API_BASE_URL=https://your-api.com"
    echo "  EXTRATO_API_TOKEN=your_jwt_token_here"
    exit 1
fi

# Load secrets from .env
source .env

# Validate required variables
if [ -z "$EXTRATO_API_BASE_URL" ] || [ -z "$EXTRATO_API_TOKEN" ]; then
    echo "ERROR: Missing required environment variables"
    echo "Ensure .env contains:"
    echo "  EXTRATO_API_BASE_URL"
    echo "  EXTRATO_API_TOKEN"
    exit 1
fi

# Default to October 2025 (or accept arguments)
MONTH=${1:-10}
YEAR=${2:-2025}
FORCE=${3:-false}

echo "Configuration:"
echo "  Base URL: $EXTRATO_API_BASE_URL"
echo "  Month: $MONTH"
echo "  Year: $YEAR"
echo "  Force: $FORCE"
echo ""

# Build JSON payload using jq (same as workflow)
PAYLOAD=$(jq -n \
    --arg month "$MONTH" \
    --arg year "$YEAR" \
    --arg force "$FORCE" \
    '{month: ($month|tonumber), year: ($year|tonumber), force: ($force=="true") }' )

echo "Payload: $PAYLOAD"
echo ""
echo "Making API request..."
echo "--------------------------------------"

# Make the request
HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$EXTRATO_API_BASE_URL/api/extrato/generate_service" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $EXTRATO_API_TOKEN" \
    -d "$PAYLOAD")

# Extract status and body
HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n -1)
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n 1)

echo "HTTP Status: $HTTP_STATUS"
echo "Response Body:"
echo "$HTTP_BODY" | jq '.' 2>/dev/null || echo "$HTTP_BODY"
echo "--------------------------------------"
echo ""

# Check result
if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "✓ SUCCESS: API request succeeded"
    exit 0
else
    echo "✗ FAILED: API returned HTTP $HTTP_STATUS"
    exit 1
fi
