from ..websocket_manager import get_websocket_manager
from ..db.models import SessionLocal
from ..db import crud
from ..config_manager import config_manager
from ..config.paths import CONFIG_DIR
import asyncio
import json

import random
import datetime
from datetime import datetime as dt
import concurrent.futures
import sys
from contextlib import contextmanager
from typing import Optional, Dict, Any

import re
import json
import logging

# ============== SAFE LOGGING HELPER ==============

def safe_log(message, level="info"):
    """Log sécurisé qui évite les erreurs I/O operation on closed file"""
    try:
        logger = logging.getLogger("analysis_tasks")
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    except:
        pass  # Éviter les crashs de logging


def extract_json_from_markdown(text):
    # Supprimer les balises ```json et ```
    cleaned = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)
    

async def run_hourly_market_scan():
    """
    Tâche horaire pour scanner le marché et identifier des opportunités
    """
    safe_log("🔍 Scan horaire du marché en cours...")
    
    try:
        
        from ..db.models import SessionLocal
        from ..db import crud
        
        # Liste des wallets à analyser (au lieu d'actifs spécifiques)
        db = SessionLocal()
        try:
            # Récupérer le wallet par défaut pour l'analyse
            wallet = crud.get_wallet_by_name(db, "default")
            if not wallet:
                safe_log("⚠️ Aucun wallet par défaut trouvé pour le scan marché", "warning")
                return
                
            # Initialiser l'agent candidats pour le scan
            candidats_agent = OpportunitySelectionAgent()
            
            # Effectuer une analyse des opportunités
            result = candidats_agent.forward(
                wallet_id=wallet.id,
                user_strategy="balanced"
            )
            
            # Parser les résultats
            try:
                import json
                decision_json = json.loads(result.decision_json) if hasattr(result, 'decision_json') else {}
                opportunities = decision_json.get('opportunities', 'no')
                assets_to_study = decision_json.get('assets_to_study', [])
                
                if opportunities == 'yes' and assets_to_study:
                    # Calculer un score de force basé sur le nombre d'assets et la confiance
                    signal_strength = min(0.5 + (len(assets_to_study) * 0.2), 1.0)
                    
                    # Diffuser l'alerte si le signal est fort
                    if signal_strength > 0.7:
                        ws_manager = get_websocket_manager()
                        alert_payload = {
                            "type": "market_alert",
                            "payload": {
                                "asset_ticker": ", ".join(assets_to_study[:3]),  # Limiter à 3 assets
                                "alert_type": "OPPORTUNITY",
                                "strength": signal_strength,
                                "message": f"Opportunités détectées sur {len(assets_to_study)} actif(s): {', '.join(assets_to_study[:3])}",
                                "timestamp": dt.now().isoformat()
                            }
                        }
                        await ws_manager.broadcast(alert_payload)
                        safe_log(f"📢 Alerte marché diffusée pour {len(assets_to_study)} actif(s)")
                else:
                    safe_log("📊 Scan marché terminé - Aucune opportunité forte détectée")
                    
            except Exception as parse_error:
                safe_log(f"⚠️ Erreur parsing résultat scan: {parse_error}", "warning")
                
        finally:
            db.close()
                
    except Exception as e:
        safe_log(f"❌ Erreur lors du scan marché: {e}", "error")

async def update_wallet_performance():
    """
    Tâche pour mettre à jour les performances du portefeuille avec les vraies données P&L
    """
    safe_log("📊 Mise à jour du portefeuille...")
    
    try:
        from ..db.models import SessionLocal
        from ..db import crud
        # ⚠️ MIGRATION: execution_engine supprimé avec DSPy
        # from ..agent.execution_engine import broadcast_wallet_update, broadcast_wallet_performance
        from ..trading.pnl_calculator import pnl_calculator
        
        # Récupérer le wallet par défaut
        db = SessionLocal()
        try:
            wallet = crud.get_wallet_by_name(db, "default")
            if not wallet:
                safe_log("⚠️ Aucun wallet par défaut trouvé, skip performance update", "warning")
                return
            
            # D'abord diffuser l'état du wallet
            # ⚠️ MIGRATION: broadcast_wallet_update supprimé avec execution_engine
            # await broadcast_wallet_update(wallet)

            # Ensuite, calculer et diffuser les performances P&L complètes
            try:
                safe_log("📈 Calcul des performances P&L...")
                # ⚠️ MIGRATION: broadcast_wallet_performance supprimé avec execution_engine
                # await broadcast_wallet_performance(db, wallet.id)
                safe_log("⏭️  Performance P&L skip (en attente réimplémentation)")
            except Exception as pnl_error:
                safe_log(f"⚠️ Erreur calcul P&L (fallback vers valeur simple): {pnl_error}", "warning")
                # Fallback: récupérer au moins la valeur totale
                wallet_value = crud.calculate_wallet_value(db, wallet.id)
                current_value = float(wallet_value["total_value"])
                safe_log(f"📈 Wallet mis à jour (fallback) - Valeur: ${current_value:.2f}")
            
        finally:
            db.close()
        
    except Exception as e:
        safe_log(f"❌ Erreur lors de la mise à jour du portefeuille: {e}", "error")


