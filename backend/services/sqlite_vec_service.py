"""
SQLite-vec Vector Index Implementation
Uses SQLite rag_documents table for vector search
"""

import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy import text

from ..interfaces.vector_index import VectorIndex, VectorSearchResult
from ..db.models import SessionLocal

logger = logging.getLogger(__name__)


class SQLiteVecIndex(VectorIndex):
    """
    SQLite-vec implementation using rag_documents table
    Stores embeddings as JSON arrays in SQLite
    """

    def __init__(self, **kwargs):
        """Initialize SQLite-vec index"""
        self.db_path = kwargs.get("db_path", "backend/db/fededge.db")
        logger.info(f"✅ SQLite-vec index initialized using {self.db_path}")

    def upsert(self, news_id: int, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Insert or update embedding in rag_documents table

        Args:
            news_id: ID of the news article
            embedding: Vector embedding as numpy array
            metadata: Optional metadata (not used in current schema)

        Returns:
            True if successful, False otherwise
        """
        try:
            db = SessionLocal()
            try:
                # Convert numpy array to JSON
                embedding_json = json.dumps(embedding.tolist())

                # Upsert into rag_documents
                db.execute(text("""
                    INSERT OR REPLACE INTO rag_documents (news_id, embedding, embedding_model, created_at)
                    VALUES (:news_id, :embedding, :model, datetime('now'))
                """), {
                    'news_id': news_id,
                    'embedding': embedding_json,
                    'model': 'bge-base-en-v1.5 (LlamaCpp)'
                })

                db.commit()
                logger.debug(f"✅ Upserted embedding for news {news_id}")
                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Error upserting embedding for news {news_id}: {e}")
            return False

    def search(self, query_embedding: np.ndarray, k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """
        Search for similar vectors using cosine similarity

        Args:
            query_embedding: Query vector as numpy array
            k: Number of results to return
            filters: Optional filters (not implemented)

        Returns:
            List of VectorSearchResult objects
        """
        try:
            db = SessionLocal()
            try:
                # Fetch all embeddings from database
                rows = db.execute(text("""
                    SELECT r.news_id, r.embedding, n.title, n.source, n.url, n.published_at
                    FROM rag_documents r
                    JOIN news_articles n ON r.news_id = n.id
                """)).fetchall()

                if not rows:
                    logger.warning("⚠️ No embeddings found in rag_documents")
                    return []

                # Calculate cosine similarity for each embedding
                results = []
                query_norm = np.linalg.norm(query_embedding)

                for row in rows:
                    news_id, embedding_json, title, source, url, published_at = row

                    # Parse embedding from JSON
                    stored_embedding = np.array(json.loads(embedding_json), dtype=np.float32)

                    # Cosine similarity
                    stored_norm = np.linalg.norm(stored_embedding)
                    if stored_norm > 0 and query_norm > 0:
                        similarity = np.dot(query_embedding, stored_embedding) / (query_norm * stored_norm)
                    else:
                        similarity = 0.0

                    results.append(VectorSearchResult(
                        id=news_id,
                        score=float(similarity),
                        metadata={
                            'title': title,
                            'source': source,
                            'url': url,
                            'published_at': str(published_at) if published_at else None
                        }
                    ))

                # Sort by similarity descending and return top k
                results.sort(key=lambda x: x.score, reverse=True)
                return results[:k]

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Error searching vectors in SQLite-vec: {e}")
            return []

    def delete(self, news_id: int) -> bool:
        """
        Delete embedding by news_id

        Args:
            news_id: ID of the news article to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            db = SessionLocal()
            try:
                db.execute(text("""
                    DELETE FROM rag_documents WHERE news_id = :news_id
                """), {'news_id': news_id})

                db.commit()
                logger.debug(f"✅ Deleted embedding for news {news_id}")
                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Error deleting embedding for news {news_id}: {e}")
            return False

    def count(self) -> int:
        """
        Get total number of embeddings

        Returns:
            Number of vectors indexed
        """
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) FROM rag_documents
                """)).fetchone()

                return result[0] if result else 0

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Error counting embeddings: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of the vector index

        Returns:
            Dictionary with health information
        """
        try:
            total = self.count()

            return {
                "status": "healthy",
                "backend": "sqlite-vec",
                "db_path": self.db_path,
                "total_embeddings": total,
                "vector_size": 768,  # BGE-base dimension
                "distance": "cosine"
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "sqlite-vec",
                "db_path": self.db_path,
                "error": str(e),
                "total_embeddings": 0
            }
