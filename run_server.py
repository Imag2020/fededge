#!/usr/bin/env python3

if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    from dotenv import load_dotenv

    load_dotenv()  # ← Ajouter cette ligne

    # Assurer que le PYTHONPATH est correct
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Initialize FedEdge Node Client
    try:
        from fededge_node_client import FedEdgeNodeClient
        node_client = FedEdgeNodeClient()
        print("🔧 FedEdge Node Client initialized")
        node_client.start_session()
        print("✅ Node session started")
    except Exception as e:
        print(f"⚠️  FedEdge Node Client failed to initialize: {e}")
        print("   Application will run without node tracking")

    # Lancer le serveur FastAPI
    # reload=False en production pour éviter les déconnexions WebSocket
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # IMPORTANT: désactivé pour stabilité WebSocket
        log_level="info"
    )
