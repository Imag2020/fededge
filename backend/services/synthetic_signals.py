# backend/services/synthetic_signals.py
"""
Synthetic Trading Signals Generator
Génère des signaux de trading réalistes pour tester la conscience de l'agent

Utilisé pour:
- Tests de la Phase 1 (conscience multi-sources)
- Validation de l'intégration signaux → consciousness
- Démos sans attendre des vrais golden cross

Author: Claude Code
Date: 2025-11-28
Version: 0.2.0
"""

import random
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
    "DOGEUSDT", "XRPUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT"
]

SIGNAL_TYPES = [
    "rsi_oversold",      # RSI < 30
    "rsi_overbought",    # RSI > 70
    "macd_bullish_cross",  # MACD crosses above signal
    "macd_bearish_cross",  # MACD crosses below signal
    "golden_cross",      # SMA20 > SMA200
    "death_cross",       # SMA20 < SMA200
    "bollinger_squeeze", # Price touches lower band
    "volume_breakout",   # Volume 2x average
    "support_bounce",    # Price bounces from support
    "resistance_break"   # Price breaks resistance
]

# Prix approximatifs réalistes (Nov 2025)
BASE_PRICES = {
    "BTCUSDT": 95000,
    "ETHUSDT": 3500,
    "SOLUSDT": 220,
    "BNBUSDT": 620,
    "ADAUSDT": 1.05,
    "DOGEUSDT": 0.38,
    "XRPUSDT": 1.15,
    "DOTUSDT": 7.50,
    "AVAXUSDT": 42.00,
    "LINKUSDT": 15.20
}


# ============================================================================
# GENERATORS
# ============================================================================

def generate_synthetic_signal(
    symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    force_side: Optional[str] = None
) -> Dict[str, Any]:
    """
    Génère un signal de trading synthétique réaliste

    Args:
        symbol: Symbol forcé (si None, random)
        signal_type: Type de signal forcé (si None, random)
        force_side: Forcer le côté LONG/SHORT

    Returns:
        Dict avec format compatible trading_bot_service
    """
    # Sélection aléatoire si non spécifié
    symbol = symbol or random.choice(CRYPTO_SYMBOLS)
    signal_type = signal_type or random.choice(SIGNAL_TYPES)

    # Déterminer le side basé sur le type de signal
    if force_side:
        side = force_side
    elif signal_type in ["rsi_oversold", "macd_bullish_cross", "golden_cross",
                          "bollinger_squeeze", "support_bounce"]:
        side = "LONG"
    elif signal_type in ["rsi_overbought", "macd_bearish_cross", "death_cross",
                          "resistance_break"]:
        side = "SHORT"
    else:
        side = random.choice(["LONG", "SHORT"])

    # Prix base avec variation réaliste ±2%
    base_price = BASE_PRICES.get(symbol, 100)
    price = base_price * random.uniform(0.98, 1.02)

    # Calcul TP/SL selon side et type de signal
    if side == "LONG":
        # TP: +1.5% to +3%
        tp = price * random.uniform(1.015, 1.03)
        # SL: -0.8% to -1.5%
        sl = price * random.uniform(0.985, 0.992)
    else:  # SHORT
        # TP: -1.5% to -3%
        tp = price * random.uniform(0.97, 0.985)
        # SL: +0.8% to +1.5%
        sl = price * random.uniform(1.008, 1.015)

    # RSI réaliste selon type de signal
    if signal_type == "rsi_oversold":
        rsi = random.uniform(20, 30)
    elif signal_type == "rsi_overbought":
        rsi = random.uniform(70, 80)
    else:
        rsi = random.uniform(35, 65)

    # ATR % (volatilité)
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        atr_pct = random.uniform(1.0, 3.0)  # Majors moins volatiles
    else:
        atr_pct = random.uniform(2.0, 6.0)  # Altcoins plus volatiles

    # Confidence basée sur RSI et type de signal
    base_confidence = {
        "rsi_oversold": 75,
        "rsi_overbought": 70,
        "golden_cross": 85,
        "death_cross": 80,
        "macd_bullish_cross": 72,
        "bollinger_squeeze": 68,
        "volume_breakout": 65,
        "support_bounce": 70,
        "resistance_break": 72
    }.get(signal_type, 60)

    confidence = min(95, max(50, base_confidence + random.uniform(-10, 10)))

    # Score (0-1)
    score = confidence / 100.0

    # Timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    scan_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Format compatible avec trading_bot_service.get_signals()
    return {
        "id": f"SYN_{scan_id}_{symbol}_{signal_type}",
        "scan_id": scan_id,
        "symbol": symbol,
        "ticker": symbol.replace("USDT", ""),  # Frontend format
        "side": side,
        "action": "BUY" if side == "LONG" else "SELL",  # Frontend format
        "last_price": round(price, 2 if price < 100 else 0),
        "entry": round(price, 2 if price < 100 else 0),
        "entry_price": round(price, 2 if price < 100 else 0),  # Frontend format
        "tp": round(tp, 2 if tp < 100 else 0),
        "target_price": round(tp, 2 if tp < 100 else 0),  # Frontend format
        "sl": round(sl, 2 if sl < 100 else 0),
        "stop_loss": round(sl, 2 if sl < 100 else 0),  # Frontend format
        "rsi": round(rsi, 1),
        "atr_pct": round(atr_pct, 2),
        "delta_sma_bps": round(random.uniform(-50, 50), 1),
        "slope_bps": round(random.uniform(-10, 10), 1),
        "event": signal_type,
        "score": round(score, 3),
        "confidence": round(confidence, 0),
        "timestamp": timestamp,
        "status": "DETECTED",
        "synthetic": True,  # Marqueur important
        "reasoning": _generate_reasoning(signal_type, rsi, atr_pct, side)
    }


