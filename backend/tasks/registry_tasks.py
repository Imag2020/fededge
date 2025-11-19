"""
Tâches planifiées pour la maintenance du registre crypto
"""

import asyncio
from ..utils.crypto_registry import get_crypto_registry
from ..utils.debug_logger import get_debug_logger
from ..websocket_manager import get_websocket_manager

async def update_crypto_registry_task():
    """
    Tâche planifiée pour mettre à jour le registre crypto
    Exécutée une fois par jour
    """
    debug = get_debug_logger()
    
    try:
        debug.log_step('REGISTRY_UPDATE', "🔄 Début mise à jour registre crypto")
        
        # Récupérer le registre et forcer la mise à jour si nécessaire
        registry = get_crypto_registry()
        stats_before = registry.get_registry_stats()
        
        # Mettre à jour si le cache est ancien (plus de 12 heures)
        if stats_before['age_hours'] > 12:
            debug.log_step('REGISTRY_UPDATE', f"🔄 Cache ancien ({stats_before['age_hours']:.1f}h), mise à jour...")
            
            success = registry.refresh_registry()
            if success:
                stats_after = registry.get_registry_stats()
                debug.log_step('REGISTRY_UPDATE', 
                    f"✅ Registre mis à jour: {stats_after['total_assets']} assets", {
                        'before_age_hours': stats_before['age_hours'],
                        'after_age_hours': stats_after['age_hours'],
                        'source': stats_after['source']
                    })
                
                # Notifier le frontend
                await broadcast_registry_update(stats_after)
            else:
                debug.log_error('REGISTRY_UPDATE', "❌ Échec mise à jour registre")
        else:
            debug.log_step('REGISTRY_UPDATE', 
                f"✅ Registre à jour ({stats_before['age_hours']:.1f}h)")
        
    except Exception as e:
        debug.log_error('REGISTRY_UPDATE', f"❌ Erreur mise à jour registre: {str(e)}", e)

async def broadcast_registry_update(stats):
    """Diffuse une notification de mise à jour du registre au frontend"""
    try:
        ws_manager = get_websocket_manager()
        
        message = {
            "type": "registry_updated",
            "payload": {
                "total_assets": stats['total_assets'],
                "source": stats['source'],
                "last_updated": stats['last_updated'],
                "age_hours": stats['age_hours'],
                "top_assets": stats['sample_assets'][:5]
            }
        }
        
        await ws_manager.broadcast(message)
        print(f"📊 Notification registre diffusée: {stats['total_assets']} assets")
        
    except Exception as e:
        print(f"❌ Erreur diffusion mise à jour registre: {e}")

async def get_registry_health_check():
    """
    Vérifie la santé du registre crypto
    Retourne des métriques pour le monitoring
    """
    try:
        registry = get_crypto_registry()
        stats = registry.get_registry_stats()
        
        # Calculer un score de santé
        health_score = 100
        
        if stats['age_hours'] > 24:
            health_score -= 30  # Données anciennes
        elif stats['age_hours'] > 12:
            health_score -= 15
        
        if stats['total_assets'] < 200:
            health_score -= 20  # Pas assez d'assets
        
        if stats['source'] == 'fallback':
            health_score -= 50  # Mode dégradé
        
        health_status = 'excellent' if health_score >= 90 else \
                       'good' if health_score >= 70 else \
                       'warning' if health_score >= 50 else 'critical'
        
        return {
            'health_score': health_score,
            'health_status': health_status,
            'stats': stats,
            'recommendations': _get_health_recommendations(stats, health_score)
        }
        
    except Exception as e:
        return {
            'health_score': 0,
            'health_status': 'critical',
            'error': str(e),
            'recommendations': ['Redémarrer le service', 'Vérifier la connectivité API']
        }

def _get_health_recommendations(stats, health_score):
    """Génère des recommandations basées sur la santé du registre"""
    recommendations = []
    
    if stats['age_hours'] > 24:
        recommendations.append('Mettre à jour le registre (données > 24h)')
    
    if stats['total_assets'] < 200:
        recommendations.append('Augmenter le nombre d\'assets supportés')
    
    if stats['source'] == 'fallback':
        recommendations.append('Restaurer la connexion à l\'API CoinGecko')
    
    if health_score >= 90:
        recommendations.append('Registre en parfait état ✅')
    
    return recommendations