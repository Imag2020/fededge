# backend/agent_tools.py
"""
Agent V3 Tools Registry
Provides available tools for the Agent V3 executor
"""

from typing import Callable, Awaitable, Dict, Any
import asyncio
import logging

logger = logging.getLogger("agents_v3")


async def get_crypto_prices(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get current crypto prices (from API or cache fallback)"""
    from .collectors.price_collector import fetch_crypto_prices

    try:
        # fetch_crypto_prices est sync
        prices = await asyncio.to_thread(fetch_crypto_prices)

        if prices is None:
            logger.warning("[Tool] get_crypto_prices: No data available (cache empty)")
            return {
                "error": "No crypto price data available",
                "prices": {}
            }

        # Vérifier si on utilise un cache expiré (indiqué par absence de certains champs)
        is_cached = any(
            'usd_24h_change' not in data
            for data in prices.values()
            if isinstance(data, dict)
        )

        logger.info(f"[Tool] get_crypto_prices: {len(prices)} cryptos retrieved" +
                   (" (cached data)" if is_cached else ""))

        return {
            "prices": prices,
            "cached": is_cached
        }
    except Exception as e:
        logger.error(f"[Tool] get_crypto_prices failed: {e}", exc_info=True)
        return {
            "error": f"Failed to fetch crypto prices: {str(e)}",
            "prices": {}
        }


async def get_market_cap(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market cap data from crypto prices"""
    from .collectors.price_collector import fetch_crypto_prices

    try:
        prices = await asyncio.to_thread(fetch_crypto_prices)

        if prices is None:
            logger.warning("[Tool] get_market_cap: No data available")
            return {
                "error": "No market cap data available",
                "market_cap": {}
            }

        # Extraire les market caps
        market_caps = {}
        for crypto_id, data in prices.items():
            if isinstance(data, dict) and 'usd_market_cap' in data:
                market_caps[crypto_id] = {
                    'market_cap': data['usd_market_cap'],
                    'price': data.get('usd', 0)
                }

        logger.info(f"[Tool] get_market_cap: {len(market_caps)} cryptos")

        return {"market_cap": market_caps}
    except Exception as e:
        logger.error(f"[Tool] get_market_cap failed: {e}", exc_info=True)
        return {
            "error": f"Failed to fetch market cap: {str(e)}",
            "market_cap": {}
        }


async def get_world_state(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get global state (prices + news from DB)"""
    from .collectors.price_collector import fetch_crypto_prices
    from .db.models import SessionLocal
    from .db import crud

    try:
        # Récupérer les prix
        prices = await asyncio.to_thread(fetch_crypto_prices)

        # Récupérer les news récentes depuis la DB
        db = SessionLocal()
        try:
            news_articles = crud.get_recent_news_articles(db, limit=5)
            news = [
                {
                    "title": article.title,
                    "summary": article.summary or "",
                    "source": article.source or ""
                }
                for article in news_articles
            ]
        finally:
            db.close()

        logger.info(f"[Tool] get_world_state: {len(prices or {})} cryptos, {len(news)} news")

        return {
            "prices": prices or {},
            "news": news
        }
    except Exception as e:
        logger.error(f"[Tool] get_world_state failed: {e}", exc_info=True)
        return {
            "error": f"Failed to fetch world state: {str(e)}",
            "prices": {},
            "news": []
        }


async def get_wallet_state(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get wallet state"""
    wallet_name = args.get("wallet_name", "default")
    # Placeholder implementation
    return {"wallet": wallet_name, "balance": {}}


async def process_news_article(args: Dict[str, Any]) -> Dict[str, Any]:
    """Process a news article"""
    article = args.get("article", {})
    return {"processed": True, "article": article}


async def search_knowledge(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search the RAG knowledge base for relevant information.

    Args:
        query: Text query to search for
        domain: Optional domain filter (e.g., "defi", "btc", "regulation")
        top_k: Number of results to return (default: 3)

    Returns:
        Dict with search results containing relevant chunks and their sources
    """
    from .db.models import SessionLocal
    from .db import crud
    from .embeddings_pool import embeddings_pool

    query = args.get("query", "")
    domain = args.get("domain")
    top_k = int(args.get("top_k", 3))

    if not query:
        logger.warning("[Tool] search_knowledge: Empty query")
        return {
            "error": "Empty query",
            "results": []
        }

    try:
        # Générer l'embedding de la query
        query_embedding = embeddings_pool.get_embedding(query)

        # Rechercher dans la base RAG
        db = SessionLocal()
        try:
            results = crud.search_rag_chunks(
                db,
                query_embedding=query_embedding,
                domain=domain,
                top_k=top_k
            )

            # Formater les résultats
            formatted_results = []
            for chunk, similarity in results:
                # Récupérer les métadonnées du document
                doc = chunk.document
                formatted_results.append({
                    "content": chunk.content,
                    "similarity": round(similarity, 3),
                    "source": {
                        "title": doc.title if doc else "Unknown",
                        "url": doc.url if doc else None,
                        "domain": chunk.domain,
                        "page": chunk.page_number
                    }
                })

            logger.info(f"[Tool] search_knowledge: Found {len(formatted_results)} results for query='{query[:50]}...' (domain={domain})")

            return {
                "query": query,
                "domain": domain,
                "results": formatted_results
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Tool] search_knowledge failed: {e}", exc_info=True)
        return {
            "error": f"Failed to search knowledge base: {str(e)}",
            "results": []
        }


def get_tools_registry() -> Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]]:
    """
    Return the tools registry for Agent V3
    """
    return {
        "get_crypto_prices": get_crypto_prices,
        "get_market_cap": get_market_cap,
        "get_world_state": get_world_state,
        "get_wallet_state": get_wallet_state,
        "process_news_article": process_news_article,
        "search_knowledge": search_knowledge,
    }
