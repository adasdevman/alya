import logging
from .handler import TrelloHandler
from django.conf import settings
import requests
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TrelloManager:
    @classmethod
    def execute_action(cls, user_integration, method_name, params):
        """Exécute une action Trello"""
        try:
            config = {
                'api_key': settings.TRELLO_API_KEY,
                'api_secret': settings.TRELLO_API_SECRET,
                'redirect_uri': settings.TRELLO_REDIRECT_URI,
                'token': user_integration.access_token,
                **user_integration.config
            }

            handler = TrelloHandler(config)

            if not hasattr(handler, method_name):
                raise Exception(f"Méthode {method_name} non trouvée pour Trello")

            method = getattr(handler, method_name)
            result = method(**params)

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {method_name} sur Trello: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _extract_task_info(text):
        """Extrait les informations de tâche du texte"""
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
                due_date = (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")

            return {
                "name": name,
                "list_name": list_name,
                "assignee": assignee,
                "due_date": due_date
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des informations de tâche: {str(e)}")
            return None

    @classmethod
    def create_task_from_text(cls, user_integration, text):
        """Crée une tâche à partir d'une description textuelle"""
        try:
            # Si text est déjà un dictionnaire, l'utiliser directement
            task_info = text if isinstance(text, dict) else cls._extract_task_info(text)
            
            if not task_info:
                return {
                    'success': False,
                    'error': "Impossible d'extraire les informations de la tâche"
                }
            
            # Récupérer l'ID de la liste
            board_id = user_integration.get_active_board_id()
            lists = cls.get_lists(user_integration)
            list_map = {lst['name'].lower(): lst['id'] for lst in lists}
            list_id = list_map.get(task_info['list_name'].lower())
            
            if not list_id:
                return {
                    'success': False,
                    'error': f"Liste '{task_info['list_name']}' non trouvée"
                }
            
            # Créer la tâche
            data = {
                'name': task_info['name'],
                'idList': list_id,
                'key': settings.TRELLO_API_KEY,
                'token': user_integration.access_token
            }
            
            if task_info.get('due_date'):
                data['due'] = task_info['due_date']
            
            if task_info.get('assignee'):
                members = cls.get_board_members(user_integration)
                # Créer une correspondance simple avec les usernames
                member_map = {m['username'].lower(): m for m in members}
                
                member = member_map.get(task_info['assignee'].lower())
                if member:
                    data['idMembers'] = [member['id']]  # Trello attend une liste d'IDs
                    task_info['assignee'] = member['display_name']
            
            response = requests.post(
                f"{settings.TRELLO_API_URL}/cards",
                json=data
            )
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json(),
                'message': f"✅ J'ai créé la tâche '{task_info['name']}' et je l'ai assignée à {task_info['assignee']}."
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche Trello: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def get_overdue_tasks_summary(cls, user_integration):
        """Récupère un résumé des tâches en retard"""
        try:
            config = {
                'api_key': settings.TRELLO_API_KEY,
                'api_secret': settings.TRELLO_API_SECRET,
                'token': user_integration.access_token
            }
            
            handler = TrelloHandler(config)
            overdue_tasks = handler.get_overdue_tasks()
            
            return {
                'success': True,
                'data': overdue_tasks,
                'message': f"Il y a {len(overdue_tasks)} tâches en retard"
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tâches en retard: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def check_connection(integration):
        """Vérifie la connexion à Trello"""
        try:
            # Tente de récupérer les tableaux pour vérifier la connexion
            boards = TrelloManager.get_boards(integration)
            return bool(boards)  # Retourne True si on a pu récupérer les tableaux
        except Exception as e:
            logger.error(f"Erreur de connexion Trello: {str(e)}")
            return False

    @staticmethod
    def get_boards(integration):
        """Récupère la liste des tableaux Trello"""
        url = f"{settings.TRELLO_API_URL}/members/me/boards"
        params = {
            'key': settings.TRELLO_API_KEY,
            'token': integration.access_token,
            'fields': 'name,id'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_lists(cls, user_integration):
        """Récupère les listes du tableau actif"""
        try:
            board_id = user_integration.get_active_board_id()
            url = f"{settings.TRELLO_API_URL}/boards/{board_id}/lists"
            params = {
                'key': settings.TRELLO_API_KEY,
                'token': user_integration.access_token,
                'fields': 'name,id'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des listes: {str(e)}")
            return []

    @staticmethod
    def get_board_members(integration):
        """Récupère les membres du tableau actif"""
        try:
            board_id = integration.get_active_board_id()
            url = f"{settings.TRELLO_API_URL}/boards/{board_id}/members"
            params = {
                'key': settings.TRELLO_API_KEY,
                'token': integration.access_token,
                'fields': 'username,fullName'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            members = response.json()
            return [{
                'id': member.get('id'),
                'username': member.get('username'),
                'display_name': member.get('username')  # Utiliser uniquement le username pour l'affichage
            } for member in members]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des membres: {str(e)}")
            return [] 