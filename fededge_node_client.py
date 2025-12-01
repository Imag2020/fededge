#!/usr/bin/env python3
"""
FedEdge Node Client - Ultra Simple
Fichier à copier dans votre application ../fededge/
"""

import json
import platform
import uuid
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import requests

class FedEdgeNodeClient:
    def __init__(self, config_file: str = '.fededge_node.json', api_url: str = 'https://fededge.net/api'):
        self.config_file = Path(__file__).parent / config_file
        self.api_url = api_url
        self.config = self._load_config()
        self.session_id = None

    def _load_config(self) -> Dict[str, Any]:
        """Charger la config du node depuis le fichier JSON"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)

        # Créer une nouvelle config
        config = {
            'node_id': str(uuid.uuid4()),
            'user_email': None,
            'registered': False,
            'version': '0.1.0',  # Version de votre app
            'node_name': None
        }
        self._save_config(config)
        return config

    def _save_config(self, config: Optional[Dict[str, Any]] = None):
        """Sauvegarder la config"""
        if config:
            self.config = config

        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _detect_gpu(self) -> tuple[bool, Optional[str]]:
        """Détecter si GPU disponible"""
        try:
            # Try nvidia-smi
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                gpu_name = result.stdout.strip()
                return (True, gpu_name)
        except:
            pass

        return (False, None)

    def _get_backend_ip(self) -> Optional[str]:
        """Obtenir l'IP publique du backend/node"""
        try:
            # Utiliser un service externe pour obtenir l'IP publique du serveur
            response = requests.get('https://api.ipify.org?format=json', timeout=3)
            if response.status_code == 200:
                return response.json().get('ip')
        except:
            pass
        return None

    def get_system_info(self) -> Dict[str, Any]:
        """Récupérer les infos système"""
        has_gpu, gpu_info = self._detect_gpu()
        backend_ip = self._get_backend_ip()

        return {
            'os': platform.system(),
            'architecture': platform.machine(),
            'has_gpu': has_gpu,
            'gpu_info': gpu_info,
            'backend_ip': backend_ip,  # IP du serveur/node
            'port': 9010  # Port de votre application
        }

    def register_user(self, email: str, name: str = '', client_ip: Optional[str] = None):
        """
        Enregistrer l'utilisateur du node
        Cette fonction sera appelée depuis l'UI quand le user clique sur "Register"

        Args:
            email: Email de l'utilisateur
            name: Nom de l'utilisateur
            client_ip: IP du client frontend (navigateur), si disponible
        """
        print(f"📤 Registering user: email={email}, name={name}")
        print(f"🌐 API URL: {self.api_url}/signup")

        # D'abord, s'inscrire sur le site si pas déjà fait
        try:
            payload = {
                'email': email,
                'name': name,
                'experience': 'developer',
                'contact': ''
            }

            # Ajouter l'IP du client frontend si fournie
            if client_ip:
                payload['client_ip'] = client_ip
                print(f"🌐 Client (frontend) IP: {client_ip}")

            print(f"📦 Payload: {payload}")

            response = requests.post(
                f'{self.api_url}/signup',
                json=payload,
                timeout=10
            )

            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response body: {response.text[:500]}")  # First 500 chars

            # Que ça réussisse ou non (email déjà existant ok), on enregistre localement
            self.config['user_email'] = email
            self.config['node_name'] = name or f"Node-{platform.node()}"
            self.config['registered'] = False  # Sera True quand email vérifié
            self._save_config()
            print(f"💾 Config saved locally")

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': data.get('message', 'Registration successful. Please check your email.'),
                    'needs_verification': True
                }
            else:
                data = response.json()
                return {
                    'success': True,  # On a sauvegardé localement quand même
                    'message': data.get('error', 'Email saved locally'),
                    'needs_verification': True
                }

        except Exception as e:
            # Même en cas d'erreur réseau, on sauvegarde localement
            print(f"❌ Error during registration: {e}")
            self.config['user_email'] = email
            self.config['node_name'] = name or f"Node-{platform.node()}"
            self._save_config()

            return {
                'success': True,
                'message': f'Saved locally. Network error: {str(e)}',
                'needs_verification': True
            }

    def check_registration_status(self) -> Dict[str, Any]:
        """Vérifier si l'email est vérifié"""
        email = self.config.get('user_email')
        if not email:
            return {'registered': False, 'verified': False}

        try:
            response = requests.get(
                f'{self.api_url}/user/status',
                params={'email': email},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('verified'):
                    self.config['registered'] = True
                    self._save_config()

                return {
                    'registered': True,
                    'verified': data.get('verified', False),
                    'user': data
                }
        except:
            pass

        return {'registered': True, 'verified': False}

    def start_session(self, client_ip: Optional[str] = None):
        """Enregistrer le démarrage du node sur le serveur

        Args:
            client_ip: IP du client frontend (navigateur), si disponible
        """
        try:
            system_info = self.get_system_info()

            payload = {
                'node_id': self.config['node_id'],
                'user_email': self.config.get('user_email'),
                'node_name': self.config.get('node_name'),
                'version': self.config['version'],
                **system_info
            }

            # Ajouter l'IP du client frontend si fournie
            if client_ip:
                payload['client_ip'] = client_ip
                print(f"🌐 Client (frontend) IP: {client_ip}")

            # backend_ip dans system_info contient l'IP du backend/node
            print(f"🖥️ Backend (node) IP: {system_info.get('backend_ip')}")
            print(f"📦 Full payload being sent to /node/register:")
            print(f"   {payload}")

            response = requests.post(
                f'{self.api_url}/node/register',
                json=payload,
                timeout=10
            )

            print(f"📥 Response from /node/register: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Response data: {data}")
                self.session_id = data.get('session', {}).get('id')
                print(f"✅ Node registered: {self.config['node_id'][:8]}...")

                if self.config.get('user_email'):
                    print(f"📧 Registered to: {self.config['user_email']}")
                else:
                    print("⚠️  Unregistered node")

                return data
            else:
                print(f"❌ Registration failed: {response.text}")
                return None
        except Exception as e:
            print(f"⚠️  Could not register node: {e}")
            print("   App will run in offline mode")

        return None

    def get_node_info(self) -> Dict[str, Any]:
        """Obtenir les infos du node pour l'affichage dans l'UI"""
        status = self.check_registration_status()

        # Detect OS
        os_name = platform.system()
        os_version = platform.release()
        os_info = f"{os_name} {os_version}"

        # Detect GPU
        has_gpu = self._check_gpu()

        # Get user name from config
        user_name = self.config.get('user_name', self.config.get('node_name', ''))

        return {
            'node_id': self.config['node_id'],
            'user_email': self.config.get('user_email'),
            'user_name': user_name,
            'node_name': self.config.get('node_name'),
            'registered': status.get('registered', False),
            'verified': status.get('verified', False),
            'version': self.config['version'],
            'os': os_info,
            'has_gpu': has_gpu
        }

    def _check_gpu(self) -> bool:
        """Check if GPU is available"""
        try:
            # Try nvidia-smi first
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=2)
            if result.returncode == 0:
                return True
        except:
            pass

        try:
            # Try to import torch and check CUDA
            import torch
            return torch.cuda.is_available()
        except:
            pass

        return False


