from ..base import BaseIntegration
import requests
from typing import Dict, Any, List
import logging
from urllib.parse import urlencode
import json

logger = logging.getLogger(__name__)

class SlackHandler(BaseIntegration):
    AUTH_URL = "https://slack.com/oauth/v2/authorize"
    API_BASE_URL = "https://slack.com/api"
    
    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        self.client_id = config.get('client_id', 'default_id')
        self.client_secret = config.get('client_secret', 'default_secret')
        self.redirect_uri = config.get('redirect_uri', 'default_uri')
        self.access_token = config.get('access_token')
        self.initialize_client()

    def initialize_client(self):
        """Initialise le client Slack"""
        self.headers = {}
        if self.access_token:
            self.headers['Authorization'] = f'Bearer {self.access_token}'
        self.headers['Content-Type'] = 'application/json'
        
    def test_connection(self):
        """Teste la connexion à l'API Slack"""
        if not self.access_token:
            logger.error("Test de connexion impossible: Token d'accès manquant pour l'API Slack")
            return False
            
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/auth.test",
                headers=self.headers
            )
            return response.status_code == 200 and response.json().get('ok', False)
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion Slack: {str(e)}")
            return False

    def validate_config(self, config):
        """Valide la configuration Slack"""
        if not isinstance(config, dict):
            raise ValueError("La configuration doit être un dictionnaire")
            
        # Si nous avons un token d'accès, c'est suffisant pour les appels API
        if 'access_token' in config and config['access_token']:
            return
            
        # Sinon, vérifier que les champs requis pour l'authentification sont présents
        required_fields = ['client_id', 'client_secret', 'redirect_uri']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Champs requis manquants pour l'authentification: {', '.join(missing_fields)}")
            
        # Vérifier si l'erreur est liée à une application non distribuée
        if 'error' in config and config['error'] == 'invalid_team_for_non_distributed_app':
            raise ValueError(
                "Cette application Slack n'est pas configurée pour être distribuée. "
                "Veuillez vérifier les paramètres de distribution de l'application sur api.slack.com/apps"
            )

    def send_message(self, channel: str, message: str, thread_ts: str = None) -> Dict[str, Any]:
        """Envoie un message dans un canal Slack"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        url = f"{self.API_BASE_URL}/chat.postMessage"
        data = {
            'channel': channel,
            'text': message,
            'thread_ts': thread_ts
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_message_reactions(self, channel: str, message_ts: str) -> List[Dict[str, Any]]:
        """Récupère les réactions à un message"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        url = f"{self.API_BASE_URL}/reactions.get"
        params = {
            'channel': channel,
            'timestamp': message_ts
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get('message', {}).get('reactions', [])

    def get_channel_replies(self, channel: str, message_ts: str) -> List[Dict[str, Any]]:
        """Récupère les réponses à un message"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        url = f"{self.API_BASE_URL}/conversations.replies"
        params = {
            'channel': channel,
            'ts': message_ts
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get('messages', [])[1:]  # Exclure le message original

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un utilisateur"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        url = f"{self.API_BASE_URL}/users.info"
        params = {'user': user_id}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get('user', {})
        
    def get_channels(self) -> List[Dict[str, Any]]:
        """Récupère la liste des canaux accessibles"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        url = f"{self.API_BASE_URL}/conversations.list"
        params = {
            'types': 'public_channel,private_channel',
            'exclude_archived': True,
            'limit': 100  # Limiter les résultats pour des performances optimales
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get('channels', [])
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux Slack: {str(e)}")
            return [] 