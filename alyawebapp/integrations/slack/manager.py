import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class SlackManager:
    @classmethod
    def send_message(cls, user_integration, channel, message):
        """Envoie un message sur un canal Slack"""
        try:
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "channel": channel,
                "text": message
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur envoi message Slack: {str(e)}")
            raise

    @classmethod
    def get_message_reactions(cls, user_integration, channel, message_ts):
        """Récupère les réactions à un message"""
        try:
            url = "https://slack.com/api/reactions.get"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}"
            }
            
            params = {
                "channel": channel,
                "timestamp": message_ts
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur récupération réactions Slack: {str(e)}")
            raise

    @classmethod
    def get_message_replies(cls, user_integration, channel, thread_ts):
        """Récupère les réponses à un message"""
        try:
            url = "https://slack.com/api/conversations.replies"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}"
            }
            
            params = {
                "channel": channel,
                "ts": thread_ts
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur récupération réponses Slack: {str(e)}")
            raise 