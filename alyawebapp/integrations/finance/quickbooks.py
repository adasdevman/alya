from ..base import BaseIntegration
from quickbooks.client import QuickBooks
from quickbooks.objects.customer import Customer

class QuickBooksIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['client_id', 'client_secret', 'refresh_token', 'company_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            return QuickBooks(
                client_id=self.config['client_id'],
                client_secret=self.config['client_secret'],
                refresh_token=self.config['refresh_token'],
                company_id=self.config['company_id']
            )
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation QuickBooks: {str(e)}")

    def test_connection(self):
        try:
            Customer.all(qb=self.client)
            return True
        except Exception:
            return False

    def get_customers(self):
        """Récupère tous les clients"""
        return Customer.all(qb=self.client)

    def create_invoice(self, customer_id, items):
        """Crée une nouvelle facture"""
        from quickbooks.objects.invoice import Invoice
        from quickbooks.objects.item import Item

        invoice = Invoice()
        invoice.CustomerRef = customer_id
        
        for item in items:
            line = invoice.Line()
            line.Amount = item['amount']
            line.Description = item['description']
            line.ItemRef = Item.get(item['item_id'], qb=self.client).Id
            invoice.Line.append(line)
        
        return invoice.save(qb=self.client) 