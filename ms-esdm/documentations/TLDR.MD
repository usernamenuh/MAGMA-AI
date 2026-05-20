# **Vendor → Client Shipping Flow (Docker + Licensing)**

```
[ Vendor Repo ]
┌─────────────────────────────┐
│ ms-esdm/                    │
│ ├─ main.py                  │
│ ├─ Dockerfile               │
│ └─ licensing/               │
│     └─ verify.py (PUBLIC_KEY) │
│ fe-esdm/                    │
│ └─ Dockerfile               │
│ license/                    │
│ ├─ private_key.pem ❌        │
│ └─ generate_license.py ❌    │
└─────────────────────────────┘
            │
            │ Build Docker Images
            ▼
┌─────────────────────────────┐
│ Vendor Docker Images        │
│ ms-esdm:1.0                 │
│ fe-esdm:1.0                 │
│ - Includes public key        │
│ - Includes app code          │
│ - Excludes private_key.pem   │
│ - Excludes generate_license.py │
└─────────────────────────────┘
            │
            │ Ship Images & License.json
            ▼
[ Client Environment ]
┌─────────────────────────────┐
│ docker-compose.yml          │
│ license/license.json        │
│ Docker images: ms-esdm, fe-esdm │
└─────────────────────────────┘
            │
            │ Run
            ▼
┌─────────────────────────────┐
│ Client Containers           │
│ ms-esdm → reads license.json │
│ licensing module verifies   │
│ - max_users                 │
│ - max_machines              │
│ - valid_from / valid_until  │
│ fe-esdm → internal service  │
└─────────────────────────────┘
```

---

## **Step-by-Step Summary**

1. **Vendor side:**
   - Generate RSA keys (`private_key.pem` / `public_key.pem`)  
   - Generate signed `license.json` using private key  
   - Build Docker images **without private key or generator**  

2. **Ship to client:**
   - Docker images (`ms-esdm:1.0`, `fe-esdm:1.0`)  
   - `docker-compose.yml`  
   - `license/license.json` (signed by vendor)  

3. **Client side:**
   - Place `license.json` in a Docker volume `/app/license`  
   - Run `docker-compose up -d`  
   - Containers validate license automatically at startup  
   - If license invalid/expired or machine limit exceeded → app won’t start  

---

## **Key Security Points**

- `private_key.pem` **never leaves vendor** → prevents license forgery  
- Client can only use the license you provide  
- Public key is safe to include in container → allows verification  

## **1️⃣ Structure Your Repo for Vendor vs Client**

Repo can look like this for building images:

```
product-root/
│
├── ms-esdm/
│   ├── main.py
│   ├── Dockerfile
│   └── licensing/
│       ├── verify.py          # contains PUBLIC_KEY
│       ├── schema.py
│       ├── service.py
│       ├── fingerprint.py
│       └── exceptions.py
│
├── fe-esdm/
│   └── Dockerfile
│
├── license/                   # Vendor-only folder
│   ├── private_key.pem        ❌
│   └── generate_license.py    ❌
│
├── docker-compose.yml
└── README.md
```

✅ **Important:**

* The `license/` folder **never gets copied into the Docker image**
* The **public key** is embedded inside `licensing/verify.py` → safe to ship

---

## **2️⃣ Dockerfile Example (ms-esdm)**

Make sure **private files never get copied**:

```dockerfile
# =========================
# Client Dockerfile (ms-esdm)
# =========================

# Base image
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (merged into ONE layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    antiword \
    fonts-dejavu \
    build-essential \
    libpq-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------
# Copy application code
# --------------------------
# Exclude private key and license generation scripts
COPY ms-esdm/ms_esdm ./ms-esdm/ms_esdm
COPY ms-esdm/licensing/verify.py ./ms-esdm/licensing/verify.py
# Do NOT copy private_key.pem or generate_license.py
# COPY ms-esdm/license/private_key.pem ./ms-esdm/license/private_key.pem  # ❌ REMOVE
# COPY ms-esdm/license/generate_license.py ./ms-esdm/license/generate_license.py  # ❌ REMOVE

# --------------------------
# License volume mount
# --------------------------
# Client will mount their license.json at runtime:
# docker run -v /path/to/license:/app/ms-esdm/license
VOLUME ["/app/ms-esdm/license"]

# Expose port for FastAPI
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "ms-esdm.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## **3️⃣ Generate License (Vendor Only)**

On your **local machine**, you run:

```bash
openssl genrsa -out license/private_key.pem 2048
openssl rsa -in license/private_key.pem -pubout -out license/public_key.pem
```

Then:

```bash
python license/generate_license.py
```

This creates **license/license.json** for the client.

❌ **Do NOT copy `private_key.pem` or `generate_license.py` into Docker**.

---

## **4️⃣ Build Docker Images**

```bash
docker build -t ms-esdm:1.0 ./ms-esdm
docker build -t fe-esdm:1.0 ./fe-esdm
```

You now have **client-ready images** that include:

* App code
* Licensing module (with public key)
* No private keys
* License is provided at runtime

---

## **5️⃣ Ship to Client**

Give the client:

* Docker images (`docker push` to a private registry or export tar)
* `docker-compose.yml`
* `license/license.json`

Client runs:

```bash
docker-compose up -d
```

The container reads the license from `/app/license/license.json`.
