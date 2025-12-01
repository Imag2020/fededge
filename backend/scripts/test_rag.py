#!/usr/bin/env python3
"""
Script de test pour le système RAG
Permet d'ingérer des PDFs et de tester la recherche
"""

import sys
from pathlib import Path

# Ajouter le projet au path
project_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_path))

from backend.utils.rag_helpers import (
    ingest_pdf,
    hybrid_search,
    build_bm25_index,
    get_stats,
    get_all_domains
)
from backend.db.models import SessionLocal


def test_ingest():
    """Test d'ingestion d'un PDF"""
    print("\n" + "="*60)
    print("TEST INGESTION PDF")
    print("="*60)

    # Exemple d'ingestion
    pdf_path = "data/docs/bitcoin_whitepaper.pdf"  # Remplacer par un vrai chemin

    if not Path(pdf_path).exists():
        print(f"⚠️  PDF non trouvé: {pdf_path}")
        print("💡 Créez le dossier data/docs/ et ajoutez-y des PDFs")
        return False

    success = ingest_pdf(
        pdf_path=pdf_path,
        url="https://bitcoin.org/bitcoin.pdf",
        domain="crypto",
        title="Bitcoin: A Peer-to-Peer Electronic Cash System"
    )

    if success:
        print("✅ Ingestion réussie!")
    else:
        print("❌ Échec de l'ingestion")

    return success


def test_search():
    """Test de recherche RAG"""
    print("\n" + "="*60)
    print("TEST RECHERCHE HYBRIDE")
    print("="*60)

    # Construire l'index BM25
    print("📊 Construction de l'index BM25...")
    build_bm25_index()

    # Exemples de requêtes
    queries = [
        "What is Bitcoin?",
        "How does blockchain work?",
        "What is proof of work?",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        results = hybrid_search(query, domain="crypto", top_k=3)

        if not results:
            print("   ℹ️  Aucun résultat")
            continue

        for i, (chunk, score) in enumerate(results, 1):
            print(f"\n   [{i}] Score: {score:.4f}")
            print(f"       Doc ID: {chunk.doc_id}")
            print(f"       Chunk {chunk.chunk_index}:")
            preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            print(f"       {preview}")


def show_stats():
    """Affiche les statistiques du système RAG"""
    print("\n" + "="*60)
    print("STATISTIQUES RAG")
    print("="*60)

    stats = get_stats()

    print(f"\n📊 Documents: {stats['total_documents']}")
    print(f"📄 Chunks: {stats['total_chunks']}")
    print(f"🏷️  Domaines: {', '.join(stats['domains']) if stats['domains'] else 'Aucun'}")

    if stats['chunks_per_domain']:
        print("\n📈 Chunks par domaine:")
        for domain, count in stats['chunks_per_domain'].items():
            print(f"   - {domain}: {count} chunks")


def main():
    """Point d'entrée principal"""
    print("\n🚀 TEST SYSTÈME RAG")

    # Afficher les stats actuelles
    show_stats()

    # Menu interactif
    print("\n" + "="*60)
    print("MENU")
    print("="*60)
    print("1. Tester l'ingestion d'un PDF")
    print("2. Tester la recherche")
    print("3. Afficher les statistiques")
    print("4. Quitter")

    while True:
        choice = input("\nChoix (1-4): ").strip()

        if choice == "1":
            test_ingest()
            show_stats()

        elif choice == "2":
            test_search()

        elif choice == "3":
            show_stats()

        elif choice == "4":
            print("\n👋 Au revoir!")
            break

        else:
            print("⚠️  Choix invalide")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt du programme")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
