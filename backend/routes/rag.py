"""
Knowledge Base & RAG Routes
Handles knowledge base management, RAG search, and document indexing
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging
import sqlite3
import os
import requests
import tempfile

from sqlalchemy import text, func  # pour les stats SQLAlchemy
from ..db.models import SessionLocal, RagDocument, RagChunk, NewsArticle
from ..db import crud
from ..services import rag_service
from ..embeddings_pool import embeddings_pool



logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge"])



@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Récupérer les statistiques de la base de connaissances RAG (nouvelle version)"""
    db = SessionLocal()
    try:
        # ---- Stats RAG (nouveau système) ----
        rag_docs_count = db.query(func.count(RagDocument.id)).scalar() or 0
        rag_chunks_count = db.query(func.count(RagChunk.id)).scalar() or 0

        # Stats News (table news_articles)
        news_articles_count = db.execute(text("SELECT COUNT(*) FROM news_articles")).scalar() or 0
        recent_articles_count = db.execute(text(
            "SELECT COUNT(*) FROM news_articles WHERE created_at > datetime('now', '-7 days')"
        )).scalar() or 0
        last_news_update = db.execute(text(
            "SELECT MAX(created_at) FROM news_articles"
        )).scalar()

    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        return {
            "status": "error",
            "message": f"Error retrieving knowledge stats: {str(e)}",
            "knowledge_stats": {}
        }
    finally:
        db.close()

    # ---- Stats datasets legacy (world_state, candidates, etc.) ----
    datasets_stats = {}
    datasets_dir = "datasets"

    if os.path.exists(datasets_dir):
        world_db = os.path.join(datasets_dir, "world_state_sessions.db")
        if os.path.exists(world_db):
            try:
                with sqlite3.connect(world_db) as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) as total, MAX(timestamp) as last_session FROM world_state_sessions"
                    )
                    result = cursor.fetchone()
                    datasets_stats["world_state"] = {
                        "total_sessions": result[0] if result else 0,
                        "last_session": result[1] if result and result[1] else None,
                        "file_size_mb": round(os.path.getsize(world_db) / (1024*1024), 2)
                    }
            except Exception:
                datasets_stats["world_state"] = {
                    "total_sessions": 0,
                    "last_session": None,
                    "file_size_mb": 0
                }

        candidates_db = os.path.join(datasets_dir, "candidates_trader_sessions.db")
        if os.path.exists(candidates_db):
            try:
                with sqlite3.connect(candidates_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) as total FROM candidates_sessions")
                    result = cursor.fetchone()
                    datasets_stats["candidates_trader"] = {
                        "total_sessions": result[0] if result else 0,
                        "file_size_mb": round(os.path.getsize(candidates_db) / (1024*1024), 2)
                    }
            except Exception:
                datasets_stats["candidates_trader"] = {
                    "total_sessions": 0,
                    "file_size_mb": 0
                }

        decider_db = os.path.join(datasets_dir, "decider_trader_sessions.db")
        if os.path.exists(decider_db):
            try:
                with sqlite3.connect(decider_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) as total FROM decider_sessions")
                    result = cursor.fetchone()
                    datasets_stats["decider_trader"] = {
                        "total_sessions": result[0] if result else 0,
                        "file_size_mb": round(os.path.getsize(decider_db) / (1024*1024), 2)
                    }
            except Exception:
                datasets_stats["decider_trader"] = {
                    "total_sessions": 0,
                    "file_size_mb": 0
                }

    datasets_last_update = datasets_stats.get("world_state", {}).get("last_session")

    # Statut DB RAG
    db_status = "online" if rag_docs_count >= 0 else "warning"

    # Récupérer le modèle d'embedding par défaut
    try:
        default_embedding = embeddings_pool.get_client()
        embedding_model = default_embedding.cfg.model if default_embedding and default_embedding.cfg else "unknown"
        embedding_url = default_embedding.cfg.url if default_embedding and default_embedding.cfg else "unknown"
    except Exception:
        embedding_model = "unknown"
        embedding_url = "unknown"

    return {
        "status": "success",
        "knowledge_stats": {
            "vector_database": {
                "status": db_status,
                "rag_documents": rag_docs_count,
                "rag_chunks": rag_chunks_count,
                "total_vectors": rag_chunks_count,
                "embedding_model": embedding_model,
                "embedding_service": embedding_url,
                "database_path": "rag_documents/rag_chunks (SQLite)",
                "vector_store": "SQLite (BLOB embeddings)"
            },
            "news_database": {
                "total_articles": news_articles_count,
                "recent_articles_7d": recent_articles_count,
                "sources": ["Cointelegraph", "CoinDesk", "The Block"],
                "last_updated": last_news_update
            },
            "training_datasets": {
                **datasets_stats,
                "last_updated": datasets_last_update
            },
            "rag_capabilities": {
                "semantic_search": True,
                "news_retrieval": True,
                "context_generation": True,
                "citation_tracking": True,
                "real_time_updates": True
            }
        }
    }



