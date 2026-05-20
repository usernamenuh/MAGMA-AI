#!/bin/bash

# Prompt the user for the EC2 instance IP address
read -p "Enter the Public IP Address of your EC2 instance: " EC2_PUBLIC_IP

# Check if the IP address was entered
if [ -z "$EC2_PUBLIC_IP" ]; then
  echo "❌ No IP address entered. Exiting."
  exit 1
fi

# Check if API_URL is set, otherwise default to EC2 public IP
if [ -z "$API_URL" ]; then
  API_URL="http://${EC2_PUBLIC_IP}:8002"
  echo "ℹ️ API_URL not set. Using default: $API_URL"
fi

# --- Step 1: Setup Logging ---
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
LOG_DIR="concurrency_log"
LOG_FILE="${LOG_DIR}/${TIMESTAMP}-chat-concurrency-test.txt"

if [ ! -d "$LOG_DIR" ]; then
  echo "📂 Log directory $LOG_DIR not found. Creating..."
  mkdir -p "$LOG_DIR"
  echo "✅ Log directory created."
else
  echo "📂 Log directory $LOG_DIR already exists."
fi

echo "📝 Logging results to $LOG_FILE"
echo "=== Chat Completion Concurrency Test Report ===" > "$LOG_FILE"
echo "EC2 Public IP: $EC2_PUBLIC_IP" >> "$LOG_FILE"
echo "API URL: $API_URL" >> "$LOG_FILE"
echo "Test Time: $(date)" >> "$LOG_FILE"
echo "================================" >> "$LOG_FILE"

# --- Step 2: Function to Run Concurrent Requests ---
run_concurrency_test() {
  local concurrency=$1
  echo -e "\n============================================================"
  echo "Running chat test with concurrency level: $concurrency"
  echo "============================================================"

  echo -e "\n--- Concurrency: $concurrency ---" >> "$LOG_FILE"
  START_TIME=$(date +%s)

  SUCCESS_COUNT=0
  FAIL_COUNT=0

  for i in $(seq 1 $concurrency); do
    (
      REQ_START=$(date +%s%3N) # ms timestamp
      RESPONSE=$(curl --fail -s -X POST "${API_URL}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{
              "model": "mistral-7b-instruct",
              "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, test run '"$i"'"}
              ],
              "temperature": 0.7,
              "stream": true

            }' -w "%{http_code}" -o tmp_${i}.out)
      EXIT_CODE=$?
      REQ_END=$(date +%s%3N)
      REQ_DURATION=$((REQ_END - REQ_START))

      if [ $EXIT_CODE -ne 0 ]; then
        echo "[Request $i] ❌ Failed (Exit code $EXIT_CODE, Duration ${REQ_DURATION}ms)" >> "$LOG_FILE"
        echo "FAIL" > tmp_${i}.status
      else
        echo "[Request $i] ✅ Success (Duration ${REQ_DURATION}ms, HTTP $RESPONSE)" >> "$LOG_FILE"
        jq . < tmp_${i}.out >> "$LOG_FILE" 2>/dev/null
        echo "SUCCESS" > tmp_${i}.status
      fi
    ) &
  done

  wait
  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))

  # Count results
  for i in $(seq 1 $concurrency); do
    if [ -f tmp_${i}.status ]; then
      STATUS=$(cat tmp_${i}.status)
      if [ "$STATUS" = "SUCCESS" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT+1))
      else
        FAIL_COUNT=$((FAIL_COUNT+1))
      fi
      rm -f tmp_${i}.status tmp_${i}.out
    fi
  done

  echo "--- Concurrency $concurrency completed in ${DURATION}s ---" | tee -a "$LOG_FILE"
  echo "Summary:" >> "$LOG_FILE"
  echo "- Total Requests: $concurrency" >> "$LOG_FILE"
  echo "- Success: $SUCCESS_COUNT" >> "$LOG_FILE"
  echo "- Failures: $FAIL_COUNT" >> "$LOG_FILE"
  echo "- Total Duration: ${DURATION}s" >> "$LOG_FILE"
  echo "- Average per Request: $((DURATION*1000/concurrency))ms (approx)" >> "$LOG_FILE"
}

# --- Step 3: Run concurrency tests ---
run_concurrency_test 1
run_concurrency_test 1
run_concurrency_test 1
# run_concurrency_test 1
# run_concurrency_test 5
# run_concurrency_test 10
# run_concurrency_test 20
# run_concurrency_test 50
# run_concurrency_test 100

# --- Step 4: Final message ---
echo "✅ Chat test completed successfully. Results saved in $LOG_FILE"
