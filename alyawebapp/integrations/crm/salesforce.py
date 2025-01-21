from ..base import BaseIntegration
from simple_salesforce import Salesforce

class SalesforceIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['username', 'password', 'security_token', 'domain']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            return Salesforce(
                username=self.config['username'],
                password=self.config['password'],
                security_token=self.config['security_token'],
                domain=self.config['domain']
            )
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Salesforce: {str(e)}")

    def test_connection(self):
        try:
            self.client.query("SELECT Id FROM Account LIMIT 1")
            return True
        except Exception:
            return False

    def get_opportunities(self):
        """Récupère les opportunités"""
        return self.client.query("SELECT Id, Name, StageName, Amount FROM Opportunity") 