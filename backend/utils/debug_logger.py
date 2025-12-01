"""
Système de logging avancé pour debugging du système de trading IA.
Trace toutes les étapes : collecte → analyse → décision → exécution
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from ..websocket_manager import get_websocket_manager

class DebugLogger:
    """Logger spécialisé pour tracer les opérations de trading IA"""
    
    def __init__(self):
        self.session_logs = []
        self.current_session = None
        
        # Configuration du logger Python standard
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('FEDEDGE_AI_DEBUG')
    
    def start_analysis_session(self, asset_ticker: str, analysis_type: str) -> str:
        """Démarre une nouvelle session d'analyse"""
        session_id = f"{asset_ticker}_{datetime.now().strftime('%H%M%S')}"
        
        self.current_session = {
            'session_id': session_id,
            'asset_ticker': asset_ticker,
            'analysis_type': analysis_type,
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'status': 'STARTED'
        }
        
        self.log_step('SESSION_START', f"🚀 Démarrage analyse {analysis_type} pour {asset_ticker}", {
            'session_id': session_id
        })
        
        return session_id
    
    def log_step(self, step_type: str, message: str, data: Dict[str, Any] = None):
        """Enregistre une étape de l'analyse"""
        timestamp = datetime.now().isoformat()
        
        step = {
            'timestamp': timestamp,
            'step_type': step_type,
            'message': message,
            'data': data or {}
        }
        
        # Ajouter à la session courante
        if self.current_session:
            self.current_session['steps'].append(step)
        
        # Logger dans les logs Python
        self.logger.info(f"[{step_type}] {message}")
        if data:
            self.logger.debug(f"[{step_type}] Data: {json.dumps(data, indent=2)}")
        
        # Diffuser en temps réel au frontend
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - schedule the broadcast
                loop.create_task(self._broadcast_debug_log(step))
            except RuntimeError:
                # No running loop - skip broadcast (probably in thread)
                pass
        except Exception as e:
            # Silently skip broadcast errors (don't spam logs)
            pass
    
    def log_data_collection(self, source: str, success: bool, data_summary: str, raw_data: Any = None):
        """Trace la collecte de données"""
        self.log_step('DATA_COLLECTION', f"📊 {source}: {data_summary}", {
            'source': source,
            'success': success,
            'data_summary': data_summary,
            'raw_data_size': len(str(raw_data)) if raw_data else 0
        })
    
    def log_llm_exchange(self, prompt: str, response: str, model: str = "ollama", duration: float = None):
        """Trace les échanges avec le LLM"""
        self.log_step('LLM_EXCHANGE', f"🤖 Échange LLM ({model})", {
            'model': model,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'duration_seconds': duration,
            'prompt_preview': prompt[:200] + "..." if len(prompt) > 200 else prompt,
            'response_preview': response[:200] + "..." if len(response) > 200 else response,
            'full_prompt': prompt,
            'full_response': response
        })
    
    def log_decision_made(self, decision: Dict[str, Any], reasoning: str, confidence: float):
        """Trace la décision prise par l'IA"""
        self.log_step('DECISION_MADE', f"🎯 Décision: {decision.get('action', 'UNKNOWN')} {self.current_session['asset_ticker'] if self.current_session else 'UNKNOWN'}", {
            'decision': decision,
            'reasoning': reasoning,
            'confidence': confidence,
            'decision_summary': f"{decision.get('action', 'UNKNOWN')} avec {confidence*100:.1f}% de confiance"
        })
    
    def log_execution_attempt(self, decision: Dict[str, Any], execution_result: Any):
        """Trace la tentative d'exécution"""
        success = getattr(execution_result, 'success', False) if execution_result else False
        message = getattr(execution_result, 'message', 'No result') if execution_result else 'No execution result'
        
        self.log_step('EXECUTION_ATTEMPT', f"💼 Exécution: {message}", {
            'decision': decision,
            'success': success,
            'execution_message': message,
            'new_budget': getattr(execution_result, 'new_budget', None) if execution_result else None,
            'order_id': getattr(execution_result, 'order_id', None) if execution_result else None
        })
    
    def log_websocket_broadcast(self, message_type: str, payload_summary: str):
        """Trace les messages WebSocket envoyés"""
        self.log_step('WEBSOCKET_BROADCAST', f"📡 Diffusion {message_type}: {payload_summary}", {
            'message_type': message_type,
            'payload_summary': payload_summary
        })
    
    def log_database_operation(self, operation: str, table: str, success: bool, details: str = ""):
        """Trace les opérations de base de données"""
        self.log_step('DATABASE_OP', f"🗃️ DB {operation} {table}: {'✅' if success else '❌'} {details}", {
            'operation': operation,
            'table': table,
            'success': success,
            'details': details
        })
    
    def log_error(self, error_type: str, error_message: str, exception: Exception = None):
        """Trace les erreurs"""
        error_details = {
            'error_type': error_type,
            'error_message': error_message,
            'exception_type': type(exception).__name__ if exception else None,
            'exception_message': str(exception) if exception else None
        }
        
        self.log_step('ERROR', f"❌ Erreur {error_type}: {error_message}", error_details)
        
        # Logger l'erreur avec le niveau ERROR
        self.logger.error(f"[ERROR] {error_type}: {error_message}")
        if exception:
            self.logger.exception(exception)
    
    def end_analysis_session(self, final_status: str = 'COMPLETED'):
        """Termine la session d'analyse courante"""
        if not self.current_session:
            return
        
        self.current_session['end_time'] = datetime.now().isoformat()
        self.current_session['status'] = final_status
        
        # Calculer la durée
        start_time = datetime.fromisoformat(self.current_session['start_time'])
        end_time = datetime.fromisoformat(self.current_session['end_time'])
        duration = (end_time - start_time).total_seconds()
        
        self.current_session['duration_seconds'] = duration
        
        self.log_step('SESSION_END', f"🏁 Fin session {self.current_session['session_id']} ({duration:.1f}s)", {
            'final_status': final_status,
            'duration_seconds': duration,
            'total_steps': len(self.current_session['steps'])
        })
        
        # Sauvegarder la session
        self.session_logs.append(self.current_session.copy())
        
        # Diffuser le résumé complet de la session
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcast_session_summary())
            except RuntimeError:
                # No running loop - skip broadcast
                pass
        except Exception as e:
            # Silently skip broadcast errors
            pass
        
        self.current_session = None
    
    def get_recent_sessions(self, count: int = 5) -> List[Dict[str, Any]]:
        """Récupère les sessions récentes"""
        return self.session_logs[-count:] if len(self.session_logs) >= count else self.session_logs
    
    def get_current_session(self) -> Dict[str, Any]:
        """Récupère la session courante"""
        return self.current_session
    
    async def _broadcast_debug_log(self, step: Dict[str, Any]):
        """Diffuse un log de debug au frontend via WebSocket"""
        try:
            ws_manager = get_websocket_manager()
            
            message = {
                "type": "debug_log",
                "payload": {
                    "session_id": self.current_session['session_id'] if self.current_session else 'unknown',
                    "step": step,
                    "session_info": {
                        'asset_ticker': self.current_session['asset_ticker'] if self.current_session else 'unknown',
                        'analysis_type': self.current_session['analysis_type'] if self.current_session else 'unknown'
                    }
                }
            }
            
            await ws_manager.broadcast(message)
        except Exception as e:
            self.logger.error(f"Failed to broadcast debug log: {e}")
    
    async def _broadcast_session_summary(self):
        """Diffuse un résumé de session au frontend"""
        try:
            if not self.current_session:
                return
                
            ws_manager = get_websocket_manager()
            
            # Créer un résumé de la session
            summary = {
                'session_id': self.current_session['session_id'],
                'asset_ticker': self.current_session['asset_ticker'],
                'duration_seconds': self.current_session.get('duration_seconds', 0),
                'total_steps': len(self.current_session['steps']),
                'status': self.current_session['status'],
                'key_steps': [
                    step for step in self.current_session['steps'] 
                    if step['step_type'] in ['DATA_COLLECTION', 'LLM_EXCHANGE', 'DECISION_MADE', 'EXECUTION_ATTEMPT']
                ]
            }
            
            message = {
                "type": "debug_session_summary",
                "payload": summary
            }
            
            await ws_manager.broadcast(message)
        except Exception as e:
            self.logger.error(f"Failed to broadcast session summary: {e}")

# Instance globale du debug logger
debug_logger = DebugLogger()

def get_debug_logger() -> DebugLogger:
    """Récupère l'instance globale du debug logger"""
    return debug_logger