from ..base import BaseIntegration
import requests
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import urlencode
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

class HubSpotHandler(BaseIntegration):
    AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    API_BASE_URL = "https://api.hubapi.com"
    
    # Scopes selon la documentation HubSpot OAuth 2.0
    REQUIRED_SCOPES = [
        "oauth",  # Toujours requis
        "crm.objects.contacts.read",  # Lecture des contacts
        "crm.objects.contacts.write",  # Écriture des contacts
        "crm.objects.companies.read",  # Lecture des compagnies
        "crm.objects.companies.write"  # Écriture des compagnies
    ]
    
    # Scopes optionnels
    OPTIONAL_SCOPES = [
        "crm.objects.companies.read",
        "crm.objects.companies.write",
        "crm.objects.leads.read",
        "crm.objects.leads.write"
    ]

    def __init__(self, config):
        """Initialise le handler HubSpot"""
        # Sauvegarder la config d'abord
        self.config = config
        
        # Valider la configuration
        self.validate_config(self.config)
        
        # Extraire les informations de configuration
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.redirect_uri = config['redirect_uri']
        self.access_token = config.get('access_token')
        self.refresh_token = config.get('refresh_token')
        
        # Initialiser le client
        self.initialize_client()

    def initialize_client(self) -> None:
        """Initialise le client HubSpot avec les configurations"""
        self.base_url = self.API_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.access_token}' if self.access_token else None,
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> bool:
        """Teste la connexion à l'API HubSpot"""
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/crm/v3/objects/contacts",
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion HubSpot: {str(e)}")
            return False

    def validate_config(self, config):
        """Valide la configuration HubSpot"""
        if not isinstance(config, dict):
            raise ValueError("La configuration doit être un dictionnaire")
            
        required_fields = ['client_id', 'client_secret', 'redirect_uri']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Champs requis manquants: {', '.join(missing_fields)}")

    def get_authorization_url(self, state=None):
        """Génère l'URL d'autorisation HubSpot"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.REQUIRED_SCOPES),  # Utiliser un espace comme séparateur
            'response_type': 'code',
            'state': state or str(uuid.uuid4())  # State est requis pour la sécurité
        }
        
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"URL d'autorisation générée: {auth_url}")
        return auth_url

    def exchange_code_for_tokens(self, code):
        """Échange le code d'autorisation contre des tokens"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            logger.info("Tentative d'échange du code d'autorisation...")
            response = requests.post(
                self.TOKEN_URL, 
                data=data, 
                headers=headers
            )
            response.raise_for_status()
            tokens = response.json()
            logger.info("Tokens reçus avec succès")
            return tokens
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'échange du code: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Réponse HubSpot: {e.response.text}")
            raise Exception(f"Échec de l'authentification HubSpot: {str(e)}")

    def get_account_info(self, access_token):
        """Récupère les informations du compte HubSpot"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/oauth/v1/access-tokens/{access_token}", 
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des infos du compte: {str(e)}")
            if response:
                logger.error(f"Réponse HubSpot: {response.text}")
            raise Exception(f"Échec de la récupération des informations du compte: {str(e)}")

    def refresh_access_token(self):
        """Rafraîchit le token d'accès en utilisant le refresh token"""
        try:
            data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens.get('refresh_token', self.refresh_token)
            
            # Mettre à jour les headers avec le nouveau token
            self.headers['Authorization'] = f'Bearer {self.access_token}'
            
            # Retourner les nouveaux tokens pour mise à jour en base
            return tokens
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}")
            raise

    def create_contact(self, properties):
        """
        Crée un contact dans HubSpot
        properties: dict avec les propriétés du contact
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Formater les propriétés pour l'API HubSpot
            data = {
                "properties": {
                    "email": properties.get('email'),
                    "firstname": properties.get('firstname')
                }
            }
            
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    # Token expiré, essayer de le rafraîchir
                    self.refresh_access_token()
                    # Réessayer avec le nouveau token
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.post(url, headers=headers, json=data)
                    response.raise_for_status()
                else:
                    raise
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du contact HubSpot: {str(e)}")
            raise

    def create_company(self, properties):
        """
        Crée une compagnie dans HubSpot
        properties: dict avec les propriétés de la compagnie
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/companies"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Formater les propriétés pour l'API HubSpot
            data = {
                "properties": {
                    "name": properties.get('name'),
                    "domain": properties.get('domain'),
                    "industry": properties.get('industry'),
                    "description": properties.get('description'),
                    "numberofemployees": properties.get('employees'),
                    "website": properties.get('website')
                }
            }
            
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    self.refresh_access_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.post(url, headers=headers, json=data)
                    response.raise_for_status()
                else:
                    raise
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la compagnie HubSpot: {str(e)}")
            raise 