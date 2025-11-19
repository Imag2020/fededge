# backend/services/rag_service.py

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy.orm import Session
from rank_bm25 import BM25Okapi
from PyPDF2 import PdfReader

from ..db.crud import (
    get_or_create_rag_document,
    add_rag_chunk,
    get_rag_chunks_by_domain,
    create_rag_trace,
)
from ..db.models import RagChunk
from ..embeddings_pool import embeddings_pool
from ..llm_pool import llm_pool

# ===================== CONFIG =====================

CHUNK_SIZE = 512
OVERLAP = 64

# Modèle LLM éventuellement dédié au RAG (id dans ton llm_pool)
RAG_LLM_ID = os.getenv("RAG_LLM_ID", None)


# ===================== EMBEDDING HELPERS =====================

def get_embedding(text: str) -> np.ndarray:
    """
    Wrapper vers embeddings_pool.
    Retourne un vecteur float32 numpy.
    """
    return embeddings_pool.get_embedding(text)


def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


# ===================== CHUNKING =====================

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    i = 0
    n = len(words)
    step = max(1, chunk_size - overlap)

    while i < n:
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += step

    return chunks


# ===================== INGESTION =====================

def ingest_pdf(
    db: Session,
    *,
    pdf_path: str,
    url: Optional[str],
    domain: str,
    title: str,
) -> Optional[int]:
    """
    Ingestion d'un PDF :
    - crée un RagDocument
    - crée les RagChunks avec embeddings
    Retourne l'id du RagDocument ou None si erreur.
    """
    import os

    if not os.path.exists(pdf_path):
        print(f"[RAG] PDF not found: {pdf_path}")
        return None

    doc = get_or_create_rag_document(
        db,
        title=title,
        url=url,
        domain=domain,
        file_path=pdf_path,
    )

    # Si doc existant sans chunks, on peut le remplir ; s'il a déjà des chunks, on sort
    if doc.chunks:
        print(f"[RAG] Document déjà ingéré: {title}")
        return doc.id

    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

        chunks = chunk_text(full_text)
        for idx, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            add_rag_chunk(
                db,
                doc_id=doc.id,
                content=chunk,
                embedding_bytes=emb.tobytes(),
                page_number=None,
                chunk_index=idx,
                domain=domain,
            )

        print(f"[RAG] Ingested PDF: {title} ({len(chunks)} chunks)")
        return doc.id

    except Exception as e:
        print(f"[RAG] Ingest error for {pdf_path}: {e}")
        return None


def ingest_text_document(
    db: Session,
    *,
    title: str,
    content: str,
    domain: str,
    url: Optional[str] = None,
) -> Optional[int]:
    """
    Ingestion d'un document texte (contenu de page web, note user, etc.).
    """
    doc = get_or_create_rag_document(
        db,
        title=title,
        url=url,
        domain=domain,
        file_path=None,
    )

    if doc.chunks:
        # Idempotence simple: si déjà des chunks, on ne duplique pas
        print(f"[RAG] Document texte déjà ingéré: {title}")
        return doc.id

    try:
        chunks = chunk_text(content)
        for idx, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            add_rag_chunk(
                db,
                doc_id=doc.id,
                content=chunk,
                embedding_bytes=emb.tobytes(),
                page_number=None,
                chunk_index=idx,
                domain=domain,
            )

        print(f"[RAG] Ingested TEXT: {title} ({len(chunks)} chunks)")
        return doc.id

    except Exception as e:
        print(f"[RAG] Ingest text error for {title}: {e}")
        return None


# ===================== SEARCH (HYBRID: EMBEDDING + BM25) =====================

