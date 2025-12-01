# backend/agent_consciousness_v2.py
"""
Advanced Multi-Source Consciousness System for Crypto Trading Agent
Synthétise toutes les sources d'information en conscience contextuelle structurée

Architecture:
- MarketState: État du marché crypto (prix, volumes, tendances)
- SentimentState: Sentiment global (Fear & Greed, news, social)
- SignalState: Signaux de trading actifs (bot, indicateurs)
- UserContextState: Contexte utilisateur (profil, préférences, positions)
- OpportunityState: Opportunités détectées automatiquement
- RiskState: Risques identifiés
- MemorySummary: Résumé mémoire long-terme

Author: Claude Code + Human
Date: 2025-11-28
Version: 0.2.0
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger("agents_v3")


# ============================================================================
# ENUMS
# ============================================================================

class ConsciousnessLayer(str, Enum):
    """Couches de la conscience globale"""
    MARKET = "market"
    SENTIMENT = "sentiment"
    SIGNALS = "signals"
    USER = "user"
    OPPORTUNITIES = "opportunities"
    RISKS = "risks"
    MEMORY = "memory"


class TrendType(str, Enum):
    """Types de tendance marché"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    CONSOLIDATION = "consolidation"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Niveaux de risque"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# DATACLASSES - STATES
# ============================================================================

