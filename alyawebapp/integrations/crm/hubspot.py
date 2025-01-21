from ..base import BaseIntegration
import requests

class HubspotIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Bearer {self.config['api_key']}",
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://api.hubapi.com'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation HubSpot: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/crm/v3/objects/contacts")
            return response.status_code == 200
        except Exception:
            return False

    def get_contacts(self, limit=100):
        """Récupère les contacts"""
        response = self.client.get(
            f"{self.base_url}/crm/v3/objects/contacts",
            params={'limit': limit}
        )
        if response.status_code == 200:
            return response.json()['results']
        raise Exception(f"Erreur lors de la récupération des contacts: {response.text}")

    def create_contact(self, properties):
        """Crée un nouveau contact"""
        response = self.client.post(
            f"{self.base_url}/crm/v3/objects/contacts",
            json={'properties': properties}
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création du contact: {response.text}")

    def update_contact(self, contact_id, properties):
        """Met à jour un contact"""
        response = self.client.patch(
            f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
            json={'properties': properties}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la mise à jour du contact: {response.text}")

    def get_deals(self, limit=100):
        """Récupère les deals"""
        response = self.client.get(
            f"{self.base_url}/crm/v3/objects/deals",
            params={'limit': limit}
        )
        if response.status_code == 200:
            return response.json()['results']
        raise Exception(f"Erreur lors de la récupération des deals: {response.text}") 