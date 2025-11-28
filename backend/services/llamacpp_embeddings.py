"""
LlamaCpp Embeddings Service - Local embedding generation using llama.cpp HTTP API
Uses BGE-base-en-v1.5 model (GGUF) for high-quality embeddings via HTTP server on port 9002
"""

import os
import numpy as np
from typing import List, Optional, Tuple
import logging
import aiohttp
import asyncio
import re

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for better embedding coverage

    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Character overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]

    # Split by paragraphs first
    paragraphs = re.split(r'\n\s*\n', text)

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If paragraph itself is too long, split by sentences
        if len(para) > max_chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                # If single sentence is too long, hard split
                if len(sentence) > max_chunk_size:
                    for i in range(0, len(sentence), max_chunk_size - overlap):
                        chunk = sentence[i:i + max_chunk_size]
                        if chunk.strip():
                            chunks.append(chunk.strip())
                else:
                    if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                        current_chunk += " " + sentence if current_chunk else sentence
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
        else:
            # Try to add paragraph to current chunk
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = para

    # Add last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Add overlap between chunks
    overlapped_chunks = []
    for i, chunk in enumerate(chunks):
        if i > 0 and overlap > 0:
            # Add end of previous chunk as context
            prev_overlap = chunks[i-1][-overlap:] if len(chunks[i-1]) > overlap else chunks[i-1]
            overlapped_chunk = prev_overlap + " [...] " + chunk
            overlapped_chunks.append(overlapped_chunk)
        else:
            overlapped_chunks.append(chunk)

    return overlapped_chunks


