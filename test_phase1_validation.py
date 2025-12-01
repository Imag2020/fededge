#!/usr/bin/env python3
"""
Script de test et validation Phase 1
Génère des signaux synthétiques et force une mise à jour de la conscience
"""

import asyncio
import sys
import time
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.synthetic_signals import generate_signal_batch
from backend.services.trading_bot_service import get_trading_bot_service
from backend.agent_runtime import get_agent_runtime
from backend.agent_core_types import EventKind, Topic


async def test_1_synthetic_signals():
    """Test 1: Générer et injecter des signaux synthétiques"""
    print("=" * 70)
    print("TEST 1: Génération signaux synthétiques")
    print("=" * 70)

    # Générer 5 signaux (scénario extreme_fear = oversold)
    signals = generate_signal_batch(count=5, scenario="extreme_fear")

    print(f"\n✅ Généré {len(signals)} signaux:")
    for sig in signals:
        print(f"   {sig['symbol']} {sig['event']} {sig['side']} @ ${sig['entry_price']:.0f} (conf: {sig['confidence']:.0f}%)")

    # Injecter dans le bot service
    bot_service = get_trading_bot_service()
    if bot_service:
        bot_service.signals_queue.extend(signals)
        print(f"\n✅ Signaux injectés dans bot service (queue size: {len(bot_service.signals_queue)})")
    else:
        print("\n❌ Bot service non disponible")
        return False

    return True


async def test_2_trigger_consciousness_update():
    """Test 2: Forcer une mise à jour de la conscience"""
    print("\n" + "=" * 70)
    print("TEST 2: Mise à jour conscience via event")
    print("=" * 70)

    runtime = get_agent_runtime()
    if not runtime:
        print("\n❌ Agent runtime non disponible")
        return False

    # Poster un event market_tick pour déclencher UPDATE_CONSCIOUSNESS
    await runtime.post_event(
        kind=EventKind.MISSION_UPDATE,
        topic=Topic.SYSTEM,
        payload={
            "mission_id": "market_update",
            "kind": "market_tick",
            "prices": {"BTC": 91135, "ETH": 3053, "SOL": 138}
        },
        source="test_validation"
    )

    print("✅ Event market_tick posté")
    print("⏳ Attente traitement (5s)...")
    await asyncio.sleep(5)

    # Vérifier la working memory
    mem = await runtime.store.load()
    consciousness_v2 = mem.working.get("global_consciousness_v2")

    if consciousness_v2:
        print("\n✅ Conscience V2 présente dans working memory")

        # Afficher les couches
        print(f"\n📊 MARKET:")
        print(f"   Assets: {len(consciousness_v2['market']['prices'])}")
        print(f"   Total cap: ${consciousness_v2['market']['total_market_cap']:,.0f}")

        print(f"\n😰 SENTIMENT:")
        print(f"   Fear & Greed: {consciousness_v2['sentiment']['fear_greed_index']} ({consciousness_v2['sentiment']['fear_greed_label']})")

        print(f"\n📡 SIGNALS:")
        print(f"   Count: {consciousness_v2['signals']['signal_count']}")
        print(f"   Bullish: {consciousness_v2['signals']['bullish_signals']}")
        print(f"   Bearish: {consciousness_v2['signals']['bearish_signals']}")

        if consciousness_v2['signals']['strongest_signal']:
            sig = consciousness_v2['signals']['strongest_signal']
            print(f"   Strongest: {sig['symbol']} {sig['type']} ({sig['confidence']:.0%})")

        print(f"\n💡 OPPORTUNITIES:")
        opportunities = consciousness_v2['opportunities']['opportunities']
        print(f"   Count: {len(opportunities)}")
        if opportunities:
            for opp in opportunities[:3]:
                print(f"   - {opp['type']}: {opp['asset']} (conf: {opp['confidence']:.0%})")

        print(f"\n⚠️ RISKS:")
        risks = consciousness_v2['risks']['active_risks']
        print(f"   Count: {len(risks)}")
        print(f"   Severity: {consciousness_v2['risks']['overall_severity']}")
        if risks:
            for risk in risks[:3]:
                print(f"   - {risk['type']}: {risk['description']}")

        # Résumé NL
        summary = mem.working.get("consciousness_summary", "N/A")
        print(f"\n📝 NATURAL LANGUAGE SUMMARY:")
        print(f"   {summary}")

        return True
    else:
        print("\n❌ Conscience V2 non trouvée dans working memory")
        return False


async def test_3_api_scan_synthetic():
    """Test 3: API /trading-bot/scan avec synthetic"""
    print("\n" + "=" * 70)
    print("TEST 3: API scan synthétique")
    print("=" * 70)

    try:
        response = requests.post(
            "http://localhost:5000/trading-bot/scan",
            json={"use_synthetic": True, "scenario": "bullish"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response: {data.get('success')}")
            print(f"   Signals: {data.get('count')}")
            print(f"   Synthetic: {data.get('synthetic')}")
            print(f"   Scenario: {data.get('scenario')}")

            if data.get('signals'):
                print(f"\n   Premiers signaux:")
                for sig in data['signals'][:3]:
                    print(f"   - {sig['symbol']} {sig['event']} {sig['side']}")

            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ API Error: {e}")
        return False


async def test_4_check_broadcast():
    """Test 4: Vérifier que la conscience est broadcastée"""
    print("\n" + "=" * 70)
    print("TEST 4: Vérification broadcast")
    print("=" * 70)

    # On ne peut pas tester le WebSocket directement ici
    # Mais on peut vérifier que le broadcaster est bien configuré
    from backend.agent_consciousness import get_consciousness_broadcaster

    broadcaster = get_consciousness_broadcaster()
    if broadcaster.ws_manager:
        print("✅ WebSocket manager configuré")
        print("   Les updates devraient être broadcastées au frontend")
        return True
    else:
        print("⚠️ WebSocket manager non configuré")
        print("   Les updates ne seront pas broadcastées")
        return False


async def main():
    """Exécute tous les tests"""
    print("\n" + "🧪" * 35)
    print("VALIDATION PHASE 1 - Conscience Multi-Sources")
    print("🧪" * 35)

    results = {}

    # Test 1: Signaux synthétiques
    try:
        results['test_1'] = await test_1_synthetic_signals()
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")
        results['test_1'] = False

    # Attendre un peu
    await asyncio.sleep(2)

    # Test 2: Mise à jour conscience
    try:
        results['test_2'] = await test_2_trigger_consciousness_update()
    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")
        results['test_2'] = False

    # Test 3: API
    try:
        results['test_3'] = await test_3_api_scan_synthetic()
    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")
        results['test_3'] = False

    # Test 4: Broadcast
    try:
        results['test_4'] = await test_4_check_broadcast()
    except Exception as e:
        print(f"\n❌ Test 4 failed: {e}")
        results['test_4'] = False

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ DES TESTS")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    total_pass = sum(results.values())
    total_tests = len(results)
    print(f"\nRésultat: {total_pass}/{total_tests} tests passés")

    if total_pass == total_tests:
        print("\n🎉 TOUS LES TESTS PASSENT - Phase 1 validée!")
        return 0
    else:
        print("\n⚠️ Certains tests ont échoué - debug nécessaire")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
