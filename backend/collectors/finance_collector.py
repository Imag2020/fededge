"""
Finance Collector - Récupération et analyse des données du marché crypto global
Fournit des statistiques de marché, top gainers/losers, et analyse financière pour le LLM
"""

import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..utils.debug_logger import get_debug_logger
from ..utils.rate_limiter import get_rate_limiter

# Cache global pour les données de marché complètes
_finance_analysis_cache: Optional[Dict[str, Any]] = None
_cache_timestamp: Optional[datetime] = None

def fetch_market_overview() -> Optional[Dict[str, Any]]:
    """
    Récupère une vue d'ensemble du marché crypto global avec cache et rate limiting
    Retourne les données formatées pour analyse
    """
    debug = get_debug_logger()
    rate_limiter = get_rate_limiter()

    try:
        debug.log_data_collection('MARKET_OVERVIEW', True, "🚀 Début récupération vue d'ensemble marché (avec cache)", None)

        # Vérifier le cache d'abord
        cached_markets = rate_limiter.get_cached_data('coins_markets', vs_currency='usd', order='market_cap_desc', per_page=250)
        if cached_markets:
            debug.log_data_collection('MARKET_OVERVIEW', True, f"✅ Données marché du cache: {len(cached_markets)} cryptos", None)
            return cached_markets

        # Si pas de cache, faire la requête avec rate limiting
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&sparkline=false&price_change_percentage=1h,24h,7d"

        debug.log_data_collection('MARKET_OVERVIEW', True, "📡 Requête API marché global", {'url': url})

        # Attendre si nécessaire pour respecter le rate limit
        rate_limiter.wait_if_needed()

        response = requests.get(url)
        rate_limiter.record_request()  # Enregistrer la requête

        if response.status_code == 429:
            # Rate limited - return last cached data if available
            debug.log_data_collection('MARKET_OVERVIEW', False, "⚠️ Rate limited (429), using stale cache", None)
            # Try to get any cached version (even expired)
            import hashlib
            cache_key = f"coins_markets_vs_currency:usd_order:market_cap_desc_per_page:250"
            stale_data = rate_limiter.cache.get(cache_key)
            if stale_data:
                return stale_data
            return None

        response.raise_for_status()
        market_data = response.json()

        # Mettre en cache avec TTL plus long (15 minutes au lieu de 5)
        rate_limiter.cache_data('coins_markets', market_data, vs_currency='usd', order='market_cap_desc', per_page=250)

        debug.log_data_collection('MARKET_OVERVIEW', True, f"✅ Données marché récupérées: {len(market_data)} cryptos", {
            'total_cryptos': len(market_data),
            'sample_symbols': [coin['symbol'].upper() for coin in market_data[:5]] if market_data else []
        })

        return market_data

    except Exception as e:
        debug.log_data_collection('MARKET_OVERVIEW', False, f"❌ Erreur API marché: {str(e)}", None)
        print(f"Erreur lors de la récupération des données de marché: {e}")
        return None

