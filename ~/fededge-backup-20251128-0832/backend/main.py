########################################################
#
#  FedEdge main  0.1.0
#  Imed MAGROUNE 09-11/2025 - Beta
#  mailto:imed@fededge.net
#
#######################################################

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import json
import logging
import asyncio

# Import du WebSocket Manager optimisé
try:
    from .websocket_manager_optimized import get_websocket_manager
    USING_OPTIMIZED_WS = True
except ImportError:
    from .websocket_manager import get_websocket_manager
    USING_OPTIMIZED_WS = False

# Import du Scheduler non-bloquant optimisé
try:
    from .scheduler_async import start_non_blocking_scheduler
    USING_ASYNC_SCHEDULER = True
except ImportError:
    from .scheduler import start_scheduler
    USING_ASYNC_SCHEDULER = False

from .db import models, crud
from .db.models import SessionLocal

from .db.models import SessionLocal  # ta Session SQLAlchemy globale
from .db.crud import (
    get_or_create_copilot_agent,
    create_copilot_mission,
    list_active_missions,
    set_copilot_state,
)

from .llm_pool import llm_pool


# Agent V3 - orchestrator générique
from .agent_runtime import get_runtime as get_agent_v3_runtime
from .agent_core_types import Topic, EventKind

from .chat_worker_agent_v3 import (
    init_chat_worker_agent_v3,
    get_chat_worker_agent_v3,
)

# Instance globale de l'orchestrator Agent V3
agent_v3_runtime = None