# ==================================================================
# INTEGRATION ULTRA SIMPLE DANS VOTRE run_server.py
# ==================================================================

def simple_integration_example():
    """
    Exemple d'intégration dans votre run_server.py existant
    """
    # 1. Créer le client au démarrage
    node_client = FedEdgeNodeClient()

    # 2. Enregistrer le node au démarrage (appel au serveur)
    node_client.start_session()

    # 3. Votre code serveur existant
    print("🚀 Starting FedEdge server on port 9010...")
    # ... votre code WebSocket ...

    # 4. Quand le user clique sur "Register" dans l'UI:
    # (vous appelez cette fonction depuis votre WebSocket handler)
    def handle_register_request(email, name):
        result = node_client.register_user(email, name)
        return result  # Envoyer au frontend via WebSocket

    # 5. Pour afficher le statut dans l'UI (remplacer le bouton "Logs"):
    def get_license_status():
        info = node_client.get_node_info()
        return info  # Envoyer au frontend via WebSocket


if __name__ == '__main__':
    # Test rapide
    client = FedEdgeNodeClient()
    print("\n🔧 FedEdge Node Client Test")
    print(f"Node ID: {client.config['node_id']}")
    print(f"Registered: {client.config.get('user_email', 'No')}")

    # Démarrer la session
    client.start_session()

    # Afficher les infos
    info = client.get_node_info()
    print(f"\n📊 Node Info:")
    print(json.dumps(info, indent=2))
