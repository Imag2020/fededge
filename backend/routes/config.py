"""
Configuration Routes
Handles LLM and Embedding configuration endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel

from ..config_manager import config_manager, LLMConfig, LLMType, EmbeddingConfig, EmbeddingType
from ..llm_pool import llm_pool
from ..embeddings_pool import embeddings_pool

router = APIRouter(tags=["config"])


# Pydantic models
class LLMConfigCreate(BaseModel):
    id: str
    name: str
    type: str
    url: str
    model: str = ""
    api_key: str = ""
    is_default: bool = False
    is_active: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    extra_params: dict = {}

class EmbeddingConfigCreate(BaseModel):
    id: str
    name: str
    type: str
    url: str
    model: str = ""
    api_key: str = ""
    is_default: bool = False
    is_active: bool = True
    dimension: int = 768
    timeout: int = 30
    extra_params: dict = {}


@router.get("/llm-config")
async def get_llm_config():
    """Récupérer la configuration LLM actuelle"""
    try:
        llms = config_manager.get_all_llms()
        default_llm = config_manager.get_default_llm()

        llms_data = []
        for llm in llms:
            llm_data = {
                "id": llm.id,
                "name": llm.name,
                "type": llm.type.value,
                "url": llm.url,
                "model": llm.model,
                "is_default": llm.is_default,
                "is_active": llm.is_active,
                "max_tokens": llm.max_tokens,
                "temperature": llm.temperature,
                "timeout": llm.timeout,
                "has_api_key": llm.has_effective_api_key(),  # Vérifie env + config
                "extra_params": llm.extra_params
            }
            llms_data.append(llm_data)

        return {
            "status": "success",
            "llms": llms_data,
            "default_llm_id": default_llm.id if default_llm else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/llm-config")
async def add_llm_config(llm_data: LLMConfigCreate):
    """Ajouter une nouvelle configuration LLM"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"📥 Ajout LLM - ID: {llm_data.id}, Type: {llm_data.type}, Name: {llm_data.name}")

        # Valider le type LLM
        try:
            llm_type = LLMType(llm_data.type)
            logger.info(f"✅ Type LLM validé: {llm_type.value}")
        except ValueError as e:
            error_msg = f"Type LLM non supporté: {llm_data.type}. Types valides: {', '.join([t.value for t in LLMType])}"
            logger.error(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}

        # Créer la configuration
        llm_config = LLMConfig(
            id=llm_data.id,
            name=llm_data.name,
            type=llm_type,
            url=llm_data.url,
            model=llm_data.model,
            api_key=llm_data.api_key,
            is_default=llm_data.is_default,
            is_active=llm_data.is_active,
            max_tokens=llm_data.max_tokens,
            temperature=llm_data.temperature,
            timeout=llm_data.timeout,
            extra_params=llm_data.extra_params
        )
        logger.info(f"📝 Configuration LLM créée: {llm_config}")

        success = config_manager.add_llm(llm_config)
        logger.info(f"💾 Résultat sauvegarde: {success}")

        if success:
            # Recharger le pool LLM
            llm_pool.reload_clients()
            logger.info(f"🔄 Pool LLM rechargé")

            # Reconfigurer DSPy si c'est le nouveau LLM par défaut
            if llm_data.is_default and llm_type.value == "ollama":
                try:
                    import dspy
                    ollama_lm = dspy.LM(
                        model=f"openai/{llm_data.model}",
                        api_base=f"{llm_data.url}/v1",
                        api_key="ollama",
                        max_tokens=llm_data.max_tokens,
                        temperature=llm_data.temperature
                    )
                    dspy.settings.configure(lm=ollama_lm)
                    logger.info(f"🔄 DSPy reconfiguré avec {llm_data.name} ({llm_data.model})")
                except Exception as e:
                    logger.warning(f"⚠️ Erreur reconfiguration DSPy: {e}")

            return {"status": "success", "message": f"LLM {llm_data.name} ajouté avec succès"}
        else:
            error_msg = "Échec de l'ajout du LLM (ID déjà existant ou erreur de sauvegarde)"
            logger.error(f"❌ {error_msg}")
            return {"status": "error", "message": error_msg}
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de l'ajout du LLM: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.put("/llm-config/{llm_id}")
async def update_llm_config(llm_id: str, llm_data: LLMConfigCreate):
    """Mettre à jour une configuration LLM"""
    try:
        # Valider le type LLM
        try:
            llm_type = LLMType(llm_data.type)
        except ValueError:
            return {"status": "error", "message": f"Type LLM non supporté: {llm_data.type}"}

        # Créer la configuration mise à jour
        llm_config = LLMConfig(
            id=llm_id,  # Utiliser l'ID de l'URL
            name=llm_data.name,
            type=llm_type,
            url=llm_data.url,
            model=llm_data.model,
            api_key=llm_data.api_key,
            is_default=llm_data.is_default,
            is_active=llm_data.is_active,
            max_tokens=llm_data.max_tokens,
            temperature=llm_data.temperature,
            timeout=llm_data.timeout,
            extra_params=llm_data.extra_params
        )

        success = config_manager.update_llm(llm_config)
        if success:
            # Recharger le pool LLM
            llm_pool.reload_clients()

            # Reconfigurer DSPy si c'est le LLM par défaut
            if llm_data.is_default and llm_type.value == "ollama":
                try:
                    import dspy
                    ollama_lm = dspy.LM(
                        model=f"openai/{llm_data.model}",
                        api_base=f"{llm_data.url}/v1",
                        api_key="ollama",
                        max_tokens=llm_data.max_tokens,
                        temperature=llm_data.temperature
                    )
                    dspy.settings.configure(lm=ollama_lm)
                    print(f"🔄 DSPy reconfiguré avec {llm_data.name} ({llm_data.model})")
                except Exception as e:
                    print(f"⚠️ Erreur reconfiguration DSPy: {e}")

            return {"status": "success", "message": f"LLM {llm_data.name} mis à jour avec succès"}
        else:
            return {"status": "error", "message": "Échec de la mise à jour du LLM"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/llm-config/{llm_id}")
async def delete_llm_config(llm_id: str):
    """Supprimer une configuration LLM"""
    try:
        success = config_manager.remove_llm(llm_id)
        if success:
            # Recharger le pool LLM
            llm_pool.reload_clients()
            return {"status": "success", "message": "LLM supprimé avec succès"}
        else:
            return {"status": "error", "message": "Échec de la suppression du LLM"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/llm-config/{llm_id}/set-default")
async def set_default_llm(llm_id: str):
    """Définir un LLM comme défaut"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"🎯 Setting default LLM: {llm_id}")

        success = config_manager.set_default_llm(llm_id)

        if success:
            # Recharger le pool LLM
            llm_pool.reload_clients()
            logger.info(f"✅ LLM par défaut changé: {llm_id}")

            # Reconfigurer DSPy si c'est un LLM Ollama
            default_llm = config_manager.get_llm(llm_id)
            if default_llm and default_llm.type.value == "ollama":
                try:
                    import dspy
                    ollama_lm = dspy.LM(
                        model=f"openai/{default_llm.model}",
                        api_base=f"{default_llm.url}/v1",
                        api_key="ollama",
                        max_tokens=default_llm.max_tokens,
                        temperature=default_llm.temperature
                    )
                    dspy.settings.configure(lm=ollama_lm)
                    logger.info(f"🔄 DSPy reconfiguré avec {default_llm.name} ({default_llm.model})")
                except Exception as e:
                    logger.warning(f"⚠️ Erreur reconfiguration DSPy: {e}")

            return {"status": "success", "message": f"LLM par défaut changé"}
        else:
            return {"status": "error", "message": "LLM introuvable"}
    except Exception as e:
        logger.error(f"❌ Erreur lors du changement de LLM par défaut: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/llm-config/{llm_id}/test")
async def test_llm_connection(llm_id: str):
    """Tester la connexion à un LLM spécifique"""
    try:
        is_connected = await llm_pool.test_client(llm_id)
        return {
            "status": "success",
            "connected": is_connected,
            "message": "Connexion réussie" if is_connected else "Connexion échouée"
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "connected": False}


@router.post("/llm-config/reload")
async def reload_llm_config():
    """Recharger la configuration LLM depuis le fichier"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("🔄 Rechargement de la configuration LLM...")
        llm_pool.reload_clients()
        logger.info("✅ Configuration LLM rechargée")
        return {"status": "success", "message": "Configuration LLM rechargée"}
    except Exception as e:
        logger.error(f"❌ Erreur rechargement config: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/llm-config/reconfigure-dspy")
async def reconfigure_dspy():
    """Reconfigurer DSPy avec le LLM par défaut actuel"""
    try:
        default_llm = config_manager.get_default_llm()

        if not default_llm:
            return {"status": "error", "message": "Aucun LLM par défaut configuré"}

        if default_llm.type.value == "ollama":
            import dspy
            ollama_lm = dspy.LM(
                model=f"openai/{default_llm.model}",
                api_base=f"{default_llm.url}/v1",
                api_key="ollama",
                max_tokens=default_llm.max_tokens,
                temperature=default_llm.temperature
            )
            dspy.settings.configure(lm=ollama_lm)
            print(f"🔄 DSPy reconfiguré avec {default_llm.name} ({default_llm.model})")
            return {
                "status": "success",
                "message": f"DSPy reconfiguré avec {default_llm.name} ({default_llm.model})"
            }
        else:
            return {
                "status": "error",
                "message": f"Type LLM {default_llm.type.value} non supporté pour DSPy"
            }

    except Exception as e:
        print(f"❌ Erreur reconfiguration DSPy: {e}")
        return {"status": "error", "message": str(e)}


# ===== Embeddings Configuration Endpoints =====

@router.get("/embeddings-config")
async def get_embeddings_config():
    """Récupérer la configuration des embeddings"""
    try:
        embeddings = config_manager.get_all_embeddings()
        default_embedding = config_manager.get_default_embedding()

        embeddings_data = []
        for emb in embeddings:
            emb_data = {
                "id": emb.id,
                "name": emb.name,
                "type": emb.type.value,
                "url": emb.url,
                "model": emb.model,
                "is_default": emb.is_default,
                "is_active": emb.is_active,
                "dimension": emb.dimension,
                "timeout": emb.timeout,
                "extra_params": emb.extra_params
            }
            embeddings_data.append(emb_data)

        return {
            "status": "success",
            "embeddings": embeddings_data,
            "default_embedding_id": default_embedding.id if default_embedding else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/embeddings-config")
async def add_embedding_config(emb_data: EmbeddingConfigCreate):
    """Ajouter une nouvelle configuration d'embedding"""
    try:
        # Valider le type d'embedding
        try:
            emb_type = EmbeddingType(emb_data.type)
        except ValueError:
            return {"status": "error", "message": f"Type d'embedding non supporté: {emb_data.type}"}

        # Créer la configuration
        embedding_config = EmbeddingConfig(
            id=emb_data.id,
            name=emb_data.name,
            type=emb_type,
            url=emb_data.url,
            model=emb_data.model,
            api_key=emb_data.api_key,
            is_default=emb_data.is_default,
            is_active=emb_data.is_active,
            dimension=emb_data.dimension,
            timeout=emb_data.timeout,
            extra_params=emb_data.extra_params
        )

        success = config_manager.add_embedding(embedding_config)
        if success:
            # Recharger le pool d'embeddings
            embeddings_pool.reload_clients()

            return {"status": "success", "message": f"Embedding {emb_data.name} ajouté avec succès"}
        else:
            return {"status": "error", "message": "Échec de l'ajout de l'embedding"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.put("/embeddings-config/{embedding_id}")
async def update_embedding_config(embedding_id: str, emb_data: EmbeddingConfigCreate):
    """Mettre à jour une configuration d'embedding"""
    try:
        # Valider le type d'embedding
        try:
            emb_type = EmbeddingType(emb_data.type)
        except ValueError:
            return {"status": "error", "message": f"Type d'embedding non supporté: {emb_data.type}"}

        # Créer la configuration mise à jour
        embedding_config = EmbeddingConfig(
            id=embedding_id,  # Utiliser l'ID de l'URL
            name=emb_data.name,
            type=emb_type,
            url=emb_data.url,
            model=emb_data.model,
            api_key=emb_data.api_key,
            is_default=emb_data.is_default,
            is_active=emb_data.is_active,
            dimension=emb_data.dimension,
            timeout=emb_data.timeout,
            extra_params=emb_data.extra_params
        )

        success = config_manager.update_embedding(embedding_config)
        if success:
            # Recharger le pool d'embeddings
            embeddings_pool.reload_clients()

            return {"status": "success", "message": f"Embedding {emb_data.name} mis à jour avec succès"}
        else:
            return {"status": "error", "message": "Échec de la mise à jour de l'embedding"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/embeddings-config/{embedding_id}")
async def delete_embedding_config(embedding_id: str):
    """Supprimer une configuration d'embedding"""
    try:
        success = config_manager.remove_embedding(embedding_id)
        if success:
            # Recharger le pool d'embeddings
            embeddings_pool.reload_clients()
            return {"status": "success", "message": "Embedding supprimé avec succès"}
        else:
            return {"status": "error", "message": "Échec de la suppression de l'embedding"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
