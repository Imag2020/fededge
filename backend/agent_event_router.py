# backend/agent_event_router.py
"""
Event Router for Agent V3
Routes all system events (news, prices, wallets) to the agent for consciousness updates
"""

import logging
from typing import Dict, Any, Optional
from .agent_core_types import EventKind, Topic

logger = logging.getLogger("agents_v3")


class AgentEventRouter:
    """Routes events to the agent V3 runtime"""

    def __init__(self, agent_runtime):
        self.runtime = agent_runtime

    async def route_news_event(self, news_article: Dict[str, Any]):
        """
        Route a news article to the agent for processing

        Args:
            news_article: Dict with keys: title, summary, url, source, published_at, category
        """
        try:
            logger.info(f"[EventRouter] Routing NEWS event: {news_article.get('title', 'N/A')[:60]}...")

            await self.runtime.post_event(
                kind=EventKind.MISSION_UPDATE,
                topic=Topic.SYSTEM,
                payload={
                    "mission_id": "news_processing",
                    "kind": "news_article",
                    "article": news_article
                },
                source="news_collector"
            )

            logger.debug(f"[EventRouter] News event routed successfully")

        except Exception as e:
            logger.error(f"[EventRouter] Error routing news event: {e}", exc_info=True)

    async def route_market_update(self, market_data: Dict[str, Any]):
        """
        Route market price update to the agent

        Args:
            market_data: Dict with crypto prices
        """
        try:
            logger.info(f"[EventRouter] Routing MARKET update event")

            await self.runtime.post_event(
                kind=EventKind.MISSION_UPDATE,
                topic=Topic.SYSTEM,
                payload={
                    "mission_id": "market_update",
                    "kind": "market_tick",
                    "prices": market_data
                },
                source="market_data"
            )

            logger.debug(f"[EventRouter] Market event routed successfully")

        except Exception as e:
            logger.error(f"[EventRouter] Error routing market event: {e}", exc_info=True)

    async def route_wallet_event(self, wallet_name: str, wallet_data: Dict[str, Any]):
        """
        Route wallet update to the agent

        Args:
            wallet_name: Name of the wallet
            wallet_data: Wallet state data
        """
        try:
            logger.info(f"[EventRouter] Routing WALLET event: {wallet_name}")

            await self.runtime.post_event(
                kind=EventKind.MISSION_UPDATE,
                topic=Topic.SYSTEM,
                payload={
                    "mission_id": "wallet_update",
                    "kind": "wallet_state",
                    "wallet": wallet_name,
                    "data": wallet_data
                },
                source="wallet_monitor"
            )

            logger.debug(f"[EventRouter] Wallet event routed successfully")

        except Exception as e:
            logger.error(f"[EventRouter] Error routing wallet event: {e}", exc_info=True)


# Singleton
_router_instance: Optional[AgentEventRouter] = None


def init_event_router(agent_runtime):
    """Initialize the event router with the agent runtime"""
    global _router_instance
    _router_instance = AgentEventRouter(agent_runtime)
    logger.info("[EventRouter] Initialized")
    return _router_instance


def get_event_router() -> Optional[AgentEventRouter]:
    """Get the event router instance"""
    return _router_instance
