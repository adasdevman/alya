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
        self.refresh_token = config.get('refresh_token')
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
            result = response.json()
            
            # Vérifier si le token est valide
            if not result.get('ok', False):
                error = result.get('error', 'unknown_error')
                logger.error(f"Erreur de connexion Slack: {error}")
                
                # Si le token est invalide et que nous avons un refresh token, essayer de le rafraîchir
                if error == 'invalid_auth' and self.refresh_token and self.client_id and self.client_secret:
                    logger.info("Tentative de rafraîchissement du token...")
                    if self.refresh_access_token():
                        logger.info("Token rafraîchi avec succès, nouvelle tentative de connexion")
                        # Réinitialiser les headers avec le nouveau token
                        self.initialize_client()
                        # Réessayer
                        response = requests.get(
                            f"{self.API_BASE_URL}/auth.test",
                            headers=self.headers
                        )
                        return response.status_code == 200 and response.json().get('ok', False)
                
                return False
                
            return True
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

    def refresh_access_token(self) -> bool:
        """Rafraîchit le token d'accès en utilisant le refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            logger.error("Impossible de rafraîchir le token: refresh_token, client_id ou client_secret manquant")
            return False
            
        try:
            url = f"{self.API_BASE_URL}/oauth.v2.access"
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token
            }
            
            logger.info("Envoi de la requête de rafraîchissement du token à Slack...")
            
            response = requests.post(url, data=data)
            
            # Vérifier le code de statut HTTP
            if response.status_code != 200:
                logger.error(f"Échec du rafraîchissement du token. Code de statut HTTP: {response.status_code}")
                try:
                    result = response.json()
                    error_info = result.get('error', 'unknown_error')
                    error_desc = result.get('error_description', 'Pas de description disponible')
                    logger.error(f"Erreur Slack: {error_info} - {error_desc}")
                except Exception as json_error:
                    logger.error(f"Impossible de parser la réponse JSON: {str(json_error)}")
                    logger.error(f"Contenu de la réponse: {response.text[:200]}")
                return False
            
            # Parser la réponse JSON
            try:
                result = response.json()
            except Exception as json_error:
                logger.error(f"Impossible de parser la réponse JSON: {str(json_error)}")
                logger.error(f"Contenu de la réponse: {response.text[:200]}")
                return False
            
            # Vérifier si l'opération a réussi
            if not result.get('ok', False):
                error_info = result.get('error', 'unknown_error')
                error_desc = result.get('error_description', 'Pas de description disponible')
                logger.error(f"Échec du rafraîchissement du token: {error_info} - {error_desc}")
                return False
                
            # Récupérer les nouveaux tokens
            new_access_token = result.get('access_token')
            new_refresh_token = result.get('refresh_token')
            
            if not new_access_token:
                logger.error("Le nouveau access_token est manquant dans la réponse")
                return False
                
            # Vérifier le format du nouveau token (pour le débogage)
            if new_access_token.startswith('xoxe.'):
                logger.info("Nouveau token au format xoxe (format attendu)")
            elif new_access_token.startswith(('xoxb-', 'xoxp-')):
                logger.info("Nouveau token au format xoxb/xoxp (format traditionnel)")
            else:
                logger.warning(f"Format de token inattendu: {new_access_token[:10]}...")
                
            # Mettre à jour les tokens
            logger.info("Mise à jour des tokens avec les nouvelles valeurs")
            self.access_token = new_access_token
            if new_refresh_token:
                logger.info("Un nouveau refresh token a été fourni, mise à jour")
                self.refresh_token = new_refresh_token
            else:
                logger.info("Aucun nouveau refresh token fourni, conservation de l'ancien")
                
            # Recréer les en-têtes avec le nouveau token
            self.initialize_client()
            
            logger.info("Token d'accès rafraîchi avec succès")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors du rafraîchissement du token: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors du rafraîchissement du token: {str(e)}")
            return False

    def verify_token(self) -> bool:
        """Vérifie si le token d'accès est valide et le rafraîchit si nécessaire"""
        if not self.access_token:
            logger.error("Vérification impossible: Token d'accès manquant")
            return False
            
        try:
            # Vérifier si le token a le bon format (pourrait commencer par xoxb- ou xoxe.xoxb-)
            token_format_valid = self.access_token.startswith(('xoxb-', 'xoxp-', 'xoxe.')) 
            if not token_format_valid:
                logger.warning(f"Format de token Slack potentiellement invalide: {self.access_token[:10]}...")
                # Continuer quand même, au cas où le format aurait changé
            
            response = requests.get(
                f"{self.API_BASE_URL}/auth.test",
                headers=self.headers
            )
            result = response.json()
            
            if not result.get('ok', False):
                error = result.get('error', 'unknown_error')
                logger.error(f"Échec de la vérification du token: {error}")
                
                # Si le token est invalide et que nous avons un refresh token, le rafraîchir
                if self.refresh_token and self.client_id and self.client_secret:
                    logger.info("Token invalide, tentative de rafraîchissement...")
                    if self.refresh_access_token():
                        # Mettre à jour les headers avec le nouveau token
                        self.initialize_client()
                        
                        # Vérifier si le nouveau token fonctionne
                        response = requests.get(
                            f"{self.API_BASE_URL}/auth.test",
                            headers=self.headers
                        )
                        if response.json().get('ok', False):
                            logger.info("Token rafraîchi avec succès et vérifié")
                            return True
                        else:
                            logger.error(f"Le nouveau token ne fonctionne pas: {response.json().get('error', 'unknown_error')}")
                            return False
                    else:
                        logger.error("Échec du rafraîchissement du token")
                        return False
                        
                logger.error(f"Token invalide et pas de possibilité de rafraîchissement: {error}")
                return False
                
            # Le token est valide
            logger.info("Token Slack vérifié avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du token: {str(e)}")
            return False

    def send_message(self, channel: str, message: str, thread_ts: str = None) -> Dict[str, Any]:
        """Envoie un message dans un canal Slack"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        # Vérifier le token et essayer de le rafraîchir si nécessaire
        if not self.verify_token():
            raise ValueError("Authentification Slack échouée: Token invalide ou expiré")
            
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
            
        # Vérifier le token et essayer de le rafraîchir si nécessaire
        if not self.verify_token():
            raise ValueError("Authentification Slack échouée: Token invalide ou expiré")
            
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
            
        # Vérifier le token et essayer de le rafraîchir si nécessaire
        if not self.verify_token():
            raise ValueError("Authentification Slack échouée: Token invalide ou expiré")
            
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
            
        # Vérifier le token et essayer de le rafraîchir si nécessaire
        if not self.verify_token():
            raise ValueError("Authentification Slack échouée: Token invalide ou expiré")
            
        url = f"{self.API_BASE_URL}/users.info"
        params = {'user': user_id}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get('user', {})
        
    def get_channels(self) -> List[Dict[str, Any]]:
        """Récupère la liste des canaux accessibles"""
        if not self.access_token:
            raise ValueError("Token d'accès manquant pour l'API Slack")
            
        # Vérifier le token et essayer de le rafraîchir si nécessaire
        if not self.verify_token():
            raise ValueError("Authentification Slack échouée: Token invalide ou expiré")
            
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