# Import modular routers
from .routes import (
    assets_router,
    wallets_router,
    trading_router,
    news_router,
    rag_router,
    tools_router,
    config_router,
    debug_router,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="FedEdge AI Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager instance
ws_manager = get_websocket_manager()

# Mount static files (frontend)
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/pages", StaticFiles(directory="frontend/pages"), name="pages")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


# ===============================
# INCLUDE MODULAR ROUTERS
# ===============================
# All API endpoints are now organized in modular route files
# located in backend/routes/ directory

app.include_router(assets_router, prefix="/api")      # Asset/crypto management (8 endpoints)
app.include_router(wallets_router, prefix="/api")     # Wallet operations (11 endpoints)
app.include_router(trading_router, prefix="/api")     # Trading simulations & bot (22 endpoints)
app.include_router(news_router, prefix="/api")        # News & market context (6 endpoints)
app.include_router(rag_router, prefix="/api")   # Knowledge base & RAG (13 endpoints)
app.include_router(tools_router, prefix="/api")       # MCP tools API (2 endpoints)
app.include_router(config_router, prefix="/api")      # LLM configuration (6 endpoints)
app.include_router(debug_router, prefix="/api")       # Debug & diagnostics (4 endpoints)

# Total: 77 endpoints across 9 modular routers
# See backend/routes/REFACTORING_SUMMARY.md for complete documentation

def bootstrap_fededge_copilot():
    """
    Initialise FedEdge dans la base (CopilotAgent + missions + état KV minimal).
    Cette fonction est idempotente : elle peut être appelée à chaque startup.
    """
    db = SessionLocal()
    try:
        # 1) Profil logique FedEdge (whoami/mission/tools)
        whoami = (
            "You are FedEdge an expert DeFi cryptos and trading copilot. "
            "You manage a user wallets, knowledge RAG database and you do paper trading simuilations to improve your skills."
        )
        tools = ["get_market_cap", "get_crypto_prices", "get_world_state", "get_wallet_state"]
        mission = "User assistance, News Analysis for knowledge RAG, paper trade simulation"

        profile_json = {
            "who_am_i": whoami,
            "tools": tools,
            "mission": mission,
            "max_context_chars": 4096,
        }

        # 2) Créer / récupérer l'agent FedEdge core
        fededge = get_or_create_copilot_agent(
            db,
            agent_id="fededge_core",
            name="FedEdge Core Copilot",
            role="core_copilot",
            mission=mission,
            profile_json=profile_json,
        )

        # 3) Créer les missions de base si besoin
        existing = list_active_missions(db, agent_id=fededge.id)
        existing_names = {m.name for m in existing}

        if "daily_news_digest" not in existing_names:
            create_copilot_mission(
                db,
                agent_id=fededge.id,
                name="daily_news_digest",
                description="Analyse quotidienne des news crypto, scoring, sélection RAG/teacher.",
                kind="periodic",
                priority=2,
                status="active",
                schedule_cron="0 * * * *",  # toutes les heures (à ajuster)
                config={"max_news_per_run": 50},
            )

        if "paper_trade_monitor" not in existing_names:
            create_copilot_mission(
                db,
                agent_id=fededge.id,
                name="paper_trade_monitor",
                description="Suivi des simulations de trading et mise à jour du contexte de marché/stratégies.",
                kind="periodic",
                priority=3,
                status="active",
                schedule_cron="*/15 * * * *",  # toutes les 15 minutes
                config={},
            )

        if "teacher_update" not in existing_names:
            create_copilot_mission(
                db,
                agent_id=fededge.id,
                name="teacher_update",
                description="Génération d'exemples pédagogiques pour entraîner un petit modèle.",
                kind="periodic",
                priority=5,
                status="active",
                schedule_cron="30 23 * * *",  # tous les jours à ~23h30
                config={"max_examples_per_run": 20},
            )

        # 4) Initialiser un état KV minimal pour FedEdge
        # (ça évite de se retrouver avec des None dans les premiers prompts)
        set_copilot_state(db, "market_overview", {"status": "unknown", "last_update": None})
        set_copilot_state(db, "wallets_summary", {"status": "empty", "wallets": []})
        set_copilot_state(db, "sim_overview", {"status": "empty", "strategies": []})
        set_copilot_state(db, "user_profile", {"risk_profile": "unknown", "notes": []})
        set_copilot_state(db, "teacher_stats", {"examples_total": 0})

        print("✅ FedEdge copilot bootstrap OK (agent + missions + state_kv)")

    except Exception as e:
        print(f"⚠️ Erreur bootstrap FedEdge copilot: {e}")
    finally:
        db.close()

###################################################
#   STARTUP
###################################################

@app.on_event("startup")
async def startup_event():
    print("FedEdge AI Starting ....")

    # Re-enable essential functionality only
    models.create_db_and_tables()

    # Initialiser les cryptos supportées et restaurer les simulations
    db = SessionLocal()
    try:
        crud.init_default_assets(db)

        # 💼 Initialiser le wallet par défaut avec USDC et la simulation par défaut
        crud.init_default_wallet_and_simulation(db)

        # 🔄 Restaurer les simulations actives après redémarrage
        from datetime import datetime
        active_simulations = db.query(models.Simulation).filter(
            models.Simulation.is_active == True
        ).all()

        restored_count = 0
        for simulation in active_simulations:
            # Mettre next_run_at à maintenant pour que le scheduler la lance immédiatement
            simulation.next_run_at = datetime.utcnow()
            simulation.is_running = False  # Le scheduler mettra True quand il lancera
            restored_count += 1
            print(f"  ↳ Simulation '{simulation.name}' prête à démarrer")

        if restored_count > 0:
            db.commit()
            print(f"✅ {restored_count} simulation(s) active(s) restaurée(s) et prête(s) à démarrer")
        else:
            print("ℹ️ No active simulation to re activate")

    finally:
        db.close()

  
    
    ####################################################################
    # 🤖 Agent V3 
    ####################################################################

    global agent_v3_runtime

    print("🤖 Initialisation de l'Agent V3 Orchestrator...")

    whoami_v3 = (
        "Act as an expert DeFi cryptos and trading. You are FedEdge a helpful Defi co pilot "
        "You manage user wallets, a knowledge database, "
        "run paper trading simulations and improve a small teacher model."
    )
    tools_v3 = ["get_market_cap", "get_crypto_prices", "get_world_state", "get_wallet_state", "process_news_article"]
    mission_v3 = "User assistance, market/world context, RAG curation, paper trading simulations."

    agent_v3_runtime = get_agent_v3_runtime(
        llm_pool=llm_pool,
        whoami=whoami_v3,
        mission=mission_v3,
        tools=tools_v3,
        use_real_tools=True,
        agent_id="fededge_core_v3",
    )

    await agent_v3_runtime.start()
    print("✅ Agent V3 Orchestrator démarré")

    # Vider l'historique du chat au démarrage
    await agent_v3_runtime.clear_chat_history()
    print("✅ Agent V3 historique de chat vidé au démarrage")

    init_chat_worker_agent_v3(agent_v3_runtime)
    print("✅ Chat Worker Agent V3 initialisé")

    # Configurer le broadcaster de conscience
    from backend.agent_consciousness import get_consciousness_broadcaster
    broadcaster = get_consciousness_broadcaster()
    broadcaster.set_websocket_manager(ws_manager)
    print("✅ Consciousness broadcaster configuré")

    # Initialiser l'event router
    from backend.agent_event_router import init_event_router
    event_router = init_event_router(agent_v3_runtime)
    print("✅ Event router initialisé - routing news/prices/wallets vers agent V3")

    ####################################################################

    # 📰 Diffuser immédiatement les news en cache (RAPIDE - non bloquant)
    async def broadcast_cached_news_startup():
        try:
            from .tasks.analysis_tasks import broadcast_cached_news
            await asyncio.sleep(2)  # Attendre que le WebSocket soit prêt
            print("📢 Diffusion des news en cache...")
            await broadcast_cached_news()
        except Exception as e:
            print(f"⚠️ Erreur diffusion news cache: {e}")

    asyncio.create_task(broadcast_cached_news_startup())

    # 📰 Bootstrap minimal si DB vide (uniquement si nécessaire)
    try:
        from backend.tasks.analysis_tasks import ensure_initial_news_in_db
        await ensure_initial_news_in_db()
        print("✅ Initial news bootstrap completed (si nécessaire)")
    except Exception as e:
        print(f"⚠️ Error bootstrapping news: {e}")

    # 🚀 Collecte de news fraîches en BACKGROUND DIFFÉRÉ (après 30s)
    async def collect_news_background():
        try:
            from backend.tasks.analysis_tasks import collect_and_broadcast_news
            await asyncio.sleep(30)  # Attendre 30s pour ne pas surcharger le démarrage
            print("📰 Collecting fresh news in background (delayed)...")
            await collect_and_broadcast_news()
            print("✅ Fresh news collected and broadcasted")
        except Exception as e:
            print(f"⚠️ Error collecting news in background: {e}")
            import traceback
            traceback.print_exc()

    asyncio.create_task(collect_news_background())

    # 📊 Envoyer les prix market immédiatement au démarrage
    async def send_initial_market_prices():
        try:
            await asyncio.sleep(5)  # Attendre 5s que tout soit prêt
            from backend.collectors.price_collector import fetch_crypto_prices
            from backend.agent_event_router import get_event_router

            print("📊 Fetching initial market prices...")
            prices = fetch_crypto_prices()

            if prices:
                # Convertir au format attendu
                market_data = {}
                for crypto_id, price_info in prices.items():
                    if isinstance(price_info, dict):
                        market_data[crypto_id] = price_info.get('usd', 0)
                    else:
                        market_data[crypto_id] = price_info

                # Envoyer au router
                router = get_event_router()
                if router:
                    await router.route_market_update(market_data)
                    print(f"✅ Initial market prices sent to agent: {len(market_data)} cryptos")
        except Exception as e:
            print(f"⚠️ Error sending initial market prices: {e}")

    asyncio.create_task(send_initial_market_prices())

    # 📊 Collecte de prix market en BACKGROUND (toutes les 5 minutes)
    async def collect_market_prices_loop():
        """Envoie les prix market à l'agent toutes les 5 minutes"""
        try:
            await asyncio.sleep(10)  # Attendre 10s au démarrage
            print("📊 Starting market prices collector loop...")

            while True:
                try:
                    from backend.collectors.price_collector import fetch_crypto_prices
                    from backend.agent_event_router import get_event_router

                    # Récupérer les prix
                    prices = fetch_crypto_prices()

                    if prices:
                        # Convertir au format attendu par l'agent
                        market_data = {}
                        for crypto_id, price_info in prices.items():
                            if isinstance(price_info, dict):
                                market_data[crypto_id] = price_info.get('usd', 0)
                            else:
                                market_data[crypto_id] = price_info

                        # Envoyer au router d'événements
                        router = get_event_router()
                        if router:
                            await router.route_market_update(market_data)
                            print(f"📊 Market prices sent to agent: {len(market_data)} cryptos")
                        else:
                            print("⚠️ Event router not available")
                    else:
                        print("⚠️ No market prices fetched")

                except Exception as e:
                    print(f"⚠️ Error in market collector loop: {e}")

                # Attendre 5 minutes avant la prochaine collecte
                await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            print(f"❌ Market collector loop crashed: {e}")
            import traceback
            traceback.print_exc()

    asyncio.create_task(collect_market_prices_loop())

    # 🤖 Restaurer l'état du bot de trading
    async def restore_trading_bot():
        try:
            await asyncio.sleep(3)  # Attendre que tout soit prêt
            from .services.trading_bot_service import get_trading_bot_service
            bot_service = get_trading_bot_service()

            if bot_service.restore_state():
                print("🔄 Bot de trading était actif, redémarrage...")
                result = await bot_service.start_bot()
                if result.get("success"):
                    print("✅ Bot de trading redémarré automatiquement")
                else:
                    print(f"⚠️ Erreur redémarrage bot: {result.get('message')}")
            else:
                print("ℹ️ Bot de trading était arrêté, pas de redémarrage")

        except Exception as e:
            print(f"⚠️ Erreur restauration bot: {e}")

    asyncio.create_task(restore_trading_bot())

    # Start the scheduler (optimized or fallback)
    if USING_ASYNC_SCHEDULER:
        print("🚀 Utilisation du scheduler asynchrone optimisé")
        start_non_blocking_scheduler()
    else:
        print("⚠️ Utilisation du scheduler classique (non-optimisé)")
        start_scheduler()

    # Log des optimisations actives
    print(f"📊 WebSocket Manager: {'Optimisé ✅' if USING_OPTIMIZED_WS else 'Standard ⚠️'}")
    print(f"📊 Scheduler: {'Non-bloquant ✅' if USING_ASYNC_SCHEDULER else 'Standard ⚠️'}")

    # Pré-charger les données de marché et prix en arrière-plan
    async def preload_market_data():
        try:
            print("📊 Pré-chargement des données de marché en arrière-plan...")
            from .collectors.finance_collector import get_complete_finance_analysis
            get_complete_finance_analysis(use_cache=False)
            print("✅ Données de marché pré-chargées")

            # Pré-charger les prix pour cache immédiat
            print("💰 Pré-chargement des prix crypto...")
            from .tasks.analysis_tasks import collect_and_broadcast_prices
            await collect_and_broadcast_prices()
            print("✅ Prix crypto pré-chargés dans le cache")

        except Exception as e:
            print(f"⚠️ Erreur pré-chargement: {e}")

    asyncio.create_task(preload_market_data())


@app.on_event("shutdown")
async def shutdown_event():
    """Arrêt propre de tous les services"""
    print("🛑 Arrêt de FedEdge AI Backend...")
    print("✅ FedEdge AI Backend arrêté proprement")


#######################################
#
#  WebSockets
#
##########################################


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await ws_manager.connect(websocket, client_id)

    # Capture client IP from WebSocket connection
    client_ip = None
    try:
        # Try to get real IP from headers (if behind proxy)
        if hasattr(websocket, 'headers'):
            x_forwarded_for = websocket.headers.get('x-forwarded-for')
            x_real_ip = websocket.headers.get('x-real-ip')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0].strip()
            elif x_real_ip:
                client_ip = x_real_ip

        # Fallback to direct client address
        if not client_ip and hasattr(websocket.client, 'host'):
            client_ip = websocket.client.host

        print(f"================🌐 WebSocket client connected: {client_id} from IP: {client_ip}")
    except Exception as e:
        print(f"⚠️ Could not detect client IP: {e}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            print(f" ================🌐  Received message from {client_id}: {message}")

            if message["type"] == "test_connection":
                print(f"✅ Test connection from {client_id}: {message['payload']}")

            elif message["type"] == "request_prices":
                print(f"💰 Request prices from {client_id}")
                from .tasks.analysis_tasks import (
                    get_latest_cached_prices,
                    trigger_price_collection_background
                )

                # A. Retour immédiat du dernier cache connu
                cached_prices = get_latest_cached_prices()
                if cached_prices:
                    print(f"💰 DEBUG: Nombre de prix dans le cache: {len(cached_prices)}")
                    print(f"💰 DEBUG: Exemple - Bitcoin: {cached_prices.get('bitcoin', 'N/A')}")
                    await websocket.send_text(json.dumps({
                        "type": "price_update",
                        "payload": cached_prices
                    }))
                    print(f"⚡ Prix du cache envoyés immédiatement à {client_id}")
                else:
                    # Pas de cache disponible, indiquer au frontend
                    await websocket.send_text(json.dumps({
                        "type": "price_update",
                        "payload": {},
                        "status": "loading"
                    }))
                    print(f"⚠️ Pas de cache, collecte nécessaire pour {client_id}")

                # B. Déclenche collecte en arrière-plan (non-bloquant)
                asyncio.create_task(trigger_price_collection_background())

            elif message["type"] == "stop_stream":
                print(f"🛑 STOP STREAM requested for {client_id}")
                ws_manager.stop_stream(client_id)
                await websocket.send_text(json.dumps({"type": "chat_stream_end", "payload": {}}))

            elif message["type"] == "chat_message":
                print(f"🎯 CHAT MESSAGE HANDLER TRIGGERED for {client_id}")
                print(f"🎯 =====================================")
                print(f"🎯 CHAT MESSAGE received  {message}")
                print(f"🎯 =====================================")

                ws_manager.set_streaming_state(client_id, True)

                print(f"🤖 Using Agent V3 Orchestrator for {client_id}")
                '''
                if agent_v3_runtime is None or not agent_v3_runtime._started:
                    await websocket.send_text(json.dumps({
                        "type": "chat_token",
                        "payload": {"token": "Agent V3 not initialized. Please wait a moment and try again."}
                    }))
                    await websocket.send_text(json.dumps({"type": "chat_stream_end"}))
                    ws_manager.set_streaming_state(client_id, False)
                    continue
                '''

                chat_worker_v3 = get_chat_worker_agent_v3()

                user_message = message["payload"]
                conversation_id = message.get("conversation_id", client_id)
                frontend_history = message.get("conversation_history", [])

                history = [msg for msg in frontend_history if msg.get("role") != "system"]

                print(f"🤖 Agent V3 chat: user='{user_message}', conv_id={conversation_id}")
                print(f"🤖 Agent V3 chat: history={history}")

                try:
                    accumulated_response = ""

                    async for event in chat_worker_v3.stream_chat(
                        user_text=user_message,
                        history=history,
                        conversation_id=conversation_id,
                    ):
                        if isinstance(event, dict):
                            event_type = event.get("type")

                            if event_type == "status":
                                status = event.get("status")
                                tool_name = event.get("tool_name")
                                await websocket.send_text(json.dumps({
                                    "type": "chat_status",
                                    "payload": {
                                        "status": status,
                                        **({"tool_name": tool_name} if tool_name else {})
                                    }
                                }))

                            elif event_type == "token":
                                chunk = event.get("token", "")
                                if chunk:
                                    accumulated_response += chunk
                                    await websocket.send_text(json.dumps({
                                        "type": "chat_token",
                                        "payload": {"token": chunk}
                                    }))

                            elif event_type == "done":
                                pass

                    ws_manager.add_to_conversation_history(client_id, "user", user_message)
                    ws_manager.add_to_conversation_history(client_id, "assistant", accumulated_response)
                    ws_manager.trim_conversation_history(client_id, max_tokens=4000)

                    await websocket.send_text(json.dumps({"type": "chat_stream_end"}))
                    ws_manager.set_streaming_state(client_id, False)

                    print(f"✅ Agent V3 chat completed: {len(accumulated_response)} chars")
                    continue

                except Exception as e:
                    logger.error(f"❌ Agent V3 chat error: {e}", exc_info=True)
                    await websocket.send_text(json.dumps({
                        "type": "chat_token",
                        "payload": {"token": f"[Agent V3 Error: {str(e)}]"}
                    }))
                    await websocket.send_text(json.dumps({"type": "chat_stream_end"}))
                    ws_manager.set_streaming_state(client_id, False)
                    continue

            elif message["type"] == "clear_conversation":
                ws_manager.clear_conversation_history(client_id)

                # Vider aussi l'historique de l'agent V3
                if agent_v3_runtime:
                    try:
                        await agent_v3_runtime.clear_chat_history()
                        logger.info(f"Agent V3 chat history cleared for client {client_id}")
                    except Exception as e:
                        logger.error(f"Error clearing agent V3 history: {e}")

                response = {
                    "type": "conversation_cleared",
                    "payload": {"message": "Conversation effacée avec succès"}
                }
                await websocket.send_text(json.dumps(response))

            elif message["type"] == "request_trades_history":
                wallet_name = message["payload"].get("wallet_name", "default")
                limit = message["payload"].get("limit", 100)

                db = SessionLocal()
                try:
                    wallet = crud.get_wallet_by_name(db, wallet_name)
                    if not wallet:
                        wallet = crud.create_wallet(db, name=wallet_name)

                    all_transactions = crud.get_wallet_transactions(db, wallet.id)
                    transactions = sorted(all_transactions, key=lambda x: x.timestamp, reverse=True)[:limit]
                    total_count = len(all_transactions)

                    trades_data = []
                    for tx in transactions:
                        asset = crud.get_asset(db, tx.asset_id)
                        reasoning = tx.reasoning if tx.reasoning else "Pas de reasoning disponible pour ce trade"
                        trade_info = {
                            "id": tx.id,
                            "timestamp": tx.timestamp.isoformat(),
                            "type": tx.type.value.upper(),
                            "asset_symbol": asset.symbol if asset else tx.asset_id,
                            "asset_name": asset.name if asset else tx.asset_id,
                            "quantity": str(tx.amount),
                            "price_at_time": str(tx.price_at_time),
                            "fee": str(tx.fees) if tx.fees else "0",
                            "notes": reasoning,
                            "reasoning": reasoning
                        }
                        trades_data.append(trade_info)

                    response = {
                        "type": "trades_history",
                        "payload": {
                            "wallet_name": wallet_name,
                            "wallet_id": wallet.id,
                            "trades": trades_data,
                            "total_count": total_count,
                            "displayed_count": len(trades_data),
                            "has_more": total_count > limit
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    print(f"✅ Historique des trades envoyé à {client_id}: {len(trades_data)}/{total_count} trades")

                except Exception as e:
                    error_response = {
                        "type": "trades_history",
                        "payload": {
                            "error": f"Erreur lors de la récupération des trades: {str(e)}",
                            "trades": []
                        }
                    }
                    await websocket.send_text(json.dumps(error_response))
                    print(f"❌ Erreur récupération trades pour {client_id}: {e}")
                finally:
                    db.close()

            elif message["type"] == "trading_decision":
                print(f"Trading decision received from {client_id}: {message['payload']}")
                # Optionnel: persister ou traiter

            elif message["type"] == "client_connected":
                print(f"🌐 CLIENT_CONNECTED message received, client_ip={client_ip}")
                try:
                    from fededge_node_client import FedEdgeNodeClient
                    node_client = FedEdgeNodeClient()
                    print(f"📤 Calling start_session with client_ip={client_ip}")
                    result = node_client.start_session(client_ip=client_ip)
                    print(f"✅ Client session updated with IP: {client_ip}, result: {result}")
                except Exception as e:
                    print(f"❌ Error updating session with client IP: {e}")
                    import traceback
                    traceback.print_exc()

            elif message["type"] == "get_node_info":
                try:
                    from fededge_node_client import FedEdgeNodeClient
                    node_client = FedEdgeNodeClient()
                    info = node_client.get_node_info()
                    response = {
                        "type": "node_info",
                        **info
                    }
                    await websocket.send_text(json.dumps(response))
                except Exception as e:
                    print(f"❌ Error getting node info: {e}")

            elif message["type"] == "register_node":
                try:
                    from fededge_node_client import FedEdgeNodeClient
                    node_client = FedEdgeNodeClient()
                    result = node_client.register_user(
                        email=message.get("email", ""),
                        name=message.get("name", ""),
                        client_ip=client_ip
                    )
                    response = {
                        "type": "registration_result",
                        **result
                    }
                    await websocket.send_text(json.dumps(response))

                    info = node_client.get_node_info()
                    node_info_response = {
                        "type": "node_info",
                        **info
                    }
                    await websocket.send_text(json.dumps(node_info_response))
                except Exception as e:
                    print(f"❌ Error registering node: {e}")
                    error_response = {
                        "type": "registration_result",
                        "success": False,
                        "message": f"Error: {str(e)}"
                    }
                    await websocket.send_text(json.dumps(error_response))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        print(f"Client {client_id} disconnected")