@dataclass
class MarketState:
    """État complet du marché crypto"""
    prices: Dict[str, float] = field(default_factory=dict)  # {"BTC": 95000, ...}
    changes_24h: Dict[str, float] = field(default_factory=dict)  # {"BTC": -3.0, ...}
    volumes_24h: Dict[str, float] = field(default_factory=dict)  # {"BTC": 28B, ...}
    market_caps: Dict[str, float] = field(default_factory=dict)  # {"BTC": 1.8T, ...}
    trends: Dict[str, str] = field(default_factory=dict)  # {"BTC": "consolidation", ...}

    # Global metrics
    total_market_cap: float = 0.0
    total_volume_24h: float = 0.0
    btc_dominance: float = 0.0

    # Derived metrics
    correlations: Dict[str, float] = field(default_factory=dict)  # {"BTC-ETH": 0.85, ...}
    support_levels: Dict[str, float] = field(default_factory=dict)
    resistance_levels: Dict[str, float] = field(default_factory=dict)

    timestamp: float = field(default_factory=time.time)

    def get_top_movers(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Retourne les top movers (plus fortes variations 24h)"""
        if not self.changes_24h:
            return []

        sorted_changes = sorted(
            self.changes_24h.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        return [
            {
                "symbol": symbol,
                "change_pct": change,
                "price": self.prices.get(symbol, 0),
                "direction": "up" if change > 0 else "down"
            }
            for symbol, change in sorted_changes[:limit]
        ]


@dataclass
class SentimentState:
    """Sentiment du marché crypto"""
    fear_greed_index: int = 50  # 0-100
    fear_greed_label: str = "Neutral"  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed

    # News sentiment
    news_sentiment: str = "neutral"  # bearish, neutral, bullish
    critical_events: List[Dict] = field(default_factory=list)  # Events majeurs récents

    # Social sentiment (future)
    social_sentiment: Optional[str] = None

    timestamp: float = field(default_factory=time.time)

    def get_overall_sentiment(self) -> str:
        """Retourne le sentiment global combiné"""
        if self.fear_greed_index < 25:
            return "extreme_fear"
        elif self.fear_greed_index < 45:
            return "fear"
        elif self.fear_greed_index < 55:
            return "neutral"
        elif self.fear_greed_index < 75:
            return "greed"
        else:
            return "extreme_greed"


@dataclass
class TradingSignal:
    """Un signal de trading individuel"""
    symbol: str
    type: str  # rsi_oversold, macd_cross, golden_cross, etc.
    side: str  # LONG, SHORT
    confidence: float  # 0-1
    price: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)  # RSI, ATR, etc.


@dataclass
class SignalState:
    """État des signaux de trading actifs"""
    signals: List[TradingSignal] = field(default_factory=list)
    signals_by_asset: Dict[str, List[TradingSignal]] = field(default_factory=dict)

    signal_count: int = 0
    bullish_signals: int = 0
    bearish_signals: int = 0
    neutral_signals: int = 0

    strongest_signal: Optional[TradingSignal] = None

    timestamp: float = field(default_factory=time.time)

    def add_signal(self, signal: TradingSignal):
        """Ajoute un signal et met à jour les compteurs"""
        self.signals.append(signal)

        # Group by asset
        if signal.symbol not in self.signals_by_asset:
            self.signals_by_asset[signal.symbol] = []
        self.signals_by_asset[signal.symbol].append(signal)

        # Update counts
        self.signal_count = len(self.signals)
        if signal.side == "LONG":
            self.bullish_signals += 1
        elif signal.side == "SHORT":
            self.bearish_signals += 1
        else:
            self.neutral_signals += 1

        # Update strongest
        if self.strongest_signal is None or signal.confidence > self.strongest_signal.confidence:
            self.strongest_signal = signal


@dataclass
class UserPosition:
    """Position utilisateur sur un asset"""
    asset: str
    amount: float
    entry_price: float
    current_price: float
    pnl_pct: float
    pnl_usd: float


@dataclass
class UserContextState:
    """Contexte utilisateur complet"""
    user_id: str = "default_user"

    # Profile
    risk_profile: str = "moderate"  # conservative, moderate, aggressive

    # Positions
    active_positions: List[UserPosition] = field(default_factory=list)
    total_portfolio_value: float = 0.0

    # Preferences
    preferences: Dict[str, Any] = field(default_factory=dict)
    favorite_assets: List[str] = field(default_factory=list)

    # Recent activity
    recent_interests: List[str] = field(default_factory=list)  # Topics discussed
    recent_questions: List[str] = field(default_factory=list)

    # Conversation context
    conversation_summary: str = ""
    last_interaction: float = 0.0

    timestamp: float = field(default_factory=time.time)


@dataclass
class Opportunity:
    """Une opportunité de trading détectée"""
    type: str  # dca_entry, swing_trade, arbitrage, etc.
    asset: str
    confidence: float  # 0-1
    reasoning: str
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OpportunityState:
    """Opportunités de trading détectées"""
    opportunities: List[Opportunity] = field(default_factory=list)
    top_opportunity: Optional[Opportunity] = None

    timestamp: float = field(default_factory=time.time)


@dataclass
class Risk:
    """Un risque identifié"""
    type: str  # macro_uncertainty, regulatory, technical, liquidity, etc.
    description: str
    severity: RiskLevel
    affected_assets: List[str] = field(default_factory=list)
    mitigation: Optional[str] = None


@dataclass
class RiskState:
    """État des risques identifiés"""
    active_risks: List[Risk] = field(default_factory=list)
    overall_severity: RiskLevel = RiskLevel.LOW

    timestamp: float = field(default_factory=time.time)


@dataclass
class MemorySummary:
    """Résumé de la mémoire long-terme"""
    user_patterns: str = ""  # Patterns comportement user
    successful_strategies: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    historical_performance: Dict[str, Any] = field(default_factory=dict)

    timestamp: float = field(default_factory=time.time)


# ============================================================================
# GLOBAL CONSCIOUSNESS
# ============================================================================

@dataclass
class GlobalConsciousness:
    """Conscience globale multi-couches du copilote crypto"""
    market: MarketState = field(default_factory=MarketState)
    sentiment: SentimentState = field(default_factory=SentimentState)
    signals: SignalState = field(default_factory=SignalState)
    user_context: UserContextState = field(default_factory=UserContextState)
    opportunities: OpportunityState = field(default_factory=OpportunityState)
    risks: RiskState = field(default_factory=RiskState)
    memory: MemorySummary = field(default_factory=MemorySummary)

    timestamp: float = field(default_factory=time.time)
    version: str = "0.2.0"

    def to_natural_language(self, max_length: int = 300) -> str:
        """
        Convertir la conscience en résumé langage naturel concis pour le LLM

        Format optimisé pour contexte LLM :
        - Market snapshot (prix + tendances)
        - Sentiment (Fear & Greed + news)
        - Signals (bullish/bearish count)
        - User context (positions)
        - Top opportunity si présente
        - Warnings si risques
        """
        parts = []

        # 1. Market snapshot (priorité aux majors)
        if self.market.prices:
            major_assets = ["BTC", "ETH", "SOL", "BNB"]
            market_parts = []
            for asset in major_assets:
                price = self.market.prices.get(asset)
                change = self.market.changes_24h.get(asset)
                if price:
                    change_str = f"{change:+.1f}%" if change else ""
                    market_parts.append(f"{asset}: ${price:,.0f} {change_str}")

            if market_parts:
                parts.append("📊 " + ", ".join(market_parts[:3]))

        # 2. Sentiment
        if self.sentiment.fear_greed_index:
            emoji = "😰" if self.sentiment.fear_greed_index < 40 else "😊" if self.sentiment.fear_greed_index > 60 else "😐"
            parts.append(f"{emoji} Sentiment: {self.sentiment.fear_greed_label} (FnG: {self.sentiment.fear_greed_index})")

        # 3. Signals
        if self.signals.signal_count > 0:
            parts.append(
                f"📡 Signals: {self.signals.bullish_signals}🟢 {self.signals.bearish_signals}🔴"
            )
            if self.signals.strongest_signal:
                sig = self.signals.strongest_signal
                parts.append(f"→ {sig.symbol} {sig.type} ({sig.confidence:.0%})")

        # 4. User positions
        if self.user_context.active_positions:
            pos_count = len(self.user_context.active_positions)
            total_val = self.user_context.total_portfolio_value
            parts.append(f"💼 {pos_count} positions (${total_val:,.0f})")

        # 5. Top opportunity
        if self.opportunities.top_opportunity:
            opp = self.opportunities.top_opportunity
            parts.append(f"💡 {opp.type}: {opp.asset} ({opp.confidence:.0%})")

        # 6. Risks
        if self.risks.overall_severity != RiskLevel.LOW:
            parts.append(f"⚠️ Risk: {self.risks.overall_severity.value}")

        # Joindre avec séparateurs
        result = " | ".join(parts)

        # Tronquer si trop long
        if len(result) > max_length:
            result = result[:max_length-3] + "..."

        return result if result else "Monitoring crypto markets..."

    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dict pour stockage/transmission"""
        return {
            "market": asdict(self.market),
            "sentiment": asdict(self.sentiment),
            "signals": {
                "signals": [asdict(s) for s in self.signals.signals],
                "signals_by_asset": {
                    k: [asdict(s) for s in v]
                    for k, v in self.signals.signals_by_asset.items()
                },
                "signal_count": self.signals.signal_count,
                "bullish_signals": self.signals.bullish_signals,
                "bearish_signals": self.signals.bearish_signals,
                "strongest_signal": asdict(self.signals.strongest_signal) if self.signals.strongest_signal else None,
                "timestamp": self.signals.timestamp
            },
            "user_context": asdict(self.user_context),
            "opportunities": {
                "opportunities": [asdict(o) for o in self.opportunities.opportunities],
                "top_opportunity": asdict(self.opportunities.top_opportunity) if self.opportunities.top_opportunity else None,
                "timestamp": self.opportunities.timestamp
            },
            "risks": {
                "active_risks": [asdict(r) for r in self.risks.active_risks],
                "overall_severity": self.risks.overall_severity.value,
                "timestamp": self.risks.timestamp
            },
            "memory": asdict(self.memory),
            "timestamp": self.timestamp,
            "version": self.version
        }

    def to_frontend_summary(self) -> Dict[str, Any]:
        """Format optimisé pour le frontend (JSON compact)"""
        return {
            "summary": self.to_natural_language(),
            "market": {
                "top_movers": self.market.get_top_movers(3),
                "total_cap": self.market.total_market_cap,
                "btc_dominance": self.market.btc_dominance
            },
            "sentiment": {
                "score": self.sentiment.fear_greed_index,
                "label": self.sentiment.fear_greed_label,
                "overall": self.sentiment.get_overall_sentiment()
            },
            "signals": {
                "count": self.signals.signal_count,
                "bullish": self.signals.bullish_signals,
                "bearish": self.signals.bearish_signals
            },
            "opportunities": len(self.opportunities.opportunities),
            "risks": self.risks.overall_severity.value,
            "timestamp": self.timestamp
        }


# ============================================================================
# CONSCIOUSNESS BUILDER
# ============================================================================

class ConsciousnessBuilder:
    """
    Constructeur de conscience globale à partir de multiples sources

    Sources intégrées :
    - Price collector (crypto prices)
    - News collector (crypto news)
    - Trading bot service (signals, Fear & Greed)
    - Wallet state (user positions)
    - Memory graph (user patterns)
    - RAG knowledge base
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30.0  # 30 secondes

    async def gather_market_data(self) -> MarketState:
        """Collecter données market depuis price_collector"""
        try:
            from .collectors.price_collector import fetch_crypto_prices

            # Async wrapper
            prices_data = await asyncio.to_thread(fetch_crypto_prices)

            if not prices_data:
                logger.warning("[ConsciousnessBuilder] No price data available")
                return MarketState()

            # Parse prices
            prices = {}
            changes_24h = {}
            volumes_24h = {}
            market_caps = {}

            for crypto_id, data in prices_data.items():
                if isinstance(data, dict):
                    # Map symbol (BTC, ETH, etc.)
                    symbol = self._normalize_symbol(crypto_id)
                    prices[symbol] = data.get('usd', 0)
                    changes_24h[symbol] = data.get('usd_24h_change', 0)
                    volumes_24h[symbol] = data.get('usd_24h_vol', 0)
                    market_caps[symbol] = data.get('usd_market_cap', 0)

            # Calculate total market cap and volume
            total_cap = sum(market_caps.values())
            total_vol = sum(volumes_24h.values())
            btc_dominance = (market_caps.get('BTC', 0) / total_cap * 100) if total_cap > 0 else 0

            # Detect trends (simple heuristic based on 24h change)
            trends = {}
            for symbol, change in changes_24h.items():
                if change > 5:
                    trends[symbol] = TrendType.BULLISH.value
                elif change < -5:
                    trends[symbol] = TrendType.BEARISH.value
                elif abs(change) < 2:
                    trends[symbol] = TrendType.SIDEWAYS.value
                else:
                    trends[symbol] = TrendType.CONSOLIDATION.value

            return MarketState(
                prices=prices,
                changes_24h=changes_24h,
                volumes_24h=volumes_24h,
                market_caps=market_caps,
                trends=trends,
                total_market_cap=total_cap,
                total_volume_24h=total_vol,
                btc_dominance=btc_dominance
            )

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error gathering market data: {e}", exc_info=True)
            return MarketState()

    async def gather_sentiment_data(self) -> SentimentState:
        """Collecter sentiment depuis bot service + news"""
        try:
            from .services.trading_bot_service import fetch_fear_greed_index

            # Fear & Greed Index
            fng_data = await asyncio.to_thread(fetch_fear_greed_index)
            fng_score = fng_data.get('score', 50)
            fng_label = fng_data.get('label', 'Neutral')

            # News sentiment (TODO: implement news sentiment analysis)
            news_sentiment = "neutral"
            critical_events = []

            # TODO: Query recent news from DB and analyze sentiment
            # from .db import crud
            # from .db.models import SessionLocal
            # db = SessionLocal()
            # recent_news = crud.get_recent_news_articles(db, limit=10)
            # news_sentiment = self._analyze_news_sentiment(recent_news)
            # critical_events = self._filter_critical_events(recent_news)
            # db.close()

            return SentimentState(
                fear_greed_index=fng_score,
                fear_greed_label=fng_label,
                news_sentiment=news_sentiment,
                critical_events=critical_events
            )

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error gathering sentiment: {e}", exc_info=True)
            return SentimentState()

    async def gather_signals(self) -> SignalState:
        """Collecter signaux du bot de trading"""
        try:
            from .services.trading_bot_service import get_trading_bot_service

            bot_service = get_trading_bot_service()
            if not bot_service:
                return SignalState()

            # Get signals from bot queue (in-memory, includes synthetic)
            # Priorité 1 : signals_queue (in-memory, includes synthetic signals)
            # Priorité 2 : get_signals() (from file, real bot scans)
            signals_data = []

            if hasattr(bot_service, 'signals_queue') and bot_service.signals_queue:
                # Use in-memory queue (includes synthetic)
                signals_data = bot_service.signals_queue[-20:]  # Last 20
                logger.debug(f"[ConsciousnessBuilder] Using {len(signals_data)} signals from in-memory queue")
            else:
                # Fallback to file-based signals
                signals_data = bot_service.get_signals(limit=20)
                logger.debug(f"[ConsciousnessBuilder] Using {len(signals_data)} signals from file")

            signal_state = SignalState()

            for sig_data in signals_data:
                # Normalize action/side: BUY -> LONG, SELL -> SHORT
                raw_side = sig_data.get('side', sig_data.get('action', 'NEUTRAL'))
                if raw_side == 'BUY':
                    normalized_side = 'LONG'
                elif raw_side == 'SELL':
                    normalized_side = 'SHORT'
                else:
                    normalized_side = raw_side

                signal = TradingSignal(
                    symbol=sig_data.get('ticker', sig_data.get('symbol', 'UNKNOWN')),
                    type=sig_data.get('event', 'unknown'),
                    side=normalized_side,
                    confidence=sig_data.get('confidence', 50) / 100.0,
                    price=sig_data.get('entry_price', sig_data.get('entry', 0)),
                    timestamp=time.time(),
                    metadata={
                        'rsi': sig_data.get('rsi'),
                        'atr_pct': sig_data.get('atr_pct'),
                        'entry': sig_data.get('entry'),
                        'tp': sig_data.get('tp'),
                        'sl': sig_data.get('sl')
                    }
                )
                signal_state.add_signal(signal)

            return signal_state

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error gathering signals: {e}", exc_info=True)
            return SignalState()

    async def gather_user_context(self, user_id: str = "default_user") -> UserContextState:
        """
        Collecter contexte utilisateur depuis Entity Graph + wallets

        Extracts:
        - User profile (risk_profile)
        - Active positions (OWNS relations)
        - Favorite assets (WATCHES relations)
        - Recent interests (recent decisions/patterns)
        """
        try:
            from .entity_memory import get_entity_graph

            entity_graph = get_entity_graph("fededge_core_v3")

            # Try to find or create user entity
            users = entity_graph.find_entities(type="user", filters={"user_id": user_id})

            if not users:
                # User not in graph yet, return basic context
                logger.debug(f"[ConsciousnessBuilder] User {user_id} not in Entity Graph, using defaults")
                return UserContextState(
                    user_id=user_id,
                    risk_profile="moderate",
                    active_positions=[],
                    total_portfolio_value=0.0,
                    preferences={},
                    favorite_assets=["BTC", "ETH", "SOL"],
                    recent_interests=[],
                    recent_questions=[],
                    conversation_summary="",
                    last_interaction=time.time()
                )

            user_entity = users[0]

            # 1. Get active positions (OWNS relations)
            positions_data = entity_graph.get_user_positions(user_entity.id)
            active_positions = []
            total_portfolio_value = 0.0

            for pos in positions_data:
                entry = pos.get('entry_price', 0)
                current = pos.get('current_price', 0)
                amount = pos.get('amount', 0)

                if current > 0 and entry > 0:
                    pnl_pct = ((current - entry) / entry) * 100
                    pnl_usd = amount * (current - entry)
                    total_portfolio_value += amount * current

                    active_positions.append(UserPosition(
                        asset=pos.get('symbol', pos.get('asset', 'UNKNOWN')),
                        amount=amount,
                        entry_price=entry,
                        current_price=current,
                        pnl_pct=pnl_pct,
                        pnl_usd=pnl_usd
                    ))

            # 2. Get favorite assets (WATCHES relations)
            watches_rels = entity_graph.get_relations(user_entity.id, "out", "WATCHES")
            favorite_assets = []
            for rel in watches_rels:
                asset = entity_graph.get_entity(rel.target)
                if asset:
                    favorite_assets.append(asset.attributes.get("symbol", asset.label))

            # If no favorites, use defaults
            if not favorite_assets:
                favorite_assets = ["BTC", "ETH", "SOL"]

            # 3. Get recent interests (recent decisions)
            recent_decisions = entity_graph.get_decision_history(user_entity.id, limit=5)
            recent_interests = []

            for dec in recent_decisions:
                asset = dec.get('asset')
                if asset and asset not in recent_interests:
                    recent_interests.append(asset)

            # 4. User attributes
            risk_profile = user_entity.attributes.get('risk_profile', 'moderate')
            preferences = user_entity.attributes.get('preferences', {})

            return UserContextState(
                user_id=user_id,
                risk_profile=risk_profile,
                active_positions=active_positions,
                total_portfolio_value=total_portfolio_value,
                preferences=preferences,
                favorite_assets=favorite_assets,
                recent_interests=recent_interests,
                recent_questions=[],  # TODO: Extract from conversation history
                conversation_summary="",  # TODO: Extract from recent context
                last_interaction=time.time()
            )

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error gathering user context: {e}", exc_info=True)
            return UserContextState()

    async def detect_opportunities(
        self,
        market: MarketState,
        signals: SignalState,
        user: UserContextState
    ) -> OpportunityState:
        """
        Détection d'opportunités basée sur confluence de signaux

        Logic:
        - Signal bullish + oversold → DCA entry
        - Multiple signals même asset → high confidence trade
        - User favorite asset + signal → personalized opportunity
        """
        try:
            opp_state = OpportunityState()

            # Group signals by asset
            for asset, asset_signals in signals.signals_by_asset.items():
                if len(asset_signals) < 1:
                    continue

                # Calculate average confidence
                avg_confidence = sum(s.confidence for s in asset_signals) / len(asset_signals)

                # Determine opportunity type
                bullish_count = sum(1 for s in asset_signals if s.side == "LONG")
                bearish_count = sum(1 for s in asset_signals if s.side == "SHORT")

                if bullish_count > bearish_count:
                    opp_type = "dca_entry" if avg_confidence > 0.7 else "swing_trade"
                    reasoning = f"{bullish_count} bullish signals detected"
                elif bearish_count > bullish_count:
                    opp_type = "short_opportunity"
                    reasoning = f"{bearish_count} bearish signals detected"
                else:
                    continue

                # Create opportunity
                strongest = max(asset_signals, key=lambda s: s.confidence)

                opportunity = Opportunity(
                    type=opp_type,
                    asset=asset,
                    confidence=avg_confidence,
                    reasoning=reasoning,
                    entry_price=strongest.price,
                    target_price=strongest.metadata.get('tp'),
                    stop_loss=strongest.metadata.get('sl'),
                    metadata={
                        "signal_count": len(asset_signals),
                        "bullish_count": bullish_count,
                        "bearish_count": bearish_count
                    }
                )

                opp_state.opportunities.append(opportunity)

            # Select top opportunity (highest confidence)
            if opp_state.opportunities:
                opp_state.top_opportunity = max(
                    opp_state.opportunities,
                    key=lambda o: o.confidence
                )

            return opp_state

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error detecting opportunities: {e}", exc_info=True)
            return OpportunityState()

    async def assess_risks(
        self,
        market: MarketState,
        sentiment: SentimentState,
        user: UserContextState
    ) -> RiskState:
        """Évaluation des risques basée sur market + sentiment"""
        try:
            risk_state = RiskState()

            # Risk 1: Extreme fear (peut être opportunité ou danger)
            if sentiment.fear_greed_index <= 25:
                risk_state.active_risks.append(Risk(
                    type="market_sentiment",
                    description=f"Extreme fear in market (FnG: {sentiment.fear_greed_index})",
                    severity=RiskLevel.MEDIUM,
                    affected_assets=list(market.prices.keys()),
                    mitigation="Consider DCA strategy during fear periods"
                ))

            # Risk 2: High volatility (top movers > 10%)
            top_movers = market.get_top_movers(5)
            high_vol_assets = [m['symbol'] for m in top_movers if abs(m['change_pct']) > 10]
            if high_vol_assets:
                risk_state.active_risks.append(Risk(
                    type="high_volatility",
                    description=f"High volatility detected on {len(high_vol_assets)} assets",
                    severity=RiskLevel.MEDIUM,
                    affected_assets=high_vol_assets,
                    mitigation="Use wider stop losses and reduce position sizes"
                ))

            # Risk 3: Critical news events
            if sentiment.critical_events:
                risk_state.active_risks.append(Risk(
                    type="critical_events",
                    description=f"{len(sentiment.critical_events)} critical events detected",
                    severity=RiskLevel.HIGH,
                    mitigation="Monitor news closely before trading"
                ))

            # Determine overall severity
            if any(r.severity == RiskLevel.CRITICAL for r in risk_state.active_risks):
                risk_state.overall_severity = RiskLevel.CRITICAL
            elif any(r.severity == RiskLevel.HIGH for r in risk_state.active_risks):
                risk_state.overall_severity = RiskLevel.HIGH
            elif any(r.severity == RiskLevel.MEDIUM for r in risk_state.active_risks):
                risk_state.overall_severity = RiskLevel.MEDIUM
            else:
                risk_state.overall_severity = RiskLevel.LOW

            return risk_state

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error assessing risks: {e}", exc_info=True)
            return RiskState()

    async def load_memory_summary(self, agent_id: str) -> MemorySummary:
        """
        Charger résumé mémoire depuis Entity Graph + DoT graph

        Extracts:
        - Recent patterns detected (last 7 days)
        - Successful strategies (win rate > 60%)
        - Lessons learned (failed trades analysis)
        - Historical performance stats
        """
        try:
            from .entity_memory import get_entity_graph

            entity_graph = get_entity_graph(agent_id)

            # 1. Recent patterns detected
            patterns = entity_graph.find_entities(
                type="pattern",
                filters={"created_at": {"$gte": time.time() - 86400 * 7}}  # Last 7 days
            )

            pattern_summary = []
            for p in sorted(patterns, key=lambda x: x.importance, reverse=True)[:5]:
                asset = p.attributes.get('asset', 'Unknown')
                ptype = p.attributes.get('pattern_type', 'unknown')
                conf = p.attributes.get('confidence', 0)
                pattern_summary.append(f"{ptype} on {asset} ({conf:.0%})")

            user_patterns = ", ".join(pattern_summary) if pattern_summary else "No recent patterns"

            # 2. Successful strategies (analyze pattern outcomes)
            successful_strategies = []
            pattern_types = {}  # pattern_type -> {wins, losses, total_pnl}

            for pattern in patterns:
                ptype = pattern.attributes.get('pattern_type', 'unknown')

                # Get outcomes
                resulted_rels = entity_graph.get_relations(pattern.id, "out", "RESULTED_IN")
                for rel in resulted_rels:
                    outcome = entity_graph.get_entity(rel.target)
                    if outcome:
                        pnl = outcome.attributes.get('pnl_pct', 0)

                        if ptype not in pattern_types:
                            pattern_types[ptype] = {"wins": 0, "losses": 0, "total_pnl": 0, "count": 0}

                        pattern_types[ptype]["count"] += 1
                        pattern_types[ptype]["total_pnl"] += pnl

                        if pnl > 0:
                            pattern_types[ptype]["wins"] += 1
                        else:
                            pattern_types[ptype]["losses"] += 1

            # Filter successful (win rate > 60%)
            for ptype, stats in pattern_types.items():
                if stats["count"] > 0:
                    win_rate = stats["wins"] / stats["count"]
                    avg_pnl = stats["total_pnl"] / stats["count"]

                    if win_rate > 0.6:
                        successful_strategies.append(
                            f"{ptype}: {win_rate:.0%} win rate, avg {avg_pnl:+.1f}%"
                        )

            # 3. Lessons learned (failed patterns)
            lessons_learned = []
            for ptype, stats in pattern_types.items():
                if stats["count"] > 0:
                    win_rate = stats["wins"] / stats["count"]
                    if win_rate < 0.4:  # Losing strategy
                        lessons_learned.append(
                            f"Avoid {ptype} (only {win_rate:.0%} success)"
                        )

            # 4. Historical performance
            historical_performance = {
                "total_patterns": len(patterns),
                "pattern_types": len(pattern_types),
                "strategies_analyzed": len(pattern_types),
                "successful_strategies": len(successful_strategies),
            }

            return MemorySummary(
                user_patterns=user_patterns,
                successful_strategies=successful_strategies[:3],  # Top 3
                lessons_learned=lessons_learned[:3],  # Top 3
                historical_performance=historical_performance
            )

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Error loading memory: {e}", exc_info=True)
            return MemorySummary()

    async def build(self, user_id: str = "default_user", agent_id: str = "fededge_core_v3") -> GlobalConsciousness:
        """
        Construire la conscience globale complète

        Process:
        1. Gather toutes les sources en parallèle (market, sentiment, signals, user)
        2. Analyses dérivées (opportunities, risks) basées sur les données gathérées
        3. Load memory summary
        4. Assembler GlobalConsciousness

        Returns:
            GlobalConsciousness object avec toutes les couches remplies
        """
        logger.info(f"[ConsciousnessBuilder] Building global consciousness for user={user_id}, agent={agent_id}")

        start_time = time.time()

        try:
            # Phase 1: Gather sources en parallèle
            market_task = self.gather_market_data()
            sentiment_task = self.gather_sentiment_data()
            signals_task = self.gather_signals()
            user_task = self.gather_user_context(user_id)
            memory_task = self.load_memory_summary(agent_id)

            market, sentiment, signals, user, memory = await asyncio.gather(
                market_task,
                sentiment_task,
                signals_task,
                user_task,
                memory_task,
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(market, Exception):
                logger.error(f"Market gather failed: {market}")
                market = MarketState()
            if isinstance(sentiment, Exception):
                logger.error(f"Sentiment gather failed: {sentiment}")
                sentiment = SentimentState()
            if isinstance(signals, Exception):
                logger.error(f"Signals gather failed: {signals}")
                signals = SignalState()
            if isinstance(user, Exception):
                logger.error(f"User context gather failed: {user}")
                user = UserContextState()
            if isinstance(memory, Exception):
                logger.error(f"Memory gather failed: {memory}")
                memory = MemorySummary()

            # Phase 2: Analyses dérivées
            opportunities = await self.detect_opportunities(market, signals, user)
            risks = await self.assess_risks(market, sentiment, user)

            # Phase 3: Assembler consciousness
            consciousness = GlobalConsciousness(
                market=market,
                sentiment=sentiment,
                signals=signals,
                user_context=user,
                opportunities=opportunities,
                risks=risks,
                memory=memory,
                timestamp=time.time()
            )

            elapsed = time.time() - start_time
            logger.info(
                f"[ConsciousnessBuilder] Built in {elapsed:.2f}s - "
                f"{len(market.prices)} assets, {signals.signal_count} signals, "
                f"{len(opportunities.opportunities)} opportunities"
            )

            return consciousness

        except Exception as e:
            logger.error(f"[ConsciousnessBuilder] Fatal error building consciousness: {e}", exc_info=True)
            # Return minimal consciousness
            return GlobalConsciousness()

    def _normalize_symbol(self, crypto_id: str) -> str:
        """Normalize crypto ID to symbol (bitcoin → BTC)"""
        symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "binancecoin": "BNB",
            "cardano": "ADA",
            "ripple": "XRP",
            "polkadot": "DOT",
            "dogecoin": "DOGE",
            "avalanche-2": "AVAX",
            "chainlink": "LINK"
        }
        return symbol_map.get(crypto_id.lower(), crypto_id.upper()[:6])


# ============================================================================
# SINGLETON
# ============================================================================

_consciousness_builder_instance: Optional[ConsciousnessBuilder] = None


def get_consciousness_builder() -> ConsciousnessBuilder:
    """Get or create the consciousness builder singleton"""
    global _consciousness_builder_instance
    if _consciousness_builder_instance is None:
        _consciousness_builder_instance = ConsciousnessBuilder()
        logger.info("[ConsciousnessBuilder] Singleton initialized")
    return _consciousness_builder_instance
