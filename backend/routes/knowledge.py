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

from ..db.models import SessionLocal
from ..db import crud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Récupérer les statistiques de la base de connaissances RAG"""
    try:
        from .db.models import SessionLocal
        from .db import crud
        import sqlite3
        import os

        # Stats Vector Database (Qdrant ou sqlite-vec)
        db_status = "online"
        news_collection_count = 0
        crypto_seed_count = 0
        total_vectors = 0

        try:
            # Essayer de compter les documents RAG dans la base SQLite
            db = SessionLocal()
            try:
                from sqlalchemy import text
                result = db.execute(text("SELECT COUNT(*) FROM rag_documents")).fetchone()
                news_collection_count = result[0] if result else 0
                total_vectors = news_collection_count
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not get vector stats: {e}")
            db_status = "warning"

        # Stats SQLite Datasets
        datasets_stats = {}
        datasets_dir = "datasets"

        if os.path.exists(datasets_dir):
            # World State Sessions
            world_db = os.path.join(datasets_dir, "world_state_sessions.db")
            if os.path.exists(world_db):
                try:
                    with sqlite3.connect(world_db) as conn:
                        cursor = conn.execute("SELECT COUNT(*) as total, MAX(timestamp) as last_session FROM world_state_sessions")
                        result = cursor.fetchone()
                        datasets_stats["world_state"] = {
                            "total_sessions": result[0] if result else 0,
                            "last_session": result[1] if result and result[1] else None,
                            "file_size_mb": round(os.path.getsize(world_db) / (1024*1024), 2)
                        }
                except:
                    datasets_stats["world_state"] = {"total_sessions": 0, "last_session": None, "file_size_mb": 0}

            # Candidates Trader Sessions
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
                except:
                    datasets_stats["candidates_trader"] = {"total_sessions": 0, "file_size_mb": 0}

            # Decider Trader Sessions
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
                except:
                    datasets_stats["decider_trader"] = {"total_sessions": 0, "file_size_mb": 0}

        # Stats SQLite (News Articles)
        db = SessionLocal()
        try:
            from sqlalchemy import text
            news_articles_count = db.execute(text("SELECT COUNT(*) FROM news_articles")).scalar()
            recent_articles_count = db.execute(text(
                "SELECT COUNT(*) FROM news_articles WHERE created_at > datetime('now', '-7 days')"
            )).scalar()
            # Récupérer la date de dernière modification
            last_news_update = db.execute(text(
                "SELECT MAX(created_at) FROM news_articles"
            )).scalar()
        except Exception as e:
            logger.error(f"Error getting news stats: {e}")
            news_articles_count = 0
            recent_articles_count = 0
            last_news_update = None
        finally:
            db.close()

        # Récupérer la dernière modification des datasets
        datasets_last_update = None
        if datasets_stats.get("world_state", {}).get("last_session"):
            datasets_last_update = datasets_stats["world_state"]["last_session"]

        return {
            "status": "success",
            "knowledge_stats": {
                "vector_database": {
                    "status": db_status,
                    "news_embeddings": news_collection_count,
                    "crypto_seed_knowledge": crypto_seed_count,
                    "total_vectors": total_vectors,
                    "embedding_model": "bge-base-en-v1.5 (LlamaCpp Q8)",
                    "embedding_service": "llama-cpp-python",
                    "database_path": "./backend/db/fededge.db (rag_documents)",
                    "vector_store": "SQLite-vec"
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

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving knowledge stats: {str(e)}",
            "knowledge_stats": {}
        }

@router.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Recherche dans la base de connaissances RAG"""
    try:
        from .services.sqlite_vec_service import SQLiteVecIndex
        from .services.llamacpp_embeddings import get_embedding

        if not query or len(query.strip()) < 3:
            return {
                "status": "error",
                "message": "Query must be at least 3 characters",
                "results": []
            }

        # Generate query embedding
        query_embedding = await get_embedding(query.strip())
        if query_embedding is None:
            return {
                "status": "error",
                "message": "Failed to generate query embedding",
                "results": []
            }

        # Search in SQLite-vec
        vec_index = SQLiteVecIndex()
        search_results = vec_index.search(query_embedding, k=limit)

        # Format results from VectorSearchResult objects
        results = []
        for result in search_results:
            metadata = result.metadata or {}
            results.append({
                "title": metadata.get("title", f"News #{result.id}"),
                "source": metadata.get("source", "news"),
                "score": round(result.score, 3),
                "content": metadata.get("url", ""),
                "metadata": metadata
            })

        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching knowledge base: {str(e)}",
            "results": []
        }

