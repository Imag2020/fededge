"""
Chat Engine V2 - Based on dev_chat.ipynb Architecture
2-pass system with plain text tool calls and streaming support.
"""

import re
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
from .chat_tools_v2 import TOOL_REGISTRY, get_system_prompt

logger = logging.getLogger(__name__)


# =====================================================================
# TOOL CALL DETECTION & PARSING (notebook-style)
# =====================================================================

# Regex patterns (tolerant)
TOOL_FENCE_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
TOOL_XML_RE = re.compile(r"<tool>\s*(\{.*?\})\s*</tool>", re.DOTALL | re.IGNORECASE)
TOOL_SHORT_RE = re.compile(r"```([a-zA-Z0-9_]+)\s*(\{.*?\})\s*```", re.DOTALL)
# NEW: Plain text format <tool>market: BTC ETH 24h</tool>
TOOL_TEXT_RE = re.compile(r"<tool>\s*([a-zA-Z0-9_]+)\s*:\s*(.*?)\s*</tool>", re.DOTALL | re.IGNORECASE)
# End tag detector for streaming
TOOL_END_RE = re.compile(r"</tool>", re.IGNORECASE)


def _safe_json_loads(s: str) -> Optional[dict]:
    """Safe JSON parsing."""
    try:
        return json.loads(s)
    except Exception:
        return None


