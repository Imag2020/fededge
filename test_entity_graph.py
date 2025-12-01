#!/usr/bin/env python3
"""
Test Entity Graph Phase 2

Valide le fonctionnement du graphe d'entités-relations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.entity_memory import (
    get_entity_graph,
    reset_entity_graph,
)


def test_1_basic_crud():
    """Test 1: CRUD de base"""
    print("=" * 70)
    print("TEST 1: CRUD de base")
    print("=" * 70)

    reset_entity_graph("test_agent")
    graph = get_entity_graph("test_agent")

    # Create user
    user_id = graph.add_entity(
        type="user",
        label="Alice",
        attributes={"risk_profile": "moderate", "portfolio_value": 10000},
        importance=0.9,
    )
    print(f"✅ User created: {user_id}")

    # Create assets
    btc_id = graph.add_entity(
        type="asset",
        label="Bitcoin",
        attributes={"symbol": "BTC", "price": 90000, "market_cap": 1.8e12},
        importance=1.0,
    )
    print(f"✅ Asset created: {btc_id} (BTC)")

    eth_id = graph.add_entity(
        type="asset",
        label="Ethereum",
        attributes={"symbol": "ETH", "price": 3000, "market_cap": 360e9},
        importance=0.9,
    )
    print(f"✅ Asset created: {eth_id} (ETH)")

    # Create relations
    owns_btc = graph.add_relation(
        source=user_id,
        target=btc_id,
        type="OWNS",
        attributes={"amount": 0.5, "entry_price": 45000},
        strength=1.0,
    )
    print(f"✅ Relation created: {user_id} OWNS {btc_id}")

    watches_eth = graph.add_relation(
        source=user_id,
        target=eth_id,
        type="WATCHES",
        attributes={},
        strength=0.7,
    )
    print(f"✅ Relation created: {user_id} WATCHES {eth_id}")

    # Read
    user = graph.get_entity(user_id)
    print(f"\n📊 User: {user.label}")
    print(f"   Attributes: {user.attributes}")
    print(f"   Importance: {user.importance}")
    print(f"   Consolidation: {user.consolidation:.2f}")

    # Query positions
    positions = graph.get_user_positions(user_id)
    print(f"\n💰 Positions:")
    for pos in positions:
        pnl_pct = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
        print(f"   - {pos['symbol']}: {pos['amount']} @ ${pos['entry_price']:,.0f} → ${pos['current_price']:,.0f} ({pnl_pct:+.1f}%)")

    print(f"\n✅ Test 1 PASSED")
    return True


def test_2_pattern_tracking():
    """Test 2: Tracking patterns et signaux"""
    print("\n" + "=" * 70)
    print("TEST 2: Pattern tracking")
    print("=" * 70)

    graph = get_entity_graph("test_agent")

    # Find BTC asset
    btc_entities = graph.find_entities(type="asset", filters={"symbol": "BTC"})
    if not btc_entities:
        print("❌ BTC asset not found")
        return False

    btc = btc_entities[0]

    # Create pattern detected on BTC
    pattern_id = graph.add_entity(
        type="pattern",
        label="Golden Cross on BTC",
        attributes={
            "pattern_type": "golden_cross",
            "asset": "BTC",
            "confidence": 0.85,
            "timeframe": "4h",
            "active": True,
        },
        importance=0.8,
    )
    print(f"✅ Pattern created: {pattern_id}")

    # Relation: BTC FOLLOWS pattern
    graph.add_relation(
        source=btc.id,
        target=pattern_id,
        type="FOLLOWS",
        attributes={"detected_at": "2025-11-20T10:00:00Z"},
    )
    print(f"✅ Relation: BTC FOLLOWS golden_cross")

    # Create signal triggered by pattern
    signal_id = graph.add_entity(
        type="signal",
        label="BUY Signal BTC",
        attributes={
            "signal_id": "SIG_123",
            "side": "LONG",
            "confidence": 0.82,
            "entry": 85000,
            "tp": 92000,
            "sl": 82000,
        },
        importance=0.7,
    )
    print(f"✅ Signal created: {signal_id}")

    # Relation: pattern TRIGGERED signal
    graph.add_relation(
        source=pattern_id,
        target=signal_id,
        type="TRIGGERED",
        attributes={},
    )
    print(f"✅ Relation: pattern TRIGGERED signal")

    # Create outcome
    outcome_id = graph.add_entity(
        type="outcome",
        label="Golden Cross BTC Outcome",
        attributes={
            "pnl_pct": 12.5,
            "pnl_usd": 625,
            "duration_hours": 48,
            "exit_reason": "take_profit",
        },
        importance=0.6,
    )
    print(f"✅ Outcome created: {outcome_id}")

    # Relation: signal RESULTED_IN outcome
    graph.add_relation(
        source=signal_id,
        target=outcome_id,
        type="RESULTED_IN",
        attributes={},
    )
    print(f"✅ Relation: signal RESULTED_IN outcome")

    # Query pattern occurrences
    occurrences = graph.get_pattern_occurrences("golden_cross", asset="BTC")
    print(f"\n📈 Pattern occurrences (golden_cross on BTC):")
    for occ in occurrences:
        print(f"   Pattern: {occ['pattern']}")
        print(f"   Asset: {occ['asset']} ({occ['symbol']})")
        print(f"   Confidence: {occ['confidence']:.0%}")
        if occ['outcome']:
            print(f"   Outcome: {occ['outcome']['pnl_pct']:+.1f}% in {occ['outcome']['duration_hours']}h")

    print(f"\n✅ Test 2 PASSED")
    return True


def test_3_decision_history():
    """Test 3: Historique de décisions"""
    print("\n" + "=" * 70)
    print("TEST 3: Decision history")
    print("=" * 70)

    graph = get_entity_graph("test_agent")

    # Get user
    users = graph.find_entities(type="user")
    if not users:
        print("❌ User not found")
        return False

    user = users[0]

    # Get signal
    signals = graph.find_entities(type="signal")
    if not signals:
        print("❌ Signal not found")
        return False

    signal = signals[0]

    # Create decision
    decision_id = graph.add_entity(
        type="decision",
        label="Decision: Buy BTC",
        attributes={
            "action": "BUY",
            "asset": "BTC",
            "amount": 0.5,
            "price": 85000,
        },
        importance=0.7,
    )
    print(f"✅ Decision created: {decision_id}")

    # User DECIDED
    graph.add_relation(
        source=user.id,
        target=decision_id,
        type="DECIDED",
        attributes={"reasoning": "Golden cross pattern detected"},
    )
    print(f"✅ Relation: user DECIDED")

    # Decision BASED_ON signal
    graph.add_relation(
        source=decision_id,
        target=signal.id,
        type="BASED_ON",
        attributes={},
    )
    print(f"✅ Relation: decision BASED_ON signal")

    # Decision RESULTED_IN outcome
    outcomes = graph.find_entities(type="outcome")
    if outcomes:
        graph.add_relation(
            source=decision_id,
            target=outcomes[0].id,
            type="RESULTED_IN",
            attributes={},
        )
        print(f"✅ Relation: decision RESULTED_IN outcome")

    # Query decision history
    history = graph.get_decision_history(user.id)
    print(f"\n📜 Decision history:")
    for dec in history:
        print(f"   Decision: {dec['decision']}")
        print(f"   Action: {dec['action']} {dec['asset']}")
        if dec['trigger']:
            print(f"   Trigger: {dec['trigger']['type']} - {dec['trigger']['label']}")
        if dec['outcome']:
            print(f"   Outcome: {dec['outcome']['pnl_pct']:+.1f}% ({dec['outcome']['exit_reason']})")

    print(f"\n✅ Test 3 PASSED")
    return True


def test_4_graph_queries():
    """Test 4: Requêtes de graphe (neighborhood, paths)"""
    print("\n" + "=" * 70)
    print("TEST 4: Graph queries")
    print("=" * 70)

    graph = get_entity_graph("test_agent")

    # Get user
    users = graph.find_entities(type="user")
    if not users:
        print("❌ User not found")
        return False

    user = users[0]

    # Neighborhood
    neighborhood = graph.neighborhood(user.id, radius=2, max_entities=20)
    print(f"✅ Neighborhood (radius=2):")
    print(f"   Entities: {len(neighborhood['entities'])}")
    print(f"   Relations: {len(neighborhood['relations'])}")

    print(f"\n   Entities in neighborhood:")
    for ent in neighborhood['entities'][:5]:
        print(f"   - {ent['type']}: {ent['label']}")

    # Path between user and outcome
    outcomes = graph.find_entities(type="outcome")
    if outcomes:
        paths = graph.path_between(user.id, outcomes[0].id, max_depth=3)
        print(f"\n✅ Paths from user to outcome:")
        print(f"   Found {len(paths)} path(s)")
        for i, path in enumerate(paths[:3]):
            entities_labels = []
            for eid in path:
                entity = graph.get_entity(eid)
                if entity:
                    entities_labels.append(f"{entity.type}:{entity.label}")
            print(f"   Path {i+1}: {' → '.join(entities_labels)}")

    print(f"\n✅ Test 4 PASSED")
    return True


def test_5_serialization():
    """Test 5: Sérialisation/désérialisation"""
    print("\n" + "=" * 70)
    print("TEST 5: Serialization")
    print("=" * 70)

    graph = get_entity_graph("test_agent")

    # Serialize
    data = graph.to_dict()
    print(f"✅ Graph serialized:")
    print(f"   Entities: {len(data['entities'])}")
    print(f"   Relations: {len(data['relations'])}")

    # Deserialize
    from backend.entity_memory import EntityGraph
    graph2 = EntityGraph.from_dict(data)
    print(f"\n✅ Graph deserialized:")
    print(f"   Entities: {len(graph2.entities)}")
    print(f"   Relations: {len(graph2.relations)}")

    # Verify
    if len(graph.entities) == len(graph2.entities):
        print(f"✅ Entity count matches")
    else:
        print(f"❌ Entity count mismatch")
        return False

    if len(graph.relations) == len(graph2.relations):
        print(f"✅ Relation count matches")
    else:
        print(f"❌ Relation count mismatch")
        return False

    print(f"\n✅ Test 5 PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("TESTS ENTITY GRAPH - Phase 2")
    print("🧪" * 35)

    results = {}

    tests = [
        ("Basic CRUD", test_1_basic_crud),
        ("Pattern Tracking", test_2_pattern_tracking),
        ("Decision History", test_3_decision_history),
        ("Graph Queries", test_4_graph_queries),
        ("Serialization", test_5_serialization),
    ]

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ DES TESTS")
    print("=" * 70)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    total_pass = sum(results.values())
    total_tests = len(results)
    print(f"\nRésultat: {total_pass}/{total_tests} tests passés")

    if total_pass == total_tests:
        print("\n🎉 TOUS LES TESTS PASSENT - EntityGraph validé!")
        return 0
    else:
        print("\n⚠️ Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
