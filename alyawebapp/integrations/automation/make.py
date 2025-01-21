from ..base import BaseIntegration
import requests

class MakeIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_token', 'team_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Token {self.config['api_token']}",
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://eu1.make.com/api/v2'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Make: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/teams/{self.config['team_id']}")
            return response.status_code == 200
        except Exception:
            return False

    def get_scenarios(self):
        """Récupère les scénarios"""
        response = self.client.get(
            f"{self.base_url}/teams/{self.config['team_id']}/scenarios"
        )
        if response.status_code == 200:
            return response.json()['scenarios']
        raise Exception(f"Erreur lors de la récupération des scénarios: {response.text}")

    def start_scenario(self, scenario_id, data=None):
        """Démarre un scénario"""
        response = self.client.post(
            f"{self.base_url}/scenarios/{scenario_id}/run",
            json=data or {}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors du démarrage du scénario: {response.text}")

    def get_scenario_history(self, scenario_id):
        """Récupère l'historique d'un scénario"""
        response = self.client.get(
            f"{self.base_url}/scenarios/{scenario_id}/executions"
        )
        if response.status_code == 200:
            return response.json()['executions']
        raise Exception(f"Erreur lors de la récupération de l'historique: {response.text}") 