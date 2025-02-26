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
from ..integrations.trello.manager import TrelloManager
from datetime import datetime, timedelta
from ..utils.retry_handler import RetryHandler
import random
from requests.exceptions import ConnectionError, SSLError, ProxyError
import socket
from urllib3.exceptions import NewConnectionError, MaxRetryError
from django.core.cache import cache
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration des timeouts
API_TIMEOUT = 10  # secondes
LONG_OPERATION_TIMEOUT = 30  # secondes
MAX_RETRIES = 3
NETWORK_TIMEOUT = 5  # secondes pour les vérifications réseau
SESSION_TIMEOUT = 3600  # 1 heure
CACHE_KEY_PREFIX = 'alya_session_'

# Configuration des modèles
INTENT_MODEL = "gpt-3.5-turbo"  # Pour la détection d'intention
RESPONSE_MODEL = "gpt-4"        # Pour les réponses complexes
TASK_MODEL = "gpt-3.5-turbo"   # Pour l'extraction d'informations simples

class NetworkError(Exception):
    """Exception personnalisée pour les erreurs réseau"""
    pass

class AITimeoutError(Exception):
    """Exception personnalisée pour les timeouts"""
    pass

class SessionState:
    """Classe pour gérer l'état de la session"""
    def __init__(self, user_id: int):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history = []
        self.current_context = {}
        self.pending_actions = []
        self.integration_states = {}
        self.error_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire pour le cache"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'conversation_history': self.conversation_history,
            'current_context': self.current_context,
            'pending_actions': self.pending_actions,
            'integration_states': self.integration_states,
            'error_count': self.error_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Crée une instance à partir d'un dictionnaire"""
        instance = cls(data['user_id'])
        instance.session_id = data['session_id']
        instance.created_at = datetime.fromisoformat(data['created_at'])
        instance.last_activity = datetime.fromisoformat(data['last_activity'])
        instance.conversation_history = data['conversation_history']
        instance.current_context = data['current_context']
        instance.pending_actions = data['pending_actions']
        instance.integration_states = data['integration_states']
        instance.error_count = data['error_count']
        return instance

