import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from .env_manager import env_manager

from backend.config.paths import CONFIG_DIR

logger = logging.getLogger(__name__)

class LLMType(Enum):
    LLAMACPP = "llamacpp"
    LLAMACPP_SERVER = "llamacpp_server"  # Serveur llama.cpp avec continuous batching
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROK = "grok"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"
    QWEN = "qwen"

class EmbeddingType(Enum):
    OPENAI_COMPATIBLE = "openai_compatible"  # Serveur compatible OpenAI embeddings API
    OLLAMA = "ollama"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"

@dataclass
class LLMConfig:
    id: str
    name: str
    type: LLMType
    url: str
    model: str = ""
    api_key: str = ""
    is_default: bool = False
    is_active: bool = True
    max_tokens: int = 16192
    temperature: float = 0.7
    timeout: int = 30
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}
    
    def get_effective_api_key(self) -> str:
        """Retourne la clé API effective (priorité au .env, sinon config)"""
        # Priorité aux variables d'environnement
        env_key = env_manager.get_api_key(self.type.value)
        if env_key:
            return env_key
        # Sinon utiliser la clé de configuration
        return self.api_key or ""
    
    def has_effective_api_key(self) -> bool:
        """Vérifie si une clé API effective est disponible"""
        return bool(self.get_effective_api_key())

@dataclass
class EmbeddingConfig:
    id: str
    name: str
    type: EmbeddingType
    url: str
    model: str = ""
    api_key: str = ""
    is_default: bool = False
    is_active: bool = True
    dimension: int = 768
    timeout: int = 30
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}

@dataclass
class TradingSimulationConfig:
    id: str
    name: str
    wallet_id: str
    llm_id: str
    strategy: str
    risk_level: str
    budget: float
    is_active: bool = True
    created_at: str = ""
    last_updated: str = ""
    performance_stats: Dict[str, Any] = None

    def __post_init__(self):
        if self.performance_stats is None:
            self.performance_stats = {}

