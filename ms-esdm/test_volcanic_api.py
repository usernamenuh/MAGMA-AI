import os
import requests
import argparse
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Get the absolute path of the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

log_lines = []

def log(message=""):
    """Prints a message to the console and adds it to the log list."""
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
            log(f"❌ Login failed: 'token' not in response. Full response: {data}")
            return None
    except requests.RequestException as e:
        log(f"❌ Login request failed: {e}")
        return None

def test_api_endpoint(base_url, token, endpoint_path, params=None):
    """Tests a specific API endpoint with the provided token and optional params."""
    if not endpoint_path.startswith('/'):
        endpoint_path = '/' + endpoint_path

    test_url = f"{base_url.rstrip('/')}{endpoint_path}"
    headers = {"Authorization": f"Bearer {token}"}

    log(f"\n--- Testing endpoint: {test_url} (Params: {params}) ---")

    try:
        res = requests.get(test_url, headers=headers, params=params, timeout=15)
        res.raise_for_status()
        log(f"✅ Success! ({res.status_code})")
        log("Response (first 300 chars):")
        log(str(res.text)[:300])
        return res.json()
    except requests.RequestException as e:
        log(f"❌ Request failed: {e}")
        if e.response is not None:
            log(f"Status Code: {e.response.status_code}")
            log(f"Response Body: {e.response.text}")
        return None
    except ValueError:
        log("⚠️ Could not decode JSON from response.")
        return None

def fetch_live_data(base_url, token):
    """Fetch live data to get valid IDs for testing."""
    log("\n--- Fetching live data for testing dynamic endpoints ---")
    live_data = {}
    
    vona_data = test_api_endpoint(base_url, token, "/api/v1/vona/latest")
    if vona_data and 'data' in vona_data and vona_data['data']:
        live_data['vona_uuid'] = vona_data['data'].get('uuid')
        log(f"✅ Extracted live VONA UUID: {live_data['vona_uuid']}")

    gunung_api_data = test_api_endpoint(base_url, token, "/api/v1/home/gunung-api")
    if gunung_api_data and isinstance(gunung_api_data, list) and gunung_api_data:
        live_data['gunung_code'] = gunung_api_data[0].get('ga_code')
        log(f"✅ Extracted live Gunung API Code: {live_data['gunung_code']}")

    return live_data

def test_volcanic_endpoints(base_url, token):
    """Reads and tests only VEN, VONA, and VAR endpoints intelligently."""
    import json
    import time

    live_data = fetch_live_data(base_url, token)
    log("\n--- Testing Volcanic (VEN, VONA, VAR) endpoints ---")
    
    examples_path = os.path.join(SCRIPT_DIR, "examples_min.json")
    try:
        with open(examples_path, "r") as f:
            examples = json.load(f)
    except FileNotFoundError:
        log(f"❌ Error: {examples_path} not found.")
        return
    except json.JSONDecodeError:
        log(f"❌ Error: Could not parse {examples_path}.")
        return

    volcanic_endpoints = set()
    for item in examples:
        api_path = item.get("api", "")
        if "/vona" in api_path or "/magma-var" in api_path or "/informasi-letusan" in api_path:
            cleaned_path = api_path.replace("{{url}}", "").split("?")[0]
            volcanic_endpoints.add(cleaned_path)

    log(f"Found {len(volcanic_endpoints)} volcanic endpoints to test.")
    
    for i, endpoint in enumerate(sorted(list(volcanic_endpoints))):
        params = None
        
        if "{uuid}" in endpoint and live_data.get('vona_uuid'):
            endpoint = endpoint.replace("{uuid}", str(live_data['vona_uuid']))
        if "{code}" in endpoint and live_data.get('gunung_code'):
             endpoint = endpoint.replace("{code}", str(live_data['gunung_code']))

        if "/filter" in endpoint:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            params = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "code": live_data.get('gunung_code', 'MER')
            }
        
        test_api_endpoint(base_url, token, endpoint, params=params)
        
        if i < len(volcanic_endpoints) - 1:
            time.sleep(0.5)

def main():
    """Main function to run the API test script."""
    load_dotenv()
    app_id = os.getenv("APP_ID")
    secret_key = os.getenv("SECRET_KEY")
    base_url = os.getenv("BASE_URL")

    if not all([app_id, secret_key, base_url]):
        log("❌ Error: Ensure APP_ID, SECRET_KEY, and BASE_URL are set in your .env file.")
        return

    token = get_api_token(base_url, app_id, secret_key)
    if token:
        test_volcanic_endpoints(base_url, token)

    log_filename = os.path.join(SCRIPT_DIR, "test_volcanic_api_results.txt")
    try:
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        log(f"\n✅ Test complete. Results saved to {log_filename}")
    except IOError as e:
        log(f"\n❌ Could not write log file: {e}")

if __name__ == "__main__":
    main()
