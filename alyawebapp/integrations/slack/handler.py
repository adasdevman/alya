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
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.redirect_uri = config['redirect_uri']
        self.access_token = config.get('access_token')
        self.initialize_client()

    def initialize_client(self):
        """Initialise le client Slack"""
        self.headers = {
            'Authorization': f'Bearer {self.access_token}' if self.access_token else None,
            'Content-Type': 'application/json'
        }

    def send_message(self, channel: str, message: str, thread_ts: str = None) -> Dict[str, Any]:
        """Envoie un message dans un canal Slack"""
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
        url = f"{self.API_BASE_URL}/users.info"
        params = {'user': user_id}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get('user', {})
        
    def get_channels(self) -> List[Dict[str, Any]]:
        """Récupère la liste des canaux accessibles"""
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