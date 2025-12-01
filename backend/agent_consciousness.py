# backend/agent_consciousness.py
"""
Agent Consciousness Broadcasting System
Gère la mise à jour et la diffusion de l'état de conscience de l'agent
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("agents_v3")


class ConsciousnessBroadcaster:
    """Broadcast agent consciousness to frontend"""

    def __init__(self):
        self.ws_manager = None

    def set_websocket_manager(self, ws_manager):
        """Set the websocket manager"""
        self.ws_manager = ws_manager

    async def broadcast_consciousness(self, memory_snapshot):
        """
        Broadcast the agent's consciousness state to frontend

        Args:
            memory_snapshot: MemorySnapshot from agent
        """
        if not self.ws_manager:
            logger.warning("[Consciousness] WebSocket manager not set")
            return

        try:
            working = memory_snapshot.working
            conscious = memory_snapshot.conscious

            # Build global consciousness summary
            global_summary = working.get("global_summary", "")
            if not global_summary and conscious:
                global_summary = conscious.summary

            # Si toujours pas de global_summary, construire une conscience par défaut
            if not global_summary:
                # Importer ici pour éviter les imports circulaires
                from .agent_executor import build_global_consciousness
                global_summary = build_global_consciousness(working)
                # Ne pas sauvegarder ici, juste pour l'affichage

            # Get recent activities
            last_results = working.get("last_results", [])
            last_tools = working.get("last_tools", {})

            # Build consciousness payload
            consciousness_data = {
                "global_consciousness": global_summary or "Monitoring crypto markets and user activities...",
                "working_memory": self._build_working_summary(working, last_results, last_tools),
                "timestamp": time.time(),
                "cycle": working.get("stats", {}).get("total_cycles", 0),
            }

            # Broadcast to frontend (skip throttle for consciousness updates)
            await self.ws_manager.broadcast({
                "type": "agent_consciousness",
                "payload": consciousness_data
            }, skip_throttle=True)

            logger.debug(f"[Consciousness] Broadcasted: {global_summary[:100]}...")

        except Exception as e:
            logger.error(f"[Consciousness] Broadcast error: {e}", exc_info=True)

    def _build_working_summary(self, working: Dict, results: list, tools: Dict) -> str:
        """Build a concise working memory summary from recent events"""
        parts = []

        # Utiliser les last_events pour construire le working memory
        last_events = working.get("last_events", [])
        if last_events:
            # Prendre les 3 derniers événements UNIQUES (dédupliquer les résumés identiques)
            recent_events = last_events[-5:]  # Prendre 5 pour avoir de la marge
            seen_summaries = set()
            unique_events = []

            # Parcourir en ordre inverse pour garder les plus récents
            for event in reversed(recent_events):
                summary = event.get("summary", "")
                if summary:
                    # Utiliser les 50 premiers caractères comme clé d'unicité
                    summary_key = summary[:50]
                    if summary_key not in seen_summaries:
                        seen_summaries.add(summary_key)
                        unique_events.append(summary[:60])
                        if len(unique_events) >= 3:  # Max 3 événements
                            break

            # Inverser pour avoir l'ordre chronologique
            parts = list(reversed(unique_events))

        # Si pas d'événements, regarder les résultats
        if not parts and results:
            last_result = results[-1]
            result_type = last_result.get("type", "")

            if result_type == "ANSWER":
                parts.append("💬 Answered user question")
            elif result_type == "EXECUTE":
                tool_name = last_result.get("tool", "")
                if tool_name:
                    parts.append(f"🔧 Used tool: {tool_name}")
            elif result_type == "UPDATE_CONSCIOUSNESS":
                summary = last_result.get("summary", "")
                if summary:
                    parts.append(summary[:60])

        # Default
        if not parts:
            parts.append("⏸️ Idle - Ready for tasks")

        return " • ".join(parts)


# Singleton
_broadcaster_instance: Optional[ConsciousnessBroadcaster] = None


def get_consciousness_broadcaster() -> ConsciousnessBroadcaster:
    """Get or create the consciousness broadcaster singleton"""
    global _broadcaster_instance
    if _broadcaster_instance is None:
        _broadcaster_instance = ConsciousnessBroadcaster()
    return _broadcaster_instance
