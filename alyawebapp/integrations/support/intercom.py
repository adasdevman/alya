from ..base import BaseIntegration
import requests

class IntercomIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['access_token']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Bearer {self.config['access_token']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://api.intercom.io'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Intercom: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/admins")
            return response.status_code == 200
        except Exception:
            return False

    def get_conversations(self, status=None, page=1):
        """Récupère les conversations"""
        params = {'per_page': 50, 'page': page}
        if status:
            params['status'] = status

        response = self.client.get(f"{self.base_url}/conversations", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des conversations: {response.text}")

    def get_conversation(self, conversation_id):
        """Récupère une conversation spécifique"""
        response = self.client.get(f"{self.base_url}/conversations/{conversation_id}")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération de la conversation: {response.text}")

    def reply_to_conversation(self, conversation_id, message_type, message):
        """Répond à une conversation"""
        data = {
            'type': 'conversation_part',
            'message_type': message_type,
            'body': message
        }
        response = self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/reply",
            json=data
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de l'envoi de la réponse: {response.text}")

    def create_contact(self, email, name=None, custom_attributes=None):
        """Crée un nouveau contact"""
        data = {
            'role': 'user',
            'email': email
        }
        if name:
            data['name'] = name
        if custom_attributes:
            data['custom_attributes'] = custom_attributes

        response = self.client.post(f"{self.base_url}/contacts", json=data)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création du contact: {response.text}")

    def search_contacts(self, query):
        """Recherche des contacts"""
        response = self.client.get(
            f"{self.base_url}/contacts/search",
            params={'query': query}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la recherche de contacts: {response.text}")

    def create_note(self, contact_id, content):
        """Ajoute une note à un contact"""
        data = {
            'body': content,
            'contact_id': contact_id
        }
        response = self.client.post(f"{self.base_url}/notes", json=data)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création de la note: {response.text}") 