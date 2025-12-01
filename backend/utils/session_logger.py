"""
Système de logging basé sur fichiers pour les sessions d'agents.
Chaque session d'analyse génère un fichier de log dédié.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from backend.config.paths import SESSIONS_DIR

class SessionFileLogger:
    """Logger qui écrit chaque session dans un fichier texte dédié"""
    
    def __init__(self, logs_dir: str= str(SESSIONS_DIR) ):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = None
        self.current_file = None
        
    def start_session(self, asset_ticker: str, analysis_type: str) -> str:
        """Démarre une nouvelle session avec un fichier de log dédié"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"{asset_ticker}_{analysis_type}_{timestamp}"
        
        # Créer le fichier de log pour cette session
        log_filename = f"{session_id}.log"
        log_filepath = self.logs_dir / log_filename
        
        self.current_session = {
            'session_id': session_id,
            'asset_ticker': asset_ticker,
            'analysis_type': analysis_type,
            'start_time': datetime.now(),
            'log_file': str(log_filepath)
        }
        
        # Ouvrir le fichier en mode écriture
        self.current_file = open(log_filepath, 'w', encoding='utf-8')
        
        # Écrire l'en-tête de session
        self.write_log("SESSION_START", f"🚀 DÉBUT SESSION {analysis_type.upper()} - {asset_ticker}", {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'asset': asset_ticker,
            'type': analysis_type
        })
        
        return session_id
    
    def write_log(self, step_type: str, message: str, data: Dict[str, Any] = None):
        """Écrit une ligne de log dans le fichier de session"""
        if not self.current_file:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Format lisible pour les humains
        log_line = f"[{timestamp}] {step_type}: {message}\n"
        
        # Si il y a des données, les ajouter de manière lisible
        if data:
            for key, value in data.items():
                # Écrire les prompts/réponses LLM en intégralité, sans troncature
                log_line += f"  └─ {key}: {value}\n"
        
        self.current_file.write(log_line)
        self.current_file.flush()  # Force l'écriture immédiate
    
    def log_llm_exchange(self, agent_name: str, prompt: str, response: str, duration: float = None):
        """Log spécialisé pour les échanges LLM"""
        self.write_log("LLM_EXCHANGE", f"🤖 Échange avec {agent_name}", {
            'agent': agent_name,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'duration_seconds': duration,
            'full_prompt': prompt,
            'full_response': response
        })
    
    def log_decision(self, decision: Dict[str, Any], reasoning: str):
        """Log spécialisé pour les décisions de trading"""
        self.write_log("DECISION", f"🎯 Décision: {decision.get('action', 'UNKNOWN')} {decision.get('asset_ticker', '')}", {
            'action': decision.get('action'),
            'asset': decision.get('asset_ticker'),
            'confidence': decision.get('confidence'),
            'reasoning': reasoning
        })
    
    def log_execution(self, result: Dict[str, Any]):
        """Log spécialisé pour l'exécution des trades"""
        success = result.get('success', False)
        message = result.get('message', 'No message')
        self.write_log("EXECUTION", f"💼 {'✅' if success else '❌'} {message}", result)
    
    def end_session(self, status: str = "COMPLETED"):
        """Termine la session et ferme le fichier"""
        if not self.current_file or not self.current_session:
            return
            
        duration = datetime.now() - self.current_session['start_time']
        
        self.write_log("SESSION_END", f"🏁 FIN SESSION ({status})", {
            'status': status,
            'duration_seconds': duration.total_seconds(),
            'session_id': self.current_session['session_id']
        })
        
        self.current_file.close()
        self.current_file = None
        
        # Retourner le chemin du fichier de log pour référence
        return self.current_session['log_file']
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère la liste des sessions récentes"""
        sessions = []
        
        # Lister tous les fichiers .log dans le répertoire
        for log_file in sorted(self.logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
            if len(sessions) >= limit:
                break
                
            # Extraire les infos du nom de fichier
            stem = log_file.stem  # ETH_daily_analysis_20250729_103000
            parts = stem.split('_')
            if len(parts) >= 4:
                asset = parts[0]
                analysis_type = '_'.join(parts[1:-2])
                date_part = parts[-2]
                time_part = parts[-1]
                
                # Lire les premières lignes pour extraire des infos
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    sessions.append({
                        'session_id': stem,
                        'asset_ticker': asset,
                        'analysis_type': analysis_type,
                        'log_file': str(log_file),
                        'file_size': log_file.stat().st_size,
                        'modified_time': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                        'line_count': len(lines),
                        'preview': '\n'.join(lines[:5]) if lines else ''
                    })
                except Exception as e:
                    print(f"Erreur lecture {log_file}: {e}")
        
        return sessions
    
    def read_session_log(self, session_id: str) -> str:
        """Lit le contenu complet d'un fichier de log de session"""
        log_file = self.logs_dir / f"{session_id}.log"
        
        if not log_file.exists():
            return f"Fichier de log {session_id} non trouvé"
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Erreur lecture du fichier: {e}"

# Instance globale
session_logger = SessionFileLogger()

def get_session_logger() -> SessionFileLogger:
    """Récupère l'instance globale du session logger"""
    return session_logger
