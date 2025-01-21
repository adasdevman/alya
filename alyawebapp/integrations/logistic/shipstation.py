from ..base import BaseIntegration
import requests
import base64

class ShipStationIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'api_secret']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            auth_string = base64.b64encode(
                f"{self.config['api_key']}:{self.config['api_secret']}".encode()
            ).decode()
            session.headers.update({
                'Authorization': f'Basic {auth_string}',
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://ssapi.shipstation.com'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation ShipStation: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/orders")
            return response.status_code == 200
        except Exception:
            return False

    def get_orders(self, status=None):
        """Récupère les commandes"""
        params = {'orderStatus': status} if status else {}
        response = self.client.get(f"{self.base_url}/orders", params=params)
        return response.json()

    def create_label(self, order_id):
        """Crée une étiquette d'expédition"""
        response = self.client.post(
            f"{self.base_url}/orders/createlabelfororder",
            json={'orderId': order_id}
        )
        return response.json() 