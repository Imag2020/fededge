import requests
import json
import time
from ..utils.debug_logger import get_debug_logger
from ..utils.rate_limiter import get_rate_limiter
from ..config.paths import CONFIG_DIR

def fetch_crypto_prices():
    """Récupère les prix depuis l'API CoinGecko avec rate limiting."""
    debug = get_debug_logger()
    rate_limiter = get_rate_limiter()
    crypto_ids_str = None  # Définir au début pour le scope

    try:
        debug.log_data_collection('COINGECKO_API', True, "🚀 Début de récupération des prix crypto", None)

        config_file = CONFIG_DIR / 'config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        crypto_ids = config['crypto_sources']['target_cryptos']
        crypto_ids_str = ",".join(crypto_ids)
        
        # Vérifier le cache d'abord
        cached_prices = rate_limiter.get_cached_data('simple_price', ids=crypto_ids_str)
        if cached_prices:
            debug.log_data_collection('COINGECKO_API', True, f"✅ Prix récupérés du cache: {len(cached_prices)} cryptos", None)
            return cached_prices
        
        # Si pas de cache, faire la requête avec rate limiting
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_ids_str}&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true"
        
        debug.log_data_collection('COINGECKO_API', True, f"📡 Requête API: {len(crypto_ids)} cryptos", {
            'url': url,
            'target_cryptos': crypto_ids
        })
        
        # Attendre si nécessaire pour respecter le rate limit
        rate_limiter.wait_if_needed()
        
        response = requests.get(url)
        rate_limiter.record_request()  # Enregistrer la requête
        
        response.raise_for_status() # Lève une exception si la requête échoue
        prices = response.json()
        
        # Enrichir les données avec les images du registre crypto
        from ..utils.crypto_registry import get_crypto_registry
        try:
            crypto_registry = get_crypto_registry()
            registry_data = crypto_registry.get_registry()
            
            # Créer un mapping coingecko_id -> image
            image_mapping = {}
            for asset in registry_data.get('assets', []):
                if 'image' in asset and asset['image']:
                    image_mapping[asset['id']] = asset['image']
            
            # Ajouter les images aux données de prix
            for crypto_id, price_data in prices.items():
                if crypto_id in image_mapping:
                    price_data['image'] = image_mapping[crypto_id]
                    
            debug.log_data_collection('COINGECKO_API', True, f"✅ Images ajoutées: {len(image_mapping)} assets avec icônes")
        except Exception as e:
            debug.log_data_collection('COINGECKO_API', False, f"⚠️ Erreur ajout images: {e}")
        
        # Mettre en cache
        rate_limiter.cache_data('simple_price', prices, ids=crypto_ids_str)
        
        # Compter les prix récupérés
        price_count = len(prices)
        sample_prices = {k: v for k, v in list(prices.items())[:3]} # Échantillon pour le debug
        
        debug.log_data_collection('COINGECKO_API', True, f"✅ Prix récupérés: {price_count} cryptos", {
            'total_cryptos': price_count,
            'sample_data': sample_prices,
            'response_size_bytes': len(str(prices))
        })
        
        # Format: {'ethereum': {'usd': 2345.67, 'image': 'https://...'}, 'bitcoin': {'usd': 45000.12, 'image': 'https://...'}}
        return prices

    except Exception as e:
        debug.log_data_collection('COINGECKO_API', False, f"❌ Erreur API CoinGecko: {str(e)}", None)
        print(f"Erreur lors de la récupération des prix: {e}")

        # Fallback: toujours retourner le cache même expiré au lieu de None
        if crypto_ids_str:  # Seulement si on a pu charger la config
            try:
                import os
                from ..config.paths import CACHE_DIR

                cache_key = rate_limiter.get_cache_key('simple_price', ids=crypto_ids_str)
                cache_file = os.path.join(str(CACHE_DIR), f"{cache_key}.json")

                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        cached_item = json.load(f)
                        fallback_data = cached_item.get('data')
                        if fallback_data:
                            age_seconds = int(time.time() - cached_item.get('timestamp', 0))
                            debug.log_data_collection('COINGECKO_API', True,
                                f"✅ Fallback: cache de {age_seconds}s utilisé ({len(fallback_data)} cryptos)", None)
                            print(f"⚠️ Utilisation cache expiré (âge: {age_seconds}s)")
                            return fallback_data
            except Exception as fallback_error:
                print(f"⚠️ Erreur fallback cache: {fallback_error}")

        return None
