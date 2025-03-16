import logging
from simple_salesforce import Salesforce
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SalesforceManager:
    @classmethod
    def get_contact_interactions(cls, user_integration, contact_email):
        """Récupère les interactions avec un contact"""
        try:
            sf = Salesforce(
                username=user_integration.config.get('username'),
                password=user_integration.config.get('password'),
                security_token=user_integration.config.get('security_token')
            )
            
            # Récupérer le contact
            contact = sf.query(
                f"SELECT Id, Name FROM Contact WHERE Email = '{contact_email}'"
            )
            
            if not contact.get('records'):
                return None
                
            contact_id = contact['records'][0]['Id']
            
            # Récupérer les tâches
            tasks = sf.query(
                f"""SELECT Subject, ActivityDate, Description, Status 
                FROM Task 
                WHERE WhoId = '{contact_id}' 
                ORDER BY ActivityDate DESC"""
            )
            
            # Récupérer les emails
            emails = sf.query(
                f"""SELECT Subject, ActivityDate, Description 
                FROM EmailMessage 
                WHERE RelatedToId = '{contact_id}' 
                ORDER BY ActivityDate DESC"""
            )
            
            return {
                'tasks': tasks.get('records', []),
                'emails': emails.get('records', [])
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération interactions Salesforce: {str(e)}")
            raise

    @classmethod
    def send_followup_email(cls, user_integration, contact_email, subject, body):
        """Envoie un email de suivi à un contact"""
        try:
            sf = Salesforce(
                username=user_integration.config.get('username'),
                password=user_integration.config.get('password'),
                security_token=user_integration.config.get('security_token')
            )
            
            # Récupérer le contact
            contact = sf.query(
                f"SELECT Id FROM Contact WHERE Email = '{contact_email}'"
            )
            
            if not contact.get('records'):
                raise ValueError(f"Contact non trouvé: {contact_email}")
                
            contact_id = contact['records'][0]['Id']
            
            # Créer l'email
            email_data = {
                'ToAddress': contact_email,
                'Subject': subject,
                'TextBody': body,
                'RelatedToId': contact_id
            }
            
            result = sf.EmailMessage.create(email_data)
            return result
            
        except Exception as e:
            logger.error(f"Erreur envoi email Salesforce: {str(e)}")
            raise

    @classmethod
    def create_opportunity(cls, user_integration, contact_email, amount, stage):
        """Crée une opportunité pour un contact"""
        try:
            sf = Salesforce(
                username=user_integration.config.get('username'),
                password=user_integration.config.get('password'),
                security_token=user_integration.config.get('security_token')
            )
            
            # Récupérer le contact
            contact = sf.query(
                f"SELECT Id, AccountId FROM Contact WHERE Email = '{contact_email}'"
            )
            
            if not contact.get('records'):
                raise ValueError(f"Contact non trouvé: {contact_email}")
                
            contact_data = contact['records'][0]
            
            # Créer l'opportunité
            opportunity_data = {
                'Name': f"Opportunité - {datetime.now().strftime('%Y-%m-%d')}",
                'AccountId': contact_data['AccountId'],
                'Amount': amount,
                'StageName': stage,
                'CloseDate': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            }
            
            result = sf.Opportunity.create(opportunity_data)
            return result
            
        except Exception as e:
            logger.error(f"Erreur création opportunité Salesforce: {str(e)}")
            raise 