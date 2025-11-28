"""
Chat Tools V2 - Notebook dev_chat.ipynb Architecture
Simple 3-tool system: market / wallet / rag
Plain text tool calls format: <tool>market: BTC</tool>
"""

import os
import json
import re
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def _read_json_any(paths: List[str]) -> dict:
    """Read JSON from first existing path."""
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"No cache found in: {paths}")


def _fmt_num(x, digits=2):
    """Format number with thousands separator."""
    try:
        return f"{float(x):,.{digits}f}".replace(",", " ")
    except Exception:
        return str(x)


def _pct(v):
    """Format percentage with sign."""
    try:
        return f"{float(v):+.2f}%"
    except Exception:
        return "n/a"


def _upper_symbols(tokens: List[str]) -> List[str]:
    """Extract uppercase symbols from tokens."""
    out = []
    for t in tokens:
        t2 = re.sub(r"[^A-Za-z0-9]", "", t).upper()
        if t2 and (t2.isalpha() or (len(t2) >= 2 and any(c.isalpha() for c in t2))):
            out.append(t2)
    return out


# =====================================================================
# TOOL IMPLEMENTATIONS (3 only: market / wallet / rag)
# =====================================================================

def tool_market(args: Dict[str, Any]) -> str:
    """
    Get market snapshot, prices, variations.

    Args:
        query: <short text> (symbols, ids, or time frame like "24h")

    Returns:
        Plain text summary (1-3 sentences)
    """
    q = (args or {}).get("query", "") or ""
    tokens = q.strip().split()
    want_24h = any(t.lower() == "24h" for t in tokens)

    # Alias mappings (id -> ticker and ticker -> id)
    ID_TO_TICKER = {
        "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP",
        "binancecoin": "BNB", "cardano": "ADA", "polkadot": "DOT", "chainlink": "LINK",
        "litecoin": "LTC", "dogecoin": "DOGE", "tether": "USDT", "usd-coin": "USDC",
        "dai": "DAI", "wrapped-bitcoin": "WBTC", "weth": "WETH", "wrapped-steth": "WSTETH",
        "staked-ether": "STETH", "wrapped-beacon-eth": "WBETH", "wrapped-eeth": "WEETH",
        "avalanche-2": "AVAX", "aave": "AAVE", "near": "NEAR", "tron": "TRX",
        "stellar": "XLM", "monero": "XMR", "uniswap": "UNI", "pepe": "PEPE",
        "okb": "OKB", "ondo-finance": "ONDO", "story-2": "STORY", "sui": "SUI",
        "internet-computer": "ICP", "hyperliquid": "HLP", "leo-token": "LEO",
        "bitget-token": "BGB", "bittensor": "TAO", "the-open-network": "TON",
        "whitebit": "WBT", "crypto-com-chain": "CRO", "coinbase-wrapped-btc": "CBBTC",
        "ethena-usde": "USDE", "ethena-staked-usde": "SUSDE", "usds": "USDS",
        "binance-bridged-usdt-bnb-smart-chain": "USDT",
    }
    TICKER_TO_ID = {v: k for k, v in ID_TO_TICKER.items()}

    def _read_cache():
        data = _read_json_any(["data/cache_prices.json", "data/prices_cache.json"])
        if isinstance(data, dict) and "prices" in data and isinstance(data["prices"], dict):
            return data.get("timestamp"), data["prices"]
        if isinstance(data, dict):
            return None, data
        raise ValueError("Unsupported price cache format.")

    try:
        ts, prices = _read_cache()
    except Exception as e:
        logger.error(f"Price cache error: {e}")
        return "Price cache not found or invalid."

    # Resolve requested symbols to IDs
    asked = [re.sub(r"[^a-zA-Z0-9\-]", "", t).lower() for t in tokens if t.strip()]
    ids = []
    for t in asked:
        if t in prices:  # Exact id match
            ids.append(t)
        elif t.upper() in TICKER_TO_ID:
            cid = TICKER_TO_ID[t.upper()]
            if cid in prices:
                ids.append(cid)

    # Default: BTC/ETH if available
    if not ids:
        for prefer in ("bitcoin", "ethereum"):
            if prefer in prices:
                ids.append(prefer)
        if not ids:
            ids = list(prices.keys())[:2]

    lines = []
    for cid in ids:
        rec = prices.get(cid) or {}
        ticker = ID_TO_TICKER.get(cid, cid.upper())
        usd = rec.get("usd")
        ch24 = rec.get("usd_24h_change")

        if usd is None:
            lines.append(f"{ticker}: no data.")
            continue

        parts = [f"{ticker} ≈ {_fmt_num(usd, 2)} USD"]
        if ch24 is not None and (want_24h or True):
            parts.append(f"({_pct(ch24)} 24h)")
        lines.append(" ".join(parts))

    if ts and lines:
        return f"{'; '.join(lines)}. As of {ts}."
    return "; ".join(lines)[:600]


