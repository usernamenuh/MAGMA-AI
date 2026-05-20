#!/bin/bash

# OpenAI-Compatible API Authentication and Feature Tests
# This script tests various aspects of the API including auth, errors, and tool calling

API_BASE_URL="http://localhost:8000"
API_KEY="test-key-123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "OpenAI-Compatible API Test Suite"
echo "========================================="
echo ""

# Function to pretty print JSON
pretty_json() {
    python3 -m json.tool 2>/dev/null || cat
}

# Test 1: Check if server is running
echo -e "${YELLOW}Test 1: Server Health Check${NC}"
echo "Testing: GET /"
response=$(curl -s -w "\n%{http_code}" ${API_BASE_URL}/)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Server is running${NC}"
    echo "$body" | pretty_json
else
    echo -e "${RED}✗ Server is not responding (HTTP $http_code)${NC}"
    echo "Please start the server first: python main.py"
    exit 1
fi
echo ""

# Test 2: Test authentication rejection (no header)
echo -e "${YELLOW}Test 2: Authentication - Missing Header${NC}"
echo "Testing: GET /v1/models (no auth header)"
echo "Expected: 401 Unauthorized (if API_KEY is set)"
response=$(curl -s -w "\n%{http_code}" ${API_BASE_URL}/v1/models)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✓ Correctly rejected request without auth${NC}"
    echo "Response:"
    echo "$body" | pretty_json
elif [ "$http_code" = "200" ]; then
    echo -e "${YELLOW}⚠ Authentication is disabled (API_KEY not set in .env)${NC}"
    echo "To enable auth, add to .env: API_KEY=$API_KEY"
else
    echo -e "${RED}✗ Unexpected response (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# Test 3: Test authentication with invalid token
echo -e "${YELLOW}Test 3: Authentication - Invalid Token${NC}"
echo "Testing: GET /v1/models (wrong token)"
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer wrong-token" \
    ${API_BASE_URL}/v1/models)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✓ Correctly rejected invalid token${NC}"
    echo "Response:"
    echo "$body" | pretty_json
elif [ "$http_code" = "200" ]; then
    echo -e "${YELLOW}⚠ Authentication is disabled${NC}"
else
    echo -e "${RED}✗ Unexpected response (HTTP $http_code)${NC}"
fi
echo ""

# Test 4: Test authentication with valid token
echo -e "${YELLOW}Test 4: Authentication - Valid Token${NC}"
echo "Testing: GET /v1/models (correct token)"
echo "Using token: $API_KEY"
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${API_KEY}" \
    ${API_BASE_URL}/v1/models)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Successfully authenticated${NC}"
    echo "Response:"
    echo "$body" | pretty_json
else
    echo -e "${YELLOW}⚠ Could not authenticate (HTTP $http_code)${NC}"
    echo "Make sure API_KEY=$API_KEY is set in .env"
    echo "$body" | pretty_json
fi
echo ""

# Test 5: Test invalid request (validation error)
echo -e "${YELLOW}Test 5: Error Format - Validation Error${NC}"
echo "Testing: POST /v1/chat/completions (invalid request)"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"invalid": "request"}' \
    ${API_BASE_URL}/v1/chat/completions)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "422" ]; then
    echo -e "${GREEN}✓ Validation error returned correctly${NC}"
    echo "OpenAI-compatible error format:"
    echo "$body" | pretty_json
else
    echo -e "${RED}✗ Unexpected response (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# Test 6: Test simple chat completion
echo -e "${YELLOW}Test 6: Chat Completion - Simple${NC}"
echo "Testing: POST /v1/chat/completions"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "mistral-7b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 50
    }' \
    ${API_BASE_URL}/v1/chat/completions)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Chat completion successful${NC}"
    echo "Response structure:"
    echo "$body" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"  ID: {data.get('id', 'N/A')}\")
print(f\"  Object: {data.get('object', 'N/A')}\")
print(f\"  Model: {data.get('model', 'N/A')}\")
print(f\"  Message: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:100]}...\")
print(f\"  Tokens: {data.get('usage', {}).get('total_tokens', 'N/A')}\")
" 2>/dev/null || echo "$body" | pretty_json
else
    echo -e "${RED}✗ Chat completion failed (HTTP $http_code)${NC}"
    echo "$body" | pretty_json
fi
echo ""

# Test 7: Test streaming
echo -e "${YELLOW}Test 7: Chat Completion - Streaming${NC}"
echo "Testing: POST /v1/chat/completions (stream=true)"
echo -e "${GREEN}Streaming response:${NC}"
curl -s -N \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "mistral-7b-instruct",
        "messages": [{"role": "user", "content": "Count to 3"}],
        "max_tokens": 50,
        "stream": true
    }' \
    ${API_BASE_URL}/v1/chat/completions | head -n 5
echo ""
echo "(Showing first 5 events)"
echo ""

# Test 8: Test tool/function calling
echo -e "${YELLOW}Test 8: Tool/Function Calling${NC}"
echo "Testing: POST /v1/chat/completions (with tools)"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "mistral-7b-instruct",
        "messages": [{"role": "user", "content": "What is the weather in New York?"}],
        "max_tokens": 150,
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["location"]
                }
            }
        }]
    }' \
    ${API_BASE_URL}/v1/chat/completions)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Tool calling request successful${NC}"
    echo "Checking for tool_calls in response..."
    echo "$body" | python3 -c "
import json, sys
data = json.load(sys.stdin)
choice = data.get('choices', [{}])[0]
message = choice.get('message', {})
tool_calls = message.get('tool_calls', [])
if tool_calls:
    print('  ✓ Model attempted to call tools:')
    for tc in tool_calls:
        func = tc.get('function', {})
        print(f\"    - {func.get('name', 'N/A')}: {func.get('arguments', 'N/A')}\")
else:
    print('  ℹ Model did not call any tools (may need a model that supports function calling)')
    print(f\"  Response: {message.get('content', 'N/A')[:100]}...\")
" 2>/dev/null || echo "$body" | pretty_json
else
    echo -e "${RED}✗ Tool calling failed (HTTP $http_code)${NC}"
    echo "$body" | pretty_json
fi
echo ""

# Test 9: Test embeddings endpoint (if enabled)
echo -e "${YELLOW}Test 9: Embeddings Endpoint${NC}"
echo "Testing: POST /v1/embeddings"
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "mistral-7b-instruct",
        "input": "Hello world"
    }' \
    ${API_BASE_URL}/v1/embeddings)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Embeddings endpoint available${NC}"
    echo "$body" | python3 -c "
import json, sys
data = json.load(sys.stdin)
embeddings = data.get('data', [])
if embeddings:
    emb = embeddings[0].get('embedding', [])
    print(f\"  Embedding dimensions: {len(emb)}\")
    print(f\"  First 5 values: {emb[:5]}\")
" 2>/dev/null || echo "Embeddings generated"
elif [ "$http_code" = "404" ]; then
    echo -e "${YELLOW}⚠ Embeddings not enabled${NC}"
    echo "To enable, set EMBEDDING_ENABLED=true in .env"
else
    echo -e "${RED}✗ Unexpected response (HTTP $http_code)${NC}"
    echo "$body" | pretty_json
fi
echo ""

# Summary
echo "========================================="
echo -e "${GREEN}Test Suite Complete!${NC}"
echo "========================================="
echo ""
echo "To enable authentication, add to your .env file:"
echo "  API_KEY=$API_KEY"
echo ""
echo "For production use, generate a secure key:"
echo "  openssl rand -hex 32"
echo "" 