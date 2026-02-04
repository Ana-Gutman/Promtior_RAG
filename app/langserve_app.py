import os
import json
import sqlite3
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.runnables import RunnableLambda

try:
    from langchain.chains import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
    HAS_CREATE_CHAIN = True
except Exception:
    HAS_CREATE_CHAIN = False
    from langchain.chains import RetrievalQA

from langchain.prompts import PromptTemplate

# LangServe
from langserve import add_routes

from openai import OpenAI

APP_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_ROOT / "app" / "prompts" / "promtior_prompt.md"
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", str(APP_ROOT / "vectorstore"))
CACHE_DB = APP_ROOT / "cache" / "cache.db"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))

app = FastAPI(title="Promtior RAG")

# serve static SPA under root
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "app" / "static")), name="static")

@app.get("/", include_in_schema=False)
def root_index():
    index_file = APP_ROOT / "app" / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index not found")
    return FileResponse(index_file)

# SQLite cache helpers
def init_cache():
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache (query TEXT PRIMARY KEY, answer TEXT, sources TEXT, created_at INTEGER)"
    )
    conn.commit()
    conn.close()

def get_cached(query: str):
    conn = sqlite3.connect(str(CACHE_DB))
    cur = conn.cursor()
    cur.execute("SELECT answer, sources, created_at FROM cache WHERE query = ?", (query,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    answer, sources_json, created_at = row
    if int(time.time()) - int(created_at) > CACHE_TTL_SECONDS:
        return None
    try:
        sources = json.loads(sources_json)
    except Exception:
        sources = []
    return {"answer": answer, "sources": sources}

def set_cached(query: str, answer: str, sources):
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("REPLACE INTO cache (query, answer, sources, created_at) VALUES (?, ?, ?, ?)",
                 (query, answer, json.dumps(sources, ensure_ascii=False), int(time.time())))
    conn.commit()
    conn.close()

# Lazy load components
_embeddings = None
_vectorstore = None
_retriever = None
_llm = None
_rag_chain = None
_prompt_template = None

def load_prompt():
    global _prompt_template
    if _prompt_template is not None:
        return _prompt_template
    if PROMPT_PATH.exists():
        txt = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        txt = ("You are an assistant that answers using only provided context. "
               "If not present say: 'I don't have that information'.\n\n"
               "Context:\n{context}\n\nQuestion:\n{input}\n\nAnswer:")
    _prompt_template = PromptTemplate.from_template(txt)
    return _prompt_template


def ensure_components():
    global _embeddings, _vectorstore, _retriever, _llm, _rag_chain
    if _rag_chain is not None:
        return
    if not Path(VECTORSTORE_DIR).exists():
        from app.ingestion import main as ingest_main
        ingest_main()
    _embeddings = OpenAIEmbeddings()
    _vectorstore = FAISS.load_local(VECTORSTORE_DIR, _embeddings, allow_dangerous_deserialization=True)
    _retriever = _vectorstore.as_retriever(search_kwargs={"k": 4})
    _llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=float(os.getenv("OPENAI_TEMPERATURE", "0")))
    prompt = load_prompt()
    try:
        if HAS_CREATE_CHAIN:
            doc_chain = create_stuff_documents_chain(llm=_llm, prompt=prompt)
            _rag_chain = create_retrieval_chain(retriever=_retriever, combine_docs_chain=doc_chain)
        else:
            _rag_chain = RetrievalQA.from_chain_type(llm=_llm, chain_type="stuff", retriever=_retriever, chain_type_kwargs={"prompt": prompt}, return_source_documents=True)
    except Exception:
            _rag_chain = None

def _langserve_invoke(inputs: dict):
    ensure_components()
    if _rag_chain is None:
        raise RuntimeError("RAG chain not initialized")
    if hasattr(_rag_chain, "invoke"):
        return _rag_chain.invoke(inputs)
    return _rag_chain(inputs)

# LangServe route (Runnable interface)
add_routes(app, RunnableLambda(_langserve_invoke), path="/promtior")

class QueryPayload(BaseModel):
    question: str

@app.post("/promtior/ask")
def ask(payload: QueryPayload):
    q = payload.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    init_cache()
    cached = get_cached(q)
    if cached:
        return {"answer": cached["answer"], "sources": cached["sources"], "cached": True}

    # ensure components available
    try:
        ensure_components()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    answer = None
    sources = []
    docs = []
    
    if _rag_chain is not None:
        try:
            if hasattr(_rag_chain, "invoke"):
                out = _rag_chain.invoke({"input": q})
            elif hasattr(_rag_chain, "__call__"):
                out = _rag_chain({"query": q})
            elif hasattr(_rag_chain, "run"):
                out = _rag_chain.run(q)
            else:
                out = None
            if isinstance(out, dict):
                answer = out.get("answer") or out.get("result") or out.get("output_text") or ""
                if "context" in out and isinstance(out["context"], list):
                    docs = out["context"]
                else:
                    docs = out.get("source_documents") or []
            elif isinstance(out, str):
                answer = out
        except Exception:
            pass

    if not answer:
        docs = _retriever.get_relevant_documents(q)
        context = "\n\n---\n\n".join([d.page_content for d in docs])
        seen = set()
        for d in docs:
            meta = getattr(d, "metadata", {}) or {}
            src = meta.get("source") if isinstance(meta, dict) else None
            if src and src not in seen:
                sources.append(src)
                seen.add(src)
        prompt_t = load_prompt()
        prompt_text = prompt_t.format(context=context, input=q)
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that must only use the provided context."},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0,
                max_tokens=512,
            )
            answer = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")
    
    if not sources and docs:
        seen = set()
        for d in docs:
            meta = getattr(d, "metadata", {}) or {}
            src = meta.get("source") if isinstance(meta, dict) else None
            if src and src not in seen:
                sources.append(src)
                seen.add(src)

    try:
        set_cached(q, answer, sources)
    except Exception:
        pass

    return {"answer": answer, "sources": sources, "cached": False}

