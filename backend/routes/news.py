"""
News & Context Routes
Handles news collection, world context, and finance market endpoints
"""

from fastapi import APIRouter
import asyncio
import logging
from datetime import datetime

from ..db.models import SessionLocal, NewsArticle
from ..db import crud

# Import WebSocket manager
try:
    from ..websocket_manager_optimized import get_websocket_manager
except ImportError:
    from ..websocket_manager import get_websocket_manager

ws_manager = get_websocket_manager()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["news"])


@router.get("/world-context")
async def get_world_context():
    """Récupérer le contexte mondial actuel depuis la base de données"""
    db = SessionLocal()
    try:
        world_context = crud.get_world_context(db)

        if not world_context:
            return {
                "status": "success",
                "world_context": {
                    "world_summary": "Aucun contexte mondial disponible",
                    "sentiment_score": 0.0,
                    "key_themes": [],
                    "last_updated": None
                }
            }

        return {
            "status": "success",
            "world_context": {
                "world_summary": world_context.summary,
                "sentiment_score": float(world_context.sentiment_score) if world_context.sentiment_score is not None else 0.0,
                "key_themes": world_context.key_events or [],
                "last_updated": world_context.timestamp.isoformat() if world_context.timestamp else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/world-context/update")
async def trigger_world_context_update():
    """Déclencher manuellement la mise à jour du contexte mondial"""
    try:
        from ..tasks import analysis_tasks

        # Lancer la mise à jour en background
        asyncio.create_task(analysis_tasks.update_world_context())

        return {
            "status": "success",
            "message": "Mise à jour du contexte mondial déclenchée"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/finance-market")
async def get_finance_market():
    """Récupérer l'état complet du marché financier crypto (avec cache rapide)"""
    try:
        from ..collectors.finance_collector import get_complete_finance_analysis

        # Récupérer l'analyse avec cache prioritaire pour chargement rapide
        finance_data = get_complete_finance_analysis(use_cache=True)

        if "error" in finance_data:
            return {"status": "error", "message": finance_data["error"]}

        return {"status": "success", "finance_data": finance_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/news")
async def get_news(limit: int = 20, hours_back: int = 168):
    """Récupérer les actualités crypto récentes (default: 7 days)"""
    db = SessionLocal()
    try:
        articles = crud.get_recent_news_articles(
            db=db,
            limit=limit,
            hours_back=hours_back
        )

        # Formater les articles pour le frontend
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "id": article.id,
                "title": article.title,
                "content": article.content or "",
                "summary": article.summary or "",
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "created_at": article.created_at.isoformat() if article.created_at else None,
                "sentiment_score": article.sentiment_score,
                "relevance_score": article.relevance_score,
                "category": article.category
            })

        return {
            "success": True,
            "articles": formatted_articles,
            "count": len(formatted_articles)
        }

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {
            "success": False,
            "message": str(e),
            "articles": [],
            "count": 0
        }
    finally:
        db.close()


@router.post("/news/collect")
async def trigger_news_collection():
    """Force la collecte immédiate des actualités et diffuse au frontend"""
    print("📡 DÉBUT /api/news/collect endpoint")
    try:
        from ..tasks import analysis_tasks

        print("🔄 Collecte manuelle des news déclenchée...")

        # Lancer la collecte en arrière-plan
        asyncio.create_task(analysis_tasks.collect_and_broadcast_news())

        # Diffuser immédiatement les derniers articles déjà en base
        db = SessionLocal()
        try:
            articles = crud.get_recent_news_articles(db=db, limit=5, hours_back=48)
            print(f"📊 Trouvé {len(articles)} articles récents à diffuser")
            # Utiliser le ws_manager global au lieu d'importer
            print(f"🔌 WebSocket Manager connexions actives: {len(ws_manager.active_connections)}")

            for i, article in enumerate(articles, 1):
                article_payload = {
                    'title': article.title,
                    'source': article.source,
                    'description': article.summary or article.content[:200] if article.content else "",
                    'url': article.url,
                    'published_at': article.published_at.isoformat() if article.published_at else None,
                    'relevance_score': article.relevance_score or 0.7,
                    'sentiment_score': article.sentiment_score or 0,
                    'category': article.category or 'general',
                    'urgency_level': 'MEDIUM',
                    'is_critical': False,
                    'mentioned_assets': []
                }

                print(f"📤 Broadcasting article {i}/{len(articles)}: {article.title[:50]}")
                await ws_manager.broadcast({
                    "type": "new_article",
                    "payload": article_payload
                })
                print(f"✅ Article {i} broadcasted")

            print(f"📰 {len(articles)} articles diffusés au frontend")

            return {
                "success": True,
                "message": f"Collecte déclenchée, {len(articles)} articles diffusés",
                "articles_sent": len(articles)
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error triggering news collection: {e}")
        return {
            "success": False,
            "message": str(e),
            "articles_sent": 0
        }


@router.post("/news/broadcast-existing")
async def broadcast_existing_news():
    """Broadcast les news déjà en DB (pas de collecte, juste broadcast)"""
    import asyncio

    async def do_broadcast():
        try:
            db = SessionLocal()
            try:
                # Récupérer les dernières news de la DB
                latest_news = db.query(NewsArticle).order_by(
                    NewsArticle.published_at.desc()
                ).limit(10).all()

                if not latest_news:
                    return {
                        "success": False,
                        "message": "No news in database",
                        "count": 0
                    }

                # Préparer les news pour le frontend
                news_for_frontend = [
                    {
                        "id": art.id,
                        "title": art.title,
                        "description": art.summary or "",
                        "source": art.source,
                        "url": art.url,
                        "published_at": art.published_at.isoformat() if art.published_at else None,
                        "category": art.category,
                        "relevance_score": float(art.relevance_score) if art.relevance_score else 0.0,
                    }
                    for art in latest_news
                ]

                # Broadcast via WebSocket
                print(f"📡 Broadcasting {len(news_for_frontend)} news via WebSocket...")
                await ws_manager.broadcast({
                    "type": "news_update",
                    "payload": news_for_frontend
                })
                print(f"✅ Broadcast done!")

                return {
                    "success": True,
                    "message": f"{len(news_for_frontend)} news articles broadcast",
                    "count": len(news_for_frontend)
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error broadcasting news: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": str(e),
                "count": 0
            }

    # Lancer en arrière-plan pour ne pas bloquer
    asyncio.create_task(do_broadcast())

    # Répondre immédiatement
    return {
        "success": True,
        "message": "Broadcast started in background",
        "count": 0
    }


@router.post("/news/collect-simple")
async def trigger_simple_news_collection():
    """Collecte simple des actualités SANS analyse AI (évite crash llama.cpp)"""
    try:
        from ..collectors.news_collector import fetch_news_articles_async

        print("📡 Collecte SIMPLE des news (sans AI)...")

        # Récupérer les articles RSS (version async non-bloquante)
        articles = await fetch_news_articles_async()

        if not articles:
            return {
                "success": False,
                "message": "Aucun article récupéré",
                "articles_stored": 0
            }

        # Stocker directement sans analyse AI
        db = SessionLocal()
        stored_count = 0

        try:
            for article in articles:
                # Vérifier si l'article existe déjà (par URL)
                existing = db.query(NewsArticle).filter(
                    NewsArticle.url == article['url']
                ).first()

                if existing:
                    continue

                # Créer l'article sans analyse
                new_article = NewsArticle(
                    title=article['title'],
                    content=article['description'],
                    summary=article['description'][:200] if len(article['description']) > 200 else article['description'],
                    url=article['url'],
                    source=article['source'],
                    published_at=article['published_at'],
                    created_at=datetime.utcnow(),
                    is_processed=False,
                    is_active=True,
                    sentiment_score=0.0,  # Neutre par défaut
                    relevance_score=0.5,  # Moyen par défaut
                    category='general'
                )
                db.add(new_article)
                stored_count += 1

            db.commit()
            print(f"✅ {stored_count} nouveaux articles stockés")

            # Diffuser les articles stockés
            recent_articles = crud.get_recent_news_articles(db=db, limit=5, hours_back=48)
            for article in recent_articles:
                await ws_manager.broadcast({
                    "type": "new_article",
                    "payload": {
                        'title': article.title,
                        'source': article.source,
                        'description': article.summary or article.content[:200] if article.content else "",
                        'url': article.url,
                        'published_at': article.published_at.isoformat() if article.published_at else None,
                        'relevance_score': article.relevance_score or 0.5,
                        'sentiment_score': article.sentiment_score or 0,
                        'category': article.category or 'general'
                    }
                })

            return {
                "success": True,
                "message": f"{stored_count} articles stockés",
                "articles_stored": stored_count,
                "total_fetched": len(articles)
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in simple news collection: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e),
            "articles_stored": 0
        }
