"""
Scheduler Asynchrone Non-Bloquant pour HIVE AI
- Exécute toutes les tâches dans des threads séparés
- Implémente un système de queue pour éviter la surcharge
- Timeout automatique pour éviter les tâches bloquées
- Monitoring en temps réel des performances
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor as APSThreadPoolExecutor

from .tasks import analysis_tasks
from .tasks import trading_tasks
from .tasks import registry_tasks

logger = logging.getLogger(__name__)

# Configuration globale
MAX_CONCURRENT_TASKS = 3  # Max 3 tâches simultanées
TASK_TIMEOUT = 300  # 5 minutes timeout par défaut
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)

# Stats globales
task_stats = {
    "total_executed": 0,
    "total_failed": 0,
    "total_timeout": 0,
    "average_duration": 0,
    "last_task_time": None,
    "active_tasks": 0,
}


class NonBlockingScheduler:
    """
    Scheduler non-bloquant qui exécute toutes les tâches en arrière-plan
    sans bloquer l'event loop principal.
    """

    def __init__(self):
        # Configurer le scheduler avec ThreadPoolExecutor
        self.scheduler = AsyncIOScheduler(
            executors={
                'default': APSThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)
            },
            job_defaults={
                'coalesce': True,  # Fusionner les exécutions multiples
                'max_instances': 1,  # Max 1 instance par job
                'misfire_grace_time': 60,  # Tolérance de 60s pour les retards
            }
        )
        self.task_queue = asyncio.Queue(maxsize=10)
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def _execute_task_safe(
        self,
        task_func: Callable,
        task_id: str,
        timeout: int = TASK_TIMEOUT,
    ) -> Optional[Any]:
        """
        Exécute une tâche de manière sécurisée avec timeout et error handling.

        Args:
            task_func: Fonction à exécuter
            task_id: Identifiant unique de la tâche
            timeout: Timeout en secondes

        Returns:
            Résultat de la tâche ou None en cas d'erreur
        """
        start_time = time.time()
        task_stats["active_tasks"] += 1

        try:
            logger.info(f"🚀 [Scheduler] Démarrage de la tâche: {task_id}")

            # Exécuter la tâche dans un thread séparé avec timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, task_func),
                timeout=timeout
            )

            duration = time.time() - start_time
            task_stats["total_executed"] += 1
            task_stats["last_task_time"] = datetime.now().isoformat()

            # Mise à jour de la moyenne
            current_avg = task_stats["average_duration"]
            total = task_stats["total_executed"]
            task_stats["average_duration"] = (
                (current_avg * (total - 1) + duration) / total
            )

            logger.info(
                f"✅ [Scheduler] Tâche terminée: {task_id} "
                f"(durée: {duration:.2f}s)"
            )

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            task_stats["total_timeout"] += 1
            logger.error(
                f"⏱️ [Scheduler] Timeout de la tâche: {task_id} "
                f"(après {duration:.2f}s, limite: {timeout}s)"
            )
            return None

        except Exception as e:
            duration = time.time() - start_time
            task_stats["total_failed"] += 1
            logger.error(
                f"❌ [Scheduler] Erreur dans la tâche: {task_id} "
                f"(après {duration:.2f}s): {e}",
                exc_info=True
            )
            return None

        finally:
            task_stats["active_tasks"] -= 1

    def add_job_safe(
        self,
        func: Callable,
        trigger: str,
        task_id: str,
        timeout: int = TASK_TIMEOUT,
        **trigger_args
    ):
        """
        Ajoute un job de manière sécurisée avec wrapper non-bloquant.

        Args:
            func: Fonction à exécuter (synchrone ou asynchrone)
            trigger: Type de trigger ('interval', 'cron', 'date')
            task_id: ID unique du job
            timeout: Timeout en secondes (note: non implémenté pour l'instant)
            **trigger_args: Arguments du trigger (minutes, hour, etc.)
        """

        # Créer un wrapper qui gère à la fois sync et async
        def smart_wrapper():
            """Wrapper intelligent qui gère les fonctions sync et async"""
            start_time = time.time()
            task_stats["active_tasks"] += 1

            try:
                logger.info(f"🚀 [Scheduler] Démarrage: {task_id}")

                # Détecter si la fonction est async ou sync
                if asyncio.iscoroutinefunction(func):
                    # Fonction async : créer un nouvel event loop dans ce thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(func())
                    finally:
                        loop.close()
                else:
                    # Fonction sync : exécuter directement
                    result = func()

                duration = time.time() - start_time
                task_stats["total_executed"] += 1
                task_stats["last_task_time"] = datetime.now().isoformat()

                # Mise à jour de la moyenne
                current_avg = task_stats["average_duration"]
                total = task_stats["total_executed"]
                task_stats["average_duration"] = (
                    (current_avg * (total - 1) + duration) / total
                )

                logger.info(
                    f"✅ [Scheduler] Terminé: {task_id} "
                    f"(durée: {duration:.2f}s)"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                task_stats["total_failed"] += 1
                logger.error(
                    f"❌ [Scheduler] Erreur: {task_id} "
                    f"(après {duration:.2f}s): {e}",
                    exc_info=True
                )
                return None

            finally:
                task_stats["active_tasks"] -= 1

        # Ajouter le job au scheduler
        # APScheduler va exécuter smart_wrapper dans le ThreadPoolExecutor
        self.scheduler.add_job(
            smart_wrapper,
            trigger=trigger,
            id=task_id,
            **trigger_args
        )

        logger.info(f"📋 [Scheduler] Job ajouté: {task_id} ({trigger})")

    def start(self):
        """Démarre le scheduler non-bloquant"""
        self.scheduler.start()
        logger.info("🚀 Scheduler non-bloquant démarré")

    def shutdown(self, wait: bool = True):
        """Arrête le scheduler"""
        self.scheduler.shutdown(wait=wait)
        executor.shutdown(wait=wait)
        logger.info("🛑 Scheduler arrêté")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du scheduler"""
        return {
            **task_stats,
            "scheduled_jobs": len(self.scheduler.get_jobs()),
            "running_tasks": len(self.running_tasks),
        }


# Instance globale du scheduler
_scheduler_instance: Optional[NonBlockingScheduler] = None


def start_non_blocking_scheduler() -> NonBlockingScheduler:
    """
    Démarre le scheduler non-bloquant avec toutes les tâches configurées.

    Returns:
        Instance du NonBlockingScheduler
    """
    global _scheduler_instance

    if _scheduler_instance is not None:
        logger.warning("⚠️ Scheduler déjà démarré, réutilisation de l'instance existante")
        return _scheduler_instance

    scheduler = NonBlockingScheduler()

    # ========================================================================
    # TÂCHES DE DONNÉES EN TEMPS RÉEL (PRIORITÉ HAUTE)
    # ========================================================================

    # Prix crypto toutes les 15 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.collect_and_broadcast_prices,
        trigger='interval',
        task_id='price_update',
        timeout=60,  # 1 minute max
        minutes=5
    )

    # News crypto toutes les 30 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.collect_and_broadcast_news,
        trigger='interval',
        task_id='news_update',
        timeout=120,  # 2 minutes max
        minutes=10
    )

    # Contexte mondial toutes les 60 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.update_world_context,
        trigger='interval',
        task_id='world_context_update',
        timeout=180,  # 3 minutes max
        minutes=15
    )

    # Performances toutes les 30 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.update_wallet_performance,
        trigger='interval',
        task_id='performance_update',
        timeout=120,  # 2 minutes max
        minutes=30
    )

    # Mise à jour des trades ouverts toutes les 30 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.update_open_trades,
        trigger='interval',
        task_id='trades_update',
        timeout=60,  # 1 minute max
        minutes=30
    )

    # Scan automatique des signaux de trading toutes les 30 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        analysis_tasks.scan_trading_signals,
        trigger='interval',
        task_id='trading_signals_scan',
        timeout=180,  # 3 minutes max
        minutes=30
    )

    # ========================================================================
    # TÂCHES DE SIMULATIONS (FRÉQUENCE RÉDUITE)
    # ========================================================================

    # Tâche de simulations dynamiques toutes les 30 minutes (optimisé pour CPU)
    scheduler.add_job_safe(
        trading_tasks.run_all_simulations,
        trigger='interval',
        task_id='simulations_runner',
        timeout=240,  # 4 minutes max
        minutes=30
    )

    logger.info("✅ Auto-scheduling des simulations ACTIVÉ (toutes les 30 minutes - optimisé CPU)")

    # ========================================================================
    # TÂCHES DE MAINTENANCE
    # ========================================================================

    # Mise à jour du registre crypto (une fois par jour à 2h du matin)
    scheduler.add_job_safe(
        registry_tasks.update_crypto_registry_task,
        trigger='cron',
        task_id='crypto_registry_update',
        timeout=600,  # 10 minutes max
        hour=2,
        minute=0
    )

    # ========================================================================
    # TÂCHES INITIALES (AVEC DÉLAIS)
    # ========================================================================

    # Bootstrap news en DB si vide (immédiatement)
    bootstrap_time = datetime.now() + timedelta(seconds=2)
    scheduler.add_job_safe(
        analysis_tasks.ensure_initial_news_in_db,
        trigger='date',
        task_id='bootstrap_news',
        timeout=60,
        run_date=bootstrap_time
    )

    # Prix immédiatement (5 secondes)
    start_time = datetime.now() + timedelta(seconds=5)
    scheduler.add_job_safe(
        analysis_tasks.collect_and_broadcast_prices,
        trigger='date',
        task_id='initial_price_collection',
        timeout=60,
        run_date=start_time
    )

    # News après 15 secondes
    news_start_time = datetime.now() + timedelta(seconds=15)
    scheduler.add_job_safe(
        analysis_tasks.collect_and_broadcast_news,
        trigger='date',
        task_id='initial_news_collection',
        timeout=120,
        run_date=news_start_time
    )

    # Performances après 30 secondes
    perf_start_time = datetime.now() + timedelta(seconds=30)
    scheduler.add_job_safe(
        analysis_tasks.update_wallet_performance,
        trigger='date',
        task_id='initial_performance',
        timeout=120,
        run_date=perf_start_time
    )

    # Contexte mondial après 60 secondes
    context_start_time = datetime.now() + timedelta(seconds=60)
    scheduler.add_job_safe(
        analysis_tasks.update_world_context,
        trigger='date',
        task_id='initial_world_context',
        timeout=180,
        run_date=context_start_time
    )

    # Signaux de trading après 90 secondes
    signals_start_time = datetime.now() + timedelta(seconds=90)
    scheduler.add_job_safe(
        analysis_tasks.scan_trading_signals,
        trigger='date',
        task_id='initial_trading_signals_scan',
        timeout=180,
        run_date=signals_start_time
    )

    # Démarrer le scheduler
    scheduler.start()

    # Afficher l'état initial
    logger.info("🚀 Scheduler non-bloquant démarré avec succès")
    logger.info(f"📋 {len(scheduler.scheduler.get_jobs())} tâches planifiées")
    logger.info(f"⚙️ Max {MAX_CONCURRENT_TASKS} tâches simultanées")
    logger.info(f"⏱️ Timeout par défaut: {TASK_TIMEOUT}s")

    # Log des jobs planifiés
    for job in scheduler.scheduler.get_jobs():
        next_run = job.next_run_time
        next_run_str = next_run.strftime('%H:%M:%S') if next_run else "N/A"
        logger.info(f"  - {job.id}: {job.trigger} (prochain: {next_run_str})")

    # Afficher l'état des simulations
    try:
        from .db.models import SessionLocal
        from .db import crud

        db = SessionLocal()
        try:
            simulations = crud.get_simulations(db, active_only=True)
            logger.info("📊 État des simulations au démarrage:")
            for sim in simulations:
                status = "✅ ACTIVE" if sim.is_active else "⏸️ INACTIVE"
                running = "🏃 EN COURS" if sim.is_running else "🛑 ARRÊTÉE"
                last_run = (
                    sim.last_run_at.strftime('%Y-%m-%d %H:%M:%S')
                    if sim.last_run_at
                    else "Jamais"
                )
                next_run = (
                    sim.next_run_at.strftime('%Y-%m-%d %H:%M:%S')
                    if sim.next_run_at
                    else "Non planifiée"
                )
                logger.info(
                    f"  - {sim.name}: {status} | {running} | "
                    f"Dernier: {last_run} | Prochain: {next_run}"
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"⚠️ Erreur récupération état simulations: {e}")

    _scheduler_instance = scheduler
    return scheduler


def get_scheduler() -> Optional[NonBlockingScheduler]:
    """Retourne l'instance du scheduler si démarré"""
    return _scheduler_instance


def get_scheduler_stats() -> Dict[str, Any]:
    """Retourne les statistiques du scheduler"""
    if _scheduler_instance is None:
        return {"error": "Scheduler not started"}
    return _scheduler_instance.get_stats()
