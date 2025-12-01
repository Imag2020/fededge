#!/usr/bin/env python3
"""
Test Phase 2 : Intégration Memory Graph + Conscience V2

Valide que la conscience est enrichie par le Memory Graph
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.entity_memory import get_entity_graph, reset_entity_graph


async def setup_test_graph():
    """Setup un graph de test avec données"""
    print("=" * 70)
    print("SETUP TEST GRAPH")
    print("=" * 70)

    agent_id = "fededge_core_v3"
    reset_entity_graph(agent_id)
    graph = get_entity_graph(agent_id)

    # 1. User
    user_id = graph.add_entity(
        type="user",
        label="Test User",
        attributes={
            "user_id": "default_user",
            "risk_profile": "aggressive",
            "portfolio_value": 150000,
        },
        importance=1.0,
        entity_id="user_default",
    )
    print(f"✅ User: {user_id}")

    # 2. Assets
    assets = [
        ("BTC", "Bitcoin", 90600),
        ("ETH", "Ethereum", 3005),
        ("SOL", "Solana", 137),
    ]

    asset_ids = {}
    for symbol, name, price in assets:
        asset_id = graph.add_entity(
            type="asset",
            label=name,
            attributes={"symbol": symbol, "price": price},
            importance=0.9,
            entity_id=f"asset_{symbol}",
        )
        asset_ids[symbol] = asset_id
        print(f"✅ Asset: {symbol} @ ${price}")

    # 3. Positions (OWNS)
    positions = [
        ("BTC", 0.5, 45000),
        ("ETH", 2.0, 2800),
    ]

    for symbol, amount, entry in positions:
        graph.add_relation(
            source=user_id,
            target=asset_ids[symbol],
            type="OWNS",
            attributes={"amount": amount, "entry_price": entry},
            strength=1.0,
        )
        print(f"✅ Position: {amount} {symbol} @ ${entry}")

    # 4. Favorites (WATCHES)
    for symbol in ["BTC", "ETH", "SOL"]:
        graph.add_relation(
            source=user_id,
            target=asset_ids[symbol],
            type="WATCHES",
            attributes={},
            strength=0.8,
        )
    print(f"✅ Favorites: BTC, ETH, SOL")

    # 5. Patterns avec outcomes
    # Pattern 1: golden_cross BTC (successful)
    pattern1 = graph.add_entity(
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
        source=asset_ids["BTC"],
        target=pattern1,
        type="FOLLOWS",
        attributes={},
    )

    outcome1 = graph.add_entity(
        type="outcome",
        label="GC BTC Success",
        attributes={"pnl_pct": 12.5, "duration_hours": 48},
        importance=0.6,
    )

    graph.add_relation(
        source=pattern1,
        target=outcome1,
        type="RESULTED_IN",
        attributes={},
    )

    print(f"✅ Pattern: golden_cross BTC → +12.5%")

    # Pattern 2: rsi_oversold ETH (successful)
    pattern2 = graph.add_entity(
        type="pattern",
        label="RSI Oversold ETH",
        attributes={
            "pattern_type": "rsi_oversold",
            "asset": "ETH",
            "confidence": 0.78,
        },
        importance=0.7,
    )

    graph.add_relation(
        source=asset_ids["ETH"],
        target=pattern2,
        type="FOLLOWS",
        attributes={},
    )

    outcome2 = graph.add_entity(
        type="outcome",
        label="RSI ETH Success",
        attributes={"pnl_pct": 8.3, "duration_hours": 24},
        importance=0.6,
    )

    graph.add_relation(
        source=pattern2,
        target=outcome2,
        type="RESULTED_IN",
        attributes={},
    )

    print(f"✅ Pattern: rsi_oversold ETH → +8.3%")

    # Pattern 3: death_cross SOL (failed)
    pattern3 = graph.add_entity(
        type="pattern",
        label="Death Cross SOL",
        attributes={
            "pattern_type": "death_cross",
            "asset": "SOL",
            "confidence": 0.70,
        },
        importance=0.7,
    )

    graph.add_relation(
        source=asset_ids["SOL"],
        target=pattern3,
        type="FOLLOWS",
        attributes={},
    )

    outcome3 = graph.add_entity(
        type="outcome",
        label="DC SOL Failed",
        attributes={"pnl_pct": -5.2, "duration_hours": 12},
        importance=0.6,
    )

    graph.add_relation(
        source=pattern3,
        target=outcome3,
        type="RESULTED_IN",
        attributes={},
    )

    print(f"✅ Pattern: death_cross SOL → -5.2%")

    print(f"\n📊 Graph totals:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    return graph


async def test_consciousness_with_memory():
    """Test consciousness enrichie par Memory Graph"""
    print("\n" + "=" * 70)
    print("TEST CONSCIENCE + MEMORY GRAPH")
    print("=" * 70)

    # Setup graph
    graph = await setup_test_graph()

    # Build consciousness
    from backend.agent_consciousness_v2 import get_consciousness_builder

    builder = get_consciousness_builder()
    consciousness = await builder.build(user_id="default_user", agent_id="fededge_core_v3")

    print(f"\n🧠 CONSCIENCE V2 RÉSULTATS:")
    print("-" * 70)

    # User Context (from graph)
    print(f"\n👤 USER CONTEXT:")
    print(f"   Risk profile: {consciousness.user_context.risk_profile}")
    print(f"   Portfolio value: ${consciousness.user_context.total_portfolio_value:,.2f}")
    print(f"   Active positions: {len(consciousness.user_context.active_positions)}")

    if consciousness.user_context.active_positions:
        for pos in consciousness.user_context.active_positions:
            print(f"      - {pos.asset}: {pos.amount} @ ${pos.entry_price:,.0f} → ${pos.current_price:,.0f} ({pos.pnl_pct:+.1f}%)")
    else:
        print(f"      ❌ FAIL: No positions (should have 2)")
        return False

    print(f"   Favorites: {consciousness.user_context.favorite_assets}")

    # Memory (from graph)
    print(f"\n🧠 MEMORY:")
    print(f"   Patterns detected: {consciousness.memory.user_patterns}")
    print(f"   Successful strategies ({len(consciousness.memory.successful_strategies)}):")

    if consciousness.memory.successful_strategies:
        for strat in consciousness.memory.successful_strategies:
            print(f"      - {strat}")
    else:
        print(f"      ❌ FAIL: No successful strategies (should detect golden_cross, rsi_oversold)")
        return False

    print(f"   Lessons learned ({len(consciousness.memory.lessons_learned)}):")

    if consciousness.memory.lessons_learned:
        for lesson in consciousness.memory.lessons_learned:
            print(f"      - {lesson}")

    print(f"   Historical performance:")
    for k, v in consciousness.memory.historical_performance.items():
        print(f"      - {k}: {v}")

    # Natural language summary
    print(f"\n📝 NATURAL LANGUAGE SUMMARY:")
    summary = consciousness.to_natural_language(max_length=500)
    print(f"   {summary}")

    # Validation checks
    print(f"\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    checks = {
        "User context has positions": len(consciousness.user_context.active_positions) > 0,
        "Portfolio value > 0": consciousness.user_context.total_portfolio_value > 0,
        "Risk profile set": consciousness.user_context.risk_profile == "aggressive",
        "Favorites set": len(consciousness.user_context.favorite_assets) >= 3,
        "Patterns detected": consciousness.memory.user_patterns != "No recent patterns",
        "Successful strategies found": len(consciousness.memory.successful_strategies) > 0,
        "Historical data present": consciousness.memory.historical_performance.get("total_patterns", 0) > 0,
    }

    all_passed = True
    for check, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check}: {status}")
        if not result:
            all_passed = False

    return all_passed


async def main():
    """Run test"""
    print("\n" + "🧪" * 35)
    print("TEST PHASE 2 - MEMORY GRAPH INTEGRATION")
    print("🧪" * 35)

    try:
        success = await test_consciousness_with_memory()

        print("\n" + "=" * 70)
        if success:
            print("✅ TOUS LES TESTS PASSENT - Phase 2 validée!")
            print("=" * 70)
            print("\n🎉 La conscience V2 est enrichie par le Memory Graph:")
            print("   - Positions utilisateur depuis graph")
            print("   - Patterns et stratégies analysés")
            print("   - Win rate et PnL tracking")
            print("   - Leçons apprises des échecs")
            return 0
        else:
            print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
