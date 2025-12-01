# -*- coding: utf-8 -*-
"""
SMA20/200 + RSI — Scanner/Alerts (PTB v13, REST public Binance) + DEBUG LOGS

Améliorations:
- QUOTE_WHITELIST (ex: EUR,USDC) + préfiltrage Top-N volume
- Cross récent (RECENT_CROSS_BARS)
- Garde-fou tendance 1h (REQUIRE_1H_TREND)
- Micro-confirmation 1m (MICRO_CONFIRM_1M)
- TP/SL "RT" (1m/5m/1h) en plus des TP/SL stratégie + choix simu (REALTIME_TPSL_CHOOSE)
- Break-even (BE_ENABLE)
- /mode scalp|day|swing : applique un profil et redémarre le scheduler
- /ping /last_rejects /stats /config /top /scan
"""

import os, json, hashlib, logging, threading, sqlite3
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict

import numpy as np
import pandas as pd
import requests

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Dispatcher
from telegram.error import NetworkError

# ------------- GLOBALS (remplis par load_config) -------------
TELEGRAM_TOKEN = ""
DEFAULT_CHAT_ID = ""

USER_SYMBOLS: List[str] = []

SCAN_SECONDS = 120
TOP_K = 5
KLINE_INTERVAL = "5m"
KLINE_LIMIT = 400
USDC_ONLY = True
QUOTE_WHITELIST: List[str] = []

SMA_FAST = 20
SMA_SLOW = 200
LONG_RSI_MIN = 45
LONG_RSI_MAX = 70
SHORTS_ENABLED = False
SHORT_RSI_MIN = 30
SHORT_RSI_MAX = 55
MIN_ATR_PCT = 0.25
MIN_24H_USD = 200_000.0
MIN_DELTA_SMA_BPS = 10.0
MIN_SMA20_SLOPE_BPS = 2.0

USE_ATR_EXITS = True
TP_PCT_MIN = 1.0
SL_PCT_MIN = 0.5
ATR_TP_MULT = 1.5
ATR_SL_MULT = 1.0
OCO_BUFFER_PCT = 0.10

ALERT_MODE = "EVENTS"
COOLDOWN_MIN = 30

LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_DIR = "./logs"
LOG_ROTATE_BYTES = 5*1024*1024
LOG_BACKUP_COUNT = 5
DEBUG_TOP_N = 10
TRACE_DIR = "./trace"
TRACE_SYMBOLS: List[str] = []
DUMP_ON_REJECT = False

PAPER_TRADING = True
DB_PATH = "./papertrades.db"

REALTIME_TPSL = False
REALTIME_TPSL_CHOOSE = False
RT_INTERVAL = "1m"
RT_LIMIT = 120
IN_CANDLE_PRIORITY = "SL_FIRST"
MAX_HOLD_HOURS = 12

# Add-ons
BE_ENABLE = False
BE_TRIGGER_FRAC = 0.6
BE_OFFSET_PCT = 0.05

RECENT_CROSS_BARS = 1
REQUIRE_1H_TREND = False
MICRO_CONFIRM_1M = False
MC1M_BARS = 3
PREFILTER_TOP_N = 300
PRICECHANGE_ABS_MIN = 0.0

# -------------------- LOGGING --------------------
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    ch = logging.StreamHandler(); ch.setFormatter(fmt); root.addHandler(ch)
    if LOG_TO_FILE:
        fh_info = RotatingFileHandler(os.path.join(LOG_DIR,"app.log"), maxBytes=LOG_ROTATE_BYTES, backupCount=LOG_BACKUP_COUNT)
        fh_info.setLevel(logging.INFO); fh_info.setFormatter(fmt); root.addHandler(fh_info)
        fh_dbg = RotatingFileHandler(os.path.join(LOG_DIR,"debug.log"), maxBytes=LOG_ROTATE_BYTES, backupCount=LOG_BACKUP_COUNT)
        fh_dbg.setLevel(logging.DEBUG); fh_dbg.setFormatter(fmt); root.addHandler(fh_dbg)
        global log_events, log_rejects
        log_events  = logging.getLogger("events")
        log_rejects = logging.getLogger("rejects")
        eh = RotatingFileHandler(os.path.join(LOG_DIR,"events.log"), maxBytes=LOG_ROTATE_BYTES, backupCount=LOG_BACKUP_COUNT)
        eh.setFormatter(fmt); eh.setLevel(logging.INFO); log_events.addHandler(eh)
        rh = RotatingFileHandler(os.path.join(LOG_DIR,"rejects.log"), maxBytes=LOG_ROTATE_BYTES, backupCount=LOG_BACKUP_COUNT)
        rh.setFormatter(fmt); rh.setLevel(logging.DEBUG); log_rejects.addHandler(rh)

logger = logging.getLogger("sma20_200_rsi_dbg")

# -------------------- UTILS ENV --------------------
def env_bool(n, d=False): v=os.getenv(n); return d if v is None else str(v).strip().lower() in ("1","true","yes","y","on")
def env_int(n, d):
    try: return int(os.getenv(n, str(d)))
    except: return d
def env_float(n, d):
    try: return float(os.getenv(n, str(d)))
    except: return d

