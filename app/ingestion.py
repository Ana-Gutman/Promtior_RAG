import os
from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from app.utils import get_openai_embeddings, make_documents_from_texts

VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "./vectorstore")
DOCS_DIR = os.getenv("DOCS_DIR", "./data")

PROMTIOR_URLS = [
    "https://www.promtior.ai/",
    "https://www.promtior.ai/service",
    "https://www.promtior.ai/use-cases",
    "https://www.promtior.ai/meet-promtior",
]

def fetch_text_from_url(url: str) -> str:
    headers = {"User-Agent": os.getenv("USER_AGENT", "promtior-rag/1.0 (+https://promtior.ai)")}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = soup.get_text(separator="\n")
    return text.strip()

def load_web_docs(urls: List[str]):
    texts = []
    metadatas = []
    for u in urls:
        try:
            t = fetch_text_from_url(u)
            if t:
                texts.append(t)
                metadatas.append({"source": u})
                print("[+] loaded (web):", u)
        except Exception as e:
            print("[!] failed to fetch", u, ":", e)
    return texts, metadatas

def load_pdf_docs():
    pdf_path = Path(DOCS_DIR) / "promtior_presentation.pdf"
    if not pdf_path.exists():
        return [], []
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n\n".join(pages)
        return [text], [{"source": str(pdf_path)}]
    except Exception as e:
        print("[!] pdf load failed:", e)
        return [], []

def chunk_texts(texts: List[str], metadatas: List[Dict], chunk_size=1000, overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = []
    metas = []
    for i, (t, m) in enumerate(zip(texts, metadatas)):
        pieces = splitter.split_text(t)
        for j, p in enumerate(pieces):
            chunks.append(p)
            new_meta = dict(m)
            new_meta.update({"chunk_index": j})
            metas.append(new_meta)
    return chunks, metas

def main():
    _texts, _metas = load_web_docs(PROMTIOR_URLS)
    pdf_texts, pdf_metas = load_pdf_docs()
    _texts.extend(pdf_texts)
    _metas.extend(pdf_metas)

    if not _texts:
        raise RuntimeError("No documents loaded; check connectivity or DOCS_DIR")

    print(f"[i] loaded {len(_texts)} top-level pages, splitting to chunks...")
    chunks, metas = chunk_texts(_texts, _metas, chunk_size=600, overlap=150)
    print(f"[i] created {len(chunks)} chunks")

    # create LangChain Documents
    from app.utils import make_documents_from_texts
    docs = make_documents_from_texts(chunks, metas)

    # embeddings client
    print("[i] building embeddings...")
    embeddings_client = get_openai_embeddings()

    print("[i] creating FAISS vectorstore...")
    # use FAISS.from_documents (expects embedding object or function)
    try:
        vectorstore = FAISS.from_documents(docs, embeddings_client)
    except Exception:
        # fallback: build directly from texts with embeddings client
        vectorstore = FAISS.from_texts(chunks, embedding=embeddings_client, metadatas=metas)

    print("[i] saving vectorstore to", VECTORSTORE_DIR)
    vectorstore.save_local(VECTORSTORE_DIR)
    print("✅ FAISS vector store created successfully at", VECTORSTORE_DIR)

if __name__ == "__main__":
    main()
