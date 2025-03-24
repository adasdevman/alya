import logging
from .hubspot_handler import HubSpotHandler
from .trello_handler import TrelloHandler
from .gmail_handler import GmailHandler
from .google_drive_handler import GoogleDriveHandler
from .salesforce_handler import SalesforceHandler
from .quickbooks_handler import QuickBooksHandler
from .slack_handler import SlackHandler
# À mesure que de nouveaux handlers sont ajoutés, nous les importerons ici

logger = logging.getLogger(__name__)

class IntegrationRouter:
    """Routeur qui gère le dispatch des requêtes vers les bons handlers d'intégration"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handlers = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialise tous les handlers d'intégration"""
        # Créer des instances de tous les handlers disponibles
        self.handlers = {
            'hubspot': HubSpotHandler(self.orchestrator),
            'trello': TrelloHandler(self.orchestrator),
            'gmail': GmailHandler(self.orchestrator),
            'google_drive': GoogleDriveHandler(self.orchestrator),
            'salesforce': SalesforceHandler(self.orchestrator),
            'quickbooks': QuickBooksHandler(self.orchestrator),
            'slack': SlackHandler(self.orchestrator),
            # D'autres handlers seront ajoutés ici
        }
    
    def route_request(self, intent, message):
        """
        Route la requête vers le handler approprié en fonction de l'intention.
        
        Args:
            intent (dict): L'intention détectée
            message (str): Le message original de l'utilisateur
            
        Returns:
            str: La réponse du handler
        """
        try:
            # Si c'est une conversation simple ou une erreur, retourner la réponse raw
            if intent.get('intent') in ['conversation', 'error', 'general_query']:
                return intent.get('raw_response', "Je ne comprends pas votre demande. Pouvez-vous préciser?")
            
            # Cas d'ambiguïté entre plusieurs intégrations
            if intent.get('intent') == 'ambiguous':
                possible_integrations = intent.get('possible_integrations', [])
                detected_actions = intent.get('detected_actions', {})
                response = "Votre demande pourrait être traitée par plusieurs services. Lequel souhaitez-vous utiliser ?\n\n"
                for integration in possible_integrations:
                    actions = detected_actions.get(integration, [])
                    if actions:
                        response += f"📎 {integration.capitalize()} - Actions possibles : {', '.join(actions)}\n"
                return response
            
            # Cas d'une intégration spécifique
            if intent.get('intent') == 'integration' or intent.get('intent') == 'integration_action':
                integration = intent.get('integration')
                if integration in self.handlers:
                    return self.handlers[integration].handle_request(message)
                else:
                    logger.warning(f"Aucun handler trouvé pour l'intégration {integration}")
                    return f"Je ne sais pas encore comment gérer les requêtes pour {integration}. Cette fonctionnalité sera bientôt disponible!"
            
            # Cas par défaut
            return "Je ne suis pas sûr de comprendre votre demande. Pouvez-vous préciser ce que vous souhaitez faire?"
            
        except Exception as e:
            logger.error(f"Erreur lors du routage de la requête: {str(e)}")
            return f"Une erreur est survenue lors du traitement de votre demande: {str(e)}"
    
    def get_handler(self, integration_name):
        """
        Récupère un handler d'intégration spécifique.
        
        Args:
            integration_name (str): Le nom de l'intégration
            
        Returns:
            object: Le handler d'intégration ou None s'il n'existe pas
        """
        return self.handlers.get(integration_name.lower(), None) 