def load_config():
    global TELEGRAM_TOKEN, DEFAULT_CHAT_ID, USER_SYMBOLS
    global SCAN_SECONDS, TOP_K, KLINE_INTERVAL, KLINE_LIMIT, USDC_ONLY, QUOTE_WHITELIST
    global SMA_FAST, SMA_SLOW, LONG_RSI_MIN, LONG_RSI_MAX, SHORTS_ENABLED, SHORT_RSI_MIN, SHORT_RSI_MAX
    global MIN_ATR_PCT, MIN_24H_USD, MIN_DELTA_SMA_BPS, MIN_SMA20_SLOPE_BPS
    global USE_ATR_EXITS, TP_PCT_MIN, SL_PCT_MIN, ATR_TP_MULT, ATR_SL_MULT, OCO_BUFFER_PCT
    global ALERT_MODE, COOLDOWN_MIN, LOG_LEVEL, LOG_TO_FILE, LOG_DIR, LOG_ROTATE_BYTES, LOG_BACKUP_COUNT, DEBUG_TOP_N, TRACE_DIR, TRACE_SYMBOLS, DUMP_ON_REJECT
    global PAPER_TRADING, DB_PATH, REALTIME_TPSL, REALTIME_TPSL_CHOOSE, RT_INTERVAL, RT_LIMIT, IN_CANDLE_PRIORITY, MAX_HOLD_HOURS
    global BE_ENABLE, BE_TRIGGER_FRAC, BE_OFFSET_PCT, RECENT_CROSS_BARS, REQUIRE_1H_TREND, MICRO_CONFIRM_1M, MC1M_BARS, PREFILTER_TOP_N, PRICECHANGE_ABS_MIN

    TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN","").strip()
    DEFAULT_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID","").strip()
    USER_SYMBOLS     = [s.strip().upper() for s in os.getenv("SYMBOLS","").split(",") if s.strip()]

    SCAN_SECONDS     = env_int("SCAN_SECONDS", 120)
    TOP_K            = env_int("TOP_K", 5)
    KLINE_INTERVAL   = os.getenv("KLINE_INTERVAL","5m").lower()
    KLINE_LIMIT      = env_int("KLINE_LIMIT", 400)
    USDC_ONLY        = env_bool("USDC_ONLY", True)
    QUOTE_WHITELIST  = [s.strip().upper() for s in os.getenv("QUOTE_WHITELIST","").split(",") if s.strip()]

    SMA_FAST         = env_int("SMA_FAST", 20)
    SMA_SLOW         = env_int("SMA_SLOW", 200)
    LONG_RSI_MIN     = env_int("LONG_RSI_MIN", 45)
    LONG_RSI_MAX     = env_int("LONG_RSI_MAX", 70)
    SHORTS_ENABLED   = env_bool("ALLOW_SHORTS", False)
    SHORT_RSI_MIN    = env_int("SHORT_RSI_MIN", 30)
    SHORT_RSI_MAX    = env_int("SHORT_RSI_MAX", 55)
    MIN_ATR_PCT      = env_float("MIN_ATR_PCT", 0.25)
    MIN_24H_USD      = env_float("MIN_24H_USD", 200000.0)
    MIN_DELTA_SMA_BPS= env_float("MIN_DELTA_SMA_BPS", 10.0)
    MIN_SMA20_SLOPE_BPS = env_float("MIN_SMA20_SLOPE_BPS", 2.0)

    USE_ATR_EXITS    = env_bool("USE_ATR_EXITS", True)
    TP_PCT_MIN       = env_float("TP_PCT_MIN", 1.0)
    SL_PCT_MIN       = env_float("SL_PCT_MIN", 0.5)
    ATR_TP_MULT      = env_float("ATR_TP_MULT", 1.5)
    ATR_SL_MULT      = env_float("ATR_SL_MULT", 1.0)
    OCO_BUFFER_PCT   = env_float("OCO_BUFFER_PCT", 0.10)

    ALERT_MODE       = os.getenv("ALERT_MODE","EVENTS").upper()
    COOLDOWN_MIN     = env_int("COOLDOWN_MIN", 30)

    LOG_LEVEL        = os.getenv("LOG_LEVEL","INFO").upper()
    LOG_TO_FILE      = env_bool("LOG_TO_FILE", True)
    LOG_DIR          = os.getenv("LOG_DIR","./logs")
    LOG_ROTATE_BYTES = env_int("LOG_ROTATE_BYTES", 5*1024*1024)
    LOG_BACKUP_COUNT = env_int("LOG_BACKUP_COUNT", 5)
    DEBUG_TOP_N      = env_int("DEBUG_TOP_N", 10)
    TRACE_DIR        = os.getenv("TRACE_DIR","./trace").strip()
    TRACE_SYMBOLS    = [s.strip().upper() for s in os.getenv("TRACE_SYMBOLS","").split(",") if s.strip()]
    DUMP_ON_REJECT   = env_bool("DUMP_ON_REJECT", False)

    PAPER_TRADING       = env_bool("PAPER_TRADING", True)
    DB_PATH             = os.getenv("DB_PATH","./papertrades.db")
    REALTIME_TPSL       = env_bool("REALTIME_TPSL", False)
    REALTIME_TPSL_CHOOSE= env_bool("REALTIME_TPSL_CHOOSE", False)
    RT_INTERVAL         = os.getenv("RT_INTERVAL","1m")
    RT_LIMIT            = env_int("RT_LIMIT", 120)
    IN_CANDLE_PRIORITY  = os.getenv("IN_CANDLE_PRIORITY","SL_FIRST").upper()
    MAX_HOLD_HOURS      = env_int("MAX_HOLD_HOURS", 12)

    BE_ENABLE           = env_bool("BE_ENABLE", False)
    BE_TRIGGER_FRAC     = env_float("BE_TRIGGER_FRAC", 0.6)
    BE_OFFSET_PCT       = env_float("BE_OFFSET_PCT", 0.05)

    RECENT_CROSS_BARS   = env_int("RECENT_CROSS_BARS", 1)
    REQUIRE_1H_TREND    = env_bool("REQUIRE_1H_TREND", False)
    MICRO_CONFIRM_1M    = env_bool("MICRO_CONFIRM_1M", False)
    MC1M_BARS           = env_int("MC1M_BARS", 3)
    PREFILTER_TOP_N     = env_int("PREFILTER_TOP_N", 300)
    PRICECHANGE_ABS_MIN = env_float("PRICECHANGE_ABS_MIN", 0.0)

# -------------------- GLOBAL STATE --------------------
bot_lock = threading.Lock()
_SCHEDULER_STARTED = False
SCHEDULER: Optional[BackgroundScheduler] = None
SUBSCRIBERS_ON = True
_LAST_REJECT_SUMMARY = "n/a"

def set_last_reject_summary(txt: str):
    global _LAST_REJECT_SUMMARY
    _LAST_REJECT_SUMMARY = txt

# -------------------- DATA (Binance REST) --------------------
BINANCE_INTERVAL_MAP = {
    "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
    "1h":"1h","2h":"2h","4h":"4h","6h":"6h","12h":"12h",
    "1d":"1d","3d":"3d","1w":"1w"
}

def fetch_all_24h(scan_id:str) -> pd.DataFrame:
    url="https://api.binance.com/api/v3/ticker/24hr"
    r=requests.get(url, timeout=20); r.raise_for_status()
    data=r.json()
    df=pd.DataFrame(data)
    keep=["symbol","lastPrice","quoteVolume","priceChangePercent","highPrice","lowPrice"]
    for k in keep: 
        if k not in df.columns: df[k]=np.nan
    df=df[keep].copy()
    for c in ["lastPrice","quoteVolume","priceChangePercent","highPrice","lowPrice"]:
        df[c]=pd.to_numeric(df[c], errors="coerce")
    return df