def maybe_extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract tool call from LLM response using multiple patterns.

    Priority:
    1. Plain text: <tool>market: BTC</tool>
    2. JSON fence: ```tool {...}```
    3. XML: <tool>{...}</tool>
    4. Short: ```name {...}```

    Returns:
        {"name": "tool_name", "args": {"query": "..."}} or None
    """
    if not text:
        return None

    # 1) Plain text format (PRIMARY for notebook)
    m = TOOL_TEXT_RE.search(text)
    if m:
        name = m.group(1).strip().lower()
        query = m.group(2).strip()
        if name in TOOL_REGISTRY:
            return {"name": name, "args": {"query": query}}

    # 2) JSON fence ```tool {...}```
    m = TOOL_FENCE_RE.search(text)
    if m:
        payload = _safe_json_loads(m.group(1))
        if isinstance(payload, dict) and "name" in payload:
            name = payload["name"]
            if name in TOOL_REGISTRY:
                return {"name": name, "args": payload.get("args", {})}

    # 3) XML <tool>{...}</tool>
    m = TOOL_XML_RE.search(text)
    if m:
        payload = _safe_json_loads(m.group(1))
        if isinstance(payload, dict) and "name" in payload:
            name = payload["name"]
            if name in TOOL_REGISTRY:
                return {"name": name, "args": payload.get("args", {})}

    # 4) Short ```name {...}```
    m = TOOL_SHORT_RE.search(text)
    if m:
        name = m.group(1).strip()
        args = _safe_json_loads(m.group(2)) or {}
        if name in TOOL_REGISTRY:
            return {"name": name, "args": args if isinstance(args, dict) else {}}

    return None


def run_tool(name: str, args: Dict[str, Any]) -> str:
    """
    Execute a tool by name and return plain text result.

    Args:
        name: Tool name
        args: Tool arguments

    Returns:
        Plain text result (string)
    """
    try:
        tool_func = TOOL_REGISTRY.get(name)
        if not tool_func:
            return f"Tool '{name}' not found."

        logger.info(f"🔧 Executing tool: {name} with args: {args}")
        result = tool_func(args)

        # Ensure result is string (tools should return plain text)
        if isinstance(result, dict):
            # Fallback: if tool returns JSON, convert to text
            return json.dumps(result, ensure_ascii=False)

        logger.info(f"✅ Tool result: {result[:200]}...")
        return str(result)

    except Exception as e:
        logger.error(f"❌ Tool execution failed: {e}", exc_info=True)
        return f"Tool '{name}' failed: {str(e)}"


# =====================================================================
# NON-STREAMING CHAT ENGINE (2-pass)
# =====================================================================

async def chat_turn(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    llm_generate_func,  # Async function(messages, conversation_id) -> str
    conversation_id: Optional[str] = None,
) -> Tuple[str, List[Dict[str, str]], bool]:
    """
    Execute a single chat turn with 2-pass tool calling (notebook style).

    Args:
        user_message: User's message
        conversation_history: List of {"role": "...", "content": "..."}
        llm_generate_func: Async function to call LLM
        conversation_id: Conversation ID for KV cache

    Returns:
        (final_response, updated_history, used_tool)
    """
    # Build messages with system prompt
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # PASS 1: Get initial LLM response
    logger.info(f"💬 Chat turn: user='{user_message[:50]}...', history_len={len(conversation_history)}")
    initial_response = await llm_generate_func(messages, conversation_id)

    # Check for tool call
    tool_call = maybe_extract_tool_call(initial_response)

    if not tool_call:
        # No tool call - return direct response
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": initial_response})
        return initial_response, conversation_history, False

    # PASS 2: Tool detected - execute it
    logger.info(f"🔧 Tool call detected: {tool_call['name']}")
    tool_result = run_tool(tool_call["name"], tool_call["args"])

    # PASS 3: Generate final response based on tool result
    follow_up_messages = messages + [
        {"role": "assistant", "content": initial_response},  # Keep trace of tool call
        {"role": "system", "content": "You received the tool result below as plain text. Reply for the user in ≤2 short sentences."},
        {"role": "user", "content": tool_result}
    ]

    final_response = await llm_generate_func(follow_up_messages, conversation_id)

    # Update conversation history
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_response})

    return final_response, conversation_history, True


# =====================================================================
# STREAMING CHAT ENGINE (2-pass with WebSocket support)
# =====================================================================

async def chat_turn_streaming(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    llm_stream_func,  # Async generator that yields tokens
    conversation_id: Optional[str] = None,
    websocket=None,  # WebSocket for real-time updates
) -> Tuple[str, List[Dict[str, str]], bool]:
    """
    Execute a streaming chat turn with 2-pass tool calling.

    Args:
        user_message: User's message
        conversation_history: Conversation history
        llm_stream_func: Async generator(messages, conversation_id, stop_sequences=[]) -> AsyncIterator[str]
        conversation_id: Conversation ID for KV cache
        websocket: WebSocket connection for status updates

    Returns:
        (final_response, updated_history, used_tool)
    """
    # Build messages
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # PASS 1: Stream response in real-time
    logger.info(f"💬 Streaming chat turn: user='{user_message[:50]}...'")

    if websocket:
        await websocket.send_json({"type": "chat_status", "payload": {"status": "thinking"}})

    accumulated_response = ""
    tool_call_detected = False

    # Stream tokens in real-time, watching for <tool> tags
    async for token in llm_stream_func(messages, conversation_id, stop_sequences=["</tool>"]):
        accumulated_response += token

        # Check if tool opening tag detected
        if not tool_call_detected and "<tool>" in accumulated_response:
            tool_call_detected = True
            # Stop streaming tokens to frontend, switch to tool mode
            if websocket:
                await websocket.send_json({"type": "chat_status", "payload": {"status": "tool_call"}})
        elif not tool_call_detected:
            # Stream token normally
            if websocket:
                await websocket.send_json({"type": "chat_token", "payload": {"token": token}})

        # Check if tool end tag detected (early exit)
        if TOOL_END_RE.search(accumulated_response):
            # Add the closing tag back (stop sequence cuts it off)
            accumulated_response += "</tool>"
            logger.info("🔧 Tool call closing tag detected")
            break

    # Check for tool call in accumulated response
    tool_call = maybe_extract_tool_call(accumulated_response)

    if not tool_call:
        # No tool call - ensure all content was streamed
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": accumulated_response})

        if websocket:
            await websocket.send_json({"type": "chat_stream_end"})

        return accumulated_response, conversation_history, False

    # PASS 2: Tool detected - execute
    logger.info(f"🔧 Tool call detected in stream: {tool_call['name']}")

    if websocket:
        await websocket.send_json({
            "type": "chat_status",
            "payload": {
                "status": "tool_running",
                "name": tool_call["name"]
            }
        })
        # Add delay so user can see the tool_running status
        await asyncio.sleep(0.3)

    # Execute tool
    tool_result = run_tool(tool_call["name"], tool_call["args"])

    if websocket:
        await websocket.send_json({
            "type": "tool_result",
            "name": tool_call["name"],
            "text": tool_result
        })
        await websocket.send_json({
            "type": "chat_status",
            "payload": {"status": "answering"}
        })
        # Add small delay before streaming final response
        await asyncio.sleep(0.2)

    # PASS 3: Generate final response from tool result
    follow_up_messages = messages + [
        {"role": "assistant", "content": accumulated_response},
        {"role": "system", "content": "You received the tool result below as plain text. Reply for the user in ≤3 short sentences."},
        {"role": "user", "content": tool_result}
    ]

    # Stream final response
    final_response = ""
    async for token in llm_stream_func(follow_up_messages, conversation_id, stop_sequences=[]):
        final_response += token

        if websocket:
            await websocket.send_json({"type": "chat_token", "payload": {"token": token}})

    # Update history with final response
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_response})

    if websocket:
        await websocket.send_json({"type": "chat_stream_end"})

    return final_response, conversation_history, True


# =====================================================================
# HELPER: LLM Generation Adapters
# =====================================================================

async def generate_with_llm_pool(
    messages: List[Dict[str, str]],
    conversation_id: Optional[str] = None
) -> str:
    """
    Adapter for llm_pool non-streaming generation.

    Args:
        messages: Message history
        conversation_id: Conversation ID

    Returns:
        Complete response text
    """
    try:
        from ..llm_pool import llm_pool

        # Get default LLM client
        client = llm_pool.get_default_client()
        if not client:
            return "[Error: No default LLM configured]"

        # Generate response (non-streaming)
        response = await asyncio.to_thread(
            client.generate_response,
            messages=messages,
            temperature=0.2,
            max_tokens=512,
            conversation_id=conversation_id
        )

        return response

    except Exception as e:
        logger.error(f"Error in generate_with_llm_pool: {e}", exc_info=True)
        return f"[Error: {str(e)}]"


async def stream_with_llm_pool(
    messages: List[Dict[str, str]],
    conversation_id: Optional[str] = None,
    stop_sequences: List[str] = None,
    llm_id: Optional[str] = None,
    llm_name: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Adapter for llm_pool streaming generation.

    Args:
        messages: Message history
        conversation_id: Conversation ID
        stop_sequences: Stop sequences (e.g., ["</tool>"])
        llm_id: Optional LLM ID to use (e.g., "ollama_gpt_oss")
        llm_name: Optional LLM name to use (alternative to llm_id)

    Yields:
        Text tokens
    """
    try:
        from ..llm_pool import llm_pool

        # Use llm_pool.generate_response_stream() directly with llm_id
        # This allows selecting specific models and respects their config
        # Don't pass max_tokens - let the model use its configured value
        async for chunk in llm_pool.generate_response_stream(
            prompt="",  # Not used when messages are provided
            messages=messages,
            llm_id=llm_id,
            name=llm_name,
            conversation_id=conversation_id,
            stop=stop_sequences
        ):
            yield chunk

    except Exception as e:
        logger.error(f"Error in stream_with_llm_pool: {e}", exc_info=True)
        yield f"[Error: {str(e)}]"
