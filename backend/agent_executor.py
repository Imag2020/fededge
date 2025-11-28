# backend/agent_executor.py
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from .agent_core_types import Context, Action, ActionType
from .llm_protocol import maybe_extract_tool_call

from .agent_tools import get_tools_registry

from .agent_core_types import Priority

from .agent_core_types import Event, EventKind, Topic  # pour EMIT

from .config.paths import AGENT_V3_LOG

# ------------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------------
logger = logging.getLogger("agents_v3")
if not logger.handlers:
    handler = logging.FileHandler(AGENT_V3_LOG)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(console_handler)

logger.setLevel(logging.DEBUG)

# --------------------------------------------------------------------------------------
# TOOL PROTOCOL
# --------------------------------------------------------------------------------------
TOOL_PROTOCOL_SNIPPET = """
TOOLS (optional)

⚠️ IMPORTANT: Tools are OPTIONAL. Only use a tool if the user explicitly asks for:
- Crypto prices (BTC, ETH, SOL...)
- Wallet information
- Market cap
- Information from the knowledge base (DeFi concepts, regulations, etc.)

Available tools (delimit by <tool> and </tool>):

- get_crypto_prices: get cryptocurrency prices

Example:

<tool>get_crypto_prices: BTC</tool>

- get_wallet_state: get wallet balances

Example:

<tool>get_wallet_state default</tool>

- get_market_cap: get global market cap

Example:

<tool>get_market_cap </tool>

- search_knowledge: search the knowledge base for information

Example:

<tool>search_knowledge: what is DeFi staking</tool>
"""


# ------------------------------------------------------------------------------------
# LLM LOGGING HELPER
# ------------------------------------------------------------------------------------
def format_messages_for_log(messages: List[Dict[str, str]], max_chars: int = 220) -> str:
    """Formate les messages pour le logging (tronqués)"""
    lines = ["--- LLM messages (truncated) ---"]
    for i, m in enumerate(messages):
        content = (m.get("content") or "").replace("\n", "\\n")
        lines.append(f"[{i}] {m.get('role')} : {content[:max_chars]}")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------
# GLOBAL CONSCIOUSNESS BUILDER
# ------------------------------------------------------------------------------------
def is_critical_news(title: str, summary: str = "") -> bool:
    """Détecte si une news est critique/importante"""
    critical_keywords = [
        "crash", "hack", "hacked", "exploit", "regulation", "banned",
        "sec", "lawsuit", "emergency", "critical", "breaking",
        "etf", "approval", "approved", "major", "significant",
        "all-time high", "ath", "record", "milestone"
    ]
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in critical_keywords)


def calculate_price_change(old_price: float, new_price: float) -> float:
    """Calcule le changement de prix en %"""
    if not old_price or old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100


