"""
Ollama Embeddings Service
Alternative plus rapide à LlamaCpp pour les embeddings
"""

import requests
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """Service d'embeddings via Ollama API"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        """
        Initialize Ollama embedder

        Args:
            base_url: URL de base d'Ollama (défaut: http://localhost:11434)
            model: Nom du modèle d'embedding (défaut: nomic-embed-text)
                   Autres options: mxbai-embed-large, all-minilm
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.embed_url = f"{self.base_url}/api/embed"

    def embed_text(self, text: str) -> np.ndarray:
        """
        Génère un embedding pour un texte

        Args:
            text: Texte à embedder

        Returns:
            Vecteur numpy (dimension dépend du modèle)
        """
        try:
            payload = {
                "model": self.model,
                "input": text
            }

            response = requests.post(
                self.embed_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            # Ollama retourne 'embeddings' (pluriel, array de vecteurs)
            # On prend le premier vecteur
            if 'embeddings' in data and len(data['embeddings']) > 0:
                embedding = np.array(data['embeddings'][0], dtype=np.float32)
            elif 'embedding' in data:
                embedding = np.array(data['embedding'], dtype=np.float32)
            else:
                raise ValueError(f"No embedding in response: {data}")

            # Normaliser L2 (vecteur unitaire)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise

    def test_connection(self) -> bool:
        """Test la connexion à Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except:
            return False


# Instance globale
_ollama_embedder = None


def get_ollama_embedder(base_url: str = "http://localhost:11434", model: str = "nomic-embed-text") -> OllamaEmbedder:
    """
    Retourne l'instance globale d'OllamaEmbedder

    Args:
        base_url: URL Ollama
        model: Modèle d'embedding à utiliser

    Returns:
        Instance d'OllamaEmbedder
    """
    global _ollama_embedder
    if _ollama_embedder is None:
        _ollama_embedder = OllamaEmbedder(base_url, model)
    return _ollama_embedder
