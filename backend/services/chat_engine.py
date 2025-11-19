"""
Chat Engine - Tool-based Chat Flow
Handles tool detection, execution, and response generation.
Based on dev_chat.ipynb architecture.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
from .chat_tools import TOOL_REGISTRY, get_system_prompt

logger = logging.getLogger(__name__)

# Tool fence regex pattern (matches ```tool {...}```)
TOOL_FENCE_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


# =====================================================================
# TOOL CALL DETECTION & PARSING
# =====================================================================

def extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract tool call from LLM response.

    Returns:
        {"name": "tool_name", "args": {...}} or None
    """
    if not text:
        return None

    match = TOOL_FENCE_RE.search(text)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
        name = payload.get("name")
        args = payload.get("args", {})

        if name in TOOL_REGISTRY:
            return {"name": name, "args": args}
        else:
            logger.warning(f"Tool '{name}' not found in registry")
            return None

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tool JSON: {e}")
        return None

    return None


def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.

    Returns:
        Tool result (JSON dict)
    """
    try:
        tool_func = TOOL_REGISTRY.get(name)
        if not tool_func:
            return {"error": f"Tool '{name}' not found"}

        logger.info(f"🔧 Executing tool: {name} with args: {args}")
        result = tool_func(args)
        logger.info(f"✅ Tool result: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ Tool execution failed: {e}", exc_info=True)
        return {"error": f"Tool '{name}' failed: {str(e)}"}


# =====================================================================
# CHAT ENGINE - Single Turn with Tool Support
# =====================================================================

async def chat_turn(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    llm_generate_func,  # Async function that generates response
    conversation_id: Optional[str] = None,
    max_tool_iterations: int = 1
) -> Tuple[str, List[Dict[str, str]], bool]:
    """
    Execute a single chat turn with optional tool calling.

    Args:
        user_message: User's message
        conversation_history: List of {"role": "...", "content": "..."}
        llm_generate_func: Async function(messages, conversation_id) -> str
        conversation_id: Conversation ID for KV cache
        max_tool_iterations: Max tool calls per turn (default: 1)

    Returns:
        (final_response, updated_history, used_tool)
    """
    # Build messages with system prompt
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    used_tool = False
    iterations = 0

    # Phase 1: Get initial LLM response
    logger.info(f"💬 Chat turn: user='{user_message[:50]}...', history_len={len(conversation_history)}")
    initial_response = await llm_generate_func(messages, conversation_id)

    # Check for tool call
    tool_call = extract_tool_call(initial_response)

    if not tool_call or iterations >= max_tool_iterations:
        # No tool call or max iterations reached - return direct response
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": initial_response})
        return initial_response, conversation_history, False

    # Phase 2: Tool detected - execute it
    used_tool = True
    iterations += 1

    logger.info(f"🔧 Tool call detected: {tool_call['name']}")
    tool_result = execute_tool(tool_call["name"], tool_call["args"])

    # Phase 3: Generate final response based on tool result
    follow_up_messages = messages + [
        {"role": "assistant", "content": initial_response},  # Keep trace of tool call
        {"role": "system", "content": "Tool result (JSON below). Summarize in ≤2 sentences for the user."},
        {"role": "user", "content": json.dumps(tool_result, ensure_ascii=False)}
    ]

    final_response = await llm_generate_func(follow_up_messages, conversation_id)

    # Update conversation history
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_response})

    return final_response, conversation_history, used_tool


# =====================================================================
# STREAMING CHAT ENGINE
# =====================================================================

async def chat_turn_streaming(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    llm_stream_func,  # Async generator that yields tokens
    conversation_id: Optional[str] = None,
    on_status_change=None  # Callback(status: "thinking"|"acting")
) -> AsyncIterator[Tuple[str, bool, Optional[str]]]:
    """
    Execute a streaming chat turn with tool support.

    Yields:
        (token, is_final, status) where:
        - token: Text token to stream
        - is_final: True if this is the last token
        - status: "thinking" | "acting" | None
    """
    # Build messages
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Phase 1: Stream initial response
    logger.info(f"💬 Streaming chat turn: user='{user_message[:50]}...'")

    if on_status_change:
        on_status_change("thinking")

    accumulated_response = ""
    async for token in llm_stream_func(messages, conversation_id):
        accumulated_response += token
        yield token, False, "thinking"

    # Check for tool call in accumulated response
    tool_call = extract_tool_call(accumulated_response)

    if not tool_call:
        # No tool call - finalize
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": accumulated_response})
        yield "", True, None
        return

    # Phase 2: Tool detected - execute
    logger.info(f"🔧 Tool call detected in stream: {tool_call['name']}")

    if on_status_change:
        on_status_change("acting")

    tool_result = execute_tool(tool_call["name"], tool_call["args"])

    # Phase 3: Generate final response from tool result
    if on_status_change:
        on_status_change("thinking")

    follow_up_messages = messages + [
        {"role": "assistant", "content": accumulated_response},
        {"role": "system", "content": "Tool result (JSON below). Summarize in ≤2 sentences for the user."},
        {"role": "user", "content": json.dumps(tool_result, ensure_ascii=False)}
    ]

    # Clear previous response and stream new one
    # Note: Frontend should handle clearing based on status change
    yield "\n\n", False, "acting"  # Separator

    final_response = ""
    async for token in llm_stream_func(follow_up_messages, conversation_id):
        final_response += token
        yield token, False, "thinking"

    # Update history with final response
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_response})

    yield "", True, None


# =====================================================================
# HELPER: Non-streaming Response
# =====================================================================

async def get_non_streaming_response(
    messages: List[Dict[str, str]],
    llm_generate_func,
    conversation_id: Optional[str] = None
) -> str:
    """
    Get a complete non-streaming response from LLM.

    Args:
        messages: Full message history
        llm_generate_func: Function to call LLM
        conversation_id: Conversation ID for KV cache

    Returns:
        Complete response text
    """
    try:
        response = await llm_generate_func(messages, conversation_id)
        return response
    except Exception as e:
        logger.error(f"Error getting LLM response: {e}", exc_info=True)
        return f"[Error: {str(e)}]"
