import logging
import json
import re
import requests
from datetime import datetime
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class MailChimpHandler:
    """Gestionnaire pour les intégrations MailChimp"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.current_operation = None
        self.mailchimp_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration MailChimp si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='mailchimp')
            self.mailchimp_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
            
            # Vérification de la configuration
            if self.mailchimp_integration and hasattr(self.mailchimp_integration, 'config'):
                logger.info(f"Configuration MailChimp trouvée: {self.mailchimp_integration.config}")
                if isinstance(self.mailchimp_integration.config, dict):
                    missing_fields = []
                    for key in ['api_key', 'data_center']:
                        if key not in self.mailchimp_integration.config:
                            missing_fields.append(key)
                    if missing_fields:
                        logger.warning(f"Champs manquants dans la configuration MailChimp: {', '.join(missing_fields)}")
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.mailchimp_integration = None
            logger.warning("Intégration MailChimp non trouvée ou non activée pour cet utilisateur")
    
    def handle_request(self, text):
        """Gère les requêtes liées à MailChimp"""
        try:
            if not self.mailchimp_integration:
                return "Vous n'avez pas installé l'intégration MailChimp. Veuillez configurer MailChimp dans vos intégrations avant de l'utiliser."
            
            # Vérifier si la clé API est présente
            if not isinstance(self.mailchimp_integration.config, dict) or 'api_key' not in self.mailchimp_integration.config:
                return "⚠️ Votre intégration MailChimp n'est pas correctement configurée. La clé API est manquante. Veuillez vous rendre dans les paramètres d'intégration pour reconfigurer MailChimp."
            
            # Machine à états pour les opérations en plusieurs étapes
            if self.conversation_state == 'waiting_for_campaign_name':
                campaign_name = text.strip()
                self.conversation_state = 'waiting_for_campaign_subject'
                self.current_operation['name'] = campaign_name
                return "Quel sera le sujet de cette campagne email ?"
                
            elif self.conversation_state == 'waiting_for_campaign_subject':
                campaign_subject = text.strip()
                self.conversation_state = 'waiting_for_campaign_content'
                self.current_operation['subject'] = campaign_subject
                return "Quel sera le contenu de cette campagne ? Vous pouvez me donner un texte ou HTML."
                
            elif self.conversation_state == 'waiting_for_campaign_content':
                campaign_content = text.strip()
                self.current_operation['content'] = campaign_content
                
                # Créer et préparer la campagne
                try:
                    result = self._create_campaign(self.current_operation)
                    campaign_id = result.get('id')
                    self.conversation_state = None  # Réinitialiser l'état
                    self.current_operation = None
                    
                    if not campaign_id:
                        return "❌ Erreur lors de la création de la campagne. Veuillez vérifier les informations et réessayer."
                    
                    return f"✅ Campagne '{self.current_operation['name']}' créée avec succès ! Vous pouvez maintenant la programmer ou l'envoyer depuis votre compte MailChimp."
                except Exception as e:
                    logger.error(f"Erreur création campagne: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    self.current_operation = None
                    return f"❌ Erreur lors de la création de la campagne: {str(e)}"
            
            # Détecter l'intention de l'utilisateur
            text_lower = text.lower()
            
            # Intention: Créer une campagne
            if any(phrase in text_lower for phrase in ["créer une campagne", "nouvelle campagne", "créer campagne"]):
                # Vérifier s'il existe au moins une liste d'abonnés
                lists = self._get_lists()
                
                if not lists or len(lists) == 0:
                    return "❌ Vous devez d'abord créer au moins une liste d'abonnés dans MailChimp avant de pouvoir créer une campagne."
                
                # Utiliser la première liste par défaut
                default_list = lists[0]
                
                self.conversation_state = 'waiting_for_campaign_name'
                self.current_operation = {
                    'list_id': default_list['id']
                }
                
                return f"Je vais vous aider à créer une nouvelle campagne email pour la liste '{default_list['name']}'. Quel nom souhaitez-vous donner à cette campagne ?"
            
            # Intention: Obtenir des statistiques de campagne
            if any(phrase in text_lower for phrase in ["statistiques campagne", "stats campagne", "résultats campagne"]):
                campaign_name_match = re.search(r'(?:pour|de|sur)\s+[\'"](.+?)[\'"]', text)
                
                if not campaign_name_match:
                    # Récupérer les campagnes récentes
                    campaigns = self._get_campaigns(count=5)
                    
                    if not campaigns or len(campaigns) == 0:
                        return "Aucune campagne n'a été trouvée dans votre compte MailChimp."
                    
                    campaign_list = "Voici vos campagnes récentes :\n\n"
                    for idx, campaign in enumerate(campaigns, 1):
                        campaign_list += f"{idx}. {campaign['settings']['title']} ({campaign['status']})\n"
                    
                    return f"{campaign_list}\nPour quelle campagne souhaitez-vous obtenir les statistiques ? Demandez par exemple 'Donne-moi les statistiques pour \"Nom de la campagne\"'"
                
                campaign_name = campaign_name_match.group(1)
                campaigns = self._get_campaigns()
                
                # Rechercher la campagne par nom
                matching_campaign = None
                for campaign in campaigns:
                    if campaign['settings']['title'].lower() == campaign_name.lower():
                        matching_campaign = campaign
                        break
                
                if not matching_campaign:
                    return f"❌ Je n'ai pas trouvé de campagne nommée '{campaign_name}'. Veuillez vérifier le nom de la campagne."
                
                # Récupérer les statistiques
                report = self._get_campaign_report(matching_campaign['id'])
                
                if not report:
                    return f"❌ Impossible de récupérer les statistiques pour la campagne '{campaign_name}'."
                
                status = matching_campaign['status']
                status_french = {
                    'save': 'Sauvegardée',
                    'paused': 'En pause',
                    'schedule': 'Programmée',
                    'sending': 'En cours d\'envoi',
                    'sent': 'Envoyée'
                }.get(status, status)
                
                stats = f"📊 Statistiques pour la campagne '{campaign_name}' ({status_french}):\n\n"
                
                if status in ['sent', 'sending']:
                    stats += f"• Taux d'ouverture: {report.get('opens', {}).get('open_rate', 0) * 100:.1f}%\n"
                    stats += f"• Taux de clics: {report.get('clicks', {}).get('click_rate', 0) * 100:.1f}%\n"
                    stats += f"• Emails envoyés: {report.get('emails_sent', 0)}\n"
                    stats += f"• Emails ouverts: {report.get('opens', {}).get('opens_total', 0)}\n"
                    stats += f"• Clics: {report.get('clicks', {}).get('clicks_total', 0)}\n"
                    stats += f"• Désabonnements: {report.get('unsubscribed', 0)}\n"
                else:
                    stats += "Cette campagne n'a pas encore été envoyée. Les statistiques ne sont pas disponibles."
                
                return stats
            
            # Intention: Obtenir des infos sur les listes d'abonnés
            if any(phrase in text_lower for phrase in ["info liste", "statistiques liste", "abonnés liste", "nombre d'abonnés"]):
                # Récupérer les listes
                lists = self._get_lists()
                
                if not lists or len(lists) == 0:
                    return "Aucune liste d'abonnés n'a été trouvée dans votre compte MailChimp."
                
                list_info = "📋 Informations sur vos listes d'abonnés :\n\n"
                
                for idx, list_item in enumerate(lists, 1):
                    list_info += f"{idx}. {list_item['name']}:\n"
                    list_info += f"   • Abonnés: {list_item['stats']['member_count']}\n"
                    list_info += f"   • Taux d'ouverture moyen: {list_item['stats']['open_rate'] * 100:.1f}%\n"
                    list_info += f"   • Taux de clics moyen: {list_item['stats']['click_rate'] * 100:.1f}%\n"
                    list_info += f"   • Désabonnements: {list_item['stats']['unsubscribe_count']}\n\n"
                
                return list_info
            
            # Intention: Ajouter un abonné
            subscriber_match = re.search(r'(?:ajouter|inscrire)\s+(?:l\'email|l\'adresse|la personne)?\s*(?:de)?\s*(?:"([^"]*)"|\'([^\']*)\')?\s*(?:à|dans|sur)\s+(?:la liste)?\s*(?:"([^"]*)"|\'([^\']*)\')?', text_lower)
            
            if subscriber_match or any(phrase in text_lower for phrase in ["ajouter abonné", "inscrire email", "ajouter contact"]):
                email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)
                
                if not email_match:
                    return "Pour ajouter un abonné, j'ai besoin d'une adresse email valide. Veuillez la fournir dans votre demande."
                
                email = email_match.group(1)
                
                # Chercher le prénom et le nom
                name_match = re.search(r'nom\s+(?:est|:)?\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)', text)
                firstname_match = re.search(r'prénom\s+(?:est|:)?\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)', text)
                
                firstname = firstname_match.group(1) if firstname_match else ""
                lastname = name_match.group(1) if name_match else ""
                
                # Si on a un nom complet, essayer de le diviser
                if name_match and not firstname_match:
                    name_parts = name_match.group(1).strip().split(' ', 1)
                    if len(name_parts) > 1:
                        firstname = name_parts[0]
                        lastname = name_parts[1]
                    else:
                        firstname = name_parts[0]
                
                # Récupérer les listes
                lists = self._get_lists()
                
                if not lists or len(lists) == 0:
                    return "❌ Vous n'avez aucune liste d'abonnés dans votre compte MailChimp. Veuillez d'abord créer une liste."
                
                # Chercher une liste spécifique mentionnée
                list_name_match = re.search(r'(?:à|dans|sur)\s+(?:la liste)?\s*[\'"](.+?)[\'"]', text_lower)
                target_list = None
                
                if list_name_match:
                    requested_list_name = list_name_match.group(1).lower()
                    for list_item in lists:
                        if list_item['name'].lower() == requested_list_name:
                            target_list = list_item
                            break
                    
                    if not target_list:
                        list_names = [f"'{list_item['name']}'" for list_item in lists]
                        return f"❌ Je n'ai pas trouvé de liste nommée '{requested_list_name}'. Les listes disponibles sont: {', '.join(list_names)}"
                else:
                    # Utiliser la première liste par défaut
                    target_list = lists[0]
                
                # Ajouter l'abonné
                try:
                    result = self._add_subscriber(target_list['id'], email, firstname, lastname)
                    
                    if result.get('id'):
                        return f"✅ L'adresse {email} a été ajoutée avec succès à la liste '{target_list['name']}'."
                    else:
                        return f"❌ Une erreur s'est produite lors de l'ajout de l'abonné à la liste '{target_list['name']}'."
                except Exception as e:
                    error_msg = str(e)
                    if "Member Exists" in error_msg:
                        return f"ℹ️ L'adresse {email} est déjà inscrite à la liste '{target_list['name']}'."
                    else:
                        logger.error(f"Erreur ajout abonné: {error_msg}")
                        return f"❌ Erreur lors de l'ajout de l'abonné: {error_msg}"
            
            # Message d'aide par défaut
            return "Je peux vous aider avec MailChimp. Voici ce que je peux faire :\n\n" + \
                   "• Créer une nouvelle campagne email\n" + \
                   "• Afficher les statistiques d'une campagne\n" + \
                   "• Afficher les informations sur vos listes d'abonnés\n" + \
                   "• Ajouter un nouvel abonné à une liste\n\n" + \
                   "Que souhaitez-vous faire ?"

        except Exception as e:
            logger.error(f"Erreur MailChimp: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _get_api_client(self):
        """Récupère le client API pour MailChimp"""
        if not self.mailchimp_integration or not isinstance(self.mailchimp_integration.config, dict):
            raise ValueError("Configuration MailChimp manquante ou incorrecte")
        
        config = self.mailchimp_integration.config
        api_key = config.get('api_key')
        data_center = config.get('data_center')
        
        if not api_key or not data_center:
            raise ValueError("Clé API ou data center manquant dans la configuration MailChimp")
        
        headers = {
            'Authorization': f'apikey {api_key}',
            'Content-Type': 'application/json'
        }
        
        base_url = f"https://{data_center}.api.mailchimp.com/3.0"
        
        return headers, base_url
    
    def _get_lists(self):
        """Récupère les listes d'abonnés de MailChimp"""
        headers, base_url = self._get_api_client()
        
        try:
            response = requests.get(f"{base_url}/lists", headers=headers)
            response.raise_for_status()
            return response.json().get('lists', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des listes MailChimp: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            return []
    
    def _get_campaigns(self, count=None):
        """Récupère les campagnes de MailChimp"""
        headers, base_url = self._get_api_client()
        
        params = {}
        if count:
            params['count'] = count
        
        try:
            response = requests.get(f"{base_url}/campaigns", headers=headers, params=params)
            response.raise_for_status()
            return response.json().get('campaigns', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des campagnes MailChimp: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            return []
    
    def _get_campaign_report(self, campaign_id):
        """Récupère le rapport d'une campagne MailChimp"""
        headers, base_url = self._get_api_client()
        
        try:
            response = requests.get(f"{base_url}/reports/{campaign_id}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération du rapport de campagne: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            return None
    
    def _create_campaign(self, campaign_info):
        """Crée une nouvelle campagne MailChimp"""
        headers, base_url = self._get_api_client()
        
        # Étape 1: Créer la campagne
        campaign_data = {
            "type": "regular",
            "recipients": {
                "list_id": campaign_info['list_id']
            },
            "settings": {
                "subject_line": campaign_info['subject'],
                "title": campaign_info['name'],
                "from_name": "Votre Nom",  # À personnaliser
                "reply_to": "email@example.com",  # À personnaliser
                "auto_footer": True
            }
        }
        
        try:
            response = requests.post(f"{base_url}/campaigns", headers=headers, json=campaign_data)
            response.raise_for_status()
            campaign = response.json()
            
            # Étape 2: Ajouter le contenu
            campaign_id = campaign['id']
            content_data = {
                "html": campaign_info['content']
            }
            
            content_response = requests.put(
                f"{base_url}/campaigns/{campaign_id}/content", 
                headers=headers, 
                json=content_data
            )
            content_response.raise_for_status()
            
            return campaign
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la création de la campagne: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            raise ValueError(f"Erreur lors de la création de la campagne: {str(e)}")
    
    def _add_subscriber(self, list_id, email, firstname="", lastname=""):
        """Ajoute un abonné à une liste MailChimp"""
        headers, base_url = self._get_api_client()
        
        subscriber_data = {
            "email_address": email,
            "status": "subscribed",
            "merge_fields": {}
        }
        
        if firstname:
            subscriber_data["merge_fields"]["FNAME"] = firstname
        
        if lastname:
            subscriber_data["merge_fields"]["LNAME"] = lastname
        
        try:
            response = requests.post(
                f"{base_url}/lists/{list_id}/members", 
                headers=headers, 
                json=subscriber_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'ajout d'un abonné: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            raise ValueError(f"Erreur lors de l'ajout d'un abonné: {str(e)}") 