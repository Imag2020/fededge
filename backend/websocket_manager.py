from fastapi import WebSocket
from typing import Dict, List
import json
import logging

# Logger sécurisé pour éviter les erreurs I/O operation on closed file
def safe_log(message, level="info"):
    """Log sécurisé qui évite les erreurs I/O operation on closed file"""
    try:
        logger = logging.getLogger("websocket_manager")
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    except:
        pass  # Éviter les crashs de logging

class WebSocketManager:
    def __init__(self):
        # Store active connections with client IDs
        self.active_connections: Dict[str, WebSocket] = {}
        # Store conversation history for each client
        self.conversation_history: Dict[str, List[Dict]] = {}
        # Store streaming state for each client
        self.streaming_state: Dict[str, bool] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection and store it"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # Initialize conversation history if not exists
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []
        safe_log(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        # Find and remove the connection
        client_id = None
        for cid, ws in self.active_connections.items():
            if ws == websocket:
                client_id = cid
                break
        
        if client_id:
            del self.active_connections[client_id]
            safe_log(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)
    
    async def broadcast(self, message):
        """Send a message to all connected clients"""
        if self.active_connections:
            # Convert dict to JSON string if needed
            if isinstance(message, dict):
                message = json.dumps(message)
            
            disconnected_clients = []
            for client_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_text(message)
                except:
                    # Connection is broken, mark for removal
                    disconnected_clients.append(client_id)
            
            # Remove disconnected clients
            for client_id in disconnected_clients:
                del self.active_connections[client_id]
    
    def add_to_conversation_history(self, client_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []
        
        self.conversation_history[client_id].append({
            "role": role,
            "content": content
        })
    
    def get_conversation_history(self, client_id: str) -> List[Dict]:
        """Get the conversation history for a client"""
        return self.conversation_history.get(client_id, [])
    
    def clear_conversation_history(self, client_id: str):
        """Clear the conversation history for a client"""
        if client_id in self.conversation_history:
            self.conversation_history[client_id] = []

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

def get_websocket_manager():
    """Get the global WebSocket manager instance"""
    global _ws_manager_instance
    if _ws_manager_instance is None:
        _ws_manager_instance = WebSocketManager()
    return _ws_manager_instance