import logging
import json
import re
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class SlackHandler:
    """Gestionnaire pour les intégrations Slack"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.message_info = {}
        self.slack_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Slack si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='slack')
            self.slack_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.slack_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à Slack"""
        try:
            if not self.slack_integration:
                return "Vous n'avez pas installé cette intégration."
            
            # Machine à états pour l'envoi de messages
            if self.conversation_state == 'message_start':
                self.message_info['channel'] = text.strip()
                self.conversation_state = 'waiting_for_message'
                return "Quel message souhaitez-vous envoyer à ce canal ?"
                
            elif self.conversation_state == 'waiting_for_message':
                self.message_info['message'] = text.strip()
                
                # Envoyer le message
                try:
                    result = self._send_message(self.message_info)
                    self.conversation_state = None  # Réinitialiser l'état
                    self.message_info = {}
                    return "✅ Message envoyé avec succès sur Slack !"
                except Exception as e:
                    logger.error(f"Erreur envoi message: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return "❌ Erreur lors de l'envoi du message. Veuillez vérifier que votre intégration Slack est correctement configurée."
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention d'envoyer un message
            if any(phrase in text_lower for phrase in ["envoyer message", "envoyer sur slack", "poster message", "écrire sur slack"]):
                # Vérifier si l'utilisateur a déjà mentionné un canal
                channel_match = re.search(r'(?:dans|sur|à)\s+(?:le\s+canal\s+|le\s+channel\s+)?[#]?([a-z0-9_-]+)', text_lower)
                if channel_match:
                    # Canal spécifié dans le message
                    channel = channel_match.group(1)
                    self.message_info['channel'] = channel
                    
                    # Extraire le message s'il est entre guillemets
                    message_match = re.search(r'"([^"]+)"', text)
                    if message_match:
                        self.message_info['message'] = message_match.group(1)
                        return self._send_message(self.message_info)
                    else:
                        self.conversation_state = 'waiting_for_message'
                        return f"Quel message souhaitez-vous envoyer au canal #{channel} ?"
                else:
                    self.conversation_state = 'message_start'
                    return "Dans quel canal Slack souhaitez-vous envoyer un message ? (sans le #)"
            
            # Intention de consulter les réactions
            if any(phrase in text_lower for phrase in ["réactions message", "qui a réagi", "réponses au message"]):
                return "Pour consulter les réactions à un message, j'ai besoin de l'ID du canal et du timestamp du message. Vous pouvez les trouver en cliquant sur 'Plus d'actions' puis 'Copier le lien' sur un message Slack."
            
            # Intention de consulter les informations d'un utilisateur
            if any(phrase in text_lower for phrase in ["infos utilisateur", "info membre", "profil slack"]):
                user_match = re.search(r'(?:de|pour|sur)\s+@?([a-z0-9._-]+)', text_lower)
                if user_match:
                    return self._get_user_info(user_match.group(1))
                else:
                    return "De quel utilisateur souhaitez-vous obtenir les informations ? Veuillez fournir son nom d'utilisateur Slack (sans le @)."
            
            return "Je peux vous aider avec Slack. Voici ce que je peux faire :\n" + \
                   "- Envoyer un message dans un canal\n" + \
                   "- Consulter les réactions à un message\n" + \
                   "- Obtenir des informations sur un utilisateur"

        except Exception as e:
            logger.error(f"Erreur Slack: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _send_message(self, message_info):
        """Envoie un message Slack en utilisant l'intégration existante"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['channel', 'message']
        missing_fields = [field for field in required_fields if field not in message_info]
        if missing_fields:
            raise ValueError(f"Informations incomplètes. Champs manquants: {', '.join(missing_fields)}")
        
        # Utiliser l'implémentation existante
        slack_handler = SlackAPI(self.slack_integration.config)
        return slack_handler.send_message(
            channel=message_info['channel'],
            message=message_info['message'],
            thread_ts=message_info.get('thread_ts')
        )
    
    def _get_message_reactions(self, channel, message_ts):
        """Récupère les réactions à un message Slack"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Utiliser l'implémentation existante
            slack_handler = SlackAPI(self.slack_integration.config)
            reactions = slack_handler.get_message_reactions(channel, message_ts)
            
            if not reactions:
                return "Aucune réaction trouvée pour ce message."
            
            # Formater les réactions pour l'affichage
            response = "👀 Réactions au message :\n\n"
            for reaction in reactions:
                count = reaction.get('count', 0)
                users = reaction.get('users', [])
                response += f"• :{reaction.get('name', 'emoji')}: : {count} personne(s)\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réactions: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer les réactions. Veuillez vérifier que votre intégration Slack est correctement configurée."
    
    def _get_user_info(self, user_id):
        """Récupère les informations d'un utilisateur Slack"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Utiliser l'implémentation existante
            slack_handler = SlackAPI(self.slack_integration.config)
            user_info = slack_handler.get_user_info(user_id)
            
            if not user_info:
                return f"Aucune information trouvée pour l'utilisateur {user_id}."
            
            # Formater les informations pour l'affichage
            response = f"👤 Informations sur l'utilisateur {user_id} :\n\n"
            
            if user_info.get('real_name'):
                response += f"• Nom : {user_info['real_name']}\n"
            
            if user_info.get('profile'):
                profile = user_info['profile']
                if profile.get('email'):
                    response += f"• Email : {profile['email']}\n"
                
                if profile.get('title'):
                    response += f"• Titre : {profile['title']}\n"
                
                if profile.get('phone'):
                    response += f"• Téléphone : {profile['phone']}\n"
            
            if user_info.get('is_admin'):
                response += "• Rôle : Administrateur\n"
            elif user_info.get('is_owner'):
                response += "• Rôle : Propriétaire\n"
            
            if user_info.get('tz'):
                response += f"• Fuseau horaire : {user_info['tz']}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations utilisateur: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer les informations de l'utilisateur. Veuillez vérifier que votre intégration Slack est correctement configurée." 