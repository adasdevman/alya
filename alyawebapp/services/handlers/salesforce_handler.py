import logging
import json
import re
from datetime import datetime, timedelta
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class SalesforceHandler:
    """Gestionnaire pour les intégrations Salesforce"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.prospect_info = {}
        self.action_info = {}
        self.salesforce_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Salesforce si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='salesforce')
            self.salesforce_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.salesforce_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à Salesforce"""
        try:
            if not self.salesforce_integration:
                return "Vous n'avez pas installé cette intégration."
            
            # Machine à états pour le suivi des prospects
            if self.conversation_state == 'prospect_interaction_start':
                self.prospect_info['prospect_id'] = text.strip()
                
                try:
                    interactions = self._get_prospect_interactions(self.prospect_info['prospect_id'])
                    self.conversation_state = None  # Réinitialiser l'état
                    
                    if not interactions:
                        return "Aucune interaction récente trouvée pour ce prospect."
                    
                    # Formater les interactions pour l'affichage
                    response = "📊 Voici les dernières interactions avec ce prospect :\n\n"
                    for i, interaction in enumerate(interactions[:5], 1):
                        response += f"• {interaction['date']} - {interaction['type']} : {interaction['subject']}\n"
                        if interaction.get('description'):
                            response += f"  Description : {interaction['description'][:100]}...\n"
                        response += "\n"
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Erreur récupération interactions: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return "❌ Erreur lors de la récupération des interactions. Veuillez vérifier que votre intégration Salesforce est correctement configurée."
            
            # Machine à états pour la programmation d'actions
            if self.conversation_state == 'schedule_action_start':
                self.action_info['prospect_id'] = text.strip()
                self.conversation_state = 'waiting_for_action_type'
                return "Quel type d'action souhaitez-vous programmer ? (appel, email, réunion, etc.)"
                
            elif self.conversation_state == 'waiting_for_action_type':
                self.action_info['action_type'] = text.strip()
                self.conversation_state = 'waiting_for_due_date'
                return "Pour quelle date ? (format: JJ/MM/AAAA)"
                
            elif self.conversation_state == 'waiting_for_due_date':
                try:
                    # Convertir la date au format attendu par Salesforce
                    date_parts = text.strip().split('/')
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                        self.action_info['due_date'] = formatted_date
                    else:
                        # Utiliser la date d'aujourd'hui + 3 jours si format invalide
                        future_date = datetime.now() + timedelta(days=3)
                        self.action_info['due_date'] = future_date.strftime("%Y-%m-%d")
                        
                    self.conversation_state = 'waiting_for_description'
                    return "Veuillez fournir une description pour cette action :"
                except Exception as e:
                    logger.error(f"Erreur traitement date: {str(e)}")
                    self.conversation_state = 'waiting_for_due_date'
                    return "Format de date invalide. Veuillez utiliser le format JJ/MM/AAAA :"
                
            elif self.conversation_state == 'waiting_for_description':
                self.action_info['description'] = text.strip()
                
                try:
                    # Programmer l'action dans Salesforce
                    result = self._schedule_next_action(self.action_info)
                    self.conversation_state = None  # Réinitialiser l'état
                    self.action_info = {}
                    return "✅ Action programmée avec succès dans Salesforce !"
                except Exception as e:
                    logger.error(f"Erreur programmation action: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return "❌ Erreur lors de la programmation de l'action. Veuillez vérifier que votre intégration Salesforce est correctement configurée."
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention de voir les interactions avec un prospect
            if any(phrase in text_lower for phrase in ["interactions prospect", "historique prospect", "activités prospect"]):
                # Vérifier si l'utilisateur a déjà fourni un ID de prospect
                prospect_id_match = re.search(r'\b([a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})\b', text)
                if prospect_id_match:
                    self.prospect_info['prospect_id'] = prospect_id_match.group(0)
                    return self._get_prospect_interactions(self.prospect_info['prospect_id'])
                else:
                    self.conversation_state = 'prospect_interaction_start'
                    return "Je vais vous montrer l'historique des interactions. Veuillez fournir l'ID Salesforce du prospect :"
            
            # Intention de programmer une action
            if any(phrase in text_lower for phrase in ["programmer action", "planifier action", "nouvelle tâche"]):
                # Vérifier si l'utilisateur a déjà fourni un ID de prospect
                prospect_id_match = re.search(r'\b([a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})\b', text)
                if prospect_id_match:
                    self.action_info['prospect_id'] = prospect_id_match.group(0)
                    self.conversation_state = 'waiting_for_action_type'
                    return "Quel type d'action souhaitez-vous programmer ? (appel, email, réunion, etc.)"
                else:
                    self.conversation_state = 'schedule_action_start'
                    return "Je vais vous aider à programmer une action. Veuillez fournir l'ID Salesforce du prospect :"
            
            # Intention de voir les opportunités
            if any(phrase in text_lower for phrase in ["opportunités", "statut opportunité", "affaires en cours"]):
                # Vérifier si l'utilisateur a déjà fourni un ID de prospect
                prospect_id_match = re.search(r'\b([a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})\b', text)
                if prospect_id_match:
                    return self._get_opportunity_status(prospect_id_match.group(0))
                else:
                    return "Pour voir les opportunités, veuillez me fournir l'ID Salesforce du prospect (par exemple: 00Q1j000004XYZ)."
            
            return "Je peux vous aider avec Salesforce. Voici ce que je peux faire :\n" + \
                   "- Consulter l'historique des interactions avec un prospect\n" + \
                   "- Programmer une action de suivi (appel, email, etc.)\n" + \
                   "- Vérifier le statut des opportunités liées à un prospect"

        except Exception as e:
            logger.error(f"Erreur Salesforce: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _get_prospect_interactions(self, prospect_id):
        """Récupère les interactions avec un prospect en utilisant l'intégration Salesforce existante"""
        from alyawebapp.integrations.salesforce.handler import SalesforceHandler as SalesforceAPI
        
        if not prospect_id:
            raise ValueError("L'ID du prospect est requis")
        
        # Utiliser l'implémentation existante
        sf_handler = SalesforceAPI(self.salesforce_integration.config)
        return sf_handler.get_prospect_interactions(prospect_id)
    
    def _schedule_next_action(self, action_info):
        """Programme une action pour un prospect en utilisant l'intégration Salesforce existante"""
        from alyawebapp.integrations.salesforce.handler import SalesforceHandler as SalesforceAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['prospect_id', 'action_type', 'due_date', 'description']
        missing_fields = [field for field in required_fields if field not in action_info]
        if missing_fields:
            raise ValueError(f"Informations incomplètes. Champs manquants: {', '.join(missing_fields)}")
        
        # Utiliser l'implémentation existante
        sf_handler = SalesforceAPI(self.salesforce_integration.config)
        return sf_handler.schedule_next_action(
            prospect_id=action_info['prospect_id'],
            action_type=action_info['action_type'],
            due_date=action_info['due_date'],
            description=action_info['description']
        )
    
    def _get_opportunity_status(self, prospect_id):
        """Récupère le statut des opportunités liées à un prospect"""
        from alyawebapp.integrations.salesforce.handler import SalesforceHandler as SalesforceAPI
        
        if not prospect_id:
            raise ValueError("L'ID du prospect est requis")
        
        try:
            # Utiliser l'implémentation existante
            sf_handler = SalesforceAPI(self.salesforce_integration.config)
            opportunities = sf_handler.get_opportunity_status(prospect_id)
            
            if not opportunities:
                return "Aucune opportunité trouvée pour ce prospect."
            
            # Formater les opportunités pour l'affichage
            response = "💰 Voici les opportunités liées à ce prospect :\n\n"
            for i, opp in enumerate(opportunities, 1):
                response += f"• Opportunité {i}: {opp['Name']}\n"
                response += f"  Étape: {opp['StageName']}\n"
                if 'Amount' in opp and opp['Amount']:
                    response += f"  Montant: {opp['Amount']} €\n"
                if 'Probability' in opp and opp['Probability']:
                    response += f"  Probabilité: {opp['Probability']}%\n"
                if 'CloseDate' in opp and opp['CloseDate']:
                    response += f"  Date de clôture prévue: {opp['CloseDate']}\n"
                response += "\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des opportunités: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer les opportunités. Veuillez vérifier que votre intégration Salesforce est correctement configurée." 