def build_global_consciousness(working: Dict[str, Any], new_event: Dict[str, Any] = None) -> str:
    """
    Construit une conscience globale synthétique de l'environnement.

    La conscience globale est une synthèse concentrée de TOUT l'environnement :
    - Market : Prix importants + tendances significatives
    - News : Seulement les news critiques/importantes
    - Wallet : État des wallets principaux
    - World state : État général

    Elle ne change que si info majeure ou critique.

    Args:
        working: La working memory
        new_event: Nouvel événement à intégrer (optionnel)

    Returns:
        Synthèse globale concentrée
    """
    # Récupérer la conscience globale actuelle
    current_consciousness = working.get("global_consciousness", {})

    # Structure de la conscience globale
    consciousness = {
        "market": current_consciousness.get("market", {}),
        "news_critical": current_consciousness.get("news_critical", []),
        "wallet": current_consciousness.get("wallet", {}),
        "last_update": current_consciousness.get("last_update", 0)
    }

    # Mettre à jour avec le nouvel événement si fourni
    if new_event:
        event_type = new_event.get("details", {}).get("type")

        if event_type == "market":
            # Market : Ne mettre à jour que si changement significatif (>2%)
            prices = new_event.get("details", {}).get("prices", {})
            old_market = consciousness["market"]

            update_market = False
            for crypto, price in prices.items():
                if crypto in ["Bitcoin", "Ethereum", "Solana"]:  # Cryptos importants
                    old_price = old_market.get(crypto, 0)
                    if old_price == 0:
                        # Première fois, on l'ajoute
                        consciousness["market"][crypto] = price
                        update_market = True
                    else:
                        change_pct = calculate_price_change(old_price, price)
                        if abs(change_pct) >= 2.0:  # Changement >= 2%
                            consciousness["market"][crypto] = price
                            update_market = True
                            logger.info(f"[Consciousness] Market update: {crypto} {change_pct:+.1f}% (${old_price:,.0f} -> ${price:,.0f})")

            if update_market:
                consciousness["last_update"] = time.time()

        elif event_type == "news":
            # News : Ne garder que les news critiques
            title = new_event.get("details", {}).get("title", "")
            summary = new_event.get("details", {}).get("summary", "")

            if is_critical_news(title, summary):
                # Ajouter la news critique
                critical_news = {
                    "title": title[:100],
                    "summary": summary[:200],
                    "ts": time.time()
                }

                # Vérifier si pas déjà présente
                exists = any(
                    news["title"][:50] == title[:50]
                    for news in consciousness["news_critical"]
                )

                if not exists:
                    consciousness["news_critical"].append(critical_news)
                    consciousness["news_critical"] = consciousness["news_critical"][-5:]  # Garder 5 max
                    consciousness["last_update"] = time.time()
                    logger.info(f"[Consciousness] Critical news added: {title[:60]}")
            else:
                logger.debug(f"[Consciousness] Non-critical news ignored: {title[:60]}")

        elif event_type == "wallet":
            # Wallet : Mettre à jour l'état
            wallet_name = new_event.get("details", {}).get("wallet", "default")
            wallet_data = new_event.get("details", {}).get("data", {})

            consciousness["wallet"][wallet_name] = {
                "balance": wallet_data.get("balance", 0),
                "updated": time.time()
            }
            consciousness["last_update"] = time.time()

    # Nettoyer les vieilles news critiques (> 24h)
    if consciousness["news_critical"]:
        now = time.time()
        consciousness["news_critical"] = [
            news for news in consciousness["news_critical"]
            if now - news.get("ts", 0) < 86400  # 24h
        ]

    # Sauvegarder la conscience mise à jour
    working["global_consciousness"] = consciousness

    # Construire la synthèse textuelle
    parts = []

    # Market
    if consciousness["market"]:
        market_parts = []
        for crypto, price in consciousness["market"].items():
            market_parts.append(f"{crypto}: ${price:,.0f}")
        parts.append("📊 " + ", ".join(market_parts))

    # News critiques
    if consciousness["news_critical"]:
        # Prendre seulement les 2 plus récentes
        recent_news = sorted(
            consciousness["news_critical"],
            key=lambda x: x.get("ts", 0),
            reverse=True
        )[:2]
        for news in recent_news:
            parts.append(f"📰 {news['title'][:60]}")

    # Wallet
    if consciousness["wallet"]:
        for wallet_name, wallet_data in consciousness["wallet"].items():
            balance = wallet_data.get("balance", 0)
            if balance > 0:
                parts.append(f"💰 {wallet_name}: ${balance:,.2f}")

    if not parts:
        return "Monitoring crypto markets and blockchain activity..."

    return " | ".join(parts)


