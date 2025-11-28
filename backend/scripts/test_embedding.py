#!/usr/bin/env python3
"""
Test rapide du service d'embedding LlamaCpp
"""

import sys
from pathlib import Path

# Ajouter le projet au path
project_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_path))

from backend.services.ollama_embeddings import get_ollama_embedder
import numpy as np
import time


def test_embedding():
    """Teste la génération d'embeddings avec Ollama"""
    print("\n" + "="*60)
    print("TEST SERVICE D'EMBEDDING - OLLAMA")
    print("="*60)

    # Texte de test
    test_texts = [
        "Bitcoin is a decentralized digital currency",
        "Ethereum is a blockchain platform with smart contracts",
        "What is the price of BTC today?"
    ]

    print(f"\n📊 Service: http://localhost:11434")
    print(f"📊 Modèle: nomic-embed-text")
    print(f"📊 Dimension attendue: 768\n")

    # Initialiser Ollama embedder
    embedder = get_ollama_embedder(
        base_url="http://localhost:11434",
        model="nomic-embed-text"
    )

    # Tester la connexion
    if not embedder.test_connection():
        print("❌ Cannot connect to Ollama on port 11434")
        print("💡 Make sure Ollama is running: ollama serve")
        print("💡 And the model is pulled: ollama pull nomic-embed-text")
        return

    for i, text in enumerate(test_texts, 1):
        print(f"\n[{i}] Texte: {text}")
        print("    Génération de l'embedding...", end=" ", flush=True)

        try:
            start = time.time()
            embedding = embedder.embed_text(text)
            elapsed = time.time() - start

            print(f"({elapsed:.3f}s)")

            # Vérifications
            print(f"    ✅ Dimension: {embedding.shape}")
            print(f"    ✅ Type: {embedding.dtype}")
            print(f"    ✅ Norme L2: {np.linalg.norm(embedding):.4f}")
            print(f"    ✅ Non-zéros: {np.count_nonzero(embedding)}/{len(embedding)}")
            print(f"    ✅ Min/Max: {embedding.min():.4f} / {embedding.max():.4f}")

            # Vérifier que ce n'est pas un vecteur nul
            if np.count_nonzero(embedding) == 0:
                print("    ❌ ERREUR: Embedding vide (tous zéros) !")
            else:
                print("    ✅ Embedding valide")

        except Exception as e:
            print(f"    ❌ ERREUR: {e}")

    # Test de similarité
    print("\n" + "="*60)
    print("TEST SIMILARITÉ")
    print("="*60)

    try:
        emb1 = embedder.embed_text("Bitcoin cryptocurrency")
        emb2 = embedder.embed_text("BTC digital money")
        emb3 = embedder.embed_text("Pizza recipe with cheese")

        # Similarité cosinus
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

        sim_12 = cosine_sim(emb1, emb2)
        sim_13 = cosine_sim(emb1, emb3)

        print(f"\n📊 Similarité 'Bitcoin cryptocurrency' vs 'BTC digital money': {sim_12:.4f}")
        print(f"📊 Similarité 'Bitcoin cryptocurrency' vs 'Pizza recipe': {sim_13:.4f}")

        if sim_12 > sim_13:
            print("\n✅ Test réussi ! Les textes similaires ont un score plus élevé.")
        else:
            print("\n⚠️  Attention : la similarité semble inversée.")

    except Exception as e:
        print(f"\n❌ Erreur test similarité: {e}")

    print("\n" + "="*60)
    print("FIN DES TESTS")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        test_embedding()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
