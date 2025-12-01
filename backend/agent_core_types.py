# backend/agent_core_types.py
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
import asyncio

class Topic(str, Enum):
    USER = "user"
    SYSTEM = "system"
    MISSION = "mission"
    TOOL = "tool"
    TIMER = "timer"


class EventKind(str, Enum):
    MESSAGE = "MESSAGE"          # chat, logs, etc.
    MISSION_TICK = "MISSION_TICK"
    TOOL_RESULT = "TOOL_RESULT"
    MISSION_UPDATE = "MISSION_UPDATE"


class Priority(IntEnum):
    HIGH = 0      # user chat, erreurs
    NORMAL = 10   # missions courantes
    LOW = 20      # tâches de fond


@dataclass
class Event:
    kind: EventKind
    topic: Topic
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    priority: Priority = Priority.NORMAL
    ts: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: f"e_{int(time.time()*1000)}")


class ActionType(str, Enum):
    PLAN = "PLAN"        # planifier une mission / tâche
    EXECUTE = "EXECUTE"  # exécuter une étape (tool, appel LLM, etc.)
    ANSWER = "ANSWER"    # répondre à l'utilisateur
    SLEEP = "SLEEP"      # micro pause
    EMIT = "EMIT"        # publier un event
    UPDATE_CONSCIOUSNESS = "UPDATE_CONSCIOUSNESS"  # mettre à jour la conscience globale


@dataclass
class Action:
    type: ActionType
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    mission_id: str
    actions: List[Action]
    rationale: str = ""


@dataclass
class AgentProfile:
    whoami: str
    mission: str
    tools: List[str]
    max_context_chars: int = 1400


@dataclass
class Context:
    memory: Any
    profile: AgentProfile
    last_event: Optional[Event]
    cycle: int
    mission_id: Optional[str] = None


class EventBus:
    """
    EventBus avec priorité simple.
    """
    def __init__(self, maxsize: int = 1000):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=maxsize)
        self._counter: int = 0

    async def publish(self, event: Event):
        self._counter += 1
        await self.queue.put((event.priority, self._counter, event))

    async def get(self) -> Event:
        _, _, ev = await self.queue.get()
        return ev
