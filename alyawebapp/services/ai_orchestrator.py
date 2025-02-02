from openai import OpenAI, OpenAIError
from django.conf import settings
import logging
import json
import traceback
from ..utils.openai_utils import call_openai_api, get_system_prompt
from ..models import Chat, ChatHistory
import requests
from alyawebapp.models import Integration, UserIntegration
from django.urls import reverse
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

class AIOrchestrator:
    # Variable de classe pour stocker les états de conversation par utilisateur
    conversation_states = {}

    def __init__(self, user=None):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.user = user
        self.user_id = user.id if user else None
        logger.info(f"Initialisation d'AIOrchestrator pour user_id: {self.user_id}")

    @property
    def conversation_state(self):
        return self.conversation_states.get(self.user_id)

    @conversation_state.setter
    def conversation_state(self, value):
        logger.info(f"Changement d'état pour user {self.user_id}: {self.conversation_state} -> {value}")
        self.conversation_states[self.user_id] = value

    def process_message(self, message):
        try:
            logger.info(f"Message reçu: {message}")
            logger.info(f"État actuel de la conversation: {self.conversation_state}")

            message_lower = message.lower()
            create_contact_keywords = ['creer', 'créer', 'nouveau', 'ajouter', 'contact', 'hubspot']
            is_create_contact_request = any(keyword in message_lower for keyword in create_contact_keywords)

            # Si c'est une demande de création de contact HubSpot
            if is_create_contact_request:
                logger.info("Détection d'une demande de création de contact HubSpot")
                if 'particulier' in message_lower:
                    self.conversation_state = 'waiting_for_personal_info'
                    response = """Pour créer un contact particulier, j'ai besoin des informations suivantes :

- Nom
- Prénom
- Email
- Numéro de téléphone (optionnel)

Veuillez fournir ces informations dans l'ordre, une par ligne."""
                    logger.info("Demande d'informations personnelles envoyée")
                    return response
                elif 'professionnel' in message_lower:
                    self.conversation_state = 'waiting_for_pro_info'
                    response = """Pour créer un contact professionnel, j'ai besoin des informations suivantes :

- Nom de l'entreprise
- Nom du contact
- Prénom du contact
- Email professionnel
- Numéro de téléphone
- Poste/Fonction
- Site web de l'entreprise (optionnel)

Veuillez fournir ces informations dans l'ordre, une par ligne."""
                    logger.info("Demande d'informations professionnelles envoyée")
                    return response
                else:
                    self.conversation_state = 'waiting_for_contact_type'
                    response = """Je vais vous aider à créer un contact dans HubSpot. 

Tout d'abord, s'agit-il d'un contact :
1. Professionnel (entreprise)
2. Particulier

Veuillez répondre avec le numéro correspondant."""
                    logger.info(f"Réponse envoyée (demande type contact): {response}")
                    return response

            # Si l'utilisateur répond 1 ou 2 et qu'on attend le type de contact
            elif self.conversation_state == 'waiting_for_contact_type':
                logger.info(f"Réception du type de contact: {message}")
                if message.strip() == "1":
                    self.conversation_state = 'waiting_for_pro_info'
                    response = """Pour créer un contact professionnel, j'ai besoin des informations suivantes :

- Nom de l'entreprise
- Nom du contact
- Prénom du contact
- Email professionnel
- Numéro de téléphone
- Poste/Fonction
- Site web de l'entreprise (optionnel)

Veuillez fournir ces informations dans l'ordre, une par ligne."""
                    logger.info("Demande d'informations professionnelles envoyée")
                    return response
                elif message.strip() == "2":
                    self.conversation_state = 'waiting_for_personal_info'
                    response = """Pour créer un contact particulier, j'ai besoin des informations suivantes :

- Nom
- Prénom
- Email
- Numéro de téléphone (optionnel)

Veuillez fournir ces informations dans l'ordre, une par ligne."""
                    logger.info("Demande d'informations personnelles envoyée")
                    return response

            # Si l'utilisateur fournit les informations du contact
            elif self.conversation_state in ['waiting_for_pro_info', 'waiting_for_personal_info']:
                logger.info("Réception des informations du contact")
                contact_info = self.parse_contact_info(message)
                logger.info(f"Informations parsées: {contact_info}")
                
                if contact_info:
                    result = self.create_hubspot_contact(contact_info)
                    self.conversation_state = None
                    
                    if result is True:
                        response = "Le contact a été créé avec succès dans HubSpot ! Souhaitez-vous créer un autre contact ?"
                    elif isinstance(result, str):
                        response = result  # Utiliser le message d'erreur retourné
                    else:
                        response = "Désolé, une erreur est survenue lors de la création du contact. Voulez-vous réessayer ?"
                else:
                    response = "Je n'ai pas pu traiter toutes les informations. Pouvez-vous les fournir à nouveau, une par ligne ?"
                
                logger.info(f"Réponse envoyée: {response}")
                return response

            # Autres cas - utiliser GPT
            else:
                logger.info("Message non lié à la création de contact, utilisation de GPT")
                self.conversation_state = None
                
                # Appel à GPT
                system_message = """Tu es Alya, une assistante IA experte. 
                Réponds de manière claire, précise et détaillée aux questions des utilisateurs."""
                
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": message}
                ]
                
                logger.info("Envoi de la requête à GPT")
                completion = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                if completion.choices and len(completion.choices) > 0:
                    response = completion.choices[0].message.content
                    logger.info(f"Réponse GPT reçue: {response}")
                    return response
                
                response = "Désolé, je n'ai pas pu générer une réponse."
                logger.error("Aucune réponse reçue de GPT")
                return response

        except Exception as e:
            logger.error(f"Erreur dans le traitement du message: {str(e)}")
            return "Désolé, une erreur est survenue. Pouvez-vous reformuler votre demande ?"

    def process_request(self, user_request, user_domains):
        """
        Traite la requête utilisateur et gère les erreurs
        """
        try:
            logger.info(f"Début du traitement de la requête: {user_request}")
            
            if not user_request:
                raise ValueError("Requête utilisateur vide")

            # Message système pour Alya
            system_message = """Tu es Alya, une assistante IA experte. 
            Réponds de manière claire, précise et détaillée aux questions des utilisateurs."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_request}
            ]

            logger.info(f"Messages envoyés à OpenAI: {json.dumps(messages, indent=2)}")

            try:
                completion = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                logger.info("Réponse OpenAI reçue")
                logger.debug(f"Réponse complète: {completion}")

            except OpenAIError as api_error:
                logger.error(f"Erreur API OpenAI: {str(api_error)}")
                logger.error(traceback.format_exc())
                return {
                    'status': 'error',
                    'message': "Erreur lors de la communication avec l'IA",
                    'error': str(api_error)
                }

            if not hasattr(completion, 'choices') or not completion.choices:
                logger.error("Réponse OpenAI invalide")
                return {
                    'status': 'error',
                    'message': "Réponse invalide de l'API"
                }

            ai_response = completion.choices[0].message.content
            logger.info(f"Réponse extraite: {ai_response}")

            if not ai_response:
                logger.error("Réponse vide reçue")
                return {
                    'status': 'error',
                    'message': "Réponse vide reçue de l'IA"
                }

            response_data = {
                'status': 'success',
                'message': ai_response
            }
            
            logger.info(f"Réponse finale: {json.dumps(response_data, indent=2)}")
            return response_data

        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': "Une erreur inattendue est survenue",
                'error': str(e)
            }

    def create_hubspot_contact(self, contact_info):
        try:
            # Vérifier si l'intégration HubSpot est active
            hubspot_integration = Integration.objects.get(name__iexact='hubspot crm')
            user_integration = UserIntegration.objects.get(
                user=self.user,
                integration=hubspot_integration,
                enabled=True
            )
            
            # Récupérer le token HubSpot
            logger.info(f"Configuration de l'utilisateur pour HubSpot: {user_integration.config}")
            # Vérifier si le token est dans le champ access_token ou dans le champ config
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("Token d'accès HubSpot manquant")
                return "Le token d'accès HubSpot est manquant. Veuillez vous connecter à HubSpot dans la section Intégrations de votre compte."
            
            logger.info(f"Token d'accès HubSpot récupéré: {access_token[:10]}...")  # Log seulement les 10 premiers caractères

            # Préparer les données pour HubSpot
            properties = {
                "email": contact_info['email'],
                "firstname": contact_info['firstname'],
                "lastname": contact_info['lastname'],
                "phone": contact_info['phone']
            }
            
            # Ajouter les champs spécifiques pour un contact professionnel
            if self.conversation_state == 'waiting_for_pro_info':
                properties.update({
                    "company": contact_info['company'],
                    "jobtitle": contact_info['jobtitle'],
                    "website": contact_info['website']
                })
            
            # Créer le contact dans HubSpot
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "properties": properties
            }
            
            logger.info(f"Envoi de la requête à HubSpot avec les données: {data}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                logger.info(f"Contact créé avec succès dans HubSpot: {contact_info['email']}")
                return True
            else:
                error_message = f"Erreur lors de la création du contact HubSpot: {response.text}"
                logger.error(error_message)
                return error_message
            
        except UserIntegration.DoesNotExist:
            error_message = "L'intégration HubSpot n'est pas activée. Veuillez l'activer dans la section Intégrations de votre compte."
            logger.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"Erreur lors de la création du contact HubSpot: {str(e)}"
            logger.error(error_message)
            return error_message

    def parse_contact_info(self, message):
        try:
            # Diviser le message en mots
            words = message.split()
            
            # Initialiser les variables pour stocker les informations
            lastname = firstname = email = phone = None
            
            # Parcourir les mots pour identifier les champs
            for word in words:
                if '@' in word and '.' in word:
                    email = word
                elif word.isdigit() and len(word) >= 10:  # Supposons que le numéro de téléphone a au moins 10 chiffres
                    phone = word
                elif not firstname:
                    firstname = word
                elif not lastname:
                    lastname = word
            
            # Vérifier si nous avons au moins les informations essentielles
            if not (firstname and lastname and email):
                return None
            
            return {
                'lastname': lastname,
                'firstname': firstname,
                'email': email,
                'phone': phone
            }
        except Exception as e:
            logger.error(f"Erreur lors du parsing des informations: {str(e)}")
            return None

    def last_message_was_contact_type(self):
        return self.conversation_state == 'waiting_for_contact_type'

    def last_message_was_contact_info_request(self):
        return self.conversation_state in ['waiting_for_pro_info', 'waiting_for_personal_info']

    def handle_hubspot_request(self, user_id, contact_data):
        try:
            response = self.send_request_to_hubspot(contact_data)
            if response.status_code == 401:  # Token expired
                logger.info("Token expired, attempting silent refresh")
                new_token = self.refresh_access_token_silently(user_id)
                if new_token:
                    logger.info("Token refreshed silently, retrying request")
                    response = self.send_request_to_hubspot(contact_data, token=new_token)
                else:
                    logger.error("Failed to refresh token silently")
                    # Optionally, initiate OAuth flow if silent refresh fails
                    return self.initiate_oauth_flow(user_id)
            return response
        except Exception as e:
            logger.error(f"Error handling HubSpot request: {e}")
            return None

    def initiate_oauth_flow(self, user_id):
        # Construct the OAuth authorization URL
        client_id = 'YOUR_CLIENT_ID'
        redirect_uri = 'YOUR_REDIRECT_URI'
        state = 'YOUR_STATE'  # Use a secure random state
        auth_url = f"https://app.hubspot.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=YOUR_SCOPES&state={state}"
        
        # Redirect the user to the OAuth authorization URL
        return HttpResponseRedirect(auth_url)

    def refresh_hubspot_token(self, user_id):
        try:
            # Logic to refresh the token using the refresh token
            refresh_token = self.get_refresh_token_for_user(user_id)
            if not refresh_token:
                logger.error("No refresh token available")
                return None

            logger.info(f"Using refresh token: {refresh_token[:10]}...")  # Log only part of the token for security
            logger.info("Requesting new access token using refresh token")
            response = self.request_new_access_token(refresh_token)
            logger.info(f"Token refresh response: {response.status_code}, {response.text}")
            if response.status_code == 200:
                new_token = response.json().get('access_token')
                if new_token:
                    logger.info("New access token received, storing it")
                    # Store the new token
                    self.store_new_access_token(user_id, new_token)
                    return new_token
                else:
                    logger.error("No access token received in response")
            else:
                logger.error(f"Failed to refresh token, status code: {response.status_code}, response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error refreshing HubSpot token: {e}")
            return None

    def update_access_token_manually(self, user_id, new_access_token):
        try:
            # Update the access token in the database
            user_integration = UserIntegration.objects.get(user_id=user_id, integration__name__iexact='hubspot crm')
            user_integration.access_token = new_access_token
            user_integration.save()
            logger.info(f"Access token for user {user_id} updated manually.")
        except UserIntegration.DoesNotExist:
            logger.error(f"UserIntegration for user {user_id} not found.")
        except Exception as e:
            logger.error(f"Error updating access token manually: {e}")

    def send_request_to_hubspot(self, contact_data, token=None):
        try:
            # Use the provided token or fetch from the database
            if not token:
                user_integration = UserIntegration.objects.get(user=self.user, integration__name__iexact='hubspot crm')
                token = user_integration.access_token

            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            data = {
                "properties": contact_data
            }
            
            logger.info(f"Sending request to HubSpot with token: {token[:10]}...")  # Log only part of the token for security
            response = requests.post(url, headers=headers, json=data)
            return response
        except Exception as e:
            logger.error(f"Error sending request to HubSpot: {e}")
            return None
