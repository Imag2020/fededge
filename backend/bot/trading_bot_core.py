"""
Trading Bot Core - Version adaptée pour l'intégration backend FedEdge
Extrait du bot original ime_bot.py sans les dépendances Telegram
"""

import os, json, hashlib, logging, sqlite3
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict

import numpy as np
import pandas as pd
import requests

from bot_config_manager import get_bot_config_manager, load_bot_globals

from backend.config.paths import BOT_LOGS_DIR, PAPERTRADES_DB

logger = logging.getLogger("trading_bot_core")

# Variables globales chargées depuis la configuration JSON
_bot_config = {}

def init_bot_config():
    """Initialise la configuration globale du bot"""
    global _bot_config
    _bot_config = load_bot_globals()

def get_config(key: str, default=None):
    """Récupère une valeur de configuration"""
    return _bot_config.get(key, default)

# -------------------- LOGGING --------------------
_logging_setup_done = False

def setup_logging():
    """Configure le logging pour le bot de trading dans data/logs/bot/"""
    global _logging_setup_done

    # Éviter la duplication de handlers
    if _logging_setup_done:
        return

    log_level = get_config('LOG_LEVEL', 'INFO')
    # Logs du bot vont dans data/logs/bot/ (centralisé via paths.py)
    bot_log_dir = str(BOT_LOGS_DIR)
    log_to_file = get_config('LOG_TO_FILE', True)
    log_rotate_bytes = get_config('LOG_ROTATE_BYTES', 5*1024*1024)
    log_backup_count = get_config('LOG_BACKUP_COUNT', 5)

    # Le dossier est déjà créé par paths.ensure_directories()
    os.makedirs(bot_log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configuration des loggers dédiés au bot (pas le root logger)
    bot_loggers = [
        "trading_bot_core",
        "trading_bot_sync",
        "trading_bot_service",
        "bot_config_manager",
        "rejects",
        "binance"
    ]

    for logger_name in bot_loggers:
        bot_logger = logging.getLogger(logger_name)
        bot_logger.setLevel(getattr(logging, log_level, logging.INFO))
        bot_logger.propagate = False  # Important: ne pas propager au root logger

        # Nettoyer les handlers existants
        bot_logger.handlers.clear()

        # Console (optionnel, décommenter si besoin)
        # ch = logging.StreamHandler()
        # ch.setLevel(getattr(logging, log_level, logging.INFO))
        # ch.setFormatter(fmt)
        # bot_logger.addHandler(ch)

        # Fichiers dans data/logs/bot/
        if log_to_file:
            fh = RotatingFileHandler(
                os.path.join(bot_log_dir, "trading_bot.log"),
                maxBytes=log_rotate_bytes,
                backupCount=log_backup_count
            )
            fh.setLevel(logging.INFO)
            fh.setFormatter(fmt)
            bot_logger.addHandler(fh)

            # Debug séparé
            if log_level == 'DEBUG':
                fh_dbg = RotatingFileHandler(
                    os.path.join(bot_log_dir, "trading_bot_debug.log"),
                    maxBytes=log_rotate_bytes,
                    backupCount=log_backup_count
                )
                fh_dbg.setLevel(logging.DEBUG)
                fh_dbg.setFormatter(fmt)
                bot_logger.addHandler(fh_dbg)

    _logging_setup_done = True
    logger.info(f"✅ Logging du bot configuré dans {bot_log_dir}")

# -------------------- DATA (Binance REST) --------------------
BINANCE_INTERVAL_MAP = {
    "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
    "1h":"1h","2h":"2h","4h":"4h","6h":"6h","12h":"12h",
    "1d":"1d","3d":"3d","1w":"1w"
}

import time

def get_proxy_config():
    """Récupère la configuration proxy depuis la config ou l'environnement"""
    proxy_url = get_config('BINANCE_PROXY', os.getenv('BINANCE_PROXY', ''))
    if proxy_url:
        return {'http': proxy_url, 'https': proxy_url}
    return None

def get_binance_base_url():
    """Retourne l'URL de base Binance selon la configuration ou région"""
    # Ordre de priorité:
    # 1. Variable d'environnement BINANCE_BASE_URL
    # 2. Config JSON binance.base_url
    # 3. Défaut: binance.com

    env_url = os.getenv('BINANCE_BASE_URL', '')
    if env_url:
        return env_url

    # Essayer depuis le JSON (nested key)
    bot_config = get_config('binance', {})
    if isinstance(bot_config, dict) and 'base_url' in bot_config:
        return bot_config['base_url']

    # Fallback: old key pour compatibilité
    base_url = get_config('BINANCE_BASE_URL', '')
    if base_url:
        return base_url

    # Par défaut : binance.com
    return "https://api.binance.com"

# Import du resolver intelligent avec fallback
try:
    from binance_resolver import get_resolver
    USE_SMART_RESOLVER = os.getenv('USE_BINANCE_RESOLVER', 'true').lower() == 'true'
except ImportError:
    USE_SMART_RESOLVER = False
    logger.warning("binance_resolver non disponible, mode classique")

def fetch_all_24h(scan_id: str) -> pd.DataFrame:
    t0 = time.time()
    data = None

    # Mode resolver intelligent avec cascade automatique
    # TEMPORARY: Force classic mode for debugging
    use_resolver = USE_SMART_RESOLVER and False  # <-- Set to False to disable resolver
    if use_resolver:
        try:
            resolver = get_resolver()
            data = resolver.get_ticker_24h()
        except Exception as e:
            logger.error("[%s] ❌ Resolver intelligent échoué: %s", scan_id, e)
            logger.info("[%s] 🔄 Fallback sur mode classique...", scan_id)
            data = None

    # Mode classique (ou fallback si resolver échoué)
    if data is None:
        base_url = get_binance_base_url()
        url = f"{base_url}/api/v3/ticker/24hr"
        proxies = get_proxy_config()

        try:
            r = requests.get(url, timeout=20, proxies=proxies)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 451:
                logger.error("[%s] ❌ Binance API bloquée (HTTP 451) - région/IP restreinte", scan_id)
                if 'binance.us' not in url:
                    logger.error("[%s] 💡 Solution USA: BINANCE_BASE_URL=https://api.binance.us", scan_id)
                logger.error("[%s] 💡 Solution proxy: BINANCE_PROXY=http://proxy:8080", scan_id)
                logger.error("[%s] 💡 Solution resolver: USE_BINANCE_RESOLVER=true", scan_id)
            raise

    df = pd.DataFrame(data)
    keep = ["symbol","lastPrice","quoteVolume","priceChangePercent","highPrice","lowPrice"]
    for k in keep:
        if k not in df.columns: df[k] = np.nan
    df = df[keep].copy()
    for c in ["lastPrice","quoteVolume","priceChangePercent","highPrice","lowPrice"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Debug logs
    logger.info("[%s] ✅ 24h data fetched: %d symbols in %.2fs", scan_id, len(df), time.time()-t0)
    if len(df) > 0:
        logger.info("[%s] Sample symbols: %s", scan_id, df['symbol'].head(10).tolist())

    return df

def fetch_klines(scan_id: str, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    t0 = time.time()
    try:
        raw = None

        # Mode resolver intelligent
        if USE_SMART_RESOLVER:
            try:
                resolver = get_resolver()
                raw = resolver.get_klines(symbol, BINANCE_INTERVAL_MAP.get(interval, "5m"), limit)
            except Exception as e:
                logger.debug("[%s] %s %s resolver échoué: %s, fallback classique", scan_id, symbol, interval, e)
                raw = None

        # Mode classique (ou fallback)
        if raw is None:
            base_url = get_binance_base_url()
            url = f"{base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": BINANCE_INTERVAL_MAP.get(interval, "5m"), "limit": limit}
            proxies = get_proxy_config()
            r = requests.get(url, params=params, timeout=20, proxies=proxies)
            r.raise_for_status()
            raw = r.json()
        if not raw:
            logging.getLogger("binance").debug("[%s] %s %s -> 0 rows (%.2fs)", scan_id, symbol, interval, time.time()-t0)
            return None
        cols = ["open_time","open","high","low","close","volume","close_time","qav","num_trades","taker_base","taker_quote","ignore"]
        df = pd.DataFrame(raw, columns=cols)
        for c in ["open","high","low","close","volume","qav","taker_base","taker_quote"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["open_time"]  = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        logging.getLogger("binance").debug("[%s] %s %s -> %d rows in %.2fs", scan_id, symbol, interval, len(df), time.time()-t0)
        return df
    except Exception as e:
        logging.getLogger("binance").warning("[%s] %s %s fetch error: %s", scan_id, symbol, interval, e)
        return None


def fetch_klines_range(scan_id: str, symbol: str, interval: str, start_ms: Optional[int]=None, end_ms: Optional[int]=None, limit: Optional[int]=None) -> Optional[pd.DataFrame]:
    try:
        base_url = get_binance_base_url()
        url=f"{base_url}/api/v3/klines"
        params={"symbol":symbol, "interval":BINANCE_INTERVAL_MAP.get(interval, interval)}
        if start_ms is not None: params["startTime"] = int(start_ms)
        if end_ms is not None: params["endTime"] = int(end_ms)
        if limit is not None: params["limit"] = int(limit)
        proxies = get_proxy_config()
        r=requests.get(url, params=params, timeout=20, proxies=proxies)
        r.raise_for_status()
        raw=r.json()
        if not raw: return None
        cols=["open_time","open","high","low","close","volume","close_time","qav","num_trades","taker_base","taker_quote","ignore"]
        df=pd.DataFrame(raw, columns=cols)
        for c in ["open","high","low","close","volume","qav","taker_base","taker_quote"]:
            df[c]=pd.to_numeric(df[c], errors="coerce")
        df["open_time"]=pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["close_time"]=pd.to_datetime(df["close_time"], unit="ms", utc=True)
        return df
    except Exception:
        return None

# -------------------- INDICATORS --------------------
def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def atr(df: pd.DataFrame, period: int=14) -> pd.Series:
    h,l,c=df["high"],df["low"],df["close"]; pc=c.shift(1)
    tr=pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

def rsi(series: pd.Series, period: int=14) -> pd.Series:
    delta=series.diff(); up=delta.clip(lower=0); down=-1*delta.clip(upper=0)
    ema_up=up.ewm(com=period-1, adjust=False).mean()
    ema_down=down.ewm(com=period-1, adjust=False).mean()
    rs=ema_up/(ema_down+1e-12)
    return 100-(100/(1+rs))

# -------------------- HELPERS --------------------
def fmt(x):
    try:
        if isinstance(x,(int,float,np.floating,np.integer)): return f"{float(x):.6g}"
    except: pass
    return str(x)

def now_utc(): return datetime.now(timezone.utc)
def now_iso(): return now_utc().isoformat()
def empty(df): return (df is None) or (not isinstance(df,pd.DataFrame)) or df.empty

def new_scan_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(os.urandom(8)).hexdigest()[:6]

# -------------------- UNIVERSE --------------------
def pick_universe(scan_id: str, t24: pd.DataFrame) -> List[str]:
    user_symbols = get_config('USER_SYMBOLS', [])
    if user_symbols:
        logger.info("[%s] Universe forced by SYMBOLS: %d", scan_id, len(user_symbols))
        logger.info("[%s] Sample: %s", scan_id, ", ".join(user_symbols[:10]))
        return user_symbols

    # Debug: log combien de symboles on a reçu
    logger.info("[%s] Received t24 DataFrame: %d rows", scan_id, len(t24))
    if len(t24) > 0:
        logger.info("[%s] t24 columns: %s", scan_id, list(t24.columns))
        logger.info("[%s] t24 sample symbols: %s", scan_id, t24['symbol'].head(10).tolist() if 'symbol' in t24.columns else 'NO SYMBOL COLUMN')

    df = t24.copy()
    quote_whitelist = get_config('QUOTE_WHITELIST', [])
    usdc_only = get_config('USDC_ONLY', True)
    min_24h_usd = get_config('MIN_24H_USD', 200000.0)
    prefilter_top_n = get_config('PREFILTER_TOP_N', 300)
    pricechange_abs_min = get_config('PRICECHANGE_ABS_MIN', 0.0)

    if quote_whitelist:
        mask = False
        for q in quote_whitelist:
            mask = mask | df["symbol"].str.endswith(q)
        df = df[mask]
    elif usdc_only:
        df = df[df["symbol"].str.endswith("USDC")]

    before = len(df)
    df = df[df["quoteVolume"] >= min_24h_usd]
    if pricechange_abs_min > 0:
        df = df[df["priceChangePercent"].abs() >= pricechange_abs_min]
    df = df.sort_values("quoteVolume", ascending=False).head(prefilter_top_n)

    syms = sorted(df["symbol"].tolist())
    logger.info("[%s] Universe: %d -> %d symbols (topN=%d, min24h=%.0f, whitelist=%s, usdc_only=%s)",
                scan_id, before, len(syms), prefilter_top_n, min_24h_usd, quote_whitelist, usdc_only)
    if syms:
        logger.info("[%s] Universe sample: %s ...", scan_id, ", ".join(syms[:20]))
    return syms or (["ETHUSDC","BTCUSDC","SOLUSDC"])


# -------------------- TP/SL helpers --------------------
def tp_sl_from_entry(price: float, side: str, atr_val: float) -> Tuple[float,float,float,float]:
    use_atr_exits = get_config('USE_ATR_EXITS', True)
    tp_pct_min = get_config('TP_PCT_MIN', 1.0)
    sl_pct_min = get_config('SL_PCT_MIN', 0.5)
    atr_tp_mult = get_config('ATR_TP_MULT', 1.5)
    atr_sl_mult = get_config('ATR_SL_MULT', 1.0)
    oco_buffer_pct = get_config('OCO_BUFFER_PCT', 0.10)
    
    if use_atr_exits:
        sl_abs=max(price*sl_pct_min/100.0, atr_sl_mult*atr_val)
        tp_abs=max(price*tp_pct_min/100.0, atr_tp_mult*atr_val)
    else:
        sl_abs=price*sl_pct_min/100.0
        tp_abs=price*tp_pct_min/100.0
    if side=="LONG":
        sl=price-sl_abs; tp=price+tp_abs
        sl_trigger=sl; sl_limit=sl_trigger*(1.0 - oco_buffer_pct/100.0)
    else:
        tp=price-tp_abs; sl=price+sl_abs
        sl_trigger=sl; sl_limit=sl_trigger*(1.0 + oco_buffer_pct/100.0)
    return tp, sl, sl_trigger, sl_limit

# -------------------- SIGNALS --------------------
def detect_recent_cross(sma_f: pd.Series, sma_s: pd.Series, bars: int) -> Optional[str]:
    if len(sma_f) < bars+1 or len(sma_s) < bars+1: return None
    for i in range(bars, 0, -1):
        prev = sma_f.iloc[-i-1] > sma_s.iloc[-i-1]
        curr = sma_f.iloc[-i]   > sma_s.iloc[-i]
        if (not prev) and curr: return "GOLDEN"
        if prev and (not curr): return "DEATH"
    return None

def trend_guard_1h(scan_id: str, symbol: str) -> bool:
    df = fetch_klines(scan_id, symbol, "1h", 240)
    if empty(df) or len(df) < 220: return False
    close = df["close"].astype(float)
    s50, s200 = sma(close, 50), sma(close, 200)
    if pd.isna(s50.iloc[-1]) or pd.isna(s200.iloc[-1]): return False
    return bool(s50.iloc[-1] > s200.iloc[-1])

def micro_confirm_1m_func(scan_id: str, symbol: str, bars: int) -> bool:
    df = fetch_klines_range(scan_id, symbol, "1m", limit=max(30, bars+5))
    if empty(df): return False
    c = df["close"].astype(float)
    ema9 = ema(c, 9)
    tail = c.tail(bars).reset_index(drop=True)
    tail_ema = ema9.tail(bars).reset_index(drop=True)
    return bool((tail > tail_ema).all())

def reject(scan_id: str, symbol: str, reason: str, details: Dict, dfk: Optional[pd.DataFrame]):
    payload = {"scan_id": scan_id, "symbol": symbol, "reason": reason, "details": details}
    logging.getLogger("rejects").debug(json.dumps(payload, ensure_ascii=False))
    trace_syms = set(get_config('TRACE_SYMBOLS', []) or [])
    if symbol in trace_syms:
        logger.info("[%s] TRACE REJECT %s: %s | %s", scan_id, symbol, reason, details)

def run_scan_events() -> pd.DataFrame:
    scan_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(os.urandom(8)).hexdigest()[:6]
    
    # Charger config
    sma_fast = get_config('SMA_FAST', 20)
    sma_slow = get_config('SMA_SLOW', 200)
    alert_mode = get_config('ALERT_MODE', 'EVENTS')
    kline_interval = get_config('KLINE_INTERVAL', '5m')
    kline_limit = get_config('KLINE_LIMIT', 400)
    
    logger.info("== scan_id=%s | SMA%u/%u + RSI | MODE=%s ==", scan_id, sma_fast, sma_slow, alert_mode)
    
    t24 = fetch_all_24h(scan_id)
    symbols = pick_universe(scan_id, t24)
    logger.info("[%s] Scanning %d symbols (interval=%s, limit=%d)", scan_id, len(symbols), kline_interval, kline_limit)

    events = []
    reason_counts: Dict[str, int] = {}
    
    # Charger tous les paramètres de configuration
    long_rsi_min = get_config('LONG_RSI_MIN', 45)
    long_rsi_max = get_config('LONG_RSI_MAX', 70)
    shorts_enabled = get_config('SHORTS_ENABLED', False)
    short_rsi_min = get_config('SHORT_RSI_MIN', 30)
    short_rsi_max = get_config('SHORT_RSI_MAX', 55)
    min_atr_pct = get_config('MIN_ATR_PCT', 0.25)
    min_delta_sma_bps = get_config('MIN_DELTA_SMA_BPS', 10.0)
    min_sma20_slope_bps = get_config('MIN_SMA20_SLOPE_BPS', 2.0)
    recent_cross_bars = get_config('RECENT_CROSS_BARS', 1)
    require_1h_trend = get_config('REQUIRE_1H_TREND', False)
    micro_confirm_1m_enabled = get_config('MICRO_CONFIRM_1M', False)
    mc1m_bars = get_config('MC1M_BARS', 3)

    # Load trace/debug config
    trace_symbols = get_config('TRACE_SYMBOLS', [])
    debug_top_n = get_config('DEBUG_TOP_N', 0)

    scanned_count = 0
    for idx, sym in enumerate(symbols, 1):
        if idx % 50 == 0:
            logger.info("[%s] 📊 Progress: %d/%d symbols scanned (%d%%), %d events found, %d rejected",
                       scan_id, idx, len(symbols), int(idx*100/len(symbols)), len(events), sum(reason_counts.values()))

        # Trace mode for specific symbols
        is_traced = sym in trace_symbols
        scanned_count += 1

        df = fetch_klines(scan_id, sym, kline_interval, kline_limit)
        if empty(df) or len(df) < max(sma_slow, 60):
            reason_counts["insufficient_data"] = reason_counts.get("insufficient_data", 0) + 1
            reject(scan_id, sym, "insufficient_data", {"len": 0 if df is None else len(df)}, df)
            if is_traced:
                logger.info("[%s] 🔍 TRACE %s: insufficient_data (len=%d)", scan_id, sym, 0 if df is None else len(df))
            continue

        close = df["close"]
        sma_f = sma(close, sma_fast)
        sma_s = sma(close, sma_slow)

        if is_traced:
            logger.info("[%s] 🔍 TRACE %s: close=%.2f, sma%d=%.2f, sma%d=%.2f",
                       scan_id, sym, close.iloc[-1], sma_fast, sma_f.iloc[-1], sma_slow, sma_s.iloc[-1])
        if pd.isna(sma_s.iloc[-1]) or pd.isna(sma_f.iloc[-1]):
            reason_counts["nan_sma"] = reason_counts.get("nan_sma", 0) + 1
            reject(scan_id, sym, "nan_sma", {}, df)
            continue

        atr_val = atr(df, 14).iloc[-1]
        atr_pct = float((atr_val / close.iloc[-1]) * 100.0) if close.iloc[-1] > 0 else 0.0
        rsi14 = rsi(close, 14)
        rsi_last = float(rsi14.iloc[-1])
        spread_bps = float(1e4 * ((sma_f.iloc[-1] - sma_s.iloc[-1]) / (sma_s.iloc[-1] + 1e-12)))

        if len(sma_f) >= 4:
            slope = (sma_f.iloc[-1] - sma_f.iloc[-4]) / 3.0
            slope_bps = float(1e4 * (slope / (close.iloc[-1] + 1e-12)))
        else:
            slope_bps = 0.0

        if is_traced:
            logger.info("[%s] 🔍 TRACE %s: RSI=%.1f, ATR_pct=%.2f%%, spread=%.1fbps, slope=%.1fbps",
                       scan_id, sym, rsi_last, atr_pct, spread_bps, slope_bps)

        # Log top candidates (high spread/slope) even if rejected later
        if idx <= 10 or spread_bps > 50 or slope_bps > 10:
            logger.info("[%s] 📈 %s: close=%.4f | SMA%d=%.4f SMA%d=%.4f | RSI=%.1f | ATR%%=%.2f | spread=%.1fbps | slope=%.1fbps",
                       scan_id, sym, close.iloc[-1], sma_fast, sma_f.iloc[-1], sma_slow, sma_s.iloc[-1],
                       rsi_last, atr_pct, spread_bps, slope_bps)

        if atr_pct < min_atr_pct:
            reason_counts["atr_pct_low"] = reason_counts.get("atr_pct_low", 0) + 1
            details = {"atr_pct": round(atr_pct, 3), "min": min_atr_pct}
            reject(scan_id, sym, "atr_pct_low", details, df)
            if is_traced:
                logger.info("[%s] ❌ REJECT %s: atr_pct_low %s", scan_id, sym, details)
            continue

        ctype = detect_recent_cross(sma_f, sma_s, recent_cross_bars)
        if ctype is None:
            reason_counts["no_cross"] = reason_counts.get("no_cross", 0) + 1
            reject(scan_id, sym, "no_cross", {}, df)
            if is_traced:
                logger.info("[%s] ❌ REJECT %s: no_cross (bars=%d)", scan_id, sym, recent_cross_bars)
            continue

        side = None
        if ctype == "GOLDEN":
            logger.info("[%s] 🟡 %s: GOLDEN CROSS detected! Checking conditions...", scan_id, sym)
            if not (long_rsi_min <= rsi_last <= long_rsi_max):
                reason_counts["rsi_outside_long"] = reason_counts.get("rsi_outside_long", 0) + 1
                details = {"rsi": round(rsi_last, 1), "min": long_rsi_min, "max": long_rsi_max}
                reject(scan_id, sym, "rsi_outside_long", details, df)
                logger.info("[%s] ❌ REJECT %s: rsi_outside_long %s", scan_id, sym, details)
                continue
            if spread_bps < min_delta_sma_bps:
                reason_counts["delta_sma_low"] = reason_counts.get("delta_sma_low", 0) + 1
                details = {"dSMA_bps": round(spread_bps, 1), "min": min_delta_sma_bps}
                reject(scan_id, sym, "delta_sma_low", details, df)
                logger.info("[%s] ❌ REJECT %s: delta_sma_low %s", scan_id, sym, details)
                continue
            if slope_bps < min_sma20_slope_bps:
                reason_counts["slope_low"] = reason_counts.get("slope_low", 0) + 1
                details = {"slope_bps": round(slope_bps, 1), "min": min_sma20_slope_bps}
                reject(scan_id, sym, "slope_low", details, df)
                logger.info("[%s] ❌ REJECT %s: slope_low %s", scan_id, sym, details)
                continue
            side="LONG"
            logger.info("[%s] ✅ %s: LONG signal confirmed!", scan_id, sym)
        elif ctype=="DEATH" and shorts_enabled:
            logger.info("[%s] 🔴 %s: DEATH CROSS detected! Checking conditions...", scan_id, sym)
            if not (short_rsi_min <= rsi_last <= short_rsi_max):
                reason_counts["rsi_outside_short"] = reason_counts.get("rsi_outside_short", 0) + 1
                details = {"rsi": round(rsi_last, 1), "min": short_rsi_min, "max": short_rsi_max}
                reject(scan_id, sym, "rsi_outside_short", details, df)
                logger.info("[%s] ❌ REJECT %s: rsi_outside_short %s", scan_id, sym, details)
                continue
            if abs(spread_bps) < min_delta_sma_bps:
                reason_counts["delta_sma_low"] = reason_counts.get("delta_sma_low", 0) + 1
                details = {"dSMA_bps": round(spread_bps, 1), "min": min_delta_sma_bps}
                reject(scan_id, sym, "delta_sma_low", details, df)
                logger.info("[%s] ❌ REJECT %s: delta_sma_low %s", scan_id, sym, details)
                continue
            if slope_bps > -min_sma20_slope_bps:
                reason_counts["slope_high_for_short"] = reason_counts.get("slope_high_for_short", 0) + 1
                details = {"slope_bps": round(slope_bps, 1), "max": -min_sma20_slope_bps}
                reject(scan_id, sym, "slope_high_for_short", details, df)
                logger.info("[%s] ❌ REJECT %s: slope_high_for_short %s", scan_id, sym, details)
                continue
            side="SHORT"
            logger.info("[%s] ✅ %s: SHORT signal confirmed!", scan_id, sym)
        else:
            reason_counts["shorts_disabled_or_no_side"] = reason_counts.get("shorts_disabled_or_no_side", 0) + 1
            reject(scan_id, sym, "shorts_disabled_or_no_side", {"cross": ctype}, df)
            continue

        if require_1h_trend and not trend_guard_1h(scan_id, sym):
            reason_counts["no_1h_trend"] = reason_counts.get("no_1h_trend", 0) + 1
            reject(scan_id, sym, "no_1h_trend_guard", {}, df)
            logger.info("[%s] ❌ REJECT %s: no_1h_trend_guard", scan_id, sym)
            continue
        if micro_confirm_1m_enabled and not micro_confirm_1m_func(scan_id, sym, mc1m_bars):
            reason_counts["no_micro_momentum"] = reason_counts.get("no_micro_momentum", 0) + 1
            reject(scan_id, sym, "no_micro_momentum_1m", {}, df)
            logger.info("[%s] ❌ REJECT %s: no_micro_momentum_1m", scan_id, sym)
            continue

        price=float(close.iloc[-1])
        tp, sl, sl_trigger, sl_limit = tp_sl_from_entry(price, side, float(atr_val))

        logger.info("[%s] 🎯 SIGNAL DETECTED: %s %s | Price=%.4f | TP=%.4f | SL=%.4f | RSI=%.1f | Spread=%.1fbps",
                   scan_id, sym, side, price, tp, sl, rsi_last, spread_bps)

        events.append(dict(
            scan_id=scan_id, symbol=sym, side=side, last_price=price, entry=price,
            tp=tp, sl=sl, oco_sl_trigger=sl_trigger, oco_sl_limit=sl_limit,
            rsi=rsi_last, atr_pct=atr_pct, dSMA_bps=spread_bps, slope_bps=slope_bps,
            event=ctype, score=spread_bps
        ))

    # Log reject summary
    if reason_counts:
        summary_items = sorted(reason_counts.items(), key=lambda x: -x[1])[:10]
        summary = ", ".join([f"{k}:{v}" for k,v in summary_items])
        logger.info("[%s] 📉 Reject summary (top 10): %s", scan_id, summary)
        logger.info("[%s] 📊 Total scanned: %d | Total rejected: %d | Total signals: %d",
                   scan_id, scanned_count, sum(reason_counts.values()), len(events))

    if not events:
        logger.info("[%s] Events: aucun signal conforme aux filtres.", scan_id)
        return pd.DataFrame(columns=["scan_id","symbol","side","last_price","entry","tp","sl","oco_sl_trigger","oco_sl_limit","rsi","atr_pct","dSMA_bps","slope_bps","event","score"])

    dfe=pd.DataFrame(events).sort_values("score", ascending=False).reset_index(drop=True)
    logger.info("[%s] EVENTS (%d):", scan_id, len(dfe))
    return dfe

# -------------------- PAPER TRADING --------------------
def db_connect():
    # Utiliser le chemin centralisé depuis paths.py
    db_path = str(PAPERTRADES_DB)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    paper_trading = get_config('PAPER_TRADING', True)
    if not paper_trading: return
    conn = db_connect()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY,
        uid TEXT UNIQUE,
        scan_id TEXT,
        symbol TEXT,
        side TEXT,
        status TEXT,
        opened_at TEXT,
        closed_at TEXT,
        entry REAL,
        tp REAL, sl REAL,
        rt_tp REAL, rt_sl REAL,
        use_rt INTEGER DEFAULT 0,
        close_reason TEXT,
        mfe REAL, mae REAL,
        notes TEXT
    );
    """)
    conn.commit(); conn.close()

def mk_uid(symbol: str, side: str, entry: float, opened_at_iso: str) -> str:
    opened_min = opened_at_iso[:16]
    raw = f"{symbol}|{side}|{round(float(entry),8)}|{opened_min}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def paper_trade_open(df_events: pd.DataFrame):
    paper_trading = get_config('PAPER_TRADING', True)
    if not paper_trading or empty(df_events): return
    
    conn = db_connect(); cur = conn.cursor(); now = now_iso()
    kline_interval = get_config('KLINE_INTERVAL', '5m')
    
    for _, r in df_events.iterrows():
        uid = mk_uid(str(r["symbol"]), str(r["side"]), float(r["entry"]), now)
        try:
            cur.execute("""
            INSERT OR IGNORE INTO trades (uid, scan_id, symbol, side, status, opened_at, entry, tp, sl, notes)
            VALUES (?,?,?,?, 'OPEN', ?, ?, ?, ?, ?)
            """, (uid, r["scan_id"], r["symbol"], r["side"], now, float(r["entry"]), 
                  float(r["tp"]), float(r["sl"]), json.dumps({"interval": kline_interval})))
        except Exception:
            logger.exception("paper_trade_open insert failed")
    conn.commit(); conn.close()

def candle_hit_order(side: str, high: float, low: float, tp: float, sl: float) -> Optional[str]:
    in_candle_priority = get_config('IN_CANDLE_PRIORITY', 'SL_FIRST')
    tp_hit = high >= tp; sl_hit = low <= sl
    if tp_hit and sl_hit: return "SL" if in_candle_priority=="SL_FIRST" else "TP"
    if tp_hit: return "TP"
    if sl_hit: return "SL"
    return None

def update_open_trades():
    paper_trading = get_config('PAPER_TRADING', True)
    if not paper_trading: return
    
    conn = db_connect(); cur = conn.cursor()
    rt_interval = get_config('RT_INTERVAL', '1m')
    rt_limit = get_config('RT_LIMIT', 120)
    max_hold_hours = get_config('MAX_HOLD_HOURS', 12)
    
    cur.execute("SELECT id, scan_id, symbol, side, opened_at, entry, tp, sl FROM trades WHERE status='OPEN'")
    rows = cur.fetchall()
    if not rows: conn.close(); return

    for (tid, scan_id, symbol, side, opened_at, entry, tp, sl) in rows:
        try:
            entry = float(entry)
            tp_use, sl_use = float(tp), float(sl)

            opened_dt = datetime.fromisoformat(opened_at.replace("Z","+00:00"))
            start_ms = int(opened_dt.timestamp()*1000)
            end_ms   = int(now_utc().timestamp()*1000)
            dfm = fetch_klines_range(scan_id or "paper", symbol, rt_interval, start_ms=start_ms, end_ms=end_ms, limit=rt_limit)
            if empty(dfm): continue

            if side=="LONG":
                mfe = (dfm["high"].max() - entry); mae = (entry - dfm["low"].min())
            else:
                mfe = (entry - dfm["low"].min()); mae = (dfm["high"].max() - entry)

            close_reason = None; close_time_iso = None

            for _, row in dfm.iterrows():
                hi, lo = float(row["high"]), float(row["low"])
                hit = candle_hit_order(side, hi, lo, tp_use, sl_use)
                if hit:
                    close_reason = hit; close_time_iso = row["close_time"].isoformat(); break

            if not close_reason and max_hold_hours>0 and (now_utc() - opened_dt >= timedelta(hours=max_hold_hours)):
                close_reason = "EXPIRED"; close_time_iso = now_iso()

            if close_reason:
                cur.execute("""
                    UPDATE trades SET status='CLOSED', closed_at=?, close_reason=?, mfe=?, mae=? WHERE id=?
                """, (close_time_iso, close_reason, float(mfe), float(mae), tid))
        except Exception:
            logger.exception("update_open_trades failed for %s %s", symbol, side)

    conn.commit(); conn.close()

def compute_stats(from_iso: Optional[str]=None, to_iso: Optional[str]=None) -> Dict[str, float]:
    conn = db_connect(); cur = conn.cursor()
    q = "SELECT close_reason, COUNT(*) FROM trades WHERE status='CLOSED'"
    args=[]
    if from_iso: q += " AND closed_at>=?"; args.append(from_iso)
    if to_iso:   q += " AND closed_at<?";  args.append(to_iso)
    q += " GROUP BY close_reason"; cur.execute(q, args)
    rows = cur.fetchall(); conn.close()
    wins = sum(ct for reason, ct in rows if reason=="TP")
    losses = sum(ct for reason, ct in rows if reason=="SL")
    expired = sum(ct for reason, ct in rows if reason=="EXPIRED")
    total = wins+losses+expired
    winrate = (wins/(wins+losses))*100.0 if (wins+losses)>0 else 0.0
    return {"total": total, "wins": wins, "losses": losses, "expired": expired, "winrate_pct": winrate}