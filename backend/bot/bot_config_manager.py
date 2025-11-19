import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from backend.config.paths import PAPERTRADES_DB, CONFIG_DIR, BOT_LOGS_DIR, BOT_TRACE_DIR

logger = logging.getLogger("bot_config_manager")

class BotConfigManager:
    """Gestionnaire de configuration pour le bot de trading remplaçant les variables d'environnement"""
    
    def __init__(self, config_path: Optional[str] = None, default_config_path: Optional[str] = None):
        self.config_path = config_path or "./bot_config.json"
        self.default_config_path = default_config_path or "./config_default.json"
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON ou crée depuis le défaut"""
        try:
            # Essaie de charger la config utilisateur
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration chargée depuis {self.config_path}")
            else:
                # Crée la config depuis le template par défaut
                self.create_from_default()
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la config: {e}")
            self.create_from_default()
    
    def create_from_default(self):
        """Crée un fichier de config utilisateur depuis le template par défaut"""
        try:
            if os.path.exists(self.default_config_path):
                with open(self.default_config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.save_config()
                logger.info(f"Configuration créée depuis {self.default_config_path}")
            else:
                logger.error(f"Fichier par défaut introuvable: {self.default_config_path}")
                self.config = self._get_minimal_config()
        except Exception as e:
            logger.error(f"Erreur lors de la création de la config par défaut: {e}")
            self.config = self._get_minimal_config()
    
    def save_config(self):
        """Sauvegarde la configuration actuelle"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration sauvegardée dans {self.config_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Récupère une valeur par chemin point séparé (ex: 'trading.scan_seconds')"""
        keys = path.split('.')
        current = self.config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set(self, path: str, value: Any):
        """Définit une valeur par chemin point séparé"""
        keys = path.split('.')
        current = self.config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def apply_preset(self, preset_name: str) -> bool:
        """Applique un preset de configuration"""
        presets = self.get('presets', {})
        if preset_name not in presets:
            logger.error(f"Preset '{preset_name}' introuvable")
            return False
        
        preset = presets[preset_name]
        logger.info(f"Application du preset '{preset_name}'")
        
        # Applique chaque section du preset
        for section_name, section_data in preset.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    self.set(f'{section_name}.{key}', value)
        
        return True
    
    def reset_to_default(self):
        """Remet la configuration aux valeurs par défaut"""
        logger.info("Reset de la configuration aux valeurs par défaut")
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        self.create_from_default()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Retourne toutes les valeurs de configuration aplaties"""
        def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict) and k != 'presets':  # Ignore presets dans l'aplatissement
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        return flatten_dict(self.config)
    
    def _get_minimal_config(self) -> Dict[str, Any]:
        """Configuration minimale de secours"""
        return {
            "telegram": {"token": "", "default_chat_id": ""},
            "trading": {"scan_seconds": 120, "kline_interval": "5m", "kline_limit": 400},
            "strategy": {"sma_fast": 20, "sma_slow": 200},
            "exits": {"use_atr_exits": True, "tp_pct_min": 1.0, "sl_pct_min": 0.5},
            "paper_trading": {"enabled": True, "db_path": "./papertrades.db"}
        }

# Variables globales pour remplacer le système d'environnement du bot original
_bot_config_manager = None

def get_bot_config_manager() -> BotConfigManager:
    """Récupère l'instance globale du gestionnaire de config"""
    global _bot_config_manager
    if _bot_config_manager is None:
        # Config dans data/config/ (centralisé)
        config_path = CONFIG_DIR / "bot_config.json"
        # Template par défaut reste dans le répertoire du bot
        bot_dir = Path(__file__).parent
        default_path = bot_dir / "config_default.json"
        _bot_config_manager = BotConfigManager(str(config_path), str(default_path))
    return _bot_config_manager

