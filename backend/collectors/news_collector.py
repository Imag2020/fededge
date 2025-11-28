import feedparser
import json
import re
from datetime import datetime, timedelta
from time import mktime
from ..utils.debug_logger import get_debug_logger
from ..utils.html_cleaner import clean_html_content
from ..config.paths import CONFIG_DIR
import asyncio
import concurrent.futures


async def fetch_news_articles_async(max_age_hours=48, max_concurrent=1):
    """
    Version ASYNCHRONE et PARALLÈLE de la collecte RSS.
    Chaque flux a un timeout strict et ils sont traités en parallèle LIMITÉ.

    Args:
        max_age_hours: Ne récupérer que les articles des dernières X heures
        max_concurrent: Nombre maximum de flux à traiter en parallèle (défaut: 3)
    """
    debug = get_debug_logger()

    try:
        debug.log_data_collection('RSS_FEEDS', True, f"🚀 Début collecte RSS ASYNC (max {max_age_hours}h, concurrent={max_concurrent})", None)

        config_file = CONFIG_DIR / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        feeds_config = config['news_sources']['rss_feeds']
        cutoff_date = datetime.now() - timedelta(hours=max_age_hours)

        debug.log_data_collection('RSS_FEEDS', True, f"📡 {len(feeds_config)} flux RSS en PARALLÈLE LIMITÉ (max {max_concurrent} simultanés)", {
            'total_feeds': len(feeds_config),
            'max_concurrent': max_concurrent,
            'feed_sources': [feed['name'] for feed in feeds_config],
            'cutoff_date': cutoff_date.isoformat()
        })

        # Traiter les flux par batch pour limiter le parallélisme
        all_articles = []
        for i in range(0, len(feeds_config), max_concurrent):
            batch = feeds_config[i:i + max_concurrent]

            tasks = [
                fetch_single_feed_async(feed, cutoff_date, debug)
                for feed in batch
            ]

            # Attendre le batch avec timeout de 20s
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=20.0
                )

                # Collecter les articles du batch
                for result in results:
                    if isinstance(result, list):
                        all_articles.extend(result)

            except asyncio.TimeoutError:
                debug.log_data_collection('RSS_FEEDS', False, f"⏱️ Timeout batch {i//max_concurrent + 1} (20s)", None)
                continue

        debug.log_data_collection('RSS_FEEDS', True, f"✅ Collecte terminée: {len(all_articles)} articles", {
            'total_articles': len(all_articles),
            'sources_processed': len(feeds_config)
        })

        return all_articles

    except Exception as e:
        debug.log_data_collection('RSS_FEEDS', False, f"❌ Erreur collecte RSS: {str(e)}", None)
        print(f"Erreur lors de la récupération des news: {e}")
        return []


async def fetch_single_feed_async(feed, cutoff_date, debug):
    """Fetch un seul flux RSS avec timeout strict (10s)"""
    try:
        # Exécuter feedparser.parse() dans un thread pool (car synchrone)
        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor() as pool:
            try:
                # Timeout de 10 secondes par flux
                d = await asyncio.wait_for(
                    loop.run_in_executor(pool, feedparser.parse, feed['url']),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                debug.log_data_collection('RSS_FEEDS', False, f"⏱️ TIMEOUT {feed['name']} (10s)", {
                    'feed_name': feed['name'],
                    'error': 'timeout'
                })
                return []

        articles = []
        feed_skipped = 0

        for entry in d.entries:
            try:
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                if pub_date < cutoff_date:
                    feed_skipped += 1
                    continue
            except (AttributeError, TypeError):
                pub_date = datetime.now()

            summary_content = getattr(entry, 'summary', '')
            clean_summary = clean_html_content(summary_content)
            if len(clean_summary) > 200:
                clean_summary = clean_summary[:200] + '...'

            articles.append({
                "source": feed['name'],
                "title": entry.title,
                "url": entry.link,
                "description": clean_summary,
                "published_at": pub_date
            })

        debug.log_data_collection('RSS_FEEDS', True, f"✅ {feed['name']}: {len(articles)} articles ({feed_skipped} filtrés)", {
            'feed_name': feed['name'],
            'articles_count': len(articles),
            'articles_skipped': feed_skipped
        })

        return articles

    except Exception as e:
        debug.log_data_collection('RSS_FEEDS', False, f"❌ Erreur {feed['name']}: {str(e)}", {
            'feed_name': feed['name'],
            'error': str(e)
        })
        return []


def fetch_news_articles(max_age_hours=48):
    """
    Version SYNCHRONE (wrapper) - appelle la version async.
    Gardée pour compatibilité avec le code existant.

    Args:
        max_age_hours: Ne récupérer que les articles des dernières X heures (défaut: 48h)
    """
    try:
        # Appeler la version async depuis un contexte sync
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(fetch_news_articles_async(max_age_hours))
            return result
        finally:
            loop.close()
    except Exception as e:
        print(f"Erreur lors de la récupération des news (sync wrapper): {e}")
        return []
