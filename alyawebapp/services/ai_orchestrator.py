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
from datetime import datetime, timedelta, timezone
from ..utils.retry_handler import RetryHandler
import random
from requests.exceptions import ConnectionError, SSLError, ProxyError
import socket
from urllib3.exceptions import NewConnectionError, MaxRetryError
from django.core.cache import cache
import uuid
from typing import Optional, Dict, Any
import re

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

# Dictionnaire des capacités des intégrations
INTEGRATION_CAPABILITIES = {
    # Actions communes
    'create_contact': {
        'name': 'Créer un contact',
        'integrations': ['HubSpot', 'Salesforce', 'Zoho CRM', 'Gmail'],
        'required_fields': ['nom', 'email'],
        'optional_fields': ['téléphone', 'entreprise', 'poste']
    },
    'send_email': {
        'name': 'Envoyer un email',
        'integrations': ['Gmail', 'Mailchimp', 'HubSpot Marketing'],
        'required_fields': ['destinataire', 'sujet', 'contenu']
    },
    'create_task': {
        'name': 'Créer une tâche',
        'integrations': ['Trello', 'Asana', 'Slack'],
        'required_fields': ['titre', 'description'],
        'optional_fields': ['date_échéance', 'assigné_à']
    },
    'schedule_meeting': {
        'name': 'Planifier une réunion',
        'integrations': ['Google Calendar', 'HubSpot', 'Salesforce'],
        'required_fields': ['date', 'heure', 'participants']
    },
    'share_document': {
        'name': 'Partager un document',
        'integrations': ['Google Drive', 'Slack'],
        'required_fields': ['document', 'destinataires']
    },
    'create_invoice': {
        'name': 'Créer une facture',
        'integrations': ['QuickBooks', 'Stripe'],
        'required_fields': ['client', 'montant', 'description']
    },
    
    # Intégrations spécifiques
    'HubSpot': {
        'actions': ['create_contact', 'create_deal', 'schedule_meeting', 'send_email'],
        'entities': ['contact', 'entreprise', 'affaire', 'ticket'],
        'keywords': ['crm', 'client', 'prospect', 'pipeline', 'vente']
    },
    'Trello': {
        'actions': ['create_task', 'assign_task', 'create_board', 'create_list'],
        'entities': ['carte', 'tableau', 'liste', 'tâche'],
        'keywords': ['projet', 'kanban', 'tâche', 'assignation']
    },
    'Slack': {
        'actions': ['send_message', 'create_channel', 'share_document'],
        'entities': ['message', 'canal', 'conversation'],
        'keywords': ['communication', 'équipe', 'discussion', 'notification']
    },
    'Gmail': {
        'actions': ['send_email', 'create_draft', 'schedule_email'],
        'entities': ['email', 'brouillon', 'pièce jointe'],
        'keywords': ['mail', 'message', 'envoyer', 'communiquer']
    },
    'Google Drive': {
        'actions': ['upload_file', 'share_document', 'create_folder'],
        'entities': ['document', 'dossier', 'fichier'],
        'keywords': ['stockage', 'partage', 'collaboration', 'fichier']
    },
    'Salesforce': {
        'actions': ['create_contact', 'create_opportunity', 'track_deal'],
        'entities': ['contact', 'opportunité', 'compte', 'lead'],
        'keywords': ['vente', 'pipeline', 'client', 'affaire']
    },
    'QuickBooks': {
        'actions': ['create_invoice', 'track_expense', 'generate_report'],
        'entities': ['facture', 'dépense', 'client', 'paiement'],
        'keywords': ['comptabilité', 'finance', 'facturation', 'paiement']
    }
}

