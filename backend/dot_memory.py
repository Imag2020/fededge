# backend/dot_memory.py

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal, Tuple
from time import time
import uuid
import math

ThoughtType = Literal[
    "goal", "plan", "hypothesis", "evidence",
    "critique", "idea", "decision", "memory"
]
RelationType = Literal[
    "supports", "contradicts", "derives_from",
    "leads_to", "refines", "cites", "summarizes"
]


def _id(prefix: str = "n") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Edge:
    src: str
    dst: str
    rel: RelationType
    confidence: float = 0.7  # 0..1


@dataclass
class ThoughtNode:
    id: str
    text: str
    ttype: ThoughtType
    score: float = 0.0        # utilité / priorité
    confidence: float = 0.7   # croyance
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time)
    meta: Dict = field(default_factory=dict)  # e.g. {"source": "news", "event_id": "..."}
    # mémoire : poids de consolidation (vers long-terme)
    consolidation: float = 0.0  # s’accumule lorsque réutilisé/référencé


class DoTGraph:
    def __init__(self):
        self.nodes: Dict[str, ThoughtNode] = {}
        self.edges: List[Edge] = []
        # mémoires
        self.scratchpad: List[str] = []   # ids de nodes très temporaires
        self.working: List[str] = []      # ids de nodes de l’épisode
        self.long_term: List[str] = []    # ids “carte mentale” consolidée

    # ---------- CRUD ----------
    def add_thought(
        self,
        text: str,
        ttype: ThoughtType,
        tags: Optional[List[str]] = None,
        score: float = 0.0,
        conf: float = 0.7,
        meta: Optional[Dict] = None,
        where: Literal["scratchpad", "working", "long_term"] = "working",
    ) -> str:
        nid = _id()
        node = ThoughtNode(
            id=nid,
            text=text,
            ttype=ttype,
            score=score,
            confidence=conf,
            tags=tags or [],
            meta=meta or {},
        )
        self.nodes[nid] = node
        getattr(self, where).append(nid)
        return nid

    def link(self, src: str, dst: str, rel: RelationType, confidence: float = 0.7) -> None:
        self.edges.append(Edge(src, dst, rel, confidence))
        # petit “renforcement” d’usage
        if src in self.nodes:
            self.nodes[src].consolidation += 0.05
        if dst in self.nodes:
            self.nodes[dst].consolidation += 0.05

    # ---------- Requêtes ----------
    def neighbors(
        self,
        nid: str,
        direction: Literal["out", "in", "both"] = "both"
    ) -> List[Tuple[str, Edge]]:
        out = [(e.dst, e) for e in self.edges if e.src == nid] if direction in ("out", "both") else []
        inc = [(e.src, e) for e in self.edges if e.dst == nid] if direction in ("in", "both") else []
        return out + inc

    def subgraph_from(self, nid: str, depth: int = 2) -> Dict:
        visited = {nid}
        frontier = [nid]
        for _ in range(depth):
            new = []
            for v in frontier:
                for nb, _e in self.neighbors(v, "both"):
                    if nb not in visited:
                        visited.add(nb)
                        new.append(nb)
            frontier = new
        es = [e for e in self.edges if e.src in visited and e.dst in visited]
        return {
            "nodes": [asdict(self.nodes[i]) for i in visited],
            "edges": [asdict(e) for e in es],
        }

    def find(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        ttype: Optional[ThoughtType] = None,
    ) -> List[str]:
        res = []
        for nid, n in self.nodes.items():
            if query and (query.lower() not in n.text.lower()):
                continue
            if tags and not set(tags).issubset(n.tags):
                continue
            if ttype and n.ttype != ttype:
                continue
            res.append(nid)
        return res

    # ---------- Gestion mémoire ----------
    def decay(self, half_life_minutes: float = 30.0) -> None:
        """Fait décroître score et confiance des pensées non réutilisées récemment."""
        now = time()
        for n in self.nodes.values():
            age_min = (now - n.created_at) / 60.0
            factor = 0.5 ** (age_min / half_life_minutes)
            # On laisse la consolidation “protéger” partiellement la décroissance
            protect = min(0.8, n.consolidation)
            n.score = (n.score * factor) * (1 - protect) + n.score * protect
            n.confidence = 0.5 + (n.confidence - 0.5) * factor

    def consolidate(self, thresh: float = 0.6) -> None:
        """Envoie au long-terme les nœuds suffisamment ‘consolidés’ ou bien scorés."""
        for nid, n in self.nodes.items():
            if (n.consolidation >= thresh or n.score >= thresh) and nid not in self.long_term:
                self.long_term.append(nid)
                # tag “memory”
                if "memory" not in n.tags:
                    n.tags.append("memory")
                if n.ttype != "memory":
                    n.ttype = "memory"

    def prune(
        self,
        min_score: float = 0.05,
        min_conf: float = 0.55,
        keep_sets: Tuple[str, ...] = ("long_term",),
    ) -> None:
        """Purge le bruit (évite de toucher au long-terme)."""
        keep_ids = set().union(*[set(getattr(self, s)) for s in keep_sets])
        dead = [
            nid
            for nid, n in self.nodes.items()
            if nid not in keep_ids and n.score < min_score and n.confidence < min_conf
        ]
        if not dead:
            return
        self.edges = [e for e in self.edges if e.src not in dead and e.dst not in dead]
        for nid in dead:
            self.nodes.pop(nid, None)
            for lst in (self.scratchpad, self.working, self.long_term):
                if nid in lst:
                    lst.remove(nid)

    # ---------- Résumés ----------
    def summarize_branch(self, root: str, depth: int = 2, limit: int = 12) -> str:
        sg = self.subgraph_from(root, depth)
        parts = []
        for n in sorted(
            sg["nodes"],
            key=lambda x: (-x["score"], -x["confidence"]),
        ):
            parts.append(
                f"- {n['ttype']}: {n['text']} "
                f"[score={n['score']:.2f}, conf={n['confidence']:.2f}]"
            )
        return "\n".join(parts[:limit])

    def summarize_long_term(self, limit: int = 12) -> str:
        """Résumé global des nœuds long-terme les plus importants."""
        if not self.long_term:
            return ""
        nodes = [self.nodes[nid] for nid in self.long_term if nid in self.nodes]
        nodes_sorted = sorted(
            nodes,
            key=lambda n: (-n.score, -n.confidence, -n.consolidation),
        )
        lines = []
        for n in nodes_sorted[:limit]:
            lines.append(
                f"- {n.ttype}: {n.text} "
                f"[score={n.score:.2f}, conf={n.confidence:.2f}]"
            )
        return "\n".join(lines)

    # ---------- I/O (dict <-> graph) ----------
    def to_dict(self) -> Dict:
        return {
            "nodes": {nid: asdict(n) for nid, n in self.nodes.items()},
            "edges": [asdict(e) for e in self.edges],
            "memory": {
                "scratchpad": self.scratchpad,
                "working": self.working,
                "long_term": self.long_term,
            },
        }

    @staticmethod
    def from_dict(data: Dict) -> "DoTGraph":
        g = DoTGraph()
        nodes_data = data.get("nodes", {})
        g.nodes = {nid: ThoughtNode(**nd) for nid, nd in nodes_data.items()}
        g.edges = [Edge(**e) for e in data.get("edges", [])]
        mem = data.get("memory", {})
        g.scratchpad = mem.get("scratchpad", [])
        g.working = mem.get("working", [])
        g.long_term = mem.get("long_term", [])
        return g
