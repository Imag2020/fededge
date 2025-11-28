"""
RAG Helpers - Fonctions utilitaires pour le système RAG
Gestion des embeddings, chunking, BM25, et recherche hybride
"""

import os
import numpy as np
from typing import List, Tuple, Optional
from rank_bm25 import BM25Okapi
from PyPDF2 import PdfReader

from ..db.models import RagDocument, RagChunk, SessionLocal

# ===================== CONFIG =====================
CHUNK_SIZE = 300  # Nombre de mots par chunk
OVERLAP = 50      # Overlap entre chunks pour la continuité

# ===================== BLOB <-> VECTOR =====================

def vector_to_blob(vector: np.ndarray) -> bytes:
    """Convertit un vecteur numpy en BLOB pour stockage SQLite"""
    return vector.astype(np.float32).tobytes()


def blob_to_vector(blob: bytes) -> np.ndarray:
    """Convertit un BLOB SQLite en vecteur numpy"""
    return np.frombuffer(blob, dtype=np.float32)


# ===================== SIMILARITY =====================

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Calcule la similarité cosinus entre deux vecteurs"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)


# ===================== BM25 INDEX =====================
# Index BM25 global pour recherche lexicale rapide
bm25_index = {}


def build_bm25_index(session=None):
    """Construit l'index BM25 pour tous les domaines"""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        for domain_tuple in session.query(RagChunk.domain).distinct():
            domain = domain_tuple[0]
            if not domain:
                continue

            chunks = session.query(RagChunk).filter(RagChunk.domain == domain).all()
            if not chunks:
                continue

            texts = [c.content.split() for c in chunks]
            bm25_index[domain] = BM25Okapi(texts)
            print(f"✅ Index BM25 construit pour {domain}: {len(chunks)} chunks")

    finally:
        if close_session:
            session.close()


def get_bm25_index(domain: str) -> Optional[BM25Okapi]:
    """Récupère l'index BM25 pour un domaine"""
    return bm25_index.get(domain)


# ===================== CHUNKING =====================

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    """
    Découpe un texte en chunks avec overlap

    Args:
        text: Texte à découper
        chunk_size: Taille des chunks en mots
        overlap: Nombre de mots qui se chevauchent

    Returns:
        Liste de chunks de texte
    """
    words = text.split()
    chunks = []
    i = 0

    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap

    return chunks


# ===================== EMBEDDING =====================

def get_embedding(text: str) -> np.ndarray:
    """
    Génère un embedding pour un texte en utilisant le service configuré

    Args:
        text: Texte à embedder

    Returns:
        Vecteur numpy de dimension configurée (défaut: 768, float32)
    """
    try:
        from ..config_manager import config_manager

        # Récupérer la configuration d'embedding par défaut
        emb_config = config_manager.get_default_embedding()

        if not emb_config:
            print("⚠️ Aucune configuration d'embedding trouvée, utilisation du fallback LlamaCpp")
            from ..services.llamacpp_embeddings import get_llamacpp_embedder
            embedder = get_llamacpp_embedder(base_url="http://localhost:9002")
            embedding = embedder.embed_text(text)
        elif emb_config.type.value == "llamacpp":
            from ..services.llamacpp_embeddings import LlamaCppEmbeddingService
            embedder = LlamaCppEmbeddingService(base_url=emb_config.url)
            embedding = embedder.embed_text(text)
        elif emb_config.type.value == "ollama":
            from ..services.ollama_embeddings import OllamaEmbedder
            embedder = OllamaEmbedder(base_url=emb_config.url, model=emb_config.model)
            embedding = embedder.embed_text(text)
        elif emb_config.type.value == "openai":
            # TODO: Implement OpenAI embeddings
            print(f"⚠️ Type {emb_config.type.value} non encore implémenté, fallback LlamaCpp")
            from ..services.llamacpp_embeddings import LlamaCppEmbeddingService
            embedder = LlamaCppEmbeddingService(base_url="http://localhost:9002")
            embedding = embedder.embed_text(text)
        else:
            print(f"⚠️ Type d'embedding non supporté: {emb_config.type.value}, fallback LlamaCpp")
            from ..services.llamacpp_embeddings import LlamaCppEmbeddingService
            embedder = LlamaCppEmbeddingService(base_url="http://localhost:9002")
            embedding = embedder.embed_text(text)

        # Vérifier que l'embedding est valide (pas que des zéros)
        if np.count_nonzero(embedding) == 0:
            print(f"⚠️ Embedding vide généré pour: {text[:50]}...")

        return embedding

    except Exception as e:
        print(f"❌ Erreur génération embedding: {e}")
        import traceback
        traceback.print_exc()
        # Fallback : vecteur zéro de dimension 768
        return np.zeros(768, dtype=np.float32)


# ===================== INGESTION =====================

