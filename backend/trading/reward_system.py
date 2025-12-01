"""
Système de reward basé sur les P&L réels pour l'entraînement et l'évaluation des agents IA.
Utilise les vraies performances du portefeuille pour améliorer les décisions futures.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import json

from .pnl_calculator import pnl_calculator, AssetPerformance, WalletPerformance
from .exchange_fees import get_realistic_trading_fees

logger = logging.getLogger(__name__)

@dataclass
class TradeReward:
    """Reward pour une décision de trading individuelle"""
    trade_id: int
    asset_symbol: str
    action: str  # BUY, SELL, HOLD
    
    # Métriques de performance
    pnl_impact: float  # Impact sur le P&L du portefeuille
    fee_efficiency: float  # Ratio P&L vs frais payés
    timing_score: float  # Score du timing (basé sur évolution prix post-trade)
    
    # Scores composites
    base_reward: float  # Reward de base (-1 à +1)
    risk_adjusted_reward: float  # Ajusté par le risque
    final_reward: float  # Score final après tous ajustements
    
    # Méta-données
    confidence_used: float  # Confiance de l'agent lors de la décision
    trade_amount_usd: float
    fees_paid: float
    timestamp: datetime

@dataclass
class AgentPerformance:
    """Performance globale d'un agent sur une période"""
    agent_name: str
    period_start: datetime
    period_end: datetime
    
    # Statistiques de trading
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Performance financière
    total_pnl: Decimal
    total_fees: Decimal
    net_profit: Decimal
    roi_percent: float
    
    # Métriques de reward
    average_reward: float
    best_trade_reward: float
    worst_trade_reward: float
    reward_volatility: float
    
    # Score composite final
    performance_score: float  # 0-100

