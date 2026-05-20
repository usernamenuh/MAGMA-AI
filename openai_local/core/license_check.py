import os
import json
import sys
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import uuid
import psutil
import hashlib
import platform

def get_local_machine_id():
    # This logic is self-contained to ensure the script can run independently.
    mac_address = ""
    try:
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac_address = addr.address
                    if "lo" not in interface and mac_address and not mac_address.startswith("00:00:00"):
                        break
            if "lo" not in interface and mac_address and not mac_address.startswith("00:00:00"):
                break
    except Exception:
        pass
    if not mac_address:
        mac_int = uuid.getnode()
        if mac_int != uuid.getnode():
             sys.exit("Error: Cannot get a stable MAC address.")
        mac_address = ':'.join(('%012X' % mac_int)[i:i+2] for i in range(0, 12, 2))
    platform_str = f"{platform.system()}-{platform.machine()}"
    composite_id = f"{mac_address}-{platform_str}"
    return hashlib.sha256(composite_id.encode()).hexdigest()


def main():
    """
    Standalone license verifier.
    On success: prints the data_key to stdout and exits with code 0.
    On failure: prints error to stderr and exits with code 1.
    """
    license_path = "license.lic"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    public_key_path = os.path.join(base_dir, "public_key.pem")

    # 1. Check license file existence
    if not os.path.exists(license_path):
        current_machine_id = get_local_machine_id()
        print(f"FATAL: license.lic not found.", file=sys.stderr)
        print(f"INFO: This machine's ID is: {current_machine_id}", file=sys.stderr)
        sys.exit(1)

    # 2. Load public key
    try:
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except FileNotFoundError:
        print(f"FATAL: Public key not found at {public_key_path}. Application is corrupt.", file=sys.stderr)
        sys.exit(1)

    # 3. Load and validate license structure
    try:
        with open(license_path, "r") as f:
            license_content = json.load(f)
        payload = license_content["payload"]
        signature = bytes.fromhex(license_content["signature"])
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    except (json.JSONDecodeError, KeyError):
        print("FATAL: License file is corrupted or invalid.", file=sys.stderr)
        sys.exit(1)

    # 4. Verify signature
    try:
        public_key.verify(
            signature,
            payload_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
    except InvalidSignature:
        print("FATAL: Invalid license signature. License has been tampered with.", file=sys.stderr)
        sys.exit(1)

    # 5. Check expiration
    try:
        expiration_date = datetime.fromisoformat(payload["expiration_date"])
        if expiration_date < datetime.utcnow():
            print(f"FATAL: License expired on {expiration_date.strftime('%Y-%m-%d')}.", file=sys.stderr)
            sys.exit(1)
    except (ValueError, KeyError):
         print("FATAL: Invalid expiration date in license.", file=sys.stderr)
         sys.exit(1)

    # 6. Check Machine ID
    current_machine_id = get_local_machine_id()
    if current_machine_id != payload.get("machine_id"):
        print("FATAL: This license is not valid for this machine.", file=sys.stderr)
        print(f"INFO: This machine's ID is: {current_machine_id}", file=sys.stderr)
        sys.exit(1)
        
    # 7. Success: Print the data key
    data_key = payload.get("data_key")
    if not data_key:
        print("FATAL: Data key is missing from license.", file=sys.stderr)
        sys.exit(1)
        
    print(data_key, end="")
    sys.exit(0)

if __name__ == "__main__":
    main() 