def load_bot_globals():
    """Charge toutes les variables globales du bot depuis la configuration JSON"""
    config = get_bot_config_manager()
    
    # Mapping de la configuration vers les variables globales du bot original
    global_vars = {
        # Binance
        'BINANCE_BASE_URL': config.get('binance.base_url', ''),
        'BINANCE_PROXY': config.get('binance.proxy', ''),

        # Telegram
        'TELEGRAM_TOKEN': config.get('telegram.token', ''),
        'DEFAULT_CHAT_ID': config.get('telegram.default_chat_id', ''),

        # Trading
        'USER_SYMBOLS': config.get('trading.user_symbols', []),
        'SCAN_SECONDS': config.get('trading.scan_seconds', 120),
        'TOP_K': config.get('trading.top_k', 5),
        'KLINE_INTERVAL': config.get('trading.kline_interval', '5m'),
        'KLINE_LIMIT': config.get('trading.kline_limit', 400),
        'USDC_ONLY': config.get('trading.usdc_only', True),
        'QUOTE_WHITELIST': config.get('trading.quote_whitelist', []),
        
        # Strategy
        'SMA_FAST': config.get('strategy.sma_fast', 20),
        'SMA_SLOW': config.get('strategy.sma_slow', 200),
        'LONG_RSI_MIN': config.get('strategy.long_rsi_min', 45),
        'LONG_RSI_MAX': config.get('strategy.long_rsi_max', 70),
        'SHORTS_ENABLED': config.get('strategy.shorts_enabled', False),
        'SHORT_RSI_MIN': config.get('strategy.short_rsi_min', 30),
        'SHORT_RSI_MAX': config.get('strategy.short_rsi_max', 55),
        'MIN_ATR_PCT': config.get('strategy.min_atr_pct', 0.25),
        'MIN_24H_USD': config.get('strategy.min_24h_usd', 50000.0),  # Reduced from 200k to 50k
        'MIN_DELTA_SMA_BPS': config.get('strategy.min_delta_sma_bps', 10.0),
        'MIN_SMA20_SLOPE_BPS': config.get('strategy.min_sma20_slope_bps', 2.0),
        'PREFILTER_TOP_N': config.get('strategy.prefilter_top_n', 500),  # Max symbols to scan
        'PRICECHANGE_ABS_MIN': config.get('strategy.pricechange_abs_min', 0.0),  # Min price change %

        # Exits
        'USE_ATR_EXITS': config.get('exits.use_atr_exits', True),
        'TP_PCT_MIN': config.get('exits.tp_pct_min', 1.0),
        'SL_PCT_MIN': config.get('exits.sl_pct_min', 0.5),
        'ATR_TP_MULT': config.get('exits.atr_tp_mult', 1.5),
        'ATR_SL_MULT': config.get('exits.atr_sl_mult', 1.0),
        'OCO_BUFFER_PCT': config.get('exits.oco_buffer_pct', 0.10),
        
        # Alerts
        'ALERT_MODE': config.get('alerts.alert_mode', 'EVENTS'),
        'COOLDOWN_MIN': config.get('alerts.cooldown_min', 30),
        
        # Logging
        'LOG_LEVEL': config.get('logging.log_level', 'INFO'),
        'LOG_TO_FILE': config.get('logging.log_to_file', True),
        'LOG_DIR': str(BOT_LOGS_DIR),  # Toujours utiliser le chemin centralisé
        'LOG_ROTATE_BYTES': config.get('logging.log_rotate_bytes', 5242880),
        'LOG_BACKUP_COUNT': config.get('logging.log_backup_count', 5),
        'DEBUG_TOP_N': config.get('logging.debug_top_n', 10),
        'TRACE_DIR': str(BOT_TRACE_DIR),  # Trace dans data/logs/bot/trace
        'TRACE_SYMBOLS': config.get('logging.trace_symbols', []),
        'DUMP_ON_REJECT': config.get('logging.dump_on_reject', False),
        
        # Paper Trading
        'PAPER_TRADING': config.get('paper_trading.enabled', True),
        'DB_PATH': str(PAPERTRADES_DB),
        'REALTIME_TPSL': config.get('paper_trading.realtime_tpsl', False),
        'REALTIME_TPSL_CHOOSE': config.get('paper_trading.realtime_tpsl_choose', False),
        'RT_INTERVAL': config.get('paper_trading.rt_interval', '1m'),
        'RT_LIMIT': config.get('paper_trading.rt_limit', 120),
        'IN_CANDLE_PRIORITY': config.get('paper_trading.in_candle_priority', 'SL_FIRST'),
        'MAX_HOLD_HOURS': config.get('paper_trading.max_hold_hours', 12),
        
        # Advanced
        'BE_ENABLE': config.get('advanced.be_enable', False),
        'BE_TRIGGER_FRAC': config.get('advanced.be_trigger_frac', 0.6),
        'BE_OFFSET_PCT': config.get('advanced.be_offset_pct', 0.05),
        'RECENT_CROSS_BARS': config.get('advanced.recent_cross_bars', 1),
        'REQUIRE_1H_TREND': config.get('advanced.require_1h_trend', False),
        'MICRO_CONFIRM_1M': config.get('advanced.micro_confirm_1m', False),
        'MC1M_BARS': config.get('advanced.mc1m_bars', 3),
        'PREFILTER_TOP_N': config.get('advanced.prefilter_top_n', 300),
        'PRICECHANGE_ABS_MIN': config.get('advanced.pricechange_abs_min', 0.0),
    }
    
    return global_vars