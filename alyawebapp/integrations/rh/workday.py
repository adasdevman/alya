from ..base import BaseIntegration
import requests
import json

class WorkdayIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['tenant_url', 'client_id', 'client_secret', 'tenant_name']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            # Obtention du token OAuth
            token_response = requests.post(
                f"{self.config['tenant_url']}/oauth/token",
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config['client_id'],
                    'client_secret': self.config['client_secret']
                }
            )
            token = token_response.json()['access_token']
            
            session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Workday-Tenant': self.config['tenant_name']
            })
            self.base_url = f"{self.config['tenant_url']}/api/v1"
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Workday: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/workers")
            return response.status_code == 200
        except Exception:
            return False

    def get_workers(self, params=None):
        """Récupère la liste des travailleurs"""
        response = self.client.get(f"{self.base_url}/workers", params=params)
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des travailleurs: {response.text}")

    def get_worker(self, worker_id):
        """Récupère les détails d'un travailleur"""
        response = self.client.get(f"{self.base_url}/workers/{worker_id}")
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération du travailleur: {response.text}")

    def create_worker(self, worker_data):
        """Crée un nouveau travailleur"""
        response = self.client.post(f"{self.base_url}/workers", json=worker_data)
        if response.status_code == 201:
            return response.json()['data']
        raise Exception(f"Erreur lors de la création du travailleur: {response.text}")

    def update_worker(self, worker_id, worker_data):
        """Met à jour un travailleur"""
        response = self.client.put(f"{self.base_url}/workers/{worker_id}", json=worker_data)
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la mise à jour du travailleur: {response.text}")

    def get_positions(self):
        """Récupère les postes disponibles"""
        response = self.client.get(f"{self.base_url}/positions")
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des postes: {response.text}") 