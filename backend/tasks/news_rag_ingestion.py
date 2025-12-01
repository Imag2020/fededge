"""
News RAG Ingestion - Scrape full news articles and add to RAG system
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def ingest_news_to_rag(batch_size: int = 5):
    """
    Scrape recent news articles and add full content to RAG system

    Args:
        batch_size: Number of articles to process per run
    """
    try:
        from ..db.models import NewsArticle, RagDocument, SessionLocal
        from ..utils.url_scraper import scrape_url
        from ..utils.rag_helpers import chunk_text, get_embedding, vector_to_blob, build_bm25_index
        from ..db.models import RagChunk

        db = SessionLocal()
        try:
            # Récupérer les articles récents (derniers 7 jours) qui n'ont pas encore été scraped
            cutoff_date = datetime.now() - timedelta(days=7)

            # Trouver les articles qui n'ont pas encore de RagDocument
            recent_articles = db.query(NewsArticle).filter(
                NewsArticle.published_at >= cutoff_date
            ).order_by(NewsArticle.published_at.desc()).limit(batch_size).all()

            if not recent_articles:
                logger.info("📰 No new articles to ingest to RAG")
                return

            logger.info(f"📰 Processing {len(recent_articles)} news articles for RAG ingestion")

            success_count = 0
            fail_count = 0

            for article in recent_articles:
                # Vérifier si déjà dans RAG
                existing = db.query(RagDocument).filter(RagDocument.url == article.url).first()
                if existing:
                    logger.debug(f"Article already in RAG: {article.title[:50]}")
                    continue

                # Scraper le contenu complet
                logger.info(f"🌐 Scraping: {article.title[:60]}...")
                title, content, error = scrape_url(article.url, timeout=15)

                if error or not content:
                    logger.warning(f"Failed to scrape {article.url}: {error}")
                    fail_count += 1
                    continue

                # Vérifier que le contenu est substantiel
                if len(content) < 500:
                    logger.warning(f"Content too short for {article.url}: {len(content)} chars")
                    fail_count += 1
                    continue

                try:
                    # Créer le document RAG
                    rag_doc = RagDocument(
                        title=article.title,
                        url=article.url,
                        domain="news",
                        file_path=None,
                        downloaded_at=datetime.now()
                    )
                    db.add(rag_doc)
                    db.flush()

                    # Chunker le contenu
                    chunks = chunk_text(content, chunk_size=300, overlap=50)

                    # Créer les chunks avec embeddings
                    for idx, chunk_content in enumerate(chunks):
                        emb = get_embedding(chunk_content)

                        chunk = RagChunk(
                            doc_id=rag_doc.id,
                            content=chunk_content,
                            embedding=vector_to_blob(emb),
                            page_number=None,
                            chunk_index=idx,
                            domain="news"
                        )
                        db.add(chunk)

                    db.commit()
                    logger.info(f"✅ Added to RAG: {article.title[:50]} ({len(chunks)} chunks)")
                    success_count += 1

                except Exception as e:
                    logger.error(f"Failed to add article to RAG: {e}", exc_info=True)
                    db.rollback()
                    fail_count += 1

            # Reconstruire l'index BM25 une seule fois à la fin
            if success_count > 0:
                logger.info("🔨 Rebuilding BM25 index...")
                build_bm25_index(db)

            logger.info(f"📊 RAG ingestion complete: {success_count} success, {fail_count} failed")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in news RAG ingestion: {e}", exc_info=True)
