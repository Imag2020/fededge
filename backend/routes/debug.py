"""
Debug Routes
Handles debugging and diagnostic endpoints
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["debug"])


@router.get("/debug/datasets/stats")
async def get_datasets_stats():
    """Retourne des stats basiques sur les 3 datasets (rows, last timestamp)"""
    try:
        from ..db.trading_datasets import trading_datasets
        stats = trading_datasets.get_basic_stats_all()
        return {"status": "success", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/debug/datasets/{dataset_type}/latest")
async def get_dataset_latest(dataset_type: str, limit: int = 20):
    """
    Retourne les dernières lignes d'un dataset ('world_state' | 'candidates' | 'decider')
    """
    try:
        from ..db.trading_datasets import trading_datasets
        rows = trading_datasets.get_latest_rows(dataset_type=dataset_type, limit=limit)
        return {"status": "success", "dataset": dataset_type, "rows": rows, "total": len(rows)}
    except Exception as e:
        return {"status": "error", "message": str(e), "rows": []}


@router.get("/debug/datasets/{dataset_type}/session/{session_id}")
async def get_dataset_session(dataset_type: str, session_id: str):
    """Retourne le contenu d'une session spécifique dans un dataset."""
    try:
        from ..db.trading_datasets import trading_datasets
        data = trading_datasets.get_session_data(session_id=session_id, dataset_type=dataset_type)
        if not data:
            return {"status": "error", "message": "Session non trouvée", "data": None}
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}


@router.get("/registry/status")
async def get_registry_status():
    """Retourne le statut du registre crypto"""
    from ..utils.asset_helpers import get_registry_status
    try:
        status = get_registry_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur statut registre: {str(e)}")


@router.get("/scheduler/stats")
async def get_scheduler_stats():
    """
    Retourne les statistiques du scheduler non-bloquant
    - Nombre de tâches exécutées, échouées, timeout
    - Durée moyenne d'exécution
    - Nombre de tâches actives
    - Liste des jobs planifiés
    """
    try:
        # Essayer d'importer le scheduler async
        try:
            from ..scheduler_async import get_scheduler_stats, get_scheduler
            scheduler = get_scheduler()

            if scheduler is None:
                return {
                    "success": False,
                    "message": "Scheduler not started or using non-async version",
                    "stats": None
                }

            stats = get_scheduler_stats()

            # Ajouter la liste des jobs
            jobs_info = []
            for job in scheduler.scheduler.get_jobs():
                next_run = job.next_run_time
                jobs_info.append({
                    "id": job.id,
                    "trigger": str(job.trigger),
                    "next_run": next_run.isoformat() if next_run else None,
                })

            stats["jobs"] = jobs_info

            return {
                "success": True,
                "stats": stats
            }

        except ImportError:
            return {
                "success": False,
                "message": "Async scheduler not available, using standard scheduler",
                "stats": None
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur récupération stats scheduler: {str(e)}"
        )


@router.post("/test-agent-consciousness")
async def test_agent_consciousness():
    """Test Agent V3 consciousness updates with sample events"""
    from ..agent_event_router import get_event_router
    import asyncio

    router_instance = get_event_router()
    if not router_instance:
        return {
            "success": False,
            "error": "Event router not initialized"
        }

    try:
        # Test news event
        await router_instance.route_news_event({
            "title": "🧪 TEST: Bitcoin reaches $94K milestone",
            "summary": "This is a test news article to verify consciousness updates",
            "url": "https://test.com/btc",
            "source": "test_api",
            "published_at": "2025-11-16T19:30:00",
            "category": "crypto"
        })

        await asyncio.sleep(1)

        # Test market update
        await router_instance.route_market_update({
            "BTC": {"price": 94157, "change_24h": -1.98},
            "ETH": {"price": 3066, "change_24h": -4.29}
        })

        return {
            "success": True,
            "message": "Test events sent to Agent V3. Check frontend consciousness display!"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