def fetch_klines(scan_id:str, symbol: str, interval: str, limit:int) -> Optional[pd.DataFrame]:
    try:
        url="https://api.binance.com/api/v3/klines"
        params={"symbol":symbol,"interval":BINANCE_INTERVAL_MAP.get(interval,"5m"),"limit":limit}
        r=requests.get(url, params=params, timeout=20); r.raise_for_status()
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

def fetch_klines_range(scan_id: str, symbol: str, interval: str, start_ms: Optional[int]=None, end_ms: Optional[int]=None, limit: Optional[int]=None) -> Optional[pd.DataFrame]:
    try:
        url="https://api.binance.com/api/v3/klines"
        params={"symbol":symbol, "interval":BINANCE_INTERVAL_MAP.get(interval, interval)}
        if start_ms is not None: params["startTime"] = int(start_ms)
        if end_ms is not None: params["endTime"] = int(end_ms)
        if limit is not None: params["limit"] = int(limit)
        r=requests.get(url, params=params, timeout=20); r.raise_for_status()
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

def ema(series: pd.Series, span:int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def atr(df: pd.DataFrame, period:int=14) -> pd.Series:
    h,l,c=df["high"],df["low"],df["close"]; pc=c.shift(1)
    tr=pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

def rsi(series: pd.Series, period:int=14) -> pd.Series:
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

NUM_COLS=["last_price","entry","tp","sl","score"]
STR_COLS=["symbol","side"]
CANON_COLS=STR_COLS+NUM_COLS

def picks_fp(df: Optional[pd.DataFrame]) -> Optional[str]:
    if empty(df): return None
    tmp=df.copy()
    for c in NUM_COLS:
        if c in tmp.columns: tmp[c]=pd.to_numeric(tmp[c],errors="coerce").round(8)
    for c in STR_COLS:
        if c in tmp.columns: tmp[c]=tmp[c].astype(str)
    tmp=tmp[[c for c in CANON_COLS if c in tmp.columns]]
    by=[c for c in ["symbol","side","score","last_price"] if c in tmp.columns]
    if by: tmp=tmp.sort_values(by=by, ascending=[True,True,False,False]).reset_index(drop=True)
    import hashlib as _h
    return _h.sha1(tmp.to_csv(index=False).encode("utf-8")).hexdigest()

# -------------------- UNIVERSE --------------------
def pick_universe(scan_id:str, t24: pd.DataFrame) -> List[str]:
    if USER_SYMBOLS:
        logger.info("[%s] Universe forced by SYMBOLS: %d", scan_id, len(USER_SYMBOLS))
        return USER_SYMBOLS
    df=t24.copy()

    if QUOTE_WHITELIST:
        mask = False
        for q in QUOTE_WHITELIST:
            mask = mask | df["symbol"].str.endswith(q)
        df = df[mask]
    elif USDC_ONLY:
        df=df[df["symbol"].str.endswith("USDC")]

    before=len(df)
    df=df[df["quoteVolume"]>=MIN_24H_USD]
    if PRICECHANGE_ABS_MIN>0:
        df=df[df["priceChangePercent"].abs()>=PRICECHANGE_ABS_MIN]
    df=df.sort_values("quoteVolume", ascending=False).head(PREFILTER_TOP_N)
    logger.info("[%s] Universe: QUOTE_WHITELIST=%s, USDC_ONLY=%s, MIN_24H_USD=%.0f → %d→%d symbols (topN=%d)",
                scan_id, QUOTE_WHITELIST, USDC_ONLY, MIN_24H_USD, before, len(df), PREFILTER_TOP_N)
    syms=sorted(df["symbol"].tolist())
    return syms or (["BTCEUR","ETHEUR"] if "EUR" in QUOTE_WHITELIST else ["ETHUSDC","BTCUSDC","SOLUSDC"])

# -------------------- TP/SL helpers --------------------
def tp_sl_from_entry(price: float, side:str, atr_val: float) -> Tuple[float,float,float,float]:
    if USE_ATR_EXITS:
        sl_abs=max(price*SL_PCT_MIN/100.0, ATR_SL_MULT*atr_val)
        tp_abs=max(price*TP_PCT_MIN/100.0, ATR_TP_MULT*atr_val)
    else:
        sl_abs=price*SL_PCT_MIN/100.0
        tp_abs=price*TP_PCT_MIN/100.0
    if side=="LONG":
        sl=price-sl_abs; tp=price+tp_abs
        sl_trigger=sl; sl_limit=sl_trigger*(1.0 - OCO_BUFFER_PCT/100.0)
    else:
        tp=price-tp_abs; sl=price+sl_abs
        sl_trigger=sl; sl_limit=sl_trigger*(1.0 + OCO_BUFFER_PCT/100.0)
    return tp, sl, sl_trigger, sl_limit

# -------------------- TRACE --------------------
def ensure_dir(path: str):
    if not path: return
    os.makedirs(path, exist_ok=True)

def dump_trace(scan_id:str, symbol:str, dfk:pd.DataFrame, extras:Dict):
    if not TRACE_DIR: return
    ensure_dir(TRACE_DIR)
    try:
        fn_csv=os.path.join(TRACE_DIR, f"{scan_id}_{symbol}_{KLINE_INTERVAL}.csv")
        dfk.to_csv(fn_csv, index=False)
        fn_meta=os.path.join(TRACE_DIR, f"{scan_id}_{symbol}_{KLINE_INTERVAL}_meta.json")
        with open(fn_meta,"w") as f:
            json.dump(extras, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def dump_on_reject(scan_id: str, symbol: str, dfk: Optional[pd.DataFrame], reason: str, metrics: Dict):
    if not DUMP_ON_REJECT or not TRACE_DIR: return
    if TRACE_SYMBOLS and symbol not in TRACE_SYMBOLS: return
    if dfk is None or dfk.empty: dfk = pd.DataFrame({"note":["no_klines_for_reject"]})
    extras = {"reject_reason": reason, "metrics": metrics}
    try: dump_trace(scan_id, symbol, dfk, extras)
    except Exception: pass

def reject(scan_id:str, symbol:str, reason:str, details:Dict, dfk: Optional[pd.DataFrame]):
    payload={"scan_id":scan_id,"symbol":symbol,"reason":reason,"details":details}
    logging.getLogger("rejects").debug(json.dumps(payload, ensure_ascii=False))
    dump_on_reject(scan_id, symbol, dfk, reason, details)

# -------------------- SIGNALS --------------------
def detect_recent_cross(sma_f: pd.Series, sma_s: pd.Series, bars: int = RECENT_CROSS_BARS) -> Optional[str]:
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

def micro_confirm_1m(scan_id: str, symbol: str, bars: int = MC1M_BARS) -> bool:
    df = fetch_klines_range(scan_id, symbol, "1m", limit=max(30, bars+5))
    if empty(df): return False
    c = df["close"].astype(float)
    ema9 = ema(c, 9)
    tail = c.tail(bars).reset_index(drop=True)
    tail_ema = ema9.tail(bars).reset_index(drop=True)
    return bool((tail > tail_ema).all())

def compute_realtime_tpsl(scan_id: str, symbol: str, side: str, entry: float) -> Tuple[float,float]:
    df_rt = fetch_klines_range(scan_id, symbol, RT_INTERVAL, limit=RT_LIMIT)
    if empty(df_rt): return (None, None)
    atr_rt = float(atr(df_rt, 14).iloc[-1])
    if USE_ATR_EXITS:
        sl_abs=max(entry*SL_PCT_MIN/100.0, ATR_SL_MULT*atr_rt)
        tp_abs=max(entry*TP_PCT_MIN/100.0, ATR_TP_MULT*atr_rt)
    else:
        sl_abs=entry*SL_PCT_MIN/100.0
        tp_abs=entry*TP_PCT_MIN/100.0
    if side=="LONG": return (entry+tp_abs, entry-sl_abs)
    else:            return (entry-tp_abs, entry+sl_abs)

def run_scan_events() -> pd.DataFrame:
    scan_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(os.urandom(8)).hexdigest()[:6]
    logger.info("== scan_id=%s | SMA%u/%u + RSI | MODE=%s ==", scan_id, SMA_FAST, SMA_SLOW, ALERT_MODE)
    t24 = fetch_all_24h(scan_id)
    symbols = pick_universe(scan_id, t24)
    logger.info("[%s] Scanning %d symbols (interval=%s, limit=%d)", scan_id, len(symbols), KLINE_INTERVAL, KLINE_LIMIT)

    events = []
    reason_counts: Dict[str, int] = {}
    dbg_count = 0

    for idx, sym in enumerate(symbols, 1):
        if idx % 200 == 0: logger.info("[%s] progress: %d/%d symbols", scan_id, idx, len(symbols))

        df = fetch_klines(scan_id, sym, KLINE_INTERVAL, KLINE_LIMIT)
        if empty(df) or len(df) < max(SMA_SLOW, 60):
            reason_counts["insufficient_data"] = reason_counts.get("insufficient_data", 0) + 1
            reject(scan_id, sym, "insufficient_data", {"len": 0 if df is None else len(df)}, df); continue

        close = df["close"]; sma_f = sma(close, SMA_FAST); sma_s = sma(close, SMA_SLOW)
        if pd.isna(sma_s.iloc[-1]) or pd.isna(sma_f.iloc[-1]):
            reason_counts["nan_sma"] = reason_counts.get("nan_sma", 0) + 1
            reject(scan_id, sym, "nan_sma", {}, df); continue

        atr_val = atr(df, 14).iloc[-1]
        atr_pct = float((atr_val / close.iloc[-1]) * 100.0) if close.iloc[-1] > 0 else 0.0
        rsi14 = rsi(close, 14); rsi_last = float(rsi14.iloc[-1])
        spread_bps = float(1e4 * ((sma_f.iloc[-1] - sma_s.iloc[-1]) / (sma_s.iloc[-1] + 1e-12)))

        if len(sma_f) >= 4:
            slope = (sma_f.iloc[-1] - sma_f.iloc[-4]) / 3.0
            slope_bps = float(1e4 * (slope / (close.iloc[-1] + 1e-12)))
        else:
            slope_bps = 0.0

        if logging.getLogger().level <= logging.DEBUG and (dbg_count < DEBUG_TOP_N or sym in TRACE_SYMBOLS):
            logger.debug("[%s] %s tail close=%s | SMA%u=%.6f SMA%u=%.6f | RSI=%.2f | ATR%%=%.3f | dSMA=%.2f bps | slope=%.2f bps",
                         scan_id, sym, [float(x) for x in close.tail(5).tolist()],
                         SMA_FAST, float(sma_f.iloc[-1]), SMA_SLOW, float(sma_s.iloc[-1]),
                         rsi_last, atr_pct, spread_bps, slope_bps)
            dbg_count += 1

        if atr_pct < MIN_ATR_PCT:
            reason_counts["atr_pct_low"] = reason_counts.get("atr_pct_low", 0) + 1
            reject(scan_id, sym, "atr_pct_low", {"atr_pct": atr_pct, "min": MIN_ATR_PCT}, df); continue

        ctype = detect_recent_cross(sma_f, sma_s, RECENT_CROSS_BARS)
        if ctype is None:
            reason_counts["no_cross"] = reason_counts.get("no_cross", 0) + 1
            reject(scan_id, sym, "no_cross", {}, df); continue

        side = None
        if ctype == "GOLDEN":
            if not (LONG_RSI_MIN <= rsi_last <= LONG_RSI_MAX):
                reason_counts["rsi_outside_long"] = reason_counts.get("rsi_outside_long", 0) + 1
                reject(scan_id, sym, "rsi_outside_long", {"rsi": rsi_last, "min": LONG_RSI_MIN, "max": LONG_RSI_MAX}, df); continue
            if spread_bps < MIN_DELTA_SMA_BPS:
                reason_counts["delta_sma_low"] = reason_counts.get("delta_sma_low", 0) + 1
                reject(scan_id, sym, "delta_sma_low", {"dSMA_bps": spread_bps, "min": MIN_DELTA_SMA_BPS}, df); continue
            if slope_bps < MIN_SMA20_SLOPE_BPS:
                reason_counts["slope_low"] = reason_counts.get("slope_low", 0) + 1
                reject(scan_id, sym, "slope_low", {"slope_bps": slope_bps, "min": MIN_SMA20_SLOPE_BPS}, df); continue
            side="LONG"
        elif ctype=="DEATH" and SHORTS_ENABLED:
            if not (SHORT_RSI_MIN <= rsi_last <= SHORT_RSI_MAX):
                reason_counts["rsi_outside_short"] = reason_counts.get("rsi_outside_short", 0) + 1
                reject(scan_id, sym, "rsi_outside_short", {"rsi": rsi_last, "min": SHORT_RSI_MIN, "max": SHORT_RSI_MAX}, df); continue
            if abs(spread_bps) < MIN_DELTA_SMA_BPS:
                reason_counts["delta_sma_low"] = reason_counts.get("delta_sma_low", 0) + 1
                reject(scan_id, sym, "delta_sma_low", {"dSMA_bps": spread_bps, "min": MIN_DELTA_SMA_BPS}, df); continue
            if slope_bps > -MIN_SMA20_SLOPE_BPS:
                reason_counts["slope_high_for_short"] = reason_counts.get("slope_high_for_short", 0) + 1
                reject(scan_id, sym, "slope_high_for_short", {"slope_bps": slope_bps, "max": -MIN_SMA20_SLOPE_BPS}, df); continue
            side="SHORT"
        else:
            reason_counts["shorts_disabled_or_no_side"] = reason_counts.get("shorts_disabled_or_no_side", 0) + 1
            reject(scan_id, sym, "shorts_disabled_or_no_side", {"cross": ctype}, df); continue

        if REQUIRE_1H_TREND and not trend_guard_1h(scan_id, sym):
            reason_counts["no_1h_trend"] = reason_counts.get("no_1h_trend", 0) + 1
            reject(scan_id, sym, "no_1h_trend_guard", {}, df); continue
        if MICRO_CONFIRM_1M and not micro_confirm_1m(scan_id, sym, MC1M_BARS):
            reason_counts["no_micro_momentum"] = reason_counts.get("no_micro_momentum", 0) + 1
            reject(scan_id, sym, "no_micro_momentum_1m", {}, df); continue

        price=float(close.iloc[-1])
        tp, sl, sl_trigger, sl_limit = tp_sl_from_entry(price, side, float(atr_val))
        rt_tp, rt_sl = (None, None)
        if REALTIME_TPSL:
            rt_tp, rt_sl = compute_realtime_tpsl(scan_id, sym, side, price)

        events.append(dict(
            scan_id=scan_id, symbol=sym, side=side, last_price=price, entry=price,
            tp=tp, sl=sl, oco_sl_trigger=sl_trigger, oco_sl_limit=sl_limit,
            rsi=rsi_last, atr_pct=atr_pct, dSMA_bps=spread_bps, slope_bps=slope_bps,
            event=ctype, score=spread_bps, rt_tp=rt_tp, rt_sl=rt_sl,
        ))

    if reason_counts:
        summary = ", ".join([f"{k}:{v}" for k,v in sorted(reason_counts.items(), key=lambda kv: -kv[1])])
        logger.info("[%s] Reject summary → %s", scan_id, summary); set_last_reject_summary(summary)

    if not events:
        logger.info("[%s] Events: aucun signal conforme aux filtres.", scan_id)
        return pd.DataFrame(columns=["scan_id","symbol","side","last_price","entry","tp","sl","oco_sl_trigger","oco_sl_limit","rsi","atr_pct","dSMA_bps","slope_bps","event","score","rt_tp","rt_sl"])

    dfe=pd.DataFrame(events).sort_values("score", ascending=False).reset_index(drop=True)
    logger.info("[%s] EVENTS (%d):", scan_id, len(dfe))
    for _,r in dfe.iterrows():
        msg=(f"{r['symbol']} {r['side']} ({r['event']}) Px {fmt(r['last_price'])} | TP {fmt(r['tp'])} | SL {fmt(r['sl'])} | "
             f"ΔSMA≈{r['dSMA_bps']:.1f} bps | slope≈{r['slope_bps']:.1f} bps | RSI={r['rsi']:.1f} | ATR%={r['atr_pct']:.2f}")
        logger.info("[%s] • %s", r["scan_id"], msg)
        logging.getLogger("events").info(json.dumps(r.to_dict(), ensure_ascii=False))
    return dfe

# -------------------- CACHE / COOLDOWN --------------------
def save_picks(ctx: CallbackContext, df: pd.DataFrame):
    with bot_lock:
        ctx.bot_data["latest_picks"] = None if empty(df) else df.head(TOP_K).reset_index(drop=True).copy()
        ctx.bot_data["latest_fp"] = picks_fp(ctx.bot_data["latest_picks"])
        ctx.bot_data["last_scan_at"] = now_iso()
        ctx.bot_data.setdefault("cooldown_until", {})

def filter_by_cooldown(ctx: CallbackContext, df: pd.DataFrame) -> pd.DataFrame:
    if empty(df): return df
    cd: Dict[str,str] = ctx.bot_data.setdefault("cooldown_until", {})
    now=now_utc(); keep=[]
    for _,r in df.iterrows():
        sym=str(r["symbol"]); ts=cd.get(sym)
        until=datetime.fromisoformat(ts) if ts else now - timedelta(seconds=1)
        if now>=until: keep.append(r)
        else: logging.getLogger("rejects").debug(json.dumps({"scan_id":r["scan_id"],"symbol":sym,"reason":"cooldown_active","until":ts}, ensure_ascii=False))
    return pd.DataFrame(keep) if keep else pd.DataFrame(columns=df.columns)

def mark_cooldown(ctx: CallbackContext, df: pd.DataFrame):
    if empty(df): return
    cd: Dict[str,str] = ctx.bot_data.setdefault("cooldown_until", {})
    until=(now_utc()+timedelta(minutes=COOLDOWN_MIN)).isoformat()
    for _,r in df.iterrows(): cd[str(r["symbol"])]=until

# -------------------- PAPER TRADING --------------------
def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    if not PAPER_TRADING: return
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

def pick_tp_sl_for_sim(row: pd.Series) -> Tuple[float,float,bool]:
    base_tp, base_sl = float(row["tp"]), float(row["sl"])
    rt_tp, rt_sl = row.get("rt_tp", None), row.get("rt_sl", None)
    if REALTIME_TPSL and REALTIME_TPSL_CHOOSE and pd.notna(rt_tp) and pd.notna(rt_sl):
        return float(rt_tp), float(rt_sl), True
    return base_tp, base_sl, False

def paper_trade_open(df_events: pd.DataFrame):
    if not PAPER_TRADING or empty(df_events): return
    conn = db_connect(); cur = conn.cursor(); now = now_iso()
    for _, r in df_events.iterrows():
        tp_use, sl_use, use_rt = pick_tp_sl_for_sim(r)
        uid = mk_uid(str(r["symbol"]), str(r["side"]), float(r["entry"]), now)
        try:
            cur.execute("""
            INSERT OR IGNORE INTO trades (uid, scan_id, symbol, side, status, opened_at, entry, tp, sl, rt_tp, rt_sl, use_rt, notes)
            VALUES (?,?,?,?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, r["scan_id"], r["symbol"], r["side"], now, float(r["entry"]), float(r["tp"]), float(r["sl"]),
                  None if pd.isna(r.get("rt_tp", np.nan)) else float(r.get("rt_tp")),
                  None if pd.isna(r.get("rt_sl", np.nan)) else float(r.get("rt_sl")),
                  1 if use_rt else 0, json.dumps({"interval": KLINE_INTERVAL})))
        except Exception:
            logger.exception("paper_trade_open insert failed")
    conn.commit(); conn.close()

def candle_hit_order(side: str, high: float, low: float, tp: float, sl: float) -> Optional[str]:
    tp_hit = high >= tp; sl_hit = low <= sl
    if tp_hit and sl_hit: return "SL" if IN_CANDLE_PRIORITY=="SL_FIRST" else "TP"
    if tp_hit: return "TP"
    if sl_hit: return "SL"
    return None

def update_open_trades():
    if not PAPER_TRADING: return
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT id, scan_id, symbol, side, opened_at, entry, tp, sl, rt_tp, rt_sl, use_rt FROM trades WHERE status='OPEN'")
    rows = cur.fetchall()
    if not rows: conn.close(); return

    for (tid, scan_id, symbol, side, opened_at, entry, tp, sl, rt_tp, rt_sl, use_rt) in rows:
        try:
            entry = float(entry)
            if use_rt and rt_tp is not None and rt_sl is not None:
                tp_use, sl_use = float(rt_tp), float(rt_sl)
            else:
                tp_use, sl_use = float(tp), float(sl)

            opened_dt = datetime.fromisoformat(opened_at.replace("Z","+00:00"))
            start_ms = int(opened_dt.timestamp()*1000)
            end_ms   = int(now_utc().timestamp()*1000)
            dfm = fetch_klines_range(scan_id or "paper", symbol, RT_INTERVAL, start_ms=start_ms, end_ms=end_ms, limit=RT_LIMIT)
            if empty(dfm): continue

            if side=="LONG":
                mfe = (dfm["high"].max() - entry); mae = (entry - dfm["low"].min())
            else:
                mfe = (entry - dfm["low"].min()); mae = (dfm["high"].max() - entry)

            close_reason = None; close_time_iso = None

            if BE_ENABLE:
                target = tp_use
                progress_price = entry + BE_TRIGGER_FRAC*(target - entry) if side=="LONG" else entry - BE_TRIGGER_FRAC*(entry - target)

            for _, row in dfm.iterrows():
                hi, lo = float(row["high"]), float(row["low"])
                if BE_ENABLE:
                    if side=="LONG" and hi >= progress_price:
                        sl_use = entry*(1 - BE_OFFSET_PCT/100.0)
                    elif side!="LONG" and lo <= progress_price:
                        sl_use = entry*(1 + BE_OFFSET_PCT/100.0)

                hit = candle_hit_order(side, hi, lo, tp_use, sl_use)
                if hit:
                    close_reason = hit; close_time_iso = row["close_time"].isoformat(); break

            if not close_reason and MAX_HOLD_HOURS>0 and (now_utc() - opened_dt >= timedelta(hours=MAX_HOLD_HOURS)):
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

# -------------------- TELEGRAM --------------------
def lines_from_df(df: pd.DataFrame) -> List[str]:
    lines=[]
    for _,r in df.iterrows():
        base=f"• {r['symbol']}  *{r.get('side','?')}*"
        if "event" in r: base+=f" ({r['event']})"
        detail=(f"\n  Px {fmt(r['last_price'])} | TP {fmt(r['tp'])} | SL {fmt(r['sl'])}"
                f" | ΔSMA≈{round(float(r.get('dSMA_bps',0)),1)} bps"
                f" | slope≈{round(float(r.get('slope_bps',0)),1)} bps"
                f" | RSI {round(float(r.get('rsi',0)),1)} | ATR% {round(float(r.get('atr_pct',0)),2)}")
        if not pd.isna(r.get('rt_tp', np.nan)) and not pd.isna(r.get('rt_sl', np.nan)):
            detail += f"\n  (RT) TP {fmt(r['rt_tp'])} | SL {fmt(r['rt_sl'])}  [{RT_INTERVAL}]"
        if "oco_sl_trigger" in r and "oco_sl_limit" in r:
            detail+=f"\n  OCO Stop: Déclenchement {fmt(r['oco_sl_trigger'])} | Limit SL {fmt(r['oco_sl_limit'])} (buffer {OCO_BUFFER_PCT}%)"
        lines.append(base+detail)
    return lines

def push_alerts(updater: Updater, df: pd.DataFrame, chat_id: Optional[str]) -> None:
    if empty(df) or not chat_id: return
    lines=lines_from_df(df)
    header=f"📣 *SMA{SMA_FAST}/{SMA_SLOW} + RSI* ({len(df)})"
    try:
        updater.bot.send_message(chat_id=chat_id, text=header+"\n"+"\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logger.exception("push_alerts failed")

# -------------------- HANDLERS --------------------
def start_cmd(update: Update, context: CallbackContext):
    with bot_lock:
        subs=context.bot_data.setdefault("subscribers", set()); subs.add(update.effective_chat.id)
    config_cmd(update, context)

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Cmd:\n"
        "• /scan — scan immédiat\n"
        "• /top — derniers signaux\n"
        "• /stats — stats paper trading\n"
        "• /last_rejects — dernier résumé de rejets\n"
        "• /mode <scalp|day|swing>\n"
        "• /alerts_on | /alerts_off | /ping | /config"
    )

def config_cmd(update: Update, context: CallbackContext):
    txt=(f"⚙️ SMA{SMA_FAST}/{SMA_SLOW} | RSI LONG [{LONG_RSI_MIN},{LONG_RSI_MAX}]\n"
         f"ΔSMA≥{MIN_DELTA_SMA_BPS} bps, slope≥{MIN_SMA20_SLOPE_BPS} bps/bar, ATR%≥{MIN_ATR_PCT}\n"
         f"Cross≤{RECENT_CROSS_BARS} | 1h_trend_guard={REQUIRE_1H_TREND} | micro_1m={MICRO_CONFIRM_1M}({MC1M_BARS})\n"
         f"TP/SL: {'ATR-based' if USE_ATR_EXITS else 'fixed'} (TP≥{TP_PCT_MIN}%, SL≥{SL_PCT_MIN}% | TPx={ATR_TP_MULT}, SLx={ATR_SL_MULT})\n"
         f"OCO buffer {OCO_BUFFER_PCT}% | Cooldown {COOLDOWN_MIN}m | Mode {ALERT_MODE}\n"
         f"Scan {SCAN_SECONDS}s | TOP_K {TOP_K} | QUOTES {QUOTE_WHITELIST or ('USDC_ONLY' if USDC_ONLY else 'ALL')}\n"
         f"Universe: MIN_24H_USD={MIN_24H_USD}, topN={PREFILTER_TOP_N}, |Δ%|≥{PRICECHANGE_ABS_MIN}\n"
         f"RT_TPSL={REALTIME_TPSL} choose={REALTIME_TPSL_CHOOSE} | Paper={PAPER_TRADING} | BE={BE_ENABLE} ({BE_TRIGGER_FRAC*100:.0f}%→{BE_OFFSET_PCT}%)\n"
         f"Logs→{LOG_DIR}  Traces→{TRACE_DIR}")
    update.message.reply_text(txt)

def alerts_on_cmd(update: Update, context: CallbackContext):
    global SUBSCRIBERS_ON
    SUBSCRIBERS_ON=True
    with bot_lock:
        subs=context.bot_data.setdefault("subscribers", set()); subs.add(update.effective_chat.id)
    update.message.reply_text("✅ Alertes activées.")

def alerts_off_cmd(update: Update, context: CallbackContext):
    global SUBSCRIBERS_ON
    SUBSCRIBERS_ON=False
    update.message.reply_text("🔕 Alertes désactivées.")

def top_cmd(update: Update, context: CallbackContext):
    with bot_lock:
        df=context.bot_data.get("latest_picks"); ts=context.bot_data.get("last_scan_at","n/a")
    if empty(df): update.message.reply_text("Aucun signal en cache."); return
    update.message.reply_text(f"TOP {len(df)} (dernier scan: {ts})\n"+"\n".join(lines_from_df(df)), parse_mode=ParseMode.MARKDOWN)

def stats_cmd(update: Update, context: CallbackContext):
    try:
        s = compute_stats()
        txt = (f"📊 Paper Trading Stats\n"
               f"Total: {s['total']}\n"
               f"TP: {s['wins']} | SL: {s['losses']} | Expired: {s['expired']}\n"
               f"Winrate: {s['winrate_pct']:.2f}%")
        update.message.reply_text(txt)
    except Exception:
        logger.exception("/stats failed"); update.message.reply_text("Erreur lors du calcul des stats.")

def last_rejects_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(f"📉 Derniers rejets:\n{_LAST_REJECT_SUMMARY}")

def ping_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("pong ✅")

def scan_cmd(update: Update, context: CallbackContext):
    update_open_trades()
    dfe=run_scan_events()
    dfe=filter_by_cooldown(context, dfe)
    save_picks(context, dfe)
    if PAPER_TRADING and not empty(dfe): paper_trade_open(dfe)
    if empty(dfe): update.message.reply_text("Scan: aucun signal."); return
    mark_cooldown(context, dfe)
    update.message.reply_text("Signaux:\n"+"\n".join(lines_from_df(dfe)), parse_mode=ParseMode.MARKDOWN)

def error_handler(update: object, context: CallbackContext):
    # ignore NetworkError spam from polling loop
    if isinstance(context.error, NetworkError):
        logging.getLogger("telegram.ext.updater").setLevel(logging.WARNING)
        return
    logger.exception("Unhandled", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try: update.effective_message.reply_text("Oups, une erreur est survenue.")
        except: pass

# -------------------- MODES --------------------
PROFILES = {
    "SCALP": {
        "USDC_ONLY":"true", "QUOTE_WHITELIST":"EUR,USDC",   # adapte à tes contraintes
        "MIN_24H_USD":"3000000", "PREFILTER_TOP_N":"300", "PRICECHANGE_ABS_MIN":"0",
        "KLINE_INTERVAL":"5m", "KLINE_LIMIT":"240",
        "SMA_FAST":"20","SMA_SLOW":"200","RECENT_CROSS_BARS":"3",
        "MIN_ATR_PCT":"0.15","MIN_DELTA_SMA_BPS":"4","MIN_SMA20_SLOPE_BPS":"0.8",
        "LONG_RSI_MIN":"45","LONG_RSI_MAX":"70",
        "REQUIRE_1H_TREND":"true","MICRO_CONFIRM_1M":"true","MC1M_BARS":"3",
        "USE_ATR_EXITS":"true","ATR_TP_MULT":"1.3","ATR_SL_MULT":"1.0","TP_PCT_MIN":"0.9","SL_PCT_MIN":"0.6","OCO_BUFFER_PCT":"0.12",
        "SCAN_SECONDS":"180","COOLDOWN_MIN":"20","TOP_K":"5",
        "RT_INTERVAL":"1m","RT_LIMIT":"120","MAX_HOLD_HOURS":"12"
    },
    "DAY": {
        "USDC_ONLY":"false","QUOTE_WHITELIST":"EUR,USDC",
        "MIN_24H_USD":"5000000","PREFILTER_TOP_N":"350","PRICECHANGE_ABS_MIN":"0",
        "KLINE_INTERVAL":"15m","KLINE_LIMIT":"300",
        "SMA_FAST":"20","SMA_SLOW":"200","RECENT_CROSS_BARS":"3",
        "MIN_ATR_PCT":"0.10","MIN_DELTA_SMA_BPS":"4","MIN_SMA20_SLOPE_BPS":"0.6",
        "LONG_RSI_MIN":"45","LONG_RSI_MAX":"70",
        "REQUIRE_1H_TREND":"true","MICRO_CONFIRM_1M":"false",
        "USE_ATR_EXITS":"true","ATR_TP_MULT":"1.4","ATR_SL_MULT":"1.0","TP_PCT_MIN":"1.1","SL_PCT_MIN":"0.7","OCO_BUFFER_PCT":"0.12",
        "SCAN_SECONDS":"300","COOLDOWN_MIN":"20","TOP_K":"6",
        "RT_INTERVAL":"5m","RT_LIMIT":"216","MAX_HOLD_HOURS":"24"
    },
    "SWING": {
        "USDC_ONLY":"false","QUOTE_WHITELIST":"EUR,USDC",
        "MIN_24H_USD":"8000000","PREFILTER_TOP_N":"250","PRICECHANGE_ABS_MIN":"0",
        "KLINE_INTERVAL":"4h","KLINE_LIMIT":"300",
        "SMA_FAST":"20","SMA_SLOW":"200","RECENT_CROSS_BARS":"3",
        "MIN_ATR_PCT":"0.60","MIN_DELTA_SMA_BPS":"6","MIN_SMA20_SLOPE_BPS":"0.8",
        "LONG_RSI_MIN":"45","LONG_RSI_MAX":"68",
        "REQUIRE_1H_TREND":"false","MICRO_CONFIRM_1M":"false",
        "USE_ATR_EXITS":"true","ATR_TP_MULT":"2.0","ATR_SL_MULT":"1.0","TP_PCT_MIN":"3.0","SL_PCT_MIN":"1.5","OCO_BUFFER_PCT":"0.15",
        "SCAN_SECONDS":"600","COOLDOWN_MIN":"60","TOP_K":"8",
        "RT_INTERVAL":"1h","RT_LIMIT":"240","MAX_HOLD_HOURS":"168"
    }
}

def apply_profile(name: str):
    prof = PROFILES.get(name.upper())
    if not prof: return False
    for k,v in prof.items(): os.environ[k] = v
    load_config()  # recharge dans les globals
    return True

def restart_scheduler(updater: Updater, dispatcher: Dispatcher):
    global SCHEDULER
    if SCHEDULER is None:
        SCHEDULER = BackgroundScheduler(timezone="UTC")
        SCHEDULER.start()
    # remplace le job
    try:
        SCHEDULER.remove_job("scheduled_scan")
    except Exception:
        pass
    SCHEDULER.add_job(scheduled_scan, "interval", seconds=SCAN_SECONDS,
                      args=[updater, dispatcher], id="scheduled_scan",
                      replace_existing=True, coalesce=True, max_instances=1)
    logger.info("Scheduler (re)started with SCAN_SECONDS=%s", SCAN_SECONDS)

def mode_cmd(update: Update, context: CallbackContext):
    args = context.args or []
    if not args:
        update.message.reply_text("Usage: /mode scalp|day|swing"); return
    name = args[0].lower()
    if name not in ("scalp","day","swing"):
        update.message.reply_text("Modes: scalp | day | swing"); return
    ok = apply_profile(name)
    if not ok:
        update.message.reply_text("Profil introuvable."); return
    # redémarre le scheduler
    restart_scheduler(context.bot, context.dispatcher)
    update.message.reply_text(f"✅ Mode *{name.upper()}* appliqué.\nTip: /config pour voir les paramètres.", parse_mode=ParseMode.MARKDOWN)

# -------------------- SCHED --------------------
def scheduled_scan(updater: Updater, dispatcher: Dispatcher):
    try:
        update_open_trades()
        dfe=run_scan_events()
        dfe=filter_by_cooldown(dispatcher, dfe)
        with bot_lock:
            prev_fp=dispatcher.bot_data.get("prev_evt_fp")
        save_picks(dispatcher, dfe)

        with bot_lock:
            df_cached=dispatcher.bot_data.get("latest_picks")
            new_fp=dispatcher.bot_data.get("latest_fp")
            subs=set(dispatcher.bot_data.get("subscribers", set()))
        if DEFAULT_CHAT_ID: subs.add(int(DEFAULT_CHAT_ID))
        if SUBSCRIBERS_ON and not empty(df_cached) and (not prev_fp or new_fp!=prev_fp):
            for chat_id in subs: push_alerts(updater, df_cached, chat_id)
            mark_cooldown(dispatcher, df_cached)
            logger.info("Alerts sent to %d subs", len(subs))
        else:
            logger.info("Dedup/cooldown: pas d'alerte.")

        if PAPER_TRADING and not empty(df_cached): paper_trade_open(df_cached)
        with bot_lock: dispatcher.bot_data["prev_evt_fp"]=new_fp
    except Exception:
        logger.exception("scheduled_scan error")

# -------------------- MAIN --------------------
def main():
    load_config()
    setup_logging()
    if not TELEGRAM_TOKEN: raise SystemExit("TELEGRAM_TOKEN manquant")
    init_db()

    updater=Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp=updater.dispatcher

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("config", config_cmd))
    dp.add_handler(CommandHandler("scan", scan_cmd))
    dp.add_handler(CommandHandler("top", top_cmd))
    dp.add_handler(CommandHandler("stats", stats_cmd))
    dp.add_handler(CommandHandler("last_rejects", last_rejects_cmd))
    dp.add_handler(CommandHandler("alerts_on", alerts_on_cmd))
    dp.add_handler(CommandHandler("alerts_off", alerts_off_cmd))
    dp.add_handler(CommandHandler("ping", ping_cmd))
    dp.add_handler(CommandHandler("mode", mode_cmd, pass_args=True))
    dp.add_error_handler(error_handler)

    if DEFAULT_CHAT_ID:
        try:
            updater.bot.send_message(chat_id=int(DEFAULT_CHAT_ID),
                text=(f"🤖 Prêt | Scan={SCAN_SECONDS}s | Mode={ALERT_MODE}\n"
                      f"Cross≤{RECENT_CROSS_BARS} | 1h_trend={REQUIRE_1H_TREND} | micro1m={MICRO_CONFIRM_1M}\n"
                      f"RT_TPSL={REALTIME_TPSL} choose={REALTIME_TPSL_CHOOSE} | BE={BE_ENABLE}\n"
                      f"Quotes={QUOTE_WHITELIST or ('USDC_ONLY' if USDC_ONLY else 'ALL')} | topN={PREFILTER_TOP_N}\n"
                      f"Cmd: /scan /top /stats /last_rejects /alerts_on /alerts_off /config /help /ping /mode"))
        except Exception:
            logger.exception("Welcome send failed")

    # Scheduler
    global SCHEDULER
    SCHEDULER = BackgroundScheduler(timezone="UTC")
    SCHEDULER.add_job(scheduled_scan, "interval", seconds=SCAN_SECONDS,
                      args=[updater, dp], id="scheduled_scan",
                      replace_existing=True, coalesce=True, max_instances=1)
    logger.info("Scheduler started (SCAN_SECONDS=%s)", SCAN_SECONDS)
    SCHEDULER.start()

    # Polling (les 502 seront loggés par PTB mais non bloquants)
    try:
        #updater.start_polling(drop_pending_updates=True, timeout=20, clean=True)
        updater.start_polling(drop_pending_updates=True, timeout=20)
    except NetworkError:
        pass
    logger.info("Bot started.")
    updater.idle()

if __name__=="__main__":
    main()
