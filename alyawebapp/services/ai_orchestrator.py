import openai
from openai import OpenAIError
from django.conf import settings
import logging
import json
import traceback
from ..utils.openai_utils import get_system_prompt
from ..models import Chat, ChatHistory
import requests
from alyawebapp.models import Integration, UserIntegration
from datetime import datetime, timedelta
from ..utils.retry_handler import RetryHandler
from requests.exceptions import ConnectionError, SSLError, ProxyError
import socket
from urllib3.exceptions import NewConnectionError, MaxRetryError
from django.core.cache import cache
import uuid
from typing import Dict, Any
from .session_utils import SessionState
from .exceptions import NetworkError, AITimeoutError
from .config import (
    API_TIMEOUT, LONG_OPERATION_TIMEOUT, MAX_RETRIES, NETWORK_TIMEOUT, SESSION_TIMEOUT, CACHE_KEY_PREFIX,
    RESPONSE_MODEL, GENERAL_RESPONSES
)
from .handlers import IntentAnalyzer, IntegrationRouter

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Orchestrateur d'IA - version modulaire
    Cette classe orchestre les interactions entre l'utilisateur et les différentes intégrations
    en utilisant une architecture modulaire avec des handlers spécialisés.
    """
    # Variables de classe pour stocker les états
    conversation_states = {}
    contact_types = {}
    contact_infos = {}

    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)
        self.openai_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        self.session_state = self._get_or_create_session()
        self.active_chat = None
        self.conversation_history = []
        self.error_count = 0
        self.max_message_length = 4000
        self.session_retry_count = 0
        
        # Initialiser les composants modulaires
        self.intent_analyzer = IntentAnalyzer(self)
        self.integration_router = IntegrationRouter(self)
        
        self.logger.info(f"Initialisation d'AIOrchestrator modulaire pour user_id: {self.user.id}")

    @property
    def conversation_state(self):
        return self.conversation_states.get(self.user.id)

    @conversation_state.setter
    def conversation_state(self, value):
        logger.info(f"Changement d'état pour user {self.user.id}: {self.conversation_state} -> {value}")
        self.conversation_states[self.user.id] = value

    @property
    def contact_type(self):
        return self.contact_types.get(self.user.id)

    @contact_type.setter
    def contact_type(self, value):
        self.contact_types[self.user.id] = value

    @property
    def contact_info(self):
        return self.contact_infos.get(self.user.id, {})

    @contact_info.setter
    def contact_info(self, value):
        self.contact_infos[self.user.id] = value

    def process_message(self, chat_id: str, message: str) -> str:
        """
        Traite un message utilisateur et retourne une réponse appropriée.
        
        Args:
            chat_id (str): L'ID de la conversation
            message (str): Le message de l'utilisateur
            
        Returns:
            str: La réponse générée
        """
        try:
            # Validation préliminaire du message
            message = self._validate_message(message)
            
            # Vérifier les cas limites
            edge_case_response = self._handle_edge_cases(message)
            if edge_case_response:
                return edge_case_response
                
            # Sauvegarder le message de l'utilisateur
            self._save_user_message(chat_id, message)

            # Détecter le service le plus approprié
            detected_service = self._detect_service_type(message)
            logger.info(f"[ORCHESTRATOR] Service détecté: {detected_service if detected_service else 'Indéterminé'}")

            # Si un service spécifique est détecté, essayer de router directement vers lui
            if detected_service:
                try:
                    # Mapper les noms de services aux noms de classes et de fichiers
                    service_handlers = {
                        "trello": ("TrelloHandler", "trello_handler"),
                        "slack": ("SlackHandler", "slack_handler"),
                        "hubspot": ("HubSpotHandler", "hubspot_handler"),
                        "gmail": ("GmailHandler", "gmail_handler"),
                        "google_drive": ("GoogleDriveHandler", "google_drive_handler"),
                        "salesforce": ("SalesforceHandler", "salesforce_handler"),
                        "quickbooks": ("QuickBooksHandler", "quickbooks_handler"),
                        "mailchimp": ("MailChimpHandler", "mailchimp_handler")
                    }
                    
                    if detected_service in service_handlers:
                        handler_class_name, module_name = service_handlers[detected_service]
                        # Import dynamique du handler
                        handler_module = __import__(f"alyawebapp.services.handlers.{module_name}", 
                                                   fromlist=[handler_class_name])
                        handler_class = getattr(handler_module, handler_class_name)
                        handler = handler_class(self)
                        
                        # Appel de la méthode handle_request du handler
                        response = handler.handle_request(message)
                        self._save_assistant_message(chat_id, response)
                        return response
                        
                except (ImportError, AttributeError) as e:
                    logger.error(f"[ORCHESTRATOR] Erreur lors du routage vers {detected_service}: {str(e)}")
                    logger.error(traceback.format_exc())

            # Si aucun service spécifique n'est détecté ou si le routage direct a échoué,
            # utiliser l'analyseur d'intention et le routeur d'intégration
            intent = self.intent_analyzer.analyze_intent(message)
            response = self.integration_router.route_request(intent, message)
            
            # Sauvegarder la réponse
            self._save_assistant_message(chat_id, response)
            
            return response
            
        except Exception as e:
            error_message = f"Une erreur est survenue : {str(e)}"
            self.logger.error(f"Erreur dans process_message: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._save_assistant_message(chat_id, error_message)
            return error_message

    def _validate_message(self, message):
        """Valide et nettoie le message entrant"""
        if not message or not isinstance(message, str):
            raise ValueError("Le message doit être une chaîne de caractères non vide")

        # Nettoyer les caractères spéciaux et espaces superflus
        message = " ".join(message.split())
        
        # Tronquer si trop long
        if len(message) > self.max_message_length:
            self.logger.warning(f"Message tronqué de {len(message)} à {self.max_message_length} caractères")
            message = message[:self.max_message_length] + "..."

        return message

    def _handle_edge_cases(self, message):
        """Gère les cas limites spécifiques"""
        # Messages vides ou trop courts
        if not message.strip():
            return "Je n'ai pas reçu de message. Que puis-je faire pour vous ?"

        if len(message.strip()) < 2:
            return "Pourriez-vous être plus précis dans votre demande ?"

        # Messages répétitifs
        if len(self.conversation_history) >= 2:
            last_two = [msg['content'] for msg in self.conversation_history[-2:]]
            if message in last_two:
                return "Vous venez de me dire la même chose. Puis-je vous aider différemment ?"

        return None  # Pas de cas limite détecté

    def _get_or_create_chat(self, chat_id):
        """Récupère ou crée un chat"""
        try:
            if chat_id:
                # Récupérer le chat existant
                return Chat.objects.get(id=chat_id, user=self.user)
            else:
                # Créer un nouveau chat
                return Chat.objects.create(user=self.user)
        except Chat.DoesNotExist:
            # Si le chat n'existe pas, en créer un nouveau
            return Chat.objects.create(user=self.user)

    def _get_or_create_active_chat(self):
        """Récupère ou crée un chat actif pour l'utilisateur"""
        try:
            # Chercher un chat actif existant
            active_chat = Chat.objects.filter(
                user=self.user,
                is_active=True
            ).order_by('-created_at').first()
            
            if not active_chat:
                active_chat = Chat.objects.create(
                    user=self.user,
                    is_active=True
                )
            
            return active_chat
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du chat actif: {str(e)}")
            # Créer un nouveau chat en cas d'erreur
            return Chat.objects.create(
                user=self.user,
                is_active=True
            )

    def _save_user_message(self, chat_id, content):
        """Sauvegarde un message utilisateur dans l'historique"""
        try:
            chat = Chat.objects.get(id=chat_id) if chat_id else self._get_or_create_active_chat()
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=content,
                is_user=True
            )
            
            # Mettre à jour l'historique en mémoire
            self.conversation_history.append({
                'role': 'user',
                'content': content
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde du message utilisateur: {str(e)}")

    def _save_assistant_message(self, chat_id, content):
        """Sauvegarde un message assistant dans l'historique"""
        try:
            chat = Chat.objects.get(id=chat_id) if chat_id else self._get_or_create_active_chat()
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=content,
                is_user=False
            )
            
            # Mettre à jour l'historique en mémoire
            self.conversation_history.append({
                'role': 'assistant',
                'content': content
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde du message assistant: {str(e)}")

    def _get_active_integrations(self):
        """Récupère la liste des intégrations actives pour l'utilisateur"""
        try:
            user_integrations = UserIntegration.objects.filter(
                user=self.user,
                enabled=True
            ).select_related('integration')
            
            return [ui.integration.name for ui in user_integrations]
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des intégrations actives: {str(e)}")
            return []

    def _get_or_create_session(self) -> SessionState:
        """Récupère ou crée une session pour l'utilisateur"""
        cache_key = f"{CACHE_KEY_PREFIX}{self.user.id}"
        session_data = cache.get(cache_key)
        
        if session_data:
            session = SessionState.from_dict(session_data)
            # Vérifier si la session n'est pas expirée
            if datetime.now() - session.last_activity < timedelta(seconds=SESSION_TIMEOUT):
                session.last_activity = datetime.now()
                self._save_session(session)
                return session
        
        # Créer une nouvelle session
        session = SessionState(self.user.id)
        self._save_session(session)
        return session

    def _save_session(self, session: SessionState):
        """Sauvegarde l'état de la session dans le cache"""
        cache_key = f"{CACHE_KEY_PREFIX}{self.user.id}"
        cache.set(cache_key, session.to_dict(), timeout=SESSION_TIMEOUT)

    def _update_session_activity(self):
        """Met à jour le timestamp de dernière activité"""
        self.session_state.last_activity = datetime.now()
        self._save_session(self.session_state)

    def _handle_error(self, error, context=None):
        """Gère les erreurs de manière intelligente"""
        self.error_count += 1
        error_msg = str(error)
        
        self.logger.error(f"Erreur ({self.error_count}): {error_msg}")
        if context:
            self.logger.error(f"Contexte: {context}")
        
        # Vérifier d'abord les erreurs réseau
        if isinstance(error, (ConnectionError, SSLError, ProxyError, 
                             socket.error, NewConnectionError, MaxRetryError)):
            return self._handle_network_error(error)

        # Gérer les timeouts
        if isinstance(error, (requests.exceptions.Timeout, AITimeoutError)) or 'timeout' in str(error).lower():
            return "Je mets un peu trop de temps à répondre. Le service semble lent actuellement."
        
        # Gérer différents types d'erreurs OpenAI
        if isinstance(error, openai.OpenAIError):
            if "rate_limit" in error_msg:
                return "Je suis un peu surchargée actuellement. Pouvez-vous réessayer dans quelques secondes ?"
            
        return "Désolée, une erreur s'est produite. Pouvez-vous reformuler votre demande ?"

    def _handle_network_error(self, error):
        """Gère spécifiquement les erreurs réseau"""
        error_msg = str(error).lower()

        # Problèmes de connexion
        if isinstance(error, (ConnectionError, NewConnectionError)):
            return "Je ne peux pas me connecter au serveur. Vérifiez votre connexion internet et réessayez."

        # Problèmes SSL
        if isinstance(error, SSLError):
            return "Il y a un problème de sécurité avec la connexion."

        # Timeouts réseau
        if 'timeout' in error_msg:
            return "La connexion est très lente. Vérifiez votre connexion internet ou réessayez plus tard."

        return "Problème de connexion détecté. Vérifiez votre connexion internet."

    def _detect_service_type(self, text):
        """Détecte le type de service le plus approprié pour traiter cette requête"""
        text_lower = text.lower()
        
        # Définir des mots-clés et phrases spécifiques à chaque service
        service_keywords = {
            "hubspot": [
                "contact", "suivi", "note", "tâche hubspot", "partenariat", "client hubspot", 
                "ajouter contact", "créer contact", "mettre à jour contact", "email",
                "hubspot", "crm", "opportunité", "pipeline"
            ],
            "trello": [
                "carte", "tâche trello", "colonne", "liste", "board", "tableau", "étiquette",
                "déplacer carte", "ajouter carte", "créer carte", "assigner", "en cours",
                "présentation client", "assigner à", "assignée à", "assigné à", "échéance",
                "vendredi", "lundi", "mardi", "mercredi", "jeudi", "samedi", "dimanche",
                "trello", "kanban"
            ],
            "slack": [
                "canal", "channel", "envoyer message", "poster", "message slack", 
                "dm", "message direct", "réaction", "émoji", "slack", "conversation"
            ],
            "gmail": [
                "email", "mail", "gmail", "message", "envoyer email", "envoyer mail",
                "boîte de réception", "pièce jointe", "objet", "destinataire", "cc", "cci",
                "brouillon", "corbeille", "signature", "répondre", "transférer"
            ],
            "google_drive": [
                "document", "fichier", "dossier", "drive", "google drive", "partager",
                "créer document", "télécharger", "uploader", "permission", "collaboration",
                "feuille de calcul", "présentation", "pdf", "accès"
            ],
            "salesforce": [
                "compte", "opportunité", "lead", "piste", "salesforce", "sf", "affaire",
                "montant", "commercial", "pipeline", "prévision", "stade", "statut",
                "contact salesforce", "prospect", "client", "partenaire"
            ],
            "quickbooks": [
                "facture", "paiement", "client quickbooks", "produit", "service", 
                "comptabilité", "tva", "taxe", "devis", "avoir", "remise", "quickbooks",
                "compte bancaire", "transaction", "dépense", "recette", "relevé"
            ],
            "mailchimp": [
                "mailchimp", "newsletter", "campagne", "email marketing", "infolettre",
                "abonné", "liste d'abonnés", "liste de diffusion", "statistiques campagne",
                "taux d'ouverture", "taux de clic", "envoi email", "créer campagne",
                "envoyer newsletter", "inscrire email", "désabonnement", "segmentation"
            ]
        }
        
        # Score initial pour chaque service
        scores = {service: 0 for service in service_keywords}
        
        # Vérifier d'abord les indicateurs forts spécifiques à certains services
        # Trello
        trello_indicators = ["colonne", "en cours", "assigner", "assignée", "assigné", "échéance"]
        if any(indicator in text_lower for indicator in trello_indicators):
            logger.info(f"[ORCHESTRATOR] Indicateurs Trello forts détectés dans: '{text}'")
            return "trello"
            
        # Gmail
        gmail_indicators = ["envoyer email à", "envoyer mail à", "envoyer un email à", "envoyer un mail à"]
        if any(indicator in text_lower for indicator in gmail_indicators):
            logger.info(f"[ORCHESTRATOR] Indicateurs Gmail forts détectés dans: '{text}'")
            return "gmail"
            
        # Slack
        slack_indicators = ["envoyer message sur slack", "poster sur slack", "envoyer sur slack"]
        if any(indicator in text_lower for indicator in slack_indicators):
            logger.info(f"[ORCHESTRATOR] Indicateurs Slack forts détectés dans: '{text}'")
            return "slack"
            
        # MailChimp
        mailchimp_indicators = ["créer une campagne", "ajouter un abonné", "statistiques campagne", "liste d'abonnés"]
        if any(indicator in text_lower for indicator in mailchimp_indicators):
            logger.info(f"[ORCHESTRATOR] Indicateurs MailChimp forts détectés dans: '{text}'")
            return "mailchimp"
        
        # Analyser chaque service
        for service, keywords in service_keywords.items():
            # Donner un score de base si le nom du service est explicitement mentionné
            if service.lower() in text_lower:
                scores[service] += 3
                
            # Vérifier des mentions de produit/marque explicites
            if service == "hubspot" and "hubspot" in text_lower:
                scores[service] += 3
            elif service == "trello" and "trello" in text_lower:
                scores[service] += 3
            elif service == "slack" and "slack" in text_lower:
                scores[service] += 3
            elif service == "gmail" and any(x in text_lower for x in ["gmail", "google mail"]):
                scores[service] += 3
            elif service == "google_drive" and any(x in text_lower for x in ["google drive", "gdrive"]):
                scores[service] += 3
            elif service == "salesforce" and any(x in text_lower for x in ["salesforce", "sales force", "sf"]):
                scores[service] += 3
            elif service == "quickbooks" and any(x in text_lower for x in ["quickbooks", "quick books", "qb"]):
                scores[service] += 3
            elif service == "mailchimp" and any(x in text_lower for x in ["mailchimp", "mail chimp"]):
                scores[service] += 3
            
            # Ajouter des points pour chaque mot-clé trouvé
            for keyword in keywords:
                if keyword in text_lower:
                    scores[service] += 1
        
        # Déterminer le service avec le score le plus élevé
        best_service = max(scores, key=scores.get)
        best_score = scores[best_service]
        
        # Si le meilleur score est trop faible, aucun service n'est clairement indiqué
        if best_score < 1:
            logger.info(f"[ORCHESTRATOR] Aucun service clairement identifié pour: '{text}'")
            return None
        
        logger.info(f"[ORCHESTRATOR] Service le plus adapté: {best_service} (score: {best_score}) pour: '{text}'")
        return best_service 