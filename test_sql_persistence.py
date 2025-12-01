#!/usr/bin/env python3
"""
Test SQL Persistence (Phase 2.5)

Vérifie que les données persistent correctement en SQL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.entity_memory import get_entity_graph, reset_entity_graph


def test_1_save_to_sql():
    """Test 1: Sauvegarder dans SQL"""
    print("=" * 70)
    print("TEST 1: SAVE TO SQL")
    print("=" * 70)

    # Reset and create fresh graph
    agent_id = "test_persistence"
    reset_entity_graph(agent_id)
    graph = get_entity_graph(agent_id, auto_load=False)  # Don't auto-load

    # Create test data
    user_id = graph.add_entity(
        type="user",
        label="Persistence Test User",
        attributes={"test": True, "value": 12345},
        importance=0.9,
        entity_id="user_test_persist",
    )
    print(f"✅ User created: {user_id}")

    btc_id = graph.add_entity(
        type="asset",
        label="Bitcoin",
        attributes={"symbol": "BTC", "price": 90600},
        importance=1.0,
        entity_id="asset_BTC_test",
    )
    print(f"✅ Asset created: {btc_id}")

    # Create relation
    graph.add_relation(
        source=user_id,
        target=btc_id,
        type="OWNS",
        attributes={"amount": 0.5, "entry_price": 45000},
        strength=1.0,
    )
    print(f"✅ Relation created: OWNS")

    print(f"\n📊 Graph avant save:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    # Save to SQL
    print(f"\n💾 Sauvegarde SQL...")
    try:
        graph.save_to_sql()
        print(f"✅ Sauvegarde réussie!")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_load_from_sql():
    """Test 2: Charger depuis SQL (nouveau processus simulé)"""
    print("\n" + "=" * 70)
    print("TEST 2: LOAD FROM SQL (simulé nouveau processus)")
    print("=" * 70)

    # Reset in-memory graph (simule nouveau processus)
    agent_id = "test_persistence"
    reset_entity_graph(agent_id)

    # Create new graph instance and load from SQL
    print(f"🔄 Création nouveau graph (auto-load=True)...")
    graph = get_entity_graph(agent_id, auto_load=True)

    print(f"\n📊 Graph après load:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    # Verify data
    if len(graph.entities) != 2:
        print(f"❌ FAIL: Expected 2 entities, got {len(graph.entities)}")
        return False

    if len(graph.relations) != 1:
        print(f"❌ FAIL: Expected 1 relation, got {len(graph.relations)}")
        return False

    # Verify user entity
    users = graph.find_entities(type="user")
    if not users:
        print(f"❌ FAIL: No user entity found")
        return False

    user = users[0]
    print(f"\n✅ User entity loaded:")
    print(f"   ID: {user.id}")
    print(f"   Label: {user.label}")
    print(f"   Attributes: {user.attributes}")

    if user.attributes.get("test") != True:
        print(f"❌ FAIL: User attributes not preserved")
        return False

    if user.attributes.get("value") != 12345:
        print(f"❌ FAIL: User attributes not preserved")
        return False

    # Verify asset entity
    assets = graph.find_entities(type="asset")
    if not assets:
        print(f"❌ FAIL: No asset entity found")
        return False

    btc = assets[0]
    print(f"\n✅ Asset entity loaded:")
    print(f"   ID: {btc.id}")
    print(f"   Label: {btc.label}")
    print(f"   Symbol: {btc.attributes.get('symbol')}")
    print(f"   Price: {btc.attributes.get('price')}")

    # Verify relation
    owns_rels = graph.get_relations(user.id, "out", "OWNS")
    if not owns_rels:
        print(f"❌ FAIL: No OWNS relation found")
        return False

    rel = owns_rels[0]
    print(f"\n✅ Relation loaded:")
    print(f"   Type: {rel.type}")
    print(f"   Amount: {rel.attributes.get('amount')}")
    print(f"   Entry price: {rel.attributes.get('entry_price')}")

    if rel.attributes.get("amount") != 0.5:
        print(f"❌ FAIL: Relation attributes not preserved")
        return False

    print(f"\n✅ ALL DATA PERSISTED CORRECTLY!")
    return True


def test_3_update_and_reload():
    """Test 3: Modifier et re-sauvegarder"""
    print("\n" + "=" * 70)
    print("TEST 3: UPDATE AND RELOAD")
    print("=" * 70)

    agent_id = "test_persistence"
    graph = get_entity_graph(agent_id)

    # Add new entity
    eth_id = graph.add_entity(
        type="asset",
        label="Ethereum",
        attributes={"symbol": "ETH", "price": 3005},
        importance=0.9,
        entity_id="asset_ETH_test",
    )
    print(f"✅ Nouveau asset ajouté: {eth_id}")

    print(f"\n📊 Graph avant save:")
    print(f"   Entities: {len(graph.entities)}")

    # Save again
    print(f"\n💾 Re-sauvegarde SQL...")
    try:
        graph.save_to_sql()
        print(f"✅ Sauvegarde réussie!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

    # Reload
    reset_entity_graph(agent_id)
    graph = get_entity_graph(agent_id, auto_load=True)

    print(f"\n📊 Graph après reload:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    if len(graph.entities) != 3:
        print(f"❌ FAIL: Expected 3 entities, got {len(graph.entities)}")
        return False

    # Verify ETH exists
    eth_entities = graph.find_entities(type="asset", filters={"symbol": "ETH"})
    if not eth_entities:
        print(f"❌ FAIL: ETH not found after reload")
        return False

    print(f"✅ ETH trouvé après reload: {eth_entities[0].label}")
    return True


def cleanup():
    """Cleanup test data"""
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)

    try:
        from backend.db.models import SessionLocal, AgentEntityNode, AgentEntityRelation

        with SessionLocal() as db:
            # Delete test data
            deleted_rels = db.query(AgentEntityRelation).filter_by(agent_id="test_persistence").delete()
            deleted_nodes = db.query(AgentEntityNode).filter_by(agent_id="test_persistence").delete()
            db.commit()

            print(f"✅ Cleanup: {deleted_nodes} entities, {deleted_rels} relations deleted")

    except Exception as e:
        print(f"⚠️ Cleanup error (non-fatal): {e}")


def main():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("TEST SQL PERSISTENCE - Phase 2.5")
    print("🧪" * 35)

    results = {}

    # Test 1: Save
    try:
        results["save"] = test_1_save_to_sql()
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        results["save"] = False

    # Test 2: Load
    try:
        results["load"] = test_2_load_from_sql()
    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        results["load"] = False

    # Test 3: Update
    try:
        results["update"] = test_3_update_and_reload()
    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        results["update"] = False

    # Cleanup
    cleanup()

    # Summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    total_pass = sum(results.values())
    total_tests = len(results)
    print(f"\nRésultat: {total_pass}/{total_tests} tests passés")

    if total_pass == total_tests:
        print("\n🎉 SQL PERSISTENCE VALIDÉE!")
        return 0
    else:
        print("\n⚠️ Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
