from ..base import BaseIntegration
import requests

class UiPathIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['tenant_url', 'client_id', 'client_secret']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            self.base_url = self.config['tenant_url']
            self.auth_data = {
                'grant_type': 'client_credentials',
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret']
            }
            session = requests.Session()
            self._refresh_token(session)
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation UiPath: {str(e)}")

    def _refresh_token(self, session):
        """Rafraîchit le token d'authentification"""
        response = session.post(f"{self.base_url}/oauth/token", data=self.auth_data)
        token = response.json()['access_token']
        session.headers.update({'Authorization': f'Bearer {token}'})

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/api/Robots")
            return response.status_code == 200
        except Exception:
            return False

    def start_job(self, process_key, input_arguments=None):
        """Démarre un job avec les arguments fournis"""
        data = {
            'startInfo': {
                'ReleaseKey': process_key,
                'Strategy': 'All',
                'InputArguments': input_arguments or {}
            }
        }
        response = self.client.post(f"{self.base_url}/api/Jobs/UiPath.Server.Configuration.OData.StartJobs", json=data)
        return response.json()

    def get_job_status(self, job_id):
        """Récupère le statut d'un job"""
        response = self.client.get(f"{self.base_url}/api/Jobs/{job_id}")
        return response.json() 