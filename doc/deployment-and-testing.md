# Deployment and Testing Guide

This guide is written for the interview submission. It provides a clear, reproducible process to deploy and verify the RAG chatbot.

---

## A) Local Run (fastest validation)

1) Create and activate a virtual environment:

```bash
python -m venv .venv
./.venv/Scripts/activate
pip install -r requirements.txt
```

2) Create a .env file (local values):

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0
VECTORSTORE_DIR=./vectorstore
DOCS_DIR=./data
CACHE_TTL_SECONDS=86400
```

3) Ingest data (builds FAISS index):

```bash
python -m app.ingestion
```

4) Run the API:

```bash
uvicorn app.langserve_app:app --host 0.0.0.0 --port 8000
```

5) Test required questions:
- UI: http://localhost:8000
- API: POST /promtior/ask
- Playground: /promtior/playground

Required questions:
- What services does Promtior offer?
- When was the company founded?

Expected behavior:
- Answer must be grounded in retrieved content.
- If missing, respond exactly: “I don't have that information”.

---

## B) Railway Deployment (recommended)

Railway is accepted by the challenge and is the simplest cloud option.

1) Push this repo to GitHub.
2) In Railway, create a new project → “Deploy from GitHub”.
3) Set environment variables (container values):

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0
VECTORSTORE_DIR=/app/vectorstore
DOCS_DIR=/app/data
CACHE_TTL_SECONDS=86400
```

4) Deploy. The app will auto-build the vector store on first request if missing.
5) Open endpoints:
- / (UI)
- /promtior/ask
- /promtior/invoke
- /promtior/playground

---

## C) Optional: Azure App Service (container)

If you want an Azure-native option:

1) Create a container-based Web App in Azure App Service.
2) Point it to your GitHub repo (Dockerfile-based deployment).
3) Configure the same env vars as Railway (container values).
4) Deploy and test the same endpoints as in Railway.

---

## Interview Submission Checklist

- Public repo with code.
- /doc/project-overview.md updated.
- /doc/component-diagram.md present.
- The two required questions answered correctly.
- A clear deployment path (Railway or Azure).
