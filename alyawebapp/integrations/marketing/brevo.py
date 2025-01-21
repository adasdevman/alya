from ..base import BaseIntegration
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

class BrevoIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['api_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = self.config['api_key']
            return sib_api_v3_sdk.ApiClient(configuration)
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Brevo: {str(e)}")

    def test_connection(self):
        try:
            api_instance = sib_api_v3_sdk.AccountApi(self.client)
            api_instance.get_account()
            return True
        except ApiException:
            return False

    def get_contacts(self, limit=50, offset=0):
        """Récupère la liste des contacts"""
        api_instance = sib_api_v3_sdk.ContactsApi(self.client)
        return api_instance.get_contacts(limit=limit, offset=offset)

    def create_contact(self, email, attributes=None):
        """Crée un nouveau contact"""
        api_instance = sib_api_v3_sdk.ContactsApi(self.client)
        create_contact = sib_api_v3_sdk.CreateContact(
            email=email,
            attributes=attributes or {}
        )
        return api_instance.create_contact(create_contact)

    def send_transactional_email(self, template_id, to_email, params=None):
        """Envoie un email transactionnel"""
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(self.client)
        send_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            template_id=template_id,
            params=params or {}
        )
        return api_instance.send_transac_email(send_email) 