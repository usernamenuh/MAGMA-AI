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
            log("❌ Login failed: 'token' not in response.")
            log(f"Full response: {data}")
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
        return res.json()  # Return JSON for data extraction
    except requests.RequestException as e:
        log(f"❌ Request failed: {e}")
        if e.response is not None:
            log(f"Status Code: {e.response.status_code}")
            log(f"Response Body: {e.response.text}")
        return None
    except ValueError: # JSONDecodeError
        log("⚠️ Could not decode JSON from response.")
        return None


def fetch_live_data(base_url, token):
    """Fetch live data to get valid IDs for testing."""
    log("\n--- Fetching live data for testing dynamic endpoints ---")
    live_data = {}
    
    # Fetch VONA data to get a live UUID
    vona_data = test_api_endpoint(base_url, token, "/api/v1/vona/latest")
    if vona_data and 'data' in vona_data and vona_data['data']:
        live_data['vona_uuid'] = vona_data['data'].get('uuid')
        log(f"✅ Extracted live VONA UUID: {live_data['vona_uuid']}")

    # Fetch volcano data to get a live code
    gunung_api_data = test_api_endpoint(base_url, token, "/api/v1/home/gunung-api")
    if gunung_api_data and isinstance(gunung_api_data, list) and gunung_api_data:
        live_data['gunung_code'] = gunung_api_data[0].get('ga_code')
        log(f"✅ Extracted live Gunung API Code: {live_data['gunung_code']}")

    return live_data


def test_all_endpoints(base_url, token):
    """Reads all unique API endpoints from examples and tests them intelligently."""
    import json
    import time

    live_data = fetch_live_data(base_url, token)

    log("\n--- Testing all unique endpoints from examples_min.json ---")
    
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

    unique_endpoints = set(item.get("api", "").replace("{{url}}", "").split("?")[0] for item in examples)

    log(f"Found {len(unique_endpoints)} unique endpoints to test.")
    
    for i, endpoint in enumerate(sorted(list(unique_endpoints))):
        params = None
        
        # Handle dynamic endpoints
        if "{uuid}" in endpoint and live_data.get('vona_uuid'):
            endpoint = endpoint.replace("{uuid}", str(live_data['vona_uuid']))
        if "{code}" in endpoint and live_data.get('gunung_code'):
             endpoint = endpoint.replace("{code}", str(live_data['gunung_code']))

        # Handle filter endpoints
        if "/filter" in endpoint:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            params = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "code": live_data.get('gunung_code', 'MER') # Add a default code
            }

        test_api_endpoint(base_url, token, endpoint, params=params)
        
        if i < len(unique_endpoints) - 1:
            time.sleep(0.5)

def main():
    """Main function to run the API test script."""
    parser = argparse.ArgumentParser(
        description="Test script for the Magma ESDM API. Tests all endpoints by default."
    )
    parser.add_argument(
        "endpoint",
        nargs='?',
        default=None,
        help="Optional: Provide a specific API endpoint path to test just one."
    )
    args = parser.parse_args()

    load_dotenv()
    app_id = os.getenv("APP_ID")
    secret_key = os.getenv("SECRET_KEY")
    base_url = os.getenv("BASE_URL")

    if not all([app_id, secret_key, base_url]):
        log("❌ Error: Ensure APP_ID, SECRET_KEY, and BASE_URL are set in your .env file.")
        return

    token = get_api_token(base_url, app_id, secret_key)
    if token:
        if args.endpoint:
            test_api_endpoint(base_url, token, args.endpoint)
        else:
            test_all_endpoints(base_url, token)

    # Save the log to a file
    log_filename = os.path.join(SCRIPT_DIR, "test_magma_api_results.txt")
    try:
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        log(f"\n✅ Test complete. Results saved to {log_filename}")
    except IOError as e:
        log(f"\n❌ Could not write log file: {e}")

if __name__ == "__main__":
    main()
