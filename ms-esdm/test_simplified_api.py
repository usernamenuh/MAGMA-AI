import os
import json
import time
import argparse
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# Get the absolute path of the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

log_lines = []
response_summary = {}


def log(message=""):
    """Print and store logs."""
    print(message)
    log_lines.append(str(message))


def get_api_token(base_url, app_id, secret_key):
    """Logs in and retrieves an API token."""
    login_url = f"{base_url.rstrip('/')}/api/login/stakeholder"
    params = {"app_id": app_id, "secret_key": secret_key}
    try:
        res = requests.post(login_url, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        if "token" in data:
            log("✅ Login successful. Token received.")
            return data["token"]
        else:
            log("❌ Login failed: 'token' not in response.")
            log(f"Response: {data}")
            return None
    except requests.RequestException as e:
        log(f"❌ Login request failed: {e}")
        return None


def test_api_endpoint(base_url, token, endpoint, params=None):
    """Tests one API endpoint."""
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}

    log(f"\n--- Testing: {url} ---")
    if params:
        log(f"Params: {params}")

    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        code = res.status_code
        response_summary[code] = response_summary.get(code, 0) + 1  # ✅ count each status code

        res.raise_for_status()
        log(f"✅ {code} OK")
        log(f"Response preview: {res.text[:250]}")
        return res.json()

    except requests.HTTPError as e:
        if e.response is not None:
            code = e.response.status_code
            response_summary[code] = response_summary.get(code, 0) + 1  # ✅ also count error responses
            log(f"❌ HTTP {code}: {e.response.text[:250]}")
        else:
            response_summary["HTTPError"] = response_summary.get("HTTPError", 0) + 1
    except requests.RequestException as e:
        response_summary["RequestError"] = response_summary.get("RequestError", 0) + 1
        log(f"❌ Request failed: {e}")
    except ValueError:
        response_summary["JSONDecodeError"] = response_summary.get("JSONDecodeError", 0) + 1
        log("⚠️ Could not decode JSON.")
    return None

# ======================================================
# 🔹 Dynamic Live Data Fetcher
# ======================================================
def fetch_live_data(base_url, token):
    """Fetch dynamic references for endpoints."""
    live_data = {}
    log("\n--- Fetching live references ---")

    # Volcano code
    res = test_api_endpoint(base_url, token, "/api/v1/home/gunung-api")
    if isinstance(res, list) and res:
        live_data["gunung_code"] = res[0].get("ga_code") or res[0].get("code") or "MER"
        log(f"✅ Found Gunung API code: {live_data['gunung_code']}")

    # VONA UUID
    res = test_api_endpoint(base_url, token, "/api/v1/vona/latest")
    if isinstance(res, dict) and "data" in res:
        data = res["data"]
        if isinstance(data, dict):
            live_data["vona_uuid"] = data.get("uuid")
            log(f"✅ Found VONA UUID: {live_data['vona_uuid']}")

    # Earthquake or seismic code fallback
    live_data.setdefault("gunung_code", "MER")
    live_data.setdefault("vona_uuid", "0000")
    return live_data

def build_smart_params(endpoint, live_data):
    """Auto-generate query parameters for known endpoint patterns."""
    now = datetime.now()
    params = {}

    if "/filter" in endpoint or "start_date" in endpoint:
        params["start_date"] = (now - timedelta(days=180)).strftime("%Y-%m-%d")
        params["end_date"] = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        if "code" in endpoint or "gunung" in endpoint:
            params["code"] = live_data.get("gunung_code", "MER")

    elif "gunung-api" in endpoint and "page" in endpoint:
        params["page"] = 1

    elif "vona" in endpoint and "uuid" not in endpoint:
        params["limit"] = 10

    elif "helicorder" in endpoint:
        params["ga_code"] = live_data.get("gunung_code", "MER")

    elif "cctv" in endpoint:
        params["code"] = live_data.get("gunung_code", "MER")

    elif "gempa" in endpoint:
        params["page"] = 1

    return params or None


def test_all_from_simplified(base_url, token):
    """Load endpoints from simplified_endpoints.json and test them intelligently."""
    endpoints_path = os.path.join(SCRIPT_DIR, "simplified_endpoints.json")
    try:
        with open(endpoints_path, "r", encoding="utf-8") as f:
            endpoints = json.load(f)
    except Exception as e:
        log(f"❌ Failed to load endpoints: {e}")
        return

    live_data = fetch_live_data(base_url, token)
    log(f"\n--- Starting API tests ({len(endpoints)} endpoints) ---")

    for i, item in enumerate(endpoints, start=1):
        url = item.get("url", "").replace("{{url}}", "")
        if not url:
            continue

        # Replace placeholders
        url = (
            url.replace("{uuid}", str(live_data.get("vona_uuid", "")))
               .replace("{code}", str(live_data.get("gunung_code", "")))
        )

        params = build_smart_params(url, live_data)

        log(f"\n[{i}/{len(endpoints)}] Testing {url}")
        test_api_endpoint(base_url, token, url, params)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="MAGMA API Endpoint Tester")
    parser.add_argument("--endpoint", help="Test a single endpoint", default=None)
    args = parser.parse_args()

    load_dotenv()
    base_url = os.getenv("BASE_URL")
    app_id = os.getenv("APP_ID")
    secret_key = os.getenv("SECRET_KEY")

    if not all([base_url, app_id, secret_key]):
        log("❌ Missing BASE_URL, APP_ID, or SECRET_KEY in .env")
        return

    token = get_api_token(base_url, app_id, secret_key)
    if not token:
        return

    if args.endpoint:
        test_api_endpoint(base_url, token, args.endpoint)
    else:
        test_all_from_simplified(base_url, token)

    log("\n--- Summary of Responses ---")
    total = sum(response_summary.values())
    for code, count in sorted(response_summary.items()):
        log(f"{code}: {count}")
    log(f"Total endpoints tested: {total}")

    log_file = os.path.join(SCRIPT_DIR, "test_results_simplified.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    log(f"\n✅ Testing complete. Log saved to {log_file}")

if __name__ == "__main__":
    main()
