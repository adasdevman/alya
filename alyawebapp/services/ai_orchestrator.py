import openai
from openai import OpenAIError
from django.conf import settings
import logging
import json
import traceback
from ..utils.openai_utils import call_openai_api, get_system_prompt
from ..models import Chat, ChatHistory, Message
import requests
from alyawebapp.models import Integration, UserIntegration
from django.urls import reverse
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

class AIOrchestrator:
    # Variable de classe pour stocker les états de conversation par utilisateur
    conversation_states = {}
    contact_types = {}  # Nouveau dictionnaire pour stocker les types de contact
    contact_infos = {}  # Nouveau dictionnaire pour stocker les informations de contact

    def __init__(self, user_id):
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.logger.info(f"Initialisation d'AIOrchestrator pour user_id: {self.user_id}")

    @property
    def conversation_state(self):
        return self.conversation_states.get(self.user_id)

    @conversation_state.setter
    def conversation_state(self, value):
        logger.info(f"Changement d'état pour user {self.user_id}: {self.conversation_state} -> {value}")
        self.conversation_states[self.user_id] = value

    @property
    def contact_type(self):
        return self.contact_types.get(self.user_id)

    @contact_type.setter
    def contact_type(self, value):
        self.contact_types[self.user_id] = value

    @property
    def contact_info(self):
        return self.contact_infos.get(self.user_id, {})

    @contact_info.setter
    def contact_info(self, value):
        self.contact_infos[self.user_id] = value

    def reset_contact_state(self):
        """Réinitialise l'état de la création de contact"""
        if self.user_id in self.conversation_states:
            del self.conversation_states[self.user_id]
        if self.user_id in self.contact_types:
            del self.contact_types[self.user_id]
        if self.user_id in self.contact_infos:
            del self.contact_infos[self.user_id]

    def process_message(self, message, chat_id=None):
        """Process a message and return the response"""
        try:
            # Récupérer ou créer le chat
            if chat_id:
                try:
                    chat = Chat.objects.get(id=chat_id, user_id=self.user_id)
                except Chat.DoesNotExist:
                    # Si le chat n'existe pas, en créer un nouveau
                    chat = Chat.objects.create(user_id=self.user_id)
                    self.logger.info(f"Nouveau chat créé avec l'ID: {chat.id}")
            else:
                # Créer un nouveau chat si aucun ID n'est fourni
                chat = Chat.objects.create(user_id=self.user_id)
                self.logger.info(f"Nouveau chat créé avec l'ID: {chat.id}")

            # Sauvegarder le message de l'utilisateur
            Message.objects.create(
                chat=chat,
                content=message,
                is_user=True
            )

            # Générer la réponse
            response = self.generate_response(message, chat)

            # Sauvegarder la réponse de l'assistant
            Message.objects.create(
                    chat=chat,
                content=response,
                is_user=False
            )

            return response

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du message: {str(e)}")
            raise

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
                    model="gpt-4o",
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
                user_id=self.user_id,
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
                new_token = self.refresh_hubspot_token(user_id)
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
        """Rafraîchit le token HubSpot en utilisant le refresh token"""
        try:
            # Récupérer l'intégration de l'utilisateur
            user_integration = UserIntegration.objects.get(
                user_id=user_id,
                integration__name__iexact='hubspot crm'
            )
            
            refresh_token = user_integration.refresh_token
            if not refresh_token:
                self.logger.error("Pas de refresh token disponible pour l'utilisateur")
                return None

            # Paramètres pour le rafraîchissement du token
            url = "https://api.hubapi.com/oauth/v1/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": settings.HUBSPOT_CLIENT_ID,
                "client_secret": settings.HUBSPOT_CLIENT_SECRET,
                "refresh_token": refresh_token
            }

            self.logger.info("Tentative de rafraîchissement du token HubSpot...")
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                tokens = response.json()
                self.logger.info("Token HubSpot rafraîchi avec succès")
                
                # Mettre à jour les tokens dans la base de données
                user_integration.access_token = tokens["access_token"]
                if "refresh_token" in tokens:
                    user_integration.refresh_token = tokens["refresh_token"]
                user_integration.save()
                
                return tokens["access_token"]
            else:
                self.logger.error(f"Échec du rafraîchissement du token HubSpot: {response.status_code} - {response.text}")
                return None

        except UserIntegration.DoesNotExist:
            self.logger.error(f"Intégration HubSpot non trouvée pour l'utilisateur {user_id}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors du rafraîchissement du token HubSpot: {str(e)}")
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
            # Récupérer le token
            if not token:
                user_integration = UserIntegration.objects.get(
                    user_id=self.user_id, 
                    integration__name__iexact='hubspot crm'
                )
                token = user_integration.access_token

                # Vérifier si le token est expiré et le rafraîchir si nécessaire
                if self.is_token_expired(token):
                    self.logger.info("Token HubSpot expiré, tentative de rafraîchissement...")
                    new_token = self.refresh_hubspot_token(self.user_id)
                    if new_token:
                        token = new_token
                    else:
                        self.logger.error("Impossible de rafraîchir le token HubSpot")
                        return None

            # Formater les données pour l'API HubSpot
            formatted_data = {
                "properties": {
                    "firstname": contact_data.get('firstname', ''),
                    "lastname": contact_data.get('lastname', ''),
                    "email": contact_data.get('email', '')
                }
            }

            if 'company' in contact_data:
                formatted_data["properties"]["company"] = contact_data['company']

            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            self.logger.info(f"Envoi de la requête à HubSpot pour créer le contact: {formatted_data}")
            response = requests.post(url, headers=headers, json=formatted_data)
            
            if response.status_code == 401:  # Token expiré
                self.logger.warning("Token expiré détecté pendant la requête, tentative de rafraîchissement...")
                new_token = self.refresh_hubspot_token(self.user_id)
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    response = requests.post(url, headers=headers, json=formatted_data)
            
            if response.status_code == 201:
                self.logger.info("Contact créé avec succès dans HubSpot")
                return response
            else:
                self.logger.error(f"Erreur HubSpot: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi à HubSpot: {str(e)}")
            return None

    def is_token_expired(self, token):
        """Vérifie si le token est expiré"""
        try:
            # Faire une requête test à l'API HubSpot
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)
            return response.status_code == 401
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du token: {str(e)}")
            return True

    def generate_response(self, message, chat):
        try:
            # Log du message reçu
            self.logger.info(f"Message reçu: '{message}'")
            self.logger.info(f"Chat ID: {chat.id}")
            self.logger.info(f"État de la conversation: {self.conversation_state}")

            # Normaliser le message pour la détection
            normalized_message = message.lower().strip('?!., ')

            # Si c'est un nouveau chat ou une demande d'identité
            if (not Message.objects.filter(chat=chat).exists() or 
                any(q in normalized_message for q in ['qui es tu', 'qui est tu', 'qui estu', 'qui es-tu', 'présente toi', 'presente toi'])):
                
                self.logger.info("Génération de la réponse de présentation d'Alya")
                response = ("Bonjour ! Je suis Alya, une intelligence artificielle polyvalente et évolutive. 😊\n\n"
                         "Ma mission est d'assister les utilisateurs dans leurs tâches quotidiennes, qu'elles soient professionnelles ou personnelles. "
                         "Je suis capable d'interagir de manière fluide, naturelle et amicale, tout en adaptant mes réponses au contexte de vos besoins.\n\n"
                         "Je peux vous aider avec :\n"
                         "• La gestion de vos contacts et CRM\n"
                         "• L'automatisation de vos tâches quotidiennes\n"
                         "• La gestion de projets et le suivi de tâches\n"
                         "• L'organisation personnelle et professionnelle\n\n"
                         "Comment puis-je vous assister aujourd'hui ?")
                self.logger.info(f"Réponse Alya: {response[:100]}...")
                return response

            # Si l'utilisateur veut créer un contact (élargi les patterns de détection)
            if any(pattern in normalized_message for pattern in [
                'créer contact', 'nouveau contact', 'ajouter contact', 
                'creer un contact', 'contact hubspot', 'contact avec hubspot',
                'nouveau contact hubspot', 'créer contact hubspot'
            ]):
                self.logger.info("Détection d'une demande de création de contact HubSpot")
                try:
                    hubspot_integration = Integration.objects.get(name__iexact='hubspot crm')
                    has_hubspot = UserIntegration.objects.filter(
                        user_id=self.user_id,
                        integration=hubspot_integration,
                        enabled=True
                    ).exists()
                    
                    self.logger.info(f"HubSpot intégré: {has_hubspot}")

                    if has_hubspot:
                        self.conversation_state = 'contact_type'
                        response = ("Je vais vous aider à créer un contact dans HubSpot. 👤\n\n"
                                  "Quel type de contact souhaitez-vous créer ?\n\n"
                                  "1. Contact Personnel (particulier)\n"
                                  "2. Contact Professionnel (entreprise)")
                        self.logger.info("Début du processus de création de contact")
                    else:
                        response = ("Pour créer un contact dans HubSpot, vous devez d'abord connecter votre compte. 🔌\n\n"
                                  "Voici comment faire :\n"
                                  "1. Cliquez sur l'icône d'intégration dans le menu\n"
                                  "2. Sélectionnez HubSpot CRM\n"
                                  "3. Suivez les étapes de connexion\n\n"
                                  "Voulez-vous que je vous guide dans ce processus ?")
                        self.logger.info("HubSpot non connecté - proposition de configuration")
                    
                    return response

                except Integration.DoesNotExist:
                    self.logger.error("Intégration HubSpot non trouvée dans la base de données")
                    return "Désolée, l'intégration HubSpot n'est pas disponible pour le moment."

            # Si l'utilisateur demande ce qu'Alya peut faire
            if any(word in message.lower() for word in ['que peux-tu faire', 'quelles sont tes fonctionnalités']):
                return ("Je peux vous aider avec plusieurs tâches :\n"
                       "1. Gestion des contacts :\n"
                       "   - Créer des contacts dans HubSpot\n"
                       "   - Mettre à jour les informations des contacts\n\n"
                       "2. Automatisation :\n"
                       "   - Configurer des intégrations\n"
                       "   - Automatiser des tâches répétitives\n\n"
                       "Que souhaitez-vous faire ?")

            # Gérer les étapes de création de contact si une conversation est en cours
            if self.conversation_state:
                return self.handle_contact_creation(message)

            # Log pour les autres types de messages
            self.logger.info("Message non reconnu - utilisation de la réponse par défaut")
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}],
                temperature=0.7,
                max_tokens=150
            )
            
            response = completion.choices[0].message.content
            self.logger.info(f"Réponse OpenAI: {response[:100]}...")
            return response

        except Exception as e:
            self.logger.error(f"Erreur dans generate_response: {str(e)}")
            return "Désolée, une erreur s'est produite. Pouvez-vous reformuler votre demande ?"

    def handle_contact_creation(self, message):
        """Gère le processus de création de contact"""
        try:
            # Vérifier l'état actuel de la conversation
            state = self.conversation_state
            self.logger.info(f"Traitement de l'état: {state}")
            
            if state == 'contact_type':
                message = message.lower().strip()
                if '1' in message or 'personnel' in message or 'particulier' in message:
                    self.conversation_state = 'personal_firstname'
                    return "Parfait, créons un contact personnel. Quel est son prénom ?"
                elif '2' in message or 'professionnel' in message or 'entreprise' in message:
                    self.conversation_state = 'pro_firstname'
                    return "D'accord, créons un contact professionnel. Quel est son prénom ?"
                else:
                    return ("Je n'ai pas compris votre choix. Veuillez répondre par :\n\n"
                           "1. Contact Personnel (particulier)\n"
                           "2. Contact Professionnel (entreprise)")

            elif state == 'personal_firstname':
                self.contact_info = {'firstname': message}
                self.conversation_state = 'personal_lastname'
                return "Très bien ! Maintenant, quel est son nom de famille ?"
                
            elif state == 'personal_lastname':
                self.contact_info['lastname'] = message
                self.conversation_state = 'personal_email'
                return "Parfait ! Quelle est son adresse email ?"
                
            elif state == 'personal_email':
                self.contact_info['email'] = message
                response = self.send_request_to_hubspot(self.contact_info)
                
                if response and response.status_code == 201:
                    self.conversation_state = None
                    self.contact_info = {}
                    return "✅ Super ! Le contact a été créé avec succès dans HubSpot."
                else:
                    return "❌ Désolé, il y a eu un problème lors de la création du contact. Voulez-vous réessayer ?"

            # Si l'état n'est pas reconnu
            self.logger.error(f"État de conversation non géré: {state}")
            return "Désolé, je ne sais pas où nous en étions. Pouvons-nous recommencer ?"

        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion de la création de contact: {str(e)}")
            return "Une erreur est survenue. Pouvons-nous reprendre depuis le début ?"

# Exemple de fonction pour appeler le modèle GPT-4o
def call_gpt_model(model_input):
    # Logique pour appeler l'API OpenAI avec les paramètres fournis
    # Assurez-vous que l'API est correctement configurée et accessible
    try:
        response = openai.ChatCompletion.create(**model_input)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au modèle GPT-4o: {e}")
        return "Désolé, une erreur est survenue lors de la génération de la réponse."
