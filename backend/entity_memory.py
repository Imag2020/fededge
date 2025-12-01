# backend/entity_memory.py
"""
Entity-Relationship Memory Graph

Complément au DoTGraph (raisonnement) pour stocker :
- Entités : Users, Assets, Positions, Patterns, Decisions, Outcomes
- Relations : OWNS, WATCHES, FOLLOWS, DECIDED, RESULTED_IN, etc.

Usage:
    graph = get_entity_graph("agent_123")

    # Add user
    user_id = graph.add_entity("user", "Alice", {"risk_profile": "moderate"})

    # Add asset
    btc_id = graph.add_entity("asset", "Bitcoin", {"symbol": "BTC", "price": 90000})

    # Create relationship
    graph.add_relation(user_id, btc_id, "OWNS", {"amount": 0.5, "entry_price": 45000})

    # Query
    positions = graph.get_user_positions(user_id)
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal, Any, Tuple
from time import time
import uuid
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Type Definitions
# ============================================================================

EntityType = Literal[
    # Acteurs
    "user",           # Utilisateur
    "asset",          # Crypto asset (BTC, ETH, SOL, ...)

    # Actions & Positions
    "position",       # Position ouverte/fermée
    "decision",       # Décision prise
    "outcome",        # Résultat d'une décision

    # Analyse
    "pattern",        # Pattern détecté
    "signal",         # Signal de trading
    "opportunity",    # Opportunité détectée

    # Événements
    "market_event",   # Événement macro
    "news_event",     # Actualité majeure
]

RelationType = Literal[
    # User ↔ Assets
    "OWNS",           # User owns Asset
    "WATCHES",        # User watches Asset
    "INTERESTED_IN",  # User intéressé par Asset

    # Patterns & Signals
    "DETECTED",       # Pattern detected on Asset
    "TRIGGERED",      # Signal triggered by Pattern
    "INVALIDATED",    # Pattern invalidated

    # Decisions & Outcomes
    "DECIDED",        # User decided to X
    "BASED_ON",       # Decision based on Signal/Pattern
    "RESULTED_IN",    # Decision resulted in Outcome

    # Patterns & Outcomes
    "FOLLOWS",        # Asset follows Pattern
    "CORRELATES",     # Pattern correlates with Outcome

    # Temporal
    "PRECEDED",       # Event A preceded Event B
    "COINCIDED",      # Event A coincided with Event B
]


# ============================================================================
# Data Classes
# ============================================================================

def _gen_id(prefix: str = "ent") -> str:
    """Generate unique entity/relation ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class EntityNode:
    """Nœud d'entité dans le graphe"""
    id: str
    type: EntityType
    label: str

    # Attributes flexibles (dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)
    tags: List[str] = field(default_factory=list)

    # Importance score (pour ranking)
    importance: float = 0.5  # 0..1

    # Consolidation (comme DoT)
    consolidation: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EntityRelation:
    """Relation entre deux entités"""
    id: str
    source: str      # Source entity ID
    target: str      # Target entity ID
    type: RelationType

    # Attributes de la relation
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Temporal
    created_at: float = field(default_factory=time)

    # Strength/confidence
    strength: float = 0.7  # 0..1

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# Entity Graph
# ============================================================================

