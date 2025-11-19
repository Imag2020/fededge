"""
Rate Limiter global pour CoinGecko API
Limite stricte: 40 appels/minute (1 appel toutes les 1.5 secondes)
"""

import time
import threading
from typing import Optional, Dict, Any
import json
import os
from datetime import datetime, timedelta
import hashlib

from backend.config.paths import CACHE_DIR

class CoinGeckoRateLimiter:
    """Rate limiter global pour CoinGecko API avec cache intelligent"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_interval = 2.0  # 2 secondes entre chaque appel (30 appels/minute max)
        self.request_count = 0
        self.window_start = time.time()
        self.window_duration = 60.0  # Fenêtre d'1 minute
        self.max_requests_per_window = 35  # Limite à 35/minute pour être sûr
        
        # Cache global
        self.cache = {}
        self.cache_dir = str(CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # TTL par type de données
        self.cache_ttl = {
            'simple_price': 300,  # 5 minutes pour les prix simples (optimisé)
            'coins_markets': 900,  # 15 minutes pour market overview
            'market_chart': 900,  # 15 minutes pour les graphiques
            'asset_info': 3600,   # 1 heure pour les infos d'assets
        }
    
    def can_make_request(self) -> bool:
        """Vérifie si on peut faire une requête maintenant"""
        with self.lock:
            current_time = time.time()
            
            # Réinitialiser le compteur si la fenêtre est expirée
            if current_time - self.window_start >= self.window_duration:
                self.request_count = 0
                self.window_start = current_time
            
            # Vérifier les limites
            time_since_last = current_time - self.last_request_time
            too_frequent = time_since_last < self.min_interval
            too_many_requests = self.request_count >= self.max_requests_per_window
            
            return not (too_frequent or too_many_requests)
    
    def wait_if_needed(self):
        """Attend si nécessaire avant de faire une requête"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                # Removed: print() pour éviter pollution console
                time.sleep(wait_time)
    
    def record_request(self):
        """Enregistre qu'une requête a été faite"""
        with self.lock:
            self.last_request_time = time.time()
            self.request_count += 1
            # Removed: print() pour éviter pollution console
            # La métrique est disponible via self.request_count si besoin
    
    def get_cache_key(self, data_type: str, **params) -> str:
        """Génère une clé de cache unique avec hash pour éviter les noms trop longs"""
        param_str = "_".join([f"{k}:{v}" for k, v in sorted(params.items())])
        
        # Si la chaîne est trop longue, utiliser un hash
        if len(param_str) > 100:  # Limite arbitraire
            param_hash = hashlib.md5(param_str.encode()).hexdigest()
            return f"{data_type}_{param_hash}"
        else:
            return f"{data_type}_{param_str}"
    
    def get_cached_data(self, data_type: str, **params) -> Optional[Dict[str, Any]]:
        """Récupère des données du cache si elles sont valides"""
        cache_key = self.get_cache_key(data_type, **params)
        
        # Vérifier le cache mémoire
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl.get(data_type, 300):
                print(f"✅ Cache hit pour {cache_key}")
                return cached_item['data']
        
        # Vérifier le cache persistant
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_item = json.load(f)
                
                if time.time() - cached_item['timestamp'] < self.cache_ttl.get(data_type, 300):
                    print(f"✅ Cache persistant hit pour {cache_key}")
                    # Remettre en cache mémoire
                    self.cache[cache_key] = cached_item
                    return cached_item['data']
            except:
                pass
        
        return None
    
    def cache_data(self, data_type: str, data: Dict[str, Any], **params):
        """Met en cache des données"""
        cache_key = self.get_cache_key(data_type, **params)
        cache_item = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Cache mémoire
        self.cache[cache_key] = cache_item
        
        # Cache persistant
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_item, f)
        except Exception as e:
            print(f"⚠️  Erreur sauvegarde cache: {e}")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Retourne le statut du rate limiter"""
        current_time = time.time()
        return {
            'requests_this_window': self.request_count,
            'max_requests_per_window': self.max_requests_per_window,
            'time_since_last_request': current_time - self.last_request_time,
            'min_interval': self.min_interval,
            'can_request_now': self.can_make_request(),
            'cache_size': len(self.cache)
        }

# Instance globale singleton
_rate_limiter = None

def get_rate_limiter() -> CoinGeckoRateLimiter:
    """Retourne l'instance globale du rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = CoinGeckoRateLimiter()
    return _rate_limiter