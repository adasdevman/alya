from ..base import BaseIntegration
import requests

class KlaviyoIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['private_key', 'public_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Klaviyo-API-Key {self.config['private_key']}",
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://a.klaviyo.com/api/v2'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Klaviyo: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/lists")
            return response.status_code == 200
        except Exception:
            return False

    def get_lists(self):
        """Récupère les listes"""
        response = self.client.get(f"{self.base_url}/lists")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des listes: {response.text}")

    def create_profile(self, email, properties=None):
        """Crée un nouveau profil"""
        data = {
            'token': self.config['public_key'],
            'properties': {
                '$email': email,
                **(properties or {})
            }
        }
        response = self.client.post(f"{self.base_url}/identify", json=data)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création du profil: {response.text}")

    def track_event(self, event_name, customer_properties, properties=None):
        """Enregistre un événement"""
        data = {
            'token': self.config['public_key'],
            'event': event_name,
            'customer_properties': customer_properties,
            'properties': properties or {}
        }
        response = self.client.post(f"{self.base_url}/track", json=data)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de l'enregistrement de l'événement: {response.text}") 