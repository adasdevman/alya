from ..base import BaseIntegration
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from datetime import datetime, timedelta

class GoogleAnalyticsIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'api_url']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            credentials = Credentials(self.config['api_key'])
            return BetaAnalyticsDataClient(credentials=credentials)
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation du client GA: {str(e)}")

    def test_connection(self):
        try:
            self.get_visitors_last_7_days()
            return True
        except Exception as e:
            return False

    def get_visitors_last_7_days(self):
        """Récupère le nombre de visiteurs des 7 derniers jours"""
        property_id = self.config.get('property_id')
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[{
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }],
            metrics=[{"name": "activeUsers"}],
            dimensions=[{"name": "date"}]
        )

        response = self.client.run_report(request)
        return self._format_visitors_data(response)

    def _format_visitors_data(self, response):
        """Formate les données de visiteurs"""
        visitors_data = []
        for row in response.rows:
            visitors_data.append({
                'date': row.dimension_values[0].value,
                'visitors': row.metric_values[0].value
            })
        return visitors_data 