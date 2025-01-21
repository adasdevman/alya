from ..base import BaseIntegration
import xmlrpc.client

class OdooIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['url', 'db', 'username', 'api_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            uid = common.authenticate(
                self.config['db'],
                self.config['username'],
                self.config['api_key'],
                {}
            )
            self.uid = uid
            return xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Odoo: {str(e)}")

    def test_connection(self):
        try:
            self.client.execute_kw(
                self.config['db'],
                self.uid,
                self.config['api_key'],
                'res.partner',
                'search_count',
                [[]]
            )
            return True
        except Exception:
            return False

    def get_products(self):
        """Récupère les produits"""
        return self.client.execute_kw(
            self.config['db'],
            self.uid,
            self.config['api_key'],
            'product.product',
            'search_read',
            [[]],
            {'fields': ['name', 'list_price', 'default_code']}
        )

    def create_sale_order(self, partner_id, order_lines):
        """Crée un bon de commande"""
        return self.client.execute_kw(
            self.config['db'],
            self.uid,
            self.config['api_key'],
            'sale.order',
            'create',
            [{
                'partner_id': partner_id,
                'order_line': [(0, 0, line) for line in order_lines]
            }]
        ) 