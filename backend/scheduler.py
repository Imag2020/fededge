from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .tasks import analysis_tasks # Importe le nouveau module de tâches d'analyse
from .tasks import trading_tasks # Importe le nouveau module de tâches d'analyse
from .tasks import registry_tasks # Importe les tâches de maintenance du registre

'''
# Vérifier si les anciennes tâches de prix/news existent encore
try:
    from .tasks import data_tasks
    HAS_DATA_TASKS = True
except ImportError:
    HAS_DATA_TASKS = False
    print("⚠️ Anciennes tâches data_tasks non trouvées, création de nouvelles tâches de prix/news")
'''

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Tâches de données en temps réel (PRIORITÉ HAUTE)
    
    # Prix crypto toutes les 10 minutes (optimisé avec cache)
    scheduler.add_job(
        analysis_tasks.collect_and_broadcast_prices,
        'interval',
        minutes=10,
        id='price_update'
    )
    
    # News crypto toutes les 30 minutes
    scheduler.add_job(
        analysis_tasks.collect_and_broadcast_news,
        'interval',
        minutes=10,
        id='news_update'
    )
    
    # Contexte mondial toutes les 30 minutes (après avoir accumulé assez d'articles)
    scheduler.add_job(
        analysis_tasks.update_world_context,
        'interval',
        minutes=20,
        id='world_context_update'
    )
    
    # Performances toutes les 20 minutes (réduit pour éviter rate limits)
    scheduler.add_job(
        analysis_tasks.update_wallet_performance,
        'interval',
        minutes=8,
        id='performance_update'
    )
    
    # Mise à jour des trades ouverts toutes les 10 minutes (pour expiration automatique)
    scheduler.add_job(
        analysis_tasks.update_open_trades,
        'interval',
        minutes=12,
        id='trades_update'
    )
    
    # Scan automatique des signaux de trading toutes les 3 minutes
    scheduler.add_job(
        analysis_tasks.scan_trading_signals,
        'interval',
        minutes=3,
        id='trading_signals_scan'
    )

   
    
    # Tâche de simulations dynamiques - Réactivée avec fréquence très réduite pour éviter blocages
    scheduler.add_job(
        trading_tasks.run_all_simulations,
        'interval',
        minutes=5,  # Fréquence très réduite pour éviter le blocage des LLM
        id='simulations_runner'
    )
    print("✅ Auto-scheduling des simulations ACTIVÉ (toutes les 15 minutes)")
    
  
    
    # Mise à jour du registre crypto (une fois par jour à 2h du matin)
    scheduler.add_job(
        registry_tasks.update_crypto_registry_task,
        'cron',
        hour=2,
        minute=0,
        id='crypto_registry_update'
    )
    
    # Tâches initiales - réactivées avec délai pour éviter les blocages
    # Ne pas déclencher immédiatement, mais après 30 secondes pour laisser le temps au serveur de démarrer
    import datetime
    from datetime import timedelta

    # FORCER la collecte des prix IMMÉDIATEMENT au démarrage (5 secondes pour laisser le serveur s'initialiser)
    price_start_time = datetime.datetime.now() + timedelta(seconds=5)
    scheduler.add_job(analysis_tasks.collect_and_broadcast_prices, 'date', run_date=price_start_time, id='initial_price_collection')

    start_time = datetime.datetime.now() + timedelta(seconds=30)
    scheduler.add_job(analysis_tasks.update_wallet_performance, 'date', run_date=start_time, id='initial_performance')

    # FORCER la collecte des actualités crypto au démarrage (après 15 secondes)
    news_start_time = datetime.datetime.now() + timedelta(seconds=15)
    scheduler.add_job(analysis_tasks.collect_and_broadcast_news, 'date', run_date=news_start_time, id='initial_news_collection')

    # Mise à jour initiale du contexte mondial après 60 secondes (pour laisser le temps aux articles de se collecter)
    context_start_time = datetime.datetime.now() + timedelta(seconds=60)
    scheduler.add_job(analysis_tasks.update_world_context, 'date', run_date=context_start_time, id='initial_world_context')
    
    # Premier scan de signaux de trading après 90 secondes (pour laisser le temps au bot de s'initialiser)
    signals_start_time = datetime.datetime.now() + timedelta(seconds=90)
    scheduler.add_job(analysis_tasks.scan_trading_signals, 'date', run_date=signals_start_time, id='initial_trading_signals_scan')
    
    # Les autres tâches restent désactivées pour éviter les blocages réseau au démarrage
    #scheduler.add_job(analysis_tasks.generate_demo_signal, 'date', id='initial_demo_signal')
    # scheduler.add_job(analysis_tasks.generate_test_signal, 'date', id='initial_test_signal')
    
    scheduler.start()
    print("🚀 Scheduler démarré avec les nouvelles tâches d'analyse IA.")
    print("📋 Tâches planifiées:")
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        next_run_str = next_run.strftime('%H:%M:%S') if next_run else "N/A"
        print(f"  - {job.id}: {job.trigger} (prochain run: {next_run_str})")
    
    # Afficher l'état des simulations au démarrage
    from .db.models import SessionLocal
    from .db import crud
    db = SessionLocal()
    try:
        simulations = crud.get_simulations(db, active_only=True)
        print("📊 État des simulations au démarrage:")
        for sim in simulations:
            status = "✅ ACTIVE" if sim.is_active else "⏸️ INACTIVE"
            running = "🏃 EN COURS" if sim.is_running else "🛑 ARRÊTÉE"
            last_run = sim.last_run_at.strftime('%Y-%m-%d %H:%M:%S') if sim.last_run_at else "Jamais exécutée"
            next_run = sim.next_run_at.strftime('%Y-%m-%d %H:%M:%S') if sim.next_run_at else "Non planifiée"
            print(f"  - {sim.name}: {status} | {running} | Dernier: {last_run} | Prochain: {next_run}")
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération de l'état des simulations: {e}")
    finally:
        db.close()

def start_scheduler():
    print("bye bye")
