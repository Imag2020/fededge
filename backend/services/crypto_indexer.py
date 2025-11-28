"""
Crypto Knowledge Base Indexer
Indexe les sources crypto dans Qdrant avec les mêmes embeddings que le RAG news
"""

import os
import re
import io
import json
import time
import logging
import asyncio
import unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from qdrant_client.models import VectorParams, Distance, PointStruct

# Imports pour traitement des documents
try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Nos services existants
from .embeddings import get_embedder
from .crypto_sources_manager import get_crypto_sources_manager, CryptoSource
from ..utils.debug_logger import get_debug_logger

logger = logging.getLogger(__name__)

class CryptoIndexer:
    """
    Indexe les sources de base de connaissances crypto
    Utilise les mêmes embeddings que le système RAG existant
    """
    
    def __init__(self):
        self.sources_manager = get_crypto_sources_manager()
        self.debug_logger = get_debug_logger()
        self.collection_name = "base_embeddings"
        
        # Session HTTP avec retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers pour éviter les blocages
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def normalize_text(self, text: str) -> str:
        """Normalise le texte (même logique que les scripts originaux)"""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'\r+', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def chunk_text(self, text: str, chunk_chars: int = 1200, overlap: int = 150) -> List[str]:
        """Découpe le texte en chunks avec overlap"""
        text = text.strip()
        if not text:
            return []
        
        chunks = []
        n = len(text)
        i = 0
        step = max(1, chunk_chars - overlap)
        
        while i < n:
            j = min(n, i + chunk_chars)
            chunk = text[i:j]
            
            # Essayer de couper à la fin d'une phrase
            if j < n:
                sentence_end = chunk.rfind('. ')
                if sentence_end > chunk_chars // 2:
                    chunk = chunk[:sentence_end + 1]
                    j = i + sentence_end + 1
            
            chunk = chunk.strip()
            if chunk and len(chunk) > 50:  # Ignorer les chunks trop petits
                chunks.append(chunk)
            
            i += step
            
            # Éviter les boucles infinies
            if len(chunks) > 1000:
                logger.warning("Too many chunks generated, stopping")
                break
        
        return chunks
    
    def extract_text_from_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extrait le texte depuis une URL (PDF ou HTML)"""
        try:
            self.debug_logger.log_step("URL_FETCH", f"📥 Téléchargement: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                return self._extract_pdf_text(response.content, url)
            else:
                return self._extract_html_text(response.content, url)
                
        except Exception as e:
            error_msg = f"Error fetching {url}: {e}"
            logger.error(error_msg)
            self.debug_logger.log_step("URL_FETCH", f"❌ {error_msg}")
            return None, error_msg
    
    def _extract_pdf_text(self, content: bytes, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extrait le texte d'un PDF"""
        if not PdfReader:
            return None, "pypdf not available for PDF extraction"
        
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num} from {url}: {e}")
            
            if text_parts:
                full_text = '\n\n'.join(text_parts)
                normalized_text = self.normalize_text(full_text)
                self.debug_logger.log_step("PDF_EXTRACT", f"✅ PDF traité: {len(normalized_text)} caractères")
                return normalized_text, None
            else:
                return None, "No text extracted from PDF"
                
        except Exception as e:
            error_msg = f"Error processing PDF: {e}"
            logger.error(error_msg)
            return None, error_msg
    
    def _extract_html_text(self, content: bytes, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extrait le texte d'une page HTML"""
        try:
            # Essayer trafilatura d'abord (meilleur pour l'extraction de contenu)
            if trafilatura:
                text = trafilatura.extract(content, include_links=False, include_images=False)
                if text and len(text.strip()) > 100:
                    normalized_text = self.normalize_text(text)
                    self.debug_logger.log_step("HTML_EXTRACT", f"✅ HTML traité (trafilatura): {len(normalized_text)} caractères")
                    return normalized_text, None
            
            # Fallback avec BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Supprimer les scripts et styles
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()
            
            # Extraire le texte principal
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile('content|main|article'))
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            if text and len(text.strip()) > 100:
                normalized_text = self.normalize_text(text)
                self.debug_logger.log_step("HTML_EXTRACT", f"✅ HTML traité (BeautifulSoup): {len(normalized_text)} caractères")
                return normalized_text, None
            else:
                return None, "No meaningful content extracted from HTML"
                
        except Exception as e:
            error_msg = f"Error processing HTML: {e}"
            logger.error(error_msg)
            return None, error_msg
    
    async def index_source(self, source: CryptoSource) -> bool:
        """Indexe une source spécifique"""
        try:
            self.debug_logger.log_step("INDEX_SOURCE", f"🚀 Début indexation: {source.title}")
            
            # 1. Extraire le texte
            text, error = self.extract_text_from_url(source.url)
            if not text:
                self.sources_manager.mark_as_failed(source.id, error or "Failed to extract text")
                return False
            
            # 2. Découper en chunks
            chunks = self.chunk_text(text)
            if not chunks:
                self.sources_manager.mark_as_failed(source.id, "No valid chunks generated")
                return False
            
            self.debug_logger.log_step("CHUNKING", f"📝 {len(chunks)} chunks générés")
            
            # 3. Générer les embeddings (même modèle que RAG news)
            embedder = get_embedder()
            embeddings = await self._generate_embeddings_async(chunks)
            
            if not embeddings:
                self.sources_manager.mark_as_failed(source.id, "Failed to generate embeddings")
                return False
            
            # 4. Indexer dans Qdrant
            success = await self._index_in_qdrant(source, chunks, embeddings)
            
            if success:
                self.sources_manager.mark_as_indexed(source.id, len(chunks))
                self.debug_logger.log_step("INDEX_SUCCESS", f"✅ {source.title} indexé: {len(chunks)} chunks")
                return True
            else:
                self.sources_manager.mark_as_failed(source.id, "Failed to index in Qdrant")
                return False
                
        except Exception as e:
            error_msg = f"Unexpected error indexing {source.title}: {e}"
            logger.error(error_msg)
            self.sources_manager.mark_as_failed(source.id, error_msg)
            return False
    
    async def _generate_embeddings_async(self, chunks: List[str]) -> Optional[List[List[float]]]:
        """Génère les embeddings de manière asynchrone"""
        try:
            embedder = get_embedder()
            
            # Traiter par batches pour éviter la surcharge mémoire
            batch_size = 32
            all_embeddings = []
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                self.debug_logger.log_step("EMBEDDING", f"🧠 Embedding batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
                
                # Générer embeddings pour ce batch
                batch_embeddings = embedder.embed_batch(batch)
                all_embeddings.extend(batch_embeddings.tolist())
                
                # Petit délai pour éviter la surcharge
                await asyncio.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None
    
    async def _index_in_qdrant(self, source: CryptoSource, chunks: List[str], embeddings: List[List[float]]) -> bool:
        """Indexe dans Qdrant (même collection que les news mais séparée)"""
        try:
            embedder = get_embedder()
            vector_index = embedder.vector_index
            
            # Vérifier que la collection existe
            try:
                collections = vector_index.client.get_collections().collections
                collection_exists = any(c.name == self.collection_name for c in collections)
                
                if not collection_exists:
                    # Créer la collection avec les mêmes paramètres que news_embeddings  
                    vector_index.client.recreate_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    self.debug_logger.log_step("QDRANT_SETUP", f"🗄️ Collection {self.collection_name} créée")
            except Exception as e:
                logger.error(f"Error checking/creating collection: {e}")
                return False
            
            # Préparer les points pour Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Générer un ID entier unique: source_id * 10000 + chunk_index
                point_id = source.id * 10000 + i
                
                payload = {
                    "source_id": source.id,
                    "source_url": source.url,
                    "source_title": source.title,
                    "tags": ",".join(source.tags),
                    "chunk_index": i,
                    "text": chunk,
                    "indexed_at": datetime.now().isoformat()
                }
                
                points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": payload
                })
            
            # Upserter par batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                # Convertir au format PointStruct de Qdrant
                qdrant_points = [
                    PointStruct(id=point["id"], vector=point["vector"], payload=point["payload"])
                    for point in batch_points
                ]
                vector_index.client.upsert(
                    collection_name=self.collection_name,
                    points=qdrant_points
                )
                self.debug_logger.log_step("QDRANT_UPSERT", f"📤 Batch {i//batch_size + 1} uploadé")
                
                await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing in Qdrant: {e}")
            return False
    
    async def index_all_pending_sources(self) -> Dict[str, Any]:
        """Indexe toutes les sources en attente"""
        pending_sources = self.sources_manager.get_unindexed_sources()
        
        if not pending_sources:
            return {
                "success": True,
                "message": "No pending sources to index",
                "indexed_count": 0,
                "failed_count": 0,
                "results": []
            }
        
        self.debug_logger.log_step("BATCH_INDEX", f"🚀 Début indexation de {len(pending_sources)} sources")
        
        results = []
        indexed_count = 0
        failed_count = 0
        
        for source in pending_sources:
            try:
                success = await self.index_source(source)
                
                result = {
                    "source_id": source.id,
                    "source_title": source.title,
                    "source_url": source.url,
                    "success": success,
                    "chunks_count": source.chunks_count if success else 0,
                    "error": source.last_error if not success else None
                }
                
                results.append(result)
                
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {source.title}: {e}"
                logger.error(error_msg)
                results.append({
                    "source_id": source.id,
                    "source_title": source.title,
                    "source_url": source.url,
                    "success": False,
                    "chunks_count": 0,
                    "error": error_msg
                })
                failed_count += 1
            
            # Petit délai entre les sources
            await asyncio.sleep(1)
        
        self.debug_logger.log_step("BATCH_COMPLETE", f"✅ Indexation terminée: {indexed_count} réussies, {failed_count} échouées")
        
        return {
            "success": True,
            "message": f"Indexing completed: {indexed_count} successful, {failed_count} failed",
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "results": results
        }
    
    async def reindex_source(self, source_id: int) -> bool:
        """Ré-indexe une source spécifique (supprime l'ancien index)"""
        source = self.sources_manager.get_source_by_id(source_id)
        if not source:
            return False
        
        try:
            # Supprimer les anciens points de cette source
            embedder = get_embedder()
            vector_index = embedder.vector_index
            
            if vector_index.collection_exists(self.collection_name):
                # Supprimer par filtre sur source_id
                vector_index.delete_points(
                    self.collection_name,
                    points_selector={"source_id": source_id}
                )
            
            # Remettre à zéro les stats
            source.indexed = False
            source.chunks_count = 0
            source.last_error = None
            self.sources_manager.save_sources()
            
            # Ré-indexer
            return await self.index_source(source)
            
        except Exception as e:
            error_msg = f"Error reindexing source {source_id}: {e}"
            logger.error(error_msg)
            self.sources_manager.mark_as_failed(source_id, error_msg)
            return False

# Instance globale
_crypto_indexer: Optional[CryptoIndexer] = None

def get_crypto_indexer() -> CryptoIndexer:
    """Récupère l'instance globale de l'indexer"""
    global _crypto_indexer
    if _crypto_indexer is None:
        _crypto_indexer = CryptoIndexer()
    return _crypto_indexer