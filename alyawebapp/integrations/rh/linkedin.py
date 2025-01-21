from ..base import BaseIntegration
import requests

class LinkedInIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['client_id', 'client_secret', 'access_token']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            session = requests.Session()
            session.headers.update({
                'Authorization': f"Bearer {self.config['access_token']}",
                'X-Restli-Protocol-Version': '2.0.0',
                'Content-Type': 'application/json'
            })
            self.base_url = 'https://api.linkedin.com/v2'
            return session
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation LinkedIn: {str(e)}")

    def test_connection(self):
        try:
            response = self.client.get(f"{self.base_url}/me")
            return response.status_code == 200
        except Exception:
            return False

    def get_profile(self):
        """Récupère le profil de l'utilisateur connecté"""
        response = self.client.get(f"{self.base_url}/me")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération du profil: {response.text}")

    def search_jobs(self, keywords=None, location=None, experience=None):
        """Recherche des offres d'emploi"""
        params = {}
        if keywords:
            params['keywords'] = keywords
        if location:
            params['location'] = location
        if experience:
            params['experience'] = experience

        response = self.client.get(f"{self.base_url}/jobs/search", params=params)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la recherche d'emplois: {response.text}")

    def post_job(self, job_data):
        """Publie une offre d'emploi"""
        response = self.client.post(f"{self.base_url}/jobs", json=job_data)
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de la publication de l'offre: {response.text}")

    def get_applicants(self, job_id):
        """Récupère les candidats pour une offre"""
        response = self.client.get(f"{self.base_url}/jobs/{job_id}/applicants")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Erreur lors de la récupération des candidats: {response.text}")

    def send_inmail(self, recipient_id, message_data):
        """Envoie un InMail à un utilisateur"""
        response = self.client.post(
            f"{self.base_url}/messages",
            json={
                "recipients": {
                    "values": [{"person": {"id": recipient_id}}]
                },
                "subject": message_data.get('subject', ''),
                "body": message_data.get('body', '')
            }
        )
        if response.status_code == 201:
            return response.json()
        raise Exception(f"Erreur lors de l'envoi du message: {response.text}") 