# backend/core_memory_store.py

import asyncio
import datetime
from typing import Dict, Any, List

from .db.models import AgentMemoryKV, AgentEvent
from .db.models import SessionLocal  # tu as probablement déjà ce SessionLocal
from .core_memory import MemorySnapshot, ConsciousState


class AgentMemoryStore:
    """
    Backend de mémoire générique basé sur AgentMemoryKV & AgentEvent.
    Remplace progressivement SQLAlchemyStore (CopilotStateKV + CopilotEvent).
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._cache = MemorySnapshot()

    async def init(self) -> None:
        # Pour l'instant rien à initialiser
        return

    async def load(self) -> MemorySnapshot:
        def _load_sync() -> MemorySnapshot:
            snap = MemorySnapshot()
            with SessionLocal() as db:
                rows = (
                    db.query(AgentMemoryKV)
                    .filter(AgentMemoryKV.agent_id == self.agent_id)
                    .all()
                )
                for row in rows:
                    if row.scope == "facts":
                        snap.facts[row.key] = row.value_json
                    elif row.scope == "working":
                        snap.working[row.key] = row.value_json
                    elif row.scope == "meta" and row.key == "conscious_state":
                        doc = row.value_json or {}
                        snap.conscious = ConsciousState(
                            ts=doc.get("ts"),
                            context=doc.get("context", {}),
                            vital_signals=doc.get("vital_signals", []),
                            summary=doc.get("summary", ""),
                        )
            return snap

        snap = await asyncio.to_thread(_load_sync)
        self._cache = snap
        return snap

    async def save(self, snapshot: MemorySnapshot) -> None:
        def _save_sync():
            with SessionLocal() as db:
                # On supprime et réécrit uniquement facts & working pour cet agent
                db.query(AgentMemoryKV).filter(
                    AgentMemoryKV.agent_id == self.agent_id,
                    AgentMemoryKV.scope.in_(["facts", "working"])
                ).delete()

                for k, v in snapshot.facts.items():
                    db.merge(AgentMemoryKV(
                        agent_id=self.agent_id,
                        scope="facts",
                        key=k,
                        value_json=v,
                    ))
                for k, v in snapshot.working.items():
                    db.merge(AgentMemoryKV(
                        agent_id=self.agent_id,
                        scope="working",
                        key=k,
                        value_json=v,
                    ))

                # Conscience dans scope="meta", key="conscious_state"
                if snapshot.conscious:
                    doc = {
                        "ts": snapshot.conscious.ts,
                        "context": snapshot.conscious.context,
                        "vital_signals": snapshot.conscious.vital_signals,
                        "summary": snapshot.conscious.summary,
                    }
                    db.merge(AgentMemoryKV(
                        agent_id=self.agent_id,
                        scope="meta",
                        key="conscious_state",
                        value_json=doc,
                    ))

                db.commit()

        await asyncio.to_thread(_save_sync)
        self._cache = snapshot

    async def append_trace(self, trace: Dict[str, Any]) -> None:
        def _append_sync():
            with SessionLocal() as db:
                evt = AgentEvent(
                    id=trace.get("id") or f"{self.agent_id}_{int(datetime.datetime.utcnow().timestamp() * 1000)}",
                    agent_id=self.agent_id,
                    ts=datetime.datetime.utcnow(),
                    topic=trace.get("topic", "trace"),
                    type=trace.get("type", "TRACE"),
                    source=trace.get("source", self.agent_id),
                    payload_json=trace,
                )
                db.merge(evt)
                db.commit()

        await asyncio.to_thread(_append_sync)
        self._cache.traces.append(trace)

    async def get_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        def _get_sync() -> List[Dict[str, Any]]:
            with SessionLocal() as db:
                events = (
                    db.query(AgentEvent)
                    .filter(
                        AgentEvent.agent_id == self.agent_id,
                        AgentEvent.topic == "trace",
                    )
                    .order_by(AgentEvent.ts.desc())
                    .limit(limit)
                    .all()
                )
                return [e.payload_json for e in events]

        return await asyncio.to_thread(_get_sync)