def ingest_pdf(
    pdf_path: str,
    url: str,
    domain: str,
    title: str,
    session=None
) -> bool:
    """
    Ingère un PDF dans le système RAG

    Args:
        pdf_path: Chemin vers le fichier PDF
        url: URL source du document
        domain: Domaine du document (ex: "crypto", "finance")
        title: Titre du document
        session: Session SQLAlchemy (optionnel)

    Returns:
        True si succès, False sinon
    """
    if not os.path.exists(pdf_path):
        print(f"❌ Fichier introuvable: {pdf_path}")
        return False

    # Créer session si nécessaire
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        # Vérifier si le document existe déjà
        existing = session.query(RagDocument).filter(RagDocument.url == url).first()
        if existing:
            print(f"ℹ️  Document déjà ingéré: {title}")
            if close_session:
                session.close()
            return True

        # Extraire le texte du PDF
        reader = PdfReader(pdf_path)
        full_text = ""

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text += text + "\n"

        if not full_text.strip():
            print(f"⚠️  PDF vide ou illisible: {pdf_path}")
            if close_session:
                session.close()
            return False

        # Créer le document
        doc = RagDocument(
            title=title,
            url=url,
            domain=domain,
            file_path=pdf_path
        )
        session.add(doc)
        session.flush()  # Pour obtenir l'ID

        # Chunker le texte
        chunks = chunk_text(full_text)
        print(f"📄 {len(chunks)} chunks créés pour {title}")

        # Créer les chunks avec embeddings
        for idx, chunk in enumerate(chunks):
            print(f"   Chunk {idx+1}/{len(chunks)}: génération embedding...", end=" ", flush=True)
            emb = get_embedding(chunk)
            print(f"✓ (dim={emb.shape[0]})", end=" ", flush=True)

            db_chunk = RagChunk(
                doc_id=doc.id,
                content=chunk,
                embedding=vector_to_blob(emb),  # Utiliser la fonction helper
                page_number=None,  # Pourrait être calculé si nécessaire
                chunk_index=idx,
                domain=domain
            )
            session.add(db_chunk)
            print("✓ ajouté")

        print("💾 Commit en base...", end=" ", flush=True)
        session.commit()
        print("✓")
        print(f"✅ [INGESTED] {title} ({len(chunks)} chunks)")

        # Reconstruire l'index BM25 pour ce domaine
        build_bm25_index(session)

        return True

    except Exception as e:
        print(f"❌ [INGEST ERROR] {pdf_path}: {e}")
        session.rollback()
        return False

    finally:
        if close_session:
            session.close()


# ===================== SEARCH =====================

def hybrid_search(
    query: str,
    domain: Optional[str] = None,
    top_k: int = 10,
    session=None
) -> List[Tuple[RagChunk, float]]:
    """
    Recherche hybride combinant similarité sémantique (embeddings) et BM25

    Args:
        query: Question ou recherche
        domain: Domaine à filtrer (optionnel)
        top_k: Nombre de résultats à retourner
        session: Session SQLAlchemy (optionnel)

    Returns:
        Liste de tuples (chunk, score) triés par pertinence
    """
    # Créer session si nécessaire
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        # Générer l'embedding de la requête
        q_emb = get_embedding(query)

        # Construire les filtres
        filters = []
        if domain:
            filters.append(RagChunk.domain == domain)

        # Récupérer les candidats
        candidates = session.query(RagChunk).filter(*filters).all()

        if not candidates:
            print(f"⚠️  Aucun chunk trouvé pour le domaine: {domain}")
            return []

        # Calculer les scores
        scores = []
        bm25 = bm25_index.get(domain) if domain else None
        query_tokens = query.split()

        for idx, chunk in enumerate(candidates):
            # Score embedding (similarité cosinus)
            vec = blob_to_vector(chunk.embedding)
            e_score = cosine_sim(q_emb, vec)

            # Score BM25 (recherche lexicale)
            b_score = 0.0
            if bm25:
                try:
                    bm25_scores = bm25.get_scores(query_tokens)
                    b_score = bm25_scores[idx] if idx < len(bm25_scores) else 0.0
                except:
                    b_score = 0.0

            # Score hybride : 70% embedding + 30% BM25
            final_score = 0.7 * e_score + 0.3 * (b_score / 10.0)
            scores.append((chunk, final_score))

        # Trier par score décroissant
        results = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

        return results

    finally:
        if close_session:
            session.close()


# ===================== UTILITIES =====================

def get_document_by_url(url: str, session=None) -> Optional[RagDocument]:
    """Récupère un document par son URL"""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        doc = session.query(RagDocument).filter(RagDocument.url == url).first()
        return doc
    finally:
        if close_session:
            session.close()


def delete_document(doc_id: int, session=None) -> bool:
    """Supprime un document et tous ses chunks"""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        doc = session.query(RagDocument).filter(RagDocument.id == doc_id).first()
        if not doc:
            return False

        session.delete(doc)  # Cascade supprimera aussi les chunks
        session.commit()
        print(f"✅ Document supprimé: {doc.title}")

        # Reconstruire l'index BM25
        build_bm25_index(session)

        return True

    except Exception as e:
        print(f"❌ Erreur suppression document: {e}")
        session.rollback()
        return False

    finally:
        if close_session:
            session.close()


def get_all_domains(session=None) -> List[str]:
    """Récupère la liste de tous les domaines"""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        domains = session.query(RagChunk.domain).distinct().all()
        return [d[0] for d in domains if d[0]]
    finally:
        if close_session:
            session.close()


def get_stats(session=None) -> dict:
    """Retourne des statistiques sur le système RAG"""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        total_docs = session.query(RagDocument).count()
        total_chunks = session.query(RagChunk).count()
        domains = get_all_domains(session)

        stats = {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "domains": domains,
            "chunks_per_domain": {}
        }

        for domain in domains:
            count = session.query(RagChunk).filter(RagChunk.domain == domain).count()
            stats["chunks_per_domain"][domain] = count

        return stats

    finally:
        if close_session:
            session.close()
