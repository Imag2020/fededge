"""
Configuration des chemins - Compatible Docker et Local

Ce module centralise tous les chemins de fichiers et dossiers.
Il détecte automatiquement l'environnement (Docker vs Local) et adapte les chemins.

Usage:
    from backend.config.paths import DATABASE_URL, PAPERTRADES_DB, LOGS_DIR

Environnements supportés:
    - Local: DATA_DIR=./data (via .env ou variable d'env)
    - Docker: DATA_DIR=/app/data (via docker-compose.yml ou Dockerfile)
"""

import os
from pathlib import Path

# ============================================================================
# Détection de l'environnement
# ============================================================================

def is_docker():
    """Détecte si on est dans un conteneur Docker"""
    return os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV') == 'true'

# ============================================================================
# Configuration des chemins de base
# ============================================================================

# DATA_DIR peut être surchargé par variable d'environnement
# Docker: /app/data (via ENV dans Dockerfile ou docker-compose)
# Local:  ./data (relatif au working directory)
DATA_DIR = os.getenv('DATA_DIR')

if DATA_DIR is None:
    # Pas de variable d'env définie -> Détecter automatiquement
    if is_docker():
        DATA_DIR = '/app/data'
    else:
        # En local : toujours au niveau projet (racine), pas backend/
        # Remonter d'un niveau depuis backend/ pour obtenir la racine du projet
        project_root = Path(__file__).parent.parent.parent
        DATA_DIR = project_root / 'data'

# Convertir en Path pour manipulation facile
DATA_DIR = Path(DATA_DIR)

# ============================================================================
# Chemins des bases de données
# ============================================================================

DATABASES_DIR = DATA_DIR / 'databases'
FEDEDGE_DB = DATABASES_DIR / 'fededge.db'
PAPERTRADES_DB = DATABASES_DIR / 'papertrades.db'

# Pour SQLAlchemy (besoin de format spécial avec sqlite:///)
DATABASE_URL = f"sqlite:///{FEDEDGE_DB.absolute()}"

# ============================================================================
# Chemins des logs
# ============================================================================

LOGS_DIR = DATA_DIR / 'logs'
SESSIONS_DIR = LOGS_DIR / 'sessions'
BOT_LOGS_DIR = LOGS_DIR / 'bot'  # Logs du trading bot
BOT_TRACE_DIR = BOT_LOGS_DIR / 'trace'  # Traces de debug du bot
CHAT_LOG = LOGS_DIR / 'chat.log'
EMBEDDINGS_LOG = LOGS_DIR / 'embeddings.log'
BACKEND_LOG = LOGS_DIR / 'backend.log'
AGENT_V3_LOG = LOGS_DIR / 'agent_v3.log'  # Logs de l'agent v3

# ============================================================================
# Chemins du cache
# ============================================================================

CACHE_DIR = DATA_DIR / 'cache'
MARKET_DATA_CACHE = CACHE_DIR / 'market_data'
NEWS_CACHE = CACHE_DIR / 'news_cache'

# ============================================================================
# Chemins de la config
# ============================================================================

CONFIG_DIR = DATA_DIR / 'config'
LLM_CONFIG = CONFIG_DIR / 'llm_config.json'
BOT_CONFIG = CONFIG_DIR / 'bot_config.json'

# ============================================================================
# Chemins des datasets (fine-tuning DSPy)
# ============================================================================

DATASETS_DIR = DATABASES_DIR / 'datasets'
WORLD_STATE_DB = DATASETS_DIR / 'world_state_sessions.db'
CANDIDATES_DB = DATASETS_DIR / 'candidates_trader_sessions.db'
DECIDER_DB = DATASETS_DIR / 'decider_trader_sessions.db'

# ============================================================================
# Créer les dossiers s'ils n'existent pas
# ============================================================================

