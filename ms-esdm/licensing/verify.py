import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# Read public key from file (or you can embed as bytes)
with open("licensing/public_key.pem", "rb") as f:
    PUBLIC_KEY = f.read()


def verify_signature(license_dict: dict) -> bool:
    data = license_dict.copy()
    signature = base64.b64decode(data.pop("signature"))  # decode signature
    message = json.dumps(data, sort_keys=True).encode()  # canonical JSON

    public_key = load_pem_public_key(PUBLIC_KEY)
    try:
        public_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        print("Verification error:", e)
        return False