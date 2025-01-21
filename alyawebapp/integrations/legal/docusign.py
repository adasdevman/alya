from ..base import BaseIntegration
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition
import base64

class DocuSignIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['account_id', 'integration_key', 'user_id', 'private_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            api_client = ApiClient()
            api_client.set_base_path("https://demo.docusign.net/restapi")
            api_client.configure_jwt_authorization_flow(
                self.config['private_key'],
                self.config['integration_key'],
                self.config['user_id'],
                self.config['account_id']
            )
            return api_client
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation DocuSign: {str(e)}")

    def test_connection(self):
        try:
            envelopes_api = EnvelopesApi(self.client)
            envelopes_api.list_status_changes(self.config['account_id'])
            return True
        except Exception:
            return False

    def send_envelope(self, document_path, signer_email, signer_name):
        """Envoie un document pour signature"""
        with open(document_path, "rb") as file:
            content_bytes = file.read()
        
        base64_file_content = base64.b64encode(content_bytes).decode('ascii')

        envelope_definition = EnvelopeDefinition(
            email_subject="Document à signer",
            documents=[{
                "documentBase64": base64_file_content,
                "name": "Document",
                "fileExtension": "pdf",
                "documentId": "1"
            }],
            recipients={
                "signers": [{
                    "email": signer_email,
                    "name": signer_name,
                    "recipientId": "1",
                    "routingOrder": "1"
                }]
            },
            status="sent"
        )

        envelopes_api = EnvelopesApi(self.client)
        return envelopes_api.create_envelope(
            self.config['account_id'],
            envelope_definition=envelope_definition
        )

    def get_envelope_status(self, envelope_id):
        """Récupère le statut d'une enveloppe"""
        envelopes_api = EnvelopesApi(self.client)
        return envelopes_api.get_envelope(
            self.config['account_id'],
            envelope_id
        ) 