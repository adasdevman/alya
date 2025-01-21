from ..base import BaseIntegration
import requests

class GoogleAdsIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['client_id', 'client_secret', 'developer_token', 'refresh_token', 'customer_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            self._refresh_access_token(session)
            self.base_url = 'https://googleads.googleapis.com/v14'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Google Ads: {str(e)}")

    def _refresh_access_token(self, session):
        """Rafraîchit le token d'accès"""
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret'],
                'refresh_token': self.config['refresh_token'],
                'grant_type': 'refresh_token'
            }
        )
        token = response.json()['access_token']
        session.headers.update({
            'Authorization': f'Bearer {token}',
            'developer-token': self.config['developer_token'],
            'login-customer-id': self.config['customer_id']
        })

    def test_connection(self):
        try:
            self.get_campaigns()
            return True
        except Exception:
            return False

    def get_campaigns(self):
        """Récupère les campagnes"""
        response = self.client.get(
            f"{self.base_url}/customers/{self.config['customer_id']}/campaigns"
        )
        if response.status_code == 200:
            return response.json()['results']
        raise Exception(f"Erreur lors de la récupération des campagnes: {response.text}")

    def create_campaign(self, name, budget_amount, start_date, end_date=None):
        """Crée une nouvelle campagne"""
        data = {
            'campaign': {
                'name': name,
                'status': 'PAUSED',
                'campaignBudget': {
                    'amountMicros': int(budget_amount * 1000000)
                },
                'startDate': start_date.strftime('%Y-%m-%d')
            }
        }
        if end_date:
            data['campaign']['endDate'] = end_date.strftime('%Y-%m-%d')

        response = self.client.post(
            f"{self.base_url}/customers/{self.config['customer_id']}/campaigns",
            json=data
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création de la campagne: {response.text}") 