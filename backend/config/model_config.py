"""
Configuration globale pour adapter les prompts selon la taille du modèle
"""

import os

# Détection automatique de la taille du modèle (ou configuration manuelle)
MODEL_SIZE = os.getenv("MODEL_SIZE", "1B")  # Options: "1B", "4B", "7B+"

# Configuration basée sur la taille
IS_SMALL_MODEL = MODEL_SIZE in ["1B", "2B"]

# ============================================================================
# PROMPTS OPTIMISÉS POUR PETITS MODÈLES (1B-2B)
# ============================================================================

if IS_SMALL_MODEL:
    # Prompts ultra-courts mais avec format tool explicite
    THINK_PROMPT = """Internal mode. One action: tool OR context OR nothing.

Tool format (JSON ONLY):
```tool
{"name": "get_market_cap", "args": {"symbol": "BTC"}}
```

Context format:
```context
{"key": "value"}
```"""

    ANSWER_PROMPT = "Answer user. Max 2 sentences."

    PLANNER_PROMPT = "Plan next step briefly."

    CRITIC_PROMPT = "Evaluate in 1 sentence."

    CONSCIOUSNESS_PROMPT = "Update context. Key info only."

    # Limites de données
    MAX_CONTEXT_LENGTH = 200  # tokens
    MAX_TOOLS_RESULTS = 2
    MAX_EVENTS = 2
    MAX_PRICES = 3
    MAX_NEWS = 2

    # Paramètres LLM
    MAX_RESPONSE_TOKENS = 50
    TEMPERATURE = 0.3

# ============================================================================
# PROMPTS STANDARDS POUR MODÈLES MOYENS (4B-7B)
# ============================================================================

else:
    # Prompts standards
    THINK_PROMPT = """You are in INTERNAL REASONING MODE.
You receive events and must decide:
- Call a tool (check if recent result exists first)
- Update context
- Do nothing
STRICT: Max 1 tool call, max 1 context update per turn."""

    ANSWER_PROMPT = """You are in USER ANSWER MODE.
Answer concisely (3-6 sentences).
Use conscious_state as source of truth.
Don't mention tools or internal memory."""

    PLANNER_PROMPT = "Your role is PLANNER. Plan the next steps."

    CRITIC_PROMPT = "Evaluate the result critically."

    CONSCIOUSNESS_PROMPT = "Update global consciousness state."

    # Limites de données
    MAX_CONTEXT_LENGTH = 1000
    MAX_TOOLS_RESULTS = 10
    MAX_EVENTS = 10
    MAX_PRICES = 20
    MAX_NEWS = 10

    # Paramètres LLM
    MAX_RESPONSE_TOKENS = 200
    TEMPERATURE = 0.7


# ============================================================================
# FONCTIONS HELPER
# ============================================================================

def truncate_string(s: str, max_length: int) -> str:
    """Tronque une chaîne à la longueur max."""
    if not s:
        return ""
    return s[:max_length] + "..." if len(s) > max_length else s


def truncate_dict(d: dict, max_items: int = None) -> dict:
    """Garde seulement les N premiers items d'un dict."""
    if not d or max_items is None:
        return d

    items = list(d.items())
    if len(items) <= max_items:
        return d

    return dict(items[:max_items])


def truncate_list(lst: list, max_items: int = None) -> list:
    """Garde seulement les N premiers items d'une liste."""
    if not lst or max_items is None:
        return lst

    return lst[:max_items]


def format_prices_minimal(prices: list) -> str:
    """Formate les prix de manière ultra-compacte."""
    if not prices:
        return "No prices"

    # Filtrer seulement les dicts valides
    valid_prices = [p for p in prices if isinstance(p, dict)]
    if not valid_prices:
        return "No prices"

    # Trier par market cap
    sorted_prices = sorted(
        valid_prices,
        key=lambda x: x.get("market_cap", 0),
        reverse=True
    )

    # Prendre les top N
    top = sorted_prices[:MAX_PRICES]

    # Format compact: BTC:$104k(+2.5%)
    formatted = []
    for p in top:
        symbol = p.get("symbol", "?")
        price = p.get("price", 0)
        change = p.get("change_24h", 0)

        # Formater le prix
        if price >= 1000:
            price_str = f"${price/1000:.1f}k"
        elif price >= 1:
            price_str = f"${price:.2f}"
        else:
            price_str = f"${price:.4f}"

        # Formater le changement
        sign = "+" if change >= 0 else ""
        change_str = f"{sign}{change:.1f}%"

        formatted.append(f"{symbol}:{price_str}({change_str})")

    return ", ".join(formatted)


def format_wallet_minimal(wallet: dict) -> str:
    """Formate le wallet de manière ultra-compacte."""
    if not wallet or not isinstance(wallet, dict):
        return "No wallet"

    balance = wallet.get("balance", 0)
    pnl = wallet.get("pnl", 0)

    # Sécuriser les conversions
    try:
        balance = float(balance) if balance else 0
        pnl = float(pnl) if pnl else 0
        pnl_sign = "+" if pnl >= 0 else ""
        return f"Balance: ${balance:.2f}, PnL: {pnl_sign}{pnl:.2f}%"
    except (ValueError, TypeError):
        return "No wallet"


def format_news_minimal(news: list) -> str:
    """Formate les news de manière ultra-compacte."""
    if not news:
        return "No news"

    # Filtrer seulement les dicts valides
    valid_news = [n for n in news if isinstance(n, dict)]
    if not valid_news:
        return "No news"

    # Prendre les N plus récentes
    recent = valid_news[:MAX_NEWS]

    # Format compact: [BTC] Title (source)
    formatted = []
    for n in recent:
        symbol = n.get("symbol", "CRYPTO")
        title = n.get("title", "")
        source = n.get("source", "")

        # Tronquer le titre
        title_short = title[:50] + "..." if len(title) > 50 else title

        formatted.append(f"[{symbol}] {title_short}")

    return " | ".join(formatted)


def build_compact_context(
    last_summary: str = "",
    last_tools: dict = None,
    prices: list = None,
    wallet: dict = None,
    news: list = None
) -> str:
    """Construit un contexte compact pour petits modèles."""

    if not IS_SMALL_MODEL:
        # Pour les gros modèles, retourner tout
        return {
            "summary": last_summary or "",
            "tools": last_tools if isinstance(last_tools, dict) else {},
            "prices": prices if isinstance(prices, list) else [],
            "wallet": wallet if isinstance(wallet, dict) else {},
            "news": news if isinstance(news, list) else []
        }

    # Pour petits modèles : ultra-compact
    parts = []

    # Résumé (max 30 mots)
    if last_summary and isinstance(last_summary, str):
        words = last_summary.split()[:30]
        summary_short = " ".join(words)
        if summary_short:
            parts.append(f"Summary: {summary_short}")

    # Outils (2 derniers seulement)
    if last_tools and isinstance(last_tools, dict):
        tools_truncated = truncate_dict(last_tools, MAX_TOOLS_RESULTS)
        if tools_truncated:
            parts.append(f"Tools: {tools_truncated}")

    # Prix (format minimal)
    if prices and isinstance(prices, list):
        prices_str = format_prices_minimal(prices)
        if prices_str and prices_str != "No prices":
            parts.append(prices_str)

    # Wallet (format minimal)
    if wallet and isinstance(wallet, dict):
        wallet_str = format_wallet_minimal(wallet)
        if wallet_str and wallet_str != "No wallet":
            parts.append(wallet_str)

    # News (format minimal)
    if news and isinstance(news, list):
        news_str = format_news_minimal(news)
        if news_str and news_str != "No news":
            parts.append(f"News: {news_str}")

    # Joindre avec séparateur compact
    if not parts:
        return "No context"

    result = " | ".join(parts)

    # Limiter la longueur totale
    max_chars = MAX_CONTEXT_LENGTH * 4  # Approximation: 1 token ≈ 4 chars
    if len(result) > max_chars:
        result = result[:max_chars] + "..."

    return result


# ============================================================================
# INFO
# ============================================================================

def get_config_info() -> str:
    """Retourne les infos de configuration."""
    return f"""
Model Configuration:
- Size: {MODEL_SIZE}
- Small model mode: {IS_SMALL_MODEL}
- Max context: {MAX_CONTEXT_LENGTH} tokens
- Max response: {MAX_RESPONSE_TOKENS} tokens
- Max prices: {MAX_PRICES}
- Max news: {MAX_NEWS}
- Temperature: {TEMPERATURE}
"""


if __name__ == "__main__":
    print(get_config_info())