def get_top_gainers_losers(market_data: List[Dict], timeframe: str = "24h") -> Dict[str, List[Dict]]:
    """
    Extrait les top 10 gainers et losers d'une période donnée
    
    Args:
        market_data: Données du marché depuis CoinGecko
        timeframe: "1h", "24h", ou "7d"
    
    Returns:
        Dict avec "gainers" et "losers"
    """
    debug = get_debug_logger()
    
    try:
        # Mapper le timeframe au champ API approprié
        price_change_field = f"price_change_percentage_{timeframe}"
        
        # Filtrer les cryptos avec des données valides
        valid_coins = [
            coin for coin in market_data 
            if coin.get(price_change_field) is not None
        ]
        
        # Trier pour les gainers (décroissant)
        gainers = sorted(
            valid_coins, 
            key=lambda x: x.get(price_change_field, 0), 
            reverse=True
        )[:10]
        
        # Trier pour les losers (croissant)
        losers = sorted(
            valid_coins, 
            key=lambda x: x.get(price_change_field, 0)
        )[:10]
        
        debug.log_data_collection('TOP_MOVERS', True, f"✅ Top movers extraits pour {timeframe}", {
            'timeframe': timeframe,
            'gainers_count': len(gainers),
            'losers_count': len(losers),
            'top_gainer': f"{gainers[0]['symbol'].upper()}: +{gainers[0][price_change_field]:.2f}%" if gainers else "N/A",
            'top_loser': f"{losers[0]['symbol'].upper()}: {losers[0][price_change_field]:.2f}%" if losers else "N/A"
        })
        
        return {
            "gainers": gainers,
            "losers": losers,
            "timeframe": timeframe,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        debug.log_error('TOP_MOVERS', f"Erreur extraction top movers: {str(e)}", e)
        return {"gainers": [], "losers": [], "timeframe": timeframe, "error": str(e)}

def calculate_market_statistics(market_data: List[Dict]) -> Dict[str, Any]:
    """
    Calcule les statistiques globales du marché crypto
    
    Returns:
        Dict avec statistiques de marché
    """
    debug = get_debug_logger()
    
    try:
        # Filtrer les cryptos avec des données valides
        valid_coins = [coin for coin in market_data if coin.get('market_cap') and coin.get('current_price')]
        
        if not valid_coins:
            return {"error": "Aucune donnée valide disponible"}
        
        # Calculs de base
        total_market_cap = sum(coin['market_cap'] for coin in valid_coins)
        total_volume_24h = sum(coin.get('total_volume', 0) for coin in valid_coins)
        
        # Distribution par performance 24h
        gains_24h = [coin for coin in valid_coins if coin.get('price_change_percentage_24h') is not None and coin.get('price_change_percentage_24h', 0) > 0]
        losses_24h = [coin for coin in valid_coins if coin.get('price_change_percentage_24h') is not None and coin.get('price_change_percentage_24h', 0) < 0]
        neutral_24h = [coin for coin in valid_coins if coin.get('price_change_percentage_24h') is not None and coin.get('price_change_percentage_24h', 0) == 0]
        
        # Dominance BTC et ETH
        btc_data = next((coin for coin in valid_coins if coin['symbol'].lower() == 'btc'), None)
        eth_data = next((coin for coin in valid_coins if coin['symbol'].lower() == 'eth'), None)
        
        btc_dominance = (btc_data['market_cap'] / total_market_cap * 100) if btc_data else 0
        eth_dominance = (eth_data['market_cap'] / total_market_cap * 100) if eth_data else 0
        
        # Sentiment de marché basé sur les performances
        valid_price_changes = [coin.get('price_change_percentage_24h', 0) for coin in valid_coins if coin.get('price_change_percentage_24h') is not None]
        avg_24h_change = sum(valid_price_changes) / len(valid_price_changes) if valid_price_changes else 0
        
        market_sentiment = "BULLISH" if avg_24h_change > 2 else "BEARISH" if avg_24h_change < -2 else "NEUTRAL"
        
        stats = {
            "total_market_cap": total_market_cap,
            "total_volume_24h": total_volume_24h,
            "total_coins_tracked": len(valid_coins),
            "gains_count": len(gains_24h),
            "losses_count": len(losses_24h),
            "neutral_count": len(neutral_24h),
            "gains_percentage": (len(gains_24h) / len(valid_coins)) * 100,
            "losses_percentage": (len(losses_24h) / len(valid_coins)) * 100,
            "btc_dominance": btc_dominance,
            "eth_dominance": eth_dominance,
            "average_24h_change": avg_24h_change,
            "market_sentiment": market_sentiment,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        debug.log_data_collection('MARKET_STATS', True, "✅ Statistiques marché calculées", {
            'total_market_cap_billions': round(total_market_cap / 1e9, 2),
            'coins_tracked': len(valid_coins),
            'market_sentiment': market_sentiment,
            'btc_dominance': round(btc_dominance, 2),
            'avg_change_24h': round(avg_24h_change, 2)
        })
        
        return stats
        
    except Exception as e:
        debug.log_error('MARKET_STATS', f"Erreur calcul statistiques: {str(e)}", e)
        return {"error": str(e)}

def get_sector_analysis(market_data: List[Dict]) -> Dict[str, Any]:
    """
    Analyse les secteurs/catégories de cryptos
    Utilise les catégories CoinGecko si disponibles
    """
    debug = get_debug_logger()
    
    try:
        # Cryptos par categories (basé sur les symboles courants)
        categories = {
            "Layer 1": ["btc", "eth", "sol", "ada", "dot", "avax", "near", "atom", "ftm"],
            "DeFi": ["uni", "aave", "comp", "mkr", "snx", "crv", "1inch"],
            "Layer 2": ["matic", "op", "arb"],
            "Meme": ["doge", "shib", "pepe", "floki"],
            "AI": ["fet", "tao", "rndr", "ocean"],
            "Gaming": ["axs", "sand", "mana", "imx"],
            "Storage": ["fil", "ar", "sia"],
            "Oracle": ["link", "band", "api3"]
        }
        
        sector_performance = {}
        
        for category, symbols in categories.items():
            category_coins = [
                coin for coin in market_data 
                if coin['symbol'].lower() in symbols
            ]
            
            if category_coins:
                avg_change_24h = sum(coin.get('price_change_percentage_24h', 0) for coin in category_coins) / len(category_coins)
                total_market_cap = sum(coin.get('market_cap', 0) for coin in category_coins)
                
                sector_performance[category] = {
                    "avg_change_24h": avg_change_24h,
                    "total_market_cap": total_market_cap,
                    "coins_count": len(category_coins),
                    "top_performer": max(category_coins, key=lambda x: x.get('price_change_percentage_24h', 0)),
                    "worst_performer": min(category_coins, key=lambda x: x.get('price_change_percentage_24h', 0))
                }
        
        debug.log_data_collection('SECTOR_ANALYSIS', True, f"✅ Analyse secteurs terminée: {len(sector_performance)} secteurs", {
            'sectors_analyzed': list(sector_performance.keys()),
            'total_sectors': len(sector_performance)
        })
        
        return {
            "sectors": sector_performance,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        debug.log_error('SECTOR_ANALYSIS', f"Erreur analyse secteurs: {str(e)}", e)
        return {"error": str(e)}

def get_complete_finance_analysis(use_cache: bool = True) -> Dict[str, Any]:
    """
    Fonction principale qui récupère et compile toutes les analyses financières

    Args:
        use_cache: Si True, retourne le cache si disponible (pour chargement rapide)

    Returns:
        Dict complet avec toutes les données de marché
    """
    global _finance_analysis_cache, _cache_timestamp

    debug = get_debug_logger()

    # Si le cache est demandé et disponible (< 15 minutes), le retourner immédiatement
    if use_cache and _finance_analysis_cache and _cache_timestamp:
        cache_age = (datetime.utcnow() - _cache_timestamp).total_seconds()
        if cache_age < 900:  # 15 minutes
            debug.log_data_collection('COMPLETE_FINANCE', True, f"✅ Retour cache ({int(cache_age)}s)", None)
            return _finance_analysis_cache

    try:
        debug.log_data_collection('COMPLETE_FINANCE', True, "🚀 Début analyse financière complète", None)

        # 1. Récupérer les données de marché
        market_data = fetch_market_overview()
        if not market_data:
            # Retourner le cache même périmé si pas de nouvelles données
            if _finance_analysis_cache:
                debug.log_data_collection('COMPLETE_FINANCE', True, "⚠️ Retour cache périmé (pas de nouvelles données)", None)
                return _finance_analysis_cache
            return {"error": "Impossible de récupérer les données de marché"}

        # 2. Calculer les statistiques globales
        market_stats = calculate_market_statistics(market_data)

        # 3. Obtenir les top gainers/losers pour différentes périodes
        movers_24h = get_top_gainers_losers(market_data, "24h")
        movers_1h = get_top_gainers_losers(market_data, "1h")
        movers_7d = get_top_gainers_losers(market_data, "7d")

        # 4. Analyse par secteurs
        sector_analysis = get_sector_analysis(market_data)

        # 5. Compiler tout ensemble
        complete_analysis = {
            "market_statistics": market_stats,
            "top_movers": {
                "1h": movers_1h,
                "24h": movers_24h,
                "7d": movers_7d
            },
            "sector_analysis": sector_analysis,
            "raw_market_data": market_data[:50],  # Top 50 pour éviter la surcharge
            "analysis_summary": {
                "total_cryptos_analyzed": len(market_data),
                "market_cap_billions": round(market_stats.get('total_market_cap', 0) / 1e9, 2),
                "market_sentiment": market_stats.get('market_sentiment', 'UNKNOWN'),
                "btc_dominance": round(market_stats.get('btc_dominance', 0), 2),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        }

        # Mettre en cache
        _finance_analysis_cache = complete_analysis
        _cache_timestamp = datetime.utcnow()

        debug.log_data_collection('COMPLETE_FINANCE', True, "✅ Analyse financière complète terminée et mise en cache", {
            'market_cap_billions': complete_analysis['analysis_summary']['market_cap_billions'],
            'market_sentiment': complete_analysis['analysis_summary']['market_sentiment'],
            'cryptos_analyzed': complete_analysis['analysis_summary']['total_cryptos_analyzed']
        })

        return complete_analysis

    except Exception as e:
        debug.log_error('COMPLETE_FINANCE', f"Erreur analyse financière complète: {str(e)}", e)
        # Retourner le cache en cas d'erreur si disponible
        if _finance_analysis_cache:
            return _finance_analysis_cache
        return {"error": str(e)}

def format_finance_analysis_for_llm(analysis_data: Dict[str, Any]) -> str:
    """
    Formate l'analyse financière pour le LLM (similaire à format_analysis_for_llm)
    
    Args:
        analysis_data: Données d'analyse depuis get_complete_finance_analysis()
    
    Returns:
        String formatée pour le LLM
    """
    debug = get_debug_logger()
    
    try:
        if "error" in analysis_data:
            return f"Erreur d'analyse financière: {analysis_data['error']}"
        
        stats = analysis_data.get('market_statistics', {})
        movers_24h = analysis_data.get('top_movers', {}).get('24h', {})
        summary = analysis_data.get('analysis_summary', {})
        
        # Format optimisé pour le LLM
        llm_text = f"""## ANALYSE FINANCIÈRE CRYPTO - {summary.get('analysis_timestamp', 'N/A')}

### STATISTIQUES GLOBALES DU MARCHÉ
• Market Cap Total: ${stats.get('total_market_cap', 0):,.0f} (${summary.get('market_cap_billions', 0)}B)
• Volume 24h: ${stats.get('total_volume_24h', 0):,.0f}
• Cryptos Analysées: {stats.get('total_coins_tracked', 0)}
• Sentiment Marché: {stats.get('market_sentiment', 'UNKNOWN')}
• Variation Moyenne 24h: {stats.get('average_24h_change', 0):+.2f}%

### DOMINANCE
• Bitcoin (BTC): {stats.get('btc_dominance', 0):.1f}%
• Ethereum (ETH): {stats.get('eth_dominance', 0):.1f}%

### DISTRIBUTION DES PERFORMANCES 24H
• En hausse: {stats.get('gains_count', 0)} cryptos ({stats.get('gains_percentage', 0):.1f}%)
• En baisse: {stats.get('losses_count', 0)} cryptos ({stats.get('losses_percentage', 0):.1f}%)
• Neutres: {stats.get('neutral_count', 0)} cryptos

### TOP 5 GAINERS 24H"""
        
        # Ajouter les top gainers
        gainers = movers_24h.get('gainers', [])[:5]
        for i, coin in enumerate(gainers, 1):
            change = coin.get('price_change_percentage_24h', 0)
            price = coin.get('current_price', 0)
            mcap = coin.get('market_cap', 0)
            llm_text += f"\n{i}. {coin.get('name', 'N/A')} ({coin.get('symbol', '').upper()}): +{change:.2f}% - ${price:.4f} (MC: ${mcap:,.0f})"
        
        llm_text += "\n\n### TOP 5 LOSERS 24H"
        
        # Ajouter les top losers
        losers = movers_24h.get('losers', [])[:5]
        for i, coin in enumerate(losers, 1):
            change = coin.get('price_change_percentage_24h', 0)
            price = coin.get('current_price', 0)
            mcap = coin.get('market_cap', 0)
            llm_text += f"\n{i}. {coin.get('name', 'N/A')} ({coin.get('symbol', '').upper()}): {change:.2f}% - ${price:.4f} (MC: ${mcap:,.0f})"
        
        # Ajouter analyse sectorielle si disponible
        sectors = analysis_data.get('sector_analysis', {}).get('sectors', {})
        if sectors:
            llm_text += "\n\n### PERFORMANCE PAR SECTEUR 24H"
            sorted_sectors = sorted(sectors.items(), key=lambda x: x[1].get('avg_change_24h', 0), reverse=True)
            for sector, data in sorted_sectors:
                avg_change = data.get('avg_change_24h', 0)
                coins_count = data.get('coins_count', 0)
                llm_text += f"\n• {sector}: {avg_change:+.2f}% (avg, {coins_count} coins)"
        
        debug.log_data_collection('LLM_FORMAT', True, "✅ Données formatées pour LLM", {
            'text_length': len(llm_text),
            'sections_included': ['global_stats', 'dominance', 'distribution', 'top_movers', 'sectors']
        })
        
        return llm_text
        
    except Exception as e:
        debug.log_error('LLM_FORMAT', f"Erreur formatage LLM: {str(e)}", e)
        return f"Erreur de formatage pour LLM: {str(e)}"