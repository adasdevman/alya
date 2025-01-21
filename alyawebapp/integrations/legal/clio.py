from ..base import BaseIntegration
import requests

class ClioIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['client_id', 'client_secret']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            auth_response = requests.post(
                'https://app.clio.com/oauth/token',
                json={
                    'client_id': self.config['client_id'],
                    'client_secret': self.config['client_secret'],
                    'grant_type': 'client_credentials'
                }
            )
            token = auth_response.json()['access_token']
            session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://app.clio.com/api/v4'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Clio: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/users/who_am_i")
            return response.status_code == 200
        except Exception:
            return False

    def get_matters(self):
        """Récupère les dossiers"""
        response = self.client.get(f"{self.base_url}/matters")
        return response.json()

    def create_matter(self, matter_data):
        """Crée un nouveau dossier"""
        response = self.client.post(f"{self.base_url}/matters", json=matter_data)
        return response.json() 