@router.post("/knowledge/add-text")
async def add_text_to_knowledge(request: dict):
    """Ajouter du texte à la base de connaissances"""
    try:
        from .services.sqlite_vec_service import SQLiteVecIndex
        from .services.llamacpp_embeddings import get_embedding
        from .db.models import NewsArticle
        from datetime import datetime

        title = request.get("title", "").strip()
        content = request.get("content", "").strip()
        source = request.get("source", "user_upload")

        if not title or not content:
            return {
                "status": "error",
                "message": "Title and content are required"
            }

        # Create NewsArticle entry
        db = SessionLocal()
        try:
            import uuid
            # Generate unique URL to avoid UNIQUE constraint
            unique_url = f"user_upload://{source}/{uuid.uuid4().hex[:12]}"

            news_article = NewsArticle(
                title=title,
                content=content,
                source=source,
                url=unique_url,
                published_at=datetime.now(),
                scraped_date=datetime.now(),
                category="knowledge",
                sentiment_score=0.0
            )
            db.add(news_article)
            db.commit()
            db.refresh(news_article)

            news_id = news_article.id

            # Generate embedding
            embedding = await get_embedding(content)
            if embedding is None:
                db.rollback()
                return {
                    "status": "error",
                    "message": "Failed to generate embedding"
                }

            # Add to SQLite-vec
            vec_index = SQLiteVecIndex()
            success = vec_index.upsert(news_id, embedding)

            if success:
                return {
                    "status": "success",
                    "message": "Text added to knowledge base",
                    "document_id": news_id
                }
            else:
                db.rollback()
                return {
                    "status": "error",
                    "message": "Failed to add text to vector index"
                }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error adding text to knowledge: {e}")
        return {
            "status": "error",
            "message": f"Error adding text: {str(e)}"
        }

