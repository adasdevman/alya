import logging
from .handler import TrelloHandler
from django.conf import settings
import requests

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

    @classmethod
    def create_task_from_text(cls, user_integration, text):
        """Crée une tâche à partir d'une description textuelle"""
        try:
            # Extraire les informations du texte avec l'IA
            task_info = cls._extract_task_info(text)
            
            config = {
                'api_key': settings.TRELLO_API_KEY,
                'api_secret': settings.TRELLO_API_SECRET,
                'token': user_integration.access_token
            }
            
            handler = TrelloHandler(config)
            
            # Récupérer l'ID de la liste
            list_id = handler.get_list_id_by_name(task_info['board_id'], task_info['list_name'])
            
            # Créer la tâche
            task = handler.create_task(
                list_id=list_id,
                name=task_info['name'],
                description=task_info.get('description'),
                due_date=task_info.get('due_date'),
                member_name=task_info.get('assignee'),
                board_id=task_info['board_id']
            )
            
            return {
                'success': True,
                'data': task,
                'message': f"Tâche '{task_info['name']}' créée avec succès"
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

    @staticmethod
    def get_lists(integration):
        """Récupère les listes du tableau actif"""
        try:
            board_id = integration.get_active_board_id()
            if not board_id:
                logger.error("Pas de tableau actif configuré")
                return []

            url = f"{settings.TRELLO_API_URL}/boards/{board_id}/lists"
            params = {
                'key': settings.TRELLO_API_KEY,
                'token': integration.access_token,
                'fields': 'name'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            lists = response.json()
            return [lst['name'] for lst in lists]
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
                'fields': 'fullName,username'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            members = response.json()
            return [{'id': m['id'], 'name': m['fullName'] or m['username']} for m in members]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des membres: {str(e)}")
            return [] 