from ..base import BaseIntegration
from amplitude import Amplitude

class AmplitudeIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'project_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            return Amplitude(self.config['api_key'])
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Amplitude: {str(e)}")

    def test_connection(self):
        try:
            self.client.track('test_event', user_id='test')
            return True
        except Exception:
            return False

    def get_events(self, start_date, end_date):
        """Récupère les événements pour une période donnée"""
        return self.client.get_events(start_date, end_date) 