class ConfigManager:
    def __init__(self, config_file:str  = str(CONFIG_DIR)+"/llm_config.json"):
        print("  init Config Manager ", config_file)
        self.config_file = config_file
        self.config_dir = str(CONFIG_DIR)
        self.llm_configs: Dict[str, LLMConfig] = {}
        self.embedding_configs: Dict[str, EmbeddingConfig] = {}
        self.trading_simulations: Dict[str, TradingSimulationConfig] = {}
        self._ensure_config_dir()
        self._load_config()
        self._ensure_default_llm()
        self._ensure_default_embedding()

    def _ensure_config_dir(self):
        """Crée le répertoire de configuration s'il n'existe pas"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def _load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Charger les configurations LLM
                if 'llm_configs' in data:
                    for llm_data in data['llm_configs']:
                        llm_config = LLMConfig(**llm_data)
                        # Convertir le type de string vers enum si nécessaire
                        if isinstance(llm_config.type, str):
                            llm_config.type = LLMType(llm_config.type)
                        self.llm_configs[llm_config.id] = llm_config

                # Charger les configurations d'embeddings
                if 'embedding_configs' in data:
                    for emb_data in data['embedding_configs']:
                        emb_config = EmbeddingConfig(**emb_data)
                        # Convertir le type de string vers enum si nécessaire
                        if isinstance(emb_config.type, str):
                            emb_config.type = EmbeddingType(emb_config.type)
                        self.embedding_configs[emb_config.id] = emb_config

                # Charger les simulations de trading
                if 'trading_simulations' in data:
                    for sim_data in data['trading_simulations']:
                        sim_config = TradingSimulationConfig(**sim_data)
                        self.trading_simulations[sim_config.id] = sim_config

                logger.info(f"Configuration chargée: {len(self.llm_configs)} LLMs, {len(self.embedding_configs)} embeddings, {len(self.trading_simulations)} simulations")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de la configuration: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Crée une configuration par défaut"""
        logger.info("Création de la configuration par défaut")
        # LLM par défaut : llama.cpp server (thread-safe, continuous batching, KV cache)
        default_llm = LLMConfig(
            id="default_llamacpp_server",
            name="llamacpp-server-gemma3-1b",
            type=LLMType.LLAMACPP_SERVER,
            url="http://127.0.0.1:9001",
            model="openai/gemma-3-1b-it-q4_0",
            api_key="dummy",
            is_default=True,
            is_active=True,
            max_tokens=4096,
            temperature=0.7,
            timeout=60,
            extra_params={
                "n_parallel": 4,
                "cont_batching": True
            }
        )
        self.llm_configs[default_llm.id] = default_llm

        # Embedding par défaut : serveur compatible OpenAI
        default_embedding = EmbeddingConfig(
            id="default_embedding",
            name="default-embedding",
            type=EmbeddingType.OPENAI_COMPATIBLE,
            url="http://localhost:9002/v1",
            model="embeddinggemma",
            api_key="",
            is_default=True,
            is_active=True,
            dimension=768,
            timeout=30,
            extra_params={}
        )
        self.embedding_configs[default_embedding.id] = default_embedding

        self._save_config()

    def _ensure_default_llm(self):
        """S'assure qu'il y a toujours un LLM par défaut"""
        default_llms = [llm for llm in self.llm_configs.values() if llm.is_default]
        if not default_llms:
            # Si aucun LLM par défaut, prendre le premier disponible
            if self.llm_configs:
                first_llm = list(self.llm_configs.values())[0]
                first_llm.is_default = True
                self._save_config()
                logger.info(f"LLM par défaut défini: {first_llm.name}")

    def _ensure_default_embedding(self):
        """S'assure qu'il y a toujours un embedding par défaut"""
        default_embeddings = [emb for emb in self.embedding_configs.values() if emb.is_default]
        if not default_embeddings:
            # Si aucun embedding par défaut, prendre le premier disponible
            if self.embedding_configs:
                first_emb = list(self.embedding_configs.values())[0]
                first_emb.is_default = True
                self._save_config()
                logger.info(f"Embedding par défaut défini: {first_emb.name}")

    def _save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        try:
            logger.info(f"💾 Début sauvegarde config dans {self.config_file}")
            logger.info(f"📊 LLMs à sauvegarder: {len(self.llm_configs)}")
            logger.info(f"📊 Embeddings à sauvegarder: {len(self.embedding_configs)}")

            config_data = {
                'llm_configs': [
                    {**asdict(llm), 'type': llm.type.value}
                    for llm in self.llm_configs.values()
                ],
                'embedding_configs': [
                    {**asdict(emb), 'type': emb.type.value}
                    for emb in self.embedding_configs.values()
                ],
                'trading_simulations': [
                    asdict(sim) for sim in self.trading_simulations.values()
                ]
            }

            logger.info(f"📝 Données config préparées: {len(config_data['llm_configs'])} LLMs")

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Configuration sauvegardée avec succès dans {self.config_file}")

            # Vérifier que le fichier existe bien
            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                logger.info(f"✅ Fichier vérifié: {self.config_file} ({file_size} bytes)")
            else:
                logger.error(f"❌ ERREUR: Le fichier n'existe pas après sauvegarde!")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}", exc_info=True)

    # ===== Gestion des LLM =====

    def add_llm(self, llm_config: LLMConfig) -> bool:
        """Ajoute une nouvelle configuration LLM"""
        try:
            logger.info(f"🔍 Tentative d'ajout LLM: {llm_config.id}")
            logger.info(f"📋 LLMs existants: {list(self.llm_configs.keys())}")

            if llm_config.id in self.llm_configs:
                logger.warning(f"❌ LLM avec l'ID {llm_config.id} existe déjà")
                return False

            # Si c'est le premier LLM, le marquer comme défaut
            if not self.llm_configs:
                logger.info(f"📌 Premier LLM, marqué comme défaut")
                llm_config.is_default = True

            # Si on marque ce LLM comme défaut, retirer le statut par défaut des autres
            if llm_config.is_default:
                logger.info(f"📌 Nouveau LLM par défaut, retrait statut des autres")
                for existing_llm in self.llm_configs.values():
                    existing_llm.is_default = False

            self.llm_configs[llm_config.id] = llm_config
            logger.info(f"✅ LLM ajouté à la mémoire: {llm_config.name}")

            self._save_config()
            logger.info(f"💾 Configuration sauvegardée dans {self.config_file}")

            return True
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'ajout du LLM: {e}", exc_info=True)
            return False

    def remove_llm(self, llm_id: str) -> bool:
        """Supprime une configuration LLM"""
        try:
            if llm_id not in self.llm_configs:
                logger.warning(f"LLM avec l'ID {llm_id} n'existe pas")
                return False
            
            # Protéger le LLM système par défaut
            if llm_id == "default_ollama":
                logger.warning(f"Impossible de supprimer le LLM système protégé: {llm_id}")
                return False
            
            llm = self.llm_configs[llm_id]
            
            # Vérifier si des simulations utilisent ce LLM
            dependent_sims = [sim for sim in self.trading_simulations.values() if sim.llm_id == llm_id]
            if dependent_sims:
                logger.warning(f"Impossible de supprimer le LLM {llm_id}: utilisé par {len(dependent_sims)} simulations")
                return False
            
            # Si c'était le LLM par défaut, assigner un nouveau défaut
            if llm.is_default and len(self.llm_configs) > 1:
                # Prendre le premier LLM restant
                remaining_llms = [l for l_id, l in self.llm_configs.items() if l_id != llm_id]
                if remaining_llms:
                    remaining_llms[0].is_default = True
            
            del self.llm_configs[llm_id]
            self._save_config()
            logger.info(f"LLM supprimé: {llm.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du LLM: {e}")
            return False

    def update_llm(self, llm_config: LLMConfig) -> bool:
        """Met à jour une configuration LLM"""
        try:
            if llm_config.id not in self.llm_configs:
                logger.warning(f"LLM avec l'ID {llm_config.id} n'existe pas")
                return False
            
            # Si on marque ce LLM comme défaut, retirer le statut par défaut des autres
            if llm_config.is_default:
                for existing_llm in self.llm_configs.values():
                    if existing_llm.id != llm_config.id:
                        existing_llm.is_default = False
            
            self.llm_configs[llm_config.id] = llm_config
            self._save_config()
            logger.info(f"LLM mis à jour: {llm_config.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du LLM: {e}")
            return False

    def get_llm(self, llm_id: str) -> Optional[LLMConfig]:
        """Récupère une configuration LLM par ID"""
        return self.llm_configs.get(llm_id)

    def get_default_llm(self) -> Optional[LLMConfig]:
        """Récupère le LLM par défaut"""
        for llm in self.llm_configs.values():
            if llm.is_default:
                return llm
        return None

    def get_all_llms(self) -> List[LLMConfig]:
        """Récupère toutes les configurations LLM"""
        return list(self.llm_configs.values())

    def get_active_llms(self) -> List[LLMConfig]:
        """Récupère les LLM actifs"""
        return [llm for llm in self.llm_configs.values() if llm.is_active]

    def reload_config(self):
        """Recharge la configuration depuis le fichier JSON"""
        logger.info("Rechargement de la configuration depuis le fichier")
        self.llm_configs.clear()
        self.trading_simulations.clear()
        self._load_config()
        self._ensure_default_llm()

    def set_default_llm(self, llm_id: str) -> bool:
        """Définit un LLM comme défaut par son ID"""
        try:
            if llm_id not in self.llm_configs:
                logger.warning(f"LLM avec l'ID {llm_id} n'existe pas")
                return False

            # Retirer le statut par défaut de tous les LLMs
            for llm in self.llm_configs.values():
                llm.is_default = False

            # Définir le nouveau LLM par défaut
            self.llm_configs[llm_id].is_default = True
            self._save_config()
            logger.info(f"LLM par défaut changé: {self.llm_configs[llm_id].name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la modification du LLM par défaut: {e}")
            return False

    # ===== Gestion des simulations de trading =====

    def add_trading_simulation(self, sim_config: TradingSimulationConfig) -> bool:
        """Ajoute une nouvelle simulation de trading"""
        try:
            if sim_config.id in self.trading_simulations:
                logger.warning(f"Simulation avec l'ID {sim_config.id} existe déjà")
                return False
            
            # Vérifier que le LLM existe
            if sim_config.llm_id not in self.llm_configs:
                logger.warning(f"LLM avec l'ID {sim_config.llm_id} n'existe pas")
                return False
            
            self.trading_simulations[sim_config.id] = sim_config
            self._save_config()
            logger.info(f"Simulation de trading ajoutée: {sim_config.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la simulation: {e}")
            return False

    def remove_trading_simulation(self, sim_id: str) -> bool:
        """Supprime une simulation de trading"""
        try:
            if sim_id not in self.trading_simulations:
                logger.warning(f"Simulation avec l'ID {sim_id} n'existe pas")
                return False
            
            sim = self.trading_simulations[sim_id]
            del self.trading_simulations[sim_id]
            self._save_config()
            logger.info(f"Simulation de trading supprimée: {sim.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la simulation: {e}")
            return False

    def update_trading_simulation(self, sim_config: TradingSimulationConfig) -> bool:
        """Met à jour une simulation de trading"""
        try:
            if sim_config.id not in self.trading_simulations:
                logger.warning(f"Simulation avec l'ID {sim_config.id} n'existe pas")
                return False
            
            # Vérifier que le LLM existe
            if sim_config.llm_id not in self.llm_configs:
                logger.warning(f"LLM avec l'ID {sim_config.llm_id} n'existe pas")
                return False
            
            self.trading_simulations[sim_config.id] = sim_config
            self._save_config()
            logger.info(f"Simulation de trading mise à jour: {sim_config.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la simulation: {e}")
            return False

    def get_trading_simulation(self, sim_id: str) -> Optional[TradingSimulationConfig]:
        """Récupère une simulation de trading par ID"""
        return self.trading_simulations.get(sim_id)

    def get_all_trading_simulations(self) -> List[TradingSimulationConfig]:
        """Récupère toutes les simulations de trading"""
        return list(self.trading_simulations.values())

    def get_active_trading_simulations(self) -> List[TradingSimulationConfig]:
        """Récupère les simulations actives"""
        return [sim for sim in self.trading_simulations.values() if sim.is_active]

    def get_simulations_by_llm(self, llm_id: str) -> List[TradingSimulationConfig]:
        """Récupère les simulations utilisant un LLM spécifique"""
        return [sim for sim in self.trading_simulations.values() if sim.llm_id == llm_id]

    # ===== Gestion des Embeddings =====

    def add_embedding(self, embedding_config: EmbeddingConfig) -> bool:
        """Ajoute une nouvelle configuration d'embedding"""
        try:
            if embedding_config.id in self.embedding_configs:
                logger.warning(f"Embedding avec l'ID {embedding_config.id} existe déjà")
                return False

            # Si c'est le premier embedding, le marquer comme défaut
            if not self.embedding_configs:
                embedding_config.is_default = True

            # Si on marque cet embedding comme défaut, retirer le statut par défaut des autres
            if embedding_config.is_default:
                for existing_emb in self.embedding_configs.values():
                    existing_emb.is_default = False

            self.embedding_configs[embedding_config.id] = embedding_config
            self._save_config()
            logger.info(f"Embedding ajouté: {embedding_config.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de l'embedding: {e}")
            return False

    def remove_embedding(self, embedding_id: str) -> bool:
        """Supprime une configuration d'embedding"""
        try:
            if embedding_id not in self.embedding_configs:
                logger.warning(f"Embedding avec l'ID {embedding_id} n'existe pas")
                return False

            # Protéger l'embedding système par défaut
            if embedding_id == "default_embedding":
                logger.warning(f"Impossible de supprimer l'embedding système protégé: {embedding_id}")
                return False

            emb = self.embedding_configs[embedding_id]

            # Si c'était l'embedding par défaut, assigner un nouveau défaut
            if emb.is_default and len(self.embedding_configs) > 1:
                # Prendre le premier embedding restant
                remaining_embs = [e for e_id, e in self.embedding_configs.items() if e_id != embedding_id]
                if remaining_embs:
                    remaining_embs[0].is_default = True

            del self.embedding_configs[embedding_id]
            self._save_config()
            logger.info(f"Embedding supprimé: {emb.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'embedding: {e}")
            return False

    def update_embedding(self, embedding_config: EmbeddingConfig) -> bool:
        """Met à jour une configuration d'embedding"""
        try:
            if embedding_config.id not in self.embedding_configs:
                logger.warning(f"Embedding avec l'ID {embedding_config.id} n'existe pas")
                return False

            # Si on marque cet embedding comme défaut, retirer le statut par défaut des autres
            if embedding_config.is_default:
                for existing_emb in self.embedding_configs.values():
                    if existing_emb.id != embedding_config.id:
                        existing_emb.is_default = False

            self.embedding_configs[embedding_config.id] = embedding_config
            self._save_config()
            logger.info(f"Embedding mis à jour: {embedding_config.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'embedding: {e}")
            return False

    def get_embedding(self, embedding_id: str) -> Optional[EmbeddingConfig]:
        """Récupère une configuration d'embedding par ID"""
        return self.embedding_configs.get(embedding_id)

    def get_default_embedding(self) -> Optional[EmbeddingConfig]:
        """Récupère l'embedding par défaut"""
        for emb in self.embedding_configs.values():
            if emb.is_default:
                return emb
        return None

    def get_all_embeddings(self) -> List[EmbeddingConfig]:
        """Récupère toutes les configurations d'embeddings"""
        return list(self.embedding_configs.values())

    def get_active_embeddings(self) -> List[EmbeddingConfig]:
        """Récupère les embeddings actifs"""
        return [emb for emb in self.embedding_configs.values() if emb.is_active]

    def set_default_embedding(self, embedding_id: str) -> bool:
        """Définit un embedding comme défaut par son ID"""
        try:
            if embedding_id not in self.embedding_configs:
                logger.warning(f"Embedding avec l'ID {embedding_id} n'existe pas")
                return False

            # Retirer le statut par défaut de tous les embeddings
            for emb in self.embedding_configs.values():
                emb.is_default = False

            # Définir le nouvel embedding par défaut
            self.embedding_configs[embedding_id].is_default = True
            self._save_config()
            logger.info(f"Embedding par défaut changé: {self.embedding_configs[embedding_id].name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la modification de l'embedding par défaut: {e}")
            return False

# Instance globale du gestionnaire de configuration
config_manager = ConfigManager()