def hybrid_search(
    db: Session,
    *,
    query: str,
    domain: Optional[str] = None,
    top_k: int = 10,
) -> List[tuple]:
    """
    Recherche hybride:
    - Embedding cosine similarity
    - BM25 sur le contenu brut
    Retourne: [(RagChunk, score), ...]
    """
    q_emb = get_embedding(query)

    # Charger les candidats (filtrés par domaine ou non)
    candidates: List[RagChunk] = get_rag_chunks_by_domain(db, domain=domain)
    if not candidates:
        return []

    # BM25 sur les candidats
    tokenized = [c.content.split() for c in candidates]
    bm25 = BM25Okapi(tokenized)
    query_tokens = query.split()
    bm25_scores = bm25.get_scores(query_tokens)  # array-like

    scores: List[tuple] = []
    for idx, c in enumerate(candidates):
        vec = blob_to_vector(c.embedding) if c.embedding else None
        e_score = cosine_sim(q_emb, vec) if vec is not None else 0.0
        b_score = float(bm25_scores[idx]) if bm25_scores is not None else 0.0
        final_score = 0.7 * e_score + 0.3 * (b_score / 10.0)
        scores.append((c, final_score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def rerank_with_llm(
    query: str,
    candidates: List[tuple],
) -> List[RagChunk]:
    """
    Rerank optionnel via LLM.

    ⚠️ Pour l'instant, version simplifiée: on garde juste l'ordre initial.
    On pourra plus tard ajouter un rerank LLM asynchrone via llm_pool.
    """
    return [c[0] for c in candidates]


# ===================== HIGH-LEVEL RAG QUERY =====================

async def rag_query(
    db: Session,
    *,
    user_query: str,
    domain: Optional[str] = None,
    wallet_context: Optional[str] = None,
    llm_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query RAG pour le frontend ou pour un agent:
    - fait la recherche hybride
    - assemble un contexte
    - appelle le LLM via llm_pool pour générer la réponse
    - loggue la trace dans RagTrace

    Retourne:
        {
          "answer": str,
          "sources": [...],
          "latency_ms": int,
        }

    ⚠️ Fonction asynchrone: à utiliser avec `await rag_query(...)`.
    """
    start = datetime.utcnow()

    # 1. RAG search
    candidates = hybrid_search(db, query=user_query, domain=domain, top_k=8)
    if candidates:
        reranked_chunks = rerank_with_llm(user_query, candidates)
    else:
        reranked_chunks = []

    top_chunks = reranked_chunks[:5]
    rag_context = "\n\n".join(
        [
            f"[Source: {c.document.title if c.document else 'N/A'}, chunk {c.chunk_index}]\n{c.content}"
            for c in top_chunks
        ]
    )

    # 2. Contexte wallet / marché (placeholder pour l’instant)
    wallet_data = wallet_context or "Aucun contexte wallet fourni."
    market_hint = "Contexte marché: utilisable via les tools get_market_cap/get_crypto_prices."

    # 3. Prompt LLM (via llm_pool)
    prompt = f"""
Tu es un expert crypto/DeFi. Réponds en français, de façon concise,
et utilise des citations de type [1], [2] en t'appuyant sur les extraits.

Question utilisateur:
{user_query}

Contexte RAG (extraits de documents):
{rag_context}

Contexte wallet/utilisateur:
{wallet_data}

{market_hint}

Réponds avec citations [1], [2], etc. Si l'information manque, dis-le clairement.
"""

    try:
        # llm_id explicite > env RAG_LLM_ID > défaut du pool
        effective_llm_id = llm_id or RAG_LLM_ID
        answer = await llm_pool.generate_response(prompt, llm_id=effective_llm_id)
        answer = (answer or "").strip()
    except Exception as e:
        answer = f"Erreur lors de l'appel LLM pour RAG via llm_pool: {e}"

    # 4. Trace en base
    latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    chunk_ids = [c.id for c in top_chunks]
    sources_meta = [
        {
            "title": c.document.title if c.document else None,
            "url": c.document.url if c.document else None,
            "chunk": c.chunk_index,
            "domain": c.domain,
        }
        for c in top_chunks
    ]

    create_rag_trace(
        db,
        question=user_query,
        chunk_ids=chunk_ids,
        model=effective_llm_id or "default",
        latency_ms=latency_ms,
        answer_preview=answer[:200],
        full_answer=answer,
        sources=sources_meta,
    )

    return {
        "answer": answer,
        "sources": sources_meta,
        "latency_ms": latency_ms,
    }
