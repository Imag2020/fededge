import asyncio
import aiohttp
import json
import logging
import threading  # FIX: requis pour le streaming llama.cpp
from typing import Dict, Optional, Any, List, AsyncIterator
from abc import ABC, abstractmethod



from .config_manager import LLMConfig, LLMType, config_manager

logger = logging.getLogger(__name__)


# OpenAI v1
try:
    from openai import AsyncOpenAI
    from openai import APIError, APITimeoutError  # disponibles dans le SDK v1+
except Exception:
    AsyncOpenAI = None
    APIError = Exception
    APITimeoutError = TimeoutError


# --- Helpers: extraction de texte depuis tout type de chunk ---
def _chunk_to_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, bytes):
        try:
            return chunk.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    if isinstance(chunk, dict):
        # Champs fréquents
        for k in ("delta", "text", "content"):
            v = chunk.get(k)
            if isinstance(v, str):
                return v
        # OpenAI-like
        ch = chunk.get("choices")
        if isinstance(ch, list) and ch and isinstance(ch[0], dict):
            delta = ch[0].get("delta") or ch[0].get("message") or {}
            if isinstance(delta, dict):
                return delta.get("content", "")
        try:
            return json.dumps(chunk, ensure_ascii=False)
        except Exception:
            return ""
    return str(chunk)


def _convert_native_tool_calls_to_text(tool_calls: List[Dict], thinking: str = "") -> str:
    """
    Convertit les tool_calls natifs (format OpenAI function calling) en format texte
    avec balises <tool>...</tool> attendu par l'agent executor.

    Args:
        tool_calls: Liste de tool_calls au format OpenAI:
            [{"id": "call_xxx", "type": "function", "function": {"name": "...", "arguments": "..."}}]
        thinking: Texte de raisonnement optionnel (pour modèles de raisonnement comme gpt-oss)

    Returns:
        Texte formaté avec balises <tool>...</tool>, précédé du thinking si présent
    """
    if not tool_calls:
        return thinking if thinking else ""

    result_parts = []

    # Ajouter le thinking en premier si présent
    if thinking:
        result_parts.append(thinking)

    # Convertir chaque tool_call au format <tool>name: args</tool>
    for tool_call in tool_calls:
        func = tool_call.get("function", {})
        func_name = func.get("name", "unknown")
        func_args_raw = func.get("arguments", "")

        # Parser les arguments (peuvent être string JSON ou dict)
        if isinstance(func_args_raw, str):
            try:
                func_args = json.loads(func_args_raw) if func_args_raw else {}
            except Exception:
                # Si pas du JSON valide, traiter comme string brut
                func_args = {"query": func_args_raw} if func_args_raw else {}
        elif isinstance(func_args_raw, dict):
            func_args = func_args_raw
        else:
            func_args = {}

        # Formater selon le type d'arguments
        if not func_args:
            # Pas d'arguments: format bare
            tool_text = f"<tool>{func_name}</tool>"
        elif len(func_args) == 1 and "query" in func_args:
            # Un seul argument "query": format texte simple
            tool_text = f"<tool>{func_name}: {func_args['query']}</tool>"
        elif len(func_args) == 1:
            # Un seul argument avec autre nom: utiliser sa valeur directement
            arg_value = list(func_args.values())[0]
            tool_text = f"<tool>{func_name}: {arg_value}</tool>"
        else:
            # Multiples arguments: format JSON
            tool_text = f"<tool>{json.dumps({'name': func_name, 'args': func_args}, ensure_ascii=False)}</tool>"

        result_parts.append(tool_text)
        logger.info(f"🔧 Converted native tool_call to: {tool_text}")

    return "\n".join(result_parts)

# --- Helper: pseudo-stream si backend ne stream pas réellement ---
async def _pseudo_stream(text: str, *, piece_chars: int = 24, delay_s: float = 0.02, cancel_event: Optional[asyncio.Event] = None) -> AsyncIterator[str]:
    i = 0
    n = len(text)
    while i < n:
        if cancel_event is not None and cancel_event.is_set():
            break
        j = min(n, i + piece_chars)
        yield text[i:j]
        i = j
        if delay_s > 0:
            try:
                await asyncio.sleep(delay_s)
            except asyncio.CancelledError:
                break