class Executor:
    def __init__(self, llm_pool, bus, profile, use_real_tools: bool = True):
        self.llm_pool = llm_pool
        self.bus = bus
        self.profile = profile
        self.use_real_tools = use_real_tools
        self.tool_registry = get_tools_registry()

    async def _call_llm(
        self,
        system: str,
        user: str,
        history: Optional[List[Dict[str, str]]] = None,
        timeout: float = 150.0,
        conversation_id: Optional[str] = None
    ) -> str:
        """Appel LLM avec logging détaillé et retry en cas d'erreur

        Args:
            system: Message système
            user: Message utilisateur courant
            history: Historique de conversation [{"role": "user"|"assistant", "content": "..."}, ...]
            timeout: Timeout en secondes
            conversation_id: ID de conversation pour KV cache (llamacpp-server)
        """
        # Construire les messages avec l'historique
        msgs = [{"role": "system", "content": system}]

        # Ajouter l'historique si présent
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content and role in ["user", "assistant"]:
                    msgs.append({"role": role, "content": content})

        # Ajouter le message utilisateur actuel
        msgs.append({"role": "user", "content": user})

        # 🔍 LOG DEBUG des prompts agent_v3
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(format_messages_for_log(msgs, max_chars=4000))

        try:
            # Passer conversation_id pour optimiser KV cache
            coro = self.llm_pool.generate_response("", messages=msgs, conversation_id=conversation_id)
            logger.info(f"⏱️  [Executor] Waiting for LLM response (timeout={timeout}s, conv_id={conversation_id})...")
            ret = await asyncio.wait_for(coro, timeout=timeout)
            logger.info(f"✅ [Executor] LLM response received ({len(ret)} chars)")
            logger.debug(f"========= LLM response = *{ret}*")
            return ret or ""
        except asyncio.TimeoutError:
            logger.error(f"⏱️ [Executor] LLM timeout after {timeout}s - asyncio.wait_for timed out")
            return ""
        except Exception as e:
            logger.warning(f"[Executor] LLM call failed: {e}, retrying with compact prompt...")
            # RETRY SECOURS : prompt compact (moins de tokens) + timeout un poil plus long
            try:
                # system ultra-court (1 ligne), user tronqué
                sys_small = "Be concise and correct."
                usr_small = user[-800:]  # garde le plus récent / utile
                msgs_retry = [
                    {"role": "system", "content": sys_small},
                    {"role": "user", "content": usr_small},
                ]
                coro2 = self.llm_pool.generate_response("", messages=msgs_retry, conversation_id=conversation_id)
                ret = await asyncio.wait_for(coro2, timeout=timeout + 1.5)
                logger.debug(f"========= LLM retry response = *{ret}*")
                return ret or ""
            except Exception as e2:
                logger.error(f"[Executor] LLM retry failed: {e2}")
                return ""

    async def run_plan(self, ctx: Context, plan) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for action in plan.actions:
            res = await self.execute(ctx, action)
            results.append(res)
        return results

    async def execute_stream(self, ctx: Context, action: Action):
        """
        Version streaming de execute() pour les actions ANSWER.

        Yields:
            - {"type": "token", "token": "..."}  # Token du LLM
            - {"type": "tool_call", "name": "get_crypto_prices", "args": {...}}  # Tool détecté
            - {"type": "tool_result", "name": "...", "result": {...}}  # Résultat du tool
            - {"type": "done", "answer": "..."}  # Réponse finale complète
        """
        if action.type != ActionType.ANSWER:
            # Pour les autres types d'actions, fallback sur execute classique
            result = await self.execute(ctx, action)
            yield {"type": "done", "result": result}
            return

        question = action.args.get("question", "")
        mem = ctx.memory
        working = mem.working

        # Récupérer conversation_id pour KV cache
        conversation_id = working.get("conversation_id")

        # Récupérer l'historique
        chat_history = working.get("chat_history", [])
        recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history

        # Contexte conscient
        conscious = mem.conscious
        conscious_snippet = ""
        if conscious and hasattr(conscious, 'summary') and conscious.summary:
            conscious_snippet = conscious.summary[:280]

        # System prompt
        system = f"""{self.profile.whoami}
Mission: {self.profile.mission}

{TOOL_PROTOCOL_SNIPPET}
"""

        # User prompt
        user_parts = []
        if conscious_snippet:
            user_parts.append("Context summary:\n" + conscious_snippet)
        user_parts.append(f"{question}")
        user_prompt = "\n\n".join(user_parts)

        # Stream du premier appel LLM avec filtrage des balises tool
        accumulated = ""
        last_sent_index = 0  # Index du dernier caractère envoyé
        tool_call = None
        tool_start_index = -1  # Position où commence le tool call dans accumulated

        try:
            async for token in self.llm_pool.generate_response_stream(
                "",
                messages=self._build_messages(system, user_prompt, recent_history),
                conversation_id=conversation_id
            ):
                accumulated += token

                # Vérifier si un tool call commence dans accumulated
                if tool_start_index == -1:
                    # Chercher les patterns de début de tool
                    for pattern in ["<tool>", "```tool", "```"]:
                        idx = accumulated.find(pattern, last_sent_index)
                        if idx != -1:
                            # Pattern trouvé !
                            # Envoyer tout ce qui est AVANT le pattern
                            if idx > last_sent_index:
                                to_send = accumulated[last_sent_index:idx]
                                if to_send:
                                    yield {"type": "token", "token": to_send}
                                    last_sent_index = idx

                            tool_start_index = idx
                            break

                # Si on est dans un tool call, attendre la fin
                if tool_start_index != -1:
                    # Chercher la fin du tool call
                    if "</tool>" in accumulated[tool_start_index:]:
                        # Tool call complet trouvé
                        from .llm_protocol import maybe_extract_tool_call
                        tool_call = maybe_extract_tool_call(accumulated, known_tools=self.tool_registry)
                        if tool_call:
                            # Extraire la position de fin du tool
                            tool_end = accumulated.find("</tool>", tool_start_index) + len("</tool>")
                            last_sent_index = tool_end
                            break  # Sortir pour traiter le tool
                    continue

                # Pas de tool call en cours : envoyer les tokens avec un délai de sécurité
                # On garde toujours les 10 derniers caractères en attente au cas où "<tool>" commence
                safe_point = len(accumulated) - 10
                if safe_point > last_sent_index:
                    to_send = accumulated[last_sent_index:safe_point]
                    if to_send:
                        yield {"type": "token", "token": to_send}
                        last_sent_index = safe_point

            # Fin du stream - envoyer ce qui reste
            if not tool_call and last_sent_index < len(accumulated):
                remaining = accumulated[last_sent_index:]
                if remaining and not ("<tool>" in remaining or "```" in remaining):
                    yield {"type": "token", "token": remaining}

            # Si tool call détecté
            if tool_call:
                name = tool_call["name"]
                args = tool_call.get("args", {}) or {}

                # Envoyer un emoji pour indiquer le tool call
                yield {"type": "token", "token": " 🔧 "}

                yield {"type": "tool_call", "name": name, "args": args}
                logger.info(f"[Executor STREAM] Tool call detected: {name}")

                tool_fn = self.tool_registry.get(name)
                if not tool_fn:
                    answer = f"Tool {name} not found"
                else:
                    # Exécuter le tool
                    tool_res = await tool_fn(args) if self.use_real_tools else {}
                    working.setdefault("last_tools", {})[name] = tool_res

                    yield {"type": "tool_result", "name": name, "result": tool_res}

                    # Préparer le follow-up stream
                    tool_json = json.dumps(tool_res, ensure_ascii=False)[:1200] if tool_res else "{}"

                    extended_history = list(recent_history)
                    extended_history.append({"role": "user", "content": question})
                    extended_history.append({"role": "assistant", "content": accumulated})

                    follow_user = (
                        "You now have fresh tool results. Answer the user in a clear, concise way.\n"
                        "Do NOT call any tool now. Do NOT mention tools or JSON.\n\n"
                        f"Tool used: {name}\n"
                        f"Tool result (JSON):\n{tool_json}\n\n"
                        "Using ONLY this information and your knowledge of trading concepts, "
                        "answer the user in 3–5 sentences max."
                    )

                    # Stream du follow-up
                    answer = ""
                    async for token in self.llm_pool.generate_response_stream(
                        "",
                        messages=self._build_messages(system, follow_user, extended_history),
                        conversation_id=conversation_id
                    ):
                        answer += token
                        yield {"type": "token", "token": token}
            else:
                # Pas de tool, réponse directe
                answer = accumulated.strip()

        except Exception as e:
            logger.error(f"[Executor STREAM] Error: {e}", exc_info=True)
            answer = f"Error: {str(e)}"

        # Mise à jour de l'historique
        ts = time.time()
        chat_history.append({"role": "user", "content": question, "ts": ts})
        chat_history.append({"role": "assistant", "content": answer, "ts": ts})
        working["chat_history"] = chat_history[-20:]

        working["last_user_answer"] = {
            "question": question,
            "answer": answer,
            "ts": ts
        }

        working["last_chat_activity"] = ts

        yield {"type": "done", "answer": answer}

    def _build_messages(self, system: str, user: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Helper pour construire les messages LLM"""
        msgs = [{"role": "system", "content": system}]

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content and role in ["user", "assistant"]:
                    msgs.append({"role": role, "content": content})

        msgs.append({"role": "user", "content": user})
        return msgs

    async def execute(self, ctx: Context, action: Action) -> Dict[str, Any]:
        if action.type == ActionType.ANSWER:
            question = action.args.get("question", "")
            mem = ctx.memory
            working = mem.working

            # Récupérer conversation_id pour KV cache (llamacpp-server)
            conversation_id = working.get("conversation_id")

            # Récupérer l'historique backend (seule source de vérité)
            chat_history = working.get("chat_history", [])
            logger.debug(f"[Executor] Backend chat history: {len(chat_history)} messages")

            # DEBUG: Log détaillé de l'historique
            if chat_history and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[Executor] Chat history details (last 4):")
                for i, msg in enumerate(chat_history[-4:]):
                    role = msg.get("role", "?")
                    content = msg.get("content", "")[:60]
                    logger.debug(f"  [{i}] {role}: {content}")

            # Ne garder que les 8 derniers messages (4 échanges) pour éviter la contamination
            recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history

            # Contexte conscient optionnel (résumé)
            conscious = mem.conscious
            conscious_snippet = ""
            if conscious and hasattr(conscious, 'summary') and conscious.summary:
                conscious_snippet = conscious.summary[:280]

            # Premier appel LLM avec prompt amélioré
            system = f"""{self.profile.whoami}
Mission: {self.profile.mission}

{TOOL_PROTOCOL_SNIPPET}
"""

            # Construire le prompt utilisateur (sans l'historique qui sera passé séparément)
            user_parts = []
            if conscious_snippet:
                user_parts.append("Context summary:\n" + conscious_snippet)
            user_parts.append(f"{question}")

            user_prompt = "\n\n".join(user_parts)

            try:
                # Passer l'historique comme paramètre séparé au lieu de le concaténer
                # Timeout élevé pour les modèles distants lents (doit être > timeout client)
                raw = await self._call_llm(
                    system, user_prompt,
                    history=recent_history,
                    timeout=150.0,
                    conversation_id=conversation_id
                )
            except Exception as e:
                logger.error(f"[Executor] LLM error: {e}", exc_info=True)
                raw = ""

            # Fallback si pas de réponse LLM
            if not raw:
                q_preview = question.strip()[:120] if question else ""
                if not q_preview:
                    answer = "Hi! I'm ready. Ask me anything about your wallets or the crypto market context."
                else:
                    answer = f"Quick note: the local model is busy. For now, I confirm I received your question: '{q_preview}'. I'll keep things short and cautious."
            else:
                # Vérifier si le LLM a demandé un tool
                tool_call = maybe_extract_tool_call(raw, known_tools=self.tool_registry)

                if tool_call:
                    name = tool_call["name"]
                    args = tool_call.get("args", {}) or {}
                    tool_fn = self.tool_registry.get(name)

                    if not tool_fn:
                        logger.warning(f"[Executor] Unknown tool requested: {name}")
                        answer = "I cannot use the requested tool at the moment. I'll respond with available information."
                    else:
                        logger.info(f"[Executor] ✨ Tool call detected: {name} with args={args}")
                        try:
                            tool_res = await tool_fn(args) if self.use_real_tools else {}

                            # Enregistrer l'usage du tool
                            working.setdefault("last_tools", {})[name] = tool_res

                            # Deuxième appel LLM pour formater la réponse avec les données
                            tool_json = json.dumps(tool_res, ensure_ascii=False)[:1200] if tool_res else "{}"

                            # OPTIMISATION KV CACHE: Ajouter le premier échange (question + tool call)
                            # à l'historique pour que llama.cpp puisse réutiliser le cache
                            extended_history = list(recent_history)  # Copie
                            extended_history.append({"role": "user", "content": question})
                            extended_history.append({"role": "assistant", "content": raw})  # Réponse avec <tool>...</tool>

                            # IMPORTANT: Utiliser le MÊME system prompt pour préserver le KV cache
                            # Les instructions spécifiques sont dans le user message
                            follow_user = (
                                "You now have fresh tool results. Answer the user in a clear, concise way.\n"
                                "Do NOT call any tool now. Do NOT mention tools or JSON.\n\n"
                                f"Tool used: {name}\n"
                                f"Tool result (JSON):\n{tool_json}\n\n"
                                "Using ONLY this information and your knowledge of trading concepts, "
                                "answer the user in 3–5 sentences max."
                            )

                            try:
                                # Timeout élevé pour les modèles distants lents
                                # Passer extended_history pour optimiser KV cache
                                answer = await self._call_llm(
                                    system, follow_user,
                                    history=extended_history,
                                    timeout=150.0,
                                    conversation_id=conversation_id
                                )
                            except Exception as e:
                                logger.warning(f"[Executor] follow-up LLM error: {e}")
                                answer = f"I retrieved data using an internal tool, but the model is unable to format a complete response. Here is a raw extract: {tool_json}"

                        except Exception as e:
                            logger.error(f"[Executor] Tool {name} failed: {e}", exc_info=True)
                            answer = "The tool call failed, so I'll respond more generally without real-time data."
                else:
                    # Pas de tool demandé : la réponse LLM est directe
                    answer = raw.strip()

            # Mise à jour de l'historique backend
            ts = time.time()
            chat_history.append({"role": "user", "content": question, "ts": ts})
            chat_history.append({"role": "assistant", "content": answer, "ts": ts})
            working["chat_history"] = chat_history[-20:]  # Garder les 20 derniers messages (10 échanges)

            # Stocker la réponse pour le chat worker
            working["last_user_answer"] = {
                "question": question,
                "answer": answer,
                "ts": ts
            }

            # Mettre à jour le timestamp de dernière activité chat (pour le timeout auto-clear)
            working["last_chat_activity"] = ts

            return {"type": "ANSWER", "text": answer}

        elif action.type == ActionType.EXECUTE:
            name = action.args.get("tool")
            params = action.args.get("params", {}) or {}
            fn = self.tool_registry.get(name)
            if not fn or not self.use_real_tools:
                logger.warning(f"[Executor] Tool {name} not found or tools disabled")
                return {"type": "EXECUTE", "ok": False, "error": f"Unknown tool {name}"}

            logger.info(f"[Executor] Executing tool: {name}")
            res = await fn(params)
            ctx.memory.working.setdefault("last_tools", {})[name] = res
            logger.debug(f"[Executor] Tool {name} returned: {str(res)[:200]}...")
            return {"type": "EXECUTE", "tool": name, "result": res}

        elif action.type == ActionType.SLEEP:
            ms = float(action.args.get("ms", 10))
            await asyncio.sleep(ms / 1000.0)
            return {"type": "SLEEP", "ms": ms}

        elif action.type == ActionType.UPDATE_CONSCIOUSNESS:
            summary = action.args.get("summary", "")
            data = action.args.get("data", {})

            logger.info(f"[Executor] Updating consciousness: {summary}")

            # Mettre à jour la conscience dans working memory
            working = ctx.memory.working

            # Construire un résumé enrichi avec les données
            enriched_summary = summary
            event_details = {}

            # Enrichir selon le type de données
            if isinstance(data, dict):
                if "title" in data:  # News article
                    event_details["type"] = "news"
                    event_details["title"] = data.get("title", "")[:80]
                    event_details["source"] = data.get("source", "")
                elif "prices" in data or any(k.lower() in ["bitcoin", "ethereum", "solana", "btc", "eth", "sol"] for k in data.keys()):  # Market data
                    event_details["type"] = "market"
                    # Extraire les principaux prix (support minuscules et majuscules)
                    prices = data.get("prices", data)
                    top_prices = {}

                    # Mapper les symboles courts vers les noms complets
                    symbol_map = {
                        "btc": "Bitcoin",
                        "eth": "Ethereum",
                        "sol": "Solana",
                        "bnb": "BNB",
                        "bitcoin": "Bitcoin",
                        "ethereum": "Ethereum",
                        "solana": "Solana"
                    }

                    for key in prices.keys():
                        key_lower = key.lower()
                        if key_lower in symbol_map:
                            price_data = prices[key]
                            if isinstance(price_data, dict):
                                top_prices[symbol_map[key_lower]] = price_data.get("price", 0)
                            else:
                                top_prices[symbol_map[key_lower]] = price_data

                    event_details["prices"] = top_prices

                    # Enrichir le summary avec les prix
                    if top_prices:
                        price_strs = [f"{k}: ${v:,.0f}" for k, v in list(top_prices.items())[:3]]
                        enriched_summary = f"📊 {', '.join(price_strs)}"
                elif "wallet" in data or "balance" in data:  # Wallet data
                    event_details["type"] = "wallet"
                    event_details["wallet"] = data.get("wallet", "default")

            # ========================================================================
            # NOUVELLE LOGIQUE : CONSCIENCE GLOBALE INTELLIGENTE
            # ========================================================================
            # Construire l'événement pour la conscience globale
            new_event = {
                "summary": enriched_summary,
                "details": event_details,
                "ts": time.time()
            }

            # Mettre à jour la conscience globale (synthèse concentrée de l'environnement)
            # Cette conscience ne change que si info majeure ou critique
            global_summary = build_global_consciousness(working, new_event)
            working["global_summary"] = global_summary

            logger.info(f"[Consciousness] Global: {global_summary[:120]}")

            # ========================================================================
            # WORKING MEMORY : Mémoire de travail de la mission en cours
            # ========================================================================
            # last_events contient l'historique des événements de travail récents
            # (utilisé pour le contexte de la mission en cours, pas pour la conscience globale)

            # Vérifier si cet événement n'est pas un doublon récent
            last_events = working.setdefault("last_events", [])
            is_duplicate = False

            # Vérifier les 3 derniers événements
            for recent_event in last_events[-3:]:
                # Comparer par type et résumé
                if (recent_event.get("data_type") == event_details.get("type") and
                    recent_event.get("summary", "")[:50] == enriched_summary[:50]):
                    is_duplicate = True
                    logger.debug(f"[Executor] Duplicate event detected in working memory: {enriched_summary[:60]}")
                    break

            # Ajouter seulement si pas un doublon
            if not is_duplicate:
                last_events.append({
                    "summary": enriched_summary,
                    "ts": time.time(),
                    "data_type": event_details.get("type", "unknown")
                })
                working["last_events"] = last_events[-10:]  # Garder les 10 derniers

            return {"type": "UPDATE_CONSCIOUSNESS", "summary": enriched_summary, "details": event_details}

        elif action.type == ActionType.EMIT:
            payload = action.args.get("payload", {})
            ev = Event(
                kind=EventKind.MISSION_UPDATE,
                topic=Topic.MISSION,
                payload=payload,
                source="executor",
                priority=Priority.NORMAL,
            )
            await self.bus.publish(ev)
            return {"type": "EMIT", "payload": payload}

        elif action.type == ActionType.PLAN:
            # ici tu peux rajouter plus tard un mode où l'Executor appelle le LLM
            # pour raffiner un plan intermédiaire
            return {"type": "PLAN", "note": "noop"}

        else:
            return {"type": "UNKNOWN_ACTION", "action": action.type}
