import os
import requests
from dotenv import load_dotenv

API_TOKEN = None
load_dotenv()

APP_ID = os.getenv("APP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")

def auto_login():
    """
    Logs into the stakeholder API and stores the token globally.
    """
    global API_TOKEN

    login_url = f"{BASE_URL.rstrip('/')}/api/login/stakeholder"
    params = {
        "app_id": APP_ID,
        "secret_key": "$2y$10$KCibTVwiX53.RV/d7Rb4QeWS7ZAZigF.LqudN3HSFcfeep1xh6mzu"
    }

    try:
        response = requests.post(login_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Login response: {data}")
        if "token" in data:
            API_TOKEN = data["token"]
            print("✅ Login successful, token saved.")
        else:
            raise ValueError("Login response missing 'token' field")

    except requests.RequestException as e:
        print(f"❌ Login request failed: {e}")
    except ValueError as e:
        print(f"❌ Invalid response: {e}")


def get_auth_header():
    """Return Authorization header if token exists."""
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}