def generate_signal_batch(
    count: int = 3,
    scenario: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Génère un batch de signaux selon un scénario

    Args:
        count: Nombre de signaux à générer
        scenario: Scénario prédéfini (bullish, bearish, mixed, extreme_fear)

    Returns:
        Liste de signaux
    """
    signals = []

    if scenario == "bullish":
        # Majorité de signaux bullish
        signal_types = ["rsi_oversold", "golden_cross", "macd_bullish_cross", "support_bounce"]
        for _ in range(count):
            sig_type = random.choice(signal_types)
            signals.append(generate_synthetic_signal(signal_type=sig_type, force_side="LONG"))

    elif scenario == "bearish":
        # Majorité de signaux bearish
        signal_types = ["rsi_overbought", "death_cross", "macd_bearish_cross", "resistance_break"]
        for _ in range(count):
            sig_type = random.choice(signal_types)
            signals.append(generate_synthetic_signal(signal_type=sig_type, force_side="SHORT"))

    elif scenario == "extreme_fear":
        # Mix de oversold + high volatility
        for _ in range(count):
            signals.append(generate_synthetic_signal(
                symbol=random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
                signal_type="rsi_oversold",
                force_side="LONG"
            ))

    elif scenario == "mixed":
        # Mix équilibré
        for _ in range(count):
            signals.append(generate_synthetic_signal())

    else:
        # Random (par défaut)
        for _ in range(count):
            signals.append(generate_synthetic_signal())

    logger.info(f"[SyntheticSignals] Generated {len(signals)} signals (scenario={scenario})")

    return signals


def generate_continuous_signals(
    duration_minutes: int = 60,
    signals_per_batch: int = 2,
    batch_interval_seconds: int = 120
) -> List[Dict[str, Any]]:
    """
    Génère des signaux étalés sur une période (pour simulation)

    Args:
        duration_minutes: Durée totale en minutes
        signals_per_batch: Signaux par batch
        batch_interval_seconds: Intervalle entre batches

    Returns:
        Liste de tous les signaux générés avec timestamps étalés
    """
    all_signals = []
    batches = (duration_minutes * 60) // batch_interval_seconds

    base_time = datetime.now(timezone.utc)

    for i in range(batches):
        # Timestamp pour ce batch
        batch_time = base_time - timedelta(seconds=i * batch_interval_seconds)

        batch_signals = generate_signal_batch(signals_per_batch)

        # Ajuster les timestamps
        for signal in batch_signals:
            signal['timestamp'] = batch_time.isoformat()
            signal['scan_id'] = batch_time.strftime("%Y%m%d-%H%M%S")

        all_signals.extend(batch_signals)

    logger.info(f"[SyntheticSignals] Generated {len(all_signals)} continuous signals over {duration_minutes}min")

    return all_signals


def _generate_reasoning(signal_type: str, rsi: float, atr_pct: float, side: str) -> str:
    """Génère un reasoning textuel pour le signal"""
    reasons = {
        "rsi_oversold": f"RSI oversold at {rsi:.1f}, potential bounce opportunity",
        "rsi_overbought": f"RSI overbought at {rsi:.1f}, possible correction ahead",
        "golden_cross": f"Golden Cross detected: SMA20 crossed above SMA200 (bullish)",
        "death_cross": f"Death Cross detected: SMA20 crossed below SMA200 (bearish)",
        "macd_bullish_cross": f"MACD bullish crossover, upward momentum building",
        "macd_bearish_cross": f"MACD bearish crossover, downward pressure increasing",
        "bollinger_squeeze": f"Price touching lower Bollinger Band (RSI: {rsi:.1f})",
        "volume_breakout": f"Volume spike detected (2x average), potential breakout",
        "support_bounce": f"Price bouncing from support level, RSI: {rsi:.1f}",
        "resistance_break": f"Price breaking resistance with volume confirmation"
    }

    base_reason = reasons.get(signal_type, f"{signal_type} signal detected")

    # Ajouter contexte volatilité
    if atr_pct > 4.0:
        vol_note = f" | High volatility (ATR: {atr_pct:.1f}%), wider stops recommended"
    else:
        vol_note = f" | Normal volatility (ATR: {atr_pct:.1f}%)"

    return base_reason + vol_note


# ============================================================================
# TEST/DEMO SCENARIOS
# ============================================================================

def get_demo_scenario(name: str) -> List[Dict[str, Any]]:
    """
    Retourne un scénario de démo prédéfini

    Scenarios:
    - market_crash: Extreme fear, oversold partout
    - bull_run: Golden crosses, bullish momentum
    - sideways: Pas de signaux clairs
    - high_volatility: Beaucoup de signaux contradictoires
    """
    scenarios = {
        "market_crash": lambda: generate_signal_batch(5, "extreme_fear"),
        "bull_run": lambda: generate_signal_batch(5, "bullish"),
        "sideways": lambda: [],  # Pas de signaux
        "high_volatility": lambda: generate_signal_batch(8, "mixed")
    }

    scenario_func = scenarios.get(name)
    if not scenario_func:
        logger.warning(f"[SyntheticSignals] Unknown scenario '{name}', using default")
        return generate_signal_batch(3)

    return scenario_func()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def inject_signals_to_bot_service(signals: List[Dict[str, Any]]):
    """Injecte des signaux dans la queue du trading bot service"""
    try:
        from backend.services.trading_bot_service import get_trading_bot_service

        bot_service = get_trading_bot_service()
        if not bot_service:
            logger.error("[SyntheticSignals] Bot service not available")
            return False

        bot_service.signals_queue.extend(signals)

        # Trim si dépasse max
        if len(bot_service.signals_queue) > bot_service.max_signals:
            bot_service.signals_queue = bot_service.signals_queue[-bot_service.max_signals:]

        logger.info(f"[SyntheticSignals] Injected {len(signals)} signals into bot service queue")
        return True

    except Exception as e:
        logger.error(f"[SyntheticSignals] Error injecting signals: {e}")
        return False
