import subprocess
import json

BASE_URL = "http://localhost:8000"
HEADERS = ["-H", "Content-Type: application/json", "-H", "Authorization: Bearer test-token"]

results = []


def run_curl(name, method, endpoint, data=None, expect_code=200, expect_keys=None, allow_skip_type=None):
    url = f"{BASE_URL}{endpoint}"
    cmd = ["curl", "-s", "-w", "%{http_code}", "-o", "response.json"]

    if method == "POST":
        cmd += ["-X", "POST"]
    if data:
        cmd += ["-d", json.dumps(data)]
    cmd += HEADERS
    cmd += [url]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    try:
        status_code = int(output[-3:])
        body = open("response.json").read().strip()
    except Exception:
        status_code, body = -1, ""

    state, flag = "FAIL", "❌"
    body_json = None

    # Parse JSON if possible
    try:
        body_json = json.loads(body)
    except Exception:
        pass

    # Check skip condition (example: embeddings disabled)
    if status_code == 404 and body_json and allow_skip_type:
        if body_json.get("error", {}).get("type") == allow_skip_type:
            state, flag = "SKIP", "⚠️"

    # Check success
    if status_code == expect_code:
        state, flag = "PASS", "✅"
        if expect_keys and body_json:
            for key in expect_keys:
                if key not in body_json:
                    state, flag = "FAIL", "❌"

    results.append((name, state, flag, status_code, body[:150]))


# ---------- Run Tests ----------
run_curl("Root", "GET", "/", expect_code=200)
run_curl("Models", "GET", "/v1/models", expect_code=200, expect_keys=["data"])
run_curl("Chat Completion", "POST", "/v1/chat/completions",
         data={"model": "mistral-7b-instruct", "messages": [{"role": "user", "content": "Hello"}]},
         expect_code=200, expect_keys=["choices"])
run_curl("Embeddings", "POST", "/v1/embeddings",
         data={"model": "mistral-7b-instruct", "input": "This is a test embedding"},
         expect_code=200, expect_keys=["data"],
         allow_skip_type="feature_not_enabled")

# ---------- Summary ----------
passed = sum(1 for r in results if r[1] == "PASS")
failed = sum(1 for r in results if r[1] == "FAIL")
skipped = sum(1 for r in results if r[1] == "SKIP")
total = len(results)

for name, state, flag, status, body in results:
    print(f"{flag} {name} (HTTP {status}) -> {state}")

print("-" * 50)
print(f"{passed} passed, {skipped} skipped, {failed} failed / {total} total")
