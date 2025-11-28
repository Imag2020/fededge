from ..websocket_manager import get_websocket_manager
from ..db.models import SessionLocal
from ..db import crud
from ..config_manager import config_manager
from ..collectors.finance_collector import get_complete_finance_analysis, format_finance_analysis_for_llm
import asyncio
import json

import random
import datetime
import concurrent.futures
import threading
import logging

import re
import json
import sys
import os
from contextlib import contextmanager

# Logger sécurisé pour éviter les erreurs I/O operation on closed file
def safe_log(message, level="info"):
    """Log sécurisé qui évite les erreurs I/O operation on closed file"""
    try:
        logger = logging.getLogger("trading_tasks")
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    except:
        pass  # Éviter les crashs de logging

async def run_in_thread(func, *args, **kwargs):
    """Exécute une fonction dans un thread séparé de manière compatible avec toutes les versions Python"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))



def _build_llm_debug_payload(agent_name: str, session_tag: str, summary: str, details: dict):
    """Construit un payload WebSocket conforme au frontend (type: debug_log)"""
    import datetime as _dt
    return {
        "type": "debug_log",
        "payload": {
            "step": {
                "step_type": "LLM_EXCHANGE",
                "timestamp": _dt.datetime.utcnow().isoformat(),
                "message": summary,
                "data": details or {}
            },
            "session_info": {
                "asset_ticker": session_tag
            }
        }
    }

def get_wallet_state_for_llm(db, wallet_id):
    """Récupère l'état du wallet formaté pour le LLM"""
    try:
        from ..db import crud
        from ..analytics.asset_stats import asset_analyzer
        
        # Récupérer le wallet
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            return "Wallet not found"
        
        # Récupérer les holdings
        holdings = crud.get_wallet_holdings(db, wallet_id)
        wallet_value = crud.calculate_wallet_value(db, wallet_id)
        
        # Récupérer les prix actuels pour chaque asset
        holdings_detail = []
        for holding in holdings:
            try:
                # Utiliser asset_analyzer pour obtenir les données de marché récentes
                market_data = asset_analyzer.get_asset_market_chart(holding.asset_id, days=1)
                if market_data and 'prices' in market_data and market_data['prices']:
                    # Prendre le prix le plus récent
                    current_price = market_data['prices'][-1][1]  # [timestamp, price]
                else:
                    current_price = holding.average_buy_price
                
                # Calculer les métriques (convertir en float pour éviter les problèmes Decimal)
                current_value = float(holding.quantity) * float(current_price)
                cost_basis = float(holding.quantity) * float(holding.average_buy_price)
                pnl = current_value - cost_basis
                pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                
                holdings_detail.append({
                    "asset_id": holding.asset_id,
                    "quantity": float(holding.quantity),
                    "average_buy_price": float(holding.average_buy_price),
                    "current_price": float(current_price),
                    "current_value": float(current_value),
                    "pnl": float(pnl),
                    "pnl_percentage": float(pnl_percentage)
                })
            except Exception as e:
                safe_log(f"Erreur récupération prix pour {holding.asset_id}: {e}", "error")
                # Utiliser le prix d'achat moyen comme fallback
                current_price = holding.average_buy_price
                holdings_detail.append({
                    "asset_id": holding.asset_id,
                    "quantity": float(holding.quantity),
                    "average_buy_price": float(holding.average_buy_price),
                    "current_price": float(current_price),
                    "current_value": float(holding.quantity * current_price),
                    "pnl": 0,
                    "pnl_percentage": 0
                })
        
        # Récupérer les transactions récentes
        recent_transactions = crud.get_wallet_transactions(db, wallet_id, limit=5)
        
        # Extraire la liste des asset IDs pour guider le LLM
        available_assets = [holding.asset_id for holding in holdings]
        
        wallet_state = {
            "wallet_id": wallet_id,
            "wallet_name": wallet.name,
            "total_value": float(wallet_value["total_value"]),
            "holdings_count": len(holdings),
            "available_asset_ids": available_assets,  # Liste explicite pour le LLM
            "holdings": holdings_detail,
            "recent_transactions": [
                {
                    "asset_id": tx.asset_id,
                    "type": tx.type.value,
                    "amount": float(tx.amount),  # Utilise 'amount' au lieu de 'quantity'
                    "price": float(tx.price_at_time),
                    "timestamp": tx.timestamp.isoformat()
                }
                for tx in recent_transactions
            ]
        }
        
        return json.dumps(wallet_state, indent=2)
        
    except Exception as e:
        safe_log(f"Erreur récupération wallet state: {e}", "error")
        return f"Error retrieving wallet state: {str(e)}"

