import logging
import json
import re
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class GmailHandler:
    """Gestionnaire pour les intégrations Gmail"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.email_info = {}
        self.gmail_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Gmail si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='gmail')
            self.gmail_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.gmail_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à Gmail"""
        try:
            if not self.gmail_integration:
                return "Vous n'avez pas installé cette intégration."
            
            # Machine à états pour la composition d'emails
            if self.conversation_state == 'email_composition_start':
                self.email_info['to'] = text.strip()
                self.conversation_state = 'waiting_for_subject'
                return "Quel est le sujet de l'email ?"
                
            elif self.conversation_state == 'waiting_for_subject':
                self.email_info['subject'] = text.strip()
                self.conversation_state = 'waiting_for_body'
                return "Veuillez saisir le contenu de l'email. Une fois terminé, écrivez '/envoyer' sur une nouvelle ligne."
                
            elif self.conversation_state == 'waiting_for_body':
                if text.strip() == '/envoyer':
                    # L'utilisateur souhaite envoyer l'email
                    try:
                        result = self._send_email(self.email_info)
                        self.conversation_state = None  # Réinitialiser l'état
                        self.email_info = {}
                        return "✅ Email envoyé avec succès !"
                    except Exception as e:
                        logger.error(f"Erreur envoi email: {str(e)}")
                        self.conversation_state = None  # Réinitialiser l'état
                        return "❌ Erreur lors de l'envoi de l'email. Veuillez vérifier que votre intégration Gmail est correctement configurée."
                else:
                    # L'utilisateur continue de composer le corps de l'email
                    if 'body' not in self.email_info:
                        self.email_info['body'] = text
                    else:
                        self.email_info['body'] += "\n" + text
                    return "Continuez à écrire le contenu de l'email. Écrivez '/envoyer' sur une nouvelle ligne quand vous avez terminé."
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention d'envoyer un email
            if any(phrase in text_lower for phrase in ["envoyer un email", "envoyer un mail", "écrire un email", "composer un email"]):
                # Extraire le destinataire s'il est mentionné
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    self.email_info['to'] = email_match.group(0)
                    self.conversation_state = 'waiting_for_subject'
                    return f"Je vais vous aider à envoyer un email à {self.email_info['to']}. Quel est le sujet de l'email ?"
                else:
                    self.conversation_state = 'email_composition_start'
                    return "Je vais vous aider à envoyer un email. À quelle adresse souhaitez-vous l'envoyer ?"
            
            # Intention de voir l'historique des emails
            if any(phrase in text_lower for phrase in ["historique des emails", "historique des mails", "emails récents", "derniers emails"]):
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    return self._get_email_history(email_match.group(0))
                else:
                    return "Avec quelle adresse email souhaitez-vous voir l'historique des échanges ?"
            
            # Intention de créer un brouillon
            if any(phrase in text_lower for phrase in ["créer un brouillon", "sauvegarder un brouillon", "nouveau brouillon"]):
                self.conversation_state = 'email_composition_start'
                return "Je vais vous aider à créer un brouillon d'email. À quelle adresse souhaitez-vous l'envoyer ?"
            
            return "Je peux vous aider avec Gmail. Voici ce que je peux faire :\n" + \
                   "- Envoyer un email (dites 'envoyer un email à [adresse]')\n" + \
                   "- Créer un brouillon d'email\n" + \
                   "- Consulter l'historique des échanges avec un contact"

        except Exception as e:
            logger.error(f"Erreur Gmail: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _get_email_history(self, email_address):
        """Récupère l'historique des échanges avec une adresse email"""
        from alyawebapp.integrations.gmail.handler import GmailHandler as GmailAPI
        
        try:
            # Utiliser l'implémentation existante
            gmail_handler = GmailAPI(self.gmail_integration.config)
            email_history = gmail_handler.get_email_history(email_address)
            
            if not email_history:
                return f"Aucun échange récent trouvé avec {email_address}."
            
            # Formater la réponse
            response = f"📧 Voici les derniers échanges avec {email_address}:\n\n"
            for i, email in enumerate(email_history[:5], 1):  # Limiter à 5 emails
                subject = next((h['value'] for h in email.get('payload', {}).get('headers', []) if h['name'].lower() == 'subject'), "Sans objet")
                date = next((h['value'] for h in email.get('payload', {}).get('headers', []) if h['name'].lower() == 'date'), "Date inconnue")
                response += f"• Email {i}: \"{subject}\" - {date}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique des emails: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer l'historique des emails. Veuillez vérifier que votre intégration Gmail est correctement configurée."
    
    def _send_email(self, email_info):
        """Envoie un email en utilisant l'intégration Gmail existante"""
        from alyawebapp.integrations.gmail.handler import GmailHandler as GmailAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['to', 'subject', 'body']
        missing_fields = [field for field in required_fields if field not in email_info]
        if missing_fields:
            raise ValueError(f"Informations incomplètes. Champs manquants: {', '.join(missing_fields)}")
        
        # Utiliser l'implémentation existante
        gmail_handler = GmailAPI(self.gmail_integration.config)
        return gmail_handler.send_email(
            to=email_info['to'],
            subject=email_info['subject'],
            body=email_info['body'],
            html=False  # Par défaut, envoyer en texte brut
        ) 