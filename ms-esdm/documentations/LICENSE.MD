# 🔐 Licensing Guide

## Overview

This application enforces a signed license file with the following limits:

* `max_users` – Maximum number of users allowed
* `max_machines` – Maximum number of activated machines
* `valid_from` – License start date
* `valid_until` – License expiration date

The license is:

* Stored as a JSON file
* Cryptographically signed using RSA
* Verified at application startup
* Enforced on every request

The license file is **NOT stored in the database**.

The database only stores activated machine fingerprints.

---

# 📁 License File Location

Create this folder:

```
ms-esdm/license/
```

Create this file:

```
ms-esdm/license/license.json
```

---

# 🧪 Development Mode (Quick Start)

If you just want to run the system locally:

### 1️⃣ Add this test license:

```json
{
  "license_id": "DEV-LOCAL-001",
  "max_users": 5,
  "max_machines": 2,
  "valid_from": "2025-01-01T00:00:00",
  "valid_until": "2030-01-01T00:00:00",
  "signature": "DEV"
}
```

### 2️⃣ Temporarily disable signature verification

In:

```
licensing/verify.py
```

Replace:

```python
def verify_signature(license_dict: dict) -> bool:
```

With:

```python
def verify_signature(license_dict: dict) -> bool:
    return True
```

### 3️⃣ Run application

```bash
cd ms-esdm
uvicorn main:app --reload
```

---

# 🔒 Production Mode (Signed License)

## Step 1 – Generate RSA Keys (One Time Only)

Run:

```bash
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

You now have:

* `private_key.pem` → keep secret
* `public_key.pem` → embed in app

---

## Step 2 – Embed Public Key In App

Open `public_key.pem`

Copy entire content into:

```
licensing/verify.py
```

Example:

```python
PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE...
...rest of key...
-----END PUBLIC KEY-----"""
```

---

## Step 3 – Generate Signed License

Create file `generate_license.py` (vendor side only):

```python
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

with open("../license/private_key.pem", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

license_data = {
    "license_id": "CUSTOMER-001",
    "max_users": 10,
    "max_machines": 2,
    "valid_from": "2026-01-01T00:00:00",
    "valid_until": "2027-01-01T00:00:00"
}

message = json.dumps(license_data, sort_keys=True).encode()

signature = private_key.sign(
    message,
    padding.PKCS1v15(),
    hashes.SHA256()
)

license_data["signature"] = base64.b64encode(signature).decode()

with open("../license/license.json", "w") as f:
    json.dump(license_data, f, indent=2)

print("License generated.")
```

Run:

```bash
python generate_license.py
```

Move the generated `license.json` into:

```
ms-esdm/license/license.json
```

---

# 🚀 How To Run (Production Mode)

```bash
cd ms-esdm
export LICENSE_PATH=license/license.json
uvicorn main:app
```

If license is:

* Expired → app will not start
* Signature invalid → app will not start
* Machine limit exceeded → app will not start

---

# 🗄 Database Table

Auto-created at startup:

```
activated_machines
```

This table stores:

* machine fingerprint
* activation timestamp

---

# 🔎 Check License Status

Endpoint:

```
GET /api/license/status
```

Example response:

```json
{
  "license_id": "CUSTOMER-001",
  "valid_until": "2027-01-01T00:00:00",
  "max_users": 10,
  "max_machines": 2
}
```

---

# 🔄 Updating License

To upgrade:

1. Replace `license/license.json`
2. Restart application

---

# ⚠️ Important Security Notes

* Never commit `private_key.pem`
* Never commit real `license.json`
* Add to `.gitignore`:

```
license/
private_key.pem
```

---

# 🧠 How Enforcement Works

| Check                  | When                       |
| ---------------------- | -------------------------- |
| Signature verification | Startup                    |
| Date validation        | Startup + every request    |
| Machine limit          | Startup                    |
| User limit             | Enforced in business logic |

---

# 🧪 Testing Licensing Module

You can test the license enforcement code without starting the full app using `pytest`.

### 1️⃣ Install test dependencies

```bash
pip install pytest pytest-mock
```

### 2️⃣ Run test file

```bash
pytest tests/test_licensing.py -v
```

---

# 🎯 Summary

License file is:

* A signed contract
* Stored on disk
* Verified at startup
* Enforced at runtime

Database only stores activation state.
