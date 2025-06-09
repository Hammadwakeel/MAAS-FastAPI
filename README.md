Here’s an updated `README.md` for your `MAAS` project, reflecting the expanded functionality and project structure that now includes the RAG-based chat system in addition to PageSpeed insights and Gemini-based analysis.

---

# MAAS API (Metrics & AI-Assisted Suggestions)

A professional FastAPI application that offers two core services:

1. **PageSpeed Performance Reports** – Using Google's PageSpeed Insights and Gemini AI for analysis and recommendations.
2. **RAG-Powered Chat System** – Retrieval-Augmented Generation (RAG) chat sessions with document ingestion, vectorstore indexing (FAISS), and persistent chat history (MongoDB).

## ✨ Features

* 🔍 PageSpeed Insights integration for web performance metrics
* 🤖 Gemini AI–powered optimization report generation
* 📚 Document ingestion and chunked embedding with FAISS
* 💬 RAG-based conversational system per user and chat session
* 📄 Clean modular FastAPI architecture
* 🛠️ Configuration via environment variables
* 🔐 Secure, with input validation and API key protection
* 📈 Built-in health check, detailed logging, and auto-generated API docs

---

## 🗂 Project Structure

```
MAAS/
├── app/
│   ├── rag/                         # RAG module for document ingestion and chat
│   │   ├── db.py
│   │   ├── embedding.py
│   │   ├── routes.py               # RAG API endpoints
│   │   ├── schemas.py
│   │   └── utils.py
│   ├── config.py                   # Environment & settings
│   ├── main.py                     # FastAPI app instance & routers
│   ├── models.py                   # Pydantic models
│   ├── run_server.py               # Server runner
│   └── services.py                 # PageSpeed + Gemini logic
├── Dockerfile                      # Optional containerization
├── requirements.txt                # Dependencies
└── README.md                       # You're reading it
```

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

```env
PAGESPEED_API_KEY=your_pagespeed_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URI=mongodb://localhost:27017
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### 3. Run the Application

```bash
# Option 1: Using the script
python run_server.py

# Option 2: Directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📘 API Overview

### 🔗 General

| Method | Endpoint  | Description                    |
| ------ | --------- | ------------------------------ |
| GET    | `/`       | Welcome + links to docs/health |
| GET    | `/health` | Health check and uptime        |

---

### 🧠 PageSpeed + Gemini Endpoints

| Method | Endpoint               | Description                       |
| ------ | ---------------------- | --------------------------------- |
| POST   | `/pagespeed`           | Fetch raw PageSpeed Insights JSON |
| POST   | `/generate-report`     | Generate AI optimization report   |
| POST   | `/generate-priorities` | Rank optimizations by priority    |

---

### 📚 RAG Chat System Endpoints

| Method | Endpoint                        | Description                                |
| ------ | ------------------------------- | ------------------------------------------ |
| POST   | `/rag/ingest/{user_id}`         | Ingest documents and store FAISS index     |
| POST   | `/rag/chat/create/{user_id}`    | Start a new chat session (returns chat ID) |
| POST   | `/rag/chat/{user_id}/{chat_id}` | Ask a question in an existing chat session |

---

## 📎 RAG Workflow

1. **Ingest Documents**

   * POST `/rag/ingest/{user_id}`
   * Body: `{"documents": ["doc 1 text", "doc 2 text", ...]}`

2. **Create Chat**

   * POST `/rag/chat/create/{user_id}`
   * Response: `chat_id`

3. **Ask Questions**

   * POST `/rag/chat/{user_id}/{chat_id}`
   * Body: `{"question": "What does the document say about X?"}`

---

## 🛠 Example Usage (Python)

```python
import requests

# Ingest docs
requests.post("http://localhost:8000/rag/ingest/user123", json={
    "documents": ["The capital of France is Paris.", "Python is a programming language."]
})

# Create chat
res = requests.post("http://localhost:8000/rag/chat/create/user123")
chat_id = res.json()["chat_id"]

# Chat
requests.post(f"http://localhost:8000/rag/chat/user123/{chat_id}", json={
    "question": "What is the capital of France?"
})
```

---

## 📄 API Docs

Once the app is running:

* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🛡️ Error Handling

* `400 Bad Request`: Invalid input
* `404 Not Found`: Unknown endpoint or missing user/chat/doc
* `500 Internal Server Error`: API or service errors

---

## 🧪 Development Tips

* Use `DEBUG=True` in `.env` for auto-reload and verbose logs
* Modify `CORS` policy in `main.py` before production
* Use `logger` calls to trace errors or logic flows

---

## 🌍 API Key Setup

### PageSpeed Insights

1. [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the API, generate a key

### Gemini AI

1. [Google AI Studio](https://makersuite.google.com/)
2. Create API Key

Add both to your `.env`.

---

## 📦 Docker Support

Basic Dockerfile is included. To build and run:

```bash
docker build -t maas-api .
docker run -p 8000:8000 --env-file .env maas-api
```

---

## 🤝 Contributing

1. Follow existing modular structure
2. Document all new endpoints clearly
3. Test edge cases (e.g., malformed docs or bad chat IDs)
4. Use logging for traceability
5. Create clear, typed Pydantic schemas

---

## 📜 License

Licensed under the MIT License.

---

## 🔗 Repository

[https://github.com/Hammadwakeel/MAAS](https://github.com/Hammadwakeel/MAAS)

---
