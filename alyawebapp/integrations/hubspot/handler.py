from ..base import BaseIntegration
import requests
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import urlencode
import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import redirect
from django.http import HttpResponse

# Importer le modèle UserIntegration
from alyawebapp.models import UserIntegration
from alyawebapp.services.ai_orchestrator import AIOrchestrator  # Import the orchestrator

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
            url = "https://api.hubapi.com/oauth/v1/token"
            data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(
                url,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=data
            )
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens.get('refresh_token', self.refresh_token)
            
            # Mettre à jour les headers avec le nouveau token
            self.headers['Authorization'] = f'Bearer {self.access_token}'
            
            # Mettre à jour la configuration dans la base de données
            if hasattr(self, 'user') and hasattr(self, 'integration'):
                user_integration = UserIntegration.objects.get(
                    user=self.user,
                    integration=self.integration
                )
                user_integration.config.update({
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token
                })
                user_integration.save()
                logger.info("Token d'accès HubSpot rafraîchi avec succès")
            
            return tokens
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du token HubSpot: {str(e)}")
            raise

    def create_contact(self, properties):
        """
        Crée un contact dans HubSpot
        properties: dict avec les propriétés du contact
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts"
            
            # Formater les propriétés pour l'API HubSpot
            data = {
                "properties": {
                    "email": properties.get('email'),
                    "firstname": properties.get('firstname'),
                    "lastname": properties.get('lastname'),
                    "phone": properties.get('phone')
                }
            }
            
            # Premier essai
            try:
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                }
                response = requests.post(url, headers=headers, json=data)
                
                # Si le token est expiré, on le rafraîchit et on réessaie
                if response.status_code == 401:
                    logger.info("Token expiré, tentative de rafraîchissement...")
                    self.refresh_access_token()
                    
                    # Mettre à jour les headers avec le nouveau token
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    
                    # Réessayer avec le nouveau token
                    response = requests.post(url, headers=headers, json=data)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                error_message = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    error_message = e.response.text
                logger.error(f"Erreur lors de la création du contact: {error_message}")
                raise Exception(f"Erreur lors de la création du contact: {error_message}")
            
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

    def refresh_access_token_silently(self, user_id):
        try:
            user_integration = UserIntegration.objects.get(user_id=user_id, integration__name__iexact='hubspot crm')
            refresh_token = user_integration.config.get('refresh_token')
            
            if not refresh_token:
                logger.error("No refresh token available")
                return None

            # Request a new access token using the refresh token
            response = requests.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    'grant_type': 'refresh_token',
                    'client_id': 'YOUR_CLIENT_ID',
                    'client_secret': 'YOUR_CLIENT_SECRET',
                    'refresh_token': refresh_token
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code == 200:
                new_token = response.json().get('access_token')
                user_integration.access_token = new_token
                user_integration.save()
                logger.info("Access token refreshed silently")
                return new_token
            else:
                logger.error(f"Failed to refresh token silently: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing token silently: {e}")
            return None

    def add_contact_with_details(self, contact_info: dict) -> dict:
        """Ajoute un nouveau contact avec tous les détails"""
        properties = {
            'firstname': contact_info.get('firstname'),
            'lastname': contact_info.get('lastname'),
            'email': contact_info.get('email'),
            'phone': contact_info.get('phone'),
            'company': contact_info.get('company'),
            'jobtitle': contact_info.get('jobtitle')
        }
        return self.create_contact(properties)

    def schedule_follow_up(self, contact_id: str, date: str, note: str) -> dict:
        """Programme un suivi pour un contact"""
        url = f"{self.API_BASE_URL}/crm/v3/objects/tasks"
        data = {
            'properties': {
                'hs_task_subject': 'Suivi planifié',
                'hs_task_body': note,
                'hs_task_due_date': date,
                'hs_task_status': 'NOT_STARTED',
                'hs_task_priority': 'HIGH'
            },
            'associations': [{
                'to': {'id': contact_id},
                'types': [{'category': 'TASK_CONTACT', 'typeId': 1}]
            }]
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def add_note_to_contact(self, contact_id: str, note: str) -> dict:
        """Ajoute une note à un contact"""
        url = f"{self.API_BASE_URL}/crm/v3/objects/notes"
        data = {
            'properties': {
                'hs_note_body': note
            },
            'associations': [{
                'to': {'id': contact_id},
                'types': [{'category': 'NOTE_CONTACT', 'typeId': 1}]
            }]
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_contact_activities(self, contact_id: str) -> List[dict]:
        """Récupère les dernières activités d'un contact"""
        url = f"{self.API_BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/notes"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get('results', [])

def hubspot_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    # Assuming you have a way to get the user_id from the state or session
    user_id = request.session.get('_auth_user_id')  # Example of getting user_id from session
    
    # Exchange the authorization code for an access token
    response = exchange_code_for_token(code)
    if response.status_code == 200:
        new_token = response.json().get('access_token')
        # Update the token in the database
        orchestrator = AIOrchestrator(user=User.objects.get(id=user_id))
        orchestrator.update_access_token_manually(user_id, new_token)
        return HttpResponse("Token updated successfully")
    else:
        return HttpResponse("Failed to update token", status=400)

def exchange_code_for_token(code):
    # Implement the logic to exchange the authorization code for an access token
    # This typically involves making a POST request to HubSpot's token endpoint
    pass 