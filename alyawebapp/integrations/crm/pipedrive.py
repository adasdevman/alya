from ..base import BaseIntegration
import requests

class PipedriveIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_token', 'company_domain']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Bearer {self.config['api_token']}",
                'Content-Type': 'application/json'
            })
            self.base_url = f"https://{self.config['company_domain']}.pipedrive.com/api/v1"
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Pipedrive: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/users/me")
            return response.status_code == 200
        except Exception:
            return False

    def get_deals(self):
        """Récupère les deals"""
        response = self.client.get(f"{self.base_url}/deals")
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des deals: {response.text}")

    def create_deal(self, title, value=0, currency='EUR', status='open'):
        """Crée un nouveau deal"""
        data = {
            'title': title,
            'value': value,
            'currency': currency,
            'status': status
        }
        response = self.client.post(f"{self.base_url}/deals", json=data)
        if response.status_code == 201:
            return response.json()['data']
        raise Exception(f"Erreur lors de la création du deal: {response.text}")

    def get_contacts(self):
        """Récupère les contacts"""
        response = self.client.get(f"{self.base_url}/persons")
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des contacts: {response.text}")

    def create_contact(self, name, email=None, phone=None):
        """Crée un nouveau contact"""
        data = {'name': name}
        if email:
            data['email'] = [{'value': email, 'primary': True}]
        if phone:
            data['phone'] = [{'value': phone, 'primary': True}]
        
        response = self.client.post(f"{self.base_url}/persons", json=data)
        if response.status_code == 201:
            return response.json()['data']
        raise Exception(f"Erreur lors de la création du contact: {response.text}") 