def extract_json_from_markdown(text):
    # Supprimer les balises ```json et ```
    cleaned = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)
    


async def run_simulation(simulation_id: int):
    """
    Exécuter une simulation spécifique
    """
    from ..db.models import SessionLocal
    from ..db import crud
    from ..utils.debug_logger import get_debug_logger
    from ..utils.session_logger import get_session_logger
    from datetime import datetime, timedelta
    
    debug = get_debug_logger()
    file_logger = get_session_logger()
    
    db = SessionLocal()
    simulation = None
    session_id = None
    file_session_id = None

    try:
        # Récupérer la simulation
        simulation = crud.get_simulation(db, simulation_id)
        if not simulation or not simulation.is_active:
            safe_log(f"⚠️ Simulation {simulation_id} non trouvée ou inactive", "warning")
            return

        # Marquer la simulation comme en cours d'exécution
        crud.set_simulation_running(db, simulation_id, True)

        # Démarrer la session de logging (remplacer espaces par underscores)
        safe_name = simulation.name.replace(" ", "_").replace("-", "_")
        session_id = debug.start_analysis_session("SIM", f"simulation_{safe_name}")
        file_session_id = file_logger.start_session("SIM", f"simulation_{safe_name}")
        ws_manager = get_websocket_manager()

        safe_log(f"🎮 Démarrage simulation '{simulation.name}' (Strategy: {simulation.strategy})")
        file_logger.write_log("SIMULATION_START", f"🎮 Démarrage simulation '{simulation.name}'", {
            'simulation_id': simulation_id,
            'strategy': simulation.strategy,
            'wallet_id': simulation.wallet_id
        })

        # Yield pour permettre au backend de traiter d'autres requêtes
        await asyncio.sleep(0.01)

        # ✅ Utilisation du nouveau FedAgent SimWorker avec LLM
        from ..fedagent_service import get_sim_worker
        from ..analytics.asset_stats import asset_analyzer
        from datetime import datetime, timedelta

        safe_log("🤖 Lancement simulation avec FedAgent SimWorker (LLM)")
        file_logger.write_log("SIM_START", "Démarrage simulation avec LLM", {
            'simulation_id': simulation_id,
            'wallet_id': simulation.wallet_id
        })

        # Récupérer le sim_worker
        sim_worker = get_sim_worker()

        # 1. Préparer le wallet state
        wallet_state_json = get_wallet_state_for_llm(db, simulation.wallet_id)
        wallet_state = json.loads(wallet_state_json)

        safe_log(f"📊 Wallet state: {len(wallet_state.get('holdings', []))} holdings, total value: ${wallet_state.get('total_value', 0):.2f}")

        # 2. Récupérer les données de marché (top gainers/losers)
        try:
            # Récupérer les top 10 cryptos par market cap
            market_list = asset_analyzer.session.get(
                    f"{asset_analyzer.base_url}/coins/markets",
                    params={
                        'vs_currency': 'usd',
                        'order': 'market_cap_desc',
                        'per_page': 20,
                        'page': 1,
                        'sparkline': False,
                        'price_change_percentage': '24h'
                    },
                timeout=10
            ).json()

            # Trier par gains/pertes
            sorted_by_change = sorted(market_list, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
            top_gainers = sorted_by_change[:10]
            top_losers = sorted_by_change[-10:]

            # Construire le dictionnaire de prix actuels
            current_prices = {coin['id']: coin['current_price'] for coin in market_list}

            # Ajouter les prix des assets du wallet si non présents
            for holding in wallet_state.get('holdings', []):
                asset_id = holding['asset_id']
                if asset_id not in current_prices:
                    try:
                        price_data = asset_analyzer.session.get(
                            f"{asset_analyzer.base_url}/simple/price",
                            params={'ids': asset_id, 'vs_currencies': 'usd'},
                            timeout=5
                        ).json()
                        if asset_id in price_data:
                            current_prices[asset_id] = price_data[asset_id]['usd']
                    except Exception as e:
                        safe_log(f"⚠️ Impossible de récupérer le prix pour {asset_id}: {e}", "warning")

            market_data = {
                'current_prices': current_prices,
                'top_gainers': [
                    {
                        'id': c['id'],
                        'symbol': c['symbol'],
                        'name': c['name'],
                        'price': c['current_price'],
                        'change_24h': c.get('price_change_percentage_24h', 0)
                    } for c in top_gainers
                ],
                'top_losers': [
                    {
                        'id': c['id'],
                        'symbol': c['symbol'],
                        'name': c['name'],
                        'price': c['current_price'],
                        'change_24h': c.get('price_change_percentage_24h', 0)
                    } for c in top_losers
                ]
            }

            safe_log(f"📈 Marché: {len(top_gainers)} gainers, {len(top_losers)} losers")

        except Exception as e:
            safe_log(f"⚠️ Erreur récupération market data: {e}", "warning")
            market_data = {
                'current_prices': {},
                'top_gainers': [],
                'top_losers': []
            }

        # 3. Contexte monde (optionnel - récupérer les dernières news importantes)
        world_context = "No recent major news or events"
        try:
            # Récupérer les événements récents de la table semantic_kv (world state)
            from ..fedagent.db_helpers import get_semantic_kv
            recent_event = get_semantic_kv(sim_worker.conn, "crypto_world.last_major_event")
            if recent_event:
                world_context = f"Recent event: {recent_event.get('title', 'N/A')}"
                safe_log(f"🌍 World context: {world_context}")
        except Exception as e:
            safe_log(f"⚠️ Pas de world context disponible: {e}", "warning")

        # 4. Appeler le sim_worker pour obtenir une décision LLM
        safe_log("🧠 Appel du LLM pour décision de trading...")

        sim_result = await sim_worker.simulate({
            'wallet_state': wallet_state,
            'market_data': market_data,
            'world_context': world_context,
            'db_session': db
        })

        # 5. Logger le résultat
        decision = sim_result.get('decision', {})
        trade = sim_result.get('trade')
        error = sim_result.get('error')

        if error:
            safe_log(f"❌ Erreur simulation: {error}", "error")
            file_logger.write_log("SIM_ERROR", f"Erreur: {error}", sim_result)
            raise Exception(error)

        action = decision.get('action', 'hold')
        safe_log(f"🎯 Décision LLM: {action.upper()}")
        safe_log(f"💡 Raisonnement: {decision.get('reasoning', 'N/A')}")

        if sim_result.get('trade_executed'):
            safe_log(f"✅ Trade exécuté: {trade}")
            file_logger.write_log("TRADE_EXECUTED", "Trade paper exécuté", trade)

            # Envoyer notification WebSocket au frontend
            await ws_manager.broadcast({
                'type': 'trade_executed',
                'payload': {
                    'simulation_id': simulation_id,
                    'simulation_name': simulation.name,
                    'trade': trade,
                    'decision': decision,
                    'wallet_id': simulation.wallet_id
                }
            })
        else:
            safe_log(f"⏸️ Aucun trade (action: {action})")
            file_logger.write_log("NO_TRADE", f"Action {action}, pas de trade", decision)

        # 6. Mettre à jour les statistiques de la simulation
        next_run = datetime.utcnow() + timedelta(minutes=simulation.frequency_minutes)
        crud.update_simulation_stats(
            db, simulation_id,
            last_run_at=datetime.utcnow(),
            next_run_at=next_run,
            success=True,
            error=None
        )

        safe_log(f"✅ Simulation terminée. Prochain run: {next_run.strftime('%H:%M:%S')}")
        file_logger.write_log("SIM_SUCCESS", "Simulation terminée avec succès", {
            'next_run': next_run.isoformat(),
            'decision': decision
        })

    except Exception as e:
        error_msg = str(e)
        safe_log(f"❌ Erreur simulation '{simulation.name if simulation else 'Unknown'}': {error_msg}", "error")

        # Log enrichi pour les erreurs DSPy
        if "JSONAdapter failed to parse" in error_msg or "Expected to find output fields" in error_msg:
            safe_log(f"⚠️  [SIMULATION {simulation_id}] ━━━ ERREUR DSPy JSON PARSING ━━━")
            safe_log(f"    🤖 Le LLM (Gemma 3 1B sur port 9001) génère du JSON malformé")
            safe_log(f"    💡 Solution: Utiliser un modèle plus puissant (Gemini Flash 2.0) ou améliorer les prompts")
            safe_log(f"    📄 Erreur complète: {error_msg[:500]}")

        if file_session_id:
            file_logger.write_log("SIMULATION_ERROR", f"❌ Erreur simulation: {error_msg}", {
                'error': error_msg,
                'error_type': type(e).__name__,
                'simulation_id': simulation_id,
                'simulation_name': simulation.name if simulation else 'Unknown',
                'strategy': simulation.strategy if simulation else 'Unknown'
            })

        # Calculer quand même la prochaine exécution (en cas d'erreur temporaire)
        if simulation:
            next_run = datetime.utcnow() + timedelta(minutes=simulation.frequency_minutes)

            # Mettre à jour les statistiques d'échec
            crud.update_simulation_stats(
                db, simulation_id,
                last_run_at=datetime.utcnow(),
                next_run_at=next_run,
                success=False,
                error=error_msg
            )

    finally:
        # CRITIQUE: Toujours démarquer la simulation, même en cas d'erreur
        try:
            if simulation:
                crud.set_simulation_running(db, simulation_id, False)
                safe_log(f"🔓 Simulation {simulation_id} déverrouillée (is_running=False)")
        except Exception as unlock_error:
            safe_log(f"❌ CRITIQUE: Impossible de déverrouiller la simulation {simulation_id}: {unlock_error}", "error")

        # Terminer les sessions de logging
        try:
            if file_session_id:
                file_logger.end_session('SUCCESS' if 'error_msg' not in locals() else 'ERROR')
            if session_id:
                debug.end_analysis_session(session_id)
        except Exception as log_error:
            safe_log(f"⚠️ Erreur fermeture logs: {log_error}", "warning")

        # Fermer la DB
        try:
            db.close()
        except Exception as db_error:
            safe_log(f"⚠️ Erreur fermeture DB: {db_error}", "warning")

async def run_all_simulations():
    """
    Tâche schedulée pour exécuter toutes les simulations prêtes
    """
    from ..db.models import SessionLocal
    from ..db import crud
    from datetime import datetime
    
    current_time = datetime.utcnow()
    safe_log(f"🎮 [{current_time.strftime('%H:%M:%S')}] Vérification des simulations à exécuter...")
    
    db = SessionLocal()
    try:
        # Récupérer toutes les simulations actives prêtes à être exécutées
        simulations_to_run = crud.get_active_simulations_to_run(db)
        
        # Log détaillé de l'état des simulations
        all_active_simulations = crud.get_simulations(db, active_only=True)
        safe_log(f"📊 État des simulations actives:")
        for sim in all_active_simulations:
            status = "✅ PRÊTE" if sim in simulations_to_run else "⏸️ EN ATTENTE"
            next_run_info = f"prochain run: {sim.next_run_at.strftime('%H:%M:%S')}" if sim.next_run_at else "pas de prochain run"
            last_run_info = f"dernier run: {sim.last_run_at.strftime('%H:%M:%S')}" if sim.last_run_at else "jamais exécutée"
            safe_log(f"   - {sim.name}: {status} | {next_run_info} | {last_run_info}")
        
        if not simulations_to_run:
            safe_log("📊 Aucune simulation à exécuter pour le moment")
            return
        
        safe_log(f"🎯 {len(simulations_to_run)} simulation(s) à exécuter:")
        for sim in simulations_to_run:
            safe_log(f"   - {sim.name} (ID: {sim.id}) - Fréquence: {sim.frequency_minutes}min")
        
        # Vérifier les simulations déjà en cours
        running_simulations = [sim for sim in all_active_simulations if sim.is_running]
        safe_log(f"📊 {len(running_simulations)} simulation(s) déjà en cours d'exécution")
        
        # Vérifier les simulations potentiellement bloquées (running depuis trop longtemps)
        SIMULATION_TIMEOUT_MINUTES = 30
        blocked_simulations = []

        for sim in running_simulations:
            if sim.last_run_at:
                minutes_since_start = (current_time - sim.last_run_at).total_seconds() / 60
                if minutes_since_start > SIMULATION_TIMEOUT_MINUTES:
                    blocked_simulations.append(sim)
                    safe_log(f"⚠️ Simulation bloquée détectée: {sim.name} (ID: {sim.id}) - Running depuis {minutes_since_start:.1f} minutes", "warning")
            else:
                # Simulation marquée "running" mais jamais exécutée = deadlock
                blocked_simulations.append(sim)
                safe_log(f"⚠️ Simulation fantôme détectée: {sim.name} (ID: {sim.id}) - Marquée running mais jamais exécutée", "warning")
        
        # Forcer l'arrêt des simulations bloquées
        if blocked_simulations:
            safe_log(f"🔧 Forçage de l'arrêt de {len(blocked_simulations)} simulation(s) bloquée(s)...", "warning")
            for blocked_sim in blocked_simulations:
                try:
                    crud.set_simulation_running(db, blocked_sim.id, False)
                    # Programmer le prochain run immédiatement pour permettre le redémarrage
                    crud.update_simulation_stats(db, blocked_sim.id, next_run_at=current_time)
                    safe_log(f"   ✅ Simulation {blocked_sim.name} (ID: {blocked_sim.id}) forcée à l'arrêt")
                    running_simulations.remove(blocked_sim)
                except Exception as e:
                    safe_log(f"   ❌ Erreur lors du forçage d'arrêt de {blocked_sim.name}: {e}", "error")
        
        # Limiter les simulations concurrentes pour éviter de bloquer le système
        MAX_CONCURRENT_SIMULATIONS = 1
        
        if len(running_simulations) >= MAX_CONCURRENT_SIMULATIONS:
            safe_log(f"⚠️ {len(running_simulations)} simulations encore en cours après nettoyage, report de nouvelles exécutions", "warning")
            return
        
        if len(simulations_to_run) > MAX_CONCURRENT_SIMULATIONS:
            safe_log(f"⚠️ {len(simulations_to_run)} simulations à exécuter, limitation à {MAX_CONCURRENT_SIMULATIONS} pour éviter le blocage", "warning")
            simulations_to_run = simulations_to_run[:MAX_CONCURRENT_SIMULATIONS]
        
        # Exécuter chaque simulation en arrière-plan (non-bloquant)
        background_tasks = []
        for simulation in simulations_to_run:
            try:
                safe_log(f"⚡ Lancement de la simulation '{simulation.name}' (ID: {simulation.id}) en arrière-plan")
                # Créer une tâche asynchrone non-bloquante avec yield pour libérer l'event loop
                task = asyncio.create_task(run_simulation_background_yielding(simulation.id))
                background_tasks.append(task)
            except Exception as e:
                safe_log(f"❌ Erreur lors du lancement de la simulation {simulation.id}: {e}", "error")
        
        safe_log(f"✅ {len(background_tasks)} simulation(s) lancée(s) en arrière-plan (max concurrent: {MAX_CONCURRENT_SIMULATIONS})")
                
        safe_log("✅ Vérification des simulations terminée")
                
    finally:
        db.close()

async def run_simulation_background_yielding(simulation_id: int):
    """
    Wrapper qui exécute une simulation avec yields réguliers pour libérer l'event loop
    """
    from ..db.models import SessionLocal
    from ..db import crud
    
    try:
        safe_log(f"🏃 Simulation {simulation_id} démarrée en arrière-plan (avec yields)")
        
        # Yield immédiatement pour libérer l'event loop
        await asyncio.sleep(0.1)
        
        # Exécuter la simulation directement (sans autre DB session car async)
        await run_single_simulation(simulation_id)
        await asyncio.sleep(0.1)  # Libérer l'event loop
        
        safe_log(f"✅ Simulation {simulation_id} terminée avec succès en arrière-plan")
    except Exception as e:
        safe_log(f"❌ Erreur simulation en arrière-plan {simulation_id}: {str(e)}", "error")
        
        # Marquer la simulation comme non running en cas d'erreur
        db = SessionLocal()
        try:
            crud.set_simulation_running(db, simulation_id, False)
            crud.update_simulation_stats(db, simulation_id, failed=True, error=str(e)[:500])
        except:
            pass
        finally:
            db.close()

async def run_simulation_background(simulation_id: int):
    """
    Wrapper pour exécuter une simulation en arrière-plan sans bloquer le système
    """
    from ..db.models import SessionLocal
    from ..db import crud
    
    try:
        safe_log(f"🏃 Simulation {simulation_id} démarrée en arrière-plan")
        await run_simulation(simulation_id)
        safe_log(f"✅ Simulation {simulation_id} terminée avec succès en arrière-plan")
    except Exception as e:
        safe_log(f"❌ Erreur simulation en arrière-plan {simulation_id}: {str(e)}", "error")
        
        # Marquer la simulation comme non running en cas d'erreur
        db = SessionLocal()
        try:
            crud.set_simulation_running(db, simulation_id, False)
            crud.update_simulation_stats(db, simulation_id, failed=True, error=str(e)[:500])
        except:
            pass  # Ne pas faire échouer si la DB est inaccessible
        finally:
            db.close()

async def run_single_simulation(simulation_id: int) -> bool:
    """
    Exécuter une seule simulation (pour déclenchement manuel)
    Returns True si succès, False sinon
    """
    try:
        safe_log(f"🔥 Déclenchement manuel simulation ID: {simulation_id}")
        await run_simulation(simulation_id)
        safe_log(f"✅ Simulation {simulation_id} terminée avec succès")
        return True
    except Exception as e:
        safe_log(f"❌ Erreur simulation {simulation_id}: {str(e)}", "error")
        return False
