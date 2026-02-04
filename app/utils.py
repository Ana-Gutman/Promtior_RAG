import os
import json
import numpy as np
from typing import List, Dict, Any

Document = None
try:
    from langchain_core.documents import Document as _Document
    Document = _Document
except Exception:
    try:
        from langchain.schema import Document as _Document
        Document = _Document
    except Exception:
        Document = None

_HAS_LANGCHAIN_EMB = False
try:
    from langchain_openai import OpenAIEmbeddings
    _HAS_LANGCHAIN_EMB = True
except Exception:
    _HAS_LANGCHAIN_EMB = False

def get_openai_embeddings(**kwargs):
    """Returns embeddings client object with embed_documents() and embed_query() methods."""
    if _HAS_LANGCHAIN_EMB:
        return OpenAIEmbeddings(**kwargs)

    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)

    class RawEmb:
        def __init__(self, model="text-embedding-3-small"):
            self.model = model
            self._client = client

        def embed_documents(self, texts: List[str]):
            results = []
            for i in range(0, len(texts), 16):
                batch = texts[i:i+16]
                resp = self._client.embeddings.create(model=self.model, input=batch)
                results.extend([d.embedding for d in resp.data])
            return results

        def embed_query(self, text: str):
            resp = self._client.embeddings.create(model=self.model, input=[text])
            return resp.data[0].embedding

    return RawEmb(**kwargs)

def make_documents_from_texts(texts: List[str], metadatas: List[Dict[str, Any]]):
    if Document is None:
        raise RuntimeError("LangChain Document class not found in this environment.")
    return [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]

# Small numpy-backed persistence helper (for optional fallback)
def save_numpy_vectorstore(path: str, texts: List[str], metadatas: List[Dict[str, Any]], embeddings: List[List[float]]):
    os.makedirs(path, exist_ok=True)
    np.save(os.path.join(path, "embeddings.npy"), np.array(embeddings, dtype=np.float32))
    with open(os.path.join(path, "texts.json"), "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
    with open(os.path.join(path, "metadatas.json"), "w", encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)
