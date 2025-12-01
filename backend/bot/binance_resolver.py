"""
Binance Endpoint Resolver with Auto-Fallback
Gère automatiquement les restrictions géographiques et propose des fallbacks
"""

import os
import time
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger("binance_resolver")

# Endpoints Binance Global (miroirs)
BINANCE_GLOBAL = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]

# Endpoint Binance US
BINANCE_US = "https://api.binance.us"

# Fallback pour lecture de prix
COINGECKO_API = "https://api.coingecko.com/api/v3"

class BinanceEndpointResolver:
    """
    Résolveur intelligent d'endpoints Binance avec fallback automatique
    - Détection de région (US vs Global)
    - Cascade sur miroirs Binance
    - Fallback CoinGecko pour prix
    - Cache des endpoints fonctionnels
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "fededge-bot/1.0"})

        # Cache du dernier endpoint fonctionnel (pour optimisation)
        self._working_endpoint = None
        self._last_check = 0
        self._check_interval = 300  # Re-vérifier toutes les 5 minutes

        # Mapping CoinGecko pour fallback prix
        self.coingecko_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binancecoin",
            "XRPUSDT": "ripple",
            "ADAUSDT": "cardano",
            "DOGEUSDT": "dogecoin",
            "SOLUSDT": "solana",
            "DOTUSDT": "polkadot",
            "MATICUSDT": "matic-network",
            "LTCUSDT": "litecoin",
            "UNIUSDT": "uniswap",
            "LINKUSDT": "chainlink",
            "AVAXUSDT": "avalanche-2",
            "ATOMUSDT": "cosmos",
            "TRXUSDT": "tron",
        }

    def is_us_region(self) -> bool:
        """Détecte si on est en région US"""
        # 1. Variable d'environnement explicite
        region = os.getenv("REGION", "").lower()
        if region in {"us", "usa", "united_states"}:
            return True

        # 2. Configuration bot (si BINANCE_BASE_URL pointe vers .us)
        base_url = os.getenv("BINANCE_BASE_URL", "")
        if "binance.us" in base_url:
            return True

        return False

    def get_base_urls(self) -> List[str]:
        """Retourne la liste des URLs à essayer selon la région"""
        if self.is_us_region():
            return [BINANCE_US]
        else:
            # Si un endpoint est en cache et récent, le mettre en premier
            if self._working_endpoint and (time.time() - self._last_check) < self._check_interval:
                urls = [self._working_endpoint]
                urls.extend([u for u in BINANCE_GLOBAL if u != self._working_endpoint])
                return urls
            return BINANCE_GLOBAL

    def test_endpoint(self, base_url: str, timeout: int = 5) -> bool:
        """Teste si un endpoint Binance est accessible"""
        try:
            r = self.session.get(f"{base_url}/api/v3/ping", timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def get_ticker_24h(self, symbol: Optional[str] = None, params: Optional[Dict] = None) -> Any:
        """
        Récupère les données ticker 24h avec fallback automatique

        Args:
            symbol: Symbole à récupérer (ex: "BTCUSDT") ou None pour tous
            params: Paramètres additionnels pour l'API Binance

        Returns:
            JSON response de l'API (dict ou list)

        Raises:
            RuntimeError: Si aucun endpoint ne fonctionne
        """
        path = "/api/v3/ticker/24hr"
        request_params = params or {}

        if symbol:
            request_params["symbol"] = symbol.upper()

        base_urls = self.get_base_urls()

        # Essayer en cascade les endpoints Binance
        for base_url in base_urls:
            url = f"{base_url}{path}"
            try:
                logger.debug(f"Tentative {base_url}...")
                r = self.session.get(url, params=request_params, timeout=10)

                if r.status_code == 200:
                    # Succès : mettre en cache cet endpoint
                    self._working_endpoint = base_url
                    self._last_check = time.time()
                    logger.debug(f"✅ Endpoint fonctionnel: {base_url}")
                    return r.json()

                elif r.status_code in [403, 451]:
                    # Blocage géographique/WAF, essayer le suivant
                    logger.warning(f"⚠️ {base_url} bloqué (HTTP {r.status_code})")
                    continue

                else:
                    logger.warning(f"⚠️ {base_url} erreur HTTP {r.status_code}")

            except requests.RequestException as e:
                logger.warning(f"⚠️ {base_url} erreur réseau: {e}")
                continue

            time.sleep(0.2)  # Petit backoff entre tentatives

        # Fallback CoinGecko (uniquement pour symboles individuels)
        if symbol:
            return self._fallback_coingecko(symbol)

        raise RuntimeError(
            "❌ Impossible d'accéder aux endpoints Binance. "
            "Vérifiez votre configuration réseau ou utilisez un proxy/VPN."
        )

    def _fallback_coingecko(self, symbol: str) -> Dict[str, Any]:
        """
        Fallback: récupère le prix depuis CoinGecko
        Retourne un format compatible avec Binance ticker/24hr
        """
        coin_id = self.coingecko_map.get(symbol.upper())
        if not coin_id:
            raise RuntimeError(f"Symbole {symbol} non supporté pour fallback CoinGecko")

        try:
            logger.info(f"🔄 Fallback CoinGecko pour {symbol}...")
            url = f"{COINGECKO_API}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }

            r = self.session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if coin_id in data:
                    coin_data = data[coin_id]

                    # Format compatible Binance
                    return {
                        "symbol": symbol.upper(),
                        "lastPrice": str(coin_data.get("usd", 0)),
                        "priceChangePercent": str(coin_data.get("usd_24h_change", 0)),
                        "quoteVolume": str(coin_data.get("usd_24h_vol", 0)),
                        # Champs manquants mis à 0
                        "highPrice": "0",
                        "lowPrice": "0",
                        "_source": "coingecko"  # Flag pour debug
                    }

            raise RuntimeError(f"CoinGecko API erreur HTTP {r.status_code}")

        except requests.RequestException as e:
            raise RuntimeError(f"CoinGecko fallback échoué: {e}")

    def get_klines(self, symbol: str, interval: str, limit: int = 500,
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[List]:
        """
        Récupère les klines avec fallback automatique

        Args:
            symbol: Symbole (ex: "BTCUSDT")
            interval: Intervalle (ex: "5m", "1h")
            limit: Nombre de klines
            start_time: Timestamp début (ms)
            end_time: Timestamp fin (ms)

        Returns:
            Liste de klines au format Binance
        """
        path = "/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }

        if start_time:
            params["startTime"] = int(start_time)
        if end_time:
            params["endTime"] = int(end_time)

        base_urls = self.get_base_urls()

        for base_url in base_urls:
            url = f"{base_url}{path}"
            try:
                r = self.session.get(url, params=params, timeout=15)

                if r.status_code == 200:
                    self._working_endpoint = base_url
                    self._last_check = time.time()
                    return r.json()

                elif r.status_code in [403, 451]:
                    logger.warning(f"⚠️ {base_url} bloqué pour klines (HTTP {r.status_code})")
                    continue

            except requests.RequestException as e:
                logger.warning(f"⚠️ {base_url} erreur klines: {e}")
                continue

            time.sleep(0.2)

        raise RuntimeError(
            f"❌ Impossible de récupérer klines pour {symbol}. "
            "Tous les endpoints Binance sont inaccessibles."
        )

    def find_working_endpoint(self) -> Optional[str]:
        """
        Trouve et retourne le premier endpoint Binance fonctionnel
        Utile pour diagnostic
        """
        logger.info("🔍 Recherche d'un endpoint Binance fonctionnel...")

        for base_url in self.get_base_urls():
            if self.test_endpoint(base_url):
                logger.info(f"✅ Endpoint trouvé: {base_url}")
                self._working_endpoint = base_url
                self._last_check = time.time()
                return base_url
            else:
                logger.warning(f"❌ Endpoint inaccessible: {base_url}")

        logger.error("❌ Aucun endpoint Binance accessible")
        return None


# Instance globale (singleton)
_resolver = None

def get_resolver() -> BinanceEndpointResolver:
    """Retourne l'instance globale du resolver"""
    global _resolver
    if _resolver is None:
        _resolver = BinanceEndpointResolver()
    return _resolver


# Fonctions de compatibilité avec l'ancien code
def fetch_24h_ticker(symbol: Optional[str] = None) -> Any:
    """Wrapper de compatibilité pour fetch_all_24h"""
    return get_resolver().get_ticker_24h(symbol)


def fetch_klines(symbol: str, interval: str, limit: int = 500) -> List[List]:
    """Wrapper de compatibilité pour fetch_klines"""
    return get_resolver().get_klines(symbol, interval, limit)