# Dictionnaire des réponses générales (non liées aux intégrations)
GENERAL_RESPONSES = {
    'time': {
        'patterns': ['quelle heure', 'heure actuelle', 'l\'heure'],
        'response': lambda: f"Il est actuellement {datetime.now().strftime('%H:%M')}."
    },
    'date': {
        'patterns': ['quel jour', 'date aujourd\'hui', 'la date'],
        'response': lambda: f"Nous sommes le {datetime.now().strftime('%d/%m/%Y')}."
    },
    'weather': {
        'patterns': ['météo', 'temps qu\'il fait', 'température'],
        'response': "Je ne peux pas accéder aux informations météo en temps réel, mais je peux vous aider à configurer une intégration météo si vous le souhaitez."
    },
    'greeting': {
        'patterns': ['bonjour', 'salut', 'hello', 'coucou'],
        'response': "Bonjour ! Je suis Alya, votre assistant IA. Comment puis-je vous aider aujourd'hui ?"
    },
    'help': {
        'patterns': ['aide', 'help', 'que peux-tu faire', 'fonctionnalités'],
        'response': "Je peux vous aider avec vos intégrations comme Trello, HubSpot, Gmail, etc. Je peux créer des contacts, envoyer des emails, créer des tâches et bien plus encore. Que souhaitez-vous faire ?"
    }
}

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
        self.active_chat = None
        self.current_conversation = None
        self.openai_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=API_TIMEOUT,
            max_retries=MAX_RETRIES
        )
        self.trello_integration = None
        self._initialize_trello()
        self.conversation_history = []
        self.task_info = {}
        self.available_members = []
        self.conversation_state = None  # État de la conversation actuelle
        self.contact_info = {}  # Informations de contact en cours
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
            # Construire le prompt pour détecter l'intention
            prompt = {
                "role": "system",
                "content": """Tu es un expert en analyse d'intention. Analyse le message et le contexte pour déterminer :
                    1. L'intégration concernée (trello, hubspot, etc.)
                    2. L'action demandée (create_task, get_overdue_tasks, etc.)
                    3. Si c'est une continuation d'une demande précédente
                    4. Le niveau de confiance (0-1)
                    
                    Pour Trello, détecte spécifiquement :
                    - La création de tâche (mots clés : ajoute, crée, nouvelle tâche)
                    - La consultation des tâches en retard (mots clés : retard, en retard, dépassées)
                    - L'assignation de tâches (mots clés : assigne, attribue à)
                    - Les dates d'échéance (mots clés : échéance, deadline, pour vendredi)
                    
                    Retourne ta réponse sous forme d'objet JSON."""
            }

            # Ajouter le contexte de la conversation
            context_messages = []
            if conversation_history:
                for msg in conversation_history:
                    role = "Utilisateur" if msg.get('role') == 'user' else "Assistant"
                    content = msg.get('content', '')
                    if content:
                        context_messages.append(f"{role}: {content}")
            
            context = "\n".join(context_messages)
            
            user_prompt = {
                "role": "user",
                "content": f"""En tenant compte de TOUTE la conversation précédente,
                    analyse ce message et retourne un JSON avec l'intention :
                    
                    Contexte précédent:
                    {context}
                    
                    Message actuel: {message}"""
            }

            completion = self.openai_client.chat.completions.create(
                model=INTENT_MODEL,
                messages=[prompt, user_prompt],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )

            intent = json.loads(completion.choices[0].message.content)
            self.logger.info(f"Intention détectée: {intent}")
            
            # S'assurer que context_type est présent
            if 'context_type' not in intent:
                intent['context_type'] = 'new_request'
                if intent.get('is_continuation'):
                    intent['context_type'] = 'continuation'
            
            return intent

        except Exception as e:
            self.logger.error(f"Erreur dans _detect_intent: {str(e)}")
            self.logger.error(f"Conversation history: {conversation_history}")
            return {
                'integration': None,
                'action': None,
                'context_type': 'error',
                'confidence': 0,
                'is_continuation': False
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
        try:
            # Extraire le nom de la tâche entre guillemets simples
            name_match = re.search(r"'([^']*)'", text)
            name = name_match.group(1) if name_match else None

            # Extraire la colonne
            column_match = re.search(r"colonne '([^']*)'", text)
            list_name = column_match.group(1) if column_match else "À faire"

            # Extraire l'assigné
            assignee_match = re.search(r"assigne[^a-zA-Z]*(la |le )?[àa]\s+([^\s\.,]+)", text)
            assignee = assignee_match.group(2) if assignee_match else None

            # Extraire la date d'échéance
            due_date = None
            if "vendredi" in text.lower():
                # Calculer le prochain vendredi
                today = datetime.now()
                days_until_friday = (4 - today.weekday()) % 7
                next_friday = today + timedelta(days=days_until_friday)
                # Ajouter l'heure de fin de journée (23:59:59)
                next_friday = next_friday.replace(hour=23, minute=59, second=59)
                # Format ISO 8601 que Trello attend
                due_date = next_friday.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            return {
                "name": name,
                "list_name": list_name,
                "assignee": assignee,
                "due_date": due_date
            }
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des informations de tâche: {str(e)}")
            return None

    @RetryHandler(max_retries=3, base_delay=2, max_delay=15)
    def handle_trello_request(self, message):
        """Gère les requêtes Trello"""
        try:
            if not self.trello_integration:
                return "Désolée, vous n'avez pas encore configuré l'intégration Trello."

            # Si c'est une demande de tâches en retard
            if "tâches en retard" in message.lower():
                overdue_tasks = self.get_overdue_tasks(self.trello_integration)
                
                if not overdue_tasks:
                    return "✅ Bonne nouvelle ! Aucune tâche n'est en retard."
                
                response = "📅 Voici les tâches en retard :\n\n"
                for task in overdue_tasks:
                    response += f"• {task['name']} (dans '{task['list']}')\n"
                    if task['assignees']:
                        response += f"  Assignée à : {', '.join(task['assignees'])}\n"
                    response += f"  Échéance : {task['due_date'].strftime('%d/%m/%Y')}\n\n"
                
                response += "Voulez-vous que j'envoie un rappel aux responsables ?"
                return response

            # Si c'est une réponse simple avec juste le nom d'un membre
            if self.task_info and message.strip().lower() in [
                m.get('username', '').lower() for m in self.members_data
            ]:
                # Mettre à jour l'assigné dans task_info
                member = next(
                    m for m in self.members_data 
                    if m.get('username', '').lower() == message.strip().lower()
                )
                self.task_info['assignee'] = member['username']
                # Créer la tâche avec les informations mises à jour
                return self._create_trello_task()

            # Récupérer d'abord les membres disponibles
            try:
                response = requests.get(
                    f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/members",
                    params={
                        'key': settings.TRELLO_API_KEY,
                        'token': self.trello_integration.access_token,
                        'fields': 'username,fullName'
                    }
                )
                response.raise_for_status()
                members = response.json()
                self.members_data = members
                self.available_members = []
                for m in members:
                    # Créer une description claire pour chaque membre
                    member_desc = []
                    if m.get('username'):
                        member_desc.append(f"@{m['username']}")
                    if m.get('fullName'):
                        member_desc.append(f"({m['fullName']})")
                    if member_desc:
                        self.available_members.append(" ".join(member_desc))
            except Exception as e:
                self.logger.error(f"Erreur lors de la récupération des membres Trello: {str(e)}")
                return "Désolée, je n'arrive pas à récupérer la liste des membres. Veuillez réessayer."

            # Extraire les informations de la tâche
            task_info = self._extract_task_info(message)
            if not task_info:
                return "Je n'ai pas pu comprendre les détails de la tâche. Pouvez-vous reformuler ?"

            # Vérifier si le membre assigné existe
            if task_info.get('assignee'):
                assignee_lower = task_info['assignee'].lower()
                member = next(
                    (m for m in self.members_data if 
                    m.get('username', '').lower() == assignee_lower.replace('@', '') or
                    (m.get('fullName') and m.get('fullName').lower() == assignee_lower)),
                    None
                )
                if not member:
                    self.task_info = task_info  # Sauvegarder pour plus tard
                    return f"Je ne trouve pas le membre '{task_info['assignee']}'. 🤔\n\nVoici les membres disponibles :\n{', '.join(self.available_members)}\n\nÀ qui souhaitez-vous assigner cette tâche ? (utilisez le nom d'utilisateur)"
                else:
                    # Utiliser le username pour l'assignation
                    task_info['assignee'] = member['username']

            # Créer la tâche
            data = {
                'name': task_info['name'],
                'idList': self._get_list_id(task_info['list_name']),
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token
            }

            if task_info.get('due_date'):
                data['due'] = task_info['due_date']

            if task_info.get('assignee'):
                if member:
                    data['idMembers'] = [member['id']]

            response = requests.post(
                f"{settings.TRELLO_API_URL}/cards",
                json=data
            )
            response.raise_for_status()

            return f"✅ J'ai créé la tâche '{task_info['name']}'" + (
                f" et je l'ai assignée à {task_info['assignee']}" if task_info.get('assignee') else ""
            )

        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion de la requête Trello: {str(e)}")
            return "Désolée, une erreur s'est produite lors de la création de la tâche. Veuillez réessayer."

    def get_overdue_tasks(self, user_integration):
        """Récupère les tâches en retard de Trello"""
        try:
            # Récupérer toutes les listes du tableau
            lists_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{user_integration.get_active_board_id()}/lists",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': user_integration.access_token
                }
            )
            lists_response.raise_for_status()
            lists = lists_response.json()
            
            # Récupérer toutes les cartes avec une date d'échéance
            cards_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{user_integration.get_active_board_id()}/cards",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': user_integration.access_token,
                    'fields': 'name,due,idList,dueComplete,idMembers'
                }
            )
            cards_response.raise_for_status()
            all_cards = cards_response.json()
            
            # Récupérer les membres du tableau
            members_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{user_integration.get_active_board_id()}/members",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': user_integration.access_token
                }
            )
            members_response.raise_for_status()
            members = {m['id']: m['username'] for m in members_response.json()}
            
            # Filtrer les cartes en retard
            now = datetime.now(timezone.utc)
            overdue_cards = []
            for card in all_cards:
                if (card.get('due') and not card.get('dueComplete') and 
                    datetime.fromisoformat(card['due'].replace('Z', '+00:00')) < now):
                    list_name = next(lst['name'] for lst in lists if lst['id'] == card['idList'])
                    assignees = [members.get(member_id) for member_id in card.get('idMembers', [])]
                    overdue_cards.append({
                        'name': card['name'],
                        'list': list_name,
                        'due_date': datetime.fromisoformat(card['due'].replace('Z', '+00:00')),
                        'assignees': assignees
                    })
            
            return overdue_cards

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des tâches en retard: {str(e)}")
            raise

    def _get_list_id(self, list_name):
        """Récupère l'ID d'une liste Trello"""
        response = requests.get(
            f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/lists",
            params={
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token,
                'fields': 'name'
            }
        )
        response.raise_for_status()
        lists = response.json()
        
        # Chercher la liste (insensible à la casse)
        list_id = next(
            (lst['id'] for lst in lists if lst['name'].lower() == list_name.lower()),
            None
        )
        
        if not list_id:
            raise ValueError(f"Liste '{list_name}' non trouvée")
        
        return list_id

    def _create_trello_task(self, task_info=None):
        """Crée une tâche Trello avec les informations fournies"""
        try:
            info = task_info or self.task_info
            if not info:
                return "Désolée, je n'ai pas les informations nécessaires pour créer la tâche."

            # Créer la tâche avec TrelloManager
            result = TrelloManager.create_task_from_text(self.trello_integration, info)
            
            if result.get('success'):
                self.task_info = {}  # Réinitialiser après succès
                return f"✅ J'ai créé la tâche '{info['name']}' et je l'ai assignée à {info['assignee']}."
            else:
                return f"❌ Désolée, je n'ai pas pu créer la tâche : {result.get('error', 'Erreur inconnue')}"

        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la tâche: {str(e)}")
            return "Désolée, une erreur s'est produite lors de la création de la tâche. Veuillez réessayer."

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

            # Vérifier la signature de la fonction call_openai_api
            try:
                # Essayer d'abord avec le paramètre model
                response = call_openai_api(
                    model_name=RESPONSE_MODEL,  # Utiliser model_name au lieu de model
                    messages=[
                        {"role": "system", "content": system_message},
                        *messages
                    ],
                    temperature=0.7
                )
            except TypeError:
                # Si ça échoue, essayer sans spécifier le modèle (utilise peut-être un modèle par défaut)
                response = call_openai_api(
                    messages=[
                        {"role": "system", "content": system_message},
                        *messages
                    ],
                    temperature=0.7
                )

            if not response:
                raise ValueError("Pas de réponse de l'IA")

            return response

        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse IA: {str(e)}")
            return "Désolée, je n'ai pas pu traiter votre demande. Pouvez-vous reformuler ?"

    def _update_conversation_history(self, role, content):
        """Met à jour l'historique de la conversation"""
        try:
            # Ajouter à l'historique en mémoire
            self.conversation_history.append({
                'role': role,
                'content': content
            })
            
            # Sauvegarder dans la base de données
            if self.current_conversation:
                ChatHistory.objects.create(
                    chat=self.current_conversation,
                    user=self.user,
                    content=content,
                    is_user=(role == 'user')
                )
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de l'historique: {str(e)}")

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
        """Gère l'intention détectée"""
        try:
            # Gérer la fin de conversation
            if intent.get('integration') == 'conversation' and intent.get('action') == 'end':
                # Vérifier le contexte précédent pour une réponse appropriée
                if self.conversation_history:
                    last_assistant_msg = next(
                        (msg['content'] for msg in reversed(self.conversation_history)
                         if msg['role'] == 'assistant'),
                        None
                    )
                    
                    if 'erreur' in last_assistant_msg.lower():
                        return "Je suis désolée de ne pas avoir pu vous aider. N'hésitez pas si vous avez d'autres questions !"
                    else:
                        return "Je suis ravie d'avoir pu vous aider. À bientôt !"
                
                return "Au revoir ! N'hésitez pas si vous avez d'autres questions."
            
            # Vérifier si c'est une salutation simple
            if not intent.get('integration') and not intent.get('action'):
                if 'bonjour' in message.lower() or 'salut' in message.lower():
                    return "Comment puis-je vous aider aujourd'hui ?"
            
            # Si c'est une nouvelle demande Trello
            if intent.get('integration', '').lower() == 'trello':
                # Vérifier si l'intégration Trello est configurée
                if not self.trello_integration:
                    return "Désolée, vous n'avez pas encore configuré l'intégration Trello."
                
                # Si c'est une continuation avec une tâche en cours
                if intent.get('context_type') == 'continuation' and self.task_info:
                    return self.handle_trello_request(message)
                
                # Extraire les informations de la tâche
                task_info = self._extract_task_info(message)
                if not task_info:
                    return "Je n'ai pas pu comprendre les détails de la tâche. Pouvez-vous reformuler ?"
                
                # Vérifier si le membre assigné existe
                if task_info.get('assignee'):
                    try:
                        members = TrelloManager.get_board_members(self.trello_integration)
                        self.available_members = [member['username'] for member in members]
                        
                        if task_info['assignee'] not in self.available_members:
                            self.task_info = task_info  # Sauvegarder pour plus tard
                            return f"Je ne trouve pas le membre '{task_info['assignee']}'. 🤔\n\nLes membres disponibles sont : {', '.join(self.available_members)}\n\nÀ qui souhaitez-vous assigner cette tâche ?"
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la récupération des membres Trello: {str(e)}")
                        return "Désolée, je n'arrive pas à récupérer la liste des membres. Veuillez réessayer."
                
                # Créer la tâche
                return self.handle_trello_request(message)
            
            # Si c'est une demande HubSpot
            if intent.get('integration') == 'hubspot':
                return self.handle_hubspot_request(message)
            
            return "Je ne suis pas sûre de comprendre votre demande. Pouvez-vous préciser ?"

        except Exception as e:
            self.logger.error(f"Erreur dans _handle_intent: {str(e)}")
            self.logger.error(f"Contexte: {{'intent': {intent}, 'message': {message}}}")
            return "Désolée, une erreur s'est produite. Pouvez-vous reformuler votre demande ?"

    def _detect_general_query(self, message):
        """Détecte si le message est une question générale non liée aux intégrations"""
        message_lower = message.lower()
        
        for category, info in GENERAL_RESPONSES.items():
            if any(pattern in message_lower for pattern in info['patterns']):
                if callable(info['response']):
                    return info['response']()
                return info['response']
        
        return None

    def _suggest_integrations_for_action(self, action):
        """Suggère des intégrations appropriées pour une action donnée"""
        if action in INTEGRATION_CAPABILITIES:
            capability = INTEGRATION_CAPABILITIES[action]
            available_integrations = []
            
            # Vérifier quelles intégrations sont configurées pour l'utilisateur
            user_integrations = UserIntegration.objects.filter(
                user=self.user,
                enabled=True
            ).select_related('integration')
            
            # Liste des intégrations actives de l'utilisateur
            user_integration_names = [ui.integration.name for ui in user_integrations]
            self.logger.info(f"Intégrations actives: {user_integration_names}")
            
            for integration_name in capability['integrations']:
                # Recherche plus souple des intégrations
                for user_int_name in user_integration_names:
                    # Vérifier si le nom de l'intégration est contenu dans le nom complet
                    # Par exemple, "HubSpot" dans "HubSpot CRM"
                    if integration_name.lower() in user_int_name.lower():
                        available_integrations.append(user_int_name)
                        break
            
            if available_integrations:
                return {
                    'action': capability['name'],
                    'integrations': available_integrations,
                    'required_fields': capability['required_fields']
                }
            else:
                return {
                    'action': capability['name'],
                    'integrations': capability['integrations'],
                    'message': "Vous n'avez pas encore configuré ces intégrations. Souhaitez-vous en configurer une maintenant ?"
                }
        
        return None

    def process_message(self, chat_id, message_content):
        """Traite un message utilisateur et génère une réponse"""
        try:
            # Débogage: vérifier les intégrations actives
            active_integrations = self._get_active_integrations()
            self.logger.info(f"Intégrations actives pour l'utilisateur {self.user.id}: {active_integrations}")
            
            # Vérifier d'abord si c'est une question générale
            general_response = self._detect_general_query(message_content)
            if general_response:
                # Enregistrer le message utilisateur
                self._save_user_message(chat_id, message_content)
                # Enregistrer la réponse générale
                self._save_assistant_message(chat_id, general_response)
                return general_response
            
            # Détecter l'intention (création de contact, tâche, etc.)
            intent = self._detect_intent(message_content, self.conversation_history)
            
            if intent and 'action' in intent:
                action = intent['action']
                suggestion = self._suggest_integrations_for_action(action)
                
                if suggestion:
                    if 'message' in suggestion:
                        # Aucune intégration configurée
                        response = f"{suggestion['message']}"
                    else:
                        # Proposer les intégrations disponibles
                        integrations_list = ", ".join(suggestion['integrations'])
                        response = f"Je peux {suggestion['action'].lower()} dans les intégrations suivantes : {integrations_list}. Quelle intégration souhaitez-vous utiliser ?"
                    
                    # Enregistrer le message utilisateur
                    self._save_user_message(chat_id, message_content)
                    # Enregistrer la réponse
                    self._save_assistant_message(chat_id, response)
                    return response
            
            # Si ce n'est pas une question générale ni une action d'intégration reconnue,
            # générer une réponse libre avec GPT-4
            try:
                # Récupérer le chat actif
                chat = Chat.objects.get(id=chat_id) if chat_id else self._get_or_create_active_chat()
                
                # Sauvegarder le message utilisateur
                self._save_user_message(chat.id, message_content)
                
                # Récupérer l'historique de conversation pour le contexte
                chat_history = ChatHistory.objects.filter(chat=chat).order_by('created_at')
                conversation_context = [
                    {'role': 'user' if msg.is_user else 'assistant', 'content': msg.content}
                    for msg in chat_history.order_by('-created_at')[:10]  # Limiter aux 10 derniers messages
                ]
                conversation_context.reverse()  # Remettre dans l'ordre chronologique
                
                # Préparer le prompt pour une réponse générale
                system_prompt = """Tu es Alya, un assistant IA intelligent et serviable. 
                Tu peux répondre à des questions générales sur n'importe quel sujet.
                Tu es amical, poli et tu fournis des informations précises et utiles.
                Si tu ne connais pas la réponse à une question, tu le dis honnêtement.
                Tu peux aussi aider avec des intégrations comme Trello, HubSpot, Gmail, etc."""
                
                # Appeler l'API OpenAI pour une réponse générale
                response = self._get_ai_response(system_prompt + "\n" + "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_context]))
                
                # Sauvegarder la réponse
                self._save_assistant_message(chat.id, response)
                return response
        except Exception as e:
                self.logger.error(f"Erreur lors de la génération de réponse libre: {str(e)}")
                return "Je ne suis pas sûre de comprendre. Pouvez-vous reformuler votre question ?"
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du message: {str(e)}")
            raise

    @RetryHandler(max_retries=3, base_delay=2, max_delay=15)
    def handle_hubspot_request(self, text):
        """Gère les requêtes liées à HubSpot"""
        try:
            # Recherche plus flexible de l'intégration HubSpot
            hubspot_integrations = Integration.objects.filter(name__icontains='hubspot')
            user_integration = None
            
            for integration in hubspot_integrations:
                try:
                    user_integration = UserIntegration.objects.get(
                        user=self.user,
                        integration=integration,
                        enabled=True
                    )
                    if user_integration:
                        break
                except UserIntegration.DoesNotExist:
                    continue

            if not user_integration:
                return "L'intégration HubSpot n'est pas configurée. Voulez-vous que je vous aide à la configurer ?"

            # Gérer les différentes étapes de création de contact
            if self.conversation_state == 'contact_creation_start':
                self.contact_info['firstname'] = text.strip()
                self.conversation_state = 'waiting_for_lastname'
                return "Quel est le nom de famille du contact ?"
                
            elif self.conversation_state == 'waiting_for_lastname':
                self.contact_info['lastname'] = text.strip()
                self.conversation_state = 'waiting_for_email'
                return "Quelle est l'adresse email du contact ?"
                
            elif self.conversation_state == 'waiting_for_email':
                self.contact_info['email'] = text.strip()
                self.conversation_state = 'waiting_for_phone'
                return "Quel est le numéro de téléphone du contact ? (optionnel, appuyez sur Entrée si aucun)"
                
            elif self.conversation_state == 'waiting_for_phone':
                if text.strip():
                    self.contact_info['phone'] = text.strip()
                
                # Créer le contact dans HubSpot
                try:
                    result = self.create_hubspot_contact(self.contact_info)
                    self.conversation_state = None
                    self.contact_info = {}
                    return "✅ Contact créé avec succès dans HubSpot !"
                except Exception as e:
                    self.logger.error(f"Erreur création contact HubSpot: {str(e)}")
                    return "❌ Erreur lors de la création du contact. Voulez-vous réessayer ?"

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
            hubspot_integrations = Integration.objects.filter(name__icontains='hubspot')
            user_integration = None
            
            for integration in hubspot_integrations:
                try:
            user_integration = UserIntegration.objects.get(
                user=self.user,
                        integration=integration,
                enabled=True
            )
                    if user_integration:
                        break
                except UserIntegration.DoesNotExist:
                    continue
            
            if not user_integration:
                logger.error("Intégration HubSpot manquante")
                return "L'intégration HubSpot n'est pas activée. Veuillez l'activer dans la section Intégrations de votre compte."
            
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
            # Utiliser le chat fourni ou récupérer/créer le chat actif
            if not chat:
                chat = Chat.objects.filter(
                    user=self.user,
                    is_active=True
                ).first()
                
                if not chat:
                    # Créer un nouveau chat actif
                    chat = Chat.objects.create(
                        user=self.user,
                        is_active=True
                    )
            
            self.active_chat = chat

            # Détecter l'intention avant de sauvegarder le message
            intent = self._detect_intent(message, self.conversation_history)
            
            # Récupérer TOUT l'historique du chat actif
            chat_history = ChatHistory.objects.filter(
                chat=chat
            ).order_by('created_at')
            
            # Mettre à jour l'historique de conversation
            self.conversation_history = [
                {'role': 'user' if msg.is_user else 'assistant', 'content': msg.content}
                for msg in chat_history
            ]

            # Sauvegarder le message de l'utilisateur
            ChatHistory.objects.create(
                chat=chat,
                user=self.user,
                content=message,
                is_user=True
            )
            
            # Récupérer l'historique récent pour le contexte
            recent_history = ChatHistory.objects.filter(
                chat=chat
            ).order_by('-created_at')[:6]
            
            # Construire le contexte avec l'historique récent
            context_messages = []
            for hist in reversed(recent_history):
                role = "Utilisateur" if hist.is_user else "Assistant"
                context_messages.append(f"{role}: {hist.content}")
            
            # Ajouter les membres disponibles au contexte si pertinent
            if intent.get('integration') == 'trello' and self.available_members:
                context_messages.append(f"Assistant: Les membres disponibles sont : {', '.join(self.available_members)}")
            
            context = "\n".join(context_messages)

            # Générer la réponse
            completion = self.openai_client.chat.completions.create(
                model=RESPONSE_MODEL,
                messages=[
                    {"role": "system", "content": "Tu es Alya, une assistante IA experte en gestion de projet et intégrations. "
                                                "Maintiens la cohérence de la conversation et évite les salutations redondantes. "
                                                "Utilise uniquement les membres disponibles fournis dans le contexte. "
                                                "Ne suggère jamais de membres qui ne sont pas dans la liste fournie."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            response = completion.choices[0].message.content
            
            # Sauvegarder la réponse
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
            state = self.conversation_state
            
            if state == 'contact_creation_start':
                self.contact_info['firstname'] = message.strip()
                self.conversation_state = 'waiting_for_lastname'
                return "Quel est le nom de famille du contact ?"
                
            elif state == 'waiting_for_lastname':
                self.contact_info['lastname'] = message.strip()
                self.conversation_state = 'waiting_for_email'
                return "Quelle est l'adresse email du contact ?"
                
            elif state == 'waiting_for_email':
                self.contact_info['email'] = message.strip()
                # Créer le contact dans HubSpot
                try:
                    result = self.create_hubspot_contact(self.contact_info)
                    self.conversation_state = None
                    self.contact_info = {}
                    return "✅ Contact créé avec succès !"
                except Exception as e:
                    self.logger.error(f"Erreur création contact: {str(e)}")
                    return "❌ Erreur lors de la création du contact. Voulez-vous réessayer ?"

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
