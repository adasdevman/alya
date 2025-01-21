from ..base import BaseIntegration
from zenpy import Zenpy

class ZendeskIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['email', 'token', 'subdomain']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            creds = {
                'email': self.config['email'],
                'token': self.config['token'],
                'subdomain': self.config['subdomain']
            }
            return Zenpy(**creds)
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Zendesk: {str(e)}")

    def test_connection(self):
        try:
            self.client.tickets.count()
            return True
        except Exception:
            return False

    def get_tickets(self, status="open"):
        """Récupère les tickets selon leur statut"""
        return self.client.tickets(status=status)

    def create_ticket(self, subject, description, priority="normal"):
        """Crée un nouveau ticket"""
        return self.client.tickets.create({
            'subject': subject,
            'description': description,
            'priority': priority
        }) 