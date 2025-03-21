from ..base import BaseIntegration
import requests
from typing import Dict, Any, List
import logging
from datetime import datetime
from simple_salesforce import Salesforce

logger = logging.getLogger(__name__)

class SalesforceHandler(BaseIntegration):
    AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
    TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
    
    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.redirect_uri = config['redirect_uri']
        self.access_token = config.get('access_token')
        self.instance_url = config.get('instance_url')
        self.initialize_client()

    def initialize_client(self):
        """Initialise le client Salesforce"""
        self.sf = Salesforce(
            instance_url=self.instance_url,
            session_id=self.access_token
        )

    def get_prospect_interactions(self, prospect_id: str) -> List[Dict[str, Any]]:
        """Récupère les dernières interactions avec un prospect"""
        try:
            # Récupérer les informations du contact
            contact = self.sf.Contact.get(prospect_id)
            
            # Récupérer les activités (appels, emails, tâches)
            activities = []
            
            # Récupérer les appels
            calls = self.sf.query(
                f"SELECT Id, Subject, ActivityDate, Description, CallType FROM Task "
                f"WHERE WhoId = '{prospect_id}' AND TaskSubtype = 'Call' "
                f"ORDER BY ActivityDate DESC LIMIT 10"
            )
            
            # Récupérer les emails
            emails = self.sf.query(
                f"SELECT Id, Subject, ActivityDate, Description FROM EmailMessage "
                f"WHERE RelatedToId = '{prospect_id}' "
                f"ORDER BY ActivityDate DESC LIMIT 10"
            )
            
            # Récupérer les tâches
            tasks = self.sf.query(
                f"SELECT Id, Subject, ActivityDate, Description FROM Task "
                f"WHERE WhoId = '{prospect_id}' AND TaskSubtype != 'Call' "
                f"ORDER BY ActivityDate DESC LIMIT 10"
            )
            
            # Combiner et trier toutes les activités
            for record in calls['records']:
                activities.append({
                    'type': 'Appel',
                    'date': record['ActivityDate'],
                    'description': record['Description'],
                    'subject': record['Subject']
                })
                
            for record in emails['records']:
                activities.append({
                    'type': 'Email',
                    'date': record['ActivityDate'],
                    'description': record['Description'],
                    'subject': record['Subject']
                })
                
            for record in tasks['records']:
                activities.append({
                    'type': 'Tâche',
                    'date': record['ActivityDate'],
                    'description': record['Description'],
                    'subject': record['Subject']
                })
            
            # Trier par date décroissante
            activities.sort(key=lambda x: x['date'], reverse=True)
            
            return activities
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des interactions: {str(e)}")
            raise

    def send_follow_up_email(self, prospect_id: str, template_id: str = None, custom_message: str = None) -> Dict[str, Any]:
        """Envoie un email de suivi à un prospect"""
        try:
            # Récupérer les informations du contact
            contact = self.sf.Contact.get(prospect_id)
            
            # Créer l'email
            email_data = {
                'ToAddress': contact['Email'],
                'Subject': 'Suivi de notre conversation',
                'TextBody': custom_message if custom_message else 'Message de suivi automatique',
                'RelatedToId': prospect_id
            }
            
            if template_id:
                email_data['TemplateId'] = template_id
            
            # Envoyer l'email
            result = self.sf.EmailMessage.create(email_data)
            
            # Créer une tâche de suivi
            task_data = {
                'Subject': 'Email de suivi envoyé',
                'WhoId': prospect_id,
                'Status': 'Completed',
                'Priority': 'Normal',
                'ActivityDate': datetime.now().strftime('%Y-%m-%d')
            }
            
            self.sf.Task.create(task_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de suivi: {str(e)}")
            raise

    def get_opportunity_status(self, prospect_id: str) -> Dict[str, Any]:
        """Récupère le statut des opportunités liées à un prospect"""
        try:
            opportunities = self.sf.query(
                f"SELECT Id, Name, StageName, Amount, CloseDate, Probability "
                f"FROM Opportunity WHERE AccountId IN "
                f"(SELECT AccountId FROM Contact WHERE Id = '{prospect_id}') "
                f"ORDER BY CloseDate DESC"
            )
            
            return opportunities['records']
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des opportunités: {str(e)}")
            raise

    def schedule_next_action(self, prospect_id: str, action_type: str, due_date: str, description: str) -> Dict[str, Any]:
        """Programme la prochaine action pour un prospect"""
        try:
            task_data = {
                'WhoId': prospect_id,
                'Subject': f"Action planifiée: {action_type}",
                'Description': description,
                'ActivityDate': due_date,
                'Status': 'Not Started',
                'Priority': 'High'
            }
            
            return self.sf.Task.create(task_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la programmation de l'action: {str(e)}")
            raise 