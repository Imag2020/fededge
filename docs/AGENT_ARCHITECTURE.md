# Architecture de l'Agent V3

**FedEdge Agent V3** - Architecture cognitive distribuée pour le trading crypto et l'analyse de marché

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture globale](#architecture-globale)
3. [Pipeline de données](#pipeline-de-données)
4. [Mémoire : Conscience globale vs Working memory](#mémoire--conscience-globale-vs-working-memory)
5. [Composants détaillés](#composants-détaillés)
6. [Flux de données](#flux-de-données)
7. [Optimisations](#optimisations)

---

## Vue d'ensemble

L'agent V3 est une architecture cognitive inspirée de la boucle **Sense → Think → Act** avec une séparation claire entre :

- **Conscience globale** : Synthèse concentrée de l'environnement (market, news, wallets)
- **Working memory** : Mémoire de travail de la mission/tâche en cours

### Principe de fonctionnement

```
┌─────────────┐
│   Events    │  ← Market ticks, News, User messages, Wallet updates
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Planner  │ → │ Executor │ → │ Reflector│ → │  Memory  │ │
│  │  (Plan)  │   │  (Act)   │   │ (Learn)  │   │  Store   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  Broadcast  │  → Frontend (WebSocket)
│Consciousness│
└─────────────┘
```

---

## Architecture globale

### Composants principaux

#### 1. **Orchestrator** (`agent_runtime.py`)
Coordonnateur central qui orchestre tout le cycle de vie de l'agent.

**Responsabilités :**
- Gestion du bus d'événements
- Coordination des composants (Planner, Executor, Reflector)
- Cycle de vie de l'agent (start/stop)
- Nettoyage automatique de l'historique chat

**Code clé :**
```python
class Orchestrator:
    def __init__(self, agent_id, llm_pool, profile):
        self.bus = EventBus()
        self.store = SQLAgentMemoryStore(agent_id)
        self.planner = Planner(llm_pool, profile)
        self.executor = Executor(llm_pool, self.bus, profile)
        self.reflector = Reflector(llm_pool, self.store, profile)
```

#### 2. **EventBus** (`agent_core_types.py`)
Bus d'événements asynchrone pour la communication inter-composants.

**Types d'événements :**
- `USER.MESSAGE` : Messages utilisateur
- `MISSION.UPDATE` : Mises à jour de missions internes
- `MARKET.TICK` : Données market
- `NEWS.ARTICLE` : Articles de news
- `WALLET.STATE` : État des wallets

#### 3. **Planner** (`agent_planner.py`)
Décide quelle mission lancer et quelles actions exécuter.

**Stratégie :**
- Messages utilisateur → Mission `chat_main`
- Market tick → Action `UPDATE_CONSCIOUSNESS`
- News article → Action `UPDATE_CONSCIOUSNESS`
- Wallet state → Action `UPDATE_CONSCIOUSNESS`

#### 4. **Executor** (`agent_executor.py`)
Exécute les actions planifiées.

**Actions disponibles :**
- `ANSWER` : Répondre à une question utilisateur (avec streaming)
- `EXECUTE` : Exécuter un outil (get_crypto_prices, search_knowledge, etc.)
- `UPDATE_CONSCIOUSNESS` : Mettre à jour la conscience globale
- `EMIT` : Émettre un événement
- `SLEEP` : Attendre

#### 5. **Reflector** (`agent_reflector.py`)
Analyse les résultats, met à jour la mémoire et persiste l'état.

**Responsabilités :**
- Construction de l'état conscient (`ConsciousState`)
- Mise à jour du graphe DoT (long-term memory)
- Sauvegarde des snapshots
- Broadcast de la conscience au frontend

---

## Pipeline de données

### Cycle complet : Event → Plan → Execute → Reflect

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. EVENT ARRIVES                                                  │
│    ┌────────────┐                                                 │
│    │   Event    │  (topic, kind, payload, source)                │
│    └─────┬──────┘                                                 │
│          │                                                        │
│          ▼                                                        │
│ 2. LOAD MEMORY                                                    │
│    ┌────────────┐                                                 │
│    │MemoryStore │ → MemorySnapshot                               │
│    └─────┬──────┘    ├─ facts: {}                                │
│          │           ├─ working: {chat_history, global_summary}  │
│          │           └─ conscious: ConsciousState                 │
│          ▼                                                        │
│ 3. CREATE CONTEXT                                                 │
│    ┌────────────┐                                                 │
│    │  Context   │                                                 │
│    └─────┬──────┘                                                 │
│          │   memory: MemorySnapshot                               │
│          │   profile: AgentProfile                                │
│          │   last_event: Event                                    │
│          │   cycle: int                                           │
│          ▼                                                        │
│ 4. PLAN                                                           │
│    ┌────────────┐                                                 │
│    │  Planner   │ → Plan                                          │
│    └─────┬──────┘    ├─ mission_id: "chat_main"                  │
│          │           ├─ actions: [Action(ANSWER, {...})]          │
│          │           └─ rationale: "user_chat_single_turn"        │
│          ▼                                                        │
│ 5. EXECUTE                                                        │
│    ┌────────────┐                                                 │
│    │  Executor  │ → Results: [{"type": "ANSWER", ...}]           │
│    └─────┬──────┘                                                 │
│          │   ┌─ Appel LLM                                         │
│          │   ├─ Tool execution (optional)                         │
│          │   └─ Update consciousness                              │
│          ▼                                                        │
│ 6. REFLECT                                                        │
│    ┌────────────┐                                                 │
│    │ Reflector  │                                                 │
│    └─────┬──────┘                                                 │
│          │   ┌─ Build ConsciousState                             │
│          │   ├─ Update DoT memory graph                           │
│          │   ├─ Save snapshot                                     │
│          │   └─ Broadcast consciousness                           │
│          ▼                                                        │
│ 7. FRONTEND UPDATE                                                │
│    ┌────────────────┐                                             │
│    │   WebSocket    │ → Frontend receives consciousness update   │
│    └────────────────┘                                             │
└──────────────────────────────────────────────────────────────────┘
```

### Détail des structures de données

#### Event
```python
@dataclass
class Event:
    id: str = field(default_factory=lambda: f"evt_{int(time.time()*1000)}")
    topic: Topic  # USER, MISSION, MARKET, NEWS, WALLET
    kind: EventKind  # MESSAGE, UPDATE, TICK, ARTICLE, STATE
    payload: Dict[str, Any]  # Données spécifiques
    source: str = "unknown"  # Source de l'événement
    priority: Priority = Priority.NORMAL
    ts: float = field(default_factory=time.time)
```

#### Context
```python
@dataclass
class Context:
    memory: MemorySnapshot
    profile: AgentProfile
    last_event: Event
    cycle: int
    mission_id: Optional[str] = None
```

#### Plan
```python
@dataclass
class Plan:
    mission_id: str
    actions: List[Action]
    rationale: str
```

#### Action
```python
@dataclass
class Action:
    type: ActionType  # ANSWER, EXECUTE, UPDATE_CONSCIOUSNESS, EMIT, SLEEP
    args: Dict[str, Any]
```

---

## Mémoire : Conscience globale vs Working memory

### Architecture de la mémoire

```
┌─────────────────────────────────────────────────────────────────┐
│                      MemorySnapshot                              │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │   facts    │  │   working    │  │     conscious        │    │
│  │ (long-term)│  │  (mission)   │  │   (environment)      │    │
│  └────────────┘  └──────────────┘  └──────────────────────┘    │
│       │                  │                     │                │
│       │                  │                     │                │
│  Persistent      Ephemeral/Task         Global awareness       │
│  knowledge       specific memory        synthesis              │
└─────────────────────────────────────────────────────────────────┘
```

### 1. **Conscience globale** (`global_summary`)

Synthèse **concentrée** et **stable** de l'environnement global. Ne change que si information **majeure** ou **critique**.

#### Structure interne (`global_consciousness`)

```python
{
    "market": {
        "Bitcoin": 47250,    # Prix actuels (mis à jour si ≥2% change)
        "Ethereum": 2800,
        "Solana": 150
    },
    "news_critical": [       # Seulement les news CRITIQUES
        {
            "title": "SEC Approves First Bitcoin ETF",
            "summary": "Major milestone for crypto adoption",
            "ts": 1234567890
        }
    ],
    "wallet": {              # État des wallets principaux
        "main_wallet": {
            "balance": 12500.50,
            "updated": 1234567890
        }
    },
    "last_update": 1234567890
}
```

#### Construction intelligente

```python
def build_global_consciousness(working: Dict, new_event: Dict) -> str:
    """
    Filtre intelligent des informations :

    1. MARKET:
       - Ne met à jour que si changement >= 2%
       - Garde uniquement BTC, ETH, SOL (cryptos importants)

    2. NEWS:
       - Filtre avec is_critical_news()
       - Keywords: hack, ETF, regulation, SEC, breaking, etc.
       - Auto-nettoyage des news > 24h

    3. WALLET:
       - État des wallets principaux
       - Mis à jour à chaque changement

    Returns:
        "📊 Bitcoin: $47,250, Ethereum: $2,800 | 📰 SEC Approves ETF | 💰 main_wallet: $12,500"
    """
```

#### Critères de mise à jour

| Type | Condition | Exemple |
|------|-----------|---------|
| **Market** | Changement ≥ 2% | BTC: $45k → $47k (+4.4%) ✅ |
| **Market** | Changement < 2% | BTC: $45k → $45.5k (+1.1%) ❌ |
| **News** | Critique (keywords) | "Bitcoin ETF Approved" ✅ |
| **News** | Non-critique | "Bitcoin technical analysis" ❌ |
| **Wallet** | Toute mise à jour | Balance change ✅ |

#### Fonction de détection de news critiques

```python
def is_critical_news(title: str, summary: str = "") -> bool:
    """
    Keywords critiques :
    - Sécurité : crash, hack, exploit
    - Régulation : SEC, regulation, banned, lawsuit
    - Événements majeurs : ETF, approval, breaking
    - Milestones : ATH, record, milestone
    """
    critical_keywords = [
        "crash", "hack", "hacked", "exploit", "regulation", "banned",
        "sec", "lawsuit", "emergency", "critical", "breaking",
        "etf", "approval", "approved", "major", "significant",
        "all-time high", "ath", "record", "milestone"
    ]
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in critical_keywords)
```

### 2. **Working memory** (`working`)

Mémoire de travail de la **mission/tâche en cours**. Éphémère et spécifique au contexte.

#### Structure

```python
working = {
    # Chat context
    "chat_history": [
        {"role": "user", "content": "What's BTC price?", "ts": 123456},
        {"role": "assistant", "content": "Bitcoin is at $47,250", "ts": 123457}
    ],  # Gardé : 20 derniers messages (10 échanges)

    # Task tracking
    "last_events": [
        {
            "summary": "📊 Market prices updated",
            "ts": 1234567890,
            "data_type": "market"
        }
    ],  # Gardé : 10 derniers événements

    # Tools usage
    "last_tools": {
        "get_crypto_prices": {"prices": {...}, "cached": False}
    },

    # Mission state
    "conversation_id": "user_123",  # Pour KV cache (llama.cpp)
    "last_chat_activity": 1234567890,

    # Statistics
    "stats": {
        "total_cycles": 42,
        "tools_used": 15
    }
}
```

#### Caractéristiques

- **Éphémère** : Nettoyée automatiquement (timeout 30min par défaut)
- **Spécifique** : Contexte de la mission en cours uniquement
- **Historique** : Gardé limité (10-20 derniers items)

### 3. **Conscious state** (`conscious`)

État conscient instantané, snapshot de la conscience à un moment T.

```python
@dataclass
class ConsciousState:
    ts: float                      # Timestamp
    context: Dict[str, Any]        # Contexte du cycle
    vital_signals: List[Dict]      # Signaux vitaux
    summary: str                   # = global_summary (IMPORTANT!)
```

**Note importante** : Le champ `summary` du `ConsciousState` contient maintenant la **conscience globale** (et non plus le summary local de la mission).

```python
# agent_reflector.py
global_summary = snap.working.get("global_summary", "")
conscious = ConsciousState(
    ts=time.time(),
    context={
        "cycle": ctx.cycle,
        "mission_id": plan.mission_id,
        "last_summary": summary,           # Working memory (local)
        "global_consciousness": global_summary  # Global consciousness
    },
    summary=global_summary or summary,  # Priorité à global_summary
)
```

### Comparaison

| Aspect | Global Consciousness | Working Memory |
|--------|---------------------|----------------|
| **Durée de vie** | Stable, long-terme | Éphémère, court-terme |
| **Contenu** | Environnement (market, news, wallets) | Mission en cours (chat, tasks) |
| **Mise à jour** | Seulement si info majeure (≥2% market, critical news) | À chaque événement |
| **Taille** | Compact, synthétique | Variable, historique limité |
| **Persistance** | Sauvegardé en DB | Nettoyé après timeout |
| **Usage** | Context pour l'agent, display frontend | Contexte d'exécution, chat history |

---

## Composants détaillés

### Executor : Gestion des actions

#### Action : ANSWER (Chat)

**Pipeline :**

```
User question
     ↓
Build context (history + global_consciousness)
     ↓
First LLM call (detect tool need?)
     ↓
  ┌─────────┐
  │Tool call│ Yes → Execute tool → Second LLM call (format answer)
  └─────────┘
      No ↓
Format answer
     ↓
Update chat_history in working memory
     ↓
Return answer
```

**Code simplifié :**

```python
async def execute(self, ctx: Context, action: Action):
    if action.type == ActionType.ANSWER:
        question = action.args["question"]

        # Récupérer contexte
        chat_history = working.get("chat_history", [])
        global_summary = working.get("global_summary", "")

        # Premier appel LLM
        raw = await self._call_llm(system, user_prompt, history=chat_history)

        # Détection tool call
        tool_call = maybe_extract_tool_call(raw)

        if tool_call:
            # Exécuter tool
            tool_result = await tool_fn(args)

            # Deuxième appel LLM pour formater
            answer = await self._call_llm(system, follow_up, history=extended)
        else:
            answer = raw

        # Sauvegarder dans working memory
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})
        working["chat_history"] = chat_history[-20:]  # Keep last 20

        return {"type": "ANSWER", "text": answer}
```

#### Action : UPDATE_CONSCIOUSNESS

**Pipeline :**

```
Event data (market/news/wallet)
     ↓
Extract event details
     ↓
Enrich summary
     ↓
Call build_global_consciousness()
     ↓
  ┌──────────────────────────────┐
  │ Intelligence filtering:       │
  │ - Market: only if ≥2% change │
  │ - News: only if critical     │
  │ - Wallet: always update      │
  └──────────────────────────────┘
     ↓
Update working["global_summary"]
     ↓
Update working["last_events"] (working memory)
     ↓
Return
```

**Code simplifié :**

```python
elif action.type == ActionType.UPDATE_CONSCIOUSNESS:
    summary = action.args.get("summary", "")
    data = action.args.get("data", {})

    # Extract event type
    event_details = {"type": "unknown"}

    if "title" in data:  # News
        event_details["type"] = "news"
        event_details["title"] = data["title"]
        event_details["summary"] = data.get("summary", "")

    elif "prices" in data:  # Market
        event_details["type"] = "market"
        event_details["prices"] = extract_top_prices(data)

    elif "wallet" in data:  # Wallet
        event_details["type"] = "wallet"
        event_details["wallet"] = data.get("wallet", "default")

    # Build new event
    new_event = {
        "summary": enriched_summary,
        "details": event_details,
        "ts": time.time()
    }

    # Update GLOBAL consciousness (intelligent filtering)
    global_summary = build_global_consciousness(working, new_event)
    working["global_summary"] = global_summary

    # Update WORKING memory (task history)
    working["last_events"].append({
        "summary": enriched_summary,
        "ts": time.time(),
        "data_type": event_details["type"]
    })
    working["last_events"] = working["last_events"][-10:]
```

### Reflector : Persistance et broadcast

**Pipeline :**

```
Results from Executor
     ↓
Generate mini summary (non-user events)
     ↓
Build ConsciousState
     ├─ context: {cycle, mission_id, stats}
     ├─ summary: global_summary (IMPORTANT!)
     └─ vital_signals: []
     ↓
Update DoT memory graph (long-term)
     ↓
Save event trace to DB
     ↓
Save memory snapshot to DB
     ↓
Save ConsciousState snapshot to DB
     ↓
Broadcast consciousness to frontend (WebSocket)
```

**Code simplifié :**

```python
async def reflect(self, ctx: Context, plan: Plan, results: List[Dict]):
    snap = ctx.memory

    # Generate mini summary (for working memory)
    summary = await generate_summary(results)

    # Build ConsciousState with GLOBAL consciousness
    global_summary = snap.working.get("global_summary", "")
    conscious = ConsciousState(
        ts=time.time(),
        context={
            "cycle": ctx.cycle,
            "mission_id": plan.mission_id,
            "last_summary": summary,              # Working (local)
            "global_consciousness": global_summary  # Global
        },
        summary=global_summary or summary  # Use global in priority
    )

    # Update DoT graph
    long_term = await self.store.update_dot(
        agent_id=self.store.agent_id,
        ctx_cycle=ctx.cycle,
        summary=summary,
        global_summary=global_summary
    )

    # Save everything
    await self.store.append_event(trace_event)
    await self.store.save(snap)
    await self.store.save_snapshot(conscious, ctx_cycle=ctx.cycle)

    # Broadcast to frontend
    broadcaster = get_consciousness_broadcaster()
    await broadcaster.broadcast_consciousness(snap)
```

### Consciousness Broadcaster

**Payload envoyé au frontend :**

```json
{
    "type": "agent_consciousness",
    "payload": {
        "global_consciousness": "📊 Bitcoin: $47,250, Ethereum: $2,800 | 📰 SEC Approves ETF | 💰 main_wallet: $12,500",
        "working_memory": "💬 Answered user question • 🔧 Used tool: get_crypto_prices",
        "timestamp": 1234567890.123,
        "cycle": 42
    }
}
```

---

## Flux de données

### Exemple complet : User pose une question

```
1. USER ACTION
   Frontend → WebSocket → POST /api/chat

2. EVENT CREATION
   Orchestrator.post_event(
       kind=EventKind.MESSAGE,
       topic=Topic.USER,
       payload={"text": "What's the Bitcoin price?"},
       source="user_123"
   )

3. EVENT BUS
   EventBus.publish(event) → EventBus.queue

4. ORCHESTRATOR LOOP
   event = await bus.get()
   cycle = 42

5. LOAD MEMORY
   mem = await store.load()
   → MemorySnapshot{
       facts: {},
       working: {
           chat_history: [...],
           global_summary: "📊 Bitcoin: $47,250 | 📰 SEC Approves ETF",
           conversation_id: "user_123"
       },
       conscious: ConsciousState{...}
   }

6. CREATE CONTEXT
   ctx = Context(
       memory=mem,
       profile=profile,
       last_event=event,
       cycle=42
   )

7. PLAN
   plan = await planner.plan(ctx, event)
   → Plan{
       mission_id: "chat_main",
       actions: [Action(ANSWER, {"question": "What's the Bitcoin price?"})],
       rationale: "user_chat_single_turn"
   }

8. EXECUTE
   results = await executor.run_plan(ctx, plan)

   8.1. First LLM call
        system = "You are a crypto assistant..."
        user = "Context: 📊 Bitcoin: $47,250\nQuestion: What's the Bitcoin price?"
        history = chat_history[-8:]  # Last 4 exchanges

        raw = await llm_pool.generate_response(
            "",
            messages=[system, ...history, user],
            conversation_id="user_123"  # KV cache optimization
        )

        → raw = "Bitcoin is currently at $47,250."

   8.2. No tool call detected
        answer = raw

   8.3. Update working memory
        chat_history.append({"role": "user", "content": "What's the Bitcoin price?"})
        chat_history.append({"role": "assistant", "content": "Bitcoin is currently at $47,250."})

   → results = [{"type": "ANSWER", "text": "Bitcoin is currently at $47,250."}]

9. REFLECT
   await reflector.reflect(ctx, plan, results)

   9.1. Generate summary
        summary = "Answered user question"

   9.2. Build ConsciousState
        global_summary = "📊 Bitcoin: $47,250 | 📰 SEC Approves ETF"
        conscious = ConsciousState(
            summary=global_summary,  # Global consciousness
            context={
                "cycle": 42,
                "last_summary": "Answered user question"  # Working
            }
        )

   9.3. Update DoT memory
        long_term = await store.update_dot(...)

   9.4. Save to DB
        await store.save(snap)
        await store.save_snapshot(conscious)

   9.5. Broadcast
        await broadcaster.broadcast_consciousness(snap)
        → WebSocket → Frontend receives:
        {
            "type": "agent_consciousness",
            "payload": {
                "global_consciousness": "📊 Bitcoin: $47,250 | 📰 SEC Approves ETF",
                "working_memory": "💬 Answered user question"
            }
        }

10. DONE
    User sees answer on frontend + consciousness updated
```

### Exemple : Market tick arrive

```
1. COLLECTOR
   PriceCollector (background task) fetches prices from CoinGecko
   prices = {"Bitcoin": 48000, "Ethereum": 2900, ...}

2. EVENT CREATION
   Orchestrator.post_event(
       kind=EventKind.UPDATE,
       topic=Topic.MISSION,
       payload={
           "mission_id": "market_monitor",
           "kind": "market_tick",
           "prices": prices
       }
   )

3. PLANNER
   plan = Plan(
       mission_id="market_monitor",
       actions=[Action(UPDATE_CONSCIOUSNESS, {
           "summary": "📊 Market prices updated",
           "data": prices
       })]
   )

4. EXECUTOR
   4.1. Extract event details
        event_details = {
            "type": "market",
            "prices": {"Bitcoin": 48000, "Ethereum": 2900, "Solana": 155}
        }

   4.2. Build global consciousness
        old_btc_price = 47250  # From global_consciousness
        new_btc_price = 48000
        change = +1.6%  # < 2% threshold

        → Price NOT updated (change too small)

        global_summary = "📊 Bitcoin: $47,250, Ethereum: $2,800 | 📰 SEC Approves ETF"
        # Bitcoin price stays at $47,250 because change < 2%

   4.3. Update working memory
        last_events.append({
            "summary": "📊 Market prices updated",
            "data_type": "market"
        })

5. REFLECT
   Consciousness broadcast shows SAME global_summary
   (no change because market movement < 2%)

6. LATER: Large market move
   If Bitcoin goes to $50,000 (+5.8% from $47,250):
   → Global consciousness UPDATED
   → "📊 Bitcoin: $50,000, Ethereum: $2,900 | ..."
```

---

## Optimisations

### 1. **KV Cache (llama.cpp)**

Pour les modèles locaux via llama.cpp server, utilisation du KV cache pour réutiliser les tokens déjà traités.

```python
# Planner stocke conversation_id
if event.source:
    ctx.memory.working["conversation_id"] = event.source

# Executor passe conversation_id au LLM
conversation_id = working.get("conversation_id")
response = await llm_pool.generate_response(
    "",
    messages=messages,
    conversation_id=conversation_id  # Optimise KV cache
)

# LlamaCppServerClient utilise le field "user" de l'API OpenAI
request_params = {
    "model": "local-model",
    "messages": messages,
    "user": conversation_id  # llama.cpp réutilise le cache
}
```

### 2. **Message history truncation**

Pour éviter l'explosion du contexte :

```python
# Garder seulement les 8 derniers messages (4 échanges)
recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history

# Passer au LLM
messages = [system] + recent_history + [user]
```

### 3. **Streaming support**

Pour les réponses en temps réel :

```python
async def execute_stream(self, ctx: Context, action: Action):
    """
    Yields:
        - {"type": "token", "token": "..."}
        - {"type": "tool_call", "name": "...", "args": {...}}
        - {"type": "tool_result", "name": "...", "result": {...}}
        - {"type": "done", "answer": "..."}
    """
    async for chunk in llm_pool.generate_response_stream(...):
        yield {"type": "token", "token": chunk}
```

### 4. **Automatic cleanup**

Nettoyage automatique de l'historique chat après inactivité :

```python
async def _cleanup_loop(self):
    while not self._stop.is_set():
        await asyncio.sleep(60)  # Check every minute

        mem = await self.store.load()
        last_activity = mem.working.get("last_chat_activity", 0)
        timeout = self.chat_timeout_minutes * 60

        if time.time() - last_activity > timeout:
            # Clear chat history
            mem.working["chat_history"] = []
            await self.store.save(mem)
```

### 5. **Parallel execution**

L'Orchestrator utilise un sémaphore pour limiter le nombre d'événements traités en parallèle :

```python
self._sem = asyncio.Semaphore(2)  # Max 2 events in parallel

async def _handle_event(self, event, cycle):
    try:
        await self._sem.acquire()
        # Process event...
    finally:
        self._sem.release()
```

---

## Résumé

### Points clés de l'architecture

1. **Séparation claire** entre conscience globale (environnement) et working memory (mission)

2. **Filtrage intelligent** des informations :
   - Market : Seulement si ≥2% de changement
   - News : Seulement si critique
   - Stabilité de la conscience globale

3. **Pipeline cohérent** : Event → Plan → Execute → Reflect

4. **Optimisations** :
   - KV cache pour modèles locaux
   - Message history truncation
   - Streaming support
   - Automatic cleanup

5. **Persistance** :
   - DB SQLite pour events, snapshots, memory
   - DoT graph pour long-term memory
   - Broadcast temps-réel au frontend

### Architecture résumée

```
Events (Market, News, User, Wallet)
    ↓
EventBus
    ↓
Orchestrator
    ├─ Planner    → Décide quoi faire
    ├─ Executor   → Exécute (LLM + Tools)
    └─ Reflector  → Apprend et persiste
         ↓
    MemoryStore
         ├─ Global consciousness (stable, synthétique)
         ├─ Working memory (éphémère, task-specific)
         └─ DoT graph (long-term knowledge)
              ↓
    Frontend (WebSocket broadcast)
```

---

**Version** : Agent V3
**Dernière mise à jour** : 2025-11-18
**Auteur** : FedEdge Team
