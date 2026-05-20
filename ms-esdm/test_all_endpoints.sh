#!/bin/bash

echo "====================================="
echo "🚀 FastAPI Endpoint Test Script"
echo "====================================="

read -p "Enter EC2 Public IP: " EC2_PUBLIC_IP

if [ -z "$EC2_PUBLIC_IP" ]; then
  echo "❌ No IP entered"
  exit 1
fi

BASE_URL="http://${EC2_PUBLIC_IP}/api"

echo "Using API URL: $BASE_URL"
echo ""

EMAIL="test$(date +%s)@tagflow-ai.com"
PASSWORD="123456"
NAME="Test User"

echo "====================================="
echo "1️⃣ Register User"
echo "====================================="

REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
-H "Content-Type: application/json" \
-d "{
  \"name\":\"$NAME\",
  \"email\":\"$EMAIL\",
  \"password\":\"$PASSWORD\"
}")

echo $REGISTER_RESPONSE | jq

echo ""
echo "====================================="
echo "2️⃣ Login"
echo "====================================="

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
-H "Content-Type: application/json" \
-d "{
  \"email\":\"$EMAIL\",
  \"password\":\"$PASSWORD\"
}")

echo $LOGIN_RESPONSE | jq

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')

if [ "$ACCESS_TOKEN" == "null" ]; then
  echo "❌ Login failed. No access token."
  exit 1
fi

echo ""
echo "✅ Access Token:"
echo $ACCESS_TOKEN

echo ""
echo "====================================="
echo "3️⃣ Validate Token"
echo "====================================="

VALIDATE_TOKEN=$(curl -s -X POST "$BASE_URL/auth/validate-token" \
-H "Content-Type: application/json" \
-d "{
  \"access_token\":\"$ACCESS_TOKEN\"
}")

echo $VALIDATE_TOKEN | jq
USER_ID=$(echo $VALIDATE_TOKEN | jq -r '.user_id')

echo ""
echo "====================================="
echo "4️⃣ Generate API Key"
echo "====================================="

GENERATE_KEY=$(curl -s -X POST "$BASE_URL/api-keys/generate" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d "{
  \"user_id\":\"$USER_ID\",
  \"name\":\"test-key\",
  \"validity_duration_days\":30
}")

echo $GENERATE_KEY | jq
API_KEY=$(echo $GENERATE_KEY | jq -r '.api_key')

echo ""
echo "====================================="
echo "5️⃣ Upload Knowledge Document"
echo "====================================="

UPLOAD=$(curl -s -X POST "$BASE_URL/knowledge/upload" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-F "file=@test.pdf")

echo $UPLOAD | jq

echo ""
echo "====================================="
echo "6️⃣ Get Knowledge Vector"
echo "====================================="

VECTOR=$(curl -s -X POST "$BASE_URL/knowledge/get_vector?query=earthquake&top_k=5")

echo $VECTOR | jq

echo ""
echo "====================================="
echo "7️⃣ Knowledge Analyze"
echo "====================================="

KNOW_ANALYZE=$(curl -s -X POST "$BASE_URL/knowledge/analyze" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d "{
  \"user_input\":\"Explain volcano eruption\"
}")

echo $KNOW_ANALYZE | jq

echo ""
echo "====================================="
echo "8️⃣ Knowledge Analyze EN"
echo "====================================="

KNOW_ANALYZE_EN=$(curl -s -X POST "$BASE_URL/knowledge/analyze-en" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d "{
  \"user_input\":\"What is a tsunami?\"
}")

echo $KNOW_ANALYZE_EN | jq

echo ""
echo "====================================="
echo "9️⃣ List Knowledge Documents"
echo "====================================="

DOCS=$(curl -s -X GET "$BASE_URL/knowledge/documents?page=1&limit=10")

echo $DOCS | jq

DOC_ID=$(echo $DOCS | jq -r '.[0].id')

echo ""
echo "====================================="
echo "🔟 Document Details"
echo "====================================="

DETAILS=$(curl -s -X GET "$BASE_URL/knowledge/documents/$DOC_ID")

echo $DETAILS | jq

echo ""
echo "====================================="
echo "1️⃣1️⃣ Chat Message"
echo "====================================="

SESSION_ID="session-$(date +%s)"

CHAT_MSG=$(curl -s -X POST "$BASE_URL/chat/message" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d "{
  \"user_id\":\"$USER_ID\",
  \"session_id\":\"$SESSION_ID\",
  \"role\":\"user\",
  \"message\":\"Hello AI\"
}")

echo $CHAT_MSG | jq

echo ""
echo "====================================="
echo "1️⃣2️⃣ Get Chat Session Messages"
echo "====================================="

SESSION_MSG=$(curl -s -X GET "$BASE_URL/chat/session/$SESSION_ID?user_id=$USER_ID")

echo $SESSION_MSG | jq

echo ""
echo "====================================="
echo "1️⃣3️⃣ Get User Sessions"
echo "====================================="

USER_SESSIONS=$(curl -s -X GET "$BASE_URL/chat/sessions?user_id=$USER_ID")

echo $USER_SESSIONS | jq

echo ""
echo "====================================="
echo "1️⃣4️⃣ Delete Chat Session"
echo "====================================="

DELETE_SESSION=$(curl -s -X DELETE "$BASE_URL/chat/sessions/$SESSION_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN")

echo $DELETE_SESSION | jq

echo ""
echo "====================================="
echo "1️⃣5️⃣ Delete User Chat History"
echo "====================================="

DELETE_HISTORY=$(curl -s -X DELETE "$BASE_URL/chat/users/$USER_ID/history" \
-H "Authorization: Bearer $ACCESS_TOKEN")

echo $DELETE_HISTORY | jq

echo ""
echo "====================================="
echo "1️⃣6️⃣ Validate API Key"
echo "====================================="

VALIDATE_KEY=$(curl -s -X GET "$BASE_URL/api-keys/validate/$API_KEY" \
-H "Authorization: Bearer $ACCESS_TOKEN")

echo $VALIDATE_KEY | jq

echo ""
echo "====================================="
echo "1️⃣7️⃣ Revoke API Key"
echo "====================================="

REVOKE=$(curl -s -X POST "$BASE_URL/api-keys/revoke/$API_KEY" \
-H "Authorization: Bearer $ACCESS_TOKEN")

echo $REVOKE | jq

echo ""
echo "====================================="
echo "1️⃣8️⃣ Remove API Key"
echo "====================================="

REMOVE=$(curl -s -X DELETE "$BASE_URL/api-keys/remove/$API_KEY" \
-H "Authorization: Bearer $ACCESS_TOKEN")

echo $REMOVE | jq

echo ""
echo "====================================="
echo "✅ All tests completed"
echo "====================================="