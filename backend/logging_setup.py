# logging_setup.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_file: str = 'app.log', level: int = logging.INFO):
    """
    Configure le logging vers un fichier avec rotation (pour limiter la taille).
    Idempotent : ne reconfigure pas si déjà setup.
    """
    if logging.getLogger().hasHandlers():
        # Déjà configuré, skip pour éviter doublons
        return

    # Crée le dossier si inexistant
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Handler fichier avec rotation (max 5MB, 5 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # Ajoute au root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)

    # Optionnel : Ajoute un handler console pour debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(console_handler)

    logging.info("Logging configuré vers %s", log_file)