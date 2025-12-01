#!/usr/bin/env python3
"""
Test Phase 2.5 : Validation complète avec persistence SQL

Simule un cycle complet :
1. Populate graph
2. Save to SQL
3. "Restart" (reset in-memory)
4. Load from SQL
5. Build consciousness with persisted data
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.entity_memory import get_entity_graph, reset_entity_graph


async def phase_1_populate():
    """Phase 1: Peupler le graphe"""
    print("=" * 70)
    print("PHASE 1: POPULATION + SAVE SQL")
    print("=" * 70)

    agent_id = "fededge_core_v3"

    # Reset for clean test
    reset_entity_graph(agent_id)

    # Get graph WITHOUT auto-load (fresh start)
    graph = get_entity_graph(agent_id, auto_load=False)

    # Create user
    user_id = graph.add_entity(
        type="user",
        label="Test User Phase 2.5",
        attributes={
            "user_id": "default_user",
            "risk_profile": "aggressive",
            "portfolio_value": 150000,
        },
        importance=1.0,
        entity_id="user_default",
    )
    print(f"✅ User: {user_id}")

    # Create assets
    btc_id = graph.add_entity(
        type="asset",
        label="Bitcoin",
        attributes={"symbol": "BTC", "price": 90600},
        importance=1.0,
        entity_id="asset_BTC",
    )
    print(f"✅ Asset: BTC")

    eth_id = graph.add_entity(
        type="asset",
        label="Ethereum",
        attributes={"symbol": "ETH", "price": 3005},
        importance=0.9,
        entity_id="asset_ETH",
    )
    print(f"✅ Asset: ETH")

    # Create positions
    graph.add_relation(
        source=user_id,
        target=btc_id,
        type="OWNS",
        attributes={"amount": 0.5, "entry_price": 45000},
        strength=1.0,
    )
    print(f"✅ Position: 0.5 BTC @ $45,000")

    graph.add_relation(
        source=user_id,
        target=eth_id,
        type="OWNS",
        attributes={"amount": 2.0, "entry_price": 2800},
        strength=1.0,
    )
    print(f"✅ Position: 2.0 ETH @ $2,800")

    # Create pattern with outcome
    pattern_id = graph.add_entity(
        type="pattern",
        label="Golden Cross BTC",
        attributes={
            "pattern_type": "golden_cross",
            "asset": "BTC",
            "confidence": 0.85,
        },
        importance=0.8,
    )

    graph.add_relation(
        source=btc_id,
        target=pattern_id,
        type="FOLLOWS",
        attributes={},
    )

    outcome_id = graph.add_entity(
        type="outcome",
        label="GC BTC Success",
        attributes={"pnl_pct": 12.5, "duration_hours": 48},
    )

    graph.add_relation(
        source=pattern_id,
        target=outcome_id,
        type="RESULTED_IN",
        attributes={},
    )

    print(f"✅ Pattern + Outcome: golden_cross BTC → +12.5%")

    print(f"\n📊 Graph état:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    # SAVE TO SQL
    print(f"\n💾 Sauvegarde SQL...")
    graph.save_to_sql()
    print(f"✅ Sauvegarde terminée!")

    return True


async def phase_2_restart_and_load():
    """Phase 2: Simuler restart + load SQL"""
    print("\n" + "=" * 70)
    print("PHASE 2: SIMULER RESTART (reset in-memory + load SQL)")
    print("=" * 70)

    agent_id = "fededge_core_v3"

    # Reset in-memory (simule restart)
    print(f"🔄 Reset in-memory graph (simule restart)...")
    reset_entity_graph(agent_id)

    # Get graph WITH auto-load (should load from SQL)
    print(f"📂 Load from SQL (auto-load=True)...")
    graph = get_entity_graph(agent_id, auto_load=True)

    print(f"\n📊 Graph après load SQL:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    # Verify
    if len(graph.entities) != 5:
        print(f"❌ FAIL: Expected 5 entities, got {len(graph.entities)}")
        return False

    if len(graph.relations) != 4:
        print(f"❌ FAIL: Expected 4 relations, got {len(graph.relations)}")
        return False

    # Verify user positions
    users = graph.find_entities(type="user")
    if not users:
        print(f"❌ FAIL: No user found")
        return False

    positions = graph.get_user_positions(users[0].id)
    if len(positions) != 2:
        print(f"❌ FAIL: Expected 2 positions, got {len(positions)}")
        return False

    print(f"\n💰 Positions restaurées:")
    for pos in positions:
        pnl_pct = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
        print(f"   - {pos['symbol']}: {pos['amount']} @ ${pos['entry_price']:,.0f} → ${pos['current_price']:,.0f} ({pnl_pct:+.1f}%)")

    # Verify patterns
    patterns = graph.find_entities(type="pattern")
    if len(patterns) != 1:
        print(f"❌ FAIL: Expected 1 pattern, got {len(patterns)}")
        return False

    print(f"\n📈 Patterns restaurés:")
    for p in patterns:
        print(f"   - {p.label} ({p.attributes.get('confidence', 0):.0%})")

    print(f"\n✅ TOUTES LES DONNÉES RESTAURÉES DEPUIS SQL!")
    return True


async def phase_3_consciousness():
    """Phase 3: Build conscience avec données persistées"""
    print("\n" + "=" * 70)
    print("PHASE 3: BUILD CONSCIENCE AVEC DONNÉES PERSISTÉES")
    print("=" * 70)

    from backend.agent_consciousness_v2 import get_consciousness_builder

    builder = get_consciousness_builder()
    consciousness = await builder.build(user_id="default_user", agent_id="fededge_core_v3")

    print(f"\n🧠 CONSCIENCE V2:")

    # User context
    print(f"\n👤 USER CONTEXT (from SQL):")
    print(f"   Portfolio value: ${consciousness.user_context.total_portfolio_value:,.2f}")
    print(f"   Active positions: {len(consciousness.user_context.active_positions)}")

    if not consciousness.user_context.active_positions:
        print(f"❌ FAIL: No positions in consciousness")
        return False

    for pos in consciousness.user_context.active_positions:
        print(f"      - {pos.asset}: {pos.amount} @ ${pos.entry_price:,.0f} ({pos.pnl_pct:+.1f}%)")

    # Memory
    print(f"\n🧠 MEMORY (from SQL):")
    print(f"   Patterns: {consciousness.memory.user_patterns}")
    print(f"   Successful strategies: {len(consciousness.memory.successful_strategies)}")

    for strat in consciousness.memory.successful_strategies:
        print(f"      - {strat}")

    if not consciousness.memory.successful_strategies:
        print(f"❌ FAIL: No strategies in memory")
        return False

    # Natural language
    print(f"\n📝 NATURAL LANGUAGE SUMMARY:")
    summary = consciousness.to_natural_language(max_length=500)
    print(f"   {summary}")

    if "$" not in summary:
        print(f"❌ FAIL: Portfolio not in summary")
        return False

    print(f"\n✅ CONSCIENCE ENRICHIE AVEC DONNÉES SQL!")
    return True


async def cleanup():
    """Cleanup test data"""
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)

    try:
        from backend.db.models import SessionLocal, AgentEntityNode, AgentEntityRelation

        with SessionLocal() as db:
            deleted_rels = db.query(AgentEntityRelation).filter_by(agent_id="fededge_core_v3").delete()
            deleted_nodes = db.query(AgentEntityNode).filter_by(agent_id="fededge_core_v3").delete()
            db.commit()

            print(f"✅ Cleanup: {deleted_nodes} entities, {deleted_rels} relations deleted")

        # Also reset in-memory
        reset_entity_graph("fededge_core_v3")

    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")


async def main():
    """Run complete test"""
    print("\n" + "🧪" * 35)
    print("TEST PHASE 2.5 - VALIDATION COMPLÈTE")
    print("🧪" * 35)

    results = {}

    # Phase 1: Populate + Save
    try:
        results["populate"] = await phase_1_populate()
    except Exception as e:
        print(f"\n❌ Phase 1 failed: {e}")
        import traceback
        traceback.print_exc()
        results["populate"] = False

    # Phase 2: Restart + Load
    try:
        results["restart_load"] = await phase_2_restart_and_load()
    except Exception as e:
        print(f"\n❌ Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        results["restart_load"] = False

    # Phase 3: Consciousness
    try:
        results["consciousness"] = await phase_3_consciousness()
    except Exception as e:
        print(f"\n❌ Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        results["consciousness"] = False

    # Cleanup
    await cleanup()

    # Summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)

    for phase, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{phase}: {status}")

    total_pass = sum(results.values())
    total_tests = len(results)
    print(f"\nRésultat: {total_pass}/{total_tests} phases passées")

    if total_pass == total_tests:
        print("\n🎉 PHASE 2.5 COMPLÈTE ET VALIDÉE!")
        print("\n📝 Résumé:")
        print("   ✅ Entity Graph persiste en SQL")
        print("   ✅ Données survivent aux restarts")
        print("   ✅ Conscience enrichie avec données persistées")
        print("   ✅ Positions, patterns, et stratégies trackés")
        return 0
    else:
        print("\n⚠️ Certaines phases ont échoué")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
