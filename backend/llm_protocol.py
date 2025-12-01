# backend/llm_protocol.py
from __future__ import annotations
from typing import Dict, Any, Optional
import re
import json
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# TOOL PROTOCOL
# --------------------------------------------------------------------------------------
# Formats supportés (identiques à ceux de ChatWorkerV2) :
# 1. <tool>name: free_text_or_args</tool>
# 2. ```tool { "name": "...", "args": {...} } ```
# 3. <tool>{ "name": "...", "args": {...} }</tool>
# 4. ```name { ... }```

TOOL_FENCE_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
TOOL_XML_RE   = re.compile(r"<tool>\s*(\{.*?\})\s*</tool>", re.DOTALL | re.IGNORECASE)
TOOL_SHORT_RE = re.compile(r"```([a-zA-Z0-9_]+)\s*(\{.*?\})\s*```", re.DOTALL)
# Modified: accepte les "." dans le nom du tool (pour gpt-oss qui génère "tool.get_crypto_prices")
TOOL_TEXT_RE  = re.compile(r"<tool>\s*([a-zA-Z0-9_.]+)\s*:\s*(.*?)\s*</tool>", re.DOTALL | re.IGNORECASE)
TOOL_END_RE   = re.compile(r"</tool>", re.IGNORECASE)

# NEW: form simple sans arguments: <tool>get_wallet_state</tool>
# Modified: accepte les "." dans le nom du tool
TOOL_BARE_RE  = re.compile(r"<tool>\s*([a-zA-Z0-9_.]+)\s*</tool>", re.DOTALL | re.IGNORECASE)

TOOL_END_RE   = re.compile(r"</tool>", re.IGNORECASE)


def _safe_json_loads(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        return None


def maybe_extract_tool_call(
    text: str,
    known_tools: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Extrait un appel de tool depuis le texte du LLM.

    Priority:
    1. Plain text: <tool>market: BTC</tool>
    2. JSON fence: ```tool {...}```
    3. XML: <tool>{...}</tool>
    4. Short: ```name {...}```

    known_tools : dict optionnel { name: func } pour filtrer sur les tools connus.

    Retourne:
        {"name": "tool_name", "args": {...}} ou None
    """
    if not text:
        return None

    def _is_known(name: str) -> bool:
        if known_tools is None:
            return True
        return name in known_tools

    def _clean_tool_name(name: str) -> str:
        """Nettoie le nom du tool (retire le préfixe 'tool.' si présent)"""
        name = name.strip()
        # Gpt-oss génère parfois "tool.get_crypto_prices" au lieu de "get_crypto_prices"
        if name.startswith("tool."):
            name = name[5:]  # Retire "tool."
        return name

    # 1) Plain text format (PRIMARY)
    m = TOOL_TEXT_RE.search(text)
    if m:
        name = _clean_tool_name(m.group(1))
        query = m.group(2).strip()
        if _is_known(name):
            logger.debug(f"[llm_protocol] Extracted tool call: {name} with query: {query[:50]}...")
            return {"name": name, "args": {"query": query}}

    # 1-bis) Bare format: <tool>get_wallet_state</tool>
    m = TOOL_BARE_RE.search(text)
    if m:
        name = _clean_tool_name(m.group(1))
        if _is_known(name):
            logger.debug(f"[llm_protocol] Extracted bare tool call: {name}")
            # aucun argument explicite → args vide
            return {"name": name, "args": {}}
            
    # 2) JSON fence ```tool {...}```
    m = TOOL_FENCE_RE.search(text)
    if m:
        payload = _safe_json_loads(m.group(1))
        if isinstance(payload, dict) and "name" in payload:
            name = _clean_tool_name(payload["name"])
            if _is_known(name):
                logger.debug(f"[llm_protocol] Extracted JSON fence tool call: {name}")
                return {"name": name, "args": payload.get("args", {}) or {}}

    # 3) XML <tool>{...}</tool>
    m = TOOL_XML_RE.search(text)
    if m:
        payload = _safe_json_loads(m.group(1))
        if isinstance(payload, dict) and "name" in payload:
            name = _clean_tool_name(payload["name"])
            if _is_known(name):
                logger.debug(f"[llm_protocol] Extracted XML tool call: {name}")
                return {"name": name, "args": payload.get("args", {}) or {}}

    # 4) Short ```name {...}```
    m = TOOL_SHORT_RE.search(text)
    if m:
        name = _clean_tool_name(m.group(1))
        args = _safe_json_loads(m.group(2)) or {}
        if _is_known(name):
            logger.debug(f"[llm_protocol] Extracted short format tool call: {name}")
            return {"name": name, "args": args if isinstance(args, dict) else {}}

    return None


# --------------------------------------------------------------------------------------
# CONTEXT-UPDATE PROTOCOL
# --------------------------------------------------------------------------------------
# On demande au LLM de proposer des mises à jour de mémoire dans un bloc :
#
# ```context
# { "working": { ... }, "facts": { ... } }
# ```
#
CONTEXT_FENCE_RE = re.compile(r"```context\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def maybe_extract_context_update(text: str) -> Optional[Dict[str, Any]]:
    """
    Extrait un bloc ```context {...}``` pour mise à jour de la mémoire.

    Exemple de payload attendu:
      {
        "working": {"risk_mode": "conservative"},
        "facts": {"fav_pair": "BTC/USDC"}
      }
    """
    if not text:
        return None
    m = CONTEXT_FENCE_RE.search(text)
    if not m:
        return None
    payload = _safe_json_loads(m.group(1))
    if isinstance(payload, dict):
        return payload
    return None


__all__ = [
    "maybe_extract_tool_call",
    "maybe_extract_context_update",
    "TOOL_END_RE",
    "TOOL_FENCE_RE",
    "TOOL_XML_RE",
    "TOOL_SHORT_RE",
    "TOOL_TEXT_RE",
]