def get_latest_cached_prices() -> Optional[Dict[str, Any]]:
    """
    Retourne immédiatement le dernier prix connu depuis les caches.
    Ordre de priorité:
    1. Cache mémoire (rate_limiter)
    2. Cache fichier persistant (rate_limiter)
    3. Cache fichier local (data/prices_cache.json)

    Returns:
        Dict de prix ou None si aucun cache disponible
    """
    import json
    from pathlib import Path
    from ..utils.rate_limiter import get_rate_limiter

    rate_limiter = get_rate_limiter()

    # 1. Essayer cache mémoire (le plus rapide)
    try:
        config_file = CONFIG_DIR / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)
        crypto_ids = config['crypto_sources']['target_cryptos']
        crypto_ids_str = ",".join(crypto_ids)

        # Récupérer cache même si expiré (pour retour immédiat)
        cached_prices = rate_limiter.get_cached_data('simple_price', ids=crypto_ids_str)
        if cached_prices:
            safe_log("✅ Prix du cache mémoire")
            return cached_prices
    except Exception as e:
        safe_log(f"⚠️ Erreur lecture cache mémoire: {e}", "warning")

    # 2. Essayer cache fichier rate_limiter
    try:
        cache_key = rate_limiter.get_cache_key('simple_price', ids=crypto_ids_str)
        cache_file = Path(rate_limiter.cache_dir) / f"{cache_key}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached_item = json.load(f)
                safe_log("✅ Prix du cache fichier rate_limiter")
                return cached_item.get('data')
    except Exception as e:
        safe_log(f"⚠️ Erreur lecture cache fichier rate_limiter: {e}", "warning")

    # 3. Essayer cache fichier local (data/prices_cache.json)
    try:
        prices_cache_file = Path("data/prices_cache.json")
        if prices_cache_file.exists():
            with open(prices_cache_file, 'r') as f:
                cached_data = json.load(f)
                safe_log("✅ Prix du cache local")
                return cached_data.get('prices')
    except Exception as e:
        safe_log(f"⚠️ Erreur lecture cache local: {e}", "warning")

    # Aucun cache disponible
    safe_log("⚠️ Aucun cache disponible", "warning")
    return None


async def trigger_price_collection_background():
    """
    Déclenche une collecte de prix en arrière-plan SEULEMENT si nécessaire.
    Vérifie d'abord si le cache est récent (< 5 min).
    """
    import time
    from pathlib import Path
    from ..utils.rate_limiter import get_rate_limiter

    rate_limiter = get_rate_limiter()

    # Vérifier âge du cache
    try:
        config_file = CONFIG_DIR / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)
        crypto_ids = config['crypto_sources']['target_cryptos']
        crypto_ids_str = ",".join(crypto_ids)

        cache_key = rate_limiter.get_cache_key('simple_price', ids=crypto_ids_str)

        # Vérifier cache mémoire
        if cache_key in rate_limiter.cache:
            cache_age = time.time() - rate_limiter.cache[cache_key]['timestamp']
            if cache_age < 300:  # 5 minutes
                safe_log(f"✅ Cache récent ({cache_age:.0f}s), skip collecte")
                return

        # Vérifier cache fichier rate_limiter
        cache_file = Path(rate_limiter.cache_dir) / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached_item = json.load(f)
                cache_age = time.time() - cached_item['timestamp']
                if cache_age < 300:  # 5 minutes
                    safe_log(f"✅ Cache fichier récent ({cache_age:.0f}s), skip collecte")
                    return

    except Exception as e:
        safe_log(f"⚠️ Erreur vérification âge cache: {e}", "warning")

    # Cache expiré ou inexistant → collecter
    safe_log("🔄 Cache expiré, déclenchement collecte en arrière-plan...")
    await collect_and_broadcast_prices()

