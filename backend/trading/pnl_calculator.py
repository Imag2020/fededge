"""
Calculateur de P&L (Profit & Loss) réaliste pour les simulations de trading.
Prend en compte les prix actuels du marché, les frais, et fournit des métriques détaillées.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from ..collectors.price_collector import fetch_crypto_prices
from ..db import models, crud
from .exchange_fees import get_realistic_trading_fees

logger = logging.getLogger(__name__)

@dataclass
class AssetPerformance:
    """Performance d'un asset individuel"""
    asset_id: str
    symbol: str
    name: str
    quantity: Decimal
    average_buy_price: Decimal
    current_price: Decimal
    
    # Valeurs calculées
    total_cost: Decimal  # Prix d'achat total (avec frais)
    current_value: Decimal  # Valeur actuelle
    unrealized_pnl: Decimal  # P&L non réalisé
    unrealized_pnl_percent: float  # P&L en pourcentage
    
    # Métriques de trading
    total_trades: int
    total_fees_paid: Decimal
    
    # Performance temporelle
    daily_change: float = 0.0
    weekly_change: float = 0.0
    monthly_change: float = 0.0

@dataclass
class WalletPerformance:
    """Performance globale du portefeuille"""
    wallet_id: int
    wallet_name: str
    
    # Valeurs totales
    total_invested: Decimal  # Montant total investi
    current_value: Decimal  # Valeur actuelle des holdings
    total_fees_paid: Decimal  # Tous les frais payés
    
    # Budget et liquidités
    initial_budget: Decimal  # Budget initial défini par l'utilisateur
    available_cash: Decimal  # Liquide disponible (budget - investi)
    total_wallet_value: Decimal  # Valeur totale (holdings + cash)
    
    # P&L global
    unrealized_pnl: Decimal  # P&L non réalisé total
    unrealized_pnl_percent: float  # P&L en pourcentage
    realized_pnl: Decimal  # P&L réalisé (ventes)
    net_pnl: Decimal  # P&L net (réalisé + non réalisé - frais)
    
    # Métriques de performance
    best_performer: Optional[AssetPerformance] = None
    worst_performer: Optional[AssetPerformance] = None
    
    # Diversification
    asset_count: int = 0
    concentration_ratio: float = 0.0  # % du plus gros holding
    
    # Performance temporelle
    daily_pnl: Decimal = Decimal('0')
    weekly_pnl: Decimal = Decimal('0')
    monthly_pnl: Decimal = Decimal('0')
    
    # Historique
    assets: List[AssetPerformance] = None

