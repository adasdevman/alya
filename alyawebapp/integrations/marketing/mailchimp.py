from ..base import BaseIntegration
from mailchimp_marketing import Client

class MailchimpIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'server_prefix']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            client = Client()
            client.set_config({
                "api_key": self.config['api_key'],
                "server": self.config['server_prefix']
            })
            return client
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Mailchimp: {str(e)}")

    def test_connection(self):
        try:
            self.client.ping.get()
            return True
        except Exception:
            return False

    def get_lists(self):
        """Récupère toutes les listes"""
        return self.client.lists.get_all_lists()

    def add_subscriber(self, list_id, email, merge_fields=None):
        """Ajoute un abonné à une liste"""
        return self.client.lists.add_list_member(list_id, {
            "email_address": email,
            "status": "subscribed",
            "merge_fields": merge_fields or {}
        }) 