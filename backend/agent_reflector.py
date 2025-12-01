# backend/agent_reflector.py
import time
import logging
from dataclasses import asdict
from typing import List, Dict, Any
from .agent_memory import ConsciousState, MemorySnapshot, MemoryStore
from .agent_core_types import Context, Plan
from .agent_consciousness import get_consciousness_broadcaster

logger = logging.getLogger("agents_v3")

def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit] + "…"

class Reflector:
    def __init__(self, llm_pool, store: MemoryStore, profile):
        self.llm_pool = llm_pool
        self.store = store
        self.profile = profile
        self._last_nonuser_ts = 0.0

    async def reflect(self, ctx: Context, plan: Plan, results: List[Dict[str, Any]]) -> None:
        logger.debug(f"[Reflector] cycle={ctx.cycle}, mission={plan.mission_id}, actions={len(plan.actions)}")

        snap: MemorySnapshot = ctx.memory
        snap.working["last_results"] = results

        # mini summary non-user
        now = time.time()
        is_user = (ctx.last_event.topic == ctx.last_event.topic.USER) if ctx.last_event else False

        summary = snap.working.get("last_summary", "")
        if self.llm_pool and not is_user and (now - self._last_nonuser_ts) > 8.0:
            logger.debug(f"[Reflector] Generating summary for non-user event")
            try:
                payload = str(results)[:800]
                prompt = (
                    "Summarize in ONE short sentence (<100 chars) what the agent just did. "
                    "If unclear, return empty.\n" + payload
                )
                s = await self.llm_pool.generate_response(prompt)
                summary = _truncate(s or "", 100)
                snap.working["last_summary"] = summary
            except Exception:
                pass
            self._last_nonuser_ts = now

        # construction état conscient minimal
        # IMPORTANT: Le ConsciousState.summary doit contenir la CONSCIENCE GLOBALE
        # (synthèse de l'environnement), pas le summary local (mémoire de travail)
        global_summary = snap.working.get("global_summary", "")

        # V2: Inclure la conscience V2 complète si disponible
        consciousness_v2 = snap.working.get("global_consciousness_v2")

        conscious = ConsciousState(
            ts=time.time(),
            context={
                "cycle": ctx.cycle,
                "mission_id": plan.mission_id,
                "stats": snap.working.get("stats", {}),
                "last_summary": summary,  # Résumé local (working memory)
                "global_consciousness": global_summary,  # Conscience globale (environnement)
                "consciousness_v2": consciousness_v2,  # Full V2 consciousness
                "consciousness_timestamp": snap.working.get("consciousness_timestamp", time.time())
            },
            vital_signals=snap.working.get("vital_signals", []),
            summary=global_summary or summary,  # Utiliser global_summary en priorité
        )
        snap.conscious = conscious

        # DoT + long_term_summary
        logger.debug(f"[Reflector] Updating DoT memory graph")
        long_term = await self.store.update_dot(
            agent_id=getattr(self.store, "agent_id", "agent"),
            ctx_cycle=ctx.cycle,
            summary=summary,
            global_summary=snap.working.get("global_summary", ""),
            vital_signals=conscious.vital_signals,
        )
        snap.working["long_term_summary"] = long_term
        logger.debug(f"[Reflector] Long-term summary updated: {long_term[:100]}..." if long_term else "[Reflector] No long-term summary")

        # enregistre un "event trace" générique
        trace_event = {
            "id": f"trace_{int(time.time()*1000)}",
            "agent_id": getattr(self.store, "agent_id", "agent"),
            "ts": time.time(),
            "topic": "trace",
            "type": "TRACE",
            "source": "reflector",
            "payload": {
                "cycle": ctx.cycle,
                "plan": {
                    "mission_id": plan.mission_id,
                    "actions": [asdict(a) for a in plan.actions],
                    "rationale": plan.rationale,
                },
                "results": results,
                "summary": summary,
            },
        }
        await self.store.append_event(trace_event)
        await self.store.save(snap)
        await self.store.save_snapshot(
            conscious,
            ctx_cycle=ctx.cycle,
            source_event_id=ctx.last_event.id if ctx.last_event else None,
        )
        logger.info(f"[Reflector] Cycle {ctx.cycle} completed and saved")

        # Broadcaster la conscience au frontend
        try:
            broadcaster = get_consciousness_broadcaster()
            await broadcaster.broadcast_consciousness(snap)
        except Exception as e:
            logger.error(f"[Reflector] Consciousness broadcast error: {e}")