class LlamaCppEmbeddingService:
    """
    Embedding service using llama.cpp HTTP API server
    Connects to llama.cpp embedding server on port 9002

    Current model: EmbeddingGemma-300M (Unsloth GGUF Q8)
    - Architecture: Gemma-based embedding model (300M params)
    - Embedding dimension: 768
    - Context length: 2048 tokens
    - Optimized for: Semantic search, RAG, low-resource environments
    - Format: GGUF Q8 quantization for CPU efficiency
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9002",
        embedding_dim: int = 768,
        timeout: int = 30
    ):
        """
        Initialize LlamaCpp embedding service HTTP client

        Args:
            base_url: Base URL of llama.cpp embedding server (default: http://localhost:9002)
            embedding_dim: Embedding dimension (768 for EmbeddingGemma-300M)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.embedding_dim = embedding_dim
        self.timeout = timeout
        self.embeddings_url = f"{self.base_url}/v1/embeddings"
        self.model_name = "embeddinggemma-300M"  # Model identifier

        logger.info(f"LlamaCpp Embedding Service configured: {self.base_url}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Embedding dimension: {self.embedding_dim}")

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text via HTTP API

        Args:
            text: Input text to embed

        Returns:
            numpy array of shape (embedding_dim,) with float32 dtype
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)

        try:
            # Truncate very long texts (server has parallel=1, needs small batches)
            text = text[:600] if len(text) > 600 else text

            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in async context - use run_in_executor to avoid blocking
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._sync_embed_text, text)
                    embedding_np = future.result(timeout=self.timeout)
                return embedding_np
            except RuntimeError:
                # No running loop - create one (sync context)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    embedding_np = loop.run_until_complete(self._embed_text_async(text))
                    return embedding_np
                finally:
                    loop.close()

        except Exception as e:
            logger.error(f"Error generating LlamaCpp embedding: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def _sync_embed_text(self, text: str) -> np.ndarray:
        """Synchronous wrapper for async embed - runs in thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._embed_text_async(text))
        finally:
            loop.close()

    async def _embed_text_async(self, text: str) -> np.ndarray:
        """Async implementation of embed_text"""
        try:
            # Truncate text to max 150 tokens (~600 chars for safety)
            # Server has parallel=1, so we need small batches to avoid 500 errors
            max_chars = 600
            truncated_text = text[:max_chars] if len(text) > max_chars else text

            if len(text) > max_chars:
                logger.warning(f"Text truncated from {len(text)} to {max_chars} chars for embedding")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "input": truncated_text,
                    "model": self.model_name  # embeddinggemma-300M
                }

                async with session.post(self.embeddings_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract embedding from OpenAI-compatible response
                        # Format: {"data": [{"embedding": [...], "index": 0}]}
                        if "data" in result and result["data"]:
                            embedding_vector = result["data"][0]["embedding"]
                        else:
                            logger.error(f"Unexpected embedding response format: {result}")
                            return np.zeros(self.embedding_dim, dtype=np.float32)

                        # Convert to numpy array
                        embedding_np = np.array(embedding_vector, dtype=np.float32)

                        # L2 normalization
                        norm = np.linalg.norm(embedding_np)
                        if norm > 0:
                            embedding_np = embedding_np / norm

                        return embedding_np

                    else:
                        error_text = await response.text()
                        logger.error(f"Embedding server error {response.status}: {error_text}")
                        return np.zeros(self.embedding_dim, dtype=np.float32)

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to embedding server at {self.base_url}")
            return np.zeros(self.embedding_dim, dtype=np.float32)
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to embedding server: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)
        except Exception as e:
            logger.error(f"Unexpected error in embedding generation: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)

        embeddings = []
        for i, text in enumerate(texts):
            if i % 10 == 0:
                logger.info(f"Embedding batch progress: {i}/{len(texts)}")

            emb = self.embed_text(text)
            embeddings.append(emb)

        return np.array(embeddings, dtype=np.float32)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings (768 for EmbeddingGemma-300M)"""
        return self.embedding_dim

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

    def upsert_news_embedding(self, news_id: int, text: str) -> bool:
        """
        Update or insert embedding for a news article

        Args:
            news_id: ID of the news article
            text: Text to embed (title + summary + content)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding
            embedding = self.embed_text(text)

            # Store in rag_documents table via direct SQL (simple fallback)
            from ..db.models import SessionLocal
            from sqlalchemy import text
            import datetime
            import json

            db = SessionLocal()
            try:
                # Serialize embedding as JSON array
                embedding_json = json.dumps(embedding.tolist())

                # UPSERT into rag_documents
                db.execute(text("""
                    INSERT OR REPLACE INTO rag_documents (news_id, embedding, embedding_model, created_at)
                    VALUES (:news_id, :embedding, :model, :created_at)
                """), {
                    'news_id': news_id,
                    'embedding': embedding_json,
                    'model': f'{self.model_name} (LlamaCpp)',
                    'created_at': datetime.datetime.utcnow()
                })

                # Update news article metadata
                db.execute(text("""
                    UPDATE news_articles
                    SET embedding_generated = 1,
                        embedding_model = :model,
                        embedding_date = :date
                    WHERE id = :news_id
                """), {
                    'model': f'{self.model_name} (LlamaCpp)',
                    'date': datetime.datetime.utcnow(),
                    'news_id': news_id
                })

                db.commit()
                logger.debug(f"✅ Embedding stored for news_id: {news_id}")
                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Failed to upsert embedding for news_id {news_id}: {e}")
            return False


# Singleton instance
_llamacpp_embedder: Optional[LlamaCppEmbeddingService] = None


def get_llamacpp_embedder(
    base_url: str = "http://localhost:9002"
) -> LlamaCppEmbeddingService:
    """
    Get or create the LlamaCpp embedder singleton (HTTP API client)

    Args:
        base_url: Base URL of llama.cpp embedding server (default: http://localhost:9002)

    Returns:
        LlamaCppEmbeddingService instance
    """
    global _llamacpp_embedder

    if _llamacpp_embedder is None:
        logger.info(f"Creating new LlamaCpp embedder HTTP client: {base_url}")
        _llamacpp_embedder = LlamaCppEmbeddingService(base_url=base_url)

    return _llamacpp_embedder


async def get_embedding(text: str) -> Optional[np.ndarray]:
    """
    Helper function to get embedding for a text (async version)

    Args:
        text: Text to embed

    Returns:
        Numpy array embedding or None on error
    """
    try:
        if not text or not text.strip():
            logger.error("get_embedding: Empty text provided")
            return None

        embedder = get_llamacpp_embedder()
        # Use async method directly (we're already in async context)
        embedding = await embedder._embed_text_async(text)

        # Check if embedding is valid (not all zeros)
        if np.count_nonzero(embedding) == 0:
            logger.error(f"Generated embedding is all zeros for text: {text[:100]}...")
            return None

        logger.info(f"✅ Successfully generated embedding (dim={len(embedding)}, nonzero={np.count_nonzero(embedding)})")
        return embedding
    except Exception as e:
        logger.error(f"Error in get_embedding: {e}", exc_info=True)
        return None
