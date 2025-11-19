"""
Chat Tools - Real FedEdge Tools for LLM Function Calling
Provides structured tools for the chat assistant to access platform data.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =====================================================================
# TOOL IMPLEMENTATIONS - Real FedEdge Data
# =====================================================================

def tool_get_current_time(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get current date and time."""
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": "UTC" if now.tzinfo else "local"
    }


def tool_get_crypto_prices(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get real-time crypto prices from the database.

    Args:
        symbols: List of crypto symbols (e.g., ["BTC", "ETH"])
        limit: Max number of prices to return (default: 10)
    """
    symbols = args.get("symbols", [])
    limit = args.get("limit", 10)

    try:
        # Import here to avoid circular imports
        from ..db.models import SessionLocal
        from ..db import crud

        db = SessionLocal()
        try:
            # Get latest prices from database
            prices = crud.get_latest_prices(db, symbols=symbols, limit=limit)

            if not prices:
                return {"error": "No price data available", "prices": []}

            result_prices = []
            for price in prices:
                result_prices.append({
                    "symbol": price.symbol,
                    "price": float(price.current_price) if price.current_price else 0,
                    "change_24h": float(price.change_24h) if price.change_24h else 0,
                    "volume_24h": float(price.volume_24h) if price.volume_24h else 0,
                    "market_cap": float(price.market_cap) if price.market_cap else 0,
                    "last_update": price.timestamp.isoformat() if price.timestamp else None
                })

            return {"prices": result_prices, "count": len(result_prices)}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in tool_get_crypto_prices: {e}", exc_info=True)
        return {"error": f"Failed to fetch prices: {str(e)}", "prices": []}


def tool_get_wallet_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get wallet information (balance, positions, performance).

    Args:
        wallet_name: Name of the wallet (default: "default")
    """
    wallet_name = args.get("wallet_name", "default")

    try:
        from ..db.models import SessionLocal
        from ..db import crud

        db = SessionLocal()
        try:
            # Get wallet from database
            wallet = crud.get_wallet_by_name(db, wallet_name)

            if not wallet:
                return {"error": f"Wallet '{wallet_name}' not found"}

            # Get wallet positions
            positions = crud.get_wallet_positions(db, wallet.id)

            # Calculate total equity
            total_equity = float(wallet.initial_budget or 0)
            positions_data = []

            for pos in positions:
                pos_value = float(pos.quantity * (pos.current_price or 0))
                total_equity += pos_value

                positions_data.append({
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    "avg_price": float(pos.avg_price) if pos.avg_price else 0,
                    "current_price": float(pos.current_price) if pos.current_price else 0,
                    "value": pos_value,
                    "pnl": float((pos.current_price or 0) - (pos.avg_price or 0)) * float(pos.quantity)
                })

            return {
                "wallet_name": wallet.name,
                "initial_budget": float(wallet.initial_budget or 0),
                "current_equity": total_equity,
                "positions": positions_data,
                "position_count": len(positions_data)
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in tool_get_wallet_info: {e}", exc_info=True)
        return {"error": f"Failed to fetch wallet: {str(e)}"}


def tool_get_trading_signals(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get latest AI trading signals.

    Args:
        limit: Max number of signals to return (default: 5)
        signal_type: Filter by type (BUY, SELL, HOLD, ALERT)
    """
    limit = args.get("limit", 5)
    signal_type = args.get("signal_type", None)

    try:
        from ..db.models import SessionLocal
        from ..db import crud

        db = SessionLocal()
        try:
            signals = crud.get_latest_signals(db, limit=limit, signal_type=signal_type)

            if not signals:
                return {"signals": [], "count": 0}

            result_signals = []
            for sig in signals:
                result_signals.append({
                    "symbol": sig.symbol,
                    "action": sig.action,
                    "confidence": float(sig.confidence) if sig.confidence else 0,
                    "price": float(sig.price) if sig.price else 0,
                    "stop_loss": float(sig.stop_loss) if sig.stop_loss else None,
                    "take_profit": float(sig.take_profit) if sig.take_profit else None,
                    "reasoning": sig.reasoning,
                    "timestamp": sig.timestamp.isoformat() if sig.timestamp else None
                })

            return {"signals": result_signals, "count": len(result_signals)}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in tool_get_trading_signals: {e}", exc_info=True)
        return {"error": f"Failed to fetch signals: {str(e)}", "signals": []}


def tool_get_market_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get global market context (sentiment, themes, summary).
    """
    try:
        from ..db.models import SessionLocal
        from ..db import crud

        db = SessionLocal()
        try:
            world_context = crud.get_world_context(db)

            if not world_context:
                return {
                    "summary": "No market context available",
                    "sentiment_score": 0.0,
                    "key_themes": []
                }

            return {
                "summary": world_context.summary,
                "sentiment_score": float(world_context.sentiment_score) if world_context.sentiment_score else 0.0,
                "key_themes": world_context.key_events or [],
                "last_updated": world_context.timestamp.isoformat() if world_context.timestamp else None
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in tool_get_market_context: {e}", exc_info=True)
        return {"error": f"Failed to fetch market context: {str(e)}"}


def tool_search_news(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search crypto news articles (RAG-enabled).

    Args:
        query: Search query
        limit: Max number of articles (default: 5)
    """
    query = args.get("query", "")
    limit = args.get("limit", 5)

    if not query:
        return {"error": "Query is required", "articles": []}

    try:
        from ..db.models import SessionLocal
        from ..db import crud

        db = SessionLocal()
        try:
            # Search news articles in database
            articles = crud.search_news_articles(db, query=query, limit=limit)

            if not articles:
                return {"articles": [], "count": 0}

            result_articles = []
            for article in articles:
                result_articles.append({
                    "title": article.title,
                    "summary": article.summary or article.content[:200] if article.content else "",
                    "source": article.source,
                    "url": article.url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "sentiment": article.sentiment if hasattr(article, 'sentiment') else None
                })

            return {"articles": result_articles, "count": len(result_articles)}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in tool_search_news: {e}", exc_info=True)
        return {"error": f"Failed to search news: {str(e)}", "articles": []}


def tool_get_asset_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed statistics for a crypto asset.

    Args:
        symbol: Crypto symbol (e.g., "BTC", "ETH")
    """
    symbol = args.get("symbol", "")

    if not symbol:
        return {"error": "Symbol is required"}

    try:
        from ..analytics.asset_stats import asset_analyzer

        # Use the asset analyzer
        stats = asset_analyzer.analyze_asset(symbol.lower())

        if not stats:
            return {"error": f"No stats available for {symbol}"}

        return {
            "symbol": symbol,
            "price": stats.get("current_price", 0),
            "market_cap": stats.get("market_cap", 0),
            "volume_24h": stats.get("volume_24h", 0),
            "change_24h": stats.get("price_change_24h", 0),
            "volatility": stats.get("volatility", 0),
            "trend": stats.get("trend", "unknown")
        }

    except Exception as e:
        logger.error(f"Error in tool_get_asset_stats: {e}", exc_info=True)
        return {"error": f"Failed to get asset stats: {str(e)}"}


# =====================================================================
# TOOL REGISTRY
# =====================================================================

TOOL_REGISTRY: Dict[str, callable] = {
    "get_current_time": tool_get_current_time,
    "get_crypto_prices": tool_get_crypto_prices,
    "get_wallet_info": tool_get_wallet_info,
    "get_trading_signals": tool_get_trading_signals,
    "get_market_context": tool_get_market_context,
    "search_news": tool_search_news,
    "get_asset_stats": tool_get_asset_stats,
}


# =====================================================================
# TOOL DESCRIPTIONS (for system prompt)
# =====================================================================

TOOL_DESCRIPTIONS = """
Available tools (use ```tool { "name": "...", "args": {...} }``` format):

1. get_current_time - Get current date/time
   Args: {} (none)

2. get_crypto_prices - Get real-time crypto prices
   Args: {"symbols": ["BTC", "ETH"], "limit": 10}

3. get_wallet_info - Get wallet balance and positions
   Args: {"wallet_name": "default"}

4. get_trading_signals - Get latest AI trading signals
   Args: {"limit": 5, "signal_type": "BUY|SELL|HOLD|ALERT"}

5. get_market_context - Get global market sentiment and themes
   Args: {} (none)

6. search_news - Search crypto news articles
   Args: {"query": "bitcoin", "limit": 5}

7. get_asset_stats - Get detailed asset statistics
   Args: {"symbol": "BTC"}
"""


def get_system_prompt() -> str:
    """Generate system prompt with current time and tool descriptions."""
    now = datetime.now()
    return f"""You are **FedEdge Copilot**: a crypto trading assistant.

Current date/time: {now.strftime("%A, %B %d, %Y at %H:%M:%S")}

CRITICAL RULES:
1. Keep ALL responses under 2 sentences - you're a small LLM
2. When user asks for prices, news, wallet, or signals - USE A TOOL
3. NEVER guess or invent data - always use tools for facts
4. Tool protocol: output ONLY ONE fenced block per response:
   ```tool
   {{"name": "tool_name", "args": {{...}}}}
   ```
5. After receiving tool results, summarize in 1-2 sentences max

{TOOL_DESCRIPTIONS}

If uncertain without tools, say: "I need data access - please enable RAG or check specific tools."
"""
