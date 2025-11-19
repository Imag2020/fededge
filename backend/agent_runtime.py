# backend/agent_runtime.py
import asyncio
import logging
from typing import Optional, Dict, Any

from .agent_core_types import EventBus, Event, Context, AgentProfile, Topic, EventKind
from .agent_memory import SQLAgentMemoryStore
from .agent_planner import Planner
from .agent_executor import Executor
from .agent_reflector import Reflector

# backend/agent_runtime.py (exemple)
from .db.models import engine  # ou de là où vient ton engine
from .agent_models import AgentBase

# À l'init globale, avant de lancer le runtime
AgentBase.metadata.create_all(bind=engine)

logger = logging.getLogger("agents_v3")


class Orchestrator:
    def __init__(self, agent_id: str, llm_pool, profile: AgentProfile, use_real_tools: bool = True, chat_timeout_minutes: int = 30):
        self.agent_id = agent_id
        self.bus = EventBus()
        self.store = SQLAgentMemoryStore(agent_id)
        self.llm_pool = llm_pool
        self.profile = profile
        self.planner = Planner(llm_pool, profile)
        self.executor = Executor(llm_pool, self.bus, profile, use_real_tools=use_real_tools)
        self.reflector = Reflector(llm_pool, self.store, profile)
        self._stop = asyncio.Event()
        self._main_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._sem = asyncio.Semaphore(2)  # 2 events en parallèle max
        self.chat_timeout_minutes = chat_timeout_minutes  # Timeout pour vider l'historique

    async def start(self):
        await self.store.init()
        if self._main_task is None:
            self._main_task = asyncio.create_task(self._run_loop(), name=f"Orchestrator-{self.agent_id}")
            logger.info("Orchestrator %s started", self.agent_id)

        # Démarrer la tâche de nettoyage automatique
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name=f"Cleanup-{self.agent_id}")
            logger.info("Chat history cleanup task started (timeout=%d min)", self.chat_timeout_minutes)

    async def stop(self):
        self._stop.set()
        if self._main_task:
            self._main_task.cancel()
            await asyncio.gather(self._main_task, return_exceptions=True)
            self._main_task = None
        if self._cleanup_task:
            self._cleanup_task.cancel()
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
            self._cleanup_task = None

    async def _run_loop(self):
        cycle = 0
        while not self._stop.is_set():
            try:
                event = await self.bus.get()
                cycle += 1
                await self._sem.acquire()
                asyncio.create_task(self._handle_event(event, cycle))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Orchestrator loop error: %s", e, exc_info=True)

    async def _handle_event(self, event: Event, cycle: int):
        try:
            logger.info(f"[Runtime] Event received - cycle={cycle}, topic={event.topic}, kind={event.kind}, source={event.source}")
            mem = await self.store.load()
            ctx = Context(
                memory=mem,
                profile=self.profile,
                last_event=event,
                cycle=cycle,
                mission_id=event.payload.get("mission_id"),
            )
            plan = await self.planner.plan(ctx, event)
            results = await self.executor.run_plan(ctx, plan)
            await self.reflector.reflect(ctx, plan, results)
            logger.info(f"[Runtime] Event processed successfully - cycle={cycle}")
        except Exception as e:
            logger.error(f"[Runtime] Error handling event cycle={cycle}: {e}", exc_info=True)
        finally:
            self._sem.release()

    async def post_event(self, kind: EventKind, topic: Topic, payload: Dict[str, Any], source: str = "api"):
        ev = Event(kind=kind, topic=topic, payload=payload, source=source)
        logger.debug(f"[Runtime] Posting event - kind={kind}, topic={topic}, source={source}")
        await self.bus.publish(ev)

    async def execute_chat_stream(self, user_text: str, conversation_id: str):
        """
        Exécute une question chat en mode streaming direct (bypass event bus).

        Yields:
            - {"type": "token", "token": "..."}
            - {"type": "tool_call", "name": "...", "args": {...}}
            - {"type": "tool_result", "name": "...", "result": {...}}
            - {"type": "done", "answer": "..."}
        """
        from .agent_core_types import Action, ActionType

        try:
            # Charger la mémoire
            mem = await self.store.load()

            # Stocker conversation_id
            mem.working["conversation_id"] = conversation_id

            # Créer le contexte
            ctx = Context(
                memory=mem,
                profile=self.profile,
                last_event=None,
                cycle=0,
                mission_id="chat_stream"
            )

            # Créer l'action ANSWER
            action = Action(ActionType.ANSWER, {"question": user_text})

            # Stream via executor
            async for event in self.executor.execute_stream(ctx, action):
                yield event

        except Exception as e:
            logger.error(f"[Runtime] execute_chat_stream error: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}

    async def clear_chat_history(self):
        """Vide l'historique du chat dans la mémoire de l'agent"""
        logger.info("[Runtime] Clearing chat history")
        mem = await self.store.load()
        mem.working["chat_history"] = []
        mem.working["last_user_answer"] = None
        mem.working["last_chat_activity"] = None  # Reset le timestamp d'activité
        await self.store.save(mem)
        logger.info("[Runtime] Chat history cleared successfully")

    async def _cleanup_loop(self):
        """Tâche périodique pour vider l'historique après inactivité"""
        import time
        while not self._stop.is_set():
            try:
                await asyncio.sleep(300)  # Vérifier toutes les 5 minutes

                mem = await self.store.load()
                last_activity = mem.working.get("last_chat_activity")
                chat_history = mem.working.get("chat_history", [])

                if last_activity and chat_history:
                    # Calculer le temps écoulé depuis la dernière activité
                    elapsed_minutes = (time.time() - last_activity) / 60
                    if elapsed_minutes > self.chat_timeout_minutes:
                        logger.info(f"[Runtime] Chat inactive for {elapsed_minutes:.1f} min, clearing history (timeout={self.chat_timeout_minutes} min)")
                        await self.clear_chat_history()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Runtime] Error in cleanup loop: {e}", exc_info=True)


# Singleton simple
_runtime_singleton: Optional[Orchestrator] = None

def get_runtime(
    llm_pool,
    *,
    whoami: str,
    mission: str,
    tools,
    agent_id: str = "fededge_core_v3",
    use_real_tools: bool = True,
) -> Orchestrator:
    global _runtime_singleton
    profile = AgentProfile(
        whoami=whoami,
        mission=mission,
        tools=tools or [],
    )

    if _runtime_singleton is None:
        _runtime_singleton = Orchestrator(
            agent_id=agent_id,
            llm_pool=llm_pool,
            profile=profile,
            use_real_tools=use_real_tools,
        )
    else:
        if _runtime_singleton.llm_pool is None and llm_pool is not None:
            _runtime_singleton.llm_pool = llm_pool
    return _runtime_singleton


def get_agent_runtime() -> Optional[Orchestrator]:
    """Get the current agent runtime singleton if it exists"""
    global _runtime_singleton
    return _runtime_singleton
