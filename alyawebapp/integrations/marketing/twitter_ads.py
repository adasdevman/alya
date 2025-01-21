from ..base import BaseIntegration
import requests

class TwitterAdsIntegration(BaseIntegration):
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
            self.base_url = 'https://ads-api.twitter.com/11'
            self.account_id = self.config['account_id']
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Twitter Ads: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(
                f"{self.base_url}/accounts/{self.account_id}"
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_campaigns(self, status=None):
        """Récupère les campagnes"""
        params = {'count': 100}
        if status:
            params['entity_status'] = status

        response = self.client.get(
            f"{self.base_url}/accounts/{self.account_id}/campaigns",
            params=params
        )
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des campagnes: {response.text}")

    def create_campaign(self, name, funding_instrument_id, daily_budget=None, total_budget=None):
        """Crée une nouvelle campagne"""
        data = {
            'name': name,
            'funding_instrument_id': funding_instrument_id,
            'entity_status': 'PAUSED'
        }
        if daily_budget:
            data['daily_budget_amount_local_micro'] = int(daily_budget * 1000000)
        if total_budget:
            data['total_budget_amount_local_micro'] = int(total_budget * 1000000)

        response = self.client.post(
            f"{self.base_url}/accounts/{self.account_id}/campaigns",
            json=data
        )
        if response.status_code == 201:
            return response.json()['data']
        raise Exception(f"Erreur lors de la création de la campagne: {response.text}")

    def get_line_items(self, campaign_id=None):
        """Récupère les éléments de ligne"""
        params = {'count': 100}
        if campaign_id:
            params['campaign_id'] = campaign_id

        response = self.client.get(
            f"{self.base_url}/accounts/{self.account_id}/line_items",
            params=params
        )
        if response.status_code == 200:
            return response.json()['data']
        raise Exception(f"Erreur lors de la récupération des éléments de ligne: {response.text}")

    def create_line_item(self, campaign_id, name, product_type, bid_amount, objective):
        """Crée un nouvel élément de ligne"""
        data = {
            'campaign_id': campaign_id,
            'name': name,
            'product_type': product_type,
            'bid_amount_local_micro': int(bid_amount * 1000000),
            'objective': objective,
            'entity_status': 'PAUSED'
        }
        response = self.client.post(
            f"{self.base_url}/accounts/{self.account_id}/line_items",
            json=data
        )
        if response.status_code == 201:
            return response.json()['data']
        raise Exception(f"Erreur lors de la création de l'élément de ligne: {response.text}") 