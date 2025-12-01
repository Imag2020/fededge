# backend/chat_worker_agent_v3.py

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChatWorkerAgentV3Config:
    poll_interval: float = 0.3
    max_wait_time: float = 600.0
    stream_chunk_size: int = 10
    stream_delay: float = 0.05


class ChatWorkerAgentV3:
    """
    Chat Worker pour l'Agent V3 (orchestrator générique).

    Hypothèses sur AgentRuntime V3 :
    - runtime.post_event(kind=EventKind.USER_CHAT, topic=Topic.USER, payload={...}, source=conversation_id)
    - runtime.store.load() retourne un snapshot avec working["last_user_answer"] : {"question": str, "answer": str, "ts": float}
    - working["last_chat_tools"] contient les tools déclenchés par le chat
    """

    def __init__(self, config: Optional[ChatWorkerAgentV3Config] = None):
        self.config = config or ChatWorkerAgentV3Config()
        self._runtime = None

    def set_runtime(self, runtime):
        """Injecter le runtime Agent V3 (appelé depuis main.py au startup)."""
        self._runtime = runtime
        logger.info("ChatWorkerAgentV3: Runtime Agent V3 configuré")

    def get_runtime(self):
        """Récupérer le runtime Agent V3."""
        if self._runtime is not None:
            return self._runtime
        raise RuntimeError("Agent V3 runtime not set on ChatWorkerAgentV3")

    async def stream_chat(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Streaming chat avec Agent V3 - VRAI STREAMING du LLM en temps réel.

        Yields:
            - {'type': 'status', 'status': 'thinking'}
            - {'type': 'token', 'token': '...'}  # Tokens LLM en temps réel
            - {'type': 'status', 'status': 'tool_call', 'tool_name': '...', 'args': {...}}
            - {'type': 'status', 'status': 'tool_result', 'tool_name': '...', 'result': {...}}
            - {'type': 'done'}
        """
        try:
            runtime = self.get_runtime()

            # Statut initial
            yield {'type': 'status', 'status': 'thinking'}
            logger.info(f"[ChatWorkerAgentV3] User message: {user_text[:60]}...")

            # Stream direct via runtime (bypass event bus pour meilleure réactivité)
            conv_id = conversation_id or "chat_worker_v3"

            async for event in runtime.execute_chat_stream(user_text, conv_id):
                event_type = event.get("type")

                if event_type == "token":
                    # Token du LLM en temps réel
                    yield {'type': 'token', 'token': event["token"]}

                elif event_type == "tool_call":
                    # Tool détecté pendant le streaming
                    tool_name = event["name"]
                    tool_args = event.get("args", {})
                    logger.info(f"[ChatWorkerAgentV3] Tool call: {tool_name}")
                    yield {
                        'type': 'status',
                        'status': 'tool_call',
                        'tool_name': tool_name,
                        'args': tool_args
                    }

                elif event_type == "tool_result":
                    # Résultat du tool
                    tool_name = event["name"]
                    tool_result = event.get("result", {})
                    logger.info(f"[ChatWorkerAgentV3] Tool result: {tool_name}")
                    yield {
                        'type': 'status',
                        'status': 'tool_result',
                        'tool_name': tool_name,
                        'result': tool_result
                    }

                elif event_type == "done":
                    # Fin du stream
                    logger.info(f"[ChatWorkerAgentV3] Stream completed")
                    yield {'type': 'done'}

                elif event_type == "error":
                    # Erreur
                    error_msg = event.get('error', 'Unknown error')
                    logger.error(f"[ChatWorkerAgentV3] Stream error: {error_msg}")
                    yield {
                        'type': 'token',
                        'token': f"❌ Error: {error_msg}"
                    }
                    yield {'type': 'done'}

        except Exception as e:
            logger.error(f"[ChatWorkerAgentV3] Error: {e}", exc_info=True)
            yield {
                'type': 'token',
                'token': f"❌ Erreur: {str(e)}"
            }
            yield {'type': 'done'}

    async def generate(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        full_response = ""
        async for event in self.stream_chat(user_text, history, conversation_id, **kwargs):
            if event['type'] == 'token':
                full_response += event['token']
        return full_response


# =========================
# Singleton
# =========================

_chat_worker_agent_v3_instance: Optional[ChatWorkerAgentV3] = None


def get_chat_worker_agent_v3() -> ChatWorkerAgentV3:
    global _chat_worker_agent_v3_instance

    if _chat_worker_agent_v3_instance is None:
        _chat_worker_agent_v3_instance = ChatWorkerAgentV3()

    return _chat_worker_agent_v3_instance


def init_chat_worker_agent_v3(runtime):
    worker = get_chat_worker_agent_v3()
    worker.set_runtime(runtime)
    logger.info("✅ ChatWorkerAgentV3 initialized with Agent V3 runtime")
