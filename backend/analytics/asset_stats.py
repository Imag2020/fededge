"""
Asset Statistics and Analysis Helper Functions
Uses CoinGecko API to fetch market data and calculate statistics for LLM analysis
"""

import requests
import pandas as pd
from scipy.stats import linregress
from typing import Dict, List, Optional, Any
import datetime
from decimal import Decimal
import logging
import time
import json
import os
from functools import lru_cache

from backend.config.paths import LOGS_DIR, CACHE_DIR

# Configure logger pour ne PAS afficher sur la console
logger = logging.getLogger(__name__)
logger.propagate = False  # Ne pas remonter au root logger
logger.setLevel(logging.WARNING)  # Seulement warnings et erreurs

# Handler vers fichier de log uniquement
if not logger.handlers:
    from logging.handlers import RotatingFileHandler
    log_dir = str(LOGS_DIR)
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "asset_stats.log"),
        maxBytes=5*1024*1024,
        backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

class AssetAnalyzer:
    """Analyzes asset market data and provides statistics for LLM consumption"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HIVE-AI-Bot/1.0'
        })
        self.last_request_time = 0
        self.min_request_interval = 15.0  # 15 secondes minimum entre les requêtes (plus conservateur)
        # Utiliser le rate limiter global au lieu du cache local
        from ..utils.rate_limiter import get_rate_limiter
        self.rate_limiter = get_rate_limiter()
        self.cache = {}  # Cache simple pour éviter les requêtes répétées
        self.cache_ttl = 1800  # 30 minutes de cache (plus long)
        self.persistent_cache_dir = str(CACHE_DIR)
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Créer le répertoire de cache s'il n'existe pas"""
        os.makedirs(self.persistent_cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self, asset_id: str, days: int, vs_currency: str = "usd") -> str:
        """Obtenir le chemin du fichier de cache pour un asset"""
        return os.path.join(self.persistent_cache_dir, f"{asset_id}_{days}d_{vs_currency}.json")
    
    def _load_from_persistent_cache(self, asset_id: str, days: int, vs_currency: str = "usd") -> Optional[Dict]:
        """Charger les données depuis le cache persistant"""
        cache_file = self._get_cache_file_path(asset_id, days, vs_currency)
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Vérifier l'âge du cache
            cached_time = cache_data.get('timestamp', 0)
            if time.time() - cached_time > self.cache_ttl:
                logger.info(f"📦 Cache persistant expiré pour {asset_id}")
                return None
            
            logger.info(f"📦 Cache persistant utilisé pour {asset_id} (âge: {time.time() - cached_time:.1f}s)")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture cache persistant pour {asset_id}: {e}")
            return None
    
    def _save_to_persistent_cache(self, asset_id: str, days: int, vs_currency: str, data: Dict):
        """Sauvegarder les données dans le cache persistant"""
        cache_file = self._get_cache_file_path(asset_id, days, vs_currency)
        
        try:
            cache_data = {
                'timestamp': time.time(),
                'asset_id': asset_id,
                'days': days,
                'vs_currency': vs_currency,
                'data': data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"📦 Données sauvegardées dans le cache persistant pour {asset_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde cache persistant pour {asset_id}: {e}")
    
    def _get_latest_cached_data(self, asset_id: str, days: int, vs_currency: str = "usd") -> Optional[Dict]:
        """Récupérer les dernières données en cache, même expirées, comme fallback"""
        cache_file = self._get_cache_file_path(asset_id, days, vs_currency)
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cached_time = cache_data.get('timestamp', 0)
            age_hours = (time.time() - cached_time) / 3600
            
            logger.info(f"🔄 Utilisation données expirées pour {asset_id} (âge: {age_hours:.1f}h)")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture fallback cache pour {asset_id}: {e}")
            return None
    
    def get_asset_market_chart(self, asset_id: str, days: int = 1, vs_currency: str = "usd") -> Optional[Dict]:
        """
        Fetch market chart data from CoinGecko API
        
        Args:
            asset_id: CoinGecko asset ID (e.g., 'bittensor', 'bitcoin')
            days: Number of days of data (1-365)
            vs_currency: Target currency (default: 'usd')
            
        Returns:
            Dict with prices, market_caps, total_volumes data or None if error
        """
        try:
            # Vérifier le cache global d'abord
            cached_data = self.rate_limiter.get_cached_data('market_chart', asset_id=asset_id, days=days, vs_currency=vs_currency)
            if cached_data:
                logger.info(f"📦 Cache global hit pour {asset_id} market chart")
                return cached_data
            
            # Si pas de cache, faire la requête avec rate limiting global
            url = f"{self.base_url}/coins/{asset_id}/market_chart"
            params = {
                'vs_currency': vs_currency,
                'days': days
            }
            
            # Utiliser le rate limiter global 
            self.rate_limiter.wait_if_needed()
            response = self.session.get(url, params=params, timeout=10)
            self.rate_limiter.record_request()
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Successfully fetched {days}d chart data for {asset_id}")
            
            # Sauvegarder dans le cache global
            self.rate_limiter.cache_data('market_chart', data, asset_id=asset_id, days=days, vs_currency=vs_currency)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching chart data for {asset_id}: {e}")

            # Fallback: TOUJOURS utiliser les dernières données en cache en cas d'erreur API
            logger.warning(f"🔄 Erreur API pour {asset_id}, tentative de récupération du cache...")
            fallback_data = self._get_latest_cached_data(asset_id, days, vs_currency)
            if fallback_data:
                logger.info(f"✅ Fallback: données historiques récupérées pour {asset_id}")
                return fallback_data
            else:
                logger.error(f"❌ Aucune donnée historique disponible pour {asset_id}")

            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error analyzing {asset_id}: {e}")
            return None
    
    
    def calculate_price_statistics(self, price_data: List[List]) -> Dict[str, Any]:
        """
        Calculate comprehensive price statistics from CoinGecko price data
        
        Args:
            price_data: List of [timestamp_ms, price] pairs from CoinGecko
            
        Returns:
            Dictionary with statistical analysis
        """
        if not price_data or len(price_data) < 2:
            return {"error": "Insufficient price data"}
        
        try:
            # Create DataFrame for analysis
            df = pd.DataFrame(price_data, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Basic price statistics
            stats = df['price'].describe()
            
            # Price movement calculations
            price_start = df['price'].iloc[0]
            price_end = df['price'].iloc[-1]
            variation_nette = price_end - price_start
            variation_pct = (variation_nette / price_start) * 100
            
            # Volatility analysis
            price_changes = df['price'].pct_change().dropna()
            volatility_pct = price_changes.std() * 100
            
            # Trend analysis using linear regression
            x_values = range(len(df))
            slope, intercept, r_value, p_value, std_err = linregress(x_values, df['price'])
            r_squared = r_value ** 2
            
            # Support and resistance levels (simple approach)
            rolling_max = df['price'].rolling(window=min(20, len(df)//4)).max()
            rolling_min = df['price'].rolling(window=min(20, len(df)//4)).min()
            resistance_level = rolling_max.max()
            support_level = rolling_min.min()
            
            # Price momentum (rate of change)
            momentum_5 = ((df['price'].iloc[-1] - df['price'].iloc[-min(5, len(df)-1)]) / 
                         df['price'].iloc[-min(5, len(df)-1)]) * 100 if len(df) >= 5 else 0
            
            # Time period info
            period_start = df['timestamp'].min()
            period_end = df['timestamp'].max()
            duration = period_end - period_start
            
            summary = {
                # Time period
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'duration_hours': round(duration.total_seconds() / 3600, 2),
                'data_points': len(df),
                
                # Price levels
                'price_start': round(price_start, 6),
                'price_end': round(price_end, 6),
                'price_min': round(stats['min'], 6),
                'price_max': round(stats['max'], 6),
                'price_mean': round(stats['mean'], 6),
                
                # Price movements
                'variation_absolute': round(variation_nette, 6),
                'variation_percent': round(variation_pct, 4),
                'momentum_5_points': round(momentum_5, 4),
                
                # Volatility metrics
                'price_std': round(stats['std'], 6),
                'volatility_percent': round(volatility_pct, 4),
                'price_range': round(stats['max'] - stats['min'], 6),
                'range_percent': round(((stats['max'] - stats['min']) / stats['mean']) * 100, 4),
                
                # Trend analysis
                'trend_slope': round(slope, 8),
                'trend_r_squared': round(r_squared, 4),
                'trend_direction': 'bullish' if slope > 0 else 'bearish' if slope < 0 else 'sideways',
                'trend_strength': 'strong' if r_squared > 0.7 else 'moderate' if r_squared > 0.3 else 'weak',
                
                # Technical levels
                'resistance_level': round(resistance_level, 6),
                'support_level': round(support_level, 6),
                'distance_to_resistance': round(((resistance_level - price_end) / price_end) * 100, 4),
                'distance_to_support': round(((price_end - support_level) / price_end) * 100, 4),
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error calculating price statistics: {e}")
            return {"error": f"Calculation error: {str(e)}"}
    
    def get_asset_full_analysis(self, asset_id: str, days: int = 1) -> Dict[str, Any]:
        """
        Get comprehensive asset analysis including price, volume, and market cap statistics
        
        Args:
            asset_id: CoinGecko asset ID
            days: Number of days of data to analyze
            
        Returns:
            Complete analysis dictionary ready for LLM consumption
        """
        try:
            # Fetch market data
            market_data = self.get_asset_market_chart(asset_id, days)
            if not market_data:
                return {"error": f"Could not fetch data for {asset_id}"}
            
            analysis = {
                'asset_id': asset_id,
                'analysis_period_days': days,
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'data_source': 'CoinGecko API'
            }
            
            # Price analysis
            if 'prices' in market_data and market_data['prices']:
                price_stats = self.calculate_price_statistics(market_data['prices'])
                analysis['price_analysis'] = price_stats
            
            # Volume analysis (if available)
            if 'total_volumes' in market_data and market_data['total_volumes']:
                volume_data = market_data['total_volumes']
                df_volume = pd.DataFrame(volume_data, columns=['timestamp', 'volume'])
                
                volume_start = df_volume['volume'].iloc[0]
                volume_end = df_volume['volume'].iloc[-1]
                volume_change_pct = ((volume_end - volume_start) / volume_start) * 100 if volume_start > 0 else 0
                
                analysis['volume_analysis'] = {
                    'volume_start': round(volume_start, 2),
                    'volume_end': round(volume_end, 2),
                    'volume_mean': round(df_volume['volume'].mean(), 2),
                    'volume_change_percent': round(volume_change_pct, 4),
                    'volume_trend': 'increasing' if volume_change_pct > 5 else 'decreasing' if volume_change_pct < -5 else 'stable'
                }
            
            # Market cap analysis (if available)
            if 'market_caps' in market_data and market_data['market_caps']:
                mcap_data = market_data['market_caps']
                df_mcap = pd.DataFrame(mcap_data, columns=['timestamp', 'market_cap'])
                
                mcap_start = df_mcap['market_cap'].iloc[0]
                mcap_end = df_mcap['market_cap'].iloc[-1]
                mcap_change_pct = ((mcap_end - mcap_start) / mcap_start) * 100 if mcap_start > 0 else 0
                
                analysis['market_cap_analysis'] = {
                    'market_cap_start': round(mcap_start, 2),
                    'market_cap_end': round(mcap_end, 2),
                    'market_cap_change_percent': round(mcap_change_pct, 4),
                    'market_cap_trend': 'growing' if mcap_change_pct > 2 else 'shrinking' if mcap_change_pct < -2 else 'stable'
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in full asset analysis for {asset_id}: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def format_analysis_for_llm(self, analysis: Dict[str, Any]) -> str:
        """
        Format analysis results into a text summary suitable for LLM consumption
        
        Args:
            analysis: Analysis dictionary from get_asset_full_analysis
            
        Returns:
            Formatted text summary
        """
        if 'error' in analysis:
            return f"Analysis Error: {analysis['error']}"
        
        try:
            asset_id = analysis.get('asset_id', 'Unknown')
            days = analysis.get('analysis_period_days', 'Unknown')
            
            summary_parts = [
                f"=== MARKET ANALYSIS: {asset_id.upper()} ({days} day period) ===\n"
            ]
            
            # Price analysis section
            if 'price_analysis' in analysis:
                price = analysis['price_analysis']
                summary_parts.append(
                    f"PRICE MOVEMENT:\n"
                    f"• Start: ${price.get('price_start', 'N/A')}\n"
                    f"• End: ${price.get('price_end', 'N/A')}\n"
                    f"• Change: {price.get('variation_percent', 'N/A')}% ({price.get('variation_absolute', 'N/A')})\n"
                    f"• Range: ${price.get('price_min', 'N/A')} - ${price.get('price_max', 'N/A')}\n"
                    f"• Volatility: {price.get('volatility_percent', 'N/A')}%\n"
                )
                
                summary_parts.append(
                    f"TREND ANALYSIS:\n"
                    f"• Direction: {price.get('trend_direction', 'N/A')}\n"
                    f"• Strength: {price.get('trend_strength', 'N/A')} (R²: {price.get('trend_r_squared', 'N/A')})\n"
                    f"• Support Level: ${price.get('support_level', 'N/A')}\n"
                    f"• Resistance Level: ${price.get('resistance_level', 'N/A')}\n"
                )
            
            # Volume analysis section
            if 'volume_analysis' in analysis:
                volume = analysis['volume_analysis']
                summary_parts.append(
                    f"VOLUME ANALYSIS:\n"
                    f"• Trend: {volume.get('volume_trend', 'N/A')}\n"
                    f"• Change: {volume.get('volume_change_percent', 'N/A')}%\n"
                    f"• Average: ${volume.get('volume_mean', 'N/A'):,.0f}\n"
                )
            
            # Market cap analysis section
            if 'market_cap_analysis' in analysis:
                mcap = analysis['market_cap_analysis']
                summary_parts.append(
                    f"MARKET CAP ANALYSIS:\n"
                    f"• Trend: {mcap.get('market_cap_trend', 'N/A')}\n"
                    f"• Change: {mcap.get('market_cap_change_percent', 'N/A')}%\n"
                    f"• Current: ${mcap.get('market_cap_end', 'N/A'):,.0f}\n"
                )
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ Error formatting analysis for LLM: {e}")
            return f"Formatting Error: {str(e)}"

# Global instance for easy import
asset_analyzer = AssetAnalyzer()

# Helper functions for easy use
def analyze_asset(asset_id: str, days: int = 1) -> Dict[str, Any]:
    """Quick helper to analyze an asset"""
    return asset_analyzer.get_asset_full_analysis(asset_id, days)

def get_asset_summary_for_llm(asset_id: str, days: int = 1) -> str:
    """Quick helper to get LLM-ready asset summary"""
    analysis = asset_analyzer.get_asset_full_analysis(asset_id, days)
    return asset_analyzer.format_analysis_for_llm(analysis)