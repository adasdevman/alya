from ..base import BaseIntegration
import requests

class BufferIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['access_token']
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
            self.base_url = 'https://api.buffer.com/1'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Buffer: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/user.json")
            return response.status_code == 200
        except Exception:
            return False

    def get_profiles(self):
        """Récupère les profils sociaux"""
        response = self.client.get(f"{self.base_url}/profiles.json")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des profils: {response.text}")

    def create_update(self, profile_ids, text, media=None, scheduled_at=None):
        """Crée une nouvelle publication"""
        data = {
            'text': text,
            'profile_ids[]': profile_ids
        }
        if media:
            data['media'] = media
        if scheduled_at:
            data['scheduled_at'] = scheduled_at

        response = self.client.post(f"{self.base_url}/updates/create.json", json=data)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la création de la publication: {response.text}") 