#!/usr/bin/env python3
"""
Module synchrone pour les scans de trading - Version non-bloquante
Implémente un scan direct du bot de trading sans dépendances async problématiques
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import logging

from backend.config.paths import BOT_LOGS_DIR
# Logger spécifique pour le bot
def setup_bot_logger():
    logger = logging.getLogger("trading_bot_sync")
    if not logger.handlers:  # Eviter les handlers multiples
        logger.setLevel(logging.INFO)

        # Handler pour fichier UNIQUEMENT (pas de console pour éviter I/O closed file)
        bot_log_path = str(BOT_LOGS_DIR / "trading_bot.log")
        os.makedirs(os.path.dirname(bot_log_path), exist_ok=True)

        file_handler = logging.FileHandler(bot_log_path)
        file_handler.setLevel(logging.INFO)

        # Format
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        # Empêcher propagation au logger root (qui pourrait avoir un StreamHandler)
        logger.propagate = False

    return logger

def scan_trading_signals_sync():
    """Scan synchrone avec le VRAI bot de trading (run_scan_events)"""
    logger = setup_bot_logger()

    try:
        logger.info("🔍 [SCAN START] Début du scan RÉEL des signaux de trading")

        # Import du vrai bot
        try:
            import trading_bot_core
        except ImportError as e:
            logger.error(f"❌ [SCAN ERROR] Impossible d'importer trading_bot_core: {e}")
            return {"success": False, "message": f"Import error: {e}"}

        # Initialiser la config du bot
        trading_bot_core.init_bot_config()
        trading_bot_core.setup_logging()

        # IMPORTANT: Update open trades BEFORE scanning for new signals
        # This closes trades that hit TP/SL and updates stats
        logger.info("📊 [UPDATE] Vérification des trades ouverts...")
        try:
            trading_bot_core.update_open_trades()
            logger.info("✅ [UPDATE] Trades mis à jour")
        except Exception as e:
            logger.error(f"❌ [UPDATE ERROR] Erreur lors de la mise à jour des trades: {e}")

        logger.info("⚡ [SCAN] Lancement du scan réel (run_scan_events)...")

        # VRAI SCAN avec run_scan_events()
        events_df = trading_bot_core.run_scan_events()

        # Convertir le DataFrame en liste de dicts pour le résultat
        if events_df is not None and len(events_df) > 0:
            signals = events_df.to_dict('records')
            count = len(signals)

            # Paper trading: ouvrir les trades dans la DB
            try:
                trading_bot_core.paper_trade_open(events_df)
                logger.info(f"📊 [PAPER TRADE] {count} trades ouverts dans la DB")
            except Exception as e:
                logger.error(f"❌ [PAPER TRADE] Erreur lors de l'ouverture des trades: {e}")
        else:
            signals = []
            count = 0

        scan_result = {
            "success": True,
            "signals": signals,
            "count": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scan_type": "real_bot_scan"
        }

        # Log du résultat
        logger.info(f"✅ [SCAN END] Scan terminé - {count} signaux détectés")
        
        # Enregistrer le résultat du scan
        scan_log_path = str(BOT_LOGS_DIR / "scan_results.json")
        try:
            with open(scan_log_path, 'a') as f:
                f.write(json.dumps(scan_result) + '\n')
        except Exception as e:
            logger.warning(f"⚠️ [SCAN] Impossible d'enregistrer le résultat: {e}")

        return scan_result

    except Exception as e:
        logger.error(f"❌ [SCAN ERROR] Erreur lors du scan synchrone: {e}")
        return {"success": False, "message": str(e)}

def get_recent_scans(limit=10):
    """Récupère les derniers résultats de scan"""
    scan_log_path = str(BOT_LOGS_DIR / "scan_results.json")
    
    if not os.path.exists(scan_log_path):
        return []
    
    try:
        with open(scan_log_path, 'r') as f:
            lines = f.readlines()
        
        scans = []
        for line in lines[-limit:]:
            try:
                scans.append(json.loads(line.strip()))
            except:
                continue
        
        return scans
    except Exception as e:
        return []

if __name__ == "__main__":
    # Test direct
    result = scan_trading_signals_sync()
    print(f"Test scan result: {result}")