import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# Load private key (PEM)
with open("licensing/private_key.pem", "rb") as f:
    PRIVATE_KEY = load_pem_private_key(f.read(), password=None)


def sign_license(license_dict: dict) -> dict:
    """
    Signs the license dict and returns a new dict with 'signature' field
    """
    data = license_dict.copy()
    message = json.dumps(data, sort_keys=True).encode()
    signature = PRIVATE_KEY.sign(
        message,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    data["signature"] = base64.b64encode(signature).decode()
    return data