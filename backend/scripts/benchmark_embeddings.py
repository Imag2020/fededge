#!/usr/bin/env python3
"""
Benchmark LlamaCpp vs Ollama pour les embeddings
Compare la vitesse et la qualité des deux services
"""

import sys
from pathlib import Path
import time
import numpy as np

# Ajouter le projet au path
project_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_path))

from backend.services.ollama_embeddings import get_ollama_embedder


def test_llamacpp():
    """Test LlamaCpp embeddings"""
    try:
        from backend.services.llamacpp_embeddings import get_llamacpp_embedder

        embedder = get_llamacpp_embedder(base_url="http://localhost:9002")

        # Test de connexion
        print("\n" + "="*60)
        print("TEST LLAMACPP (port 9002)")
        print("="*60)

        test_texts = [
            "Bitcoin is a decentralized digital currency",
            "Ethereum enables smart contracts",
            "What is the price of BTC?",
            "Cryptocurrency market analysis"
        ]

        timings = []
        embeddings = []

        for i, text in enumerate(test_texts, 1):
            print(f"\n[{i}/{len(test_texts)}] Testing: {text[:50]}...")

            start = time.time()
            emb = embedder.embed_text(text)
            elapsed = time.time() - start

            timings.append(elapsed)
            embeddings.append(emb)

            print(f"    ⏱️  Time: {elapsed:.3f}s")
            print(f"    📊 Dimension: {emb.shape[0]}")
            print(f"    ✅ Norm: {np.linalg.norm(emb):.4f}")

        avg_time = np.mean(timings)
        total_time = sum(timings)

        print(f"\n{'='*60}")
        print(f"LLAMACPP RESULTS:")
        print(f"  Average time: {avg_time:.3f}s per text")
        print(f"  Total time: {total_time:.3f}s for {len(test_texts)} texts")
        print(f"  Dimension: {embeddings[0].shape[0]}")
        print(f"{'='*60}")

        return {
            "service": "LlamaCpp",
            "avg_time": avg_time,
            "total_time": total_time,
            "dimension": embeddings[0].shape[0],
            "embeddings": embeddings
        }

    except Exception as e:
        print(f"❌ LlamaCpp error: {e}")
        return None


def test_ollama():
    """Test Ollama embeddings"""
    try:
        # Tester avec nomic-embed-text (768 dim)
        embedder = get_ollama_embedder(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )

        # Test de connexion
        if not embedder.test_connection():
            print("❌ Cannot connect to Ollama on port 11434")
            return None

        print("\n" + "="*60)
        print("TEST OLLAMA (port 11434, model: nomic-embed-text)")
        print("="*60)

        test_texts = [
            "Bitcoin is a decentralized digital currency",
            "Ethereum enables smart contracts",
            "What is the price of BTC?",
            "Cryptocurrency market analysis"
        ]

        timings = []
        embeddings = []

        for i, text in enumerate(test_texts, 1):
            print(f"\n[{i}/{len(test_texts)}] Testing: {text[:50]}...")

            start = time.time()
            emb = embedder.embed_text(text)
            elapsed = time.time() - start

            timings.append(elapsed)
            embeddings.append(emb)

            print(f"    ⏱️  Time: {elapsed:.3f}s")
            print(f"    📊 Dimension: {emb.shape[0]}")
            print(f"    ✅ Norm: {np.linalg.norm(emb):.4f}")

        avg_time = np.mean(timings)
        total_time = sum(timings)

        print(f"\n{'='*60}")
        print(f"OLLAMA RESULTS:")
        print(f"  Average time: {avg_time:.3f}s per text")
        print(f"  Total time: {total_time:.3f}s for {len(test_texts)} texts")
        print(f"  Dimension: {embeddings[0].shape[0]}")
        print(f"{'='*60}")

        return {
            "service": "Ollama",
            "avg_time": avg_time,
            "total_time": total_time,
            "dimension": embeddings[0].shape[0],
            "embeddings": embeddings
        }

    except Exception as e:
        print(f"❌ Ollama error: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_quality(llamacpp_result, ollama_result):
    """Compare la qualité des embeddings via similarité"""
    if not llamacpp_result or not ollama_result:
        return

    print("\n" + "="*60)
    print("QUALITY COMPARISON (Cosine Similarity)")
    print("="*60)

    llamacpp_embs = llamacpp_result['embeddings']
    ollama_embs = ollama_result['embeddings']

    # Comparer les paires
    test_pairs = [
        (0, 1, "Bitcoin vs Ethereum"),
        (0, 2, "Bitcoin vs Price question"),
        (1, 3, "Ethereum vs Market analysis")
    ]

    for idx1, idx2, desc in test_pairs:
        # LlamaCpp similarity
        llama_sim = np.dot(llamacpp_embs[idx1], llamacpp_embs[idx2])
        # Ollama similarity
        ollama_sim = np.dot(ollama_embs[idx1], ollama_embs[idx2])

        print(f"\n{desc}:")
        print(f"  LlamaCpp: {llama_sim:.4f}")
        print(f"  Ollama:   {ollama_sim:.4f}")


def main():
    """Point d'entrée principal"""
    print("\n🚀 EMBEDDING SERVICES BENCHMARK")
    print("="*60)
    print("Comparing LlamaCpp (port 9002) vs Ollama (port 11434)")
    print("="*60)

    # Test LlamaCpp
    llamacpp_result = test_llamacpp()

    # Test Ollama
    ollama_result = test_ollama()

    # Comparaison finale
    if llamacpp_result and ollama_result:
        print("\n" + "="*60)
        print("FINAL COMPARISON")
        print("="*60)

        speedup = llamacpp_result['avg_time'] / ollama_result['avg_time']

        print(f"\nSpeed:")
        print(f"  LlamaCpp: {llamacpp_result['avg_time']:.3f}s/text")
        print(f"  Ollama:   {ollama_result['avg_time']:.3f}s/text")
        print(f"  → Ollama is {speedup:.1f}x {'FASTER' if speedup > 1 else 'SLOWER'}")

        print(f"\nDimensions:")
        print(f"  LlamaCpp: {llamacpp_result['dimension']}D")
        print(f"  Ollama:   {ollama_result['dimension']}D")

        # Comparaison qualité
        compare_quality(llamacpp_result, ollama_result)

        print("\n" + "="*60)
        if speedup > 1.5:
            print(f"✅ RECOMMENDATION: Use Ollama ({speedup:.1f}x faster)")
        elif speedup > 1.0:
            print(f"⚠️  Ollama slightly faster ({speedup:.1f}x), both are viable")
        else:
            print(f"❌ LlamaCpp is faster, keep current setup")
        print("="*60)

    elif ollama_result:
        print("\n✅ Only Ollama is available")
    elif llamacpp_result:
        print("\n✅ Only LlamaCpp is available")
    else:
        print("\n❌ Both services failed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Benchmark interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