class PnLCalculator:
    """Calculateur de P&L avec prix de marché en temps réel"""
    
    def __init__(self):
        self.price_cache = {}
        self.cache_timestamp = None
        self.cache_duration = timedelta(minutes=1)  # Cache 1 minute
    
    async def get_current_prices(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """Récupère les prix actuels avec cache et fallback"""
        now = datetime.now()
        
        if (force_refresh or 
            not self.price_cache or 
            not self.cache_timestamp or 
            (now - self.cache_timestamp) > self.cache_duration):
            
            logger.info("🔄 Récupération des prix actuels...")
            try:
                self.price_cache = fetch_crypto_prices()
                if self.price_cache:
                    self.cache_timestamp = now
                    logger.info(f"✅ Prix récupérés pour {len(self.price_cache)} actifs")
                else:
                    raise Exception("API returned empty data")
            except Exception as e:
                logger.warning(f"⚠️ Erreur API CoinGecko ({e}), utilisation de prix simulés")
                # Fallback: utiliser des prix simulés basés sur des données récentes connues
                self.price_cache = self._get_fallback_prices()
                self.cache_timestamp = now
            
        return self.price_cache
    
    def _get_fallback_prices(self) -> Dict[str, Dict]:
        """Prix de fallback simulés quand l'API est indisponible"""
        import random
        
        # Prix de base approximatifs (mise à jour manuelle selon le marché réel)
        base_prices = {
            'bitcoin': {'usd': 114500.0, 'usd_24h_change': random.uniform(-3, 3)},
            'ethereum': {'usd': 3420.0, 'usd_24h_change': random.uniform(-4, 4)},
            'solana': {'usd': 185.0, 'usd_24h_change': random.uniform(-5, 5)},
            'bittensor': {'usd': 350.0, 'usd_24h_change': random.uniform(-8, 8)},  # TAO
            'fetch-ai': {'usd': 1.35, 'usd_24h_change': random.uniform(-6, 6)},
            'cardano': {'usd': 0.42, 'usd_24h_change': random.uniform(-3, 3)},
            'polkadot': {'usd': 7.2, 'usd_24h_change': random.uniform(-4, 4)},
            'chainlink': {'usd': 14.8, 'usd_24h_change': random.uniform(-4, 4)}
        }
        
        # Ajouter un peu de volatilité réaliste (±2% par rapport aux prix de base)
        fallback_prices = {}
        for asset_id, data in base_prices.items():
            base_price = data['usd']
            volatility = random.uniform(-0.02, 0.02)  # ±2%
            current_price = base_price * (1 + volatility)
            
            fallback_prices[asset_id] = {
                'usd': current_price,
                'usd_24h_change': data['usd_24h_change'],
                'usd_market_cap': current_price * 20000000,  # Estimation
                'usd_24h_vol': current_price * 1000000  # Estimation
            }
        
        logger.info(f"📊 Prix simulés générés pour {len(fallback_prices)} actifs")
        return fallback_prices
    
    async def calculate_asset_performance(self, 
                                        db, 
                                        holding: models.WalletHolding,
                                        current_prices: Dict[str, Dict]) -> Optional[AssetPerformance]:
        """Calcule la performance d'un asset individuel"""
        try:
            # Récupérer les détails de l'asset
            asset = crud.get_asset(db, holding.asset_id)
            if not asset:
                return None
            
            # Prix actuel
            coingecko_id = asset.coingecko_id or asset.asset_id
            if coingecko_id not in current_prices:
                logger.warning(f"Prix non disponible pour {asset.symbol} ({coingecko_id})")
                return None
            
            current_price = Decimal(str(current_prices[coingecko_id]['usd']))
            
            # Calculs de base
            quantity = holding.quantity
            avg_buy_price = holding.average_buy_price or Decimal('0')  # Gérer les NULL
            
            # Si pas de prix d'achat, utiliser le prix actuel comme référence
            if avg_buy_price == 0:
                avg_buy_price = current_price
                logger.info(f"Prix d'achat manquant pour {asset.symbol}, utilisation du prix actuel: ${current_price}")
            
            total_cost = quantity * avg_buy_price
            current_value = quantity * current_price
            
            # P&L non réalisé
            unrealized_pnl = current_value - total_cost
            unrealized_pnl_percent = float((unrealized_pnl / total_cost) * 100) if total_cost > 0 else 0.0
            
            # Récupérer les statistiques de trading pour cet asset
            transactions = crud.get_asset_transactions(db, holding.wallet_id, asset.id)
            total_trades = len([t for t in transactions if t.type in [models.TransactionType.BUY, models.TransactionType.SELL]])
            total_fees = sum(t.fees for t in transactions if t.fees)
            
            # Performance temporelle (approximation basée sur les prix actuels)
            # TODO: Implémenter un vrai historique de prix
            daily_change = current_prices[coingecko_id].get('usd_24h_change', 0.0)
            
            return AssetPerformance(
                asset_id=asset.id,
                symbol=asset.symbol,
                name=asset.name,
                quantity=quantity,
                average_buy_price=avg_buy_price,
                current_price=current_price,
                total_cost=total_cost,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                total_trades=total_trades,
                total_fees_paid=total_fees,
                daily_change=daily_change
            )
            
        except Exception as e:
            logger.error(f"Erreur calcul performance asset {holding.asset_id}: {e}")
            return None
    
    async def calculate_wallet_performance(self, 
                                            db, 
                                            wallet_id: int,
                                            force_refresh: bool = False) -> Optional[WalletPerformance]:
        """Calcule la performance complète du portefeuille"""
        try:
            # Récupérer le wallet
            wallet = crud.get_wallet(db, wallet_id)
            if not wallet:
                return None
            
            # Prix actuels
            current_prices = await self.get_current_prices(force_refresh)
            if not current_prices:
                logger.error("Impossible de récupérer les prix actuels")
                return None
            
            # Récupérer tous les holdings
            holdings = crud.get_wallet_holdings(db, wallet_id)
            active_holdings = [h for h in holdings if h.quantity > 0]
            
            if not active_holdings:
                budget_initial = Decimal(str(wallet.initial_budget_usd or 0))
                # P&L = Valeur actuelle (0) - Budget initial = -budget_initial
                net_pnl = Decimal('0') - budget_initial
                return WalletPerformance(
                    wallet_id=wallet_id,
                    wallet_name=wallet.name,
                    total_invested=Decimal('0'),
                    current_value=Decimal('0'),
                    total_fees_paid=Decimal('0'),
                    initial_budget=budget_initial,
                    available_cash=budget_initial,
                    total_wallet_value=budget_initial,
                    unrealized_pnl=Decimal('0'),
                    unrealized_pnl_percent=0.0,
                    realized_pnl=Decimal('0'),
                    net_pnl=net_pnl,
                    asset_count=0,
                    assets=[]
                )
            
            # Calculer la performance de chaque asset
            asset_performances = []
            total_invested = Decimal('0')
            current_value = Decimal('0')
            total_fees = Decimal('0')
            
            for holding in active_holdings:
                asset_perf = await self.calculate_asset_performance(db, holding, current_prices)
                if asset_perf:
                    asset_performances.append(asset_perf)
                    total_invested += asset_perf.total_cost
                    current_value += asset_perf.current_value
                    total_fees += asset_perf.total_fees_paid
            
            # P&L calculations avec prise en compte du budget initial
            # Si on a un budget initial défini, utiliser celui-ci comme référence
            budget_initial = Decimal(str(wallet.initial_budget_usd or 0))
            
            # P&L non réalisé par rapport au coût d'investissement (pour les holdings individuels)
            unrealized_pnl = current_value - total_invested
            unrealized_pnl_percent = float((unrealized_pnl / total_invested) * 100) if total_invested > 0 else 0.0
            
            # Liquide disponible = Budget initial - Montant investi
            available_cash = budget_initial - total_invested
            total_wallet_value = current_value + available_cash  # Holdings + cash disponible
            
            # P&L Total par rapport au budget initial (ce que l'utilisateur veut voir)
            total_pnl_vs_initial = current_value - budget_initial
            
            # Calcul du P&L réalisé (ventes passées)
            all_transactions = crud.get_wallet_transactions(db, wallet_id)
            sell_transactions = [t for t in all_transactions if t.type == models.TransactionType.SELL]
            
            realized_pnl = Decimal('0')
            for sell_tx in sell_transactions:
                # P&L réalisé = Prix de vente - Prix d'achat moyen - Frais
                # (Simplifié, idealement il faudrait tracker les lots FIFO/LIFO)
                asset = crud.get_asset(db, sell_tx.asset_id)
                if asset:
                    holding = crud.get_holding(db, wallet_id, asset.id)
                    if holding:
                        sale_value = sell_tx.amount * sell_tx.price_at_time
                        cost_basis = sell_tx.amount * holding.average_buy_price
                        tx_pnl = sale_value - cost_basis - (sell_tx.fees or 0)
                        realized_pnl += tx_pnl
            
            # P&L net total - utiliser le P&L par rapport au budget initial pour l'affichage principal
            net_pnl = total_pnl_vs_initial  # P&L principal = Valeur actuelle - Budget initial
            
            # P&L traditionnel (pour les métriques internes)
            traditional_net_pnl = realized_pnl + unrealized_pnl - total_fees
            
            # Métriques de performance
            best_performer = max(asset_performances, key=lambda x: x.unrealized_pnl_percent) if asset_performances else None
            worst_performer = min(asset_performances, key=lambda x: x.unrealized_pnl_percent) if asset_performances else None
            
            # Concentration (% du plus gros holding)
            concentration_ratio = 0.0
            if asset_performances and current_value > 0:
                largest_position = max(asset_performances, key=lambda x: x.current_value)
                concentration_ratio = float((largest_position.current_value / current_value) * 100)
            
            return WalletPerformance(
                wallet_id=wallet_id,
                wallet_name=wallet.name,
                total_invested=total_invested,
                current_value=current_value,
                total_fees_paid=total_fees,
                initial_budget=budget_initial,
                available_cash=available_cash,
                total_wallet_value=total_wallet_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                realized_pnl=realized_pnl,
                net_pnl=net_pnl,
                best_performer=best_performer,
                worst_performer=worst_performer,
                asset_count=len(asset_performances),
                concentration_ratio=concentration_ratio,
                assets=asset_performances
            )
            
        except Exception as e:
            logger.error(f"Erreur calcul performance wallet {wallet_id}: {e}")
            return None
    
    def get_performance_summary_for_llm(self, wallet: WalletPerformance) -> str:
        """Génère un résumé de performance formaté pour les prompts LLM"""
        
        summary = f"""📊 Performance du Portefeuille "{wallet.wallet_name}":

💰 Valeurs:
• Investi: ${wallet.total_invested:,.2f}
• Valeur actuelle: ${wallet.current_value:,.2f}
• Frais payés: ${wallet.total_fees_paid:,.2f}

📈 P&L:
• Non réalisé: ${wallet.unrealized_pnl:,.2f} ({wallet.unrealized_pnl_percent:+.2f}%)
• Réalisé: ${wallet.realized_pnl:,.2f}
• P&L Net: ${wallet.net_pnl:,.2f}

🎯 Performance:
• Meilleur: {wallet.best_performer.symbol if wallet.best_performer else 'N/A'} ({wallet.best_performer.unrealized_pnl_percent:+.1f}% si disponible)
• Pire: {wallet.worst_performer.symbol if wallet.worst_performer else 'N/A'} ({wallet.worst_performer.unrealized_pnl_percent:+.1f}% si disponible)

📊 Diversification:
• Assets: {wallet.asset_count}
• Concentration: {wallet.concentration_ratio:.1f}% (plus gros holding)

⚠️ Considérations pour trading:
• Impact frais sur rendement: {float(wallet.total_fees_paid / wallet.total_invested * 100) if wallet.total_invested > 0 else 0:.2f}%
• Besoin de rééquilibrage si concentration > 50%
• Vendre les perdants si P&L < -20% (stop loss)"""

        return summary
    
    async def get_trade_impact_analysis(self, 
                                      db, 
                                      wallet_id: int,
                                      proposed_trade: Dict) -> Dict:
        """Analyse l'impact d'un trade proposé sur le wallet"""
        
        # Performance actuelle
        current_performance = await self.calculate_wallet_performance(db, wallet_id)
        if not current_performance:
            return {"error": "Impossible d'analyser le wallet actuel"}
        
        # Simuler les frais du trade proposé
        trade_amount = proposed_trade.get('amount_usd', 0)
        fees_analysis = get_realistic_trading_fees(trade_amount)
        
        # Impact sur les frais totaux
        new_total_fees = current_performance.total_fees_paid + Decimal(str(fees_analysis['total_fee']))
        fee_impact = float(fees_analysis['total_fee'] / trade_amount * 100) if trade_amount > 0 else 0
        
        return {
            "current_wallet_value": float(current_performance.current_value),
            "trade_amount_usd": trade_amount,
            "estimated_fees": fees_analysis,
            "fee_impact_percent": fee_impact,
            "new_total_fees": float(new_total_fees),
            "fee_ratio_to_wallet": float(new_total_fees / current_performance.current_value * 100) if current_performance.current_value > 0 else 0,
            "recommendation": self._get_trade_recommendation(fee_impact, current_performance)
        }
    
    def _get_trade_recommendation(self, fee_impact: float, wallet: WalletPerformance) -> str:
        """Génère une recommandation basée sur l'analyse des frais et performance"""
        
        if fee_impact > 2.0:
            return f"⚠️ ATTENTION: Frais élevés ({fee_impact:.1f}%) - Considérer un montant plus important"
        elif fee_impact > 1.0:
            return f"💡 Frais modérés ({fee_impact:.1f}%) - Trade acceptable"
        elif wallet.concentration_ratio > 70:
            return "🎯 DIVERSIFICATION: Wallet trop concentré - Considérer diversifier"
        elif wallet.unrealized_pnl_percent < -15:
            return "🔄 REBALANCING: Performance négative - Considérer stop-loss ou rebalancing"
        else:
            return f"✅ OPTIMAL: Frais faibles ({fee_impact:.1f}%) - Trade recommandé"

# Instance globale
pnl_calculator = PnLCalculator()