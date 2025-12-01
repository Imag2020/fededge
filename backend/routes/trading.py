"""
Trading & Simulation Routes
Handles trading simulations, bot management, and trading statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from ..db.models import SessionLocal, Simulation, Wallet, WalletTransaction
from ..db import crud
from ..config_manager import config_manager, TradingSimulationConfig
from ..services.trading_bot_service import get_trading_bot_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trading"])


# Pydantic models
class TradingSimulationCreate(BaseModel):
    id: str
    name: str
    wallet_id: str
    llm_id: str
    strategy: str
    risk_level: str
    budget: float
    is_active: bool = True

@router.post("/trading-simulations")

class BotConfigUpdate(BaseModel):
    updates: Dict[str, Any]

@router.put("/bot-config")



# ============== TRADING SIMULATIONS (Legacy) ==============

@router.get("/trading-simulations")
async def get_trading_simulations():
    """Récupérer toutes les simulations de trading"""
    try:
        simulations = config_manager.get_all_trading_simulations()
        
        sims_data = []
        for sim in simulations:
            # Récupérer le LLM associé
            llm = config_manager.get_llm(sim.llm_id)
            llm_name = llm.name if llm else "LLM inconnu"
            
            sim_data = {
                "id": sim.id,
                "name": sim.name,
                "wallet_id": sim.wallet_id,
                "llm_id": sim.llm_id,
                "llm_name": llm_name,
                "strategy": sim.strategy,
                "risk_level": sim.risk_level,
                "budget": sim.budget,
                "is_active": sim.is_active,
                "created_at": sim.created_at,
                "last_updated": sim.last_updated,
                "performance_stats": sim.performance_stats
            }
            sims_data.append(sim_data)
        
        return {"status": "success", "simulations": sims_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class TradingSimulationCreate(BaseModel):
    id: str
    name: str
    wallet_id: str
    llm_id: str
    strategy: str
    risk_level: str
    budget: float
    is_active: bool = True

@router.post("/trading-simulations")
async def create_trading_simulation(sim_data: TradingSimulationCreate):
    """Créer une nouvelle simulation de trading"""
    try:
        from datetime import datetime
        
        sim_config = TradingSimulationConfig(
            id=sim_data.id,
            name=sim_data.name,
            wallet_id=sim_data.wallet_id,
            llm_id=sim_data.llm_id,
            strategy=sim_data.strategy,
            risk_level=sim_data.risk_level,
            budget=sim_data.budget,
            is_active=sim_data.is_active,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        
        success = config_manager.add_trading_simulation(sim_config)
        if success:
            return {"status": "success", "message": f"Simulation {sim_data.name} créée avec succès"}
        else:
            return {"status": "error", "message": "Échec de la création de la simulation"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.delete("/trading-simulations/{sim_id}")
async def delete_trading_simulation(sim_id: str):
    """Supprimer une simulation de trading"""
    try:
        success = config_manager.remove_trading_simulation(sim_id)
        if success:
            return {"status": "success", "message": "Simulation supprimée avec succès"}
        else:
            return {"status": "error", "message": "Échec de la suppression de la simulation"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============== SIMULATIONS (New) ==============

@router.get("/simulations")
async def get_simulations(active_only: bool = False):
    """Récupérer toutes les simulations"""
    db = SessionLocal()
    try:
        simulations = crud.get_simulations(db, active_only=active_only)
        
        # Convertir en format JSON avec les relations
        simulations_data = []
        for sim in simulations:
            simulations_data.append({
                "id": sim.id,
                "name": sim.name,
                "description": sim.description,
                "wallet_id": sim.wallet_id,
                "wallet_name": sim.wallet.name if sim.wallet else "Unknown",
                "strategy": sim.strategy,
                "frequency_minutes": sim.frequency_minutes,
                "is_active": sim.is_active,
                "is_running": sim.is_running,
                "created_at": sim.created_at.isoformat() if sim.created_at else None,
                "last_run_at": sim.last_run_at.isoformat() if sim.last_run_at else None,
                "next_run_at": sim.next_run_at.isoformat() if sim.next_run_at else None,
                "total_runs": sim.total_runs,
                "successful_runs": sim.successful_runs,
                "failed_runs": sim.failed_runs,
                "success_rate": (sim.successful_runs / sim.total_runs * 100) if sim.total_runs > 0 else 0,
                "last_error": sim.last_error
            })
        
        return {"status": "success", "simulations": simulations_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.get("/simulations-wallet")
async def get_simulations_wallet():
    """Récupérer toutes les simulations avec leurs données de wallet détaillées"""
    db = SessionLocal()
    try:
        simulations = crud.get_simulations(db, active_only=False)
        
        simulations_wallet = []
        for sim in simulations:
            try:
                # Récupérer le wallet et ses données
                wallet = crud.get_wallet(db, sim.wallet_id)
                if not wallet:
                    continue
                
                # Calculer la valeur du wallet
                wallet_value = crud.calculate_wallet_value(db, sim.wallet_id)
                
                # Récupérer les holdings
                holdings = crud.get_wallet_holdings(db, sim.wallet_id)
                
                # Récupérer toutes les transactions pour le comptage
                all_transactions = crud.get_wallet_transactions(db, sim.wallet_id)
                # Récupérer les transactions récentes pour l'affichage
                recent_transactions = crud.get_wallet_transactions(db, sim.wallet_id, limit=10)
                
                # Calculer les statistiques de trading
                total_trades = len(all_transactions)
                winning_trades = 0  # Simplifier pour éviter les erreurs
                win_rate = 0
                
                # Calculer P&L (inclure le cash + holdings)
                initial_budget = float(wallet.initial_budget_usd) if wallet.initial_budget_usd else 0
                holdings_value = float(wallet_value.get("total_value", 0))  # Valeur des holdings
                cash_value = float(wallet.total_value_usd) if wallet.total_value_usd else 0  # Cash restant
                total_wallet_value = holdings_value  # La valeur totale est déjà dans holdings_value
                
                total_pnl = total_wallet_value - initial_budget
                pnl_percent = (total_pnl / initial_budget * 100) if initial_budget > 0 else 0
                
                # Formater les holdings pour l'affichage
                holdings_data = []
                for holding in holdings:
                    try:
                        # Récupérer l'asset pour obtenir son symbol
                        asset = crud.get_asset(db, holding.asset_id)
                        asset_symbol = asset.symbol if asset else holding.asset_id.upper()
                        
                        # Récupérer les prix actuels
                        from .analytics.asset_stats import asset_analyzer
                        market_data = asset_analyzer.get_asset_market_chart(holding.asset_id, days=1)
                        current_price = market_data['prices'][-1][1] if market_data and 'prices' in market_data and market_data['prices'] else float(holding.average_buy_price)
                        
                        current_value = float(holding.quantity) * current_price
                        cost_basis = float(holding.quantity) * float(holding.average_buy_price)
                        holding_pnl = current_value - cost_basis
                        holding_pnl_percent = (holding_pnl / cost_basis * 100) if cost_basis > 0 else 0
                        
                        holdings_data.append({
                            "asset_id": holding.asset_id,
                            "asset_symbol": asset_symbol,
                            "quantity": float(holding.quantity),
                            "average_buy_price": float(holding.average_buy_price),
                            "current_price": current_price,
                            "current_value": current_value,
                            "pnl": holding_pnl,
                            "pnl_percent": holding_pnl_percent
                        })
                    except Exception as e:
                        # Fallback en cas d'erreur
                        asset = crud.get_asset(db, holding.asset_id)
                        asset_symbol = asset.symbol if asset else holding.asset_id.upper()
                        holdings_data.append({
                            "asset_id": holding.asset_id,
                            "asset_symbol": asset_symbol,
                            "quantity": float(holding.quantity),
                            "average_buy_price": float(holding.average_buy_price),
                            "current_price": float(holding.average_buy_price),
                            "current_value": float(holding.quantity) * float(holding.average_buy_price),
                            "pnl": 0,
                            "pnl_percent": 0
                        })
                
                simulation_data = {
                    "id": sim.id,
                    "name": sim.name,
                    "description": sim.description,
                    "wallet_name": wallet.name,
                    "wallet_id": sim.wallet_id,
                    "strategy": sim.strategy,
                    "frequency_minutes": sim.frequency_minutes,
                    "is_active": sim.is_active,
                    "is_running": sim.is_running,
                    
                    # Données financières
                    "total_value": total_wallet_value,  # Valeur totale corrigée (cash + holdings)
                    "initial_budget": initial_budget,
                    "total_pnl": total_pnl,
                    "pnl_percent": pnl_percent,
                    "assets_count": len(holdings),
                    
                    # Statistiques de trading
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                    "successful_runs": sim.successful_runs,
                    "total_runs": sim.total_runs,
                    "success_rate": (sim.successful_runs / sim.total_runs * 100) if sim.total_runs > 0 else 0,
                    
                    # Détails des holdings
                    "holdings": holdings_data,
                    
                    # Dernière exécution
                    "last_run_at": sim.last_run_at.isoformat() if sim.last_run_at else None,
                    "next_run_at": sim.next_run_at.isoformat() if sim.next_run_at else None,
                    "last_error": sim.last_error
                }
                
                simulations_wallet.append(simulation_data)
                
            except Exception as e:
                print(f"Erreur récupération données simulation {sim.id}: {e}")
                continue
        
        return {"status": "success", "simulations": simulations_wallet}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.post("/simulations")
async def create_simulation(simulation_data: dict):
    """Créer une nouvelle simulation"""
    db = SessionLocal()
    try:
        # Validation des données requises
        required_fields = ['name', 'wallet_id', 'strategy', 'frequency_minutes']
        for field in required_fields:
            if field not in simulation_data:
                return {"status": "error", "message": f"Champ requis manquant: {field}"}
        
        # Vérifier que le wallet existe
        wallet = crud.get_wallet(db, simulation_data['wallet_id'])
        if not wallet:
            return {"status": "error", "message": "Wallet non trouvé"}
        
        # Vérifier l'unicité du nom
        existing = crud.get_simulation_by_name(db, simulation_data['name'])
        if existing:
            return {"status": "error", "message": "Une simulation avec ce nom existe déjà"}
        
        # Créer la simulation
        simulation = crud.create_simulation(
            db=db,
            name=simulation_data['name'],
            wallet_id=simulation_data['wallet_id'],
            strategy=simulation_data['strategy'],
            frequency_minutes=simulation_data['frequency_minutes'],
            description=simulation_data.get('description', '')
        )
        
        # Calculer la prochaine exécution
        from datetime import datetime, timedelta
        next_run = datetime.utcnow() + timedelta(minutes=simulation.frequency_minutes)
        crud.update_simulation_stats(db, simulation.id, next_run_at=next_run)
        
        return {
            "status": "success", 
            "message": "Simulation créée avec succès",
            "simulation_id": simulation.id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.delete("/simulations/{simulation_id}")
async def delete_simulation(simulation_id: int):
    """Supprimer une simulation"""
    db = SessionLocal()
    try:
        # Vérifier que la simulation existe et n'est pas en cours d'exécution
        simulation = crud.get_simulation(db, simulation_id)
        if not simulation:
            return {"status": "error", "message": "Simulation non trouvée"}
        
        if simulation.is_running:
            return {"status": "error", "message": "Impossible de supprimer une simulation en cours d'exécution"}
        
        # Supprimer la simulation
        success = crud.delete_simulation(db, simulation_id)
        
        if success:
            return {"status": "success", "message": "Simulation supprimée avec succès"}
        else:
            return {"status": "error", "message": "Erreur lors de la suppression"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.post("/simulations/{simulation_id}/trigger")
async def trigger_simulation_manually(simulation_id: int):
    """Déclencher manuellement une simulation pour tests"""
    from .tasks.trading_tasks import run_single_simulation
    
    db = SessionLocal()
    try:
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not simulation:
            return {"status": "error", "message": "Simulation non trouvée"}
            
        if not simulation.is_active:
            return {"status": "error", "message": "La simulation doit être active pour être déclenchée manuellement"}
        
        # Lancer la simulation dans un thread séparé pour éviter tout blocage
        def run_background_simulation_thread():
            import asyncio
            try:
                print(f"🔥 Déclenchement manuel de la simulation: {simulation.name}")
                # Créer un nouvel event loop pour ce thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(run_single_simulation(simulation.id))
                status = "success" if success else "error"
                message = f"Simulation '{simulation.name}' terminée" if success else "Erreur lors de l'exécution"
                print(f"📊 Simulation {simulation.name} terminée: {status}")
                loop.close()
            except Exception as e:
                print(f"❌ Erreur simulation en arrière-plan {simulation_id}: {str(e)}")
        
        # Lancer dans un thread séparé pour éviter complètement le blocage
        import threading
        thread = threading.Thread(target=run_background_simulation_thread, daemon=True)
        thread.start()
        
        return {
            "status": "success", 
            "message": f"Simulation '{simulation.name}' lancée en arrière-plan. Consultez les logs pour suivre le progrès."
        }
            
    except Exception as e:
        print(f"❌ Erreur déclenchement simulation {simulation_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.post("/simulations/{simulation_id}/toggle")
async def toggle_simulation(simulation_id: int):
    """Toggle simulation active status (start/stop)"""
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        # Récupérer la simulation
        simulation = db.query(Simulation).filter(
            Simulation.id == simulation_id
        ).first()

        if not simulation:
            return {"status": "error", "message": "Simulation not found"}

        # Inverser le statut is_active
        new_status = not simulation.is_active
        simulation.is_active = new_status

        # Si on active la simulation, mettre next_run_at à maintenant
        if new_status:
            simulation.next_run_at = datetime.utcnow()
            logger.info(f"✅ Simulation {simulation_id} activée, next_run_at = {simulation.next_run_at}")

        db.commit()
        db.refresh(simulation)

        status_text = "started" if new_status else "stopped"

        return {
            "status": "success",
            "message": f"Simulation {status_text}",
            "simulation": {
                "id": simulation.id,
                "name": simulation.name,
                "is_active": simulation.is_active,
                "next_run_at": simulation.next_run_at.isoformat() if simulation.next_run_at else None
            }
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.post("/simulations/{simulation_id}/run")
async def run_simulation_now(simulation_id: int):
    """Exécute immédiatement une simulation (déclenchement manuel)"""
    from ..tasks.trading_tasks import run_single_simulation
    import asyncio

    try:
        logger.info(f"🔥 Déclenchement manuel de la simulation {simulation_id}")

        # Lancer la simulation de manière asynchrone
        asyncio.create_task(run_single_simulation(simulation_id))

        return {
            "status": "success",
            "message": f"Simulation {simulation_id} lancée"
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement manuel de la simulation: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.put("/simulations/{simulation_id}")
async def update_simulation(simulation_id: int, simulation_data: dict):
    """Modifier une simulation existante"""
    db = SessionLocal()
    try:
        # Utiliser la fonction CRUD existante
        updated_simulation = crud.update_simulation(
            db=db,
            simulation_id=simulation_id,
            name=simulation_data.get('name'),
            description=simulation_data.get('description'),
            strategy=simulation_data.get('strategy'),
            frequency_minutes=simulation_data.get('frequency_minutes'),
            is_active=simulation_data.get('is_active')
        )

        if not updated_simulation:
            return {"status": "error", "message": "Simulation non trouvée"}

        return {
            "status": "success",
            "message": "Simulation mise à jour avec succès",
            "simulation": {
                "id": updated_simulation.id,
                "name": updated_simulation.name,
                "description": updated_simulation.description,
                "strategy": updated_simulation.strategy,
                "frequency_minutes": updated_simulation.frequency_minutes,
                "is_active": updated_simulation.is_active,
                "next_run_at": updated_simulation.next_run_at.isoformat() if updated_simulation.next_run_at else None
            }
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.get("/wallets")
async def get_wallets():
    """Récupérer tous les wallets (pour le dropdown des simulations)"""
    db = SessionLocal()
    try:
        wallets = db.query(Wallet).all()
        wallets_data = [
            {
                "id": wallet.id,
                "name": wallet.name,
                "initial_budget_usd": float(wallet.initial_budget_usd) if wallet.initial_budget_usd else 0,
                "total_value_usd": float(wallet.total_value_usd) if wallet.total_value_usd else 0
            }
            for wallet in wallets
        ]
        return {"status": "success", "wallets": wallets_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# ============== RAG CHAT ENDPOINTS ==============



# ============== TRADES HISTORY ==============

@router.get("/trades/history")
async def get_trades_history(wallet_name: str = "default"):
    """
    Récupérer l'historique des trades pour un wallet
    Alias pour /wallets/{wallet_name}/transactions
    """
    db = SessionLocal()
    try:
        # Récupérer le wallet par nom
        wallet = crud.get_wallet_by_name(db, wallet_name)

        if not wallet:
            return {
                "status": "success",
                "wallet_name": wallet_name,
                "trades": [],
                "count": 0
            }

        # Récupérer toutes les transactions
        transactions = crud.get_wallet_transactions(db, wallet.id)

        # Formater les transactions pour le frontend
        trades_data = []
        for tx in transactions:
            asset = crud.get_asset(db, tx.asset_id)

            trade_info = {
                "id": tx.id,
                "timestamp": tx.timestamp.isoformat(),
                "action": tx.type.value.upper(),  # BUY or SELL
                "ticker": asset.symbol if asset else str(tx.asset_id),
                "asset_name": asset.name if asset else str(tx.asset_id),
                "amount": float(tx.amount),
                "price": float(tx.price_at_time),
                "total_value": float(tx.total_value),
                "fee": float(tx.fees) if tx.fees else 0.0,
                "reasoning": tx.reasoning if tx.reasoning else "No reasoning available"
            }
            trades_data.append(trade_info)

        return {
            "status": "success",
            "wallet_name": wallet_name,
            "trades": trades_data,
            "count": len(trades_data)
        }
    except Exception as e:
        logger.error(f"Error fetching trades history: {e}")
        return {"status": "error", "message": str(e), "trades": [], "count": 0}
    finally:
        db.close()


# ============== TRADING BOT & CONFIG ==============

@router.get("/trading/simulations/{simulation_id}/trades/count")
async def get_simulation_trades_count(simulation_id: int):
    """Récupérer le nombre de trades pour une simulation"""
    db = SessionLocal()
    try:
        # Récupérer la simulation
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not simulation:
            return {"error": "Simulation not found", "count": 0}
        
        # Récupérer le wallet associé
        wallet = db.query(Wallet).filter(Wallet.name == simulation.name).first()
        if not wallet:
            return {"count": 0}
        
        # Compter les transactions de ce wallet
        transactions_count = db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == wallet.id
        ).count()
        
        return {"count": transactions_count}
        
    except Exception as e:
        print(f"❌ Erreur lors du comptage des trades pour la simulation {simulation_id}: {e}")
        return {"error": str(e), "count": 0}
    finally:
        db.close()

# ================== TRADING BOT API ENDPOINTS ==================

# Instance du service bot de trading
trading_bot = get_trading_bot_service()

@router.post("/trading-bot/start")
async def start_trading_bot():
    """Démarre le bot de trading"""
    return await trading_bot.start_bot()

@router.post("/trading-bot/stop")
async def stop_trading_bot():
    """Arrête le bot de trading"""
    return await trading_bot.stop_bot()

@router.get("/trading-bot/status")
async def get_trading_bot_status():
    """Récupère le statut du bot de trading"""
    return {
        "success": True,
        "is_running": trading_bot.is_running,
        "config": trading_bot.get_config()
    }

class ScanRequest(BaseModel):
    use_synthetic: bool = False
    scenario: str = "mixed"  # bullish, bearish, mixed, extreme_fear

@router.post("/trading-bot/scan")
async def manual_scan(request: ScanRequest = None):
    """
    Lance un scan manuel des signaux

    Args:
        use_synthetic: Si True, génère des signaux synthétiques (pour tests Phase 1)
        scenario: Scénario synthétique (bullish, bearish, mixed, extreme_fear)

    Returns:
        Dict avec success, signals, count
    """
    # Parse request (None si appelé sans body)
    use_synthetic = request.use_synthetic if request else False
    scenario = request.scenario if request else "mixed"

    result = await trading_bot.scan_signals(
        use_synthetic=use_synthetic,
        scenario=scenario
    )

    # Broadcast signals to WebSocket clients
    if result.get('success') and result.get('signals'):
        from ..websocket_manager import get_websocket_manager
        ws_manager = get_websocket_manager()

        for signal in result['signals']:
            try:
                await ws_manager.broadcast({
                    "type": "new_signal",
                    "payload": signal
                })
                logger.info(f"📡 Broadcasted signal: {signal.get('symbol', 'UNKNOWN')}")
            except Exception as e:
                logger.error(f"Error broadcasting signal: {e}")

    return result

@router.get("/signals")
async def get_signals(limit: int = 50):
    """Récupère les signaux de trading en FIFO"""
    signals = trading_bot.get_signals(limit)
    return {
        "success": True,
        "signals": signals,
        "count": len(signals)
    }

@router.get("/trading-stats")
async def get_trading_stats():
    """Récupère les statistiques de trading"""
    stats = trading_bot.get_trading_stats()
    return {
        "success": True,
        "stats": stats
    }

@router.get("/bot-config")
async def get_bot_config():
    """Récupère la configuration complète du bot"""
    config = trading_bot.get_config()
    return {
        "success": True,
        "config": config
    }

@router.post("/bot-config/reload")
async def reload_bot_config():
    """Recharge la configuration du bot depuis le fichier JSON"""
    try:
        # Force reload from file
        from ..bot.bot_config_manager import load_bot_globals
        from ..bot.trading_bot_core import init_bot_config

        # Reload globals
        new_config = load_bot_globals()
        logger.info(f"🔄 Reloading config: TP={new_config.get('TP_PCT_MIN')}%, SL={new_config.get('SL_PCT_MIN')}%")

        # Re-initialize bot config
        init_bot_config()

        # Reload in service
        trading_bot.bot_globals = new_config
        trading_bot._load_bot_modules()

        return {
            "success": True,
            "message": "Configuration rechargée avec succès",
            "config": {
                "tp_min": new_config.get('TP_PCT_MIN'),
                "sl_min": new_config.get('SL_PCT_MIN'),
                "volume_min": new_config.get('MIN_24H_USD'),
                "quotes": new_config.get('QUOTE_WHITELIST'),
                "interval": new_config.get('KLINE_INTERVAL'),
                "realtime_tpsl": new_config.get('REALTIME_TPSL')
            }
        }
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return {
            "success": False,
            "message": f"Erreur: {str(e)}"
        }

class BotConfigUpdate(BaseModel):
    updates: Dict[str, Any]

@router.put("/bot-config")
async def update_bot_config(config_update: BotConfigUpdate):
    """Met à jour la configuration du bot"""
    return trading_bot.update_config(config_update.updates)

@router.post("/bot-config/preset/{preset_name}")
async def apply_bot_preset(preset_name: str):
    """Applique un preset de configuration au bot"""
    return trading_bot.apply_preset(preset_name)

@router.post("/bot-config/reset")
async def reset_bot_config():
    """Remet la configuration du bot aux valeurs par défaut"""
    return trading_bot.reset_to_default()