async def collect_and_broadcast_prices():
    """
    Collecte et diffuse les prix crypto depuis l'API CoinGecko
    Enregistre les prix réels dans un fichier local pour fallback futur
    """
    # Removed print to fix I/O error in scheduler
    
    try:
        import json
        import os
        from pathlib import Path
        
        # Chemin du fichier de cache des prix (relatif au projet)
        prices_cache_file = Path("data/prices_cache.json")

        # Créer le répertoire data s'il n'existe pas
        prices_cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Fonction pour charger les prix du cache
        def load_cached_prices():
            try:
                if prices_cache_file.exists():
                    with open(prices_cache_file, 'r') as f:
                        cached_data = json.load(f)
                        # Vérifier si le cache n'est pas trop ancien (moins de 24h)
                        from datetime import datetime, timedelta
                        cache_time = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
                        if datetime.now() - cache_time < timedelta(hours=24):
                            return cached_data.get('prices', {})
            except Exception as e:
                safe_log(f"⚠️ Erreur lecture cache prix: {e}", "warning")
            return None
        
        # Fonction pour sauvegarder les prix dans le cache
        def save_prices_to_cache(prices_data):
            try:
                from datetime import datetime
                cache_data = {
                    'timestamp': datetime.now().isoformat(),
                    'prices': prices_data
                }
                with open(prices_cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                safe_log(f"💾 Prix sauvegardés dans {prices_cache_file}")
            except Exception as e:
                safe_log(f"⚠️ Erreur sauvegarde cache prix: {e}", "warning")
        
        # Importer la fonction de collecte des prix réels
        from ..collectors.price_collector import fetch_crypto_prices
        
        # Récupérer les vrais prix depuis CoinGecko
        real_prices = fetch_crypto_prices()
        
        if real_prices:
            # Utiliser les vrais prix
            prices = real_prices
            safe_log(f"💰 Prix réels récupérés: BTC ${prices.get('bitcoin', {}).get('usd', 'N/A')}")
            
            # Sauvegarder les prix réels dans le cache
            save_prices_to_cache(prices)
            
        else:
            # Tentative de fallback avec les prix du cache
            cached_prices = load_cached_prices()
            
            if cached_prices:
                prices = cached_prices
                safe_log(f"📦 Prix récupérés du cache local: BTC ${prices.get('bitcoin', {}).get('usd', 'N/A')}")
            else:
                # Dernier recours : prix simulés (mais cohérents)
                safe_log("⚠️ Aucune donnée API ou cache disponible, utilisation de prix simulés...", "warning")
                
                # Générer des prix simulés mais plus réalistes (basés sur les derniers prix connus)
                import random
                base_prices = {
                    'bitcoin': 115000,
                    'ethereum': 3500,
                    'cardano': 1.0,
                    'solana': 200,
                    'polkadot': 10
                }
                
                prices = {}
                for asset, base_price in base_prices.items():
                    # Variation de ±5% pour plus de réalisme
                    variation = random.uniform(-0.05, 0.05)
                    simulated_price = base_price * (1 + variation)
                    prices[asset] = {'usd': round(simulated_price, 4 if simulated_price < 10 else 2)}
                
                safe_log(f"🎲 Prix simulés générés: BTC ${prices.get('bitcoin', {}).get('usd', 'N/A')}")
        
        ws_manager = get_websocket_manager()
        await ws_manager.broadcast({"type": "price_update", "payload": prices})
        safe_log(f"💰 Prix diffusés: BTC ${prices.get('bitcoin', {}).get('usd', 'N/A')}")
        
    except Exception as e:
        safe_log(f"❌ Erreur lors de la collecte des prix: {e}", "error")



async def broadcast_cached_news():
    """
    Envoie immédiatement les news en cache/DB vers les WebSocket connectés.
    Utilisé au démarrage pour feedback immédiat au frontend.
    """
    from ..db.models import SessionLocal, NewsArticle

    try:
        db = SessionLocal()
        try:
            # Récupérer les 15 dernières news de la DB
            latest_news = db.query(NewsArticle).order_by(
                NewsArticle.published_at.desc()
            ).limit(15).all()

            if not latest_news:
                safe_log("ℹ️ Aucune news en cache à diffuser")
                return

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

            ws_manager = get_websocket_manager()
            await ws_manager.broadcast({
                "type": "news_update",
                "payload": news_for_frontend
            })
            safe_log(f"📢 {len(news_for_frontend)} news (depuis cache DB) diffusées au frontend")

            # Router la première news vers l'agent V3 pour mise à jour de conscience
            from ..agent_event_router import get_event_router
            router = get_event_router()
            if router and latest_news:
                first_article = latest_news[0]
                await router.route_news_event({
                    "title": first_article.title,
                    "summary": first_article.summary or "",
                    "url": first_article.url,
                    "source": first_article.source,
                    "published_at": first_article.published_at.isoformat() if first_article.published_at else None,
                    "category": first_article.category
                })
                safe_log(f"🤖 Latest news routed to Agent V3 consciousness")

        finally:
            db.close()

    except Exception as e:
        safe_log(f"❌ Erreur diffusion news cached: {e}", "error")


async def ensure_initial_news_in_db():
    """
    S'assure qu'il y a toujours des news en DB au démarrage.
    Si la DB est vide, collecte SEULEMENT 5 news rapidement.
    """
    from ..db.models import SessionLocal, NewsArticle
    from ..collectors.news_collector import fetch_news_articles_async
    from ..db import crud

    db = SessionLocal()
    try:
        count = db.query(NewsArticle).count()

        if count > 0:
            safe_log(f"✅ {count} news déjà en DB, pas besoin de bootstrap")
            return

        safe_log("🔄 DB vide, bootstrap rapide (5 news max, 1 flux)...")

        # Collecter SEULEMENT 1 flux RSS pour bootstrap rapide
        articles = await fetch_news_articles_async(max_age_hours=48, max_concurrent=1)
        if not articles:
            safe_log("⚠️ Impossible de collecter des news RSS pour bootstrap", "warning")
            return

        # Stocker directement les 5 premières news en DB (sans passer par agent)
        stored_count = 0
        for art in articles[:5]:
            title = art.get("title", "").strip()
            if not title:
                continue

            try:
                news_article = NewsArticle(
                    title=title,
                    content=art.get("content") or art.get("description") or "",
                    summary=art.get("description", "")[:500],
                    url=art.get("url", ""),
                    source=art.get("source", "unknown"),
                    published_at=art.get("published_at"),
                    category="unprocessed",  # Sera traité plus tard par agent
                    relevance_score=0.5,
                )
                db.add(news_article)
                stored_count += 1
            except Exception as e:
                safe_log(f"⚠️ Erreur stockage news: {e}", "warning")
                continue

        db.commit()
        safe_log(f"✅ {stored_count} news initiales stockées en DB (bootstrap rapide)")

    except Exception as e:
        safe_log(f"❌ Erreur bootstrap news: {e}", "error")
        db.rollback()
    finally:
        db.close()


async def collect_and_broadcast_news():
    from ..collectors.news_collector import fetch_news_articles_async
    from ..db.models import SessionLocal, NewsArticle

    safe_log("📰 Collecte brute des actualités crypto (mode ASYNC parallèle)...")

    # Utiliser la version ASYNC avec timeouts
    real_articles = await fetch_news_articles_async()
    safe_log(f"📊 Collected {len(real_articles) if real_articles else 0} RSS articles (async)")

    if not real_articles:
        safe_log("⚠️ Aucun article RSS récupéré", "warning")

        # Fallback : diffuser les dernières news de la DB même si pas de nouvelles
        try:
            db = SessionLocal()
            try:
                latest_news = db.query(NewsArticle).order_by(
                    NewsArticle.published_at.desc()
                ).limit(10).all()

                if latest_news:
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

                    ws_manager = get_websocket_manager()
                    await ws_manager.broadcast({
                        "type": "news_update",
                        "payload": news_for_frontend
                    })
                    safe_log(f"📢 {len(news_for_frontend)} news (depuis DB) diffusées au frontend")
            finally:
                db.close()
        except Exception as e:
            safe_log(f"❌ Erreur lors du fallback news DB: {e}", "error")

        return

    # Stocker en DB et diffuser au frontend
    safe_log("💾 Stockage des news en DB et diffusion...")
    try:
        db = SessionLocal()
        try:
            latest_news = db.query(NewsArticle).order_by(
                NewsArticle.published_at.desc()
            ).limit(10).all()

            if latest_news:
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

                ws_manager = get_websocket_manager()
                await ws_manager.broadcast({
                    "type": "news_update",
                    "payload": news_for_frontend
                })
                safe_log(f"📢 {len(news_for_frontend)} news diffusées immédiatement au frontend")

                # Router la première news vers l'agent V3 pour mise à jour de conscience
                from ..agent_event_router import get_event_router
                router = get_event_router()
                if router and latest_news:
                    first_article = latest_news[0]
                    await router.route_news_event({
                        "title": first_article.title,
                        "summary": first_article.summary or "",
                        "url": first_article.url,
                        "source": first_article.source,
                        "published_at": first_article.published_at.isoformat() if first_article.published_at else None,
                        "category": first_article.category
                    })
                    safe_log(f"🤖 Latest news routed to Agent V3 consciousness")

            else:
                safe_log("⚠️ Aucune news en DB à diffuser", "warning")
        finally:
            db.close()
    except Exception as e:
        safe_log(f"❌ Erreur lors du broadcast news: {e}", "error")


async def update_world_context():
    """
    Met à jour le contexte mondial en analysant les articles récents.

    Nouvelle version :
    - Récupère les articles classés "world_state" ou "immediate" sur les 7 derniers jours
    - Synthétise un résumé via llm_pool (FedEdge core model)
    - Calcule un sentiment simple
    - Sauvegarde via crud.create_or_update_world_context
    - Diffuse au frontend via WebSocket
    """
    safe_log("🌍 Mise à jour du contexte mondial (v2)...")

    from ..db.models import SessionLocal, NewsArticle
    from ..db import crud
    
    from ..llm_pool import llm_pool
    from datetime import datetime, timedelta

    try:
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            # On prend tous les articles récents (toutes catégories)
            articles = (
                db.query(NewsArticle)
                .filter(
                    NewsArticle.published_at >= cutoff_date,
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(20)
                .all()
            )

            if not articles:
                safe_log("ℹ️ Aucun article récent - pas de mise à jour du contexte")
                return

            safe_log(f"📊 {len(articles)} articles récents trouvés pour contexte mondial")

            # Construire le contexte textuel
            articles_text = "\n\n".join(
                [
                    f"- {art.title} ({art.published_at.strftime('%Y-%m-%d') if art.published_at else 'N/A'}): "
                    f"{(art.summary or art.content or '')[:280]}"
                    for art in articles
                ]
            )

            # Prompt pour le modèle principal (FedEdge core)
            prompt = f"""Analyze these recent crypto news articles and create a concise world context summary (max 200 words).
Focus on:
1. Major market trends
2. Regulatory developments
3. Key events affecting the crypto ecosystem
4. Overall market sentiment (bullish / bearish / uncertain)

Articles:
{articles_text}
"""

            # Appel LLM via llm_pool (non-streaming)
            world_summary = (await llm_pool.generate_response(prompt)).strip()

            if not world_summary:
                safe_log("⚠️ llm_pool n'a pas généré de résumé de contexte mondial", "warning")
                return

            # Sentiment simple basé sur des mots-clés anglais/fr
            sentiment_words = {
                "positive": [
                    "bullish", "rally", "surge", "growth", "adoption", "positive",
                    "hausse", "rallye", "progression", "optimisme"
                ],
                "negative": [
                    "bearish", "crash", "drop", "losses", "concerns", "negative",
                    "baisse", "chute", "inquiétudes", "crise"
                ],
            }

            text_lower = world_summary.lower()
            positive_count = sum(1 for w in sentiment_words["positive"] if w in text_lower)
            negative_count = sum(1 for w in sentiment_words["negative"] if w in text_lower)
            sentiment_score = (positive_count - negative_count) / max(
                positive_count + negative_count, 1
            )

            # Thèmes clés simples
            key_themes = ["Bitcoin", "Ethereum", "Regulation", "DeFi", "Stablecoins", "ETF"]
            mentioned_themes = [
                theme for theme in key_themes if theme.lower() in text_lower
            ][:3]

            # Sauvegarde du contexte mondial
            crud.create_or_update_world_context(
                db,
                world_summary=world_summary,
                sentiment_score=sentiment_score,
                key_themes=mentioned_themes or ["crypto"],
            )

            safe_log(
                f"✅ Contexte mondial mis à jour (v2) avec {len(articles)} articles "
                f"(sentiment: {sentiment_score:.2f}, thèmes: {mentioned_themes})"
            )

            # Diffusion frontend
            ws_manager = get_websocket_manager()
            await ws_manager.broadcast(
                {
                    "type": "world_context_updated",
                    "payload": {
                        "status": "success",
                        "summary": world_summary[:200],
                        "timestamp": datetime.utcnow().isoformat(),
                        "articles_processed": len(articles),
                        "sentiment": sentiment_score,
                        "themes": mentioned_themes,
                    },
                }
            )

        finally:
            db.close()

    except Exception as e:
        safe_log(f"❌ Erreur lors de la mise à jour du contexte mondial (v2): {e}", "error")
        import traceback
        safe_log(f"Traceback: {traceback.format_exc()}", "error")


async def update_open_trades():
    """Tâche planifiée pour mettre à jour les trades ouverts du bot de trading"""
    try:
        from ..services.trading_bot_service import get_trading_bot_service
        
        bot_service = get_trading_bot_service()
        if bot_service and bot_service.is_running and hasattr(bot_service, 'update_open_trades'):
            safe_log("🔄 Mise à jour des trades ouverts...")
            bot_service.update_open_trades()
            safe_log("✅ Trades ouverts mis à jour")
        else:
            # Fallback: appel direct à la fonction du bot si le service n'est pas disponible
            try:
                from ..bot.trading_bot_core import update_open_trades as core_update_trades
                safe_log("🔄 Mise à jour des trades ouverts (fallback)...")
                core_update_trades()
                safe_log("✅ Trades ouverts mis à jour")
            except Exception as e:
                safe_log(f"⚠️ Erreur lors de la mise à jour des trades ouverts: {e}", "warning")
                
    except Exception as e:
        safe_log(f"❌ Erreur dans la tâche update_open_trades: {e}", "error")

async def scan_trading_signals():
    """Tâche planifiée pour scanner automatiquement les signaux de trading - NON BLOQUANTE"""
    import asyncio
    from datetime import datetime
    import os
    
    # Logger spécifique pour le bot
    bot_log_path = "/home/imed/fededge/backend/bot/logs/trading_bot.log"
    
    def log_to_bot(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        # Removed print(log_msg) to fix I/O operation on closed file error
        try:
            with open(bot_log_path, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except:
            pass  # Ne pas faire échouer si erreur d'écriture
    
    def run_scan_in_background():
        """Fonction qui s'exécute en arrière-plan sans bloquer le scheduler"""
        try:
            # Import du module synchrone pour éviter les blocages LLM
            from ..bot.trading_bot_sync import scan_trading_signals_sync
            
            log_to_bot("🔍 [SCAN START] Début du scan automatique des signaux de trading...")
            
            # Utiliser la version synchrone non-bloquante
            result = scan_trading_signals_sync()
            
            if result.get('success'):
                signal_count = result.get('count', 0)
                scan_type = result.get('scan_type', 'unknown')
                
                if signal_count > 0:
                    log_to_bot(f"✅ [SCAN SUCCESS] {signal_count} nouveaux signaux détectés ({scan_type})")
                else:
                    log_to_bot(f"ℹ️ [SCAN SUCCESS] Aucun signal détecté ({scan_type})")
            else:
                error_msg = result.get('message', 'Unknown error')
                log_to_bot(f"⚠️ [SCAN ERROR] Échec du scan: {error_msg}")
                
        except Exception as e:
            log_to_bot(f"❌ [SCAN CRITICAL] Erreur critique lors du scan: {e}")
    
    try:
        # Lance le scan en arrière-plan sans attendre
        asyncio.create_task(asyncio.to_thread(run_scan_in_background))
        # Removed print to fix I/O error in scheduler

    except Exception as e:
        # Removed print to fix I/O error in scheduler
        pass