class RewardCalculator:
    """Calculateur de rewards pour les décisions de trading"""
    
    def __init__(self):
        # Paramètres de scoring
        self.base_pnl_weight = 0.4      # Poids du P&L brut
        self.fee_efficiency_weight = 0.2 # Poids de l'efficacité des frais
        self.timing_weight = 0.2         # Poids du timing
        self.risk_weight = 0.2           # Poids de l'ajustement risque
        
        # Seuils de performance
        self.excellent_pnl_threshold = 0.05    # +5% = excellent
        self.good_pnl_threshold = 0.02         # +2% = bon
        self.poor_pnl_threshold = -0.02        # -2% = mauvais
        self.terrible_pnl_threshold = -0.05    # -5% = terrible
        
    async def calculate_trade_reward(self, 
                                   db,
                                   trade_transaction,
                                   wallet_before: WalletPerformance,
                                   wallet_after: WalletPerformance,
                                   agent_confidence: float = 0.5) -> TradeReward:
        """
        Calcule le reward pour une décision de trade spécifique.
        
        Args:
            trade_transaction: Transaction de la DB
            wallet_before: État du portefeuille avant le trade
            wallet_after: État du portefeuille après le trade
            agent_confidence: Confiance exprimée par l'agent (0-1)
        """
        
        # 1. Calcul de l'impact P&L
        pnl_delta = float(wallet_after.net_pnl - wallet_before.net_pnl)
        trade_amount = float(trade_transaction.amount * trade_transaction.price_at_time)
        pnl_percent = pnl_delta / trade_amount if trade_amount > 0 else 0
        
        # Score P&L basé sur les seuils
        if pnl_percent >= self.excellent_pnl_threshold:
            pnl_score = 1.0
        elif pnl_percent >= self.good_pnl_threshold:
            pnl_score = 0.5
        elif pnl_percent >= self.poor_pnl_threshold:
            pnl_score = 0.0
        elif pnl_percent >= self.terrible_pnl_threshold:
            pnl_score = -0.5
        else:
            pnl_score = -1.0
        
        # 2. Efficacité des frais
        fees_paid = float(trade_transaction.fees or 0)
        fee_ratio = fees_paid / trade_amount if trade_amount > 0 else 0
        
        # Frais efficaces si le P&L couvre largement les frais
        if pnl_delta > fees_paid * 3:  # P&L > 3x frais = très efficace
            fee_efficiency = 1.0
        elif pnl_delta > fees_paid:    # P&L > frais = efficace
            fee_efficiency = 0.5
        elif pnl_delta > 0:           # P&L positif mais < frais
            fee_efficiency = 0.0
        else:                         # P&L négatif + frais = très inefficace
            fee_efficiency = -1.0
        
        # 3. Score de timing (simplifié - basé sur le changement de prix récent)
        timing_score = 0.0  # TODO: Implémenter avec historique des prix
        
        # 4. Calcul du reward de base
        base_reward = (
            pnl_score * self.base_pnl_weight +
            fee_efficiency * self.fee_efficiency_weight +
            timing_score * self.timing_weight
        )
        
        # 5. Ajustement par le risque et la confiance
        # Pénaliser les trades trop confiants qui échouent
        confidence_penalty = 0.0
        if base_reward < 0 and agent_confidence > 0.8:
            confidence_penalty = -0.2  # Pénalité pour over-confidence
        elif base_reward > 0 and agent_confidence < 0.3:
            confidence_penalty = -0.1  # Légère pénalité pour sous-confiance sur bon trade
        
        risk_adjusted_reward = base_reward + confidence_penalty
        
        # 6. Score final (clamped entre -1 et +1)
        final_reward = max(-1.0, min(1.0, risk_adjusted_reward))
        
        return TradeReward(
            trade_id=trade_transaction.id,
            asset_symbol=trade_transaction.asset.symbol if hasattr(trade_transaction, 'asset') else 'UNKNOWN',
            action=trade_transaction.type.value,
            pnl_impact=pnl_delta,
            fee_efficiency=fee_efficiency,
            timing_score=timing_score,
            base_reward=base_reward,
            risk_adjusted_reward=risk_adjusted_reward,
            final_reward=final_reward,
            confidence_used=agent_confidence,
            trade_amount_usd=trade_amount,
            fees_paid=fees_paid,
            timestamp=trade_transaction.timestamp
        )
    
    async def calculate_agent_performance(self, 
                                        db, 
                                        agent_name: str,
                                        wallet_id: int,
                                        period_days: int = 30) -> AgentPerformance:
        """
        Calcule la performance globale d'un agent sur une période.
        """
        
        from ..db import crud
        from datetime import datetime, timedelta
        
        period_start = datetime.now() - timedelta(days=period_days)
        period_end = datetime.now()
        
        # Récupérer toutes les transactions de la période
        transactions = crud.get_wallet_transactions(db, wallet_id)
        period_transactions = [
            t for t in transactions 
            if t.timestamp >= period_start and t.timestamp <= period_end
        ]
        
        if not period_transactions:
            return AgentPerformance(
                agent_name=agent_name,
                period_start=period_start,
                period_end=period_end,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=Decimal('0'),
                total_fees=Decimal('0'),
                net_profit=Decimal('0'),
                roi_percent=0.0,
                average_reward=0.0,
                best_trade_reward=0.0,
                worst_trade_reward=0.0,
                reward_volatility=0.0,
                performance_score=50.0  # Score neutre
            )
        
        # Calculer les métriques de base
        total_trades = len(period_transactions)
        total_pnl = sum(self._calculate_trade_pnl(t) for t in period_transactions)
        total_fees = sum(t.fees for t in period_transactions if t.fees)
        net_profit = total_pnl - total_fees
        
        # Calculer win rate (approximation basée sur le P&L individuel)
        winning_trades = len([t for t in period_transactions if self._calculate_trade_pnl(t) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Performance wallet sur la période
        current_wallet = await pnl_calculator.calculate_wallet_performance(db, wallet_id)
        roi_percent = float(current_wallet.unrealized_pnl_percent) if current_wallet else 0.0
        
        # Score de performance composite (0-100)
        performance_score = self._calculate_performance_score(
            win_rate=win_rate,
            roi_percent=roi_percent,
            fee_efficiency=float(total_pnl / total_fees) if total_fees > 0 else 1.0,
            total_trades=total_trades
        )
        
        return AgentPerformance(
            agent_name=agent_name,
            period_start=period_start,
            period_end=period_end,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_fees=total_fees,
            net_profit=net_profit,
            roi_percent=roi_percent,
            average_reward=0.0,  # TODO: Calculer à partir des rewards stockés
            best_trade_reward=0.0,
            worst_trade_reward=0.0,
            reward_volatility=0.0,
            performance_score=performance_score
        )
    
    def _calculate_trade_pnl(self, transaction) -> Decimal:
        """Calcul simplifié du P&L d'une transaction"""
        # Approximation basée sur le type de transaction
        if transaction.type.value == 'BUY':
            # Pour un achat, le P&L dépend de l'évolution du prix après
            # Ici on simplifie en retournant 0 (neutre)
            return Decimal('0')
        elif transaction.type.value == 'SELL':
            # Pour une vente, on assume un P&L basé sur la différence de prix
            # Simplification: random entre -5% et +10%
            amount = transaction.amount * transaction.price_at_time
            return amount * Decimal('0.02')  # Assume 2% de gain moyen
        return Decimal('0')
    
    def _calculate_performance_score(self, win_rate: float, roi_percent: float, 
                                   fee_efficiency: float, total_trades: int) -> float:
        """Calcule un score de performance composite (0-100)"""
        
        # Score basé sur le win rate (0-30 points)
        win_score = min(30, win_rate * 30)
        
        # Score basé sur le ROI (0-40 points)
        roi_score = max(0, min(40, (roi_percent + 10) * 2))  # -10% = 0, +10% = 40
        
        # Score basé sur l'efficacité des frais (0-20 points)
        fee_score = max(0, min(20, fee_efficiency * 10))
        
        # Score basé sur l'activité (0-10 points)
        activity_score = min(10, total_trades / 10)  # 10 trades = score max
        
        total_score = win_score + roi_score + fee_score + activity_score
        return min(100, max(0, total_score))
    
    def get_reward_feedback_for_llm(self, reward: TradeReward) -> str:
        """Génère un feedback formaté pour améliorer les futurs prompts"""
        
        if reward.final_reward >= 0.5:
            feedback_type = "🎉 EXCELLENT TRADE"
        elif reward.final_reward >= 0:
            feedback_type = "✅ BON TRADE"
        elif reward.final_reward >= -0.5:
            feedback_type = "⚠️ TRADE MÉDIOCRE"
        else:
            feedback_type = "❌ MAUVAIS TRADE"
        
        feedback = f"""{feedback_type}
Asset: {reward.asset_symbol} ({reward.action})
Montant: ${reward.trade_amount_usd:,.2f}

📊 Performance:
• P&L Impact: ${reward.pnl_impact:+.2f}
• Frais payés: ${reward.fees_paid:.2f}
• Efficacité frais: {reward.fee_efficiency:+.1f}
• Score final: {reward.final_reward:+.2f}/1.0

💡 Leçons apprises:
"""
        
        if reward.final_reward < 0:
            if reward.fee_efficiency < 0:
                feedback += "• Les frais ont mangé le profit - considérer des montants plus importants\n"
            if reward.confidence_used > 0.8 and reward.final_reward < -0.3:
                feedback += "• Éviter la sur-confiance sur des signaux incertains\n"
            feedback += "• Améliorer l'analyse ou attendre de meilleurs signaux\n"
        else:
            feedback += "• Continuer avec ce type d'analyse\n"
            if reward.fee_efficiency > 0.5:
                feedback += "• Excellent ratio P&L/frais - répliquer cette approche\n"
        
        return feedback

# Instance globale
reward_calculator = RewardCalculator()