class AIOrchestrator:
    # Variable de classe pour stocker les états de conversation par utilisateur
    conversation_states = {}
    contact_types = {}  # Nouveau dictionnaire pour stocker les types de contact
    contact_infos = {}  # Nouveau dictionnaire pour stocker les informations de contact

    def __init__(self, user):
        self.user = user
        self.session_state = self._get_or_create_session()
        # Récupérer ou créer le chat actif
        self.active_chat = self._get_or_create_active_chat()
        # Vérifier la connexion internet
        if not self._check_internet_connection():
            logger.error("Pas de connexion internet détectée")
            raise NetworkError("Pas de connexion internet")

        self.openai_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=API_TIMEOUT,
            max_retries=MAX_RETRIES
        )
        self.trello_integration = None
        self._initialize_trello()
        self.conversation_history = []
        self.error_count = 0
        self.last_successful_action = None
        self.max_message_length = 4000  # Limite de longueur des messages
        self.max_retries_per_session = 5  # Limite de tentatives par session
        self.session_retry_count = 0  # Compteur de tentatives pour la session
        self.logger = logging.getLogger(__name__)
        self.retry_handler = RetryHandler(
            max_retries=MAX_RETRIES,
            base_delay=1,
            max_delay=LONG_OPERATION_TIMEOUT
        )
        self.logger.info(f"Initialisation d'AIOrchestrator pour user_id: {self.user.id}")

    def _initialize_trello(self):
        """Initialise l'intégration Trello si elle existe"""
        try:
            integration = Integration.objects.get(name__iexact='trello')
            self.trello_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.trello_integration = None

    def _build_conversation_context(self):
        """Construit le contexte de la conversation à partir de l'historique"""
        try:
            # Utiliser le chat actif de l'instance
            if not self.active_chat:
                return ""

            # Récupérer les 5 derniers messages de ce chat spécifique
            history = ChatHistory.objects.filter(
                chat=self.active_chat,
                user=self.user
            ).order_by('-created_at')[:5]
            
            # Construire le contexte
            context = []
            for msg in reversed(history):
                role = "Utilisateur" if msg.is_user else "Assistant"
                context.append(f"{role}: {msg.content}")
            
            return "\n".join(context)
        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du contexte: {str(e)}")
            return ""

    def _detect_intent(self, message, conversation_history):
        """Détecte l'intention de l'utilisateur avec l'IA"""
        try:
            # Construire le contexte de la conversation
            context = "\n".join([
                f"{'Utilisateur' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in conversation_history[-3:]
            ])

            prompt = f"""
            Analyse le message suivant et le contexte de la conversation pour déterminer l'intention de l'utilisateur.

            Contexte de la conversation :
            {context}

            Message actuel : {message}

            Identifie :
            - integration: (trello, hubspot, ou null)
            - action: (create_task, move_card, create_contact, etc.)
            - confidence: (0-1)
            - context_type: (new_request, continuation, clarification, correction, cancellation)
            - previous_requests: []
            - corrections: []

            Retourne un objet JSON avec ces informations.
            """

            response = self.openai_client.chat.completions.create(
                model=INTENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0.3
            )

            intent = json.loads(response.choices[0].message.content)
            self.logger.info(f"Intention détectée: {intent}")
            return intent

        except Exception as e:
            self.logger.error(f"Erreur lors de la détection d'intention: {str(e)}")
            return {
                "integration": None,
                "action": "unknown",
                "confidence": 0.0,
                "context_type": "error",
                "previous_requests": [],
                "corrections": []
            }

    def _extract_trello_task_info(self, text):
        """Extrait les informations de tâche du texte avec l'IA"""
        prompt = f"""
        Extrait les informations suivantes du texte pour créer une tâche Trello :
        - Nom de la tâche
        - Description (optionnel)
        - Liste/Colonne
        - Assigné à (optionnel)
        - Date d'échéance (optionnel)

        Texte : {text}

        Réponds uniquement en JSON avec ces champs.
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )

        return json.loads(response.choices[0].message.content)

    def _extract_task_info(self, text):
        """Extrait les informations de tâche du texte avec l'IA"""
        prompt = f"""
        En tant qu'assistant expert en gestion de projet, analyse naturellement cette demande 
        pour en extraire les informations nécessaires à la création d'une tâche Trello.
        
        Comprends le contexte et l'intention pour identifier :
        - Le titre principal de la tâche
        - Tout détail supplémentaire comme description
        - Une date d'échéance (convertis les mentions comme "demain", "vendredi", etc. en date ISO)
        - La liste ou colonne concernée (par défaut "À faire" si non précisé)
        - La personne à qui la tâche est assignée si mentionnée
        
        Texte à analyser : {text}
        
        Retourne uniquement un objet JSON avec les champs name, description, due_date, list_name, et assignee.
        Si un champ n'est pas mentionné, ne pas l'inclure dans le JSON.
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un expert en analyse de langage naturel et gestion de projet."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        task_info = json.loads(response.choices[0].message.content)
        
        # Générer une confirmation naturelle
        confirmation = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es Alya, une assistante amicale. Confirme la création de la tâche de manière naturelle et concise."
                },
                {
                    "role": "user",
                    "content": f"Confirme la création d'une tâche avec ces détails : {json.dumps(task_info, ensure_ascii=False)}"
                }
            ]
        ).choices[0].message.content
        
        task_info['confirmation_message'] = confirmation
        return task_info

    @RetryHandler(max_retries=3, base_delay=2, max_delay=15)
    def handle_trello_request(self, text):
        """Gère les requêtes liées à Trello"""
        if not self.trello_integration:
            return ("Pour utiliser Trello, vous devez d'abord connecter votre compte. 🔌\n\n"
                    "Voici comment faire :\n"
                    "1. Cliquez sur l'icône d'intégration dans le menu\n"
                    "2. Sélectionnez Trello\n"
                    "3. Suivez les étapes de connexion\n\n"
                    "Voulez-vous que je vous guide dans ce processus ?")

        # Analyse le texte pour déterminer l'action
        text_lower = text.lower()
        
        try:
            # Vérifier la connexion à Trello
            if not self._verify_integration_connection('trello'):
                return ("Je n'arrive pas à me connecter à Trello. 😕\n"
                        "Veuillez vérifier que votre connexion est toujours valide dans les paramètres d'intégration.")

            # Détection plus précise des demandes de création de tâches
            if ("ajoute" in text_lower and "tâche" in text_lower) or \
               ("crée" in text_lower and "tâche" in text_lower) or \
               ("créer" in text_lower and "tâche" in text_lower) or \
               ("nouvelle" in text_lower and "tâche" in text_lower):
                info = self._extract_task_info(text)
                if not info.get('name'):
                    return "Je n'ai pas bien compris le nom de la tâche. Pouvez-vous reformuler ?"
                
                # Vérifier si la liste existe
                list_name = info.get('list_name', 'À faire')
                try:
                    lists = TrelloManager.get_lists(self.trello_integration)
                    if list_name not in lists:
                        return (f"Je ne trouve pas la liste '{list_name}'. 🤔\n"
                                f"Les listes disponibles sont : {', '.join(lists)}\n"
                                "Dans quelle liste souhaitez-vous créer la tâche ?")
                except Exception as e:
                    self.logger.error(f"Erreur lors de la récupération des listes: {str(e)}")
                    return "Je n'arrive pas à accéder aux listes Trello. Veuillez réessayer."
                
                # Vérifier si l'assigné existe
                if 'assignee' in info:
                    try:
                        members = TrelloManager.get_board_members(self.trello_integration)
                        member = next((m for m in members if m['name'].lower() == info['assignee'].lower()), None)
                        if not member:
                            return (f"Je ne trouve pas le membre '{info['assignee']}'. 🤔\n"
                                    f"Les membres disponibles sont : {', '.join(m['name'] for m in members)}\n"
                                    "À qui souhaitez-vous assigner cette tâche ?")
                        info['member_id'] = member['id']
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la récupération des membres: {str(e)}")
                        return "Je n'arrive pas à accéder aux membres du tableau. Veuillez réessayer."
                
                result = TrelloManager.create_task(self.trello_integration, info)
                # Sauvegarder l'action pour pouvoir l'annuler
                self.last_successful_action = {
                    'integration': 'trello',
                    'type': 'create_task',
                    'id': result.get('id')
                }
                
                # Construire un message de confirmation détaillé
                confirmation = f"✅ J'ai créé la tâche '{info['name']}' "
                confirmation += f"dans la liste '{list_name}'"
                if 'assignee' in info:
                    confirmation += f", assignée à {info['assignee']}"
                if 'due_date' in info:
                    confirmation += f", à terminer pour le {info['due_date']}"
                confirmation += "."
                return confirmation

            elif "crée" in text_lower or "créer" in text_lower:
                if "tableau" in text_lower:
                    info = self._extract_board_info(text)
                    result = TrelloManager.create_board(self.trello_integration, info)
                    return f"Le tableau '{info.get('name', '')}' a été créé avec succès ! 📋"
                elif "liste" in text_lower:
                    info = self._extract_list_info(text)
                    result = TrelloManager.create_list(self.trello_integration, info)
                    return f"La liste '{info.get('name', '')}' a été créée ! ✅"

            elif "déplace" in text_lower or "déplacer" in text_lower:
                info = self._extract_move_info(text)
                result = TrelloManager.move_card(self.trello_integration, info)
                return "La carte a été déplacée avec succès ! 🔄"

            elif "commente" in text_lower or "ajoute un commentaire" in text_lower:
                info = self._extract_comment_info(text)
                result = TrelloManager.add_comment(self.trello_integration, info)
                return f"Le commentaire a été ajouté avec succès ! 💬"

            elif "checklist" in text_lower:
                info = self._extract_checklist_info(text)
                result = TrelloManager.add_checklist(self.trello_integration, info)
                return f"Le checklist '{info.get('name', '')}' a été créé avec succès ! 📋"

            elif "label" in text_lower or "étiquette" in text_lower:
                info = self._extract_label_info(text)
                result = TrelloManager.add_label(self.trello_integration, info)
                return f"Le label '{info.get('name', '')}' a été créé avec succès ! 🏷"

            elif "activité" in text_lower or "activites" in text_lower:
                info = self._extract_activity_info(text)
                result = TrelloManager.get_board_activity(self.trello_integration, info)
                return f"Voici les activités du tableau '{info.get('name', '')}' : {result}"

            elif "tâches en retard" in text_lower:
                result = TrelloManager.get_overdue_tasks_summary(self.trello_integration)
                return f"Voici les tâches en retard pour le tableau '{info.get('name', '')}' : {result}"

            else:
                return "Je ne comprends pas votre demande. Voici ce que je peux faire avec Trello :\n" + \
                       "- Créer un tableau, une liste ou une tâche\n" + \
                       "- Déplacer une carte\n" + \
                       "- Ajouter des commentaires, checklists ou labels\n" + \
                       "- Voir l'activité d'un tableau\n" + \
                       "- Lister les tâches en retard"

            if result['success']:
                return f"✅ {result['message']}"
            else:
                return f"❌ Erreur : {result['error']}"

        except TrelloManager.TrelloError as e:
            self.logger.error(f"Erreur Trello: {str(e)}")
            return f"Désolée, une erreur est survenue avec Trello : {str(e)}"
        except Exception as e:
            self.logger.error(f"Erreur dans handle_trello_request: {str(e)}")
            return ("Une erreur inattendue s'est produite. 😕\n"
                    "Voici quelques suggestions :\n"
                    "1. Vérifiez que votre demande est claire\n"
                    "2. Assurez-vous que les éléments mentionnés existent\n"
                    "3. Essayez de reformuler votre demande")

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

    def reset_contact_state(self):
        """Réinitialise l'état de la création de contact"""
        if self.user.id in self.conversation_states:
            del self.conversation_states[self.user.id]
        if self.user.id in self.contact_types:
            del self.contact_types[self.user.id]
        if self.user.id in self.contact_infos:
            del self.contact_infos[self.user.id]

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

    def _get_ai_response(self, message_content):
        """Obtient une réponse de l'IA pour un message donné"""
        try:
            # Message système pour Alya
            system_message = """Tu es Alya, une assistante IA experte. 
            Réponds de manière claire, précise et détaillée aux questions des utilisateurs."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": message_content}
            ]

            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
            if not completion.choices:
                raise ValueError("Pas de réponse de l'IA")

            return completion.choices[0].message.content

        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse IA: {str(e)}")
            return "Désolée, je n'ai pas pu traiter votre demande. Pouvez-vous reformuler ?"

    def _update_conversation_history(self, role, content):
        """Met à jour l'historique de conversation"""
        self.conversation_history.append({"role": role, "content": content})
        # Garder seulement les 10 derniers messages pour éviter une trop grande utilisation de tokens
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

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

    def _handle_edge_cases(self, message, intent=None):
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

        # Détecter les boucles de conversation
        if len(self.conversation_history) >= 6:
            last_responses = [msg['content'] for msg in self.conversation_history[-6:] if msg['role'] == 'assistant']
            if len(set(last_responses)) <= 2:  # Si les 3 dernières réponses sont similaires
                return ("Il semble que nous tournions en rond. "
                       "Essayons une approche différente ou passons à autre chose. "
                       "Que souhaitez-vous faire ?")

        # Vérifier les limites de tentatives
        if self.session_retry_count >= self.max_retries_per_session:
            self.session_retry_count = 0  # Réinitialiser pour la prochaine session
            return ("Nous avons fait plusieurs tentatives sans succès. "
                   "Je vous suggère de :\n"
                   "1. Prendre une pause et réessayer plus tard\n"
                   "2. Reformuler complètement votre demande\n"
                   "3. Contacter le support si le problème persiste")

        return None  # Pas de cas limite détecté

    def _handle_intent(self, intent, message):
        """Gère la demande en fonction de l'intention détectée"""
        try:
            # Gérer les confirmations
            if intent['context_type'] == 'confirmation':
                return self._handle_confirmation(intent, message)

            # Gérer les annulations
            if intent['context_type'] == 'cancellation':
                if self._can_undo_action():
                    return self._undo_last_action()
                return "Il n'y a pas d'action récente à annuler."

            # Gérer les corrections
            if intent['context_type'] == 'correction':
                return self._handle_correction(intent, message)

            # Gérer les salutations et messages généraux
            if intent['confidence'] < 0.5 or not intent.get('integration'):
                if any(word in message.lower() for word in ['bonjour', 'hello', 'salut', 'bonsoir', 'hi']):
                    return ("Bonjour ! 👋 Je suis Alya, votre assistante virtuelle.\n"
                           "Je peux vous aider avec la gestion de vos tâches Trello, "
                           "vos contacts HubSpot et bien plus encore.\n"
                           "Comment puis-je vous aider aujourd'hui ?")
                return self.generate_response(message, None)

            # Gérer les intégrations spécifiques
            integration = intent.get('integration')
            if integration and integration.lower() == 'trello':
                return self.handle_trello_request(message)
            elif integration and integration.lower() == 'hubspot':
                return self.handle_hubspot_request(message)

            # Si l'intention n'est pas claire ou la confiance est faible
            if not intent.get('action') or intent.get('confidence', 0) < 0.5:
                return self.generate_response(message, None)

            # Gérer les autres types de demandes
            return self.generate_response(message, None)

        except Exception as e:
            self.logger.error(f"Erreur dans _handle_intent: {str(e)}")
            return self._handle_error(e, context={
                'intent': intent,
                'message': message
            })

    def process_message(self, chat_id, message_content):
        try:
            self._update_session_activity()
            # Valider et nettoyer le message
            message_content = self._validate_message(message_content)

            # Vérifier les cas limites
            edge_case_response = self._handle_edge_cases(message_content)
            if edge_case_response:
                return edge_case_response

            chat = self._get_or_create_chat(chat_id)
            Message.objects.create(chat=chat, content=message_content, is_user=True)
            self._update_conversation_history("user", message_content)

            # Détecter l'intention avec l'IA
            intent = self._detect_intent(message_content, self.conversation_history)
            
            # Vérifier à nouveau les cas limites avec l'intention
            edge_case_response = self._handle_edge_cases(message_content, intent)
            if edge_case_response:
                return edge_case_response

            response = self._handle_intent(intent, message_content)
            
            Message.objects.create(chat=chat, content=response, is_user=False)
            self._update_conversation_history("assistant", response)

            # Réinitialiser le compteur de tentatives si succès
            self.session_retry_count = 0

            return response
            
        except Exception as e:
            self.session_retry_count += 1
            logger.error(f"Erreur dans process_message: {str(e)}")
            return self._handle_error(e)

    @RetryHandler(max_retries=3, base_delay=2, max_delay=15)
    def handle_hubspot_request(self, text):
        """Gère les requêtes liées à HubSpot"""
        try:
            # Vérifier si l'intégration HubSpot est active
            hubspot_integration = Integration.objects.get(name__iexact='hubspot crm')
            user_integration = UserIntegration.objects.get(
                user=self.user,
                integration=hubspot_integration,
                enabled=True
            )

            if not user_integration:
                return "L'intégration HubSpot n'est pas configurée. Voulez-vous que je vous aide à la configurer ?"

            text_lower = text.lower()
            
            # Détection plus précise des demandes HubSpot
            if any(pattern in text_lower for pattern in [
                'créer contact', 'nouveau contact', 'ajouter contact',
                'creer un contact', 'contact hubspot', 'contact avec hubspot',
                'nouveau contact hubspot', 'créer contact hubspot'
            ]):
                # Extraire les informations du contact
                contact_info = self._extract_contact_info(text)
                result = self.create_hubspot_contact(contact_info)
                
                if isinstance(result, bool) and result:
                    return f"✅ J'ai créé le contact {contact_info.get('firstname', '')} {contact_info.get('lastname', '')} dans HubSpot."
                else:
                    return f"❌ Erreur : {result}"

            return "Je ne comprends pas votre demande HubSpot. Je peux :\n" + \
                   "- Créer un nouveau contact\n" + \
                   "- Mettre à jour un contact existant\n" + \
                   "- Rechercher des contacts"

        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            return "L'intégration HubSpot n'est pas configurée. Voulez-vous que je vous aide à la configurer ?"
        except Exception as e:
            logger.error(f"Erreur HubSpot: {str(e)}")
            return "Une erreur est survenue lors de l'exécution de votre demande."

    def _extract_contact_info(self, text):
        """Extrait les informations de contact du texte"""
        prompt = f"""
        En tant qu'expert en CRM, analyse cette demande pour extraire les informations de contact.
        
        Identifie naturellement :
        - Le prénom
        - Le nom
        - L'email
        - Le téléphone
        - L'entreprise (si mentionnée)
        - Le poste/titre (si mentionné)
        - Le site web (si mentionné)
        
        Texte à analyser : {text}
        
        Retourne uniquement un objet JSON avec les champs trouvés.
        Si un champ n'est pas mentionné, ne pas l'inclure dans le JSON.
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en analyse de données CRM."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        return json.loads(response.choices[0].message.content)

    def create_hubspot_contact(self, contact_info):
        try:
            # Vérifier si l'intégration HubSpot est active
            hubspot_integration = Integration.objects.get(name__iexact='hubspot crm')
            user_integration = UserIntegration.objects.get(
                user_id=self.user.id,
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

    def generate_response(self, message, chat):
        """Génère une réponse avec l'IA"""
        try:
            # Si un chat est fourni, vérifier s'il doit devenir le chat actif
            if chat and chat != self.active_chat:
                # Désactiver l'ancien chat actif s'il existe
                if self.active_chat:
                    self.active_chat.is_active = False
                    self.active_chat.save()
                # Activer le nouveau chat
                chat.is_active = True
                chat.save()
                self.active_chat = chat
            else:
                chat = self.active_chat
  
            # Détecter l'intention
            intent = self._detect_intent(message, self.conversation_history)
            self.logger.info(f"Message reçu: '{message}'")
  
            # Sauvegarder le message avant de le traiter
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=message,
                is_user=True
            )

            # Si c'est une réponse à une demande précédente (continuation)
            if intent['context_type'] == 'continuation':
                if 'assignee' in message.lower():
                    # Mettre à jour les informations de la tâche et continuer le processus
                    return self.handle_trello_request(message)

            # Construire le contexte de la conversation
            context = self._build_conversation_context()
            
            # Ajouter le message actuel au contexte
            context += f"\nUtilisateur: {message}"
            
            # Générer la réponse
            completion = self.openai_client.chat.completions.create(
                model=RESPONSE_MODEL,
                messages=[
                    {"role": "system", "content": "Tu es Alya, une assistante IA experte en gestion de projet et intégrations."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            response = completion.choices[0].message.content
            
            # Sauvegarder l'historique
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=message,
                is_user=True
            )
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=response,
                is_user=False
            )
            
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
                    self.contact_info = {}  # Initialiser le dictionnaire de contact
                    return "Parfait, créons un contact personnel. Quel est son prénom ?"
                elif '2' in message or 'professionnel' in message or 'entreprise' in message:
                    self.conversation_state = 'pro_firstname'
                    self.contact_info = {}  # Initialiser le dictionnaire de contact
                    return "D'accord, créons un contact professionnel. Quel est son prénom ?"
                else:
                    return ("Je n'ai pas compris votre choix. Veuillez répondre par :\n\n"
                           "1. Contact Personnel (particulier)\n"
                           "2. Contact Professionnel (entreprise)")
  
            elif state == 'personal_firstname':
                if not message.strip():
                    return "Le prénom ne peut pas être vide. Quel est son prénom ?"
                self.contact_info = {'firstname': message}
                self.conversation_state = 'personal_lastname'
                return "Très bien ! Maintenant, quel est son nom de famille ?"
                
            elif state == 'personal_lastname':
                if not message.strip():
                    return "Le nom ne peut pas être vide. Quel est son nom de famille ?"
                self.contact_info['lastname'] = message
                self.conversation_state = 'personal_email'
                return "Parfait ! Quelle est son adresse email ?"
                
            elif state == 'personal_email':
                if not message.strip():
                    return "L'email ne peut pas être vide. Quelle est son adresse email ?"
                self.contact_info['email'] = message
                
                # Vérifier que toutes les informations requises sont présentes
                required_fields = ['firstname', 'lastname', 'email']
                if not all(field in self.contact_info for field in required_fields):
                    self.logger.error(f"Informations de contact incomplètes: {self.contact_info}")
                    return "Il manque des informations essentielles. Pouvons-nous recommencer ?"
                
                # Créer le contact dans HubSpot
                try:
                    response = self.hubspot_manager.create_contact(self.contact_info)
                    if response and response.status_code == 201:
                        self.conversation_state = None
                        self.contact_info = {}
                        return "✅ Super ! Le contact a été créé avec succès dans HubSpot."
                    else:
                        self.logger.error(f"Erreur HubSpot: {response.text if response else 'No response'}")
                        return "❌ Désolé, il y a eu un problème lors de la création du contact. Voulez-vous réessayer ?"
                except Exception as e:
                    self.logger.error(f"Erreur lors de la création du contact HubSpot: {str(e)}")
                    return "❌ Une erreur s'est produite. Voulez-vous réessayer ?"

            # Si l'état n'est pas reconnu
            self.logger.error(f"État de conversation non géré: {state}")
            return "Désolé, je ne sais pas où nous en étions. Pouvons-nous recommencer ?"

        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion de la création de contact: {str(e)}")
            return "Une erreur est survenue. Pouvons-nous reprendre depuis le début ?"

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
            return ("Je mets un peu trop de temps à répondre. "
                    "Le service semble lent actuellement. "
                    "Voulez-vous réessayer ?")
        
        # Gérer différents types d'erreurs
        if isinstance(error, openai.OpenAIError):
            if "rate_limit" in error_msg:
                return "Je suis un peu surchargée actuellement. Pouvez-vous réessayer dans quelques secondes ?"
            elif "context_length" in error_msg:
                self.conversation_history = self.conversation_history[-3:]
                return "La conversation est devenue trop longue. Pouvez-vous reformuler votre dernière demande ?"
        
        elif isinstance(error, requests.exceptions.RequestException):
            return "Je rencontre des problèmes de connexion. Vérifiez votre connexion internet et réessayez."
        
        # Si trop d'erreurs consécutives, proposer une alternative
        if self.error_count >= 3:
            self.error_count = 0  # Réinitialiser le compteur
            return ("Je semble avoir des difficultés à traiter vos demandes. Voici ce que vous pouvez faire :\n"
                    "1. Reformulez votre demande différemment\n"
                    "2. Essayez une action plus simple\n"
                    "3. Vérifiez que les intégrations nécessaires sont bien configurées\n"
                    "4. Contactez le support si le problème persiste")
        
        return "Désolée, une erreur s'est produite. Pouvez-vous reformuler votre demande ?"

    def _handle_success(self):
        """Gère les succès et réinitialise les compteurs d'erreur"""
        self.error_count = 0
        return True

    def _can_undo_action(self):
        """Vérifie si la dernière action peut être annulée"""
        return self.last_successful_action is not None

    def _undo_last_action(self):
        """Annule la dernière action si possible"""
        if not self._can_undo_action():
            return "Désolée, je ne peux pas annuler car il n'y a pas d'action récente."
        
        try:
            action = self.last_successful_action
            if action['integration'] == 'trello':
                if action['type'] == 'create_task':
                    TrelloManager.delete_card(self.trello_integration, action['id'])
                # Ajouter d'autres types d'actions...
            
            elif action['integration'] == 'hubspot':
                if action['type'] == 'create_contact':
                    # Logique pour supprimer le contact HubSpot
                    pass
            
            self.last_successful_action = None
            return "J'ai annulé la dernière action avec succès."
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'annulation: {str(e)}")
            return "Désolée, je n'ai pas pu annuler la dernière action."

    def _check_internet_connection(self, host="8.8.8.8", port=53, timeout=NETWORK_TIMEOUT):
        """Vérifie la connexion internet"""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except (socket.error, socket.timeout):
            return False

    def _handle_network_error(self, error):
        """Gère spécifiquement les erreurs réseau"""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Problèmes de connexion
        if isinstance(error, (ConnectionError, NewConnectionError)):
            return ("Je ne peux pas me connecter au serveur. "
                    "Vérifiez votre connexion internet et réessayez.")

        # Problèmes SSL
        if isinstance(error, SSLError):
            return ("Il y a un problème de sécurité avec la connexion. "
                    "Vérifiez que votre date/heure système est correcte.")

        # Problèmes de proxy
        if isinstance(error, ProxyError):
            return ("Il y a un problème avec votre configuration proxy. "
                    "Vérifiez vos paramètres réseau.")

        # Timeouts réseau
        if isinstance(error, (socket.timeout, MaxRetryError)) or 'timeout' in error_msg:
            return ("La connexion est très lente. "
                    "Vérifiez votre connexion internet ou réessayez plus tard.")

        return "Problème de connexion détecté. Vérifiez votre connexion internet."

    def _verify_integration_connection(self, integration_name):
        """Vérifie la connexion à une intégration spécifique"""
        try:
            if integration_name.lower() == 'trello':
                return TrelloManager.check_connection(self.trello_integration)
            elif integration_name.lower() == 'hubspot':
                return self._check_hubspot_connection()
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de {integration_name}: {str(e)}")
            return False

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

    def _get_or_create_active_chat(self):
        """Récupère ou crée un chat actif pour l'utilisateur"""
        try:
            # Chercher un chat actif existant
            active_chat = Chat.objects.filter(
                user=self.user,
                # Vous pouvez ajouter un champ is_active dans le modèle Chat
                # is_active=True
            ).order_by('-created_at').first()
            
            if not active_chat:
                active_chat = Chat.objects.create(user=self.user)
            
            return active_chat
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du chat actif: {str(e)}")
            return Chat.objects.create(user=self.user)

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
