import logging
import json
import requests
import re
from datetime import datetime, timedelta, timezone
from ..exceptions import NetworkError

logger = logging.getLogger(__name__)

class TrelloHandler:
    """Gestionnaire pour les intégrations Trello"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.trello_integration = None
        self.task_info = {}
        self.available_members = []
        self.members_data = []
        self.available_lists = []
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Trello si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='trello')
            self.trello_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.trello_integration = None
    
    def handle_request(self, message):
        """Gère les requêtes Trello"""
        from django.conf import settings
        from ..utils.retry_handler import RetryHandler
        
        try:
            if not self.trello_integration:
                return "Vous n'avez pas installé cette intégration. Veuillez configurer Trello dans vos intégrations avant de l'utiliser."

            active_board_id = self.trello_integration.get_active_board_id()
            if not active_board_id:
                return "❌ Aucun tableau Trello actif n'a été configuré. Veuillez configurer un tableau dans vos paramètres d'intégration Trello."

            # Vérifier si le tableau existe et est accessible
            if not self._verify_board_exists(active_board_id):
                return f"❌ Le tableau Trello configuré n'est pas accessible. Veuillez vérifier que le tableau existe et que vous avez les permissions nécessaires."

            # Si c'est une demande de tâches en retard
            if "tâches en retard" in message.lower():
                overdue_tasks = self.get_overdue_tasks()
                
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

            # Si c'est une demande de lister les tableaux
            if "affiche" in message.lower() and "tableaux" in message.lower():
                boards = self._get_available_boards()
                if not boards:
                    return "❌ Je n'ai pas pu récupérer vos tableaux Trello. Veuillez vérifier votre intégration."
                
                response = "📋 Voici vos tableaux Trello :\n\n"
                active_board_id = self.trello_integration.get_active_board_id()
                
                for board in boards:
                    is_active = board['id'] == active_board_id
                    response += f"• {board['name']}{' (Tableau actif)' if is_active else ''}\n"
                
                response += "\nVous pouvez changer de tableau actif dans les paramètres de votre intégration Trello."
                return response

            # Si c'est une demande de lister les listes du tableau
            if "affiche" in message.lower() and "listes" in message.lower():
                self._load_board_lists()
                
                if not self.available_lists:
                    return "❌ Je n'ai pas pu récupérer les listes du tableau. Veuillez vérifier que le tableau existe et que vous avez les permissions nécessaires."
                
                response = "📝 Voici les listes disponibles sur votre tableau Trello actif :\n\n"
                for lst in self.available_lists:
                    response += f"• {lst}\n"
                
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
                return self._create_task()

            # Récupérer d'abord les membres disponibles
            try:
                self._load_board_members()
                self._load_board_lists()
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des données Trello: {str(e)}")
                return "Désolée, je n'arrive pas à récupérer les informations du tableau Trello. Veuillez vérifier votre configuration."

            # Extraire les informations de la tâche
            task_info = self._extract_task_info(message)
            if not task_info:
                return "Je n'ai pas pu comprendre les détails de la tâche. Pouvez-vous reformuler en précisant le nom de la tâche entre guillemets simple (par exemple : 'Ma tâche') et la liste où l'ajouter ?"

            # Vérifier si la liste existe
            if task_info.get('list_name') and task_info['list_name'] not in self.available_lists:
                list_suggestions = "\n\nListes disponibles :\n" + "\n".join([f"• {lst}" for lst in self.available_lists])
                return f"❌ La liste '{task_info['list_name']}' n'existe pas dans le tableau actif.{list_suggestions}"

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
                    return f"❌ Je ne trouve pas le membre '{task_info['assignee']}' dans le tableau actif.\n\nMembres disponibles :\n{', '.join(self.available_members)}\n\nÀ qui souhaitez-vous assigner cette tâche ? (utilisez le nom d'utilisateur)"
                else:
                    # Utiliser le username pour l'assignation
                    task_info['assignee'] = member['username']

            # Créer la tâche avec les informations complètes
            self.task_info = task_info
            return self._create_task()

        except Exception as e:
            logger.error(f"Erreur lors de la gestion de la requête Trello: {str(e)}")
            return "Désolée, une erreur s'est produite lors de la création de la tâche. Veuillez réessayer."
    
    def _verify_board_exists(self, board_id):
        """Vérifie si le tableau existe et est accessible"""
        from django.conf import settings
        
        try:
            response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{board_id}",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'fields': 'name'
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du tableau: {str(e)}")
            return False
    
    def _get_available_boards(self):
        """Récupère la liste des tableaux disponibles"""
        from django.conf import settings
        
        try:
            response = requests.get(
                f"{settings.TRELLO_API_URL}/members/me/boards",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'filter': 'open',
                    'fields': 'name'
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tableaux: {str(e)}")
            return []
    
    def _load_board_members(self):
        """Charge les membres du tableau Trello actif"""
        from django.conf import settings
        
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
    
    def _load_board_lists(self):
        """Charge les listes du tableau Trello actif"""
        from django.conf import settings
        
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
        self.available_lists = [lst['name'] for lst in lists]
    
    def _extract_task_info(self, text):
        """Extrait les informations de tâche du texte"""
        try:
            # Extraire le nom de la tâche entre guillemets simples
            name_match = re.search(r"'([^']*)'", text)
            name = name_match.group(1) if name_match else None
            
            if not name:
                return None  # Si pas de nom clairement identifié, on ne peut pas créer la tâche

            # Extraire la colonne
            column_match = re.search(r"(?:dans|colonne)\s+(?:la colonne\s+)?['\"]?([^'\"]+)['\"]?", text, re.IGNORECASE)
            list_name = column_match.group(1) if column_match else "À faire"
            
            # Nettoyer le nom de la liste (enlever les guillemets)
            list_name = list_name.strip("'").strip('"')

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
            elif "demain" in text.lower():
                tomorrow = datetime.now() + timedelta(days=1)
                tomorrow = tomorrow.replace(hour=23, minute=59, second=59)
                due_date = tomorrow.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            elif "semaine prochaine" in text.lower():
                next_week = datetime.now() + timedelta(days=7)
                next_week = next_week.replace(hour=23, minute=59, second=59)
                due_date = next_week.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            return {
                "name": name,
                "list_name": list_name,
                "assignee": assignee,
                "due_date": due_date
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des informations de tâche: {str(e)}")
            return None
    
    def get_overdue_tasks(self):
        """Récupère les tâches en retard de Trello"""
        from django.conf import settings
        
        try:
            # Récupérer toutes les listes du tableau
            lists_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/lists",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token
                }
            )
            lists_response.raise_for_status()
            lists = lists_response.json()
            
            # Récupérer toutes les cartes avec une date d'échéance
            cards_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/cards",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'fields': 'name,due,idList,dueComplete,idMembers'
                }
            )
            cards_response.raise_for_status()
            all_cards = cards_response.json()
            
            # Récupérer les membres du tableau
            members_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/members",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token
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
            logger.error(f"Erreur lors de la récupération des tâches en retard: {str(e)}")
            raise
    
    def _get_list_id(self, list_name):
        """Récupère l'ID d'une liste Trello"""
        from django.conf import settings
        
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
            lists_names = [lst['name'] for lst in lists]
            error_msg = f"Liste '{list_name}' non trouvée. Listes disponibles : {', '.join(lists_names)}"
            raise ValueError(error_msg)
        
        return list_id
    
    def _create_task(self):
        """Crée une tâche Trello avec les informations fournies"""
        from django.conf import settings
        
        try:
            info = self.task_info
            if not info or not info.get('name'):
                return "Désolée, je n'ai pas les informations nécessaires pour créer la tâche."

            # Obtenir l'id de la liste
            try:
                list_id = self._get_list_id(info['list_name'])
            except ValueError as e:
                # Retourner une liste des listes disponibles
                return f"❌ {str(e)}"

            # Création de la tâche dans Trello
            data = {
                'name': info['name'],
                'idList': list_id,
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token
            }

            if info.get('due_date'):
                data['due'] = info['due_date']

            if info.get('assignee'):
                # Trouver l'ID du membre à partir du nom d'utilisateur
                member = next(
                    (m for m in self.members_data if 
                    m.get('username', '').lower() == info['assignee'].lower()),
                    None
                )
                if member:
                    data['idMembers'] = [member['id']]

            response = requests.post(
                f"{settings.TRELLO_API_URL}/cards",
                json=data
            )
            response.raise_for_status()

            # Réinitialiser après succès
            result = response.json()
            card_url = result.get('shortUrl', '#')
            self.task_info = {}
            
            success_message = f"✅ J'ai créé la tâche '{info['name']}' dans la liste '{info['list_name']}'"
            if info.get('assignee'):
                success_message += f" et je l'ai assignée à {info['assignee']}"
            
            if info.get('due_date'):
                due_date = datetime.fromisoformat(info['due_date'].replace('Z', '+00:00'))
                success_message += f", avec échéance le {due_date.strftime('%d/%m/%Y')}"
            
            success_message += f"\n\nVoir la carte: {card_url}"
            
            return success_message

        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche: {str(e)}")
            return f"Désolée, une erreur s'est produite lors de la création de la tâche: {str(e)}" 