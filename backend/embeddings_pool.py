# backend/embeddings_pool.py

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict

import numpy as np
import requests

logger = logging.getLogger(__name__)

# Import config_manager for loading embeddings config
from .config_manager import config_manager, EmbeddingConfig as ConfigEmbeddingConfig


class EmbeddingClient:
    """
    Client pour serveur d'embeddings.

    Conforme à l'API OpenAI embeddings:
      POST http://localhost:9002/v1/embeddings
      {
        "model": "embeddinggemma",
        "input": "Instruct: ... Input: <text>"
      }
    """

    def __init__(self, cfg: ConfigEmbeddingConfig):
        self.cfg = cfg
        self.endpoint = self.cfg.url.rstrip("/") + "/embeddings"

    def embed(self, text: str) -> np.ndarray:
        try:
            payload = {
                "model": self.cfg.model,
                "input": (
                    "Instruct: Représente ce texte pour recherche sémantique.\n"
                    f"Input: {text}"
                ),
            }

            resp = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.cfg.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # Deux formats possibles :
            # 1) Ancien format: { "embedding": [...] }
            # 2) Format OpenAI: { "data": [ { "embedding": [...] } ] }
            emb = None
            if "embedding" in data:
                emb = data["embedding"]
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                emb = data["data"][0].get("embedding")

            if emb is None:
                raise ValueError(f"No embedding field in response: {data}")

            return np.array(emb, dtype=np.float32)

        except Exception as e:
            logger.error(f"[EmbeddingClient] Embedding error: {e}", exc_info=True)
            # Fallback: vecteur nul pour ne pas casser le pipeline
            return np.zeros(self.cfg.dimension, dtype=np.float32)


class EmbeddingsPool:
    """
    Pool de clients d'embeddings chargés depuis la configuration JSON.
    Permet de gérer plusieurs modèles d'embeddings et de les sélectionner par ID.
    """

    def __init__(self):
        self.clients: Dict[str, EmbeddingClient] = {}
        self.default_client_id: Optional[str] = None
        self.load_clients()

    def load_clients(self):
        """Charge tous les clients d'embeddings depuis config_manager"""
        logger.info("[EmbeddingsPool] Loading embedding configurations from config_manager...")

        # Récupérer toutes les configs d'embeddings
        embeddings = config_manager.get_all_embeddings()

        if not embeddings:
            # Fallback : créer un client depuis les variables d'environnement
            logger.warning("[EmbeddingsPool] No embeddings in config, using environment variables")
            base_url = os.getenv("EMBEDDINGS_BASE_URL", "http://localhost:9002/v1")
            model = os.getenv("RAG_EMBEDDING_MODEL", "embeddinggemma")
            dim = int(os.getenv("RAG_EMBEDDING_DIM", "768"))

            from .config_manager import EmbeddingConfig, EmbeddingType
            fallback_cfg = EmbeddingConfig(
                id="default_embedding",
                name="default-embedding",
                type=EmbeddingType.OPENAI_COMPATIBLE,
                url=base_url,
                model=model,
                dimension=dim,
                is_default=True,
                is_active=True
            )
            config_manager.add_embedding(fallback_cfg)
            embeddings = [fallback_cfg]

        # Créer un client pour chaque embedding actif
        for emb_cfg in embeddings:
            if emb_cfg.is_active:
                try:
                    client = EmbeddingClient(emb_cfg)
                    self.clients[emb_cfg.id] = client
                    logger.info(f"[EmbeddingsPool] Loaded {emb_cfg.name} (ID: {emb_cfg.id})")

                    if emb_cfg.is_default:
                        self.default_client_id = emb_cfg.id
                        logger.info(f"[EmbeddingsPool] Default embedding: {emb_cfg.name}")
                except Exception as e:
                    logger.error(f"[EmbeddingsPool] Failed to load {emb_cfg.name}: {e}")

        # Si aucun client par défaut, prendre le premier disponible
        if not self.default_client_id and self.clients:
            self.default_client_id = list(self.clients.keys())[0]
            logger.info(f"[EmbeddingsPool] Using first client as default: {self.default_client_id}")

        logger.info(f"[EmbeddingsPool] Loaded {len(self.clients)} embedding client(s)")

    def reload_clients(self):
        """Recharge tous les clients depuis config_manager"""
        logger.info("[EmbeddingsPool] Reloading embedding clients...")
        self.clients.clear()
        self.default_client_id = None
        self.load_clients()

    def get_client(self, client_id: Optional[str] = None) -> EmbeddingClient:
        """Récupère un client d'embedding par ID, ou le client par défaut"""
        if client_id is None:
            client_id = self.default_client_id

        if client_id not in self.clients:
            logger.warning(f"[EmbeddingsPool] Client {client_id} not found, using default")
            client_id = self.default_client_id

        if client_id is None or client_id not in self.clients:
            raise ValueError("[EmbeddingsPool] No embedding clients available")

        return self.clients[client_id]

    def get_embedding(self, text: str, client_id: Optional[str] = None) -> np.ndarray:
        """Génère un embedding pour le texte donné"""
        return self.get_client(client_id).embed(text)

    def get_available_clients(self) -> Dict[str, str]:
        """Retourne un dictionnaire {id: name} des clients disponibles"""
        return {
            client_id: self.clients[client_id].cfg.name
            for client_id in self.clients
        }


# Instance globale
embeddings_pool = EmbeddingsPool()
