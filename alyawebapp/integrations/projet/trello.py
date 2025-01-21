from ..base import BaseIntegration
import requests

class TrelloIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'token']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            self.auth_params = {
                'key': self.config['api_key'],
                'token': self.config['token']
            }
            self.base_url = 'https://api.trello.com/1'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Trello: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(
                f"{self.base_url}/members/me",
                params=self.auth_params
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_boards(self):
        """Récupère les tableaux"""
        response = self.client.get(
            f"{self.base_url}/members/me/boards",
            params=self.auth_params
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des tableaux: {response.text}")

    def create_board(self, name, description=None):
        """Crée un nouveau tableau"""
        params = {
            **self.auth_params,
            'name': name,
            'desc': description or ''
        }
        response = self.client.post(f"{self.base_url}/boards", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création du tableau: {response.text}")

    def get_lists(self, board_id):
        """Récupère les listes d'un tableau"""
        response = self.client.get(
            f"{self.base_url}/boards/{board_id}/lists",
            params=self.auth_params
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des listes: {response.text}")

    def create_card(self, list_id, name, description=None, due=None):
        """Crée une nouvelle carte"""
        params = {
            **self.auth_params,
            'name': name,
            'desc': description or '',
            'idList': list_id
        }
        if due:
            params['due'] = due
            
        response = self.client.post(f"{self.base_url}/cards", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création de la carte: {response.text}")

    def add_comment(self, card_id, text):
        """Ajoute un commentaire à une carte"""
        params = {
            **self.auth_params,
            'text': text
        }
        response = self.client.post(
            f"{self.base_url}/cards/{card_id}/actions/comments",
            params=params
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de l'ajout du commentaire: {response.text}") 