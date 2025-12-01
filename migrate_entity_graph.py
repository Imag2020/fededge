#!/usr/bin/env python3
"""
Migration SQL pour Entity Graph (Phase 2.5)

Crée les tables:
- agent_entity_nodes
- agent_entity_relations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.db.models import (
    Base,
    engine,
    AgentEntityNode,
    AgentEntityRelation,
)
from sqlalchemy import inspect


def check_tables_exist():
    """Vérifie si les tables existent déjà"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    entity_nodes_exists = "agent_entity_nodes" in existing_tables
    entity_relations_exists = "agent_entity_relations" in existing_tables

    return entity_nodes_exists, entity_relations_exists


def migrate():
    """Exécute la migration"""
    print("=" * 70)
    print("MIGRATION SQL - ENTITY GRAPH (Phase 2.5)")
    print("=" * 70)

    # Check existing tables
    nodes_exist, relations_exist = check_tables_exist()

    print(f"\n📊 État actuel:")
    print(f"   agent_entity_nodes: {'✅ Existe' if nodes_exist else '❌ Nexiste pas'}")
    print(f"   agent_entity_relations: {'✅ Existe' if relations_exist else '❌ Nexiste pas'}")

    if nodes_exist and relations_exist:
        print(f"\n⚠️ Les tables existent déjà!")
        response = input("Voulez-vous recréer les tables? (cela supprimera toutes les données) (y/N): ").strip().lower()

        if response != 'y':
            print("❌ Migration annulée")
            return False

        print("\n🗑️ Suppression des tables existantes...")
        AgentEntityRelation.__table__.drop(engine, checkfirst=True)
        AgentEntityNode.__table__.drop(engine, checkfirst=True)
        print("✅ Tables supprimées")

    # Create tables
    print(f"\n🔨 Création des tables...")

    # Create only the entity graph tables (not all Base tables)
    AgentEntityNode.__table__.create(engine, checkfirst=True)
    AgentEntityRelation.__table__.create(engine, checkfirst=True)

    print("✅ Tables créées:")
    print("   - agent_entity_nodes")
    print("   - agent_entity_relations")

    # Verify
    nodes_exist, relations_exist = check_tables_exist()

    if nodes_exist and relations_exist:
        print(f"\n✅ MIGRATION RÉUSSIE!")
        print(f"\n📊 Schéma:")
        print_schema()
        return True
    else:
        print(f"\n❌ MIGRATION ÉCHOUÉE")
        return False


def print_schema():
    """Affiche le schéma des tables"""
    inspector = inspect(engine)

    for table_name in ["agent_entity_nodes", "agent_entity_relations"]:
        print(f"\n📋 Table: {table_name}")
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)

        print(f"   Colonnes ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"      - {col['name']}: {col['type']} {nullable}")

        print(f"   Indexes ({len(indexes)}):")
        for idx in indexes:
            cols = ", ".join(idx['column_names'])
            unique = "UNIQUE" if idx.get('unique') else ""
            print(f"      - {idx['name']}: ({cols}) {unique}")


def main():
    """Main"""
    try:
        success = migrate()

        if success:
            print("\n" + "=" * 70)
            print("🎉 Migration Phase 2.5 terminée!")
            print("=" * 70)
            print("\nProchaines étapes:")
            print("  1. Implémenter save/load dans EntityGraph")
            print("  2. Tester persistence")
            print("  3. Mettre à jour populate script")
            return 0
        else:
            return 1

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
