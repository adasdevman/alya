from ..base import BaseIntegration
import stripe

class StripeIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key', 'webhook_secret']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            stripe.api_key = self.config['api_key']
            return stripe
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Stripe: {str(e)}")

    def test_connection(self):
        try:
            stripe.Account.retrieve()
            return True
        except Exception:
            return False

    def get_payments(self, limit=10):
        """Récupère les derniers paiements"""
        return stripe.PaymentIntent.list(limit=limit)

    def create_payment(self, amount, currency="eur", description=None):
        """Crée un nouveau paiement"""
        return stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            description=description
        ) 