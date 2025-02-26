from ..base import BaseIntegration
import requests
from typing import Dict, Any, List
import logging
from urllib.parse import urlencode
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class TrelloHandler(BaseIntegration):
    AUTH_URL = "https://trello.com/1/authorize"
    API_BASE_URL = "https://api.trello.com/1"
    
    REQUIRED_SCOPES = [
        "read",
        "write",
        "account"
    ]
    
    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.token = config.get('token')
        self.redirect_uri = config['redirect_uri']
        
        self.initialize_client()

    def initialize_client(self):
        self.headers = {
            'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.token}"' if self.token else None,
            'Content-Type': 'application/json'
        }

    def get_authorization_url(self, state=None):
        params = {
            'expiration': 'never',
            'name': 'Alya App',
            'scope': ','.join(self.REQUIRED_SCOPES),
            'response_type': 'token',
            'key': self.api_key,
            'return_url': self.redirect_uri
        }
        
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"URL d'autorisation Trello générée: {auth_url}")
        return auth_url

    def create_card(self, list_id: str, name: str, desc: str = None, due: str = None, member_ids: List[str] = None):
        """Crée une carte dans une liste Trello"""
        url = f"{self.API_BASE_URL}/cards"
        
        data = {
            'idList': list_id,
            'name': name,
            'key': self.api_key,
            'token': self.token
        }
        
        if desc:
            data['desc'] = desc
        if due:
            data['due'] = due
        if member_ids:
            data['idMembers'] = ','.join(member_ids)
            
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_boards(self):
        """Récupère les tableaux de l'utilisateur"""
        url = f"{self.API_BASE_URL}/members/me/boards"
        params = {
            'key': self.api_key,
            'token': self.token
        }
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_lists(self, board_id: str):
        """Récupère les listes d'un tableau"""
        url = f"{self.API_BASE_URL}/boards/{board_id}/lists"
        params = {
            'key': self.api_key,
            'token': self.token
        }
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_member_id_by_name(self, board_id: str, member_name: str):
        """Récupère l'ID d'un membre par son nom"""
        url = f"{self.API_BASE_URL}/boards/{board_id}/members"
        params = {
            'key': self.api_key,
            'token': self.token
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        members = response.json()
        
        for member in members:
            if member['fullName'].lower() == member_name.lower():
                return member['id']
        return None

    def get_list_id_by_name(self, board_id: str, list_name: str):
        """Récupère l'ID d'une liste par son nom"""
        lists = self.get_lists(board_id)
        for lst in lists:
            if lst['name'].lower() == list_name.lower():
                return lst['id']
        return None

    def create_task(self, list_id: str, name: str, description: str = None, 
                    due_date: str = None, member_name: str = None, board_id: str = None):
        """Crée une tâche dans une liste"""
        data = {
            'name': name,
            'idList': list_id,
            'key': self.api_key,
            'token': self.token
        }
        
        if description:
            data['desc'] = description
            
        if due_date:
            data['due'] = due_date
            
        if member_name and board_id:
            member_id = self.get_member_id_by_name(board_id, member_name)
            if member_id:
                data['idMembers'] = [member_id]

        url = f"{self.API_BASE_URL}/cards"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_overdue_tasks(self, board_id: str = None):
        """Récupère les tâches en retard"""
        url = f"{self.API_BASE_URL}/boards/{board_id}/cards"
        params = {
            'key': self.api_key,
            'token': self.token,
            'filter': 'due'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        cards = response.json()
        
        overdue_cards = []
        now = datetime.now()
        
        for card in cards:
            if card.get('due') and datetime.fromisoformat(card['due'].replace('Z', '+00:00')) < now:
                overdue_cards.append(card)
                
        return overdue_cards

    def create_board(self, name: str, description: str = None, background_color: str = None):
        """Crée un nouveau tableau"""
        data = {
            'name': name,
            'key': self.api_key,
            'token': self.token
        }
        if description:
            data['desc'] = description
        if background_color:
            data['prefs_background'] = background_color

        url = f"{self.API_BASE_URL}/boards"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def create_list(self, board_id: str, name: str, position: str = 'bottom'):
        """Crée une nouvelle liste dans un tableau"""
        data = {
            'name': name,
            'idBoard': board_id,
            'pos': position,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/lists"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def move_card(self, card_id: str, list_id: str):
        """Déplace une carte vers une autre liste"""
        data = {
            'idList': list_id,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/cards/{card_id}"
        response = requests.put(url, json=data)
        response.raise_for_status()
        return response.json()

    def add_comment(self, card_id: str, comment: str):
        """Ajoute un commentaire à une carte"""
        data = {
            'text': comment,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/cards/{card_id}/actions/comments"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def add_checklist(self, card_id: str, name: str, items: list):
        """Ajoute une checklist à une carte"""
        # Créer la checklist
        checklist_data = {
            'name': name,
            'idCard': card_id,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/checklists"
        response = requests.post(url, json=checklist_data)
        response.raise_for_status()
        checklist = response.json()

        # Ajouter les items
        for item in items:
            item_data = {
                'name': item,
                'key': self.api_key,
                'token': self.token
            }
            url = f"{self.API_BASE_URL}/checklists/{checklist['id']}/checkItems"
            requests.post(url, json=item_data)

        return checklist

    def add_label(self, card_id: str, name: str, color: str = None):
        """Ajoute un label à une carte"""
        data = {
            'name': name,
            'color': color,
            'idCard': card_id,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/cards/{card_id}/labels"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_board_activity(self, board_id: str, limit: int = 50):
        """Récupère l'activité récente d'un tableau"""
        params = {
            'limit': limit,
            'key': self.api_key,
            'token': self.token
        }

        url = f"{self.API_BASE_URL}/boards/{board_id}/actions"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json() 