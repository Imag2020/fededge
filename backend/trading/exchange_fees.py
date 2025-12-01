"""
Système de frais d'échange réalistes pour les simulations de trading.
Basé sur les vrais frais des exchanges populaires (données 2025).
"""

from enum import Enum
from typing import Dict, Tuple, Optional
import random
import logging

logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    """Types d'échanges avec leurs caractéristiques de frais"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BYBIT = "bybit"
    OKX = "okx"
    LBANK = "lbank"
    KUCOIN = "kucoin"
    
    # Échanges décentralisés
    UNISWAP = "uniswap"
    PANCAKESWAP = "pancakeswap"

class TradingTier(Enum):
    """Niveaux de trading qui affectent les frais"""
    RETAIL = "retail"        # Utilisateur particulier
    VOLUME_TRADER = "volume" # Trader à gros volume
    VIP = "vip"             # Client VIP
    INSTITUTIONAL = "institutional"  # Institutionnel

class FeeStructure:
    """Structure de frais pour un échange"""
    
    def __init__(self, 
                 maker_fee: float, 
                 taker_fee: float, 
                 withdrawal_fee: float = 0.0,
                 minimum_fee: float = 0.0,
                 gas_fee_range: Tuple[float, float] = (0.0, 0.0)):
        self.maker_fee = maker_fee      # Frais pour les ordres maker (ajoutent de la liquidité)
        self.taker_fee = taker_fee      # Frais pour les ordres taker (prennent de la liquidité)
        self.withdrawal_fee = withdrawal_fee  # Frais de retrait
        self.minimum_fee = minimum_fee  # Frais minimum par transaction
        self.gas_fee_range = gas_fee_range  # Pour les DEX (min, max en USD)

# Frais réels des exchanges (données 2025)
EXCHANGE_FEES: Dict[ExchangeType, Dict[TradingTier, FeeStructure]] = {
    ExchangeType.BINANCE: {
        TradingTier.RETAIL: FeeStructure(0.001, 0.001),  # 0.1% maker/taker
        TradingTier.VOLUME_TRADER: FeeStructure(0.0009, 0.001),  # Réduction maker
        TradingTier.VIP: FeeStructure(0.0008, 0.0009),
        TradingTier.INSTITUTIONAL: FeeStructure(0.0006, 0.0008)
    },
    
    ExchangeType.COINBASE: {
        TradingTier.RETAIL: FeeStructure(0.005, 0.005),  # 0.5% (plus cher)
        TradingTier.VOLUME_TRADER: FeeStructure(0.0035, 0.005),
        TradingTier.VIP: FeeStructure(0.003, 0.0035),
        TradingTier.INSTITUTIONAL: FeeStructure(0.002, 0.003)
    },
    
    ExchangeType.BYBIT: {
        TradingTier.RETAIL: FeeStructure(0.001, 0.001),  # 0.1% maker/taker
        TradingTier.VOLUME_TRADER: FeeStructure(0.0008, 0.001),
        TradingTier.VIP: FeeStructure(0.0006, 0.0008),
        TradingTier.INSTITUTIONAL: FeeStructure(0.0004, 0.0006)
    },
    
    ExchangeType.OKX: {
        TradingTier.RETAIL: FeeStructure(0.0008, 0.001),  # 0.08% maker, 0.1% taker
        TradingTier.VOLUME_TRADER: FeeStructure(0.0006, 0.0009),
        TradingTier.VIP: FeeStructure(0.0004, 0.0007),
        TradingTier.INSTITUTIONAL: FeeStructure(0.0002, 0.0005)
    },
    
    ExchangeType.KRAKEN: {
        TradingTier.RETAIL: FeeStructure(0.0016, 0.0026),  # Plus cher mais plus régulé
        TradingTier.VOLUME_TRADER: FeeStructure(0.0014, 0.0024),
        TradingTier.VIP: FeeStructure(0.0012, 0.0022),
        TradingTier.INSTITUTIONAL: FeeStructure(0.001, 0.002)
    },
    
    ExchangeType.LBANK: {
        TradingTier.RETAIL: FeeStructure(0.001, 0.001),  # 0.1% maker/taker
        TradingTier.VOLUME_TRADER: FeeStructure(0.0008, 0.001),
        TradingTier.VIP: FeeStructure(0.0006, 0.0008),
        TradingTier.INSTITUTIONAL: FeeStructure(0.0004, 0.0006)
    },
    
    # Échanges décentralisés avec frais de gas variables
    ExchangeType.UNISWAP: {
        TradingTier.RETAIL: FeeStructure(0.003, 0.003, gas_fee_range=(5.0, 50.0)),  # 0.3% + gas
        TradingTier.VOLUME_TRADER: FeeStructure(0.003, 0.003, gas_fee_range=(5.0, 50.0)),
        TradingTier.VIP: FeeStructure(0.003, 0.003, gas_fee_range=(5.0, 50.0)),
        TradingTier.INSTITUTIONAL: FeeStructure(0.003, 0.003, gas_fee_range=(5.0, 50.0))
    },
    
    ExchangeType.PANCAKESWAP: {
        TradingTier.RETAIL: FeeStructure(0.0025, 0.0025, gas_fee_range=(0.5, 2.0)),  # 0.25% + gas BSC
        TradingTier.VOLUME_TRADER: FeeStructure(0.0025, 0.0025, gas_fee_range=(0.5, 2.0)),
        TradingTier.VIP: FeeStructure(0.0025, 0.0025, gas_fee_range=(0.5, 2.0)),
        TradingTier.INSTITUTIONAL: FeeStructure(0.0025, 0.0025, gas_fee_range=(0.5, 2.0))
    }
}

class ExchangeFeeCalculator:
    """Calculateur de frais d'échange réaliste"""
    
    def __init__(self, 
                 preferred_exchange: ExchangeType = ExchangeType.BINANCE,
                 trading_tier: TradingTier = TradingTier.RETAIL,
                 simulate_market_conditions: bool = True):
        self.preferred_exchange = preferred_exchange
        self.trading_tier = trading_tier
        self.simulate_market_conditions = simulate_market_conditions
        
    def calculate_trading_fees(self, 
                             trade_amount_usd: float, 
                             is_maker: bool = False,
                             exchange_override: Optional[ExchangeType] = None) -> Dict[str, float]:
        """
        Calcule les frais de trading pour une transaction donnée.
        
        Args:
            trade_amount_usd: Montant du trade en USD
            is_maker: True si ordre maker, False si taker
            exchange_override: Forcer un exchange spécifique
            
        Returns:
            Dict avec les détails des frais
        """
        exchange = exchange_override or self.preferred_exchange
        fee_structure = EXCHANGE_FEES[exchange][self.trading_tier]
        
        # Sélectionner le bon taux de frais
        base_fee_rate = fee_structure.maker_fee if is_maker else fee_structure.taker_fee
        
        # Calculer les frais de base
        base_fee = trade_amount_usd * base_fee_rate
        
        # Frais de gas pour les DEX
        gas_fee = 0.0
        if exchange in [ExchangeType.UNISWAP, ExchangeType.PANCAKESWAP]:
            gas_min, gas_max = fee_structure.gas_fee_range
            gas_fee = random.uniform(gas_min, gas_max)
            
            # Conditions de réseau : frais plus élevés pendant les pics
            if self.simulate_market_conditions:
                network_congestion = random.random()
                if network_congestion > 0.8:  # 20% de chance de congestion
                    gas_fee *= random.uniform(2.0, 5.0)  # 2x à 5x plus cher
        
        # Frais minimum
        total_trading_fee = max(base_fee, fee_structure.minimum_fee)
        
        # Frais total
        total_fee = total_trading_fee + gas_fee
        
        return {
            "exchange": exchange.value,
            "trading_tier": self.trading_tier.value,
            "trade_amount_usd": trade_amount_usd,
            "base_fee_rate": base_fee_rate,
            "trading_fee": total_trading_fee,
            "gas_fee": gas_fee,
            "total_fee": total_fee,
            "effective_fee_rate": total_fee / trade_amount_usd if trade_amount_usd > 0 else 0,
            "is_maker": is_maker
        }
    
    def get_exchange_comparison(self, trade_amount_usd: float) -> Dict[str, Dict]:
        """Compare les frais across plusieurs exchanges pour un montant donné"""
        comparison = {}
        
        for exchange in ExchangeType:
            if exchange in EXCHANGE_FEES:
                fees = self.calculate_trading_fees(
                    trade_amount_usd, 
                    is_maker=False,  # Assume taker order
                    exchange_override=exchange
                )
                comparison[exchange.value] = fees
        
        return comparison
    
    def optimize_exchange_selection(self, trade_amount_usd: float) -> Tuple[ExchangeType, Dict]:
        """
        Sélectionne le meilleur exchange pour minimiser les frais.
        
        Returns:
            Tuple (meilleur_exchange, détails_frais)
        """
        comparison = self.get_exchange_comparison(trade_amount_usd)
        
        # Trouver l'exchange avec les frais les plus bas
        best_exchange = min(comparison.keys(), key=lambda x: comparison[x]["total_fee"])
        
        return ExchangeType(best_exchange), comparison[best_exchange]
    
    def get_fee_summary_for_llm(self, trade_amount_usd: float) -> str:
        """
        Génère un résumé des frais formaté pour les prompts LLM.
        """
        fees = self.calculate_trading_fees(trade_amount_usd)
        
        summary = f"""Frais de trading estimés:
• Exchange: {fees['exchange'].title()}
• Niveau: {fees['trading_tier'].title()}
• Montant: ${trade_amount_usd:,.2f}
• Frais de trading: ${fees['trading_fee']:.2f} ({fees['base_fee_rate']:.2%})
• Frais de gas: ${fees['gas_fee']:.2f}
• Frais total: ${fees['total_fee']:.2f} ({fees['effective_fee_rate']:.3%})
• Impact sur rendement: -{fees['effective_fee_rate']:.2%}"""

        return summary

# Instance globale pour l'utilisation dans l'application
fee_calculator = ExchangeFeeCalculator()

def get_realistic_trading_fees(trade_amount_usd: float, 
                             is_maker: bool = False,
                             exchange: Optional[str] = None) -> Dict[str, float]:
    """
    Fonction utilitaire pour obtenir des frais de trading réalistes.
    Utilisable depuis d'autres modules.
    """
    exchange_enum = None
    if exchange:
        try:
            exchange_enum = ExchangeType(exchange.lower())
        except ValueError:
            logger.warning(f"Exchange {exchange} non reconnu, utilisation de {fee_calculator.preferred_exchange}")
    
    return fee_calculator.calculate_trading_fees(
        trade_amount_usd,
        is_maker=is_maker,
        exchange_override=exchange_enum
    )