@router.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10, domain: Optional[str] = None):
    """
    Recherche dans la base de connaissances RAG (nouveau backend).
    Retourne une liste de documents/chunks pertinents (sans génération LLM).
    """
    if not query or len(query.strip()) < 3:
        return {
            "status": "error",
            "message": "Query must be at least 3 characters",
            "results": []
        }

    db = SessionLocal()
    try:
        # Utilise la recherche hybride, mais sans reranking LLM pour rester rapide
        candidates = rag_service.hybrid_search(
            db,
            query=query.strip(),
            domain=domain,
            top_k=limit,
        )

        results = []
        for chunk, score in candidates:
            doc = chunk.document
            results.append({
                "title": doc.title if doc else f"Document #{chunk.doc_id}",
                "source": doc.domain if doc else "unknown",
                "score": round(score, 3),
                "content": chunk.content[:500],
                "metadata": {
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "url": doc.url if doc else None,
                    "domain": chunk.domain,
                }
            })

        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error searching knowledge base: {str(e)}",
            "results": []
        }
    finally:
        db.close()


@router.post("/knowledge/add-text")
async def add_text_to_knowledge(request: dict):
    """Ajouter du texte à la base de connaissances (nouveau RAG)"""
    try:
        title = (request.get("title") or "").strip()
        content = (request.get("content") or "").strip()
        source = (request.get("source") or "user_upload").strip()
        domain = request.get("domain") or "user_knowledge"

        if not title or not content:
            return {
                "status": "error",
                "message": "Title and content are required"
            }

        db = SessionLocal()
        try:
            doc_id = rag_service.ingest_text_document(
                db,
                title=title,
                content=content,
                domain=domain,
                url=None,  # on peut générer une URL logique plus tard si besoin
            )

            if doc_id is None:
                return {
                    "status": "error",
                    "message": "Failed to ingest text into RAG"
                }

            return {
                "status": "success",
                "message": "Text added to RAG knowledge base",
                "document_id": doc_id,
                "domain": domain,
                "source": source,
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error adding text to knowledge: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error adding text: {str(e)}"
        }



@router.post("/knowledge/add-file")
async def add_file_to_knowledge(file: UploadFile = File(...)):
    """Ajouter un fichier à la base de connaissances (nouveau RAG)"""
    import tempfile
    import re

    try:
        allowed_extensions = ['.pdf', '.txt', '.doc', '.docx']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            return {
                "status": "error",
                "message": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            }

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            return {
                "status": "error",
                "message": "File too large (max 10MB)"
            }

        logger.info(f"File upload: {file.filename} ({len(content)} bytes, type: {file_ext})")

        db = SessionLocal()
        try:
            base_title = os.path.splitext(file.filename)[0]
            domain = "user_knowledge"

            # Cas PDF : ingestion directe via rag_service.ingest_pdf
            if file_ext == ".pdf":
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(content)
                    tmp_path = tmp_file.name

                try:
                    doc_id = rag_service.ingest_pdf(
                        db,
                        pdf_path=tmp_path,
                        url=None,
                        domain=domain,
                        title=base_title,
                    )
                finally:
                    os.unlink(tmp_path)

                if doc_id is None:
                    return {
                        "status": "error",
                        "message": "Failed to ingest PDF into RAG"
                    }

                return {
                    "status": "success",
                    "message": "PDF added to RAG knowledge base",
                    "document_id": doc_id,
                    "domain": domain,
                }

            # Cas texte / Word : extraire texte puis ingest_text_document
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                extracted_text = ""

                if file_ext == ".txt":
                    with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                        extracted_text = f.read()

                elif file_ext in [".doc", ".docx"]:
                    try:
                        import docx
                        doc = docx.Document(tmp_path)
                        extracted_text = "\n".join(p.text for p in doc.paragraphs)
                    except ImportError:
                        return {
                            "status": "error",
                            "message": "Word document processing not available. Please install python-docx."
                        }

                # Nettoyage minimal
                extracted_text = extracted_text.strip()
                extracted_text = re.sub(r'\s+\n', '\n', extracted_text)
                extracted_text = re.sub(r'\n{3,}', '\n\n', extracted_text)

                if not extracted_text or len(extracted_text) < 50:
                    return {
                        "status": "error",
                        "message": f"Extracted text too short or invalid (got {len(extracted_text)} chars)"
                    }

                doc_id = rag_service.ingest_text_document(
                    db,
                    title=base_title,
                    content=extracted_text,
                    domain=domain,
                )

                if doc_id is None:
                    return {
                        "status": "error",
                        "message": "Failed to ingest file text into RAG"
                    }

                return {
                    "status": "success",
                    "message": "File text added to RAG knowledge base",
                    "document_id": doc_id,
                    "domain": domain,
                    "extracted_length": len(extracted_text),
                }

            finally:
                os.unlink(tmp_path)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error adding file to knowledge: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing file: {str(e)}"
        }

