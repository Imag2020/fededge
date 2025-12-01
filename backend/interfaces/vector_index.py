"""
Qdrant Vector Index Interface and Implementation
Provides abstraction layer for vector database operations using Qdrant
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
import logging

# Lazy import pour Qdrant (optionnel)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    from qdrant_client.http.models import UpdateResult
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("qdrant_client not available, only SQLite-vec backend will be available")

import uuid

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Result from vector search"""
    id: int
    score: float
    metadata: Dict[str, Any] = None

class VectorIndex(ABC):
    """
    Abstract interface for vector index operations
    Allows switching between different vector database backends
    """
    
    @abstractmethod
    def upsert(self, news_id: int, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Insert or update vector embedding for a news article
        
        Args:
            news_id: ID of the news article
            embedding: Vector embedding as numpy array
            metadata: Optional metadata to store with the vector
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query vector as numpy array
            k: Number of results to return
            filters: Optional filters (implementation-specific)
            
        Returns:
            List of VectorSearchResult objects
        """
        pass
    
    @abstractmethod
    def delete(self, news_id: int) -> bool:
        """
        Delete vector embedding for a news article
        
        Args:
            news_id: ID of the news article to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get total number of vectors in the index
        
        Returns:
            Number of vectors indexed
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of the vector index
        
        Returns:
            Dictionary with health information
        """
        pass

class QdrantIndex(VectorIndex):
    """
    Qdrant implementation of VectorIndex
    Uses Qdrant vector database for high-performance vector operations
    """
    
    def __init__(self, host: str = None, port: int = None, collection_name: str = "news_embeddings"):
        """
        Initialize Qdrant vector index

        Args:
            host: Qdrant server host (defaults to env QDRANT_HOST or localhost)
            port: Qdrant server port (defaults to env QDRANT_PORT or 6333)
            collection_name: Name of the collection to store vectors
        """
        import os
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name

        # Auto-detect embedding dimension from active embedder
        try:
            from ..services.llamacpp_embeddings import get_llamacpp_embedder
            embedder = get_llamacpp_embedder()
            self.embedding_dim = embedder.get_embedding_dimension()
            logger.info(f"✅ Detected embedding dimension: {self.embedding_dim} from {embedder.model_name}")
        except Exception as e:
            # Fallback to EmbeddingGemma-300M default (768 dimensions)
            self.embedding_dim = 768
            logger.warning(f"⚠️ Could not auto-detect embedding dimension, using default: {self.embedding_dim}. Error: {e}")
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=self.host, port=self.port)
        
        # Collection will be created on first upsert if needed
        logger.info(f"✅ Qdrant client initialized for {self.host}:{self.port}")
        
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE  # Use cosine similarity
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"✅ Qdrant collection exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring collection: {e}")
            raise
    
    def upsert(self, news_id: int, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Insert or update embedding in Qdrant"""
        try:
            # Ensure collection exists before first upsert
            self._ensure_collection()
            
            # Convert numpy array to list
            if isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            # Prepare metadata
            payload = metadata or {}
            payload["news_id"] = news_id
            
            # Create point
            point = PointStruct(
                id=news_id,  # Use news_id as Qdrant point ID
                vector=embedding_list,
                payload=payload
            )
            
            # Upsert point
            result = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            # Check if operation was successful
            if hasattr(result, 'status') and result.status == 'completed':
                logger.debug(f"✅ Upserted embedding for news {news_id}")
                return True
            else:
                logger.warning(f"⚠️ Upsert may have failed for news {news_id}: {result}")
                return True  # Qdrant usually succeeds if no exception
                
        except Exception as e:
            logger.error(f"❌ Error upserting embedding for news {news_id}: {e}")
            return False
    
    def search(self, query_embedding: np.ndarray, k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """Search using Qdrant similarity search"""
        try:
            # Convert numpy array to list
            if isinstance(query_embedding, np.ndarray):
                query_list = query_embedding.tolist()
            else:
                query_list = list(query_embedding)
            
            # Prepare filters if provided
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_list,
                limit=k,
                query_filter=search_filter
            )
            
            # Convert to VectorSearchResult
            results = []
            for hit in search_results:
                result = VectorSearchResult(
                    id=int(hit.id),
                    score=float(hit.score),
                    metadata=hit.payload or {}
                )
                results.append(result)
            
            logger.debug(f"✅ Found {len(results)} results in Qdrant search")
            return results
                
        except Exception as e:
            logger.error(f"❌ Error searching vectors in Qdrant: {e}")
            return []
    
    def delete(self, news_id: int) -> bool:
        """Delete embedding by news_id"""
        try:
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=[news_id]
            )
            
            if hasattr(result, 'status') and result.status == 'completed':
                logger.debug(f"✅ Deleted embedding for news {news_id}")
                return True
            else:
                logger.warning(f"⚠️ Delete may have failed for news {news_id}: {result}")
                return True  # Assume success if no exception
                
        except Exception as e:
            logger.error(f"❌ Error deleting embedding for news {news_id}: {e}")
            return False
    
    def count(self) -> int:
        """Get total number of embeddings"""
        try:
            # Use alternative method to count points - scroll with limit 0
            response = self.client.scroll(
                collection_name=self.collection_name,
                limit=0,
                with_payload=False,
                with_vectors=False
            )
            # Response should have next_page_offset = None when complete
            if hasattr(response, 'points'):
                return len(response.points)
            else:
                # Fallback: try collection info with error handling
                try:
                    collection_info = self.client.get_collection(self.collection_name)
                    return collection_info.points_count or 0
                except:
                    return 0
                
        except Exception as e:
            logger.debug(f"⚠️ Error counting embeddings (non-critical): {e}")
            return 0  # Return 0 instead of failing
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of Qdrant index"""
        try:
            # Test basic connection
            collections = self.client.get_collections()
            
            # Check if our collection exists
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                # Get collection info
                collection_info = self.client.get_collection(self.collection_name)
                
                return {
                    "status": "healthy",
                    "backend": "qdrant",
                    "host": self.host,
                    "port": self.port,
                    "collection_name": self.collection_name,
                    "total_embeddings": collection_info.points_count or 0,
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value
                }
            else:
                # Collection doesn't exist yet but connection works
                return {
                    "status": "healthy",
                    "backend": "qdrant",
                    "host": self.host,
                    "port": self.port,
                    "collection_name": self.collection_name,
                    "total_embeddings": 0,
                    "vector_size": self.embedding_dim,
                    "distance": "Cosine",
                    "note": "Collection will be created on first upsert"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "qdrant",
                "host": self.host,
                "port": self.port,
                "collection_name": self.collection_name,
                "error": str(e),
                "total_embeddings": 0
            }

# Factory function to create the appropriate vector index
def create_vector_index(backend: str = "qdrant", **kwargs) -> VectorIndex:
    """
    Factory function to create vector index instances

    Args:
        backend: Vector backend to use ("qdrant" or "sqlite-vec")
        **kwargs: Backend-specific configuration

    Returns:
        VectorIndex instance
    """
    if backend == "qdrant":
        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant not available, falling back to SQLite-vec")
            backend = "sqlite-vec"
        else:
            return QdrantIndex(**kwargs)

    if backend == "sqlite-vec":
        try:
            from ..services.sqlite_vec_service import SQLiteVecIndex
            return SQLiteVecIndex(**kwargs)
        except ImportError:
            raise ImportError("SQLite-vec backend not available")

    raise ValueError(f"Unsupported vector backend: {backend}")