def ensure_directories():
    """Crée tous les dossiers nécessaires"""
    dirs = [
        DATA_DIR,
        DATABASES_DIR,
        DATASETS_DIR,
        LOGS_DIR,
        SESSIONS_DIR,
        BOT_LOGS_DIR,
        BOT_TRACE_DIR,
        CACHE_DIR,
        MARKET_DATA_CACHE,
        NEWS_CACHE,
        CONFIG_DIR
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

# Créer les dossiers au chargement du module
ensure_directories()

# ============================================================================
# Info de debug
# ============================================================================

def print_paths_info():
    """Affiche la configuration des chemins (pour debug)"""
    print("=" * 70)
    print("📁 Configuration des Chemins - FedEdge")
    print("=" * 70)
    print(f"🔍 Environnement: {'🐳 Docker' if is_docker() else '💻 Local'}")
    print(f"📂 DATA_DIR: {DATA_DIR.absolute()}")
    print()
    print(f"📊 Bases de données:")
    print(f"   • fededge.db:     {FEDEDGE_DB}")
    print(f"   • papertrades.db: {PAPERTRADES_DB}")
    print(f"   • DATABASE_URL:   {DATABASE_URL}")
    print()
    print(f"📝 Logs:")
    print(f"   • LOGS_DIR:     {LOGS_DIR}")
    print(f"   • SESSIONS_DIR: {SESSIONS_DIR}")
    print(f"   • chat.log:     {CHAT_LOG}")
    print(f"   • embeddings.log: {EMBEDDINGS_LOG}")
    print()
    print(f"💾 Cache:")
    print(f"   • CACHE_DIR: {CACHE_DIR}")
    print()
    print(f"⚙️  Config:")
    print(f"   • CONFIG_DIR: {CONFIG_DIR}")
    print()
    print(f"🎯 Datasets (DSPy fine-tuning):")
    print(f"   • DATASETS_DIR: {DATASETS_DIR}")
    print(f"   • world_state:  {WORLD_STATE_DB.name}")
    print(f"   • candidates:   {CANDIDATES_DB.name}")
    print(f"   • decider:      {DECIDER_DB.name}")
    print("=" * 70)

# Appeler au démarrage si DEBUG activé
if os.getenv('DEBUG_PATHS') == 'true':
    print_paths_info()

# ============================================================================
# Exports pour compatibilité
# ============================================================================

# Exporter les chemins en tant que strings pour compatibilité avec ancien code
FEDEDGE_DB_STR = str(FEDEDGE_DB)
PAPERTRADES_DB_STR = str(PAPERTRADES_DB)
LOGS_DIR_STR = str(LOGS_DIR)
SESSIONS_DIR_STR = str(SESSIONS_DIR)
CACHE_DIR_STR = str(CACHE_DIR)
CONFIG_DIR_STR = str(CONFIG_DIR)

__all__ = [
    # Variables d'environnement
    'is_docker',
    'DATA_DIR',

    # Bases de données
    'DATABASES_DIR',
    'FEDEDGE_DB',
    'PAPERTRADES_DB',
    'DATABASE_URL',

    # Logs
    'LOGS_DIR',
    'SESSIONS_DIR',
    'BOT_LOGS_DIR',
    'BOT_TRACE_DIR',
    'CHAT_LOG',
    'EMBEDDINGS_LOG',
    'BACKEND_LOG',
    'AGENT_V3_LOG',

    # Cache
    'CACHE_DIR',
    'MARKET_DATA_CACHE',
    'NEWS_CACHE',

    # Config
    'CONFIG_DIR',
    'LLM_CONFIG',
    'BOT_CONFIG',

    # Datasets
    'DATASETS_DIR',
    'WORLD_STATE_DB',
    'CANDIDATES_DB',
    'DECIDER_DB',

    # Fonctions
    'ensure_directories',
    'print_paths_info',

    # Exports string (compatibilité)
    'FEDEDGE_DB_STR',
    'PAPERTRADES_DB_STR',
    'LOGS_DIR_STR',
    'SESSIONS_DIR_STR',
    'CACHE_DIR_STR',
    'CONFIG_DIR_STR',
]
