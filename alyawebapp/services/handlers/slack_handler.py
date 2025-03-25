import logging
import json
import re
import requests
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
            
            # Affichage de débogage pour examiner la structure de la configuration
            if self.slack_integration and hasattr(self.slack_integration, 'config'):
                logger.info(f"Configuration Slack trouvée: {self.slack_integration.config}")
                if isinstance(self.slack_integration.config, dict):
                    missing_fields = []
                    for key in ['client_id', 'client_secret', 'redirect_uri']:
                        if key not in self.slack_integration.config:
                            missing_fields.append(key)
                    if missing_fields:
                        logger.warning(f"Champs manquants dans la configuration Slack: {', '.join(missing_fields)}")
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.slack_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à Slack"""
        try:
            if not self.slack_integration:
                return "Vous n'avez pas installé l'intégration Slack. Veuillez configurer Slack dans vos intégrations avant de l'utiliser."
            
            # Vérifier si le token d'accès est présent
            if not isinstance(self.slack_integration.config, dict) or 'access_token' not in self.slack_integration.config or not self.slack_integration.config['access_token']:
                return "⚠️ Votre intégration Slack nécessite une réautorisation. Le token d'accès est manquant ou a expiré. Veuillez vous rendre dans les paramètres d'intégration pour reconfigurer Slack."
            
            # Machine à états pour l'envoi de messages
            if self.conversation_state == 'message_start':
                channel = text.strip()
                # Vérifier si le canal existe avant de continuer
                channel_exists = self._verify_channel_exists(channel)
                if not channel_exists:
                    self.conversation_state = None
                    return f"❌ Le canal #{channel} n'existe pas ou Alya n'y a pas accès. Veuillez vérifier le nom du canal et les permissions."
                
                self.message_info['channel'] = channel
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
            
            # Détection simple basée sur la présence de mots clés
            text_lower = text.lower()
            if "envoie un message sur slack dans le canal" in text_lower:
                # Trouver l'indice après cette phrase
                start_index = text_lower.find("envoie un message sur slack dans le canal") + len("envoie un message sur slack dans le canal")
                remaining_text = text[start_index:].strip()
                
                # Extraire le canal (avant ":")
                if ":" in remaining_text:
                    parts = remaining_text.split(":", 1)
                    channel = parts[0].strip().strip('#')
                    message_content = parts[1].strip()
                    
                    # Enlever les guillemets du message si présents
                    if (message_content.startswith("'") and message_content.endswith("'")) or \
                       (message_content.startswith('"') and message_content.endswith('"')):
                        message_content = message_content[1:-1]
                
                if not channel or not message_content:
                    return "Je n'ai pas pu identifier clairement le canal ou le message. Veuillez spécifier à la fois le canal et le message à envoyer."
                
                # Vérifier si le canal existe
                channel_exists = self._verify_channel_exists(channel)
                if not channel_exists:
                    return f"❌ Le canal #{channel} n'existe pas ou Alya n'y a pas accès. Veuillez vérifier le nom du canal."
                
                self.message_info = {
                    'channel': channel,
                    'message': message_content
                }
                
                try:
                    result = self._send_message(self.message_info)
                    return f"✅ Message envoyé avec succès dans le canal #{channel} !"
                except Exception as e:
                    logger.error(f"Erreur envoi message: {str(e)}")
                    if "channel_not_found" in str(e):
                        return f"❌ Le canal #{channel} n'a pas été trouvé. Veuillez vérifier le nom du canal."
                    elif "not_in_channel" in str(e):
                        return f"❌ Alya n'est pas membre du canal #{channel}. Veuillez l'ajouter au canal d'abord."
                    elif "invalid_auth" in str(e):
                        return "❌ Problème d'authentification avec Slack. Veuillez reconfigurer votre intégration Slack."
                    else:
                        return f"❌ Erreur lors de l'envoi du message: {str(e)}"
                else:
                    return "Format incorrect. Veuillez utiliser le format 'envoie un message sur Slack dans le canal #nom_du_canal : ton message'"
            
            # Intention d'envoyer un message
            if any(phrase in text_lower for phrase in ["envoyer message", "envoyer sur slack", "poster message", "écrire sur slack"]):
                # Vérifier si l'utilisateur a déjà mentionné un canal
                channel_match = re.search(r'(?:dans|sur|à)\s+(?:le\s+canal\s+|le\s+channel\s+)?[#]?([a-z0-9_-]+)', text_lower)
                message_content = None
                
                # Rechercher le message entre guillemets
                quote_matches = re.findall(r'[\'"](.+?)[\'"]', text)
                if quote_matches:
                    message_content = quote_matches[0]
                
                if channel_match and message_content:
                    # Canal et message spécifiés dans le texte
                    channel = channel_match.group(1)
                    
                    # Vérifier si le canal existe
                    channel_exists = self._verify_channel_exists(channel)
                    if not channel_exists:
                        return f"❌ Le canal #{channel} n'existe pas ou Alya n'y a pas accès. Veuillez vérifier le nom du canal."
                    
                    self.message_info = {
                        'channel': channel,
                        'message': message_content
                    }
                    
                    try:
                        result = self._send_message(self.message_info)
                        return f"✅ Message envoyé avec succès dans le canal #{channel} !"
                    except Exception as e:
                        logger.error(f"Erreur envoi message: {str(e)}")
                        if "channel_not_found" in str(e):
                            return f"❌ Le canal #{channel} n'a pas été trouvé. Veuillez vérifier le nom du canal."
                        else:
                            return f"❌ Erreur lors de l'envoi du message: {str(e)}"
                
                elif channel_match:
                    # Canal spécifié dans le message
                    channel = channel_match.group(1)
                    
                    # Vérifier si le canal existe
                    channel_exists = self._verify_channel_exists(channel)
                    if not channel_exists:
                        return f"❌ Le canal #{channel} n'existe pas ou Alya n'y a pas accès. Veuillez vérifier le nom du canal."
                    
                    self.message_info['channel'] = channel
                    
                    # Extraire le message s'il est présent
                    if message_content:
                        self.message_info['message'] = message_content
                        try:
                            result = self._send_message(self.message_info)
                            return f"✅ Message envoyé avec succès dans le canal #{channel} !"
                        except Exception as e:
                            logger.error(f"Erreur envoi message: {str(e)}")
                            return f"❌ Erreur lors de l'envoi du message: {str(e)}"
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
                    # Vérifier si l'utilisateur existe avant de chercher ses infos
                    user_id = user_match.group(1)
                    user_exists = self._verify_user_exists(user_id)
                    if not user_exists:
                        return f"❌ L'utilisateur @{user_id} n'a pas été trouvé sur votre espace de travail Slack."
                    
                    return self._get_user_info(user_id)
                else:
                    return "De quel utilisateur souhaitez-vous obtenir les informations ? Veuillez fournir son nom d'utilisateur Slack (sans le @)."
            
            # Intention de lister les canaux disponibles
            if any(phrase in text_lower for phrase in ["liste des canaux", "canaux disponibles", "channels disponibles"]):
                channels = self._get_available_channels()
                if not channels:
                    return "❌ Je n'ai pas pu récupérer la liste des canaux. Veuillez vérifier votre intégration Slack."
                
                if len(channels) == 0:
                    return "Aucun canal public accessible n'a été trouvé."
                
                response = "📢 Voici les canaux Slack disponibles :\n\n"
                for channel in channels[:15]:  # Limiter à 15 canaux pour éviter les réponses trop longues
                    response += f"• #{channel['name']} {' (privé)' if channel.get('is_private', False) else ''}\n"
                
                if len(channels) > 15:
                    response += f"\n... et {len(channels) - 15} autres canaux."
                    
                return response
            
            return "Je peux vous aider avec Slack. Voici ce que je peux faire :\n" + \
                   "- Envoyer un message dans un canal\n" + \
                   "- Consulter les réactions à un message\n" + \
                   "- Obtenir des informations sur un utilisateur\n" + \
                   "- Lister les canaux disponibles"

        except Exception as e:
            logger.error(f"Erreur Slack: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _verify_channel_exists(self, channel_name):
        """Vérifie si un canal existe et est accessible"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Formater le canal
            if not channel_name.startswith('#') and not channel_name.startswith('@'):
                channel_name = '#' + channel_name
                
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                logger.error("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                return False
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                logger.error("Configuration Slack incorrecte: access_token manquant")
                return False
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            # Récupérer la liste des canaux
            slack_handler = SlackAPI(minimal_config)
            channels = slack_handler.get_channels()
            
            # Vérifier si le canal existe dans la liste
            channel_exists = False
            for channel in channels:
                if ('#' + channel.get('name', '')) == channel_name or channel.get('name', '') == channel_name.lstrip('#'):
                    channel_exists = True
                    break
                    
            return channel_exists
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du canal: {str(e)}")
            return False
    
    def _verify_user_exists(self, user_id):
        """Vérifie si un utilisateur existe sur l'espace de travail Slack"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                logger.error("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                return False
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                logger.error("Configuration Slack incorrecte: access_token manquant")
                return False
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            slack_handler = SlackAPI(minimal_config)
            user_info = slack_handler.get_user_info(user_id)
            return bool(user_info) and 'id' in user_info
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'utilisateur: {str(e)}")
            return False
    
    def _get_available_channels(self):
        """Récupère la liste des canaux Slack disponibles"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                logger.error("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                return []
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                logger.error("Configuration Slack incorrecte: access_token manquant")
                return []
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            slack_handler = SlackAPI(minimal_config)
            return slack_handler.get_channels()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux: {str(e)}")
            return []
    
    def _send_message(self, message_info):
        """Envoie un message Slack en utilisant l'intégration existante"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['channel', 'message']
        missing_fields = [field for field in required_fields if field not in message_info or not message_info[field]]
        
        if missing_fields:
            error_messages = {
                'channel': "Le canal Slack n'a pas été spécifié. Veuillez indiquer dans quel canal envoyer le message.",
                'message': "Le contenu du message n'a pas été spécifié. Veuillez indiquer quel message envoyer."
            }
            error_msg = " ".join([error_messages[field] for field in missing_fields])
            raise ValueError(error_msg)
        
        # Formater le canal (ajouter # si nécessaire)
        channel = message_info['channel']
        if not channel.startswith('#') and not channel.startswith('@'):
            channel = '#' + channel
        
        # Utiliser l'implémentation existante
        try:
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                raise ValueError("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                raise ValueError("Configuration Slack incorrecte: access_token manquant. Veuillez reconfigurer votre intégration Slack.")
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            slack_handler = SlackAPI(minimal_config)
            result = slack_handler.send_message(
                channel=channel,
                message=message_info['message'],
                thread_ts=message_info.get('thread_ts')
            )
            
            # Vérifier les erreurs dans la réponse
            if not result.get('ok', False):
                error = result.get('error', 'unknown_error')
                if error == 'channel_not_found':
                    raise ValueError(f"Le canal {channel} n'a pas été trouvé. Veuillez vérifier le nom du canal.")
                elif error == 'not_in_channel':
                    raise ValueError(f"Alya n'est pas membre du canal {channel}. Veuillez l'ajouter au canal d'abord.")
                elif error == 'invalid_auth':
                    raise ValueError("Problème d'authentification avec Slack. Veuillez reconfigurer votre intégration Slack.")
                else:
                    raise ValueError(f"Erreur Slack: {error}")
                    
            return result
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erreur de connexion à Slack: {str(e)}")
    
    def _get_message_reactions(self, channel, message_ts):
        """Récupère les réactions à un message Slack"""
        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
        
        try:
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                logger.error("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                return "Désolé, votre intégration Slack n'est pas correctement configurée. Veuillez vérifier vos paramètres d'intégration."
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                logger.error("Configuration Slack incorrecte: access_token manquant")
                return "Désolé, votre intégration Slack n'a pas de token d'accès. Veuillez reconfigurer votre intégration."
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            # Utiliser l'implémentation existante
            slack_handler = SlackAPI(minimal_config)
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
            # Vérifier la configuration avant d'initialiser le handler
            config = self.slack_integration.config
            if not isinstance(config, dict):
                logger.error("Configuration Slack incorrecte: ce n'est pas un dictionnaire")
                return "Désolé, votre intégration Slack n'est pas correctement configurée. Veuillez vérifier vos paramètres d'intégration."
                
            # Pour les appels API, seul l'access_token est vraiment nécessaire
            if 'access_token' not in config or not config['access_token']:
                logger.error("Configuration Slack incorrecte: access_token manquant")
                return "Désolé, votre intégration Slack n'a pas de token d'accès. Veuillez reconfigurer votre intégration."
                
            # Assurons-nous que les champs requis par le constructeur existent
            minimal_config = {
                'client_id': config.get('client_id', 'default_id'),
                'client_secret': config.get('client_secret', 'default_secret'),
                'redirect_uri': config.get('redirect_uri', 'default_uri'),
                'access_token': config['access_token']
            }
                
            # Utiliser l'implémentation existante
            slack_handler = SlackAPI(minimal_config)
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