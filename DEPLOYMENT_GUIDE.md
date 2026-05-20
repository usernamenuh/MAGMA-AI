# ESDM Deployment Guide

Complete guide for running and deploying the ESDM stack in both development and production environments.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Clone the Repository](#3-clone-the-repository)
4. [Environment Configuration](#4-environment-configuration)
5. [Docker Deployment (Recommended)](#5-docker-deployment-recommended)
6. [Manual / Development Deployment](#6-manual--development-deployment)
7. [Service Reference](#7-service-reference)
8. [Production Checklist](#8-production-checklist)
9. [Common Operations](#9-common-operations)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Architecture Overview

The ESDM stack is composed of four services orchestrated by Docker Compose, fronted by a single nginx reverse proxy:

```
                        ┌──────────────────────┐
                        │   nginx  (port 80)   │
                        └──────┬───────┬───────┘
                               │       │
              ┌────────────────┘       └───────────────┐
              │  /                     /api/            │  /openai/
              ▼                          ▼              ▼
    ┌──────────────────┐   ┌─────────────────┐  ┌──────────────────┐
    │  fe-esdm         │   │  ms-esdm        │  │  openai_local    │
    │  React/Vite      │   │  FastAPI        │  │  llama-cpp-python│
    │  (port 3000)     │   │  (port 8000)    │  │  (port 8002)     │
    └──────────────────┘   └────────┬────────┘  └──────────────────┘
                                    │
                           ┌────────▼────────┐
                           │  PostgreSQL 15   │
                           │  + pgvector      │
                           │  (port 5432)     │
                           └─────────────────┘
```

| Service | Technology | Internal Port | Public Route |
|---|---|---|---|
| `fe-esdm` | React 19 + Vite + nginx | 3000 | `http://<server>/` |
| `ms-esdm` | FastAPI + Python 3.11 | 8000 | `http://<server>/api/` |
| `openai-local` | FastAPI + llama-cpp-python | 8002 | `http://<server>/openai/` |
| `db` | PostgreSQL 15 + pgvector | 5432 | internal only |

---

## 2. Prerequisites

### For Docker Deployment (Recommended)

| Requirement | Minimum Version | Notes |
|---|---|---|
| Docker Engine | 24+ | `docker --version` |
| Docker Compose | v2 plugin | `docker compose version` |
| Git | any | With submodule support |
| Disk space | ~10 GB | Node modules, model files, images |
| RAM | 8 GB | 16 GB recommended if loading GGUF models |

### For Manual / Development Deployment

| Requirement | Minimum Version |
|---|---|
| Python | 3.11+ |
| Node.js | 20+ |
| npm | 9+ |
| PostgreSQL | 15+ with pgvector extension |
| LibreOffice | any | Required by backend for document processing |

---

## 3. Clone the Repository

The project uses **Git submodules** for `ms-esdm`, `fe-esdm`, and `openai_local`. You must initialize them after cloning.

```bash
# Clone with all submodules in a single command
git clone --recurse-submodules <parent-repo-url> esdm-parent
cd esdm-parent
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

To pull updates for all submodules later:

```bash
git submodule update --remote --merge
```

After cloning, your directory should look like:

```
esdm-parent/
├── docker-compose.yml
├── nginx/nginx.conf
├── migrations/
├── fe-esdm/          ← React frontend
├── ms-esdm/          ← FastAPI backend
└── openai_local/     ← Local LLM service
```

---

## 4. Environment Configuration

Each service needs its own `.env` file. Create them from the provided examples before running anything.

### 4.1 Backend — `ms-esdm/.env`

```bash
cp ms-esdm/.env.example ms-esdm/.env
```

Edit `ms-esdm/.env`:

```env
# Database — use container hostname "db" when running in Docker
DATABASE_URL=postgresql+asyncpg://esdm_user:password@db:5432/esdm_db
SYNC_DATABASE_URL=postgresql+psycopg2://esdm_user:password@db:5432/esdm_db

# JWT — generate strong random secrets for production
JWT_SECRET_KEY=<generate-a-long-random-string>
JWT_REFRESH_SECRET_KEY=<generate-a-different-long-random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Internal key for inter-service requests
MS_KEY=sk-<your-internal-api-key>

# Local LLM — use container name when running in Docker
OPENAI_API_BASE=http://openai-local:8002/v1

# MAGMA integration
APP_ID=<your-app-id>
SECRET_KEY=<your-secret-key>
BASE_URL=https://magma.esdm.go.id

# Email domain allowlist for registration (comma-separated)
DOMAIN_EMAIL=@esdm.id,@esdm.go.id

# Set to "true" to skip license validation (development only)
DISABLE_LICENSE=false

# Optional
POSTMAN_API_KEY=
```

> **Important:** When running via Docker Compose, the database host **must** be `db` (the container name), not `localhost`. The same applies to `OPENAI_API_BASE` — use `http://openai-local:8002/v1`.

Generate secure JWT secrets:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4.2 Frontend — `fe-esdm/.env`

```bash
cp fe-esdm/.env.example fe-esdm/.env
```

Edit `fe-esdm/.env`:

```env
# Public API URL — this is the URL the BROWSER uses to reach the backend
# In Docker with nginx on port 80, use /api path prefix
VITE_API_URL=http://<your-server-ip-or-domain>

# Must match MS_KEY in ms-esdm/.env
VITE_MS_KEY=sk-<your-internal-api-key>
```

> `VITE_API_URL` is baked into the frontend build at compile time. If you change the server address you must rebuild the Docker image.

### 4.3 Local LLM — `openai_local/.env`

```bash
cp openai_local/env.example openai_local/.env
```

Edit `openai_local/.env`:

```env
# Path to the GGUF model file — relative path inside the container
MODEL_PATH=models/mistral-7b-instruct-v0.2.Q2_K.gguf
MODEL_NAME=mistral-7b-instruct

# Context window — reduce if you run out of memory
N_CTX=4096

# CPU threads — set to number of physical cores on the server
N_THREADS=8

# GPU offload layers — 0 for CPU-only, increase to use GPU VRAM
N_GPU_LAYERS=0

SEED=-1
F16_KV=true
VERBOSE=false

HOST=0.0.0.0
PORT=8002
LOG_LEVEL=info
```

### 4.4 Model Files

The `openai-local` service loads a GGUF model from the host filesystem via a Docker volume mount. The default path in `docker-compose.yml` is:

```yaml
volumes:
  - /home/gabriel-mac/models:/app/models
```

**You must change this path** to match your server. Edit `docker-compose.yml`:

```yaml
openai-local:
  ...
  volumes:
    - /path/to/your/models:/app/models   # ← change left side to your host path
```

Place your GGUF model file at that host path. Example for Mistral 7B:

```bash
# Create models directory and download a model
mkdir -p /opt/esdm-models
# Download from Hugging Face (example — adjust as needed)
wget -P /opt/esdm-models https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

Then update `docker-compose.yml` and `openai_local/.env` with the matching path and filename.

---

## 5. Docker Deployment (Recommended)

This is the recommended method for server / production deployments.

### 5.1 First-Time Setup

```bash
# 1. Navigate to the parent directory
cd esdm-parent

# 2. Complete environment configuration (Section 4 above)

# 3. Update the model volume path in docker-compose.yml if not already done

# 4. Build and start all services
sudo docker compose up --build -d
```

Docker Compose will:
- Pull `pgvector/pgvector:pg15` and `nginx:latest`
- Build the backend (`ms-esdm`), frontend (`fe-esdm`), and LLM (`openai_local`) images
- Start PostgreSQL and run the init script (`ms-esdm/db-init/init.sql`)
- Start the backend, which creates all tables via SQLAlchemy on first run
- Start the LLM service and load the model into memory (this takes time)
- Start the frontend
- Start nginx on port 80

### 5.2 Verify Services Are Running

```bash
# Check all container statuses
sudo docker compose ps

# View logs for all services
sudo docker compose logs -f

# View logs for a specific service
sudo docker compose logs -f backend
sudo docker compose logs -f openai-local
sudo docker compose logs -f db
```

Expected output of `docker compose ps` when healthy:

```
NAME                STATUS          PORTS
esdm-nginx          running         0.0.0.0:80->80/tcp
ms-esdm-backend     running (healthy)
fe-esdm-frontend    running
openai-local        running
esdm-postgres       running (healthy)   0.0.0.0:5432->5432/tcp
```

### 5.3 Access the Application

| URL | What |
|---|---|
| `http://<server-ip>/` | Web application (frontend) |
| `http://<server-ip>/api/docs` | Backend Swagger UI |
| `http://<server-ip>/api/redoc` | Backend ReDoc |
| `http://<server-ip>/openai/v1/models` | Local LLM — list available models |
| `http://<server-ip>/openai/v1/chat/completions` | Local LLM — chat endpoint |

### 5.4 Rebuild After Changes

If you change any source code, Dockerfile, or dependency:

```bash
# Rebuild and restart a specific service (faster)
sudo docker compose up --build -d backend

# Rebuild everything
sudo docker compose up --build -d
```

If you only change environment variables (not code), restart without rebuilding:

```bash
sudo docker compose restart backend
```

### 5.5 Stop and Remove Services

```bash
# Stop all containers (data is preserved)
sudo docker compose down

# Stop and remove containers + network (data is preserved)
sudo docker compose down

# Remove everything including the PostgreSQL data volume
# ⚠️ WARNING: This deletes all database data permanently
sudo docker compose down -v
```

---

## 6. Manual / Development Deployment

Use this method for local development when you want hot-reload and faster iteration.

### 6.1 Database

Start PostgreSQL with the pgvector extension. The easiest option is Docker:

```bash
docker run -d \
  --name esdm-postgres \
  -e POSTGRES_USER=esdm_user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=esdm_db \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

Or set it up manually on an existing PostgreSQL 15 instance:

```sql
-- Run as postgres superuser
CREATE DATABASE esdm_db;
CREATE USER esdm_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE esdm_db TO esdm_user;

\c esdm_db

CREATE EXTENSION IF NOT EXISTS vector;
```

### 6.2 Backend (`ms-esdm`)

```bash
cd ms-esdm

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables
# Edit ms-esdm/.env and set DATABASE_URL to use localhost:
# DATABASE_URL=postgresql+asyncpg://esdm_user:password@localhost:5432/esdm_db
# SYNC_DATABASE_URL=postgresql+psycopg2://esdm_user:password@localhost:5432/esdm_db
# OPENAI_API_BASE=http://localhost:8002/v1

# Start the backend with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 6.3 Local LLM Service (`openai_local`)

```bash
cd openai_local

# Create and activate virtual environment
python3.11 -m venv openai-venv
source openai-venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
# Edit openai_local/.env — set MODEL_PATH to absolute path of your GGUF file

# Start the LLM service (listens on port 8002)
python main.py
```

> Note: Loading a 7B+ parameter model takes 30–120 seconds depending on hardware. Watch the logs for "Model loaded" confirmation.

### 6.4 Frontend (`fe-esdm`)

```bash
cd fe-esdm

# Install dependencies
npm install

# Configure environment
# Edit fe-esdm/.env:
# VITE_API_URL=http://localhost:8000

# Start Vite dev server (port 3000, hot-reload enabled)
npm run dev
```

Frontend available at `http://localhost:3000`.

To build a production bundle:

```bash
npm run build
# Output is in fe-esdm/dist/
npm run preview  # preview the production build locally
```

---

## 7. Service Reference

### 7.1 Backend API Endpoints

| Route | Description |
|---|---|
| `POST /auth/register` | Register a new user |
| `POST /auth/login` | Login and obtain JWT token |
| `GET /auth/me` | Get current user info |
| `GET /analyze/...` | Data analysis endpoints |
| `GET /logs/...` | Log management |
| `GET /scrapping/...` | Web scraping utilities |
| `GET /api-keys/...` | API key management |
| `GET /knowledge/...` | Knowledge base CRUD |
| `GET /chat/...` | Chat history endpoints |

Full interactive API docs: `http://<server>/api/docs`

### 7.2 Local LLM API Endpoints

The `openai_local` service is OpenAI-compatible. Endpoints:

| Route | Description |
|---|---|
| `GET /v1/models` | List available models |
| `POST /v1/chat/completions` | Chat with the model (streaming supported) |
| `POST /v1/embeddings` | Generate text embeddings |
| `GET /v1/api-keys` | Manage LLM API keys |

Via nginx proxy: replace `/v1/` with `/openai/v1/` in the URLs above.

### 7.3 Environment Variables Reference

#### `ms-esdm/.env`

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `SYNC_DATABASE_URL` | Yes | — | Sync PostgreSQL URL (`postgresql+psycopg2://...`) |
| `JWT_SECRET_KEY` | Yes | `secret_key` | JWT signing secret |
| `JWT_REFRESH_SECRET_KEY` | No | `refresh_secret_key` | JWT refresh token secret |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_EXPIRATION_MINUTES` | No | `60` | Access token lifetime |
| `MISTRAL_API_KEY` | No | — | Mistral AI API key |
| `OPENAI_API_KEY` | No | — | OpenAI API key |
| `GEMINI_API_KEY` | No | — | Gemini API key |
| `OPENAI_API_BASE` | Yes | — | Base URL for local LLM |
| `MS_KEY` | Yes | — | Internal auth key (must match `VITE_MS_KEY`) |
| `APP_ID` | No | — | MAGMA integration app ID |
| `SECRET_KEY` | No | — | MAGMA integration secret |
| `BASE_URL` | No | `https://magma.esdm.go.id` | MAGMA base URL |
| `DOMAIN_EMAIL` | No | `@esdm.gov.id,...` | Comma-separated allowed email domains |
| `DISABLE_LICENSE` | No | `false` | Skip license check (dev only) |

#### `fe-esdm/.env`

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes | Base URL the browser uses to reach the backend |
| `VITE_MS_KEY` | Yes | Internal key (must match `MS_KEY` in backend) |

#### `openai_local/.env`

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL_PATH` | Yes | — | Path to GGUF model file (relative to `/app/`) |
| `MODEL_NAME` | No | `mistral-7b-instruct` | Model display name |
| `N_CTX` | No | `4096` | Context window size in tokens |
| `N_THREADS` | No | `4` | CPU threads for inference |
| `N_GPU_LAYERS` | No | `0` | GPU layers to offload (0 = CPU only) |
| `F16_KV` | No | `true` | Use fp16 key/value cache |
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8000` | Ignored in parent compose (hardcoded 8002) |
| `LOG_LEVEL` | No | `info` | Logging verbosity |

---

## 8. Production Checklist

Before going live, verify each item:

### Security

- [ ] Replace all default passwords and secrets in `.env` files
- [ ] Generate strong JWT secrets: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set `DISABLE_LICENSE=false` (or remove the variable entirely)
- [ ] Restrict `DOMAIN_EMAIL` to only your organization's domains
- [ ] Do not expose port `5432` (PostgreSQL) to the public internet — remove the `ports` mapping in `docker-compose.yml` if external DB access is not needed
- [ ] Use HTTPS — place a TLS-terminating reverse proxy (e.g., Caddy, Traefik, or another nginx instance) in front of the stack

### Configuration

- [ ] Set `VITE_API_URL` to your actual public domain/IP (not localhost)
- [ ] Update the model volume path in `docker-compose.yml` to your server's model directory
- [ ] Set `OPENAI_API_BASE=http://openai-local:8002/v1` in `ms-esdm/.env` (container hostname, not localhost)
- [ ] Confirm the GGUF model file exists at the mounted host path
- [ ] Tune `N_THREADS` in `openai_local/.env` to match your server's CPU core count
- [ ] Increase `N_GPU_LAYERS` if the server has a GPU with sufficient VRAM

### Verification

- [ ] `sudo docker compose ps` — all containers show `running` or `running (healthy)`
- [ ] `http://<server>/` — frontend loads
- [ ] `http://<server>/api/docs` — Swagger UI loads
- [ ] `http://<server>/openai/v1/models` — model list returns JSON
- [ ] Register a new user and verify email domain restriction works
- [ ] Send a test chat message and verify LLM responds

---

## 9. Common Operations

### View Logs

```bash
# All services, follow mode
sudo docker compose logs -f

# Single service
sudo docker compose logs -f backend
sudo docker compose logs -f openai-local
sudo docker compose logs -f db
sudo docker compose logs -f nginx
sudo docker compose logs -f frontend
```

### Access the Database

```bash
# Open psql inside the running container
sudo docker compose exec db psql -U esdm_user -d esdm_db

# Run a single query
sudo docker compose exec db psql -U esdm_user -d esdm_db -c "SELECT count(*) FROM users;"
```

### Backup the Database

```bash
# Dump to file
sudo docker compose exec db pg_dump -U esdm_user esdm_db > backup_$(date +%Y%m%d).sql

# Restore from dump
sudo docker compose exec -T db psql -U esdm_user esdm_db < backup_20260101.sql
```

### Update Source Code

```bash
# Pull latest changes in all submodules
git submodule update --remote --merge

# Rebuild and restart only the changed service
sudo docker compose up --build -d backend
sudo docker compose up --build -d frontend
```

### Restart a Single Service

```bash
sudo docker compose restart backend
sudo docker compose restart openai-local
```

### Scale / Resource Limits

To add memory limits (recommended for production), edit `docker-compose.yml`:

```yaml
services:
  openai-local:
    ...
    deploy:
      resources:
        limits:
          memory: 8G
```

---

## 10. Troubleshooting

### Backend fails to start — database connection refused

**Symptom:** `ms-esdm-backend` exits immediately with a connection error.

**Cause:** The database is not ready, or `DATABASE_URL` uses `localhost` instead of `db`.

**Fix:**
1. Check `ms-esdm/.env` — both `DATABASE_URL` and `SYNC_DATABASE_URL` must use `db` as the host.
2. Verify the database container is healthy: `sudo docker compose ps db`
3. Check DB logs: `sudo docker compose logs db`

---

### `openai-local` service crashes on startup

**Symptom:** Container exits immediately after starting.

**Cause:** Model file not found, or out of memory.

**Fix:**
1. Verify the host model directory exists and contains the GGUF file.
2. Double-check the volume mount in `docker-compose.yml` matches the host path.
3. Verify `MODEL_PATH` in `openai_local/.env` matches the filename.
4. Check available RAM — a 7B Q4 model requires ~5 GB RAM minimum.

```bash
sudo docker compose logs openai-local
```

---

### Frontend shows blank page or API errors

**Symptom:** App loads but API calls fail (CORS or network error in browser console).

**Fix:**
1. Verify `VITE_API_URL` in `fe-esdm/.env` points to the correct server address.
2. Remember that `VITE_*` variables are baked in at build time — rebuild the image after changing them: `sudo docker compose up --build -d frontend`
3. Check nginx is running: `sudo docker compose logs nginx`

---

### Port 80 is already in use

**Symptom:** `Error starting userland proxy: ... bind: address already in use`

**Fix:** Find and stop the conflicting process, or change the nginx port in `docker-compose.yml`:

```bash
sudo lsof -i :80

# Or change the port mapping
# In docker-compose.yml, under nginx:
#   ports:
#     - "8080:80"   ← access via port 8080 instead
```

---

### Database volume already exists with wrong schema

**Symptom:** SQLAlchemy errors about missing columns after an update.

**Fix:** The database schema is managed by SQLAlchemy `create_all` (adds new tables) and optional migration scripts in `migrations/`. For a clean slate in development:

```bash
# WARNING: destroys all data
sudo docker compose down -v
sudo docker compose up --build -d
```

---

### Submodule directories are empty

**Symptom:** `ms-esdm/`, `fe-esdm/`, or `openai_local/` directories exist but are empty.

**Fix:**

```bash
git submodule update --init --recursive
```

---

### Check which container is using the most resources

```bash
sudo docker stats
```

---

## Quick Reference

```bash
# Start everything (first time or after changes)
sudo docker compose up --build -d

# Check status
sudo docker compose ps

# View all logs
sudo docker compose logs -f

# Stop everything
sudo docker compose down

# Stop + wipe database volume (⚠️ destructive)
sudo docker compose down -v

# Rebuild one service
sudo docker compose up --build -d backend

# Open database shell
sudo docker compose exec db psql -U esdm_user -d esdm_db
```
