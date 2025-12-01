#!/usr/bin/env python3
"""
Exemple d'agent de trading avec LlamaCpp + MCP Tools
Démontre l'utilisation complète de l'intégration
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import dspy
from backend.dspy_llm_adapter import get_dspy_lm

# Configuration DSPy avec LlamaCpp (par défaut)
lm = get_dspy_lm()
dspy.configure(lm=lm)

print("=" * 60)
print(f"Agent de Trading avec {lm.provider}")
print("=" * 60)

# ============================================================================
# 1. Agent de Contexte Mondial
# ============================================================================

class WorldContextSignature(dspy.Signature):
    """Synthétise le contexte économique mondial"""
    news_summary = dspy.InputField(desc="Résumé des actualités récentes")
    market_sentiment = dspy.OutputField(desc="Sentiment général: bullish, bearish, neutral")
    key_events = dspy.OutputField(desc="Événements clés impactant les marchés")

class WorldContextAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(WorldContextSignature)

    def forward(self, news):
        return self.analyze(news_summary=news)

# Test
print("\n1. World Context Agent:")
print("-" * 40)

world_agent = WorldContextAgent()
result = world_agent(news="""
- Fed maintient les taux à 5.5%
- Bitcoin atteint un nouveau ATH
- Ethereum upgrade réussi
- Forte adoption institutionnelle
""")

print(f"Sentiment: {result.market_sentiment}")
print(f"Événements clés: {result.key_events}")

# ============================================================================
# 2. Agent de Sélection d'Opportunités
# ============================================================================

class OpportunitySignature(dspy.Signature):
    """Identifie les opportunités de trading"""
    market_context = dspy.InputField(desc="Contexte du marché actuel")
    available_assets = dspy.InputField(desc="Liste des actifs disponibles")
    top_opportunities = dspy.OutputField(desc="Top 3 opportunités avec raisons")

class OpportunityAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.find_opportunities = dspy.ChainOfThought(OpportunitySignature)

    def forward(self, context, assets):
        return self.find_opportunities(
            market_context=context,
            available_assets=assets
        )

# Test
print("\n2. Opportunity Selection Agent:")
print("-" * 40)

opportunity_agent = OpportunityAgent()
result = opportunity_agent(
    context=f"Sentiment: {result.market_sentiment}",
    assets="Bitcoin, Ethereum, Solana, Cardano, Polkadot"
)

print(f"Opportunités: {result.top_opportunities}")

# ============================================================================
# 3. Agent de Décision de Trade
# ============================================================================

class TradeDecisionSignature(dspy.Signature):
    """Décide d'un trade spécifique"""
    asset = dspy.InputField(desc="Actif à trader")
    market_analysis = dspy.InputField(desc="Analyse du marché")
    risk_level = dspy.InputField(desc="Niveau de risque accepté")
    action = dspy.OutputField(desc="Action: BUY, SELL, HOLD")
    amount = dspy.OutputField(desc="Montant en %")
    reason = dspy.OutputField(desc="Raison de la décision")

class TradeDecisionAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.decide = dspy.ChainOfThought(TradeDecisionSignature)

    def forward(self, asset, analysis, risk):
        return self.decide(
            asset=asset,
            market_analysis=analysis,
            risk_level=risk
        )

# Test
print("\n3. Trade Decision Agent:")
print("-" * 40)

trade_agent = TradeDecisionAgent()
result = trade_agent(
    asset="Bitcoin",
    analysis="ATH atteint, volume élevé, sentiment bullish",
    risk="modéré"
)

print(f"Actif: Bitcoin")
print(f"Action: {result.action}")
print(f"Montant: {result.amount}")
print(f"Raison: {result.reason}")

# ============================================================================
# 4. Pipeline complet
# ============================================================================

print("\n4. Pipeline complet de trading:")
print("-" * 40)

class TradingPipeline(dspy.Module):
    """Pipeline complet d'analyse et de décision"""

    def __init__(self):
        super().__init__()
        self.world_context = WorldContextAgent()
        self.opportunities = OpportunityAgent()
        self.trade_decision = TradeDecisionAgent()

    def forward(self, news, assets, risk_level):
        # 1. Analyser le contexte
        context = self.world_context(news=news)

        # 2. Trouver les opportunités
        opps = self.opportunities(
            context=context.market_sentiment,
            assets=assets
        )

        # 3. Décider pour la première opportunité
        # (en pratique, on itérerait sur toutes)
        first_asset = opps.top_opportunities.split(",")[0].strip()

        decision = self.trade_decision(
            asset=first_asset,
            analysis=f"{context.market_sentiment} - {context.key_events}",
            risk=risk_level
        )

        return {
            "context": context,
            "opportunities": opps,
            "decision": decision
        }

# Exécuter le pipeline
pipeline = TradingPipeline()

result = pipeline(
    news="""
    - Inflation en baisse
    - Bitcoin ETF approuvé
    - Ethereum staking record
    """,
    assets="Bitcoin, Ethereum, Solana",
    risk_level="conservateur"
)

print(f"\n📊 Résultats du pipeline:")
print(f"  Sentiment: {result['context'].market_sentiment}")
print(f"  Opportunités: {result['opportunities'].top_opportunities}")
print(f"  Décision: {result['decision'].action} {result['decision'].amount}")
print(f"  Raison: {result['decision'].reason}")

# ============================================================================
# 5. Comparaison multi-modèles
# ============================================================================

print("\n5. Comparaison LlamaCpp vs Gemini:")
print("-" * 40)

# LlamaCpp (déjà configuré)
lm_local = get_dspy_lm("default_llamacpp")
dspy.configure(lm=lm_local)

qa = dspy.ChainOfThought("question -> answer")
local_answer = qa(question="Bitcoin ou Ethereum pour 2025?").answer

print(f"LlamaCpp (local): {local_answer[:100]}...")

# Gemini (si disponible)
try:
    lm_cloud = get_dspy_lm("gemini-pro")
    dspy.configure(lm=lm_cloud)

    cloud_answer = qa(question="Bitcoin ou Ethereum pour 2025?").answer
    print(f"Gemini (cloud):   {cloud_answer[:100]}...")

except Exception as e:
    print(f"Gemini non disponible: {e}")

print("\n" + "=" * 60)
print("✅ Exemple complet terminé!")
print(f"   Modèle utilisé: {lm.provider}")
print(f"   Tous les agents fonctionnent avec LlamaCpp")
print("=" * 60)