def tool_wallet(args: Dict[str, Any]) -> str:
    """
    Get wallet summary: equity, positions, P&L.

    Args:
        query: <short text> (e.g., "positions pnl", "history")

    Returns:
        Plain text summary (1-3 sentences)
    """
    q = (args or {}).get("query", "")

    try:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from db.models import SessionLocal
        from db import crud

        db = SessionLocal()
        try:
            # Get default wallet
            wallet = crud.get_wallet_by_name(db, "default")
            if not wallet:
                return "No default wallet found. Please create a wallet first."

            # Get wallet value
            wallet_value = crud.calculate_wallet_value(db, wallet.id)
            total_value = float(wallet_value.get("total_value", 0))

            # Get positions (always show for general wallet queries)
            show_positions = not q or "position" in q.lower() or "pnl" in q.lower() or "all" in q.lower() or q.lower() == "query"

            if show_positions:
                holdings = crud.get_wallet_holdings(db, wallet.id)
                if holdings:
                    # Handle both dict and SQLAlchemy object formats
                    pos_list = []
                    for h in holdings[:5]:  # Show up to 5 positions
                        if isinstance(h, dict):
                            symbol = h.get('symbol', 'Unknown')
                            qty = h.get('quantity', 0)
                        else:
                            # SQLAlchemy object - try asset relationship first
                            qty = getattr(h, 'quantity', 0)
                            if hasattr(h, 'asset') and h.asset:
                                symbol = h.asset.symbol
                            elif hasattr(h, 'asset_id'):
                                # Fallback: load asset by ID
                                asset = crud.get_asset(db, h.asset_id)
                                symbol = asset.symbol if asset else h.asset_id
                            else:
                                symbol = 'Unknown'
                        pos_list.append(f"{symbol}: {float(qty):.4f}")

                    pos_summary = ", ".join(pos_list)
                    return f"Wallet equity: ${total_value:,.2f}. Positions: {pos_summary}."
                else:
                    return f"Wallet equity: ${total_value:,.2f}. No open positions."

            return f"Wallet '{wallet.name}' equity: ${total_value:,.2f}."

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Wallet tool error: {e}", exc_info=True)
        return f"Wallet data unavailable: {str(e)}"


def tool_rag(args: Dict[str, Any]) -> str:
    """
    Search knowledge/news base.

    Args:
        query: <short text> (search query)

    Returns:
        Plain text summary (1-3 sentences)
    """
    # TEMPORARY: Disable RAG to prevent frontend blocking
    # Set ENABLE_RAG=true in environment to re-enable
    if not os.getenv("ENABLE_RAG", "false").lower() == "true":
        return "RAG search is temporarily disabled for performance. News articles are available in the dashboard."

    q = (args or {}).get("query", "")

    if not q:
        return "No query provided for RAG search."

    try:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from db.models import SessionLocal
        from db import crud

        db = SessionLocal()
        try:
            # Search news articles
            articles = crud.search_news_articles(db, query=q, limit=3)

            if not articles:
                return f"No relevant information found for '{q}'."

            # Summarize top results
            summaries = []
            for article in articles[:2]:
                title = article.title[:60]
                summaries.append(f"{title} ({article.source})")

            return f"Found {len(articles)} articles: {'; '.join(summaries)}."

        finally:
            db.close()

    except Exception as e:
        logger.error(f"RAG tool error: {e}", exc_info=True)
        return f"RAG search failed: {str(e)}"


# =====================================================================
# TOOL REGISTRY (3 tools only)
# =====================================================================

TOOL_REGISTRY = {
    "market": tool_market,
    "wallet": tool_wallet,
    "rag": tool_rag,
}


# =====================================================================
# SYSTEM PROMPT (minimal, notebook-style)
# =====================================================================

def get_system_prompt() -> str:
    """Generate minimal system prompt (optimized for 4B models)."""
    now = datetime.now()
    return f"""You are a helpful crypto assistant. Date: {now.strftime("%Y-%m-%d %H:%M")}

⚠️ ABSOLUTE RULES - NEVER BREAK THESE:
1. You do NOT know wallet balances, prices, or any data
2. You MUST use tools to get ALL data
3. NEVER invent or guess numbers
4. If you don't have data from a tool, CALL THE TOOL FIRST
5. For greetings only, respond directly

AVAILABLE TOOLS (use immediately when data needed):
<tool>wallet: query</tool> - Check wallet (ANY wallet question = use this)
<tool>market: symbols</tool> - Get crypto prices
<tool>rag: query</tool> - Search news (ONLY for news/research)

CORRECT EXAMPLES:

User: hello
Assistant: Hello! How can I help you with crypto today?

User: BTC price?
Assistant: <tool>market: BTC</tool>

User: combien de BTC dans mon wallet?
Assistant: <tool>wallet: BTC balance</tool>

User: how much BTC in my wallet?
Assistant: <tool>wallet: BTC balance</tool>

User: wallet status
Assistant: <tool>wallet: all positions</tool>

User: vérifie mon wallet
Assistant: <tool>wallet: status</tool>

❌ WRONG EXAMPLES (NEVER DO THIS):

User: combien de BTC?
Assistant: You have 5.2 BTC ❌ WRONG! Must use tool first!
Correct: <tool>wallet: BTC balance</tool> ✅

User: wallet balance?
Assistant: Your wallet has $1000 ❌ WRONG! Must use tool first!
Correct: <tool>wallet: balance</tool> ✅

RULES SUMMARY:
- Wallet question? → Use <tool>wallet: ...</tool>
- Price question? → Use <tool>market: ...</tool>
- News question? → Use <tool>rag: ...</tool>
- Greeting? → Respond directly
- Everything else? → Use appropriate tool

NEVER answer with numbers unless they come from a tool response you just received."""
