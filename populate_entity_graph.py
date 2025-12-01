#!/usr/bin/env python3
"""
Population initiale Entity Graph

Peuple le graphe avec :
- User default
- Assets top 10 crypto
- Positions d'exemple (si wallets disponibles)
- Patterns d'exemple (depuis signaux récents)
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.entity_memory import get_entity_graph, reset_entity_graph
from backend.services.trading_bot_service import get_trading_bot_service


async def populate_user(graph):
    """Créer entité utilisateur"""
    print("\n1️⃣ CRÉATION USER")
    print("-" * 70)

    # Check if user already exists
    existing = graph.find_entities(type="user", filters={"user_id": "default_user"})

    if existing:
        print(f"✅ User existe déjà: {existing[0].id}")
        return existing[0].id

    # Create default user
    user_id = graph.add_entity(
        type="user",
        label="Default User",
        attributes={
            "user_id": "default_user",
            "risk_profile": "moderate",
            "portfolio_value": 0.0,
            "preferences": {
                "notifications": True,
                "auto_trade": False,
            }
        },
        importance=1.0,
        tags=["primary"],
        entity_id="user_default",  # Fixed ID for consistency
    )

    print(f"✅ User créé: {user_id}")
    return user_id


async def populate_assets(graph):
    """Créer entités assets (top cryptos)"""
    print("\n2️⃣ CRÉATION ASSETS")
    print("-" * 70)

    # Top crypto assets with current prices (approximate)
    assets_data = [
        {"symbol": "BTC", "name": "Bitcoin", "price": 90500, "market_cap": 1.78e12},
        {"symbol": "ETH", "name": "Ethereum", "price": 3000, "market_cap": 360e9},
        {"symbol": "SOL", "name": "Solana", "price": 137, "market_cap": 64e9},
        {"symbol": "BNB", "name": "BNB", "price": 620, "market_cap": 90e9},
        {"symbol": "XRP", "name": "Ripple", "price": 0.60, "market_cap": 33e9},
        {"symbol": "ADA", "name": "Cardano", "price": 0.38, "market_cap": 13e9},
        {"symbol": "AVAX", "name": "Avalanche", "price": 37, "market_cap": 14e9},
        {"symbol": "DOT", "name": "Polkadot", "price": 6.5, "market_cap": 9e9},
        {"symbol": "MATIC", "name": "Polygon", "price": 0.85, "market_cap": 8e9},
        {"symbol": "LINK", "name": "Chainlink", "price": 15, "market_cap": 9e9},
    ]

    asset_ids = {}

    for asset_data in assets_data:
        # Check if exists
        existing = graph.find_entities(type="asset", filters={"symbol": asset_data["symbol"]})

        if existing:
            print(f"✅ Asset existe: {asset_data['symbol']} ({existing[0].id})")
            asset_ids[asset_data["symbol"]] = existing[0].id
            continue

        # Create asset
        asset_id = graph.add_entity(
            type="asset",
            label=asset_data["name"],
            attributes={
                "symbol": asset_data["symbol"],
                "name": asset_data["name"],
                "price": asset_data["price"],
                "market_cap": asset_data["market_cap"],
            },
            importance=0.9 if asset_data["symbol"] in ["BTC", "ETH", "SOL"] else 0.7,
            tags=["crypto", "top10"],
            entity_id=f"asset_{asset_data['symbol']}",  # Fixed ID
        )

        print(f"✅ Asset créé: {asset_data['symbol']} ({asset_id})")
        asset_ids[asset_data["symbol"]] = asset_id

    return asset_ids


async def populate_user_favorites(graph, user_id, asset_ids):
    """Créer relations WATCHES (favoris)"""
    print("\n3️⃣ CRÉATION FAVORIS")
    print("-" * 70)

    favorites = ["BTC", "ETH", "SOL"]

    for symbol in favorites:
        if symbol in asset_ids:
            # Check if relation exists
            existing_rels = graph.get_relations(user_id, "out", "WATCHES")
            already_watches = any(rel.target == asset_ids[symbol] for rel in existing_rels)

            if already_watches:
                print(f"✅ Favoris existe: {symbol}")
                continue

            # Create WATCHES relation
            graph.add_relation(
                source=user_id,
                target=asset_ids[symbol],
                type="WATCHES",
                attributes={"added_at": "2025-11-29"},
                strength=0.8,
            )

            print(f"✅ Favoris ajouté: {symbol}")


async def populate_demo_positions(graph, user_id, asset_ids):
    """Créer positions de démonstration (optionnel)"""
    print("\n4️⃣ CRÉATION POSITIONS DÉMO (optionnel)")
    print("-" * 70)

    demo_positions = [
        {"symbol": "BTC", "amount": 0.5, "entry_price": 45000},
        {"symbol": "ETH", "amount": 2.0, "entry_price": 2800},
    ]

    for pos in demo_positions:
        symbol = pos["symbol"]
        if symbol not in asset_ids:
            continue

        # Check if OWNS relation exists
        existing_rels = graph.get_relations(user_id, "out", "OWNS")
        already_owns = any(rel.target == asset_ids[symbol] for rel in existing_rels)

        if already_owns:
            print(f"✅ Position existe: {symbol}")
            continue

        # Create OWNS relation
        graph.add_relation(
            source=user_id,
            target=asset_ids[symbol],
            type="OWNS",
            attributes={
                "amount": pos["amount"],
                "entry_price": pos["entry_price"],
                "entry_date": "2025-01-15",
            },
            strength=1.0,
        )

        # Calculate PnL
        asset = graph.get_entity(asset_ids[symbol])
        current_price = asset.attributes.get("price", 0)
        entry_price = pos["entry_price"]
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        print(f"✅ Position créée: {pos['amount']} {symbol} @ ${entry_price:,.0f} → ${current_price:,.0f} ({pnl_pct:+.1f}%)")


async def populate_patterns_from_signals(graph, asset_ids):
    """Créer patterns depuis signaux récents (si disponibles)"""
    print("\n5️⃣ CRÉATION PATTERNS (depuis signaux)")
    print("-" * 70)

    try:
        bot_service = get_trading_bot_service()

        if not bot_service:
            print("⚠️ Bot service non disponible, skip patterns")
            return

        # Get recent signals
        if hasattr(bot_service, 'signals_queue') and bot_service.signals_queue:
            signals = bot_service.signals_queue[-10:]  # Last 10
        else:
            signals = bot_service.get_signals(limit=10)

        if not signals:
            print("⚠️ Aucun signal disponible, skip patterns")
            return

        print(f"📊 {len(signals)} signaux trouvés")

        # Group signals by pattern type
        pattern_counts = {}
        for sig in signals:
            event = sig.get('event', 'unknown')
            symbol = sig.get('ticker', sig.get('symbol', 'UNKNOWN'))

            if event not in pattern_counts:
                pattern_counts[event] = []
            pattern_counts[event].append((symbol, sig))

        # Create pattern entities
        for pattern_type, occurrences in pattern_counts.items():
            # Take first occurrence as representative
            symbol, sig = occurrences[0]

            # Check if pattern already exists
            existing = graph.find_entities(
                type="pattern",
                filters={"pattern_type": pattern_type, "asset": symbol}
            )

            if existing:
                print(f"✅ Pattern existe: {pattern_type} on {symbol}")
                continue

            # Create pattern entity
            pattern_id = graph.add_entity(
                type="pattern",
                label=f"{pattern_type} on {symbol}",
                attributes={
                    "pattern_type": pattern_type,
                    "asset": symbol,
                    "confidence": sig.get('confidence', 70) / 100.0,
                    "timeframe": "4h",
                    "active": True,
                },
                importance=0.7,
                tags=["detected", "synthetic" if sig.get('synthetic') else "real"],
            )

            print(f"✅ Pattern créé: {pattern_type} on {symbol} ({pattern_id})")

            # Create DETECTED relation (Asset -> Pattern)
            if symbol in asset_ids or f"asset_{symbol}" in graph.entities:
                asset_id = asset_ids.get(symbol) or f"asset_{symbol}"

                graph.add_relation(
                    source=asset_id,
                    target=pattern_id,
                    type="FOLLOWS",
                    attributes={"detected_at": sig.get('timestamp', '')},
                    strength=0.7,
                )

                print(f"   → Relation: {symbol} FOLLOWS {pattern_type}")

    except Exception as e:
        print(f"❌ Erreur création patterns: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Peuple le graphe d'entités"""
    print("=" * 70)
    print("POPULATION ENTITY GRAPH")
    print("=" * 70)

    # Get or reset graph
    agent_id = "fededge_core_v3"

    # Ask user if reset
    response = input("\n⚠️ Reset graph existant? (y/N): ").strip().lower()
    if response == 'y':
        reset_entity_graph(agent_id)
        print("✅ Graph reset")

    graph = get_entity_graph(agent_id)

    print(f"\n📊 Graph actuel:")
    print(f"   Entities: {len(graph.entities)}")
    print(f"   Relations: {len(graph.relations)}")

    # Populate
    try:
        # 1. User
        user_id = await populate_user(graph)

        # 2. Assets
        asset_ids = await populate_assets(graph)

        # 3. Favorites
        await populate_user_favorites(graph, user_id, asset_ids)

        # 4. Demo positions (optional)
        create_demo = input("\n💰 Créer positions démo? (y/N): ").strip().lower()
        if create_demo == 'y':
            await populate_demo_positions(graph, user_id, asset_ids)

        # 5. Patterns from signals
        await populate_patterns_from_signals(graph, asset_ids)

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)

    print(f"📊 Entities: {len(graph.entities)}")
    print(f"   - Users: {len(graph.find_entities(type='user'))}")
    print(f"   - Assets: {len(graph.find_entities(type='asset'))}")
    print(f"   - Patterns: {len(graph.find_entities(type='pattern'))}")

    print(f"\n🔗 Relations: {len(graph.relations)}")

    # User positions
    positions = graph.get_user_positions(user_id)
    if positions:
        print(f"\n💰 Positions:")
        for pos in positions:
            pnl_pct = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
            print(f"   - {pos['symbol']}: {pos['amount']} @ ${pos['entry_price']:,.0f} → ${pos['current_price']:,.0f} ({pnl_pct:+.1f}%)")

    print(f"\n✅ Population terminée!")

    # Save to SQL (Phase 2.5)
    print(f"\n💾 Sauvegarde SQL...")
    try:
        graph.save_to_sql()
        print(f"✅ Sauvegarde SQL réussie!")
        print(f"   Le graphe persistera entre les redémarrages")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde SQL: {e}")
        print(f"   Le graphe reste en mémoire uniquement")

    print(f"\n📝 Le graphe est maintenant prêt pour Phase 2.5 (avec persistence SQL)")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
