"""
Crypto Sources Manager - Gestion des sources de base de connaissances crypto
Gère l'indexation, la mise à jour et la recherche dans la collection base_embeddings
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CryptoSource:
    """Représente une source crypto à indexer"""
    id: int
    url: str
    title: str
    tags: List[str]
    indexed: bool = False
    indexed_at: Optional[str] = None
    chunks_count: int = 0
    last_error: Optional[str] = None
    enabled: bool = True
    error_count: int = 0
    last_error_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "tags": self.tags,
            "indexed": self.indexed,
            "indexed_at": self.indexed_at,
            "chunks_count": self.chunks_count,
            "last_error": self.last_error,
            "enabled": self.enabled,
            "error_count": self.error_count,
            "last_error_at": self.last_error_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CryptoSource':
        return cls(
            id=data["id"],
            url=data["url"],
            title=data["title"],
            tags=data.get("tags", []),
            indexed=data.get("indexed", False),
            indexed_at=data.get("indexed_at"),
            chunks_count=data.get("chunks_count", 0),
            last_error=data.get("last_error"),
            enabled=data.get("enabled", True),
            error_count=data.get("error_count", 0),
            last_error_at=data.get("last_error_at")
        )

class CryptoSourcesManager:
    """
    Gestionnaire des sources de base de connaissances crypto
    """
    
    def __init__(self, sources_file: str = "sources.json"):
        self.sources_file = Path(sources_file)
        self.sources: Dict[int, CryptoSource] = {}
        self.metadata: Dict[str, Any] = {}
        self.load_sources()
    
    def load_sources(self):
        """Charge les sources depuis le fichier JSON"""
        try:
            if not self.sources_file.exists():
                self._create_default_sources_file()
            
            with open(self.sources_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.sources = {}
            for source_data in data.get("sources", []):
                source = CryptoSource.from_dict(source_data)
                self.sources[source.id] = source
            
            self.metadata = data.get("metadata", {
                "last_updated": datetime.now().isoformat(),
                "total_sources": 0,
                "indexed_sources": 0,
                "next_id": 1,
                "collection_name": "base_embeddings"
            })
            
            logger.info(f"Loaded {len(self.sources)} crypto sources from {self.sources_file}")
            
        except Exception as e:
            logger.error(f"Error loading sources: {e}")
            self.sources = {}
            self.metadata = {
                "last_updated": datetime.now().isoformat(),
                "total_sources": 0,
                "indexed_sources": 0,
                "next_id": 1,
                "collection_name": "base_embeddings"
            }
    
    def save_sources(self):
        """Sauvegarde les sources dans le fichier JSON"""
        try:
            # Mise à jour des métadonnées
            self.metadata.update({
                "last_updated": datetime.now().isoformat(),
                "total_sources": len(self.sources),
                "indexed_sources": len([s for s in self.sources.values() if s.indexed])
            })
            
            data = {
                "sources": [source.to_dict() for source in self.sources.values()],
                "metadata": self.metadata
            }
            
            # Backup du fichier existant
            if self.sources_file.exists():
                backup_path = self.sources_file.with_suffix('.json.bak')
                self.sources_file.rename(backup_path)
            
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.sources)} sources to {self.sources_file}")
            
        except Exception as e:
            logger.error(f"Error saving sources: {e}")
            raise
    
    def get_all_sources(self) -> List[CryptoSource]:
        """Récupère toutes les sources"""
        return list(self.sources.values())
    
    def get_source_by_id(self, source_id: int) -> Optional[CryptoSource]:
        """Récupère une source par son ID"""
        return self.sources.get(source_id)
    
    def get_sources_by_tags(self, tags: List[str]) -> List[CryptoSource]:
        """Récupère les sources par tags"""
        matching_sources = []
        for source in self.sources.values():
            if any(tag in source.tags for tag in tags):
                matching_sources.append(source)
        return matching_sources
    
    def get_unindexed_sources(self) -> List[CryptoSource]:
        """Récupère les sources non indexées et activées, en évitant celles avec trop d'erreurs récentes"""
        from datetime import datetime, timedelta
        
        eligible_sources = []
        for source in self.sources.values():
            if not source.indexed and source.enabled:
                # Si la source a déjà échoué plusieurs fois, attendre avant de réessayer
                if source.error_count > 0 and source.last_error_at:
                    try:
                        last_error = datetime.fromisoformat(source.last_error_at.replace('Z', '+00:00'))
                        hours_since_error = (datetime.now() - last_error).total_seconds() / 3600
                        
                        # Délai progressif: 1h après 1ère erreur, 6h après 2ème, 24h après 3ème+
                        if source.error_count == 1 and hours_since_error < 1:
                            continue
                        elif source.error_count == 2 and hours_since_error < 6:
                            continue
                        elif source.error_count >= 3 and hours_since_error < 24:
                            continue
                    except:
                        pass  # En cas d'erreur de parsing, continuer normalement
                
                eligible_sources.append(source)
        
        return eligible_sources
    
    def get_indexed_sources(self) -> List[CryptoSource]:
        """Récupère les sources déjà indexées"""
        return [s for s in self.sources.values() if s.indexed]
    
    def add_source(self, url: str, title: str, tags: List[str], enabled: bool = True) -> CryptoSource:
        """Ajoute une nouvelle source"""
        # Vérifier si l'URL existe déjà
        for source in self.sources.values():
            if source.url == url:
                raise ValueError(f"Source with URL {url} already exists")
        
        source_id = self.metadata.get("next_id", 1)
        source = CryptoSource(
            id=source_id,
            url=url,
            title=title,
            tags=tags,
            enabled=enabled
        )
        
        self.sources[source_id] = source
        self.metadata["next_id"] = source_id + 1
        
        self.save_sources()
        return source
    
    def update_source(self, source_id: int, **kwargs) -> Optional[CryptoSource]:
        """Met à jour une source existante"""
        source = self.sources.get(source_id)
        if not source:
            return None
        
        # Mise à jour des champs autorisés
        allowed_fields = {"title", "tags", "enabled", "indexed", "indexed_at", "chunks_count", "last_error"}
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(source, field, value)
        
        self.save_sources()
        return source
    
    def delete_source(self, source_id: int) -> bool:
        """Supprime une source"""
        if source_id in self.sources:
            del self.sources[source_id]
            self.save_sources()
            return True
        return False
    
    def mark_as_indexed(self, source_id: int, chunks_count: int):
        """Marque une source comme indexée avec succès"""
        source = self.sources.get(source_id)
        if source:
            source.indexed = True
            source.indexed_at = datetime.now().isoformat()
            source.chunks_count = chunks_count
            source.last_error = None
            # Reset error tracking on successful indexing
            source.error_count = 0
            source.last_error_at = None
            self.save_sources()
    
    def mark_as_failed(self, source_id: int, error: str):
        """Marque une source comme échouée avec comptage des erreurs"""
        source = self.sources.get(source_id)
        if source:
            source.indexed = False
            source.last_error = error
            source.chunks_count = 0
            source.error_count += 1
            source.last_error_at = datetime.now().isoformat()
            
            # Désactiver automatiquement les sources avec trop d'erreurs
            if source.error_count >= 5:  # Augmenté à 5 pour être moins agressif
                logger.warning(f"Source {source.title} désactivée après {source.error_count} échecs")
                source.enabled = False
            
            self.save_sources()
    
    def reset_source_errors(self, source_id: int) -> bool:
        """Remet à zéro les erreurs d'une source et la réactive"""
        source = self.sources.get(source_id)
        if source:
            source.error_count = 0
            source.last_error = None
            source.last_error_at = None
            source.enabled = True
            self.save_sources()
            logger.info(f"Source {source.title} réactivée - erreurs remises à zéro")
            return True
        return False
    
    def get_indexing_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques d'indexation"""
        total_sources = len(self.sources)
        indexed_sources = len([s for s in self.sources.values() if s.indexed])
        enabled_sources = len([s for s in self.sources.values() if s.enabled])
        failed_sources = len([s for s in self.sources.values() if s.last_error is not None])
        
        # Statistiques par tags
        tag_stats = {}
        for source in self.sources.values():
            for tag in source.tags:
                if tag not in tag_stats:
                    tag_stats[tag] = {"total": 0, "indexed": 0}
                tag_stats[tag]["total"] += 1
                if source.indexed:
                    tag_stats[tag]["indexed"] += 1
        
        # Chunks totaux
        total_chunks = sum(s.chunks_count for s in self.sources.values())
        
        return {
            "total_sources": total_sources,
            "indexed_sources": indexed_sources,
            "enabled_sources": enabled_sources,
            "failed_sources": failed_sources,
            "pending_sources": len(self.get_unindexed_sources()),
            "indexing_progress": round(indexed_sources / max(1, enabled_sources) * 100, 2),
            "total_chunks": total_chunks,
            "tag_statistics": tag_stats,
            "collection_name": self.metadata.get("collection_name", "base_embeddings"),
            "last_updated": self.metadata.get("last_updated")
        }
    
    def _create_default_sources_file(self):
        """Crée le fichier sources.json par défaut s'il n'existe pas"""
        default_data = {
            "sources": [],
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_sources": 0,
                "indexed_sources": 0,
                "next_id": 1,
                "collection_name": "base_embeddings"
            }
        }
        
        with open(self.sources_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)

# Instance globale
_sources_manager: Optional[CryptoSourcesManager] = None

def get_crypto_sources_manager() -> CryptoSourcesManager:
    """Récupère l'instance globale du gestionnaire de sources"""
    global _sources_manager
    if _sources_manager is None:
        _sources_manager = CryptoSourcesManager()
    return _sources_manager

def reload_sources_manager():
    """Recharge le gestionnaire de sources (pour les tests)"""
    global _sources_manager
    _sources_manager = None
    return get_crypto_sources_manager()