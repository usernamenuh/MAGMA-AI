# 📖 API Documentation – Scraping & Analysis ESDM

## Overview

This API provides three main functionalities:

1. **Analyze (`/analyze`)** → Scrapes an API endpoint (based on user input), analyzes the response with **Mistral**, and saves the result into `log.json`.
2. **Logs (`/logs`)** → Retrieves saved analysis results from `log.json` with pagination.
3. **Scrapping (`/scrapping`)** → Scrapes raw data directly from API endpoints without analysis or logging.

---

## Base URL

```
http://localhost:8000
```

---

## 📌 Endpoints

### 1. 🔍 Analyze – `POST /analyze/`

Run the full pipeline: **recommend API → call API → analyze response → save log**.

#### Request

```json
{
  "user_input": "Show me the latest volcanic activity"
}
```

#### Response

```json
{
  "date": "2025-09-23T08:30:00.123Z",
  "user_input": "Show me the latest volcanic activity",
  "api_call": "https://magma.esdm.go.id/api/volcanoes",
  "output": "There were several volcanic activities reported this year..."
}
```

---

### 2. 📜 Logs – `GET /logs/`

Retrieve analysis history saved in `log.json`.

#### Query Parameters

* `page` (optional, default = 1)
* `limit` (optional, default = 10, max = 100)

#### Example Request

```
GET /logs?page=1&limit=5
```

#### Response

```json
{
  "page": 1,
  "limit": 5,
  "total": 23,
  "data": [
    {
      "date": "2025-09-23T08:30:00.123Z",
      "user_input": "Show me the latest volcanic activity",
      "api_call": "https://magma.esdm.go.id/api/volcanoes",
      "output": "There were several volcanic activities reported this year..."
    }
  ]
}
```

---

### 3. 🗂 Scrapping – `GET /scrapping/`

Scrape raw API data.
⚠️ This **does not analyze or log** the result.

#### Query Parameters

* `user_input` (optional)

    * If provided → scrape only the recommended API.
    * If empty → scrape all APIs in `examples_min.json`.
* `limit` (optional, default = 10)

    * Max items per API response (if supported).

#### Example 1 – With User Input

```
GET /scrapping?user_input=latest volcanic activity&limit=5
```

##### Response

```json
{
  "count": 1,
  "results": [
    {
      "api_call": "https://magma.esdm.go.id/api/volcanoes",
      "data": {
        "status": "success",
        "data": [
          { "volcano": "Merapi", "activity": "eruption", "date": "2025-09-21" },
          { "volcano": "Semeru", "activity": "ash cloud", "date": "2025-09-19" }
        ]
      }
    }
  ]
}
```

#### Example 2 – Scrap All APIs

```
GET /scrapping?limit=3
```

##### Response

```json
{
  "count": 5,
  "results": [
    {
      "api_call": "https://magma.esdm.go.id/api/volcanoes",
      "data": {...}
    },
    {
      "api_call": "https://magma.esdm.go.id/api/earthquakes",
      "data": {...}
    }
  ]
}
```

---

## ⚙️ Project Structure

```
project/
├── main.py              # FastAPI entrypoint
├── routes/
│   ├── analyze.py       # /analyze endpoint
│   ├── logs.py          # /logs endpoint
│   └── scrapping.py     # /scrapping endpoint
├── services/
│   ├── pipeline.py      # pipeline logic (recommend, call, analyze)
│   └── logger.py        # save/load logs
├── examples_min.json    # API examples reference
└── log.json             # Logs storage
```

---

## ▶️ Run Server

```bash
uvicorn main:app --reload
```

* Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
