# 🏗️ **Parent Repository for ESDM**

This repository contains two child services:

* **`ms-esdm`** — A FastAPI-based backend service providing:

  * Analysis endpoints
  * Scraping utilities
  * Knowledge management
  * Chat history
  * Authentication

* **`fe-esdm`** — A React frontend application that delivers the UI for interacting with the ESDM system, including  knowledge search, chat interface, API Keys, user authentication, etc.

---

# 🐳 Run with Docker

You can run the entire stack—including FastAPI and PostgreSQL—using **Docker Compose**.

## ▶️ **Start Containers**

```bash
sudo docker compose up --build
```

This will:

* ✔ Build the FastAPI image
* ✔ Start PostgreSQL with initialization
* ✔ Run migrations (if configured)
* ✔ Start the FastAPI server at **[http://localhost:8000](http://localhost:8000)**

---

## 🔧 **Environment Variables (Docker)**

Your `.env` file must use **container hostnames** (e.g., `db`) instead of `localhost`:

```env
DATABASE_URL=postgresql+psycopg2://esdm_user:password@db:5432/esdm_db
```

---

## 🔄 **Rebuild & Restart**

If you change dependencies, Dockerfile, or environment:

```bash
sudo docker compose up --build -d
```

---

## 🛑 **Stop Services**

```bash
sudo docker compose down
```

---

## 🧹 **Remove Everything (Including DB Volume)**

> ⚠️ **Warning:** This removes your PostgreSQL data.

```bash
sudo docker compose down -v
```