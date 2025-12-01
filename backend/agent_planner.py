# backend/agent_planner.py
import logging
from typing import List
from .agent_core_types import Context, Event, Plan, Action, ActionType, Topic, EventKind

logger = logging.getLogger("agents_v3")

class Planner:
    """
    Planner très simple :
    - USER MESSAGE -> mission "chat:<session_id>"
    - MISSION events -> mission indiquée dans payload["mission_id"]
    """

    def __init__(self, llm_pool, profile):
        self.llm_pool = llm_pool
        self.profile = profile

    async def plan(self, ctx: Context, event: Event) -> Plan:
        # Détermine mission_id
        if event.topic == Topic.USER and event.kind == EventKind.MESSAGE:
            mission_id = "chat_main"
            question = event.payload.get("text", "")

            # Stocker conversation_id pour KV cache (llamacpp-server)
            if event.source:
                ctx.memory.working["conversation_id"] = event.source
                logger.debug(f"[Planner] Stored conversation_id: {event.source}")

            logger.info(f"[Planner] USER MESSAGE received: {question[:100]}...")
            actions = [
                Action(ActionType.ANSWER, {"question": question})
            ]
            rationale = "user_chat_single_turn"
            return Plan(mission_id=mission_id, actions=actions, rationale=rationale)

        # Missions internes (market, world, etc.)
        mission_id = event.payload.get("mission_id", "background")
        kind = event.payload.get("kind")

        if kind == "market_tick":
            logger.info(f"[Planner] MARKET_TICK mission")
            actions = [
                Action(ActionType.UPDATE_CONSCIOUSNESS, {
                    "summary": "📊 Market prices updated",
                    "data": event.payload.get("prices", {})
                }),
            ]
            rationale = "market_tick_refresh"

        elif kind == "news_article":
            article = event.payload.get("article", {})
            logger.info(f"[Planner] NEWS_ARTICLE mission: {article.get('title', 'N/A')[:40]}...")
            actions = [
                Action(ActionType.UPDATE_CONSCIOUSNESS, {
                    "summary": f"📰 {article.get('title', 'N/A')[:80]}",
                    "data": article
                }),
            ]
            rationale = "news_processing"

        elif kind == "wallet_state":
            wallet_name = event.payload.get("wallet", "default")
            logger.info(f"[Planner] WALLET_STATE mission: {wallet_name}")
            actions = [
                Action(ActionType.UPDATE_CONSCIOUSNESS, {
                    "summary": f"💰 Wallet '{wallet_name}' state checked",
                    "data": event.payload.get("data", {})
                }),
            ]
            rationale = "wallet_update"

        elif kind == "world_state":
            logger.info(f"[Planner] WORLD_STATE mission")
            actions = [
                Action(ActionType.EXECUTE, {"tool": "get_world_state", "params": {}}),
            ]
            rationale = "world_state_refresh"

        else:
            logger.debug(f"[Planner] Unknown event kind={kind}, sleeping")
            actions = [Action(ActionType.SLEEP, {"ms": 50})]
            rationale = "no_op"

        return Plan(mission_id=mission_id, actions=actions, rationale=rationale)
