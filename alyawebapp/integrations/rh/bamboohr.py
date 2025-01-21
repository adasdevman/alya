from ..base import BaseIntegration
import requests
import base64

class BambooHRIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'subdomain']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            auth_string = base64.b64encode(
                f"{self.config['api_key']}:x".encode()
            ).decode()
            session.headers.update({
                'Authorization': f'Basic {auth_string}',
                'Accept': 'application/json'
            })
            self.base_url = f"https://api.bamboohr.com/api/gateway.php/{self.config['subdomain']}/v1"
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation BambooHR: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/employees/directory")
            return response.status_code == 200
        except Exception:
            return False

    def get_employees(self):
        """Récupère la liste des employés"""
        response = self.client.get(f"{self.base_url}/employees/directory")
        if response.status_code == 200:
            return response.json()['employees']
        raise Exception(f"Erreur lors de la récupération des employés: {response.text}")

    def get_employee(self, employee_id, fields=None):
        """Récupère les détails d'un employé"""
        params = {'fields': ','.join(fields)} if fields else {}
        response = self.client.get(
            f"{self.base_url}/employees/{employee_id}",
            params=params
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération de l'employé: {response.text}")

    def get_time_off_requests(self, start_date=None, end_date=None):
        """Récupère les demandes de congés"""
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date

        response = self.client.get(
            f"{self.base_url}/time_off/requests",
            params=params
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des congés: {response.text}")

    def create_employee(self, employee_data):
        """Crée un nouvel employé"""
        response = self.client.post(
            f"{self.base_url}/employees",
            json=employee_data
        )
        if response.status_code == 201:
            return response.json() 