from ..base import BaseIntegration
import requests

class ActiveCampaignIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'base_url']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Api-Token': self.config['api_key'],
                'Content-Type': 'application/json'
            })
            self.base_url = f"{self.config['base_url']}/api/3"
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation ActiveCampaign: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/contacts")
            return response.status_code == 200
        except Exception:
            return False

    def get_contacts(self, limit=100):
        """Récupère les contacts"""
        response = self.client.get(f"{self.base_url}/contacts", params={'limit': limit})
        if response.status_code == 200:
            return response.json()['contacts']
        raise Exception(f"Erreur lors de la récupération des contacts: {response.text}")

    def create_contact(self, email, first_name=None, last_name=None, phone=None):
        """Crée un nouveau contact"""
        data = {
            'contact': {
                'email': email,
                'firstName': first_name,
                'lastName': last_name,
                'phone': phone
            }
        }
        response = self.client.post(f"{self.base_url}/contacts", json=data)
        if response.status_code == 201:
            return response.json()['contact']
        raise Exception(f"Erreur lors de la création du contact: {response.text}")

    def create_automation(self, name, triggers=None, actions=None):
        """Crée une nouvelle automation"""
        data = {
            'automation': {
                'name': name,
                'triggers': triggers or [],
                'actions': actions or []
            }
        }
        response = self.client.post(f"{self.base_url}/automations", json=data)
        if response.status_code == 201:
            return response.json()['automation']
        raise Exception(f"Erreur lors de la création de l'automation: {response.text}") 