class EntityGraph:
    """
    Graphe d'entités-relations pour la mémoire factuelle

    Séparé du DoTGraph (qui gère le raisonnement)
    """

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id
        self.entities: Dict[str, EntityNode] = {}
        self.relations: List[EntityRelation] = []

        # Index pour performance
        self._relations_by_source: Dict[str, List[EntityRelation]] = {}
        self._relations_by_target: Dict[str, List[EntityRelation]] = {}
        self._entities_by_type: Dict[EntityType, List[str]] = {}

    # ========================================================================
    # CRUD - Create
    # ========================================================================

    def add_entity(
        self,
        type: EntityType,
        label: str,
        attributes: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        entity_id: Optional[str] = None,
    ) -> str:
        """
        Ajoute une entité au graphe

        Returns:
            entity_id
        """
        eid = entity_id or _gen_id("ent")

        entity = EntityNode(
            id=eid,
            type=type,
            label=label,
            attributes=attributes or {},
            importance=importance,
            tags=tags or [],
        )

        self.entities[eid] = entity

        # Update index
        if type not in self._entities_by_type:
            self._entities_by_type[type] = []
        self._entities_by_type[type].append(eid)

        logger.debug(f"[EntityGraph] Added entity: {eid} ({type}: {label})")
        return eid

    def add_relation(
        self,
        source: str,
        target: str,
        type: RelationType,
        attributes: Optional[Dict[str, Any]] = None,
        strength: float = 0.7,
        relation_id: Optional[str] = None,
    ) -> str:
        """
        Ajoute une relation entre deux entités

        Returns:
            relation_id
        """
        # Validate entities exist
        if source not in self.entities:
            raise ValueError(f"Source entity not found: {source}")
        if target not in self.entities:
            raise ValueError(f"Target entity not found: {target}")

        rid = relation_id or _gen_id("rel")

        relation = EntityRelation(
            id=rid,
            source=source,
            target=target,
            type=type,
            attributes=attributes or {},
            strength=strength,
        )

        self.relations.append(relation)

        # Update indexes
        if source not in self._relations_by_source:
            self._relations_by_source[source] = []
        self._relations_by_source[source].append(relation)

        if target not in self._relations_by_target:
            self._relations_by_target[target] = []
        self._relations_by_target[target].append(relation)

        # Increment consolidation (like DoT)
        if source in self.entities:
            self.entities[source].consolidation += 0.05
        if target in self.entities:
            self.entities[target].consolidation += 0.05

        logger.debug(f"[EntityGraph] Added relation: {source} --[{type}]--> {target}")
        return rid

    # ========================================================================
    # CRUD - Read
    # ========================================================================

    def get_entity(self, entity_id: str) -> Optional[EntityNode]:
        """Récupère une entité par ID"""
        return self.entities.get(entity_id)

    def find_entities(
        self,
        type: Optional[EntityType] = None,
        tags: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_importance: Optional[float] = None,
    ) -> List[EntityNode]:
        """
        Recherche d'entités avec filtres

        Args:
            type: Filtrer par type d'entité
            tags: Filtrer par tags (doit contenir tous les tags)
            filters: Filtres sur attributes (ex: {"symbol": "BTC"})
            min_importance: Importance minimale

        Returns:
            Liste d'entités matchant les critères
        """
        results = []

        # Start with type filter if specified (uses index)
        if type:
            candidate_ids = self._entities_by_type.get(type, [])
            candidates = [self.entities[eid] for eid in candidate_ids if eid in self.entities]
        else:
            candidates = list(self.entities.values())

        for entity in candidates:
            # Tags filter
            if tags and not set(tags).issubset(set(entity.tags)):
                continue

            # Importance filter
            if min_importance is not None and entity.importance < min_importance:
                continue

            # Attribute filters
            if filters:
                match = True
                for key, value in filters.items():
                    # Support for nested keys with dot notation (e.g., "meta.source")
                    attr_value = entity.attributes.get(key)

                    # Special operators
                    if isinstance(value, dict):
                        # Range queries: {"$gte": 100, "$lte": 200}
                        if "$gte" in value and attr_value is not None and attr_value < value["$gte"]:
                            match = False
                            break
                        if "$lte" in value and attr_value is not None and attr_value > value["$lte"]:
                            match = False
                            break
                        if "$gt" in value and attr_value is not None and attr_value <= value["$gt"]:
                            match = False
                            break
                        if "$lt" in value and attr_value is not None and attr_value >= value["$lt"]:
                            match = False
                            break
                    else:
                        # Exact match
                        if attr_value != value:
                            match = False
                            break

                if not match:
                    continue

            results.append(entity)

        return results

    def get_relations(
        self,
        entity_id: str,
        direction: Literal["out", "in", "both"] = "both",
        rel_type: Optional[RelationType] = None,
    ) -> List[EntityRelation]:
        """
        Récupère les relations d'une entité

        Args:
            entity_id: ID de l'entité
            direction: "out" (sortantes), "in" (entrantes), "both"
            rel_type: Filtrer par type de relation

        Returns:
            Liste de relations
        """
        results = []

        if direction in ("out", "both"):
            out_rels = self._relations_by_source.get(entity_id, [])
            results.extend(out_rels)

        if direction in ("in", "both"):
            in_rels = self._relations_by_target.get(entity_id, [])
            results.extend(in_rels)

        # Filter by relation type
        if rel_type:
            results = [r for r in results if r.type == rel_type]

        return results

    def neighbors(
        self,
        entity_id: str,
        direction: Literal["out", "in", "both"] = "both",
        rel_type: Optional[RelationType] = None,
    ) -> List[Tuple[EntityNode, EntityRelation]]:
        """
        Récupère les voisins d'une entité

        Returns:
            Liste de (entity, relation) tuples
        """
        relations = self.get_relations(entity_id, direction, rel_type)
        results = []

        for rel in relations:
            # Determine neighbor entity
            if rel.source == entity_id:
                neighbor_id = rel.target
            else:
                neighbor_id = rel.source

            neighbor = self.get_entity(neighbor_id)
            if neighbor:
                results.append((neighbor, rel))

        return results

    # ========================================================================
    # CRUD - Update
    # ========================================================================

    def update_entity(
        self,
        entity_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Met à jour une entité"""
        entity = self.get_entity(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")

        if attributes:
            entity.attributes.update(attributes)
        if importance is not None:
            entity.importance = importance
        if tags is not None:
            entity.tags = tags

        entity.updated_at = time()
        logger.debug(f"[EntityGraph] Updated entity: {entity_id}")

    def update_relation(
        self,
        relation_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        strength: Optional[float] = None,
    ) -> None:
        """Met à jour une relation"""
        relation = None
        for rel in self.relations:
            if rel.id == relation_id:
                relation = rel
                break

        if not relation:
            raise ValueError(f"Relation not found: {relation_id}")

        if attributes:
            relation.attributes.update(attributes)
        if strength is not None:
            relation.strength = strength

        logger.debug(f"[EntityGraph] Updated relation: {relation_id}")

    # ========================================================================
    # CRUD - Delete
    # ========================================================================

    def remove_entity(self, entity_id: str, cascade: bool = True) -> None:
        """
        Supprime une entité

        Args:
            entity_id: ID de l'entité
            cascade: Si True, supprime aussi les relations associées
        """
        if entity_id not in self.entities:
            return

        entity = self.entities[entity_id]

        # Remove from indexes
        if entity.type in self._entities_by_type:
            if entity_id in self._entities_by_type[entity.type]:
                self._entities_by_type[entity.type].remove(entity_id)

        # Remove relations if cascade
        if cascade:
            # Remove from relations list
            self.relations = [
                r for r in self.relations
                if r.source != entity_id and r.target != entity_id
            ]

            # Update indexes
            self._relations_by_source.pop(entity_id, None)
            self._relations_by_target.pop(entity_id, None)

        # Remove entity
        del self.entities[entity_id]
        logger.debug(f"[EntityGraph] Removed entity: {entity_id}")

    def remove_relation(self, relation_id: str) -> None:
        """Supprime une relation"""
        relation = None
        for i, rel in enumerate(self.relations):
            if rel.id == relation_id:
                relation = rel
                del self.relations[i]
                break

        if not relation:
            return

        # Update indexes
        if relation.source in self._relations_by_source:
            self._relations_by_source[relation.source] = [
                r for r in self._relations_by_source[relation.source]
                if r.id != relation_id
            ]

        if relation.target in self._relations_by_target:
            self._relations_by_target[relation.target] = [
                r for r in self._relations_by_target[relation.target]
                if r.id != relation_id
            ]

        logger.debug(f"[EntityGraph] Removed relation: {relation_id}")

    # ========================================================================
    # Graph Queries
    # ========================================================================

    def neighborhood(
        self,
        entity_id: str,
        radius: int = 2,
        max_entities: int = 100,
    ) -> Dict[str, Any]:
        """
        Récupère le voisinage d'une entité (BFS)

        Returns:
            Dict with "entities" and "relations"
        """
        if entity_id not in self.entities:
            return {"entities": [], "relations": []}

        visited_entities = {entity_id}
        visited_relations = set()
        frontier = [entity_id]

        for _ in range(radius):
            if len(visited_entities) >= max_entities:
                break

            new_frontier = []
            for eid in frontier:
                neighbors = self.neighbors(eid, "both")

                for neighbor, relation in neighbors:
                    if neighbor.id not in visited_entities:
                        visited_entities.add(neighbor.id)
                        new_frontier.append(neighbor.id)

                    visited_relations.add(relation.id)

                    if len(visited_entities) >= max_entities:
                        break

            frontier = new_frontier

        entities = [self.entities[eid].to_dict() for eid in visited_entities if eid in self.entities]
        relations = [r.to_dict() for r in self.relations if r.id in visited_relations]

        return {
            "entities": entities,
            "relations": relations,
        }

    def path_between(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> List[List[str]]:
        """
        Trouve tous les chemins entre deux entités (DFS)

        Returns:
            Liste de chemins (chaque chemin = liste d'entity IDs)
        """
        if source not in self.entities or target not in self.entities:
            return []

        paths = []

        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return

            if current == target:
                paths.append(path[:])
                return

            neighbors = self.neighbors(current, "out")
            for neighbor, _ in neighbors:
                if neighbor.id not in path:  # Avoid cycles
                    path.append(neighbor.id)
                    dfs(neighbor.id, path, depth + 1)
                    path.pop()

        dfs(source, [source], 0)
        return paths

    # ========================================================================
    # Domain-Specific Queries
    # ========================================================================

    def get_user_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Récupère les positions d'un utilisateur"""
        owns_relations = self.get_relations(user_id, "out", "OWNS")

        positions = []
        for rel in owns_relations:
            asset = self.get_entity(rel.target)
            if asset:
                positions.append({
                    "asset": asset.label,
                    "symbol": asset.attributes.get("symbol"),
                    "amount": rel.attributes.get("amount", 0),
                    "entry_price": rel.attributes.get("entry_price", 0),
                    "current_price": asset.attributes.get("price", 0),
                })

        return positions

    def get_pattern_occurrences(
        self,
        pattern_type: str,
        asset: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Récupère les occurrences d'un pattern (optionnellement sur un asset)"""
        # Find pattern entities
        patterns = self.find_entities(
            type="pattern",
            filters={"pattern_type": pattern_type}
        )

        results = []
        for pattern in patterns[:limit]:
            # Get asset via DETECTED relation
            detected_rels = self.get_relations(pattern.id, "in", "DETECTED")

            for rel in detected_rels:
                asset_entity = self.get_entity(rel.source)
                if asset_entity:
                    if asset and asset_entity.attributes.get("symbol") != asset:
                        continue

                    # Get outcome if exists
                    outcome = None
                    resulted_rels = self.get_relations(pattern.id, "out", "RESULTED_IN")
                    if resulted_rels:
                        outcome_entity = self.get_entity(resulted_rels[0].target)
                        if outcome_entity:
                            outcome = outcome_entity.attributes

                    results.append({
                        "pattern": pattern.label,
                        "pattern_type": pattern.attributes.get("pattern_type"),
                        "asset": asset_entity.label,
                        "symbol": asset_entity.attributes.get("symbol"),
                        "confidence": pattern.attributes.get("confidence", 0),
                        "detected_at": pattern.created_at,
                        "outcome": outcome,
                    })

        return results

    def get_decision_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Récupère l'historique des décisions d'un utilisateur"""
        decided_rels = self.get_relations(user_id, "out", "DECIDED")

        decisions = []
        for rel in decided_rels[:limit]:
            decision = self.get_entity(rel.target)
            if decision:
                # Get signal/pattern that triggered decision
                based_on_rels = self.get_relations(decision.id, "out", "BASED_ON")
                trigger = None
                if based_on_rels:
                    trigger_entity = self.get_entity(based_on_rels[0].target)
                    if trigger_entity:
                        trigger = {
                            "type": trigger_entity.type,
                            "label": trigger_entity.label,
                        }

                # Get outcome
                outcome = None
                resulted_rels = self.get_relations(decision.id, "out", "RESULTED_IN")
                if resulted_rels:
                    outcome_entity = self.get_entity(resulted_rels[0].target)
                    if outcome_entity:
                        outcome = outcome_entity.attributes

                decisions.append({
                    "decision": decision.label,
                    "action": decision.attributes.get("action"),
                    "asset": decision.attributes.get("asset"),
                    "timestamp": decision.created_at,
                    "trigger": trigger,
                    "outcome": outcome,
                })

        return decisions

    # ========================================================================
    # SQL Persistence (Phase 2.5)
    # ========================================================================

    def save_to_sql(self) -> None:
        """
        Sauvegarde le graphe dans SQL (tables agent_entity_nodes, agent_entity_relations)

        Stratégie:
        - DELETE all existing entities/relations for this agent
        - INSERT all current entities/relations
        """
        try:
            from .db.models import SessionLocal, AgentEntityNode, AgentEntityRelation
            import datetime

            with SessionLocal() as db:
                # 1. Delete existing data for this agent
                db.query(AgentEntityRelation).filter_by(agent_id=self.agent_id).delete()
                db.query(AgentEntityNode).filter_by(agent_id=self.agent_id).delete()

                # 2. Insert entities
                for entity_id, entity in self.entities.items():
                    db_entity = AgentEntityNode(
                        id=entity.id,
                        agent_id=self.agent_id,
                        type=entity.type,
                        label=entity.label,
                        attributes=entity.attributes,
                        created_at=datetime.datetime.fromtimestamp(entity.created_at),
                        updated_at=datetime.datetime.fromtimestamp(entity.updated_at),
                        tags=entity.tags,
                        importance=entity.importance,
                        consolidation=entity.consolidation,
                    )
                    db.add(db_entity)

                # 3. Insert relations
                for relation in self.relations:
                    db_relation = AgentEntityRelation(
                        id=relation.id,
                        agent_id=self.agent_id,
                        source_id=relation.source,
                        target_id=relation.target,
                        type=relation.type,
                        attributes=relation.attributes,
                        created_at=datetime.datetime.fromtimestamp(relation.created_at),
                        strength=relation.strength,
                    )
                    db.add(db_relation)

                db.commit()
                logger.info(f"[EntityGraph] Saved to SQL: {len(self.entities)} entities, {len(self.relations)} relations")

        except Exception as e:
            logger.error(f"[EntityGraph] Error saving to SQL: {e}", exc_info=True)
            raise

    def load_from_sql(self) -> None:
        """
        Charge le graphe depuis SQL

        Remplace le graphe en mémoire avec les données SQL
        """
        try:
            from .db.models import SessionLocal, AgentEntityNode, AgentEntityRelation

            with SessionLocal() as db:
                # 1. Load entities
                db_entities = db.query(AgentEntityNode).filter_by(agent_id=self.agent_id).all()

                self.entities = {}
                self._entities_by_type = {}

                for db_entity in db_entities:
                    entity = EntityNode(
                        id=db_entity.id,
                        type=db_entity.type,
                        label=db_entity.label,
                        attributes=db_entity.attributes or {},
                        created_at=db_entity.created_at.timestamp() if db_entity.created_at else time(),
                        updated_at=db_entity.updated_at.timestamp() if db_entity.updated_at else time(),
                        tags=db_entity.tags or [],
                        importance=db_entity.importance or 0.5,
                        consolidation=db_entity.consolidation or 0.0,
                    )

                    self.entities[entity.id] = entity

                    # Rebuild index
                    if entity.type not in self._entities_by_type:
                        self._entities_by_type[entity.type] = []
                    self._entities_by_type[entity.type].append(entity.id)

                # 2. Load relations
                db_relations = db.query(AgentEntityRelation).filter_by(agent_id=self.agent_id).all()

                self.relations = []
                self._relations_by_source = {}
                self._relations_by_target = {}

                for db_relation in db_relations:
                    relation = EntityRelation(
                        id=db_relation.id,
                        source=db_relation.source_id,
                        target=db_relation.target_id,
                        type=db_relation.type,
                        attributes=db_relation.attributes or {},
                        created_at=db_relation.created_at.timestamp() if db_relation.created_at else time(),
                        strength=db_relation.strength or 0.7,
                    )

                    self.relations.append(relation)

                    # Rebuild indexes
                    if relation.source not in self._relations_by_source:
                        self._relations_by_source[relation.source] = []
                    self._relations_by_source[relation.source].append(relation)

                    if relation.target not in self._relations_by_target:
                        self._relations_by_target[relation.target] = []
                    self._relations_by_target[relation.target].append(relation)

                logger.info(f"[EntityGraph] Loaded from SQL: {len(self.entities)} entities, {len(self.relations)} relations")

        except Exception as e:
            logger.error(f"[EntityGraph] Error loading from SQL: {e}", exc_info=True)
            # Don't raise - just log and keep empty graph
            return

    # ========================================================================
    # Serialization
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dict"""
        return {
            "agent_id": self.agent_id,
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EntityGraph:
        """Deserialize graph from dict"""
        graph = cls(agent_id=data.get("agent_id", "default_agent"))

        # Load entities
        for eid, edata in data.get("entities", {}).items():
            entity = EntityNode(**edata)
            graph.entities[eid] = entity

            # Rebuild indexes
            if entity.type not in graph._entities_by_type:
                graph._entities_by_type[entity.type] = []
            graph._entities_by_type[entity.type].append(eid)

        # Load relations
        for rdata in data.get("relations", []):
            relation = EntityRelation(**rdata)
            graph.relations.append(relation)

            # Rebuild indexes
            if relation.source not in graph._relations_by_source:
                graph._relations_by_source[relation.source] = []
            graph._relations_by_source[relation.source].append(relation)

            if relation.target not in graph._relations_by_target:
                graph._relations_by_target[relation.target] = []
            graph._relations_by_target[relation.target].append(relation)

        return graph


# ============================================================================
# Singleton / Factory
# ============================================================================

_entity_graphs: Dict[str, EntityGraph] = {}


def get_entity_graph(agent_id: str = "default_agent", auto_load: bool = True) -> EntityGraph:
    """
    Get or create entity graph for agent

    Args:
        agent_id: Agent ID
        auto_load: If True, automatically load from SQL on first access

    Returns:
        EntityGraph instance
    """
    if agent_id not in _entity_graphs:
        _entity_graphs[agent_id] = EntityGraph(agent_id=agent_id)
        logger.info(f"[EntityGraph] Created new graph for agent: {agent_id}")

        # Auto-load from SQL if enabled
        if auto_load:
            try:
                _entity_graphs[agent_id].load_from_sql()
            except Exception as e:
                logger.warning(f"[EntityGraph] Could not auto-load from SQL: {e}")
                # Continue with empty graph

    return _entity_graphs[agent_id]


def reset_entity_graph(agent_id: str = "default_agent") -> None:
    """Reset entity graph (for testing)"""
    if agent_id in _entity_graphs:
        del _entity_graphs[agent_id]
        logger.info(f"[EntityGraph] Reset graph for agent: {agent_id}")
