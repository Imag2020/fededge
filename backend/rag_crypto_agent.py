# rag_crypto_agent.py
import os
import json
import requests
import numpy as np
import struct
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, BLOB, DateTime, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from PyPDF2 import PdfReader
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any

# ===================== CONFIG =====================
LLAMA_SERV_URL = "http://localhost:11434"  # Ollama / llama-serv
EMBEDDING_MODEL = "embeddinggemma"
LLM_MODEL_DEFAULT = "gemma3:4b"
CHUNK_SIZE = 512
OVERLAP = 64
BASE_DIR = "rag_pdfs"
DB_PATH = "sqlite:///rag_crypto.db"

# ===================== SQLALCHEMY =====================
from .db.models import RagDocument, RagChunk, RagTrace, SessionLocal as Session
# ===================== EMBEDDING =====================
def get_embedding(text: str) -> np.ndarray:
    try:
        resp = requests.post(f"{LLAMA_SERV_URL}/api/embeddings", json={
            "model": EMBEDDING_MODEL,
            "prompt": f"Instruct: Représente ce texte pour recherche sémantique.\nInput: {text}"
        }, timeout=30)
        return np.array(resp.json()["embedding"], dtype=np.float32)
    except Exception as e:
        print(f"[Embedding Error] {e}")
        return np.zeros(768, dtype=np.float32)

def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

# ===================== BM25 INDEX =====================
bm25_index = {}

def build_bm25_index(session):
    for domain in session.query(RagChunk.domain).distinct():
        domain = domain[0]
        chunks = session.query(RagChunk).filter(RagChunk.domain == domain).all()
        texts = [c.content.split() for c in chunks]
        bm25_index[domain] = BM25Okapi(texts)

# ===================== CHUNKING =====================
def chunk_text(text: str):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunks.append(chunk)
        i += CHUNK_SIZE - OVERLAP
    return chunks

# ===================== INGESTION =====================
def ingest_pdf(pdf_path: str, url: str, domain: str, title: str):
    if not os.path.exists(pdf_path):
        return False

    session = Session()
    existing = session.query(RagDocument).filter(RagDocument.url == url).first()
    if existing:
        session.close()
        return True

    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

        doc = RagDocument(title=title, url=url, domain=domain, file_path=pdf_path)
        session.add(doc)
        session.flush()

        chunks = chunk_text(full_text)
        for idx, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            db_chunk = RagChunk(
                doc_id=doc.id,
                content=chunk,
                embedding=emb.tobytes(),
                page_number=None,
                chunk_index=idx,
                domain=domain
            )
            session.add(db_chunk)
        session.commit()
        print(f"[INGESTED] {title}")
        return True
    except Exception as e:
        print(f"[INGEST ERROR] {pdf_path}: {e}")
        session.rollback()
        return False
    finally:
        session.close()

# ===================== SEARCH =====================
def hybrid_search(query: str, domain: str = None, top_k: int = 10) -> List[tuple]:
    session = Session()
    q_emb = get_embedding(query)
    filters = [RagChunk.domain == domain] if domain else []
    candidates = session.query(RagChunk).filter(*filters).all()
    session.close()

    scores = []
    bm25 = bm25_index.get(domain)
    query_tokens = query.split()

    for c in candidates:
        vec = blob_to_vector(c.embedding)
        e_score = cosine_sim(q_emb, vec)
        b_score = bm25.get_scores(query_tokens)[0] if bm25 else 0
        final_score = 0.7 * e_score + 0.3 * (b_score / 10)
        scores.append((c, final_score))

    return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

# ===================== RERANKING =====================
def rerank_with_llm(query: str, candidates: List) -> List:
    if len(candidates) <= 3:
        return [c[0] for c in candidates]

    context = "\n---\n".join([f"[{i+1}] {c[0].content[:500]}" for i, c in enumerate(candidates[:6])])
    prompt = f"""
Classifie du plus pertinent (10) au moins (1) pour :

"{query}"

{context}

Réponds en JSON : {{"scores": [10, 8, ...]}}
"""
    try:
        resp = requests.post(f"{LLAMA_SERV_URL}/api/generate", json={
            "model": "gemma3:1b",
            "prompt": prompt,
            "stream": False
        }, timeout=20)
        scores = json.loads(resp.json()["response"])["scores"]
        paired = list(zip(candidates, scores))
        return [c[0] for c, s in sorted(paired, key=lambda x: x[1], reverse=True)]
    except:
        return [c[0] for c in candidates]

# ===================== AGENT QUERY =====================
def crypto_agent_query(
    user_query: str,
    wallet_address: str = None,
    domain: str = None,
    model: str = LLM_MODEL_DEFAULT
) -> str:
    start = datetime.utcnow()
    
    # 1. RAG
    rag_results = hybrid_search(user_query, domain=domain, top_k=8)
    rag_results = rerank_with_llm(user_query, rag_results)
    rag_context = "\n\n".join([
        f"[Source: {c.document.title}, chunk {c.chunk_index}]\n{c.content}"
        for c in rag_results[:5]
    ])

    # 2. Mock wallet + prix
    wallet_data = f"Wallet {wallet_address}: 2.5 ETH, 1000 USDC" if wallet_address else "Aucun wallet"
    price_data = "ETH: $3200 | BTC: $69k | USDC: $1.00"

    # 3. Prompt
    prompt = f"""
Tu es un expert crypto DeFi. Réponds en français, concis, avec citations [1][2].

Question: {user_query}

RAG:
{rag_context}

Wallet: {wallet_data}
Prix: {price_data}

Réponds avec citations [1], [2], etc.
"""

    # 4. LLM
    resp = requests.post(f"{LLAMA_SERV_URL}/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    answer = resp.json()["response"]

    # 5. Trace
    latency = int((datetime.utcnow() - start).total_seconds() * 1000)
    trace = RagTrace(
        question=user_query,
        chunk_ids=[c.id for c in rag_results[:5]],
        model=model,
        latency_ms=latency,
        answer_preview=answer[:200],
        full_answer=answer,
        sources=[{
            "title": c.document.title,
            "url": c.document.url,
            "chunk": c.chunk_index
        } for c in rag_results[:5]]
    )
    session = Session()
    session.add(trace)
    session.commit()
    session.close()

    return answer