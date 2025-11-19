import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EnvManager:
    """Gestionnaire des variables d'environnement et API keys sécurisées"""
    
    def __init__(self):
        self._load_dotenv()
        
    def _load_dotenv(self):
        """Charge le fichier .env s'il existe"""
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if value and value != f"your_{key.lower()}_here":
                                os.environ[key] = value
                logger.info("Fichier .env chargé avec succès")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du .env: {e}")
        else:
            logger.info("Fichier .env non trouvé, utilisation des variables d'environnement système")
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Récupère une clé API pour un service donné"""
        env_keys = {
            'gemini': 'GEMINI_API_KEY',
            'openai': 'OPENAI_API_KEY', 
            'claude': 'CLAUDE_API_KEY',
            'grok': 'GROK_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'kimi': 'KIMI_API_KEY',
            'qwen': 'QWEN_API_KEY'
        }
        
        env_key = env_keys.get(service.lower())
        if env_key:
            api_key = os.environ.get(env_key, '').strip()
            if api_key and api_key != f"your_{service.lower()}_api_key_here":
                return api_key
        
        return None
    
    def has_api_key(self, service: str) -> bool:
        """Vérifie si une clé API est configurée pour un service"""
        return self.get_api_key(service) is not None
    
    def get_all_configured_services(self) -> list:
        """Retourne la liste des services avec une clé API configurée"""
        services = ['gemini', 'openai', 'claude', 'grok', 'deepseek', 'kimi', 'qwen']
        return [service for service in services if self.has_api_key(service)]

# Instance globale
env_manager = EnvManager()