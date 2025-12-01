"""
RAG News Service - Vector search and retrieval for crypto news
Implements chunking, similarity search, and re-ranking
"""

import os
import math
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

from .embeddings import get_embedder
from ..db.models import SessionLocal, engine, RagTrace
from ..interfaces.vector_index import create_vector_index, VectorIndex
import datetime

logger = logging.getLogger(__name__)

@dataclass
class EvidenceCard:
    """Evidence card for RAG results"""
    id: int
    title: str
    url: str
    source: str
    published_at: str
    score: float
    passage: str  # Best chunk from the article
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "score": self.score,
            "passage": self.passage
        }

class TextChunker:
    """
    Text chunking utility for RAG
    Creates overlapping chunks for better coverage
    """
    
    def __init__(self, chunk_size: int = 800, overlap: int = 120):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If we're not at the end, try to break at word boundary
            if end < len(text):
                # Look for space to break cleanly
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward with overlap
            start = end - self.overlap
            if start >= len(text):
                break
        
        return chunks

class NewsRAGService:
    """
    RAG service for crypto news articles
    Provides vector search with chunking and re-ranking
    """
    
    def __init__(self):
        self.embedder = get_embedder()
        self.chunker = TextChunker(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "800")),
            overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
        )
        self.max_results = int(os.getenv("RAG_MAX_RESULTS", "20"))
        # Use SQLite-vec for news embeddings (stored in rag_documents table)
        self.vector_index = create_vector_index("sqlite-vec")
        
    def search_news(self, query: str, k: int = 6) -> List[EvidenceCard]:
        """
        Search for relevant news articles using vector similarity
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of EvidenceCard objects with relevant articles
        """
        start_time = time.time()
        
        try:
            # Step 1: Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            
            # Step 2: Vector search using sqlite-vec
            candidates = self._vector_search(query_embedding, limit=self.max_results)
            
            if not candidates:
                logger.warning("No candidates found in vector search")
                return []
            
            # Step 3: Chunk and find best passages
            evidence_cards = self._process_candidates(candidates, query, k)
            
            # Step 4: Log the search for future training
            self._log_search(query, evidence_cards, time.time() - start_time)
            
            return evidence_cards
            
        except Exception as e:
            logger.error(f"Error in news search: {e}")
            return []
    
    def _vector_search(self, query_embedding: np.ndarray, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using sqlite-vec
        
        Args:
            query_embedding: Query embedding as numpy array
            limit: Maximum results to return
            
        Returns:
            List of candidate articles with similarity scores
        """
        try:
            # Use vector index for search
            vector_results = self.vector_index.search(query_embedding, k=limit)
            
            if not vector_results:
                return []
            
            # Get article details for the matching IDs
            candidates = []
            from sqlalchemy import text
            with engine.connect() as conn:
                # Build query for matching news articles
                ids = [int(result.id) for result in vector_results]
                id_placeholders = ','.join([str(id) for id in ids])
                
                result = conn.execute(text(f"""
                    SELECT id, title, url, source, published_at, summary, content
                    FROM news_rag_view
                    WHERE id IN ({id_placeholders})
                """))
                
                # Create lookup for scores
                score_lookup = {result.id: result.score for result in vector_results}
                
                for row in result:
                    news_id = row[0]
                    candidates.append({
                        'id': news_id,
                        'title': row[1],
                        'url': row[2],
                        'source': row[3],
                        'published_at': row[4],
                        'summary': row[5] or '',
                        'content': row[6] or '',
                        'score': score_lookup.get(news_id, 1.0)
                    })
                
                # Sort by score (lower is better for distance)
                candidates.sort(key=lambda x: x['score'])
                return candidates
                
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _process_candidates(self, candidates: List[Dict], query: str, k: int) -> List[EvidenceCard]:
        """
        Process candidates with chunking and re-ranking
        
        Args:
            candidates: Raw candidates from vector search
            query: Original query for chunking relevance
            k: Number of final results
            
        Returns:
            List of EvidenceCard objects
        """
        try:
            # Prepare texts for chunking and TF-IDF
            candidate_texts = []
            candidate_metadata = []
            
            for candidate in candidates:
                # Combine summary and content for chunking
                full_text = ""
                if candidate['summary']:
                    full_text += candidate['summary'] + "\n"
                if candidate['content']:
                    full_text += candidate['content']
                
                if not full_text.strip():
                    continue
                
                # Create chunks
                chunks = self.chunker.chunk_text(full_text)
                
                # Find best chunk for this candidate using cosine similarity
                best_chunk = self._find_best_chunk(chunks, query)
                
                candidate_texts.append(best_chunk)
                candidate_metadata.append({
                    **candidate,
                    'best_chunk': best_chunk
                })
            
            if not candidate_texts:
                return []
            
            # Re-rank using TF-IDF similarity
            final_candidates = self._rerank_with_tfidf(
                candidate_texts, candidate_metadata, query, k
            )
            
            # Convert to EvidenceCard objects
            evidence_cards = []
            for candidate in final_candidates:
                # Format published_at safely
                published_at_str = 'Unknown'
                if candidate['published_at']:
                    if hasattr(candidate['published_at'], 'strftime'):
                        # It's a datetime object
                        published_at_str = candidate['published_at'].strftime('%Y-%m-%d')
                    elif isinstance(candidate['published_at'], str):
                        # It's already a string
                        published_at_str = candidate['published_at'][:10]  # Take first 10 chars (YYYY-MM-DD)
                
                card = EvidenceCard(
                    id=candidate['id'],
                    title=candidate['title'],
                    url=candidate['url'] or f"news://{candidate['id']}",
                    source=candidate['source'],
                    published_at=published_at_str,
                    score=candidate['final_score'],
                    passage=candidate['best_chunk'][:500] + "..." if len(candidate['best_chunk']) > 500 else candidate['best_chunk']
                )
                evidence_cards.append(card)
            
            return evidence_cards
            
        except Exception as e:
            logger.error(f"Error processing candidates: {e}")
            return []
    
    def _find_best_chunk(self, chunks: List[str], query: str) -> str:
        """
        Find the most relevant chunk for the query using embedding similarity
        
        Args:
            chunks: List of text chunks
            query: Search query
            
        Returns:
            Best matching chunk
        """
        if not chunks:
            return ""
        
        if len(chunks) == 1:
            return chunks[0]
        
        try:
            # Embed query and chunks
            query_emb = self.embedder.embed_text(query)
            chunk_embs = self.embedder.embed_batch(chunks)
            
            # Calculate similarities
            similarities = cosine_similarity([query_emb], chunk_embs)[0]
            
            # Return chunk with highest similarity
            best_idx = np.argmax(similarities)
            return chunks[best_idx]
            
        except Exception as e:
            logger.error(f"Error finding best chunk: {e}")
            return chunks[0]  # Fallback to first chunk
    
    def _rerank_with_tfidf(self, texts: List[str], metadata: List[Dict], 
                          query: str, k: int) -> List[Dict]:
        """
        Re-rank candidates using TF-IDF similarity
        
        Args:
            texts: List of candidate texts (best chunks)
            metadata: Corresponding metadata for each text
            query: Search query
            k: Number of results to return
            
        Returns:
            Top-k re-ranked candidates
        """
        try:
            if len(texts) <= k:
                # No need to rerank, return all with scores
                for i, meta in enumerate(metadata):
                    meta['final_score'] = 1.0 - (i * 0.1)  # Simple decreasing score
                return metadata
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2)
            )
            
            # Fit on all texts + query
            all_texts = texts + [query]
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Calculate similarities between query and candidates
            query_vec = tfidf_matrix[-1]  # Last item is the query
            candidate_vecs = tfidf_matrix[:-1]  # All except last
            
            similarities = cosine_similarity(query_vec, candidate_vecs)[0]
            
            # Combine with original vector scores (weighted average)
            for i, meta in enumerate(metadata):
                vector_score = 1.0 - meta['score']  # Convert distance to similarity
                tfidf_score = similarities[i]
                
                # Weighted combination: 70% vector, 30% TF-IDF
                final_score = 0.7 * vector_score + 0.3 * tfidf_score
                meta['final_score'] = final_score
            
            # Sort by final score and return top-k
            ranked = sorted(metadata, key=lambda x: x['final_score'], reverse=True)
            return ranked[:k]
            
        except Exception as e:
            logger.error(f"Error in TF-IDF reranking: {e}")
            # Fallback: return top-k by original vector score
            sorted_by_vector = sorted(metadata, key=lambda x: x['score'])
            for i, meta in enumerate(sorted_by_vector):
                meta['final_score'] = 1.0 - (i * 0.1)
            return sorted_by_vector[:k]
    
    def _log_search(self, query: str, results: List[EvidenceCard], latency_ms: float):
        """
        Log search interaction for future fine-tuning
        
        Args:
            query: Search query
            results: Retrieved evidence cards
            latency_ms: Search latency in milliseconds
        """
        try:
            with SessionLocal() as db:
                card_ids = [card.id for card in results]
                sources = [{"id": card.id, "title": card.title, "url": card.url, "score": card.score} 
                          for card in results]
                
                answer_preview = f"Found {len(results)} relevant articles"
                if results:
                    answer_preview += f": {results[0].title[:100]}..."
                
                trace = RagTrace(
                    question=query,
                    card_ids_json=card_ids,
                    model="vector_search",
                    latency_ms=int(latency_ms * 1000),
                    answer_preview=answer_preview,
                    sources_json=sources
                )
                
                db.add(trace)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error logging search: {e}")

# Global RAG service instance
_rag_service: Optional[NewsRAGService] = None

def get_rag_service() -> NewsRAGService:
    """Get global RAG service instance"""
    global _rag_service
    
    if _rag_service is None:
        _rag_service = NewsRAGService()
    
    return _rag_service

def search_news(query: str, k: int = 6) -> List[EvidenceCard]:
    """Convenience function for news search"""
    return get_rag_service().search_news(query, k)

def refresh_news_embedding(news_id: int) -> bool:
    """
    Refresh embedding for a specific news article
    
    Args:
        news_id: ID of the news article
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from ..db.crud import regenerate_article_embedding, SessionLocal
        
        with SessionLocal() as db:
            return regenerate_article_embedding(db, news_id)
            
    except Exception as e:
        logger.error(f"Error refreshing embedding for news {news_id}: {e}")
        return False