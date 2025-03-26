import logging
import json
import requests
from datetime import datetime, timedelta
from ..exceptions import NetworkError, AITimeoutError
import re

logger = logging.getLogger(__name__)

class HubSpotHandler:
    """Gestionnaire pour les intégrations HubSpot"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.contact_info = {}
        self.existing_contact = None
        self.task_info = {}
        self.note_info = {}
        self.combined_info = {}
    
    def handle_request(self, message):
        """Gère une requête HubSpot"""
        try:
            # Vérification et redirection multi-services
            detected_service = self._detect_service_type(message)
            logger.info(f"[AIGUILLAGE] Service détecté: '{detected_service}' pour: '{message}'")
            
            # Si un autre service que HubSpot est détecté, essayer de rediriger
            if detected_service and detected_service != "hubspot":
                try:
                    if detected_service == "trello":
                        try:
                            from .trello_handler import TrelloHandler
                            logger.info(f"[AIGUILLAGE] Redirection vers Trello: '{message}'")
                            trello_handler = TrelloHandler(self.orchestrator)
                            return trello_handler.handle_request(message)
                        except (ImportError, AttributeError) as e:
                            logger.error(f"[AIGUILLAGE] Impossible d'accéder au service Trello: {str(e)}")
                            return "Je comprends que votre demande concerne Trello, mais je ne peux pas y accéder actuellement. Vous pouvez soit reconfigurer l'intégration Trello, soit me demander autre chose. Comment puis-je vous aider autrement ?"
                    elif detected_service == "slack":
                        try:
                            from .slack_handler import SlackHandler
                            logger.info(f"[AIGUILLAGE] Redirection vers Slack: '{message}'")
                            slack_handler = SlackHandler(self.orchestrator)
                            return slack_handler.handle_request(message)
                        except (ImportError, AttributeError) as e:
                            logger.error(f"[AIGUILLAGE] Impossible d'accéder au service Slack: {str(e)}")
                            return "Je comprends que votre demande concerne Slack, mais je ne peux pas y accéder actuellement. Vous pouvez soit reconfigurer l'intégration Slack, soit me demander autre chose. Comment puis-je vous aider autrement ?"
                except Exception as e:
                    logger.error(f"[AIGUILLAGE] Erreur lors de la détection du service: {str(e)}")
                    detected_service = "hubspot"
            
            # Début du traitement HubSpot
            logger.info("===== DÉBUT DU TRAITEMENT HUBSPOT =====")
            logger.info(f"Texte reçu: '{message}'")
            logger.info(f"État de conversation actuel: {self.conversation_state}")
            
            # Vérifier l'intégration HubSpot avant de continuer
            hubspot_integration = self._get_hubspot_integrations()
            if not hubspot_integration:
                redirected_response = self._try_other_integration(message)
                if redirected_response:
                    return redirected_response
                
                if detected_service == "hubspot":
                    return "Je comprends que votre demande concerne HubSpot (contacts, tâches, notes), mais l'intégration n'est pas configurée. Vous pouvez la configurer dans vos paramètres d'intégration. Puis-je vous aider avec autre chose ?"
                else:
                    return "Votre demande n'a pas pu être traitée car les intégrations nécessaires ne sont pas configurées. Vous pouvez configurer HubSpot, Trello ou Slack dans vos paramètres d'intégration. Comment puis-je vous aider autrement ?"
            
            # Vérifier la validité du token de manière proactive
            token_valid = self._ensure_valid_token()
            if not token_valid:
                config = hubspot_integration.config
                error_details = ""
                
                if not isinstance(config, dict):
                    error_details = "La configuration de l'intégration est invalide."
                elif not config.get('refresh_token'):
                    error_details = "Le refresh_token est manquant. Vous devez reconfigurer l'application."
                elif not config.get('client_id') or not config.get('client_secret'):
                    error_details = "Les informations client (client_id ou client_secret) sont manquantes ou incorrectes."
                elif config.get('refresh_errors'):
                    last_error = config['refresh_errors'][-1]
                    if isinstance(last_error, dict):
                        if 'error' in last_error and isinstance(last_error['error'], dict):
                            error_status = last_error['error'].get('status')
                            if error_status == 'BAD_REFRESH_TOKEN':
                                error_details = "Le refresh_token n'est plus valide ou a expiré."
                            elif error_status == 'UNAUTHORIZED':
                                error_details = "Les informations client (client_id ou client_secret) sont incorrectes."
                
                error_message = "⚠️ Votre intégration HubSpot nécessite une réautorisation. "
                error_message += "Le token d'accès est expiré et n'a pas pu être rafraîchi. "
                
                if error_details:
                    error_message += f"Diagnostic : {error_details} "
                
                error_message += "Veuillez vous rendre dans les paramètres d'intégration pour reconfigurer HubSpot. "
                error_message += "Puis-je vous aider avec autre chose en attendant ?"
                
                return error_message
            
            # Vérifier spécifiquement pour les emails avec partenariat potentiel
            partenariat_match = re.search(r'partenariat potentiel', message, re.IGNORECASE)
            email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', message)
            
            if partenariat_match and email_match:
                email = email_match.group(1)
                logger.info(f"DÉTECTION SPÉCIALE: {email} trouvé dans le message avec mention de partenariat potentiel")
                logger.info(f"TRAITEMENT DIRECT pour {email}")
                
                nom_match = re.search(r'pour\s+([A-Za-z]+)\s+([A-Za-z]+)', message)
                first_name = nom_match.group(1) if nom_match else ""
                last_name = nom_match.group(2) if nom_match else ""
                
                contact = self._ensure_contact_exists(email, first_name, last_name)
                
                if contact:
                    logger.info(f"Contact trouvé ou créé: {contact.get('id')} - {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}")
                    
                    try:
                        date_info = datetime.now() + timedelta(weeks=1)
                        date_info_str = date_info.strftime("%Y-%m-%d")
                        note_content = "À contacter pour un partenariat potentiel"
                        
                        note_info = {
                            'contact_id': contact.get('id'),
                            'contact_email': email,
                            'content': note_content
                        }
                        logger.info(f"Tentative de création de note pour {email}")
                        note_result = self._create_note(note_info)
                        note_created = note_result and note_result.get('id')
                        logger.info(f"Note créée avec succès: {note_result.get('id', 'Unknown') if note_created else 'Échec'}")
                        
                        task_info = {
                            'contact_id': contact.get('id'),
                            'contact_email': email,
                            'title': 'Suivi de contact',
                            'due_date': date_info_str,
                            'notes': note_content
                        }
                        logger.info(f"Tentative de création de tâche pour {email}")
                        
                        try:
                            task_result = self._create_task(task_info)
                            task_created = task_result and task_result.get('id')
                            logger.info(f"Tâche créée avec succès: {task_result.get('id', 'Unknown') if task_created else 'Échec'}")
                        except Exception as task_error:
                            task_created = False
                            logger.error(f"Erreur lors de la création de la tâche: {str(task_error)}")
                        
                        self.conversation_state = None
                        logger.info("Réinitialisation de l'état de conversation")
                        
                        if note_created and task_created:
                            return f"✅ J'ai planifié un suivi pour la semaine prochaine et ajouté la note 'À contacter pour un partenariat potentiel' pour {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}."
                        elif note_created:
                            return f"✅ J'ai ajouté la note 'À contacter pour un partenariat potentiel' pour {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}. ⚠️ La tâche de suivi n'a pas pu être créée."
                        elif task_created:
                            return f"✅ J'ai planifié un suivi pour la semaine prochaine pour {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}. ⚠️ La note n'a pas pu être ajoutée."
                        else:
                            return f"❌ Je n'ai pas pu créer la tâche ni la note. Veuillez réessayer plus tard."
                    except Exception as e:
                        logger.error(f"Erreur lors de la création: {str(e)}")
                        self.conversation_state = None
                        return f"❌ Erreur lors de la création du suivi et de la note: {str(e)}"
                else:
                    return "❌ Je n'ai pas pu trouver ou créer le contact. Veuillez réessayer."
            
            # Détection d'ajout de contact HubSpot
            contact_match = re.search(r'(?:ajoute|crée|creer|créer|créé|ajouter)\s+(?:un\s+)?(?:nouveau\s+)?contact', message, re.IGNORECASE)
            
            if contact_match:
                logger.info("Détection d'une demande d'ajout de contact")
                
                try:
                    contact_info = self.extract_contact_info(message)
                    
                    if not contact_info or not isinstance(contact_info, dict):
                        logger.error(f"Extraction d'informations de contact échouée. Résultat: {contact_info}")
                        return "Je n'ai pas pu extraire toutes les informations nécessaires pour créer ce contact. Pourriez-vous reformuler en précisant l'email, le prénom et le nom du contact?"
                    
                    required_fields = ['email', 'firstname', 'lastname']
                    missing_fields = [field for field in required_fields if field not in contact_info]
                    
                    if missing_fields:
                        logger.warning(f"Informations de contact incomplètes. Champs manquants: {missing_fields}")
                        return f"Il me manque des informations pour créer ce contact: {', '.join(missing_fields)}. Pourriez-vous les préciser?"
                    
                    logger.info(f"Tentative de création de contact avec les informations: {contact_info}")
                    result = self.create_contact(contact_info)
                    
                    if isinstance(result, str):
                        logger.error(f"Erreur lors de la création du contact: {result}")
                        return f"❌ {result}"
                    elif isinstance(result, dict) and result.get('id'):
                        contact_id = result.get('id')
                        properties = result.get('properties', {})
                        firstname = properties.get('firstname', contact_info.get('firstname', ''))
                        lastname = properties.get('lastname', contact_info.get('lastname', ''))
                        
                        existing_contact = self._check_contact_exists(contact_info['email'])
                        if existing_contact and existing_contact.get('id') == contact_id:
                            return f"✅ Les informations du contact {firstname} {lastname} ont été mises à jour dans HubSpot."
                        else:
                            return f"✅ Le contact {firstname} {lastname} a été créé avec succès dans HubSpot."
                    else:
                        logger.error(f"Résultat inattendu de la création de contact: {result}")
                        return "Une erreur inattendue s'est produite lors du traitement du contact. Veuillez réessayer."
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la demande d'ajout de contact: {str(e)}")
                    return f"❌ Une erreur est survenue lors de la création du contact: {str(e)}"
            
            # Continuer avec le reste du traitement normal
            return "Je ne comprends pas exactement ce que vous souhaitez faire. Pourriez-vous préciser votre demande ?"
            
        except Exception as e:
            logger.error(f"Erreur HubSpot: {str(e)}")
            self.conversation_state = None
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer." 