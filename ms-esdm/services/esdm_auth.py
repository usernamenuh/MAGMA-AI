import os
import threading
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


load_dotenv()

API_TOKEN = None
_AUTH_LOCK = threading.Lock()


def _auth_config():
    """Read stakeholder credentials at call time and validate the base URL."""
    app_id = os.getenv("APP_ID", "").strip()
    secret_key = os.getenv("SECRET_KEY", "").strip()
    base_url = os.getenv("BASE_URL", "https://vsi.esdm.go.id/data").strip().rstrip("/")

    missing = [
        name
        for name, value in (("APP_ID", app_id), ("SECRET_KEY", secret_key))
        if not value
    ]
    if missing:
        raise ValueError(f"Konfigurasi MAGMA belum lengkap: {', '.join(missing)}")

    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("BASE_URL MAGMA tidak valid")

    return app_id, secret_key, base_url


def auto_login():
    """Login to the MAGMA stakeholder API and keep its bearer token in memory."""
    global API_TOKEN

    try:
        app_id, secret_key, base_url = _auth_config()
    except ValueError as error:
        API_TOKEN = None
        print(f"MAGMA authentication disabled: {error}")
        return False

    login_url = f"{base_url}/api/login/stakeholder"

    # Avoid simultaneous refresh attempts when several requests receive 401.
    with _AUTH_LOCK:
        try:
            response = requests.post(
                login_url,
                params={"app_id": app_id, "secret_key": secret_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("token") if isinstance(data, dict) else None
            if not isinstance(token, str) or not token.strip():
                raise ValueError("respons login tidak memiliki token yang valid")

            API_TOKEN = token.strip()
            # Never print the response because it contains the stakeholder token.
            print("MAGMA stakeholder login successful.")
            return True
        except (requests.RequestException, ValueError) as error:
            API_TOKEN = None
            print(f"MAGMA stakeholder login failed: {error}")
            return False


def get_auth_header():
    """Return the stakeholder Authorization header when login has succeeded."""
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
