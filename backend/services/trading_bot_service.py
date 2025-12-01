import asyncio
import logging
import sqlite3
import json
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import concurrent.futures

# Import du bot core adapté pour le backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))

from bot_config_manager import get_bot_config_manager, load_bot_globals
from trading_bot_core import (
    init_bot_config, run_scan_events, update_open_trades,
    compute_stats, paper_trade_open, init_db, setup_logging
)

logger = logging.getLogger("trading_bot_service")

async def run_in_thread(func, *args, **kwargs):
    """Exécute une fonction dans un thread séparé de manière non-bloquante"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))

def fetch_fear_greed_index() -> Dict[str, Any]:
    """
    Récupère le Fear & Greed Index depuis alternative.me
    Returns: Dict avec 'score' (0-100) et 'label' (Extreme Fear, Fear, Neutral, Greed, Extreme Greed)
    """
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and len(data['data']) > 0:
            fng_data = data['data'][0]
            score = int(fng_data.get('value', 50))
            label = fng_data.get('value_classification', 'Neutral')

            return {
                'score': score,
                'label': label,
                'timestamp': fng_data.get('timestamp', '')
            }
    except Exception as e:
        logger.warning(f"Erreur récupération Fear & Greed Index: {e}")

    # Fallback en cas d'erreur
    return {
        'score': 50,
        'label': 'Neutral',
        'timestamp': ''
    }

class TradingBotService:
    """Service intégré du bot de trading dans le backend FedEdge"""
    
    def __init__(self):
        self.config_manager = get_bot_config_manager()
        self.is_running = False
        self.signals_queue = []  # FIFO pour les signaux
        self.max_signals = 100  # Limite des signaux en mémoire
        self.bot_globals = {}
        self.state_file = Path("data/bot_state.json")
        self._load_bot_modules()

    def _save_state(self):
        """Sauvegarde l'état du bot dans un fichier"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({
                    "is_running": self.is_running,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }, f)
        except Exception as e:
            logger.warning(f"Erreur sauvegarde état bot: {e}")

    def restore_state(self):
        """Restaure l'état du bot depuis le fichier"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                was_running = state.get("is_running", False)
                logger.info(f"📂 État restauré: was_running={was_running}")
                return was_running
        except Exception as e:
            logger.warning(f"Erreur restauration état bot: {e}")
        return False
    
    def _load_bot_modules(self):
        """Charge les modules du bot core adapté pour le backend"""
        try:
            # Charge les variables globales depuis JSON
            self.bot_globals = load_bot_globals()
            
            # Initialise la configuration globale du bot
            init_bot_config()
            
            # Setup logging avec la config JSON
            setup_logging()
            init_db()
            
            # Store les fonctions importantes
            self.run_scan_events = run_scan_events
            self.update_open_trades = update_open_trades
            self.compute_stats = compute_stats
            self.paper_trade_open = paper_trade_open
            
            logger.info("Modules bot core chargés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modules bot: {e}")
            raise
    
    async def start_bot(self):
        """Démarre le service bot"""
        if self.is_running:
            return {"success": False, "message": "Bot déjà en cours"}

        try:
            self.is_running = True
            self._save_state()  # Sauvegarde l'état
            logger.info("🚀 Bot de trading démarré")
            return {"success": True, "message": "Bot démarré"}
        except Exception as e:
            self.is_running = False
            self._save_state()
            logger.error(f"Erreur démarrage bot: {e}")
            return {"success": False, "message": f"Erreur: {e}"}

    async def stop_bot(self):
        """Arrête le service bot"""
        if not self.is_running:
            return {"success": False, "message": "Bot déjà arrêté"}

        self.is_running = False
        self._save_state()  # Sauvegarde l'état
        logger.info("⏸️ Bot de trading arrêté")
        return {"success": True, "message": "Bot arrêté"}
    
    async def scan_signals(self, use_synthetic: bool = False, scenario: str = "mixed") -> Dict[str, Any]:
        """
        Lance un scan manuel des signaux (non-bloquant)

        Args:
            use_synthetic: Si True, génère des signaux synthétiques pour tests
            scenario: Scénario synthétique (bullish, bearish, mixed, extreme_fear)

        Returns:
            Dict avec success, signals, count
        """
        # MODE SYNTHETIC pour tests Phase 1
        if use_synthetic:
            try:
                from backend.services.synthetic_signals import generate_signal_batch

                logger.info(f"Génération de signaux synthétiques (scenario={scenario})")
                signals = generate_signal_batch(count=3, scenario=scenario)

                # Ajouter à la queue
                self.signals_queue.extend(signals)
                if len(self.signals_queue) > self.max_signals:
                    self.signals_queue = self.signals_queue[-self.max_signals:]

                return {
                    "success": True,
                    "signals": signals,
                    "count": len(signals),
                    "synthetic": True,
                    "scenario": scenario
                }
            except Exception as e:
                logger.error(f"Erreur génération signaux synthétiques: {e}")
                return {"success": False, "message": f"Erreur synthetic: {e}"}

        # MODE NORMAL : Vrais signaux du bot
        try:
            logger.info("Lancement scan manuel des signaux (non-bloquant)")

            # Update des trades ouverts dans un thread
            await run_in_thread(self.update_open_trades)

            # Scan des nouveaux signaux dans un thread
            df_events = await run_in_thread(self.run_scan_events)
            
            if df_events is None or df_events.empty:
                return {
                    "success": True,
                    "signals": [],
                    "message": "Aucun signal trouvé"
                }
            
            # Note: Le cooldown sera géré côté frontend/API si nécessaire
            
            # Convertir en format JSON pour l'API
            signals = []
            for _, row in df_events.iterrows():
                signal = {
                    "id": f"{row['scan_id']}_{row['symbol']}_{row['side']}",
                    "scan_id": row['scan_id'],
                    "symbol": row['symbol'],
                    "side": row['side'],
                    "last_price": float(row['last_price']),
                    "entry": float(row['entry']),
                    "tp": float(row['tp']),
                    "sl": float(row['sl']),
                    "rsi": float(row['rsi']),
                    "atr_pct": float(row['atr_pct']),
                    "delta_sma_bps": float(row['dSMA_bps']),
                    "slope_bps": float(row['slope_bps']),
                    "event": row['event'],
                    "score": float(row['score']),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "DETECTED"
                }
                signals.append(signal)
            
            # Ajoute à la queue FIFO
            self.signals_queue.extend(signals)
            if len(self.signals_queue) > self.max_signals:
                self.signals_queue = self.signals_queue[-self.max_signals:]
            
            # Paper trading si activé
            if self.bot_globals.get('PAPER_TRADING', True):
                self.paper_trade_open(df_events)
                logger.info(f"Paper trades ouverts pour {len(signals)} signaux")
            
            return {
                "success": True,
                "signals": signals,
                "count": len(signals)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du scan: {e}")
            return {"success": False, "message": f"Erreur scan: {e}"}
    
    def get_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Récupère les signaux en FIFO depuis scan_results.json"""
        try:
            # Lire depuis scan_results.json (écrits par les scans automatiques)
            from backend.config.paths import BOT_LOGS_DIR
            scan_results_path = BOT_LOGS_DIR / "scan_results.json"

            if not scan_results_path.exists():
                return []

            # Lire les derniers scans
            with open(scan_results_path, 'r') as f:
                lines = f.readlines()

            all_signals = []
            for line in lines[-50:]:  # Derniers 50 scans
                try:
                    scan_result = json.loads(line.strip())
                    if scan_result.get('success') and scan_result.get('signals'):
                        # Convertir au format attendu par le frontend
                        for sig in scan_result['signals']:
                            # Mapper les champs du bot vers le format frontend
                            signal = {
                                "id": f"{sig['scan_id']}_{sig['symbol']}",
                                "ticker": sig['symbol'],
                                "action": "BUY" if sig['side'] == "LONG" else "SELL",
                                "entry_price": sig['entry'],
                                "target_price": sig['tp'],
                                "stop_loss": sig['sl'],
                                "confidence": min(100, max(0, 50 + sig['rsi']/2)),  # RSI-based confidence
                                "timestamp": scan_result.get('timestamp', datetime.now(timezone.utc).isoformat()),
                                "reasoning": f"GOLDEN CROSS detected: SMA20 crossed above SMA200. RSI: {sig['rsi']:.1f}, ATR: {sig['atr_pct']:.2f}%",
                                # Garder aussi les données brutes du bot
                                "symbol": sig['symbol'],
                                "side": sig['side'],
                                "entry": sig['entry'],
                                "tp": sig['tp'],
                                "sl": sig['sl'],
                                "rsi": sig['rsi'],
                                "atr_pct": sig['atr_pct'],
                                "event": sig['event']
                            }
                            all_signals.append(signal)
                except Exception as e:
                    continue

            # Dédupliquer par ticker (garder le plus récent)
            seen = {}
            for sig in reversed(all_signals):  # Parcourir du plus récent au plus ancien
                if sig['ticker'] not in seen:
                    seen[sig['ticker']] = sig

            # Retourner les N derniers signaux uniques
            unique_signals = list(seen.values())
            return unique_signals[-limit:]

        except Exception as e:
            logger.error(f"Erreur lors de la lecture des signaux: {e}")
            return []
    
    def get_trading_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de trading + données de marché globales"""
        try:
            stats = self.compute_stats()

            # Enrichit avec des stats supplémentaires
            db_path = self.bot_globals.get('DB_PATH', './papertrades.db')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)

                # Trades ouverts
                open_trades = pd.read_sql_query(
                    "SELECT COUNT(*) as count FROM trades WHERE status='OPEN'",
                    conn
                )
                stats['open_trades'] = int(open_trades['count'].iloc[0])

                # Derniers trades
                recent_trades = pd.read_sql_query("""
                    SELECT symbol, side, status, opened_at, closed_at, entry, tp, sl, close_reason
                    FROM trades
                    ORDER BY id DESC
                    LIMIT 10
                """, conn)

                stats['recent_trades'] = recent_trades.to_dict('records') if not recent_trades.empty else []
                conn.close()
            else:
                stats['open_trades'] = 0
                stats['recent_trades'] = []

            # Info sur la configuration actuelle
            # Recharger bot_globals pour avoir la dernière config
            from bot_config_manager import load_bot_globals
            current_globals = load_bot_globals()

            stats['config'] = {
                'scan_seconds': current_globals.get('SCAN_SECONDS', 120),
                'kline_interval': current_globals.get('KLINE_INTERVAL', '5m'),
                'paper_trading': current_globals.get('PAPER_TRADING', True),
                'realtime_tpsl': current_globals.get('REALTIME_TPSL', False),
                'quote_whitelist': current_globals.get('QUOTE_WHITELIST', []),
                'min_24h_usd': current_globals.get('MIN_24H_USD', 200000)
            }

            # ===== AJOUT DES DONNÉES DE MARCHÉ GLOBALES =====
            try:
                # Import du collector de données financières (import absolu)
                from backend.collectors.finance_collector import get_complete_finance_analysis

                # Récupérer l'analyse financière complète (avec cache)
                finance_data = get_complete_finance_analysis(use_cache=True)

                if finance_data and 'market_statistics' in finance_data:
                    market_stats = finance_data['market_statistics']

                    # Récupérer le Fear & Greed Index
                    fear_greed = fetch_fear_greed_index()

                    # Ajouter les données au format attendu par le frontend
                    stats['total_market_cap'] = market_stats.get('total_market_cap', 0)
                    stats['total_volume_24h'] = market_stats.get('total_volume_24h', 0)
                    stats['btc_dominance'] = market_stats.get('btc_dominance', 0)
                    stats['market_sentiment'] = {
                        'score': fear_greed.get('score', 50),
                        'label': fear_greed.get('label', 'Neutral')
                    }

                    logger.info(f"📊 Market data added: cap=${stats['total_market_cap']:,.0f}, sentiment={fear_greed.get('label')}")
                else:
                    logger.warning("Finance data not available, using defaults")
                    stats['total_market_cap'] = 0
                    stats['total_volume_24h'] = 0
                    stats['btc_dominance'] = 0
                    stats['market_sentiment'] = {'score': 50, 'label': 'Neutral'}

            except Exception as market_error:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Erreur récupération données marché: {market_error}")
                logger.error(f"Traceback complet: {error_details}")
                print(f"❌ ERREUR MARCHÉ: {market_error}")
                print(f"📋 TRACEBACK: {error_details}")
                # Fallback avec valeurs par défaut
                stats['total_market_cap'] = 0
                stats['total_volume_24h'] = 0
                stats['btc_dominance'] = 0
                stats['market_sentiment'] = {'score': 50, 'label': 'Neutral'}

            return stats

        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return {
                'total': 0, 'wins': 0, 'losses': 0, 'expired': 0, 'winrate_pct': 0.0,
                'open_trades': 0, 'recent_trades': [], 'config': {},
                'total_market_cap': 0, 'total_volume_24h': 0, 'btc_dominance': 0,
                'market_sentiment': {'score': 50, 'label': 'Neutral'}
            }
    
    def get_config(self) -> Dict[str, Any]:
        """Récupère la configuration complète"""
        return self.config_manager.config
    
    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour la configuration"""
        try:
            for key, value in updates.items():
                self.config_manager.set(key, value)
            
            self.config_manager.save_config()
            
            # Recharge les variables globales
            self.bot_globals = load_bot_globals()
            init_bot_config()
            
            return {"success": True, "message": "Configuration mise à jour"}
        except Exception as e:
            logger.error(f"Erreur mise à jour config: {e}")
            return {"success": False, "message": f"Erreur: {e}"}
    
    def apply_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applique un preset de configuration"""
        try:
            success = self.config_manager.apply_preset(preset_name)
            if success:
                self.config_manager.save_config()
                self.bot_globals = load_bot_globals()
                init_bot_config()
                return {"success": True, "message": f"Preset '{preset_name}' appliqué"}
            else:
                return {"success": False, "message": f"Preset '{preset_name}' introuvable"}
        except Exception as e:
            logger.error(f"Erreur application preset: {e}")
            return {"success": False, "message": f"Erreur: {e}"}
    
    def reset_to_default(self) -> Dict[str, Any]:
        """Remet la configuration par défaut"""
        try:
            self.config_manager.reset_to_default()
            self.bot_globals = load_bot_globals()
            init_bot_config()
            return {"success": True, "message": "Configuration remise aux valeurs par défaut"}
        except Exception as e:
            logger.error(f"Erreur reset config: {e}")
            return {"success": False, "message": f"Erreur: {e}"}

# Instance globale du service
_trading_bot_service = None

def get_trading_bot_service() -> TradingBotService:
    """Récupère l'instance globale du service bot"""
    global _trading_bot_service
    if _trading_bot_service is None:
        _trading_bot_service = TradingBotService()
    return _trading_bot_service