# backend/agent_memory.py
import asyncio
import time
import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .db.models import SessionLocal
from .agent_models import AgentMemoryKV, AgentEvent, AgentSnapshot
from .dot_memory import DoTGraph
from .db.crud import get_dot_memory, save_dot_memory


@dataclass
class ConsciousState:
    ts: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    vital_signals: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


@dataclass
class MemorySnapshot:
    facts: Dict[str, Any] = field(default_factory=dict)
    working: Dict[str, Any] = field(default_factory=dict)
    conscious: Optional[ConsciousState] = None


class MemoryStore:
    async def init(self): ...
    async def load(self) -> MemorySnapshot: ...
    async def save(self, snapshot: MemorySnapshot) -> None: ...
    async def append_event(self, event_doc: Dict[str, Any]) -> None: ...
    async def save_snapshot(self, conscious: ConsciousState, ctx_cycle: int, source_event_id: Optional[str]): ...
    async def update_dot(self, agent_id: str, ctx_cycle: int, summary: str, global_summary: str,
                         vital_signals: List[Dict[str, Any]]) -> str: ...


class SQLAgentMemoryStore(MemoryStore):
    FACTS_KEY = "__root__"
    WORKING_KEY = "__root__"

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._cache = MemorySnapshot()

    async def init(self):
        # rien de spécial pour l'instant
        return

    async def load(self) -> MemorySnapshot:
        def _load_sync() -> MemorySnapshot:
            snap = MemorySnapshot()
            with SessionLocal() as db:
                facts_row = (
                    db.query(AgentMemoryKV)
                    .filter_by(agent_id=self.agent_id, scope="facts", key=self.FACTS_KEY)
                    .one_or_none()
                )
                working_row = (
                    db.query(AgentMemoryKV)
                    .filter_by(agent_id=self.agent_id, scope="working", key=self.WORKING_KEY)
                    .one_or_none()
                )

                snap.facts = dict(facts_row.value_json) if facts_row and facts_row.value_json else {}
                snap.working = dict(working_row.value_json) if working_row and working_row.value_json else {}
            return snap

        snap = await asyncio.to_thread(_load_sync)
        self._cache = snap
        return snap

    async def save(self, snapshot: MemorySnapshot) -> None:
        def _save_sync():
            with SessionLocal() as db:
                for scope, key, value in (
                    ("facts", self.FACTS_KEY, snapshot.facts),
                    ("working", self.WORKING_KEY, snapshot.working),
                ):
                    row = (
                        db.query(AgentMemoryKV)
                        .filter_by(agent_id=self.agent_id, scope=scope, key=key)
                        .one_or_none()
                    )
                    if row is None:
                        row = AgentMemoryKV(
                            agent_id=self.agent_id,
                            scope=scope,
                            key=key,
                            value_json=value,
                        )
                        db.add(row)
                    else:
                        row.value_json = value
                        row.updated_at = datetime.datetime.utcnow()
                db.commit()
        await asyncio.to_thread(_save_sync)
        self._cache = snapshot

    async def append_event(self, event_doc: Dict[str, Any]) -> None:
        def _sync():
            with SessionLocal() as db:
                obj = AgentEvent(
                    id=event_doc["id"],
                    agent_id=self.agent_id,
                    ts=datetime.datetime.utcfromtimestamp(event_doc["ts"]),
                    topic=event_doc["topic"],
                    kind=event_doc["type"],
                    source=event_doc.get("source", ""),
                    payload_json=event_doc.get("payload", {}),
                )
                db.add(obj)
                db.commit()
        await asyncio.to_thread(_sync)

    async def save_snapshot(self, conscious: ConsciousState, ctx_cycle: int, source_event_id: Optional[str]):
        doc = {
            "ts": conscious.ts,
            "context": conscious.context,
            "vital_signals": conscious.vital_signals,
            "summary": conscious.summary,
            "cycle": ctx_cycle,
        }

        def _sync():
            with SessionLocal() as db:
                obj = AgentSnapshot(
                    agent_id=self.agent_id,
                    ts=datetime.datetime.utcfromtimestamp(conscious.ts),
                    snapshot_json=doc,
                    summary_text=conscious.summary,
                    source_event_id=source_event_id,
                )
                db.add(obj)
                db.commit()
        await asyncio.to_thread(_sync)

    async def update_dot(
        self,
        agent_id: str,
        ctx_cycle: int,
        summary: str,
        global_summary: str,
        vital_signals: List[Dict[str, Any]],
    ) -> str:
        """
        Met à jour DoTGraph et renvoie un long_term_summary.
        """
        def _sync_update() -> str:
            with SessionLocal() as db:
                g: DoTGraph = get_dot_memory(db, agent_id)

                long_term_root_id = None
                if global_summary:
                    long_term_root_id = g.add_thought(
                        text=global_summary,
                        ttype="memory",
                        tags=["global"],
                        score=0.7,
                        conf=0.8,
                        meta={"source": "global_summary"},
                        where="long_term",
                    )

                if summary:
                    ev_id = g.add_thought(
                        text=summary,
                        ttype="evidence",
                        tags=["cycle"],
                        score=0.4,
                        conf=0.7,
                        meta={"source": "cycle_summary", "cycle": ctx_cycle},
                        where="working",
                    )
                    if long_term_root_id:
                        g.link(ev_id, long_term_root_id, "supports", confidence=0.7)

                for sig in vital_signals or []:
                    txt = (sig.get("reason") or sig.get("text") or str(sig))[:300]
                    dec_id = g.add_thought(
                        text=txt,
                        ttype="decision",
                        tags=["vital"],
                        score=0.6,
                        conf=0.75,
                        meta={"source": "vital_signal"},
                        where="working",
                    )
                    if long_term_root_id:
                        g.link(dec_id, long_term_root_id, "supports", confidence=0.8)

                g.decay(half_life_minutes=120.0)
                g.consolidate(thresh=0.6)
                g.prune(min_score=0.05, min_conf=0.55, keep_sets=("long_term",))

                long_term_summary = g.summarize_long_term(limit=12)
                save_dot_memory(db, agent_id, g)
                return long_term_summary

        return await asyncio.to_thread(_sync_update)