@router.post("/knowledge/add-url")
async def add_url_to_knowledge(request: dict):
    """Ajouter le contenu d'une URL à la base de connaissances (nouveau RAG)"""
    url = (request.get("url") or "").strip()
    domain = (request.get("domain") or "user_knowledge").strip()

    if not url:
        return {
            "status": "error",
            "message": "URL is required"
        }

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch URL: {str(e)}"
        }

    content_type = (resp.headers.get("content-type") or "").lower()
    is_pdf = ("pdf" in content_type) or url.lower().endswith(".pdf")

    db = SessionLocal()
    try:
        # -------------------- CAS PDF --------------------
        if is_pdf:
            logger.info(f"[RAG] URL detected as PDF: {url}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(resp.content)
                tmp_path = tmp_file.name

            try:
                # Titre à partir de l’URL
                base_title = os.path.basename(url).replace(".pdf", "") or "PDF Document"

                doc_id = rag_service.ingest_pdf(
                    db,
                    pdf_path=tmp_path,
                    url=url,
                    domain=domain,
                    title=base_title,
                )
            finally:
                os.unlink(tmp_path)

            if doc_id is None:
                return {
                    "status": "error",
                    "message": "Failed to ingest PDF into RAG"
                }

            return {
                "status": "success",
                "message": "PDF URL added to RAG knowledge base",
                "document_id": doc_id,
                "domain": domain,
                "url": url,
            }

        # -------------------- CAS HTML --------------------
        logger.info(f"[RAG] URL detected as HTML: {url}")

        soup = BeautifulSoup(resp.content, "html.parser")

        # virer scripts & styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # titre
        title_tag = soup.find("title")
        title_text = (title_tag.get_text().strip() if title_tag else "") or "Web Page"

        # texte brut
        text_content = soup.get_text(separator="\n")
        # nettoyage léger
        lines = [line.strip() for line in text_content.splitlines()]
        lines = [l for l in lines if l]  # remove blank
        text_content = "\n".join(lines)

        # nettoyage additionnel
        text_content = re.sub(r"\s+\n", "\n", text_content)
        text_content = re.sub(r"\n{3,}", "\n\n", text_content)
        text_content = text_content.strip()

        if not text_content or len(text_content) < 50:
            return {
                "status": "error",
                "message": f"Extracted text too short ({len(text_content)} chars)"
            }

        doc_id = rag_service.ingest_text_document(
            db,
            title=title_text,
            content=text_content,
            domain=domain,
            url=url,
        )

        if doc_id is None:
            return {
                "status": "error",
                "message": "Failed to ingest URL content into RAG"
            }

        return {
            "status": "success",
            "message": "URL content added to RAG knowledge base",
            "document_id": doc_id,
            "domain": domain,
            "url": url,
            "content_length": len(text_content),
        }

    except Exception as e:
        logger.error(f"❌ Error adding URL to knowledge: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing URL: {str(e)}"
        }
    finally:
        db.close()



# ============== KNOWLEDGE SOURCES & INDEXING ==============

@router.get("/knowledge/sources")
async def get_crypto_sources():
    """Récupérer toutes les sources de la base de connaissances crypto"""
    try:
        from .services.crypto_sources_manager import get_crypto_sources_manager
        
        manager = get_crypto_sources_manager()
        sources = manager.get_all_sources()
        stats = manager.get_indexing_stats()
        
        return {
            "success": True,
            "sources": [source.to_dict() for source in sources],
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting crypto sources: {e}")
        return {
            "success": False,
            "error": str(e),
            "sources": [],
            "stats": {}
        }

class CryptoSourceRequest(BaseModel):
    url: str
    title: str
    tags: List[str]
    enabled: bool = True

@router.post("/knowledge/sources")
async def add_crypto_source(source_request: CryptoSourceRequest):
    """Ajouter une nouvelle source crypto"""
    try:
        from .services.crypto_sources_manager import get_crypto_sources_manager
        
        manager = get_crypto_sources_manager()
        source = manager.add_source(
            url=source_request.url,
            title=source_request.title,
            tags=source_request.tags,
            enabled=source_request.enabled
        )
        
        return {
            "success": True,
            "message": "Source added successfully",
            "source": source.to_dict()
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error adding crypto source: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.put("/knowledge/sources/{source_id}")
async def update_crypto_source(source_id: int, updates: Dict[str, Any]):
    """Mettre à jour une source crypto"""
    try:
        from .services.crypto_sources_manager import get_crypto_sources_manager
        
        manager = get_crypto_sources_manager()
        source = manager.update_source(source_id, **updates)
        
        if not source:
            return {
                "success": False,
                "error": f"Source {source_id} not found"
            }
        
        return {
            "success": True,
            "message": "Source updated successfully",
            "source": source.to_dict()
        }
    except Exception as e:
        logger.error(f"Error updating crypto source {source_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/knowledge/sources/{source_id}")
async def delete_crypto_source(source_id: int):
    """Supprimer une source crypto"""
    try:
        from .services.crypto_sources_manager import get_crypto_sources_manager
        
        manager = get_crypto_sources_manager()
        success = manager.delete_source(source_id)
        
        if not success:
            return {
                "success": False,
                "error": f"Source {source_id} not found"
            }
        
        return {
            "success": True,
            "message": f"Source {source_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting crypto source {source_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/knowledge/sources/{source_id}/reset")
async def reset_crypto_source_errors(source_id: int):
    """Réactiver une source en remettant ses erreurs à zéro"""
    try:
        from .services.crypto_sources_manager import get_crypto_sources_manager
        
        manager = get_crypto_sources_manager()
        success = manager.reset_source_errors(source_id)
        
        if not success:
            return {
                "success": False,
                "error": f"Source {source_id} not found"
            }
        
        return {
            "success": True,
            "message": f"Source {source_id} reactivated successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting crypto source {source_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/knowledge/index")
async def start_crypto_indexing():
    """Démarrer l'indexation des sources crypto en arrière-plan"""
    try:
        from .services.crypto_indexer import get_crypto_indexer
        
        indexer = get_crypto_indexer()
        
        # Lancer l'indexation en arrière-plan
        async def run_indexing():
            results = await indexer.index_all_pending_sources()
            logger.info(f"Crypto indexing completed: {results}")
        
        # Créer une tâche asynchrone
        asyncio.create_task(run_indexing())
        
        return {
            "success": True,
            "message": "Crypto indexing started in background",
            "status": "running"
        }
    except Exception as e:
        logger.error(f"Error starting crypto indexing: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }

@router.post("/knowledge/index/{source_id}")
async def reindex_crypto_source(source_id: int):
    """Ré-indexer une source crypto spécifique"""
    try:
        from .services.crypto_indexer import get_crypto_indexer
        
        indexer = get_crypto_indexer()
        
        # Lancer la ré-indexation en arrière-plan
        async def run_reindexing():
            success = await indexer.reindex_source(source_id)
            logger.info(f"Source {source_id} reindexing: {'success' if success else 'failed'}")
        
        asyncio.create_task(run_reindexing())
        
        return {
            "success": True,
            "message": f"Source {source_id} reindexing started",
            "status": "running"
        }
    except Exception as e:
        logger.error(f"Error reindexing source {source_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }


@router.get("/rag/health")
async def rag_health_check():
    """
    RAG system health check pour la nouvelle stack (RagDocument/RagChunk + embeddings HTTP).
    """
    db = SessionLocal()
    try:
        docs_count = db.query(func.count(RagDocument.id)).scalar() or 0
        chunks_count = db.query(func.count(RagChunk.id)).scalar() or 0

        # Test embedding simple
        try:
            vec = rag_service.get_embedding("healthcheck test")
            embedding_ok = bool(vec is not None and vec.shape[0] > 0 and float(np.linalg.norm(vec)) > 0)
        except Exception as e:
            logger.error(f"RAG health embedding error: {e}")
            embedding_ok = False

        is_healthy = (docs_count >= 0) and embedding_ok

        return {
            "status": "healthy" if is_healthy else "degraded",
            "docs_count": docs_count,
            "chunks_count": chunks_count,
            "checks": {
                "database_connection": True,
                "embeddings_ok": embedding_ok,
                "documents_available": docs_count > 0,
                "chunks_available": chunks_count > 0,
            },
            "model_info": {
                "embedding_model": rag_service.EMBEDDING_MODEL,
                "llm_model_default": rag_service.LLM_MODEL_DEFAULT,
                "llama_server_url": rag_service.LLAMA_SERV_URL,
            },
        }

    except Exception as e:
        logger.error(f"RAG healthcheck error: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "checks": {
                "database_connection": False,
                "embeddings_ok": False,
                "documents_available": False,
                "chunks_available": False,
            },
        }
    finally:
        db.close()
