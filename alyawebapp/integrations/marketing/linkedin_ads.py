from ..base import BaseIntegration
import requests

class LinkedInAdsIntegration(BaseIntegration):
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
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            })
            self.base_url = 'https://api.linkedin.com/v2'
            self.account_id = self.config['account_id']
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation LinkedIn Ads: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(
                f"{self.base_url}/adAccounts/{self.account_id}"
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_campaigns(self, status=None):
        """Récupère les campagnes"""
        params = {
            'q': 'account',
            'search.account.values[0]': self.account_id
        }
        if status:
            params['search.status.values[0]'] = status

        response = self.client.get(
            f"{self.base_url}/adCampaigns",
            params=params
        )
        if response.status_code == 200:
            return response.json()['elements']
        raise Exception(f"Erreur lors de la récupération des campagnes: {response.text}")

    def create_campaign(self, name, objective, format='SPONSORED_CONTENT', status='PAUSED', daily_budget=None):
        """Crée une nouvelle campagne"""
        data = {
            'account': self.account_id,
            'name': name,
            'objective': objective,
            'format': format,
            'status': status
        }
        if daily_budget:
            data['dailyBudget'] = {
                'amount': str(daily_budget),
                'currencyCode': 'EUR'
            }

        response = self.client.post(
            f"{self.base_url}/adCampaigns",
            json=data
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création de la campagne: {response.text}")

    def get_creatives(self, campaign_id=None):
        """Récupère les créations publicitaires"""
        params = {'q': 'account', 'search.account.values[0]': self.account_id}
        if campaign_id:
            params['search.campaign.values[0]'] = campaign_id

        response = self.client.get(
            f"{self.base_url}/adCreatives",
            params=params
        )
        if response.status_code == 200:
            return response.json()['elements']
        raise Exception(f"Erreur lors de la récupération des créations: {response.text}")

    def create_creative(self, campaign_id, title, description, url, image_url):
        """Crée une nouvelle création publicitaire"""
        data = {
            'account': self.account_id,
            'campaign': campaign_id,
            'type': 'SPONSORED_CONTENT',
            'content': {
                'title': title,
                'description': description,
                'landingUrl': url,
                'imageUrl': image_url
            }
        }
        response = self.client.post(
            f"{self.base_url}/adCreatives",
            json=data
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la création de la publicité: {response.text}") 