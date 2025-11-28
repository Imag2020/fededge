"""
Fonctions utilitaires pour la gestion des assets crypto
"""

from typing import List, Dict, Optional, Tuple
from .crypto_registry import get_crypto_registry

from backend.config.paths import CACHE_DIR


def get_supported_assets_list() -> List[Dict]:
    """
    Retourne la liste complète des assets supportés
    Format: [{'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin', ...}, ...]
    """
    registry = get_crypto_registry()
    return registry.get_supported_assets()

def get_top_assets_by_market_cap(limit: int = 50) -> List[Dict]:
    """
    Retourne les N premiers assets par market cap
    """
    assets = get_supported_assets_list()
    return assets[:limit]

def search_assets(query: str, limit: int = 20) -> List[Dict]:
    """
    Recherche des assets par nom ou symbole
    D'abord dans la base locale, puis sur CoinGecko si aucun résultat
    """
    query = query.lower()
    assets = get_supported_assets_list()
    
    # Recherche locale d'abord
    matches = []
    for asset in assets:
        if (query in asset['name'].lower() or 
            query in asset['symbol'].lower() or
            query in asset['id'].lower()):
            matches.append(asset)
            
            if len(matches) >= limit:
                break
    
    # Si pas de résultats locaux, chercher sur CoinGecko
    if len(matches) == 0:
        try:
            coingecko_results = search_coingecko_assets(query, limit)
            matches.extend(coingecko_results)
        except Exception as e:
            print(f"⚠️ CoinGecko search failed: {e}")
    
    return matches

def search_coingecko_assets(query: str, limit: int = 10) -> List[Dict]:
    """
    Recherche d'assets sur CoinGecko API
    """
    import requests
    
    try:
        # API CoinGecko pour rechercher des assets
        url = "https://api.coingecko.com/api/v3/search"
        params = {
            'query': query
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        coins = data.get('coins', [])[:limit]
        
        # Formater les résultats pour correspondre au format local
        formatted_results = []
        for coin in coins:
            formatted_results.append({
                'id': coin['id'],
                'symbol': coin['symbol'].upper(),
                'name': coin['name'],
                'market_cap_rank': coin.get('market_cap_rank', 999),
                'image': coin.get('large', ''),
                # Marquer comme nouvel asset
                'is_new_asset': True,
                'source': 'coingecko'
            })
        
        print(f"🌐 Found {len(formatted_results)} assets on CoinGecko for '{query}'")
        return formatted_results
        
    except Exception as e:
        print(f"❌ CoinGecko search error: {e}")
        return []

def resolve_asset_identifier(asset_input: str) -> Optional[Tuple[str, str]]:
    """
    Résout un identifiant d'asset (ticker ou coingecko_id) vers (coingecko_id, ticker)
    
    Args:
        asset_input: Peut être 'BTC', 'btc', 'bitcoin', etc.
    
    Returns:
        (coingecko_id, ticker) ou None si non trouvé
    """
    registry = get_crypto_registry()
    ticker_to_coingecko = registry.get_ticker_to_coingecko_mapping()
    coingecko_to_ticker = registry.get_coingecko_to_ticker_mapping()
    
    asset_lower = asset_input.lower()
    
    # Essayer comme ticker
    if asset_lower in ticker_to_coingecko:
        coingecko_id = ticker_to_coingecko[asset_lower]
        return (coingecko_id, asset_lower)
    
    # Essayer comme coingecko_id
    if asset_lower in coingecko_to_ticker:
        ticker = coingecko_to_ticker[asset_lower]
        return (asset_lower, ticker)
    
    return None

def get_asset_display_info(asset_id_or_ticker: str) -> Optional[Dict]:
    """
    Retourne les infos d'affichage d'un asset
    """
    registry = get_crypto_registry()
    return registry.get_asset_info(asset_id_or_ticker)

def is_asset_supported(asset_id_or_ticker: str) -> bool:
    """
    Vérifie si un asset est supporté
    """
    registry = get_crypto_registry()
    return registry.is_asset_supported(asset_id_or_ticker)

def get_assets_for_dropdown() -> List[Dict]:
    """
    Retourne les assets formatés pour un dropdown frontend
    Format optimisé pour l'affichage: {value, label, subtitle}
    """
    assets = get_top_assets_by_market_cap(100)  # Top 100 pour le dropdown
    
    dropdown_options = []
    for asset in assets:
        price_str = f"${asset.get('current_price', 0):.2f}" if asset.get('current_price') else ""
        rank_str = f"#{asset.get('market_cap_rank', '?')}" if asset.get('market_cap_rank') else ""
        
        dropdown_options.append({
            'value': asset['id'],  # coingecko_id pour l'API
            'label': f"{asset['symbol']} - {asset['name']}",
            'subtitle': f"{rank_str} {price_str}".strip(),
            'symbol': asset['symbol'],
            'name': asset['name'],
            'rank': asset.get('market_cap_rank', 999)
        })
    
    return dropdown_options

def get_registry_status() -> Dict:
    """
    Retourne le statut du registre crypto (pour debug/monitoring)
    """
    registry = get_crypto_registry()
    return registry.get_registry_stats()