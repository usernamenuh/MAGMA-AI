# MS-ESDM

`ms-esdm` is a FastAPI-based service providing endpoints for analysis, scrapping, knowledge management, chat history, and authentication.

## Features

* User Authentication (`/auth`)
* Data Analysis (`/analyze`)
* Logs Management (`/logs`)
* Web Scrapping (`/scrapping`)
* API Key Management (`/api-keys`)
* Knowledge Documents (`/knowledge`)
* Chat History (`/chat`)

---

## Prerequisites

* Python 3.11+
* PostgreSQL 15+
* Docker (optional, for database)
* `pip` for dependencies

---

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/ms-esdm.git
cd ms-esdm
```

---

## 2. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

---

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Set Environment Variables

Create a `.env` file in the root:

```env
DATABASE_URL=postgresql+psycopg2://esdm_user:password@localhost:5432/esdm_db
JWT_SECRET_KEY=your_jwt_secret
MISTRAL_API_KEY=your_mistral_api_key
APP_ID=your_app_id
SECRET_KEY=your_secret_key
BASE_URL=https://vsi.esdm.go.id/data
OPENAI_API_BASE=http://localhost:8002/v1 #(run in the TPU server)
MS_KEY=sk-your-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
POSTMAN_API_KEY=your_postman_key
```

---

## 5. Create PostgreSQL Database

You can create the database manually or using `psql`:

```bash
-- Login to PostgreSQL
psql -U postgres

-- Create database and user
CREATE DATABASE esdm_db;
CREATE USER esdm_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE esdm_db TO esdm_user;

-- Connect to the new database
\c esdm_db

-- Create vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Exit
\q
```

---

## 6. Run the OpenAI Local and FastAPI App

In OpenAI local (TPU server):

```bash
cd openai_local/
source openai-venv/bin/activate
python main.py
```

In this project: 
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

* API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 7. Test API Endpoints

* `/auth`: Login/Register
* `/analyze`: Data analysis endpoints
* `/logs`: Fetch logs
* `/scrapping`: Scrapping endpoints
* `/api-keys`: Manage API keys
* `/knowledge`: Knowledge document CRUD
* `/chat`: Chat history endpoints

---

Here is an updated **README section with a new "Run with Docker" section**, including the proper `docker-compose` command and clear instructions.

You can paste this under your current documentation.

---

# 8. Run with Docker (Recommended)

You can run the entire service—including FastAPI and PostgreSQL—using Docker Compose.

## **Start Containers**

```bash
sudo docker compose up --build
```

This will:

✔ Build the FastAPI image
✔ Start PostgreSQL with initialization
✔ Run migrations (if configured)
✔ Start the FastAPI server on **[http://localhost:8000](http://localhost:8000)**

---

## **Environment Variables for Docker**

Make sure your `.env` uses **container hostnames**, not localhost:

```env
DATABASE_URL=postgresql+psycopg2://esdm_user:password@db:5432/esdm_db
```

---

## **Rebuild & Restart**

If you update dependencies or Dockerfile:

```bash
sudo docker compose up --build -d
```

To stop:

```bash
sudo docker compose down
```

To remove everything including DB volume (not recommended for prod/deployment):

```bash
sudo docker compose down -v
```

# 9. Run Testing Answer Quality
You need `oauth_client.json` to access google drive for run this testing

```bash
python test-kb-answer-quality.py
```

# 10. Run Synchronize knowledge base to drive
You need `oauth_client.json` to access google drive for run this testing
```bash
python sync-knowledge-base.py
```