@router.post("/knowledge/add-file")
async def add_file_to_knowledge(file: UploadFile = File(...)):
    """Ajouter un fichier à la base de connaissances"""
    try:
        from .services.sqlite_vec_service import SQLiteVecIndex
        from .services.llamacpp_embeddings import get_embedding
        from .db.models import NewsArticle
        import tempfile
        import os
        from datetime import datetime

        # Vérifier le type de fichier
        allowed_extensions = ['.pdf', '.txt', '.doc', '.docx']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            return {
                "status": "error",
                "message": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            }

        # Vérifier la taille (10MB max)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            return {
                "status": "error",
                "message": "File too large (max 10MB)"
            }

        logger.info(f"File upload: {file.filename} ({len(content)} bytes, type: {file_ext})")

        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Extraire le texte selon le type
            extracted_text = ""
            logger.info(f"Extracting text from {file_ext} file...")

            if file_ext == '.txt':
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()

            elif file_ext == '.pdf':
                try:
                    # Try pdfplumber first (more robust)
                    try:
                        import pdfplumber
                        with pdfplumber.open(tmp_path) as pdf:
                            extracted_text = ""
                            for page in pdf.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    extracted_text += page_text + "\n"
                        logger.info(f"PDF extraction (pdfplumber): {len(extracted_text)} chars from {len(pdf.pages)} pages")
                    except ImportError:
                        # Fallback to PyPDF2
                        import PyPDF2
                        with open(tmp_path, 'rb') as f:
                            reader = PyPDF2.PdfReader(f)
                            extracted_text = ""
                            for page in reader.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    extracted_text += page_text + "\n"
                        logger.info(f"PDF extraction (PyPDF2): {len(extracted_text)} chars from {len(reader.pages)} pages")
                except Exception as e:
                    logger.error(f"Error extracting PDF: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "message": f"Error extracting PDF: {str(e)}"
                    }

            elif file_ext in ['.doc', '.docx']:
                try:
                    import docx
                    doc = docx.Document(tmp_path)
                    extracted_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                except ImportError:
                    return {
                        "status": "error",
                        "message": "Word document processing not available. Please install python-docx."
                    }

            if not extracted_text.strip():
                logger.error(f"No text extracted from {file.filename} (type: {file_ext}, size: {len(content)} bytes)")
                return {
                    "status": "error",
                    "message": f"No text could be extracted from the {file_ext} file. Extracted: '{extracted_text[:200]}'"
                }

            # Clean extracted text (remove PDF headers, binary content)
            import re
            # Remove PDF header patterns
            extracted_text = re.sub(r'^%PDF-[\d.]+.*?[\r\n]+', '', extracted_text, flags=re.MULTILINE)
            # Remove binary/control characters
            extracted_text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', extracted_text)
            # Remove multiple spaces/newlines
            extracted_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', extracted_text)
            extracted_text = extracted_text.strip()

            if not extracted_text or len(extracted_text) < 50:
                logger.error(f"Extracted text too short after cleaning: {len(extracted_text)} chars")
                return {
                    "status": "error",
                    "message": f"Extracted text is too short or contains mostly binary data (got {len(extracted_text)} chars)"
                }

            logger.info(f"Successfully extracted and cleaned {len(extracted_text)} chars from {file.filename}")

            # Chunk long documents
            from .services.llamacpp_embeddings import chunk_text
            chunks = chunk_text(extracted_text, max_chunk_size=500, overlap=50)
            logger.info(f"Document chunked into {len(chunks)} parts (avg {sum(len(c) for c in chunks)//len(chunks)} chars/chunk)")

            # Create NewsArticle entries for each chunk
            db = SessionLocal()
            try:
                import uuid
                base_title = os.path.splitext(file.filename)[0]
                vec_index = SQLiteVecIndex()

                created_ids = []
                failed_chunks = 0

                for i, chunk_text_content in enumerate(chunks):
                    chunk_title = f"{base_title} (part {i+1}/{len(chunks)})"
                    # Generate unique URL to avoid UNIQUE constraint
                    unique_url = f"file://{file.filename}/{uuid.uuid4().hex[:12]}"

                    news_article = NewsArticle(
                        title=chunk_title,
                        content=chunk_text_content,
                        source="file_upload",
                        url=unique_url,
                        published_at=datetime.now(),
                        scraped_date=datetime.now(),
                        category="knowledge",
                        sentiment_score=0.0
                    )
                    db.add(news_article)
                    db.commit()
                    db.refresh(news_article)

                    news_id = news_article.id
                    created_ids.append(news_id)

                    # Generate embedding for this chunk
                    embedding = await get_embedding(chunk_text_content)
                    if embedding is None:
                        logger.warning(f"Failed to generate embedding for chunk {i+1}/{len(chunks)}")
                        failed_chunks += 1
                        continue

                    # Add to SQLite-vec
                    success = vec_index.upsert(news_id, embedding)
                    if not success:
                        logger.warning(f"Failed to add chunk {i+1}/{len(chunks)} to vector index")
                        failed_chunks += 1

                if len(created_ids) == 0:
                    db.rollback()
                    return {
                        "status": "error",
                        "message": "Failed to create any chunks"
                    }

                if failed_chunks > 0:
                    return {
                        "status": "partial",
                        "message": f"File processed with {failed_chunks}/{len(chunks)} failed chunks",
                        "document_ids": created_ids,
                        "chunks_created": len(created_ids),
                        "chunks_failed": failed_chunks,
                        "extracted_length": len(extracted_text)
                    }
                else:
                    return {
                        "status": "success",
                        "message": f"File processed and added to knowledge base ({len(chunks)} chunks)",
                        "document_ids": created_ids,
                        "chunks_created": len(created_ids),
                        "extracted_length": len(extracted_text)
                    }
            finally:
                db.close()

        finally:
            # Nettoyer le fichier temporaire
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"❌ Error adding file to knowledge: {e}")
        return {
            "status": "error",
            "message": f"Error processing file: {str(e)}"
        }

@router.post("/knowledge/add-url")


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
    RAG system health check endpoint
    """
    try:
        from ..mcp.rag_tools import RagTools

        # Get RAG stats
        stats_result = RagTools.rag_stats_tool()

        if not stats_result["success"]:
            return {
                "status": "unhealthy",
                "error": stats_result.get("error", "Unknown error"),
                "details": {}
            }

        stats = stats_result["stats"]

        # Check Qdrant connection via vector index
        vector_index_info = stats.get("vector_index", {})
        qdrant_healthy = vector_index_info.get("status") == "healthy"

        # Health status
        is_healthy = (
            qdrant_healthy and
            stats["total_articles"] > 0 and
            stats["embedding_coverage"] > 0
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "qdrant_connected": qdrant_healthy,
            "total_articles": stats["total_articles"],
            "embedded_articles": stats["embedded_articles"],
            "embedding_coverage": stats["embedding_coverage"],
            "model_info": stats["model_info"],
            "vector_index": vector_index_info,
            "checks": {
                "database_connection": True,
                "qdrant_connection": qdrant_healthy,
                "articles_available": stats["total_articles"] > 0,
                "embeddings_available": stats["embedded_articles"] > 0
            }
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "checks": {
                "database_connection": False,
                "qdrant_connection": False,
                "articles_available": False,
                "embeddings_available": False
            }
        }
