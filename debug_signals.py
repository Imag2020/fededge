#!/usr/bin/env python3
"""Debug: Vérifier pourquoi les signaux ne s'affichent pas"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("=" * 70)
    print("DEBUG SIGNAUX - Pourquoi pas de signals dans la conscience ?")
    print("=" * 70)

    # 1. Vérifier bot service
    print("\n1️⃣ VÉRIFICATION BOT SERVICE")
    print("-" * 70)
    try:
        from backend.services.trading_bot_service import get_trading_bot_service
        bot = get_trading_bot_service()

        if bot:
            signals_in_queue = len(bot.signals_queue)
            print(f"✅ Bot service actif")
            print(f"   Signaux in queue: {signals_in_queue}")

            if signals_in_queue > 0:
                print(f"\n   Premiers signaux dans la queue:")
                for sig in bot.signals_queue[:3]:
                    print(f"   - {sig.get('symbol', 'N/A')} {sig.get('event', 'N/A')} {sig.get('side', 'N/A')}")
            else:
                print("   ⚠️ AUCUN signal dans la queue !")

            # Vérifier get_signals()
            signals_from_method = bot.get_signals(limit=10)
            print(f"\n   Signaux from get_signals(): {len(signals_from_method)}")

            if signals_from_method:
                print(f"\n   Premiers signaux from get_signals():")
                for sig in signals_from_method[:3]:
                    print(f"   - {sig.get('ticker', sig.get('symbol', 'N/A'))} {sig.get('event', 'N/A')}")
        else:
            print("❌ Bot service non disponible")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    # 2. Vérifier conscience builder
    print("\n\n2️⃣ VÉRIFICATION CONSCIOUSNESS BUILDER")
    print("-" * 70)
    try:
        from backend.agent_consciousness_v2 import ConsciousnessBuilder

        builder = ConsciousnessBuilder()

        # Tester gather_signals()
        signal_state = await builder.gather_signals()

        print(f"✅ ConsciousnessBuilder actif")
        print(f"   Signals récupérés: {signal_state.signal_count}")
        print(f"   Bullish: {signal_state.bullish_signals}")
        print(f"   Bearish: {signal_state.bearish_signals}")

        if signal_state.signals:
            print(f"\n   Détails des signaux:")
            for sig in signal_state.signals[:3]:
                print(f"   - {sig.symbol} {sig.type} {sig.side} (conf: {sig.confidence:.0%})")
        else:
            print("   ⚠️ AUCUN signal récupéré par gather_signals() !")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    # 3. Build conscience complète
    print("\n\n3️⃣ BUILD CONSCIENCE COMPLÈTE")
    print("-" * 70)
    try:
        consciousness = await builder.build()

        print(f"✅ Conscience construite")
        print(f"\n📊 MARKET:")
        print(f"   Assets: {len(consciousness.market.prices)}")

        print(f"\n😰 SENTIMENT:")
        print(f"   FnG: {consciousness.sentiment.fear_greed_index}")

        print(f"\n📡 SIGNALS:")
        print(f"   Count: {consciousness.signals.signal_count}")
        print(f"   Bullish: {consciousness.signals.bullish_signals}")
        print(f"   Bearish: {consciousness.signals.bearish_signals}")

        if consciousness.signals.strongest_signal:
            sig = consciousness.signals.strongest_signal
            print(f"   Strongest: {sig.symbol} {sig.type} ({sig.confidence:.0%})")

        print(f"\n💡 OPPORTUNITIES:")
        print(f"   Count: {len(consciousness.opportunities.opportunities)}")
        if consciousness.opportunities.opportunities:
            for opp in consciousness.opportunities.opportunities[:3]:
                print(f"   - {opp.type}: {opp.asset} ({opp.confidence:.0%})")

        print(f"\n⚠️ RISKS:")
        print(f"   Count: {len(consciousness.risks.active_risks)}")
        print(f"   Severity: {consciousness.risks.overall_severity.value}")

        print(f"\n📝 RÉSUMÉ NL:")
        print(f"   {consciousness.to_natural_language()}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    # 4. Générer des signaux synthétiques
    print("\n\n4️⃣ GÉNÉRATION SIGNAUX SYNTHÉTIQUES")
    print("-" * 70)
    try:
        from backend.services.synthetic_signals import generate_signal_batch

        signals = generate_signal_batch(count=3, scenario="extreme_fear")
        print(f"✅ Généré {len(signals)} signaux synthétiques")

        for sig in signals:
            print(f"   - {sig['symbol']} {sig['event']} {sig['side']} @ ${sig['entry_price']:.0f} (conf: {sig['confidence']:.0f}%)")

        # Injecter dans bot
        if bot:
            bot.signals_queue.extend(signals)
            print(f"\n✅ Signaux injectés dans bot.signals_queue")
            print(f"   Queue size: {len(bot.signals_queue)}")

            # Re-test gather_signals
            signal_state_after = await builder.gather_signals()
            print(f"\n   Après injection:")
            print(f"   Signals récupérés: {signal_state_after.signal_count}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("DEBUG TERMINÉ")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
