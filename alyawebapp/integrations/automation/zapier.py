from ..base import BaseIntegration
import requests

class ZapierIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['webhook_url']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            self.webhook_url = self.config['webhook_url']
            return requests.Session()
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Zapier: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.post(
                self.webhook_url,
                json={"test": True}
            )
            return response.status_code == 200
        except Exception:
            return False

    def trigger_zap(self, data):
        """Déclenche un Zap avec les données fournies"""
        response = self.client.post(self.webhook_url, json=data)
        return response.json() 