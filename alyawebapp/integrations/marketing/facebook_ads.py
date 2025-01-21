from ..base import BaseIntegration
import requests

class FacebookAdsIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['access_token', 'account_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Bearer {self.config['access_token']}",
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://graph.facebook.com/v17.0'
            self.account_id = self.config['account_id']
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Facebook Ads: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(
                f"{self.base_url}/act_{self.account_id}/campaigns"
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_campaigns(self, status=None):
        """Récupère les campagnes"""
        params = {'fields': 'name,objective,status,lifetime_budget,daily_budget'}
        if status:
            params['filtering'] = [{'field': 'status', 'operator': 'EQUAL', 'value': status}]

        response = self.client.get(
            f"{self.base_url}/act_{self.account_id}/campaigns",
            params=params
        )
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des campagnes: {response.text}")

    def create_campaign(self, name, objective, status='PAUSED', daily_budget=None, lifetime_budget=None):
        """Crée une nouvelle campagne"""
        data = {
            'name': name,
            'objective': objective,
            'status': status
        }
        if daily_budget:
            data['daily_budget'] = int(daily_budget * 100)  # En centimes
        if lifetime_budget:
            data['lifetime_budget'] = int(lifetime_budget * 100)  # En centimes

        response = self.client.post(
            f"{self.base_url}/act_{self.account_id}/campaigns",
            json=data
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création de la campagne: {response.text}")

    def get_ad_sets(self, campaign_id=None):
        """Récupère les ensembles de publicités"""
        params = {
            'fields': 'name,campaign_id,targeting,bid_amount,budget_remaining'
        }
        if campaign_id:
            params['filtering'] = [{'field': 'campaign_id', 'operator': 'EQUAL', 'value': campaign_id}]

        response = self.client.get(
            f"{self.base_url}/act_{self.account_id}/adsets",
            params=params
        )
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des ensembles de publicités: {response.text}")

    def create_ad_set(self, campaign_id, name, targeting, bid_amount, daily_budget):
        """Crée un nouvel ensemble de publicités"""
        data = {
            'campaign_id': campaign_id,
            'name': name,
            'targeting': targeting,
            'bid_amount': int(bid_amount * 100),
            'daily_budget': int(daily_budget * 100)
        }
        response = self.client.post(
            f"{self.base_url}/act_{self.account_id}/adsets",
            json=data
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création de l'ensemble de publicités: {response.text}") 