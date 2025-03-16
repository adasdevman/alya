import logging
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# Configurer OpenAI
openai.api_key = settings.OPENAI_API_KEY

class GmailManager:
    @classmethod
    def send_email(cls, user_integration, to_email, subject, body, draft=False):
        """Envoie ou crée un brouillon d'email"""
        try:
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/gmail.compose']
            )
            
            service = build('gmail', 'v1', credentials=creds)
            
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            if draft:
                result = service.users().drafts().create(
                    userId='me',
                    body={'message': {'raw': raw_message}}
                ).execute()
            else:
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur envoi email Gmail: {str(e)}")
            raise

    @classmethod
    def generate_email_content(cls, user_integration, context, tone="professional"):
        """Génère le contenu d'un email avec l'IA"""
        try:
            # Utiliser l'API OpenAI pour générer le contenu
            prompt = f"""Génère un email {tone} pour {context}.
            L'email doit être clair, concis et professionnel."""
            
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un expert en rédaction d'emails professionnels."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erreur génération email: {str(e)}")
            raise

    @classmethod
    def schedule_email(cls, user_integration, to_email, subject, body, send_time):
        """Programme l'envoi d'un email"""
        try:
            # Créer d'abord un brouillon
            draft = cls.send_email(
                user_integration,
                to_email,
                subject,
                body,
                draft=True
            )
            
            # Programmer l'envoi
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/gmail.compose']
            )
            
            service = build('gmail', 'v1', credentials=creds)
            
            # Créer une tâche planifiée
            scheduled_send = {
                'draft_id': draft['id'],
                'send_time': send_time.isoformat()
            }
            
            # Stocker la tâche planifiée (à implémenter selon votre système)
            cls._store_scheduled_email(user_integration, scheduled_send)
            
            return scheduled_send
            
        except Exception as e:
            logger.error(f"Erreur programmation email: {str(e)}")
            raise

    @classmethod
    def get_email_thread(cls, user_integration, thread_id):
        """Récupère tous les messages d'un thread"""
        try:
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/gmail.readonly']
            )
            
            service = build('gmail', 'v1', credentials=creds)
            
            thread = service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread['messages']:
                headers = {
                    header['name']: header['value']
                    for header in msg['payload']['headers']
                }
                
                messages.append({
                    'from': headers.get('From'),
                    'to': headers.get('To'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date'),
                    'body': cls._get_message_body(msg)
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Erreur récupération thread Gmail: {str(e)}")
            raise

    @classmethod
    def _get_message_body(cls, message):
        """Extrait le corps du message"""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    return base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8')
        elif 'body' in message['payload']:
            return base64.urlsafe_b64decode(
                message['payload']['body']['data']
            ).decode('utf-8')
        return "" 