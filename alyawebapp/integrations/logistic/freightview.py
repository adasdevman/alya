from ..base import BaseIntegration
import requests

class FreightviewIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'account_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f'Bearer {self.config["api_key"]}',
                'Account-Id': self.config['account_id']
            })
            self.base_url = 'https://api.freightview.com/v1'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Freightview: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/shipments")
            return response.status_code == 200
        except Exception:
            return False

    def get_shipments(self, status=None):
        """Récupère les expéditions"""
        params = {'status': status} if status else {}
        response = self.client.get(f"{self.base_url}/shipments", params=params)
        return response.json()

    def create_shipment(self, shipment_data):
        """Crée une nouvelle expédition"""
        response = self.client.post(f"{self.base_url}/shipments", json=shipment_data)
        return response.json() 