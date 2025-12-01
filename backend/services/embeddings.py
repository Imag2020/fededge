"""
Embeddings Service - Local text embedding generation
Uses BGE/E5 models for generating embeddings for RAG system
"""

import os
import numpy as np
from typing import Optional, List
import logging
from ..db.models import SessionLocal, engine
from ..interfaces.vector_index import create_vector_index, VectorIndex

logger = logging.getLogger(__name__)

# Lazy imports pour sentence-transformers
try:
    import torch
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available")

class EmbeddingService:
    """
    Local embedding service using sentence-transformers
    Optimized for crypto news and RAG use case
    """
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """
        Initialize embedding service
        
        Args:
            model_name: HuggingFace model name (default: BGE-small for efficiency)
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dim = 384  # BGE-small dimension
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
        
        # Initialize Qdrant vector index
        self.vector_index = create_vector_index("qdrant")
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            
            # Enable model to use less memory if CPU
            if self.device == "cpu":
                self.model.max_seq_length = 512
            
            logger.info(f"✅ Embedding model loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            numpy array of shape (384,) with float32 dtype
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        try:
            # Truncate very long texts
            text = text[:4000] if len(text) > 4000 else text
            
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            numpy array of shape (len(texts), 384)
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        if not texts:
            return np.array([]).reshape(0, self.embedding_dim)
        
        try:
            # Preprocess texts
            clean_texts = []
            for text in texts:
                if not text or not text.strip():
                    clean_texts.append("")
                else:
                    clean_texts.append(text[:4000])
            
            # Generate embeddings in batches
            embeddings = self.model.encode(
                clean_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 50
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

    def upsert_news_embedding(self, news_id: int, text: str) -> bool:
        """
        Update or insert embedding for a news article using sqlite-vec
        
        Args:
            news_id: ID of the news article
            text: Text to embed (title + summary + content)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding
            embedding = self.embed_text(text)
            
            # Use vector index for proper UPSERT
            success = self.vector_index.upsert(news_id, embedding)
            
            if success:
                # Update news article metadata
                with SessionLocal() as db:
                    from ..db.models import NewsArticle
                    import datetime
                    
                    article = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()
                    if article:
                        article.embedding_generated = True
                        article.embedding_model = self.model_name
                        article.embedding_date = datetime.datetime.utcnow()
                        db.commit()
                
                logger.debug(f"✅ Embedding updated for news_id: {news_id}")
                return True
            else:
                logger.error(f"❌ Vector index upsert failed for news_id: {news_id}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert embedding for news_id {news_id}: {e}")
            return False
    
    def get_text_for_embedding(self, news_article) -> str:
        """
        Prepare text for embedding from news article
        
        Args:
            news_article: NewsArticle instance
            
        Returns:
            Concatenated text for embedding
        """
        parts = []
        
        if news_article.title:
            parts.append(news_article.title)
        
        if news_article.summary:
            parts.append(news_article.summary)
        
        if news_article.content:
            # Truncate content to avoid very long texts
            content = news_article.content[:4000] if len(news_article.content) > 4000 else news_article.content
            parts.append(content)
        
        return "\n".join(parts)

# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None

def get_embedder():
    """
    Get global embedding service instance

    Returns LlamaCppEmbeddingService if enabled, otherwise sentence-transformers
    """
    global _embedding_service

    # Check if LlamaCpp embeddings are enabled
    use_llamacpp = os.getenv("USE_LLAMACPP_EMBEDDINGS", "true").lower() == "true"

    if _embedding_service is None:
        if use_llamacpp:
            try:
                from .llamacpp_embeddings import get_llamacpp_embedder
                logger.info("Using LlamaCpp embeddings (Gemma 3 270M)")
                _embedding_service = get_llamacpp_embedder()
            except Exception as e:
                logger.warning(f"Failed to load LlamaCpp embeddings: {e}, falling back to sentence-transformers")
                use_llamacpp = False

        if not use_llamacpp:
            # Fallback to sentence-transformers
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("Neither LlamaCpp nor sentence-transformers available for embeddings")

            model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
            logger.info(f"Using sentence-transformers embeddings: {model_name}")
            _embedding_service = EmbeddingService(model_name)

    return _embedding_service

def embed_text(text: str) -> np.ndarray:
    """Convenience function to embed single text"""
    return get_embedder().embed_text(text)

def upsert_news_embedding(news_id: int, text: str) -> bool:
    """Convenience function to update news embedding"""
    return get_embedder().upsert_news_embedding(news_id, text)