#!/bin/bash

# Comprehensive API Test Suite for all openai_local endpoints
# This script tests:
# 1. Basic endpoints without authentication.
# 2. Endpoints with authentication enabled.
# 3. The full lifecycle of an API key (generate, validate, revoke).
#
# Usage:
#   - To run interactively:
#     ./test_api_suite.sh
#
#   - To run with command-line arguments:
#     ./test_api_suite.sh http://54.189.189.171:8000
#
#   - To run all tests (including auth) against a secure server:
#     ADMIN_API_KEY="my-super-secret-admin-key" ./test_api_suite.sh

# --- Configuration ---
API_BASE_URL=${1:-""}
# Read ADMIN_API_KEY from the environment, if it's set
ADMIN_API_KEY=${ADMIN_API_KEY:-""}

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- User Input ---
if [ -z "$API_BASE_URL" ]; then
    read -p "Enter the server IP address or URL (e.g., 54.189.189.171): " SERVER_IP
    if [ -z "$SERVER_IP" ]; then
        echo -e "${RED}Error: Server address cannot be empty.${NC}"
        exit 1
    fi
    # check if http:// or https:// is present
    if [[ $SERVER_IP != http* ]]; then
      API_BASE_URL="http://${SERVER_IP}:8002"
    else
      API_BASE_URL=$SERVER_IP
    fi
fi

# Ask for Admin API Key if not set as an environment variable
if [ -z "$ADMIN_API_KEY" ]; then
    read -p "Enter Admin API Key to run auth tests (or press Enter to skip): " CLI_API_KEY
    ADMIN_API_KEY=$CLI_API_KEY
fi

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}  Comprehensive API Test Suite for openai_local      ${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo "Targeting API server at: $API_BASE_URL"
echo ""

# --- Helper Functions ---
pretty_json() {
    # Try to use python to pretty-print json, otherwise just cat
    python3 -c "import json, sys; print(json.dumps(json.load(sys.stdin), indent=4))" 2>/dev/null || cat
}

# --- Test Execution ---

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Server Health Check (GET /)${NC}"
response=$(curl -s -w "\n%{http_code}" "${API_BASE_URL}/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d') # Use sed for macOS compatibility

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server is not responding (HTTP $http_code)${NC}"
    echo "Please ensure the server is running at the specified URL."
    exit 1
fi
echo ""

# Test 2: List Models
echo -e "${YELLOW}Test 2: List Models (GET /v1/models)${NC}"
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer ${ADMIN_API_KEY}" "${API_BASE_URL}/v1/models")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Successfully listed models.${NC}"
elif [ "$http_code" = "401" ]; then
    echo -e "${YELLOW}⚠  Could not authenticate. If this is unexpected, check your ADMIN_API_KEY.${NC}"
else
    echo -e "${RED}✗ Unexpected response (HTTP $http_code)${NC}"
fi
echo ""

# Test 3: Chat Completion (Non-Streaming)
echo -e "${YELLOW}Test 3: Chat Completion - Non-Streaming (POST /v1/chat/completions)${NC}"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ADMIN_API_KEY}" \
    -d '{
        "model": "mistral-7b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}]
    }' \
    "${API_BASE_URL}/v1/chat/completions")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Chat completion successful${NC}"
else
    echo -e "${RED}✗ Chat completion failed (HTTP $http_code)${NC}"
fi
echo ""


# --- Authentication and API Key Management Tests ---

if [ -z "$ADMIN_API_KEY" ]; then
    echo -e "${YELLOW}=====================================================${NC}"
    echo -e "${YELLOW}  Skipping Authentication & API Key Management Tests ${NC}"
    echo -e "${YELLOW}=====================================================${NC}"
    echo "Reason: ADMIN_API_KEY environment variable is not set and was not provided."
    echo "To run these tests, you can also execute the script like this:"
    echo '  ADMIN_API_KEY="your-admin-key" ./test_api_suite.sh'
    echo ""
    exit 0
fi

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}  Running Authentication & API Key Management Tests  ${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo "Using provided Admin API Key."
echo ""

# Test 4: Generate New API Key
echo -e "${YELLOW}Test 4: Generate New Key (POST /keys/generate)${NC}"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${ADMIN_API_KEY}" \
    "${API_BASE_URL}/keys/generate")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Successfully generated a new API key${NC}"
    # Extract the key using Python for robust JSON parsing
    NEW_KEY=$(echo "$body" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])' 2>/dev/null)
    if [ -z "$NEW_KEY" ]; then
        echo -e "${RED}✗ Could not parse new API key from response body:${NC}"
        echo "$body"
        exit 1
    fi
    echo "  New key: $NEW_KEY"
else
    echo -e "${RED}✗ Failed to generate key (HTTP $http_code). Is your ADMIN_API_KEY correct?${NC}"
    echo "$body"
    exit 1
fi
echo ""

# Test 5: Validate New Key (Success)
echo -e "${YELLOW}Test 5: Validate New Key (GET /keys/validate)${NC}"
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${NEW_KEY}" \
    "${API_BASE_URL}/keys/validate")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ The new API key is valid${NC}"
else
    echo -e "${RED}✗ Key validation failed unexpectedly (HTTP $http_code)${NC}"
fi
echo ""

# Test 6: Revoke New Key
echo -e "${YELLOW}Test 6: Revoke New Key (POST /keys/revoke/{api_key})${NC}"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${ADMIN_API_KEY}" \
    "${API_BASE_URL}/keys/revoke/${NEW_KEY}")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Successfully sent request to revoke the key${NC}"
else
    echo -e "${RED}✗ Revoke request failed (HTTP $http_code)${NC}"
fi
echo ""

# Test 7: Validate Revoked Key (Failure)
echo -e "${YELLOW}Test 7: Validate Revoked Key (GET /keys/validate)${NC}"
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${NEW_KEY}" \
    "${API_BASE_URL}/keys/validate")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✓ Correctly identified the revoked key as invalid${NC}"
else
    echo -e "${RED}✗ Revoked key was not rejected. Expected 401 but got $http_code.${NC}"
fi
echo ""

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN}  All API tests completed!                       ${NC}"
echo -e "${GREEN}=====================================================${NC}" 