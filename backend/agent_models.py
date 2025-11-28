# backend/agent_models.py

import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import declarative_base, relationship

AgentBase = declarative_base()


class AgentConfig(AgentBase):
    __tablename__ = "agent_config"

    id = Column(String, primary_key=True)     # ex: "core_agent", "risk_guard"
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)     # "copilot", "teacher", "monitor", ...
    profile_json = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class AgentMemoryKV(AgentBase):
    __tablename__ = "agent_memory_kv"

    agent_id = Column(String, ForeignKey("agent_config.id"), primary_key=True)
    scope = Column(String, primary_key=True)       # "facts" | "working" | "meta" | ...
    key = Column(String, primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    agent = relationship("AgentConfig")


class AgentEvent(AgentBase):
    """
    Log d'événements génériques pour l'agent core.
    """
    __tablename__ = "agent_events"

    id = Column(String, primary_key=True)  # "e_<timestamp>_..." ou autre
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False)

    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    topic = Column(String, nullable=False)         # "user", "external", "tool", "timer", ...
    kind = Column(String, nullable=False)          # "USER_MESSAGE", "TIMER_TICK", "TOOL_RESULT", ...
    source = Column(String, nullable=False)        # "frontend", "scheduler", "tool:get_market", ...
    payload_json = Column(JSON, nullable=False)    # contenu métier

    agent = relationship("AgentConfig")


class AgentSnapshot(AgentBase):
    """
    Snapshots de l'état conscient / mémoire globale de l'agent.
    """
    __tablename__ = "agent_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agent_config.id"), nullable=False, index=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    snapshot_json = Column(JSON, nullable=False)
    summary_text = Column(Text)
    source_event_id = Column(String)

    agent = relationship("AgentConfig")
