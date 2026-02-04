# Project Overview — Promtior RAG Chatbot

## Assignment Challenge

**Objective**: Design, implement, and deploy a chatbot that uses the RAG (Retrieval Augmented Generation) architecture to answer questions about the Promtior company website.

**Required Questions**:
- What services does Promtior offer?
- When was the company founded?

**Tech Stack**:
- LangChain with LangServe
- OpenAI API (gpt-4o-mini)
- FAISS vector store
- FastAPI
- Docker for containerization
- Cloud deployment (Railway recommended)

**Required Documentation**:
- Project overview (this document)
- Component diagram showing interactions
- Comprehensive deployment guide

---

## Implementation Approach

This solution implements a production-ready RAG architecture that prioritizes **accuracy, grounding, and non-hallucination** over generative flexibility. The chatbot answers ONLY using verified sources; if the answer is not found, it explicitly states: "I don't have that information".

---

## System Architecture (Question to Answer Flow)

The solution follows a standard but production-ready RAG architecture with five main stages:

1. **Content Ingestion**
   - Public website content is scraped and normalized.
   - An optional Promtior PDF presentation is ingested to enrich the knowledge base.
   - Documents are split into semantically coherent chunks.
   - Each chunk is embedded using OpenAI embeddings.
   - Embeddings are persisted locally using a FAISS vector store.

2. **Retrieval**
   - At query time, the user question is embedded and compared against the FAISS index.
   - The top-K most relevant chunks are retrieved.
   - No additional knowledge beyond the retrieved context is allowed.

3. **Generation**
   - A strict prompt instructs the LLM to answer **only** using the retrieved context.
   - If the answer is not present, the assistant must reply exactly:
     > “I don't have that information”.
   - This constraint prevents hallucinations and ensures factual correctness.

4. **API Layer (LangServe + FastAPI)**
   - **LangServe Integration**: Exposes the RAG chain via standard endpoints (`/promtior/invoke` for direct chain access, `/promtior/playground` for UI).
   - **Custom Endpoint**: `/promtior/ask` provides a production-ready endpoint with SQLite caching to avoid redundant LLM calls.
   - **Caching Strategy**: Responses are cached with a configurable TTL (default 24 hours) to reduce API costs and improve latency.
   - **LangChain Composition**: The retriever and LLM are composed using LangChain's `create_retrieval_chain` and `create_stuff_documents_chain` for robust document inclusion.

5. **Frontend and Deployment**
   - A lightweight single-page application (SPA) provides an intuitive user interface for testing.
   - The entire application is containerized using Docker for reproducible deployments.
   - **Auto-initialization**: The vector store is automatically built on first API request if missing (useful for cloud platforms).
   - **Multi-platform Ready**: Verified to work on Railway, AWS App Service, and other container-based cloud platforms.

---

## Key Design Decisions

- **Strict RAG grounding**  
  The assistant intentionally refuses to answer questions that go beyond the ingested content.  
  This behavior is considered a feature, not a limitation, and reflects real-world production best practices.

- **FAISS as Vector Store**  
  FAISS was chosen for its speed, local persistence, and simplicity, which are appropriate for the scope of the challenge.

- **Externalized Prompting**  
  Prompts are stored in a dedicated file to allow easy iteration and auditing.

- **Deterministic LLM Configuration**  
  Temperature is set to zero to ensure consistent and reproducible answers during evaluation.

- **Caching Layer**  
  A lightweight SQLite cache improves performance and reduces OpenAI API usage without adding operational complexity.

---

## Main Challenges Encountered and Solutions

**1) Preventing Hallucinations and Ensuring Factual Accuracy**
- **Challenge**: Early implementations allowed the LLM to infer or extrapolate beyond the retrieved documents.
- **Solution**: Implemented a strict prompt contract that explicitly instructs the LLM to ONLY use retrieved context. If the answer is not present, a deterministic fallback response ("I don't have that information") is enforced. Temperature is set to 0 for reproducibility.

**2) Vector Store Persistence Across Local and Cloud Environments**
- **Challenge**: Local development uses relative paths (./vectorstore), but containerized deployments expect absolute paths (/app/vectorstore). This inconsistency broke deployments.
- **Solution**: Made environment variables configurable (VECTORSTORE_DIR, DOCS_DIR) so the same code works in both local and cloud environments. Added auto-initialization so the vector store is built on first request if missing.

**3) LangChain and OpenAI SDK Compatibility**
- **Challenge**: LangChain 0.3.x, LangServe, and OpenAI SDK versions have interdependencies that can break unexpectedly.
- **Solution**: Pinned compatible versions in requirements.txt (langchain==0.3.27, langchain-openai==0.2.9, openai>=1.0.0). Added fallback code paths so the API still works if the primary chain fails.

**4) Dependency Resolution in Python 3.12**
- **Challenge**: langchain-text-splitters version was too old for Python 3.12.
- **Solution**: Updated to langchain-text-splitters==0.3.11 and httpx==0.27.2 for compatibility.

**5) Data Ingestion from Dynamic Sources**
- **Challenge**: Scraping the website could fail due to network issues or HTML structure changes.
- **Solution**: Implemented robust error handling with user-agent headers and try-catch blocks. The PDF is optional to support partial failure. Logs show which sources succeeded.

---

## Validation Results

**Local Testing (Verified ✓)**:
- Both required questions are answered correctly and are fully grounded in retrieved sources.
- Responses consistently match the PDF and website content.
- Caching mechanism works as expected.

**Deployment Readiness**:
- Code is containerized and verified to run in Docker.
- Environment variables are documented for local, Docker, and cloud deployments.
- Auto-initialization ensures the vector store is always available.

**Code Quality**:
- Clean separation of concerns (ingestion, API, utils).
- Type hints and error handling throughout.
- Comprehensive logging for debugging.

---

## Step-by-Step: Local Validation

To validate this solution locally before submission:

```bash
# 1. Setup environment
python -m venv .venv
./.venv/Scripts/activate
pip install -r requirements.txt

# 2. Set environment variables
set OPENAI_API_KEY=your_key
set OPENAI_MODEL=gpt-4o-mini
set OPENAI_TEMPERATURE=0
set VECTORSTORE_DIR=./vectorstore
set DOCS_DIR=./data

# 3. Build the vector store
python -m app.ingestion

# 4. Run the API
uvicorn app.langserve_app:app --host 0.0.0.0 --port 8000

# 5. Test the required questions
# - UI: http://localhost:8000
# - What services does Promtior offer?
# - When was the company founded?
```

For detailed cloud deployment steps, see [deployment-and-testing.md](./deployment-and-testing.md).
