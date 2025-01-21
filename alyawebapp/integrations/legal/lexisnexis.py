from ..base import BaseIntegration
import requests

class LexisNexisIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'api_secret']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            auth_response = requests.post(
                'https://auth.lexisnexis.com/oauth/v2/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config['api_key'],
                    'client_secret': self.config['api_secret']
                }
            )
            token = auth_response.json()['access_token']
            session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://api.lexisnexis.com/v1'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation LexisNexis: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/status")
            return response.status_code == 200
        except Exception:
            return False

    def search_cases(self, query, jurisdiction=None):
        """Recherche des cas juridiques"""
        params = {
            'q': query,
            'jurisdiction': jurisdiction
        }
        response = self.client.get(f"{self.base_url}/cases", params=params)
        return response.json()

    def get_case_details(self, case_id):
        """Récupère les détails d'un cas"""
        response = self.client.get(f"{self.base_url}/cases/{case_id}")
        return response.json()

    def search_statutes(self, query, jurisdiction):
        """Recherche des lois et règlements"""
        params = {
            'q': query,
            'jurisdiction': jurisdiction
        }
        response = self.client.get(f"{self.base_url}/statutes", params=params)
        return response.json() 