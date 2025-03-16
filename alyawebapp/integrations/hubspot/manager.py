import logging
from .handler import HubSpotHandler
from django.conf import settings
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class HubSpotManager:
    @classmethod
    def execute_action(cls, user_integration, method_name, params):
        """
        Exécute une action HubSpot
        """
        try:
            # Récupérer la configuration complète
            config = {
                'access_token': user_integration.access_token,
                'refresh_token': user_integration.refresh_token,
                'client_id': settings.HUBSPOT_CLIENT_ID,
                'client_secret': settings.HUBSPOT_CLIENT_SECRET,
                'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
                **user_integration.config  # Ajouter toute configuration supplémentaire
            }

            # Créer le handler avec les tokens de l'utilisateur
            handler = HubSpotHandler(config)

            # Vérifier que la méthode existe
            if not hasattr(handler, method_name):
                raise Exception(f"Méthode {method_name} non trouvée pour HubSpot")

            # Exécuter la méthode
            method = getattr(handler, method_name)
            if method_name == 'create_contact':
                # Valider les champs requis pour un contact
                if not params.get('email') or not params.get('firstname'):
                    raise ValueError("L'email et le prénom sont requis pour créer un contact")
                try:
                    result = method(properties=params)
                   
                    # Si les tokens ont été rafraîchis, les mettre à jour
                    if handler.access_token != user_integration.access_token:
                        user_integration.access_token = handler.access_token
                        user_integration.refresh_token = handler.refresh_token
                        user_integration.save()
                       
                except Exception as e:
                    logger.error(f"Erreur lors de la création du contact: {str(e)}")
                    raise
            elif method_name == 'create_company':
                # Valider les champs requis pour une compagnie
                if not params.get('name'):
                    raise ValueError("Le nom est requis pour créer une compagnie")
                result = method(properties=params)
            else:
                result = method(**params)

            return {
                'success': True,
                'contact_id': result.get('id') if result else None
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {method_name} sur HubSpot: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def create_contact(cls, user_integration, contact_info):
        """Crée un contact dans HubSpot"""
        try:
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}",
                "Content-Type": "application/json"
            }
            
            # Préparer les propriétés du contact
            properties = {
                "firstname": contact_info.get('firstname'),
                "lastname": contact_info.get('lastname'),
                "email": contact_info.get('email'),
                "phone": contact_info.get('phone'),
                "company": contact_info.get('company'),
                "jobtitle": contact_info.get('jobtitle')
            }
            
            # Nettoyer les propriétés None
            properties = {k: v for k, v in properties.items() if v is not None}
            
            data = {
                "properties": properties
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur création contact HubSpot: {str(e)}")
            raise

    @classmethod
    def add_note_to_contact(cls, user_integration, contact_id, note_content):
        """Ajoute une note à un contact"""
        try:
            url = f"https://api.hubapi.com/crm/v3/objects/notes"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "properties": {
                    "hs_note_body": note_content,
                    "hs_timestamp": datetime.now().isoformat()
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [{"category": "HUBSPOT_DEFINED", "typeId": 1}]
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur ajout note HubSpot: {str(e)}")
            raise

    @classmethod
    def schedule_followup(cls, user_integration, contact_id, date, task_description):
        """Programme un suivi pour un contact"""
        try:
            url = f"https://api.hubapi.com/crm/v3/objects/tasks"
            headers = {
                "Authorization": f"Bearer {user_integration.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "properties": {
                    "hs_task_body": task_description,
                    "hs_task_subject": "Suivi contact",
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": "HIGH",
                    "hs_timestamp": date.isoformat()
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [{"category": "HUBSPOT_DEFINED", "typeId": 1}]
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur programmation suivi HubSpot: {str(e)}")
            raise 