class BaseLLMClient(ABC):
    """Classe de base pour tous les clients LLM"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.id = config.id
        self.name = config.name

    @abstractmethod
    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        """Génère une réponse à partir d'un prompt"""
        raise NotImplementedError

    # FIX: fournir un fallback non-abstract pour éviter l'erreur d’instanciation
    async def generate_response_stream(
        self,
        prompt: str,
        messages: List[Dict] = None,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Fallback de streaming: yield le texte complet en un seul chunk."""
        text = await self.generate_response(prompt, messages=messages, **kwargs)
        # on découpe éventuellement en petits morceaux pour un effet "stream"
        chunk = 1024
        for i in range(0, len(text), chunk):
            yield text[i:i+chunk]

    @abstractmethod
    async def test_connection(self) -> bool:
        """Teste la connexion au service LLM"""
        raise NotImplementedError


class LlamaCppServerClient(BaseLLMClient):
    """
    Client pour serveur llama.cpp (OpenAI-compatible)

    Utilise le serveur llama.cpp lancé avec la commande native:
    ./llama-server --model path/to/model.gguf --port 9001 --ctx-size 16192 --parallel 2 --cont-batching

    Avantages:
    - Thread-safe: Le serveur gère la concurrence nativement
    - Continuous batching: Requêtes parallèles efficaces avec KV cache partagé
    - OpenAI API compatible: Fonctionne avec DSPy et OpenAI SDK
    - Pas de dépendance llama_cpp_python: API HTTP uniquement
    - Optimisé pour edge: Gestion mémoire et performance optimales
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # URL du serveur llama.cpp (format: http://localhost:8080)
        self.base_url = (config.url or "http://localhost:9001").rstrip("/")
        self.api_base = f"{self.base_url}/v1"

        # Créer client OpenAI qui pointe vers le serveur llama.cpp
        if AsyncOpenAI:
            self.client = AsyncOpenAI(
                api_key="dummy",  # Pas besoin de clé pour serveur local
                base_url=self.api_base,
                timeout=config.timeout or 60.0
            )
        else:
            raise ImportError("AsyncOpenAI not available. Install: pip install openai")

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        """Génère une réponse via le serveur llama.cpp avec support conversation ID et optimisation KV cache"""
        # Si pas de messages fournis, créer un message user simple
        if not messages:
            messages = [{"role": "user", "content": prompt}]
        else:
            # Si messages fournis ET prompt non vide, ajouter le prompt comme dernier message user
            if prompt and prompt.strip() and messages[-1].get("content") != prompt:
                messages = messages + [{"role": "user", "content": prompt}]
            # Sinon, utiliser les messages tels quels (le prompt est déjà dans l'historique)

        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        temperature = kwargs.get('temperature', self.config.temperature)
        conversation_id = kwargs.get('conversation_id')  # ID de conversation pour KV cache

        # KV CACHE pour llamacpp-server:
        # Le conversation_id permet à llama.cpp de réutiliser le KV cache pour les tokens identiques
        # On envoie toujours l'historique complet pour éviter la désynchronisation
        # (notre architecture 2-appels-par-question rend l'optimisation agressive trop complexe)
        if conversation_id:
            logger.debug(f"📦 [KV Cache] Using conversation_id={conversation_id} (full history: {len(messages)} messages)")

        try:
            # Préparer les paramètres de requête
            request_params = {
                "model": "local-model",  # Le nom n'importe pas, le serveur n'a qu'un modèle
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }

            # Ajouter l'ID de conversation si fourni (optimise KV cache dans llama.cpp)
            if conversation_id:
                request_params["user"] = conversation_id  # OpenAI API utilise "user" pour identifier les sessions

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"Model: {request_params['model']}")
            logger.info(f"Messages context: {len(messages)} message(s)")
            for i, msg in enumerate(messages[-3:]):  # Derniers 3 messages
                logger.info(f"  [{i}] {msg.get('role', '?')}: {msg.get('content', '')}...")
            logger.info(f"Conversation ID: {conversation_id or 'none'}")
            logger.info("=" * 80)

            response = await self.client.chat.completions.create(**request_params)

            message = response.choices[0].message
            content = message.content or ""

            # GESTION DES FUNCTION CALLS (pour modèles qui utilisent OpenAI function calling)
            # Si le modèle retourne un tool_call au lieu de texte, convertir en format <tool>...</tool>
            if not content and hasattr(message, 'tool_calls') and message.tool_calls:
                logger.warning(f"⚠️ LlamaCpp model returned function calls instead of text - tool_calls: {message.tool_calls}")

                # Convertir les tool_calls SDK OpenAI au format dict attendu
                tool_calls_dict = []
                for tc in message.tool_calls:
                    tool_calls_dict.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

                # Convertir au format <tool>...</tool>
                content = _convert_native_tool_calls_to_text(tool_calls_dict, "")
                logger.info(f"📝 Conversion tool_calls natifs -> format <tool>: {content}")

            # Log de la réponse reçue
            logger.info("=" * 80)
            logger.info(f"===========> RETOUR LLM [{self.config.name}]")
            logger.info(f"Response length: {len(content)} chars")
            logger.info(f"Content: {content[:500]}...")
            if len(content) > 500:
                logger.info(f"... [truncated, total: {len(content)} chars]")
            logger.info("=" * 80)

            return content

        except Exception as e:
            logger.error(f"Error with llama.cpp server: {e}")
            raise

    async def generate_response_stream(
        self,
        prompt: str,
        messages: List[Dict] = None,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Génère une réponse en streaming avec support conversation ID et optimisation KV cache"""
        # Si pas de messages fournis, créer un message user simple
        if not messages:
            messages = [{"role": "user", "content": prompt}]
        else:
            # Si messages fournis ET prompt non vide, ajouter le prompt comme dernier message user
            # (sauf si déjà dans le dernier message)
            if prompt and prompt.strip() and messages[-1].get("content") != prompt:
                messages = messages + [{"role": "user", "content": prompt}]
            # Sinon, utiliser les messages tels quels (le prompt est déjà dans l'historique)

        tokens = max_tokens or self.config.max_tokens
        temperature = kwargs.get('temperature', self.config.temperature)
        conversation_id = kwargs.get('conversation_id')  # ID de conversation pour KV cache

        # KV CACHE pour llamacpp-server:
        # Le conversation_id permet à llama.cpp de réutiliser le KV cache pour les tokens identiques
        # On envoie toujours l'historique complet pour éviter la désynchronisation
        # (notre architecture 2-appels-par-question rend l'optimisation agressive trop complexe)
        if conversation_id:
            logger.debug(f"📦 [KV Cache STREAM] Using conversation_id={conversation_id} (full history: {len(messages)} messages)")

        try:
            # Préparer les paramètres de requête
            request_params = {
                "model": "local-model",
                "messages": messages,
                "max_tokens": tokens,
                "temperature": temperature,
                "stream": True
            }

            # Ajouter l'ID de conversation si fourni (optimise KV cache dans llama.cpp)
            if conversation_id:
                request_params["user"] = conversation_id

            # Log du prompt envoyé (streaming)
            logger.info("=" * 80)
            logger.info(f"===========> Ollama PROMPT ENVOYÉ (STREAMING) [{self.config.name}]")
            logger.info(f"Model: {request_params['model']}")
            logger.info(f"Messages context: {len(messages)} message(s)")
            logger.info(f"Messages : {messages}")
            logger.info(f"Conversation ID: {conversation_id or 'none'}")
            logger.info("=" * 80)

            stream = await self.client.chat.completions.create(**request_params)

            accumulated_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_response += content
                    yield content

            # Log de la réponse complète
            logger.info("=" * 80)
            logger.info(f"===========> RETOUR LLM (STREAMING) [{self.config.name}]")
            logger.info(f"Response length: {len(accumulated_response)} chars")
            logger.info(f"Content: {accumulated_response[:500]}...")
            if len(accumulated_response) > 500:
                logger.info(f"... [truncated, total: {len(accumulated_response)} chars]")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Streaming error with llama.cpp server: {e}")
            raise

    def test_connection(self) -> bool:
        """Teste la connexion au serveur llama.cpp"""
        import requests
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class OllamaClient(BaseLLMClient):
    """Client pour Ollama (local)"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        base = (config.url or "").rstrip("/")
        self.chat_endpoint = f"{base}/api/chat"
        self.generate_endpoint = f"{base}/api/generate"

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        try:
            chat_messages = []
            if messages:
                chat_messages = messages
            if prompt !="":
                chat_messages.append({"role": "user", "content": prompt})

            
            payload = {
                "model": self.config.model,
                "messages": chat_messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                },
                # Désactiver le mode function calling natif d'Ollama pour forcer le texte libre
                # Le modèle doit générer des balises <tool>...</tool> au lieu de tool_calls JSON
                "tools": []
            }

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> Ollama PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"🎯 URL: {self.chat_endpoint}")
            logger.info(f"🎯 Model: {self.config.model}")
            logger.info(f"⏱️  Timeout: {self.config.timeout}s")
            logger.info(f"📦 PAYLOAD:")
            logger.info(f"   - model: {payload['model']}")
            logger.info(f"   - messages: {len(chat_messages)} messages")
            for i, msg in enumerate(chat_messages):
                logger.info(f"     [{i}] {msg.get('role', '?')}: {msg.get('content', '')[:100]}")
            logger.info(f"   - options: {payload['options']}")
            if messages and len(messages) > 0:
                logger.info(f"📜 Messages context: {len(messages)} message(s)")
                for i, msg in enumerate(messages):  # Derniers 3 messages
                    logger.info(f"  [{i}] {msg.get('role', '?')}: {msg.get('content', '')}")
            logger.info(f"💬 User prompt: *{prompt}*")
            logger.info("=" * 80)

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.post(self.chat_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Log du JSON brut reçu
                        logger.info(f"📥 Raw JSON response: {result}")

                        # Format attendu: { "message": {"role":"assistant","content":"..."} }
                        message_obj = result.get("message") or {}
                        msg = message_obj.get("content", "")

                        # GESTION DES FUNCTION CALLS (pour modèles comme gpt-oss qui supportent OpenAI function calling)
                        # Si le modèle retourne un tool_call au lieu de texte, convertir en format <tool>...</tool>
                        if not msg and "tool_calls" in message_obj:
                            tool_calls = message_obj.get("tool_calls", [])
                            thinking = message_obj.get("thinking", "")

                            logger.warning(f"⚠️ Modèle retourne function call au lieu de texte - tool_calls: {tool_calls}")

                            # Convertir les tool_calls natifs en format <tool>...</tool>
                            msg = _convert_native_tool_calls_to_text(tool_calls, thinking)
                            logger.info(f"📝 Conversion tool_calls natifs -> format <tool>: {msg}")

                        # Log de la réponse reçue
                        logger.info("=" * 80)
                        logger.info(f"Ollama ===========> RETOUR LLM [{self.config.name}]")
                        logger.info(f"Response length: {len(msg)} chars")
                        logger.info(f"Content: *{msg}*")
                        logger.info(f"Done: {result.get('done')}")
                        logger.info(f"Duration: {result.get('total_duration', 0)/1e9:.1f}s" if 'total_duration' in result else "N/A")
                        logger.info("=" * 80)

                        return msg or ""
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama error {response.status}: {error_text}")
                        return f"Error: Ollama request failed with status {response.status}"

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to Ollama at {self.config.url}")
            return "Error: Timeout connecting to Ollama"
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Ollama: {e}")
            return f"Error: Could not connect to Ollama at {self.config.url}"
        except Exception as e:
            logger.error(f"Unexpected error with Ollama: {e}")
            return f"Error: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.config.url.rstrip('/')}/api/tags") as response:
                    return response.status == 200
        except Exception:
            return False

    # dans class OllamaClient(BaseLLMClient):

    async def generate_response_stream(
        self,
        prompt: str,
        messages: List[Dict] = None,
        max_tokens: int = None,
        *,
        cancel_event: Optional[asyncio.Event] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming réel via /api/chat (JSONL multi-lignes).
        Accumule un buffer et découpe par '\n' pour parser chaque event JSON,
        sinon aiohttp peut livrer des fragments partiels.
        """
        try:
            chat_messages = []
            if messages:
                chat_messages.extend(messages)
            if prompt and prompt.strip():
                chat_messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.config.model,
                "messages": chat_messages,
                "stream": True,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": max_tokens or self.config.max_tokens,
                },
                # Désactiver le mode function calling natif d'Ollama pour forcer le texte libre
                # Le modèle doit générer des balises <tool>...</tool> au lieu de tool_calls JSON
                "tools": []
            }

            # Log du prompt envoyé (streaming)
            logger.info("=" * 80)
            logger.info(f"🌊 ===========> OllamaClient STREAM [{self.config.name}]")
            logger.info(f"🎯 URL: {self.chat_endpoint}")
            logger.info(f"🎯 Model: {self.config.model}")
            logger.info(f"⏱️  Timeout: {self.config.timeout}s")
            if messages and len(messages) > 0:
                logger.info(f"📜 Messages context: {len(messages)} message(s)")
                for i, msg in enumerate(messages[-3:]):  # Derniers 3 messages
                    logger.info(f"  [{i}] {msg.get('role', '?')}: {msg.get('content', '')[:100]}")
            if prompt:
                logger.info(f"💬 User prompt: {prompt[:500]}...")
            logger.info("=" * 80)

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.chat_endpoint, json=payload) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"Ollama stream error {resp.status}: {err}")
                        return

                    buf = ""
                    yielded_any_content = False  # Track if we ever yield content
                    accumulated_response = ""  # Pour logger la réponse complète
                    accumulated_thinking = ""  # Pour accumuler le thinking
                    accumulated_tool_calls = []  # Pour accumuler les tool_calls

                    async for chunk in resp.content.iter_chunked(1024):
                        if cancel_event is not None and cancel_event.is_set():
                            return
                        if not chunk:
                            continue
                        buf += chunk.decode("utf-8", errors="ignore")

                        # Traite toutes les lignes complètes disponibles
                        while True:
                            nl = buf.find("\n")
                            if nl == -1:
                                break
                            line = buf[:nl].strip()
                            buf = buf[nl + 1 :]
                            if not line:
                                continue
                            try:
                                j = json.loads(line)
                            except Exception:
                                # ligne incomplète/imparsable -> on ignore
                                continue

                            # format typique: {"message":{"content":"..."}, "done":false}
                            # Support pour modèles de raisonnement (DeepSeek R1, gpt-oss):
                            # Ces modèles envoient d'abord des "thinking" tokens, puis "content"
                            msg = j.get("message") or {}
                            content = msg.get("content") or ""
                            thinking = msg.get("thinking") or ""
                            tool_calls = msg.get("tool_calls", [])

                            # Accumuler thinking et tool_calls
                            if thinking:
                                accumulated_thinking += thinking
                            if tool_calls:
                                # Fusionner les tool_calls (éviter les doublons)
                                for tc in tool_calls:
                                    if tc not in accumulated_tool_calls:
                                        accumulated_tool_calls.append(tc)

                            # Yield content tokens (reasoning models separate thinking from content)
                            if content:
                                yielded_any_content = True
                                accumulated_response += content  # Accumulate for final logging
                                yield content
                            # Note: thinking tokens are internal reasoning and not yielded to user
                            # This is by design for reasoning models like gpt-oss/DeepSeek R1

                            if j.get("done"):
                                # Si pas de content mais des tool_calls, convertir et yielder
                                if not yielded_any_content and accumulated_tool_calls:
                                    logger.warning(f"⚠️ Ollama stream: tool_calls détectés sans content")
                                    tool_text = _convert_native_tool_calls_to_text(
                                        accumulated_tool_calls,
                                        accumulated_thinking
                                    )
                                    if tool_text:
                                        accumulated_response = tool_text
                                        yield tool_text
                                        yielded_any_content = True
                                elif not yielded_any_content:
                                    logger.warning(f"⚠️ Ollama stream completed with 0 content tokens (thinking-only response from reasoning model)")

                                # Log accumulated response at end of stream
                                logger.info("=" * 80)
                                logger.info(f"===========> RETOUR LLM (STREAMING) [{self.config.name}]")
                                logger.info(f"Response length: {len(accumulated_response)} chars")
                                logger.info(f"Content: {accumulated_response[:500]}...")
                                if len(accumulated_response) > 500:
                                    logger.info(f"... [truncated, total: {len(accumulated_response)} chars]")
                                logger.info("=" * 80)
                                return

                    # Fin de stream: flush le reste si c’est une dernière ligne valable
                    tail = buf.strip()
                    if tail:
                        try:
                            j = json.loads(tail)
                            msg = j.get("message") or {}
                            delta = msg.get("content") or ""
                            if delta:
                                yield delta
                        except Exception:
                            pass

        except asyncio.TimeoutError:
            logger.error(f"Timeout streaming from Ollama at {self.config.url}")
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error (stream): {e}")
        except Exception as e:
            logger.error(f"Unexpected Ollama stream error: {e}", exc_info=True)





class OpenAIClient(BaseLLMClient):
    """Client pour OpenAI"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if AsyncOpenAI is None:
            raise ImportError("openai SDK v1+ non disponible")
        # Timeout via with_options
        base_url = config.url if (config.url and config.url != "https://api.openai.com/v1") else None
        client = AsyncOpenAI(api_key=config.get_effective_api_key(), base_url=base_url)
        self.client = client.with_options(timeout=self.config.timeout)

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        try:
            chat_messages = []
            if messages:
                chat_messages.extend(messages)
            chat_messages.append({"role": "user", "content": prompt})

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"Model: {self.config.model}")
            if messages and len(messages) > 0:
                logger.info(f"Messages context: {len(messages)} message(s)")
                for i, msg in enumerate(messages[-3:]):  # Derniers 3 messages
                    logger.info(f"  [{i}] {msg.get('role', '?')}: {msg.get('content', '')}...")
            logger.info(f"User prompt: {prompt[:500]}...")
            logger.info("=" * 80)

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=chat_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            message = response.choices[0].message
            content = (message.content or "").strip()

            # GESTION DES FUNCTION CALLS (pour modèles qui utilisent OpenAI function calling)
            # Si le modèle retourne un tool_call au lieu de texte, convertir en format <tool>...</tool>
            if not content and hasattr(message, 'tool_calls') and message.tool_calls:
                logger.warning(f"⚠️ OpenAI model returned function calls instead of text - tool_calls: {message.tool_calls}")

                # Convertir les tool_calls SDK OpenAI au format dict attendu
                tool_calls_dict = []
                for tc in message.tool_calls:
                    tool_calls_dict.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

                # Convertir au format <tool>...</tool>
                content = _convert_native_tool_calls_to_text(tool_calls_dict, "")
                logger.info(f"📝 Conversion tool_calls natifs -> format <tool>: {content}")

            # Log de la réponse reçue
            logger.info("=" * 80)
            logger.info(f"===========> RETOUR LLM [{self.config.name}]")
            logger.info(f"Response length: {len(content)} chars")
            logger.info(f"Content: {content[:500]}...")
            if len(content) > 500:
                logger.info(f"... [truncated, total: {len(content)} chars]")
            logger.info("=" * 80)

            return content
        except APITimeoutError:
            logger.error("OpenAI API timeout")
            return "Error: OpenAI API timeout"
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error: OpenAI API error - {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            _ = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False


class ClaudeClient(BaseLLMClient):
    """Client pour Claude (Anthropic)"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = (config.url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
        self.headers = {
            "x-api-key": config.get_effective_api_key(),
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

    @staticmethod
    def _to_claude_messages(messages: List[Dict], prompt: str) -> List[Dict]:
        # Anthropic Messages API: contenu sous forme de blocs
        out = []
        if messages:
            for msg in messages:
                role = "assistant" if msg.get("role") == "assistant" else "user"
                out.append({
                    "role": role,
                    "content": [{"type": "text", "text": str(msg.get("content", ""))}]
                })
        out.append({"role": "user", "content": [{"type": "text", "text": str(prompt)}]})
        return out

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        try:
            claude_messages = self._to_claude_messages(messages, prompt)
            payload = {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": claude_messages
            }

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"Model: {self.config.model}")
            if messages and len(messages) > 0:
                logger.info(f"Messages context: {len(messages)} message(s)")
            logger.info(f"User prompt: {prompt[:500]}...")
            logger.info("=" * 80)

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        # result["content"] = [ { "type":"text","text":"..." }, ... ]
                        content = result.get("content") or []
                        if content and isinstance(content, list):
                            first = content[0]
                            if isinstance(first, dict) and first.get("type") == "text":
                                text_content = first.get("text", "")

                                # Log de la réponse reçue
                                logger.info("=" * 80)
                                logger.info(f"===========> RETOUR LLM [{self.config.name}]")
                                logger.info(f"Response length: {len(text_content)} chars")
                                logger.info(f"Content: {text_content[:500]}...")
                                if len(text_content) > 500:
                                    logger.info(f"... [truncated, total: {len(text_content)} chars]")
                                logger.info("=" * 80)

                                return text_content
                        logger.error(f"Claude: unexpected response format: {result}")
                        return "Error: Unexpected Claude response format"
                    else:
                        error_text = await response.text()
                        logger.error(f"Claude error {response.status}: {error_text}")
                        return f"Error: Claude request failed with status {response.status}"

        except asyncio.TimeoutError:
            logger.error("Timeout connecting to Claude")
            return "Error: Timeout connecting to Claude"
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Claude: {e}")
            return f"Error: Could not connect to Claude"
        except Exception as e:
            logger.error(f"Unexpected error with Claude: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            payload = {
                "model": self.config.model,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": [{"type": "text", "text": "test"}]}]
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    return response.status == 200
        except Exception:
            return False


class GeminiClient(BaseLLMClient):
    """Client pour Google Gemini avec format spécifique"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.headers = {"Content-Type": "application/json"}
        effective_api_key = config.get_effective_api_key()
        base_url = (config.url or "").strip()
        if not base_url.startswith('https://'):
            base_url = f"https://{base_url}" if base_url else "https://generativelanguage.googleapis.com"
        if 'v1beta' not in base_url and 'v1' not in base_url:
            base_url = f"{base_url.rstrip('/')}/v1beta"
        self.api_url = f"{base_url}/models/{config.model}:generateContent?key={effective_api_key}"

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        try:
            contents = []
            if messages:
                for msg in messages:
                    role = "user" if msg.get("role") == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": str(msg.get("content", ""))}]})
            contents.append({"role": "user", "parts": [{"text": str(prompt)}]})

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": self.config.temperature,
                    "maxOutputTokens": self.config.max_tokens,
                    "topP": 0.8,
                    "topK": 10
                }
            }

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"Model: {self.config.model}")
            if messages and len(messages) > 0:
                logger.info(f"Messages context: {len(messages)} message(s)")
            logger.info(f"User prompt: {prompt[:500]}...")
            logger.info("=" * 80)

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        cand = (result.get("candidates") or [])
                        if cand and cand[0].get("content") and cand[0]["content"].get("parts"):
                            text_content = cand[0]["content"]["parts"][0].get("text", "") or ""

                            # Log de la réponse reçue
                            logger.info("=" * 80)
                            logger.info(f"===========> RETOUR LLM [{self.config.name}]")
                            logger.info(f"Response length: {len(text_content)} chars")
                            logger.info(f"Content: {text_content[:500]}...")
                            if len(text_content) > 500:
                                logger.info(f"... [truncated, total: {len(text_content)} chars]")
                            logger.info("=" * 80)

                            return text_content
                        logger.error(f"Format de réponse Gemini inattendu: {result}")
                        return "Erreur: Format de réponse Gemini inattendu"
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini error {response.status}: {error_text}")
                        logger.error(f"Gemini URL utilisée: {self.api_url}")
                        logger.error(f"Gemini payload: {payload}")
                        return f"Error: Gemini request failed with status {response.status}: {error_text}"

        except asyncio.TimeoutError:
            logger.error("Timeout connecting to Gemini")
            return "Error: Timeout connecting to Gemini"
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Gemini: {e}")
            return f"Error: Could not connect to Gemini"
        except Exception as e:
            logger.error(f"Unexpected error with Gemini: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "test"}]}],
                "generationConfig": {"maxOutputTokens": 5}
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    return response.status == 200
        except Exception:
            return False


class GenericAPIClient(BaseLLMClient):
    """Client générique pour les APIs compatibles OpenAI (DeepSeek, Grok, Qwen, etc.)"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.headers = {
            "Authorization": f"Bearer {config.get_effective_api_key()}",
            "Content-Type": "application/json"
        }
        base = (config.url or "").rstrip("/")
        self.api_url = f"{base}/chat/completions" if not base.endswith('/chat/completions') else base

    async def generate_response(self, prompt: str, messages: List[Dict] = None, **kwargs) -> str:
        try:
            chat_messages = []
            if messages:
                chat_messages.extend(messages)
            chat_messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.config.model,
                "messages": chat_messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                **(self.config.extra_params or {})  # FIX: gère None
            }

            # Log du prompt envoyé
            logger.info("=" * 80)
            logger.info(f"===========> PROMPT ENVOYÉ [{self.config.name}]")
            logger.info(f"Model: {self.config.model}")
            if messages and len(messages) > 0:
                logger.info(f"Messages context: {len(messages)} message(s)")
                for i, msg in enumerate(messages[-3:]):  # Derniers 3 messages
                    logger.info(f"  [{i}] {msg.get('role', '?')}: {msg.get('content', '')[:100]}...")
            logger.info(f"User prompt: {prompt[:500]}...")
            logger.info("=" * 80)

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        message_obj = result["choices"][0]["message"]
                        content = message_obj.get("content", "")

                        # GESTION DES FUNCTION CALLS (pour modèles compatibles OpenAI function calling)
                        # Si le modèle retourne un tool_call au lieu de texte, convertir en format <tool>...</tool>
                        if not content and "tool_calls" in message_obj:
                            tool_calls = message_obj.get("tool_calls", [])
                            logger.warning(f"⚠️ Generic API model returned function calls instead of text - tool_calls: {tool_calls}")

                            # Convertir au format <tool>...</tool>
                            content = _convert_native_tool_calls_to_text(tool_calls, "")
                            logger.info(f"📝 Conversion tool_calls natifs -> format <tool>: {content}")

                        # Log de la réponse reçue
                        logger.info("=" * 80)
                        logger.info(f"===========> RETOUR LLM [{self.config.name}]")
                        logger.info(f"Response length: {len(content)} chars")
                        logger.info(f"Content: {content[:500]}...")
                        if len(content) > 500:
                            logger.info(f"... [truncated, total: {len(content)} chars]")
                        logger.info("=" * 80)

                        return content
                    else:
                        error_text = await response.text()
                        logger.error(f"{getattr(self.config.type,'value',self.config.type)} error {response.status}: {error_text}")
                        return f"Error: request failed with status {response.status}"

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to {getattr(self.config.type,'value',self.config.type)}")
            return "Error: Timeout"
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to {getattr(self.config.type,'value',self.config.type)}: {e}")
            return "Error: Could not connect"
        except Exception as e:
            logger.error(f"Unexpected error with {getattr(self.config.type,'value',self.config.type)}: {e}", exc_info=True)
            return f"Error: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            payload = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    return response.status == 200
        except Exception:
            return False


class LLMPool:
    """Gestionnaire du pool de modèles LLM"""

    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {}
        self.by_name: Dict[str, str] = {}     # FIX: index name -> id
        self.default_id: Optional[str] = None # FIX: id du LLM par défaut
        self._load_clients()

    def _reindex(self):
        """Rebâtit l’index par nom et le défaut."""
        self.by_name.clear()
        for cid, client in self.clients.items():
            if client.name:
                self.by_name[client.name.lower()] = cid
        default_llm = config_manager.get_default_llm()
        self.default_id = default_llm.id if default_llm else None

    def _load_clients(self):
        """Charge tous les clients LLM depuis la configuration"""
        self.clients.clear()
        for llm_config in config_manager.get_active_llms():
            client = self._create_client(llm_config)
            if client:
                self.clients[llm_config.id] = client
                logger.info(f"Client LLM chargé: {llm_config.name} ({llm_config.type.value})")
        self._reindex()  # FIX: construit by_name + default_id

    def _create_client(self, config: LLMConfig) -> Optional[BaseLLMClient]:
        """Crée un client LLM basé sur le type"""
        try:
            if config.type == LLMType.LLAMACPP:
                # DEPRECATED: Direct llama_cpp_python binding no longer supported
                logger.warning(f"LLMType.LLAMACPP is deprecated. Use LLAMACPP_SERVER instead for {config.name}")
                # Fallback to server client
                return LlamaCppServerClient(config)
            elif config.type == LLMType.LLAMACPP_SERVER:
                return LlamaCppServerClient(config)
            elif config.type == LLMType.OLLAMA:
                return OllamaClient(config)
            elif config.type == LLMType.OPENAI:
                return OpenAIClient(config)
            elif config.type == LLMType.CLAUDE:
                return ClaudeClient(config)
            elif config.type == LLMType.GEMINI:
                return GeminiClient(config)
            elif config.type in [LLMType.GROK, LLMType.DEEPSEEK, LLMType.KIMI, LLMType.QWEN]:
                return GenericAPIClient(config)
            else:
                logger.error(f"Type LLM non supporté: {config.type}")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la création du client {config.name}: {e}", exc_info=True)
            return None

    def reload_clients(self):
        """Recharge tous les clients depuis la configuration"""
        logger.info("Rechargement du pool LLM")
        # D'abord recharger le config_manager depuis le fichier JSON
        config_manager.reload_config()
        # Ensuite recharger les clients LLM
        self._load_clients()

    def get_client(self, llm_id: Optional[str] = None, name: Optional[str] = None) -> BaseLLMClient:
        """
        Récupère un client par id ou par name. Fallback sur défaut.
        (Accepte 'name' pour compatibilité avec l’appelant.)
        """
        if llm_id and llm_id in self.clients:
            return self.clients[llm_id]

        if name:
            cid = self.by_name.get(name.lower())
            if cid and cid in self.clients:
                return self.clients[cid]

        if self.default_id and self.default_id in self.clients:
            return self.clients[self.default_id]

        # dernier fallback: premier client disponible
        if self.clients:
            return next(iter(self.clients.values()))

        raise RuntimeError("Aucun client LLM disponible dans le pool.")

    def get_default_client(self) -> Optional[BaseLLMClient]:
        """Récupère le client LLM par défaut"""
        if self.default_id:
            return self.clients.get(self.default_id)
        default_llm = config_manager.get_default_llm()
        if default_llm:
            return self.clients.get(default_llm.id)
        return None

    def get_all_clients(self) -> Dict[str, BaseLLMClient]:
        """Récupère tous les clients"""
        return self.clients.copy()

    def list_clients(self) -> List[Dict[str, str]]:
        """Liste tous les clients avec leurs infos (pratique pour affichage)"""
        clients_list = []
        for llm_id, client in self.clients.items():
            llm_config = config_manager.get_llm(llm_id)
            clients_list.append({
                "id": llm_id,
                "name": client.name,
                "type": llm_config.type.value if llm_config else "unknown",
                "is_default": llm_config.is_default if llm_config else False,
                "is_active": llm_config.is_active if llm_config else True
            })
        return clients_list

    def set_default(self, llm_id: str) -> bool:
        """Change le LLM par défaut et met à jour le pool"""
        success = config_manager.set_default_llm(llm_id)
        if success:
            # Mettre à jour le cache du default_id
            self._reindex()
            logger.info(f"LLM par défaut changé pour: {llm_id}")
        return success

    async def test_client(self, llm_id: str) -> bool:
        """Teste la connexion d'un client spécifique"""
        client = self.get_client(llm_id=llm_id)
        if client:
            return await client.test_connection()
        return False

    async def test_all_clients(self) -> Dict[str, bool]:
        """Teste la connexion de tous les clients"""
        results = {}
        for llm_id, client in self.clients.items():
            try:
                results[llm_id] = await client.test_connection()
            except Exception as e:
                logger.error(f"Erreur lors du test de {client.name}: {e}", exc_info=True)
                results[llm_id] = False
        return results

    async def generate_response(
        self,
        prompt: str,
        llm_id: str = None,
        max_tokens: int = None,
        messages: List[Dict] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """Génère une réponse avec un LLM spécifique ou le défaut"""
        try:
            client = self.get_client(llm_id=llm_id) if llm_id else self.get_default_client()
            if not client:
                logger.error("❌ No LLM client available")
                return "Error: No LLM client available"

            # LOG: Identifier quel modèle est utilisé
            logger.info("=" * 80)
            logger.info(f"🤖 [LLM_POOL] Calling LLM:")
            logger.info(f"  - Client ID: {client.config.id}")
            logger.info(f"  - Name: {client.config.name}")
            logger.info(f"  - Type: {client.config.type.value}")
            logger.info(f"  - Model: {client.config.model}")
            logger.info(f"  - URL: {client.config.url}")
            logger.info(f"  - Timeout: {client.config.timeout}s")
            logger.info(f"  - Prompt length: {len(prompt)} chars")
            logger.info(f"  - Messages history: {len(messages) if messages else 0} messages")
            logger.info(f"  - Conversation ID: {conversation_id or 'none'}")
            logger.info("=" * 80)

            return await client.generate_response(prompt, messages, conversation_id=conversation_id)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération de réponse: {e}", exc_info=True)
            return f"Error: {str(e)}"


    async def generate_response_stream(
        self,
        prompt: str,
        messages: List[Dict] = None,
        *,
        llm_id: Optional[str] = None,
        name: Optional[str] = None,
        max_tokens: int = None,
        cancel_event: Optional[asyncio.Event] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        client = self.get_client(llm_id=llm_id, name=name)

        # LOG: Identifier quel modèle est utilisé (STREAM)
        logger.info("=" * 80)
        logger.info(f"🌊 [LLM_POOL] Calling LLM STREAM:")
        logger.info(f"  - Client ID: {client.config.id}")
        logger.info(f"  - Name: {client.config.name}")
        logger.info(f"  - Type: {client.config.type.value}")
        logger.info(f"  - Model: {client.config.model}")
        logger.info(f"  - URL: {client.config.url}")
        logger.info(f"  - Timeout: {client.config.timeout}s")
        logger.info(f"  - Prompt length: {len(prompt)} chars")
        logger.info(f"  - Messages history: {len(messages) if messages else 0} messages")
        logger.info("=" * 80)

        # si le client supporte l'arg cancel_event, passe-le (Ollama via aiohttp n'en a pas, llama.cpp non plus)
        gen = getattr(client, "generate_response_stream")
        if "cancel_event" in gen.__code__.co_varnames:  # best-effort
            async for tok in gen(prompt, messages, max_tokens=max_tokens, cancel_event=cancel_event, **kwargs):
                if cancel_event and cancel_event.is_set():
                    break
                yield tok
        else:
            async for tok in gen(prompt, messages, max_tokens=max_tokens, **kwargs):
                if cancel_event and cancel_event.is_set():
                    break
                yield tok


# Instance globale du pool LLM
llm_pool = LLMPool()
