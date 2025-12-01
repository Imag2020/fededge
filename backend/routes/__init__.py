"""
Routes Package
Exports all API routers for the FedEdge backend

Usage in main.py:
    from routes import (
        assets_router,
        wallets_router,
        trading_router,
        news_router,
        knowledge_router,
        chat_router,
        tools_router,
        config_router,
        debug_router
    )

    app.include_router(assets_router)
    app.include_router(wallets_router)
    # ... etc
"""

from .assets import router as assets_router
from .wallets import router as wallets_router
from .trading import router as trading_router
from .news import router as news_router
from .rag import router as rag_router
from .tools import router as tools_router
from .config import router as config_router
from .debug import router as debug_router
from .registration import router as registration_router

__all__ = [
    'assets_router',
    'wallets_router',
    'trading_router',
    'news_router',
    'rag_router',
    'tools_router',
    'config_router',
    'debug_router',
    'registration_router',
]
