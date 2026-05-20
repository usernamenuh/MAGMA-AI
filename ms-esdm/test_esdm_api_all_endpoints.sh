#!/bin/bash

BASE_URL="http://localhost:8000/api"
OUT_FILE="esdm_api_test_results.txt"

NAME="Test User"
EMAIL="test@tagflow-ai.com"
PASSWORD="password123"

USER_ID="test-user-id"
SESSION_ID="test-session-id"
UPLOAD_FILE="sample.pdf"

echo "ESDM API TEST – $(date)" > "$OUT_FILE"

log () {
  echo -e "\n$1\n" >> "$OUT_FILE"
}

req () {
  METHOD=$1
  URL=$2
  DATA=$3
  AUTH=$4

  echo "[$METHOD] $URL" >> "$OUT_FILE"

  if [ "$AUTH" = "auth" ]; then
    HDR=(-H "Authorization: Bearer $ACCESS_TOKEN")
  else
    HDR=()
  fi

  if [ -z "$DATA" ]; then
    curl -s -w "\nHTTP_STATUS: %{http_code}\n\n" \
      -X "$METHOD" -H "Content-Type: application/json" \
      "${HDR[@]}" "$URL" >> "$OUT_FILE"
  else
    curl -s -w "\nHTTP_STATUS: %{http_code}\n\n" \
      -X "$METHOD" -H "Content-Type: application/json" \
      "${HDR[@]}" -d "$DATA" "$URL" >> "$OUT_FILE"
  fi
}

# --------------------------------------------------
# REGISTER (FIRST)
# --------------------------------------------------
log "REGISTER"

REGISTER_RESP=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$NAME\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "[POST] /auth/register" >> "$OUT_FILE"
echo "$REGISTER_RESP" >> "$OUT_FILE"

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
log "LOGIN"

LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "[POST] /auth/login" >> "$OUT_FILE"
echo "$LOGIN_RESP" >> "$OUT_FILE"

ACCESS_TOKEN=$(echo "$LOGIN_RESP" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
REFRESH_TOKEN=$(echo "$LOGIN_RESP" | sed -n 's/.*"refresh_token":"\([^"]*\)".*/\1/p')
USER_ID=$(echo "$LOGIN_RESP" | sed -n 's/.*"user":[^{]*{[^}]*"id":"\([^"]*\)".*/\1/p')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login failed, stopping secure tests" >> "$OUT_FILE"
  exit 1
fi

echo "ACCESS_TOKEN OK" >> "$OUT_FILE"

# --------------------------------------------------
# TOKEN VALIDATION
# --------------------------------------------------
log "TOKEN VALIDATION"

req POST "$BASE_URL/auth/validate-token" \
  "{\"access_token\":\"$ACCESS_TOKEN\"}"

# --------------------------------------------------
# ANALYZE
# --------------------------------------------------
log "ANALYZE"

req POST "$BASE_URL/analyze" \
  '{"user_input":"Analyze test"}' auth

req POST "$BASE_URL/analyze/en" \
  '{"user_input":"Analyze EN test"}' auth

# --------------------------------------------------
# KNOWLEDGE
# --------------------------------------------------
log "KNOWLEDGE"

if [ -f "$UPLOAD_FILE" ]; then
  echo "[POST] /knowledge/upload" >> "$OUT_FILE"
  curl -s -w "\nHTTP_STATUS: %{http_code}\n\n" \
    -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "file=@$UPLOAD_FILE" \
    "$BASE_URL/knowledge/upload" >> "$OUT_FILE"
else
  echo "⚠ upload skipped (file not found)" >> "$OUT_FILE"
fi

req POST "$BASE_URL/knowledge/get_vector?query=test&top_k=3"

req POST "$BASE_URL/knowledge/analyze" \
  '{"user_input":"KB analyze"}' auth

req GET "$BASE_URL/knowledge/documents?page=1&limit=5"

# --------------------------------------------------
# CHAT
# --------------------------------------------------
log "CHAT"

req POST "$BASE_URL/chat/message" \
  "{\"user_id\":\"$USER_ID\",\"session_id\":\"$SESSION_ID\",\"role\":\"user\",\"message\":\"Hello\"}" auth

req GET "$BASE_URL/chat/sessions?user_id=$USER_ID" auth

echo "DONE – $(date)" >> "$OUT_FILE"
