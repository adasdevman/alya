from ..base import BaseIntegration
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class GmailHandler(BaseIntegration):
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    API_VERSION = 'v1'
    API_SERVICE_NAME = 'gmail'

    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        self.credentials = self._build_credentials()
        self.service = self._build_service()

    def _build_credentials(self) -> Credentials:
        """Construit les credentials Google"""
        return Credentials(
            token=self.config.get('access_token'),
            refresh_token=self.config.get('refresh_token'),
            token_uri=self.config.get('token_uri'),
            client_id=self.config.get('client_id'),
            client_secret=self.config.get('client_secret'),
            scopes=self.SCOPES
        )

    def _build_service(self):
        """Construit le service Gmail"""
        return build(self.API_SERVICE_NAME, self.API_VERSION, credentials=self.credentials)

    def send_email(self, to: str, subject: str, body: str, html: bool = True) -> Dict[str, Any]:
        """Envoie un email via Gmail"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject

            # Créer les versions texte et HTML du message
            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))

            # Encoder le message en base64URL
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Envoyer l'email
            return self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
            raise

    def get_email_thread(self, thread_id: str) -> Dict[str, Any]:
        """Récupère un fil de discussion complet"""
        try:
            return self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du fil de discussion: {str(e)}")
            raise

    def create_draft(self, to: str, subject: str, body: str, html: bool = True) -> Dict[str, Any]:
        """Crée un brouillon d'email"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject

            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            return self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': raw
                    }
                }
            ).execute()

        except Exception as e:
            logger.error(f"Erreur lors de la création du brouillon: {str(e)}")
            raise

    def schedule_email(self, to: str, subject: str, body: str, send_at: str, html: bool = True) -> Dict[str, Any]:
        """Programme l'envoi d'un email pour plus tard"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject
            message['x-gm-schedule-time'] = send_at  # Format: RFC3339 timestamp

            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            return self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw,
                    'labelIds': ['SCHEDULED']
                }
            ).execute()

        except Exception as e:
            logger.error(f"Erreur lors de la programmation de l'email: {str(e)}")
            raise

    def get_email_history(self, email_address: str) -> List[Dict[str, Any]]:
        """Récupère l'historique des échanges avec une adresse email"""
        try:
            query = f"to:{email_address} OR from:{email_address}"
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()

            messages = []
            if 'messages' in results:
                for msg in results['messages']:
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
            raise 