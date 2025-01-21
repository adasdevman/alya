from ..base import BaseIntegration
from mixpanel import Mixpanel
from datetime import datetime, timedelta

class MixpanelIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'api_url']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            return Mixpanel(self.config['api_key'])
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation du client Mixpanel: {str(e)}")

    def test_connection(self):
        try:
            self.get_events_last_7_days()
            return True
        except Exception as e:
            return False

    def get_events_last_7_days(self):
        """Récupère les événements des 7 derniers jours"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        return self.client.request(
            'events',
            {
                'from_date': start_date.strftime("%Y-%m-%d"),
                'to_date': end_date.strftime("%Y-%m-%d"),
                'event': ['$pageview']
            }
        ) 