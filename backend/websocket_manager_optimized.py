"""
WebSocket Manager Optimisé pour HIVE AI
- Broadcasts asynchrones avec throttling
- Compression des messages volumineux
- Gestion des déconnexions propre
"""

from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging
import asyncio
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

class OptimizedWebSocketManager:
    """
    WebSocket Manager avec optimisations pour réduire la latence
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.conversation_history: Dict[str, List[Dict]] = {}
        # Store streaming state for each client
        self.streaming_state: Dict[str, bool] = {}

        # Throttling: buffer pour éviter trop de broadcasts
        self.broadcast_buffer: deque = deque(maxlen=100)
        self.last_broadcast: Dict[str, datetime] = {}
        self.min_broadcast_interval = timedelta(milliseconds=100)  # Max 10 msg/sec

        # Stats
        self.stats = {
            "total_messages": 0,
            "throttled_messages": 0,
            "failed_sends": 0
        }

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []

        logger.info(f"✅ Client {client_id} connected. Total: {len(self.active_connections)}")

        # Envoyer un message de bienvenue
        await self.send_personal_message(json.dumps({
            "type": "connection_status",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }), client_id)

        # Broadcaster immédiatement l'état de conscience actuel au nouveau client
        await self._send_initial_consciousness(client_id)

    async def _send_initial_consciousness(self, client_id: str):
        """Send the current consciousness state to a newly connected client"""
        try:
            from .agent_consciousness import get_consciousness_broadcaster
            from .agent_runtime import get_agent_runtime

            # Obtenir le runtime de l'agent
            runtime = get_agent_runtime()
            if runtime and runtime.store:
                # Charger la mémoire actuelle depuis le store
                memory = await runtime.store.load()

                working = memory.working
                conscious = memory.conscious

                # Build global consciousness summary
                global_summary = working.get("global_summary", "")
                if not global_summary and conscious:
                    global_summary = conscious.summary

                # Get recent activities
                last_results = working.get("last_results", [])
                last_tools = working.get("last_tools", {})

                # Build consciousness payload using the broadcaster helper
                broadcaster = get_consciousness_broadcaster()
                consciousness_data = {
                    "global_consciousness": global_summary or "Monitoring crypto markets and user activities...",
                    "working_memory": broadcaster._build_working_summary(working, last_results, last_tools),
                    "timestamp": datetime.now().timestamp(),
                    "cycle": working.get("stats", {}).get("total_cycles", 0),
                }

                # Envoyer au client spécifique
                await self.send_personal_message(json.dumps({
                    "type": "agent_consciousness",
                    "payload": consciousness_data
                }), client_id)

                logger.info(f"📊 Initial consciousness sent to {client_id}: {global_summary[:60] if global_summary else 'No summary'}")
        except Exception as e:
            logger.warning(f"⚠️ Could not send initial consciousness to {client_id}: {e}", exc_info=True)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        client_id = None
        for cid, ws in list(self.active_connections.items()):
            if ws == websocket:
                client_id = cid
                break

        if client_id:
            del self.active_connections[client_id]
            logger.info(f"❌ Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
                self.stats["total_messages"] += 1
            except Exception as e:
                logger.error(f"❌ Erreur envoi message à {client_id}: {e}")
                self.stats["failed_sends"] += 1

    async def broadcast(self, message, skip_throttle: bool = False):
        """
        Send a message to all connected clients
        Avec throttling pour éviter surcharge
        """
        if not self.active_connections:
            return

        # Convertir dict to JSON string si nécessaire
        if isinstance(message, dict):
            message = json.dumps(message)

        # Throttling (sauf si skip_throttle = True pour messages urgents)
        if not skip_throttle:
            message_type = json.loads(message).get("type", "unknown")
            now = datetime.now()

            # Vérifier si on peut envoyer (throttle par type de message)
            if message_type in self.last_broadcast:
                elapsed = now - self.last_broadcast[message_type]
                if elapsed < self.min_broadcast_interval:
                    self.stats["throttled_messages"] += 1
                    logger.debug(f"⏸️ Message {message_type} throttled")
                    return

            self.last_broadcast[message_type] = now

        # Broadcast async à tous les clients
        disconnected_clients = []
        tasks = []

        for client_id, websocket in self.active_connections.items():
            async def send_to_client(cid, ws, msg):
                try:
                    await ws.send_text(msg)
                    self.stats["total_messages"] += 1
                except Exception as e:
                    logger.warning(f"⚠️ Connexion perdue pour {cid}: {e}")
                    disconnected_clients.append(cid)
                    self.stats["failed_sends"] += 1

            tasks.append(send_to_client(client_id, websocket, message))

        # Exécuter tous les envois en parallèle
        await asyncio.gather(*tasks, return_exceptions=True)

        # Nettoyer les clients déconnectés
        for client_id in disconnected_clients:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

    async def broadcast_chunked(self, large_data: dict, chunk_size: int = 5000):
        """
        Envoie de gros messages en chunks pour éviter surcharge
        Utile pour debug logs, historique, etc.
        """
        data_str = json.dumps(large_data)

        if len(data_str) < chunk_size:
            await self.broadcast(data_str)
            return

        # Découper en chunks
        chunks = [data_str[i:i+chunk_size] for i in range(0, len(data_str), chunk_size)]
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_message = {
                "type": "chunked_data",
                "chunk_index": i,
                "total_chunks": total_chunks,
                "data": chunk
            }
            await self.broadcast(chunk_message)
            await asyncio.sleep(0.05)  # Petit délai entre chunks

    def add_to_conversation_history(self, client_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []

        # Limiter l'historique à 50 messages pour éviter surcharge mémoire
        if len(self.conversation_history[client_id]) >= 50:
            self.conversation_history[client_id].pop(0)

        self.conversation_history[client_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_conversation_history(self, client_id: str) -> List[Dict]:
        """Get the conversation history for a client"""
        return self.conversation_history.get(client_id, [])

    def clear_conversation_history(self, client_id: str):
        """Clear the conversation history for a client"""
        if client_id in self.conversation_history:
            self.conversation_history[client_id] = []

    def update_system_message(self, client_id: str, content: str):
        """Update or add system message in conversation history"""
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []

        history = self.conversation_history[client_id]

        # Find and update existing system message, or add new one
        system_msg_found = False
        for msg in history:
            if msg.get("role") == "system":
                msg["content"] = content
                msg["timestamp"] = datetime.now().isoformat()
                system_msg_found = True
                break

        if not system_msg_found:
            # Add at the beginning
            history.insert(0, {
                "role": "system",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

    def get_stats(self) -> Dict:
        """Retourne les statistiques du WebSocket Manager"""
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "connection_ids": list(self.active_connections.keys())
        }

    def set_streaming_state(self, client_id: str, is_streaming: bool):
        """Set the streaming state for a client"""
        self.streaming_state[client_id] = is_streaming

    def get_streaming_state(self, client_id: str) -> bool:
        """Get the streaming state for a client"""
        return self.streaming_state.get(client_id, False)

    def stop_stream(self, client_id: str):
        """Stop streaming for a client"""
        self.streaming_state[client_id] = False

    def trim_conversation_history(self, client_id: str, max_tokens: int = 4000):
        """Trim conversation history to fit within token limit"""
        if client_id not in self.conversation_history:
            return

        history = self.conversation_history[client_id]
        if not history:
            return

        # Rough estimation: 4 chars per token
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token

        # Keep system message if exists
        system_messages = [msg for msg in history if msg.get("role") == "system"]
        conversation_messages = [msg for msg in history if msg.get("role") != "system"]

        # Calculate current size
        total_chars = sum(len(msg.get("content", "")) for msg in conversation_messages)

        # Remove oldest messages until we're under the limit
        while total_chars > max_chars and len(conversation_messages) > 2:
            # Remove the oldest user-assistant pair
            if len(conversation_messages) >= 2:
                removed_user = conversation_messages.pop(0)
                removed_assistant = conversation_messages.pop(0)
                total_chars -= len(removed_user.get("content", ""))
                total_chars -= len(removed_assistant.get("content", ""))
            else:
                break

        # Reconstruct history with system messages first
        self.conversation_history[client_id] = system_messages + conversation_messages


# Global singleton instance
_ws_manager_instance = None

def get_websocket_manager() -> OptimizedWebSocketManager:
    """Get the global WebSocket manager instance"""
    global _ws_manager_instance
    if _ws_manager_instance is None:
        _ws_manager_instance = OptimizedWebSocketManager()
    return _ws_manager_instance
