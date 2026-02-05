# Promtior RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers factual questions about Promtior using only verified content from the official website and an optional company presentation PDF.

---

## Live Demo

Deployed chatbot:

- https://promtiorrag-production.up.railway.app/

Tip: Open the root URL to use the web UI.
To call the backend directly, send a POST request to `/promtior/ask`, for example:

```bash
curl -X POST "https://promtiorrag-production.up.railway.app/promtior/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What services does Promtior offer?"}'
```


---

## Features

- Context-grounded answers (no hallucinations)
- Website + PDF ingestion
- FAISS vector store persistence
- OpenAI-powered embeddings and generation
- SQLite caching for performance
- Dockerized and cloud-ready
- Simple web UI for demonstration

---

## Tech Stack

- Python 3.11+
- LangChain + LangServe
- FastAPI
- FAISS
- OpenAI API
- SQLite
- Docker

---

## Project Structure

```
├── app/
│   ├── ingestion.py
│   ├── langserve_app.py
│   ├── utils.py
│   ├── prompts/
│   │   └── promtior_prompt.md
│   └── static/
│       └── index.html
├── data/
│   └── promtior_presentation.pdf
├── vectorstore/
├── cache/
├── doc/
│   ├── project-overview.md
│   ├── component-diagram.md
│   └── deployment-and-testing.md
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0
VECTORSTORE_DIR=./vectorstore
DOCS_DIR=./data
CACHE_TTL_SECONDS=86400
```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Ingest Data

```bash
python -m app.ingestion
```

This will:
- Scrape the Promtior website (4 pages)
- Load the optional PDF from `/data`
- Build and persist the FAISS vector store

### 4. Run the API

```bash
uvicorn app.langserve_app:app --host 0.0.0.0 --port 8000
```

Visit: **http://localhost:8000**

---

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/` | Web UI for testing the chatbot |
| `POST /promtior/ask` | Custom endpoint with caching and sources (recommended) |
| `POST /promtior/invoke` | LangServe endpoint for the RAG chain |
| `/promtior/playground` | LangServe interactive playground |
| `/docs` | OpenAPI documentation |

### Example Request

```bash
curl -X POST "http://localhost:8000/promtior/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What services does Promtior offer?"}'
```

---

## Validation

Test with these required questions:

1. **What services does Promtior offer?**
2. **When was the company founded?**

Expected: Answers grounded in retrieved sources. If not found, the response will be: *"I don't have that information"*

---

## Deployment

For detailed deployment instructions (local, Docker, Railway), see **[doc/deployment-and-testing.md](doc/deployment-and-testing.md)**.

---

## Documentation

- **[doc/project-overview.md](doc/project-overview.md)** — Challenge description, architecture, design decisions, validation results
- **[doc/component-diagram.md](doc/component-diagram.md)** — Visual diagram of the RAG pipeline