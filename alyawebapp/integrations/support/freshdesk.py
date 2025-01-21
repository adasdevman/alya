from ..base import BaseIntegration
import requests
import base64

class FreshdeskIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'domain']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            auth_string = base64.b64encode(
                f"{self.config['api_key']}:X".encode()
            ).decode()
            session.headers.update({
                'Authorization': f'Basic {auth_string}',
                'Content-Type': 'application/json'
            })
            self.base_url = f"https://{self.config['domain']}.freshdesk.com/api/v2"
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Freshdesk: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/tickets")
            return response.status_code == 200
        except Exception:
            return False

    def get_tickets(self, status=None, page=1):
        """Récupère les tickets"""
        params = {'per_page': 100, 'page': page}
        if status:
            params['status'] = status

        response = self.client.get(f"{self.base_url}/tickets", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des tickets: {response.text}")

    def get_ticket(self, ticket_id):
        """Récupère un ticket spécifique"""
        response = self.client.get(f"{self.base_url}/tickets/{ticket_id}")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération du ticket: {response.text}")

    def create_ticket(self, subject, description, email, priority=1, status=2):
        """Crée un nouveau ticket"""
        data = {
            'subject': subject,
            'description': description,
            'email': email,
            'priority': priority,
            'status': status
        }
        response = self.client.post(f"{self.base_url}/tickets", json=data)
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création du ticket: {response.text}")

    def update_ticket(self, ticket_id, **kwargs):
        """Met à jour un ticket"""
        response = self.client.put(f"{self.base_url}/tickets/{ticket_id}", json=kwargs)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la mise à jour du ticket: {response.text}")

    def add_note(self, ticket_id, body, is_private=False):
        """Ajoute une note à un ticket"""
        data = {
            'body': body,
            'private': is_private
        }
        response = self.client.post(
            f"{self.base_url}/tickets/{ticket_id}/notes",
            json=data
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de l'ajout de la note: {response.text}")

    def get_contacts(self, page=1):
        """Récupère les contacts"""
        params = {'per_page': 100, 'page': page}
        response = self.client.get(f"{self.base_url}/contacts", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des contacts: {response.text}")

    def create_contact(self, name, email, phone=None, mobile=None):
        """Crée un nouveau contact"""
        data = {
            'name': name,
            'email': email
        }
        if phone:
            data['phone'] = phone
        if mobile:
            data['mobile'] = mobile

        response = self.client.post(f"{self.base_url}/contacts", json=data)
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création du contact: {response.text}") 