"""
Registre dynamique des cryptomonnaies basé sur l'API CoinGecko
Récupère automatiquement les top 250 cryptos avec leurs métadonnées
"""

import requests
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from .rate_limiter import get_rate_limiter
from backend.config.paths import CACHE_DIR

class CryptoRegistry:
    """Gestionnaire dynamique de la liste des cryptomonnaies supportées"""
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        self.registry_file = str(CACHE_DIR)+"/crypto_registry.json"
        self.registry_ttl = 86400  # 24 heures
        self.top_n = 250  # Top 250 cryptos par market cap
        
        # Cache mémoire
        self._registry = None
        self._ticker_to_coingecko = None
        self._coingecko_to_ticker = None
        
        # Créer le répertoire de cache
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
    
    def _load_registry_from_cache(self) -> Optional[Dict]:
        """Charge le registre depuis le cache local"""
        if not os.path.exists(self.registry_file):
            return None
        
        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
            
            # Vérifier si le cache n'est pas expiré
            if time.time() - data.get('timestamp', 0) < self.registry_ttl:
                print(f"✅ Registre crypto chargé du cache: {len(data.get('assets', []))} assets")
                return data
            else:
                print("⏰ Cache crypto expiré, récupération depuis l'API")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lecture cache crypto: {e}")
            return None
    
    def _save_registry_to_cache(self, data: Dict):
        """Sauvegarde le registre dans le cache local"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Registre crypto sauvegardé: {len(data.get('assets', []))} assets")
        except Exception as e:
            print(f"❌ Erreur sauvegarde cache crypto: {e}")
    
    def _fetch_top_cryptos_from_api(self) -> Optional[List[Dict]]:
        """Récupère le top N des cryptos depuis CoinGecko"""
        try:
            # Utiliser le rate limiter global
            cached_data = self.rate_limiter.get_cached_data('coins_markets', per_page=self.top_n)
            if cached_data:
                print(f"📦 Top cryptos récupérés du cache global")
                return cached_data
            
            # Faire la requête API
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': self.top_n,
                'page': 1,
                'sparkline': 'false',
                'locale': 'en'
            }
            
            print(f"🔄 Récupération du top {self.top_n} des cryptos depuis CoinGecko...")
            
            # Rate limiting
            self.rate_limiter.wait_if_needed()
            response = requests.get(url, params=params, timeout=30)
            self.rate_limiter.record_request()
            
            response.raise_for_status()
            data = response.json()
            
            # Cache la réponse
            self.rate_limiter.cache_data('coins_markets', data, per_page=self.top_n)
            
            print(f"✅ {len(data)} cryptos récupérés avec succès")
            return data
            
        except Exception as e:
            print(f"❌ Erreur récupération cryptos API: {e}")
            return None
    
    def _build_registry(self, cryptos_data: List[Dict]) -> Dict:
        """Construit le registre complet à partir des données CoinGecko"""
        registry = {
            'timestamp': time.time(),
            'source': 'coingecko_markets_api',
            'total_assets': len(cryptos_data),
            'assets': [],
            'ticker_to_coingecko': {},
            'coingecko_to_ticker': {}
        }
        
        for crypto in cryptos_data:
            asset_info = {
                'id': crypto['id'],  # coingecko_id
                'symbol': crypto['symbol'].upper(),
                'name': crypto['name'],
                'market_cap_rank': crypto.get('market_cap_rank'),
                'current_price': crypto.get('current_price'),
                'market_cap': crypto.get('market_cap'),
                'image': crypto.get('image'),
                'price_change_24h': crypto.get('price_change_percentage_24h')
            }
            
            registry['assets'].append(asset_info)
            
            # Mapping bidirectionnel
            registry['ticker_to_coingecko'][crypto['symbol'].lower()] = crypto['id']
            registry['coingecko_to_ticker'][crypto['id']] = crypto['symbol'].lower()
        
        return registry
    
    def refresh_registry(self) -> bool:
        """Force la mise à jour du registre depuis l'API"""
        print("🔄 Mise à jour forcée du registre crypto...")
        
        cryptos_data = self._fetch_top_cryptos_from_api()
        if not cryptos_data:
            return False
        
        registry = self._build_registry(cryptos_data)
        self._save_registry_to_cache(registry)
        
        # Mettre à jour le cache mémoire
        self._registry = registry
        self._ticker_to_coingecko = registry['ticker_to_coingecko']
        self._coingecko_to_ticker = registry['coingecko_to_ticker']
        
        return True
    
    def get_registry(self) -> Dict:
        """Récupère le registre complet (cache ou API)"""
        if self._registry is not None:
            return self._registry
        
        # Essayer le cache d'abord
        cached_registry = self._load_registry_from_cache()
        if cached_registry:
            self._registry = cached_registry
            return cached_registry
        
        # Sinon, récupérer depuis l'API
        if self.refresh_registry():
            return self._registry
        
        # Fallback: registre minimal
        return self._get_fallback_registry()
    
    def _get_fallback_registry(self) -> Dict:
        """Registre de fallback avec les principales cryptos"""
        fallback_assets = [
            {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'},
            {'id': 'ethereum', 'symbol': 'ETH', 'name': 'Ethereum'},
            {'id': 'solana', 'symbol': 'SOL', 'name': 'Solana'},
            {'id': 'bittensor', 'symbol': 'TAO', 'name': 'Bittensor'},
            {'id': 'cardano', 'symbol': 'ADA', 'name': 'Cardano'}
        ]
        
        registry = {
            'timestamp': time.time(),
            'source': 'fallback',
            'total_assets': len(fallback_assets),
            'assets': fallback_assets,
            'ticker_to_coingecko': {},
            'coingecko_to_ticker': {}
        }
        
        for asset in fallback_assets:
            registry['ticker_to_coingecko'][asset['symbol'].lower()] = asset['id']
            registry['coingecko_to_ticker'][asset['id']] = asset['symbol'].lower()
        
        return registry
    
    def get_ticker_to_coingecko_mapping(self) -> Dict[str, str]:
        """Retourne le mapping ticker -> coingecko_id"""
        if self._ticker_to_coingecko is None:
            registry = self.get_registry()
            self._ticker_to_coingecko = registry['ticker_to_coingecko']
        
        return self._ticker_to_coingecko
    
    def get_coingecko_to_ticker_mapping(self) -> Dict[str, str]:
        """Retourne le mapping coingecko_id -> ticker"""
        if self._coingecko_to_ticker is None:
            registry = self.get_registry()
            self._coingecko_to_ticker = registry['coingecko_to_ticker']
        
        return self._coingecko_to_ticker
    
    def get_supported_assets(self) -> List[Dict]:
        """Retourne la liste des assets supportés"""
        registry = self.get_registry()
        return registry['assets']
    
    def get_asset_info(self, asset_id_or_ticker: str) -> Optional[Dict]:
        """Récupère les infos d'un asset par son ID CoinGecko ou ticker"""
        registry = self.get_registry()
        
        # Recherche par coingecko_id
        for asset in registry['assets']:
            if asset['id'] == asset_id_or_ticker.lower():
                return asset
        
        # Recherche par ticker
        for asset in registry['assets']:
            if asset['symbol'].lower() == asset_id_or_ticker.lower():
                return asset
        
        return None
    
    def is_asset_supported(self, asset_id_or_ticker: str) -> bool:
        """Vérifie si un asset est supporté"""
        return self.get_asset_info(asset_id_or_ticker) is not None
    
    def get_registry_stats(self) -> Dict:
        """Statistiques du registre"""
        registry = self.get_registry()
        return {
            'total_assets': registry['total_assets'],
            'source': registry['source'],
            'last_updated': registry['timestamp'],
            'age_hours': (time.time() - registry['timestamp']) / 3600,
            'sample_assets': registry['assets'][:5]  # 5 premiers assets
        }

# Instance globale singleton
_crypto_registry = None

def get_crypto_registry() -> CryptoRegistry:
    """Retourne l'instance globale du registre crypto"""
    global _crypto_registry
    if _crypto_registry is None:
        _crypto_registry = CryptoRegistry()
    return _crypto_registry