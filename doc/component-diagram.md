# Component Diagram — Promtior RAG Chatbot

Below is a high-level component diagram that shows the flow from user question to final answer.

```mermaid
flowchart LR
  U[User / Web UI] -->|Question| API[FastAPI + LangServe]
  API -->|Cache lookup| C[(SQLite Cache)]
  C -->|Hit: answer| API
  API -->|Miss| RAG[LangChain RAG Chain]
  RAG -->|Embed query| E[OpenAI Embeddings]
  RAG -->|Retrieve top-k| VS[(FAISS Vector Store)]
  VS -->|Context| RAG
  RAG -->|Prompt + context| LLM[OpenAI Chat Model]
  LLM -->|Answer| API
  API -->|Response| U

  subgraph Ingestion (offline)
    W[Promtior Website] --> S[Scraper]
    P[Promtior PDF] --> S
    S --> T[Text Splitter]
    T --> E2[OpenAI Embeddings]
    E2 --> VS
  end
```

Notes:
- The UI calls the custom `/promtior/ask` endpoint (cached), while LangServe exposes `/promtior/invoke` for direct chain access.
- The ingestion pipeline runs separately to build and persist the FAISS index.
