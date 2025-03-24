import logging
import json
import requests
from datetime import datetime
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class HubSpotHandler:
    """Gestionnaire pour les intégrations HubSpot"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.contact_info = {}
    
    def handle_request(self, text):
        """Gère les requêtes liées à HubSpot"""
        try:
            # Récupérer les intégrations HubSpot de l'utilisateur
            hubspot_integrations = self._get_hubspot_integrations()
            
            if not hubspot_integrations:
                return "Vous n'avez pas installé cette intégration."

            # Détecter si l'utilisateur veut créer un contact
            text_lower = text.lower()
            if "créer" in text_lower and "contact" in text_lower or "nouveau contact" in text_lower:
                self.conversation_state = 'contact_creation_start'
                return "Je vais vous aider à créer un contact dans HubSpot. Quel est le prénom du contact ?"

            # Gérer les différentes étapes de création de contact
            if self.conversation_state == 'contact_creation_start':
                self.contact_info = {'firstname': text.strip()}
                self.conversation_state = 'waiting_for_lastname'
                return "Quel est le nom de famille du contact ?"
                
            elif self.conversation_state == 'waiting_for_lastname':
                self.contact_info['lastname'] = text.strip()
                self.conversation_state = 'waiting_for_email'
                return "Quelle est l'adresse email du contact ?"
                
            elif self.conversation_state == 'waiting_for_email':
                self.contact_info['email'] = text.strip()
                self.conversation_state = 'waiting_for_phone'
                return "Quel est le numéro de téléphone du contact ? (optionnel, appuyez sur Entrée si aucun)"
                
            elif self.conversation_state == 'waiting_for_phone':
                if text.strip():
                    self.contact_info['phone'] = text.strip()
                else:
                    self.contact_info['phone'] = ""
                
                # Créer le contact dans HubSpot
                try:
                    result = self.create_contact(self.contact_info)
                    self.conversation_state = None
                    self.contact_info = {}
                    return "✅ Contact créé avec succès dans HubSpot !"
                except Exception as e:
                    logger.error(f"Erreur création contact HubSpot: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état pour éviter de bloquer l'utilisateur
                    return "❌ Erreur lors de la création du contact. Veuillez vérifier que votre intégration HubSpot est correctement configurée."

            return "Je peux vous aider avec HubSpot. Voici ce que je peux faire :\n" + \
                   "- Créer un nouveau contact (dites 'créer un contact')\n" + \
                   "- Mettre à jour un contact existant\n" + \
                   "- Rechercher des contacts"

        except Exception as e:
            logger.error(f"Erreur HubSpot: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _get_hubspot_integrations(self):
        """Récupère les intégrations HubSpot actives de l'utilisateur"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            hubspot_integrations = Integration.objects.filter(name__icontains='hubspot')
            user_integration = None
            
            for integration in hubspot_integrations:
                try:
                    user_integration = UserIntegration.objects.get(
                        user=self.user,
                        integration=integration,
                        enabled=True
                    )
                    if user_integration:
                        return user_integration
                except UserIntegration.DoesNotExist:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des intégrations HubSpot: {str(e)}")
            return None
    
    def extract_contact_info(self, text):
        """Extrait les informations de contact du texte"""
        prompt = f"""
        En tant qu'expert en CRM, analyse cette demande pour extraire les informations de contact.
        
        Identifie naturellement :
        - Le prénom
        - Le nom
        - L'email
        - Le téléphone
        - L'entreprise (si mentionnée)
        - Le poste/titre (si mentionné)
        - Le site web (si mentionné)
        
        Texte à analyser : {text}
        
        Retourne uniquement un objet JSON avec les champs trouvés.
        Si un champ n'est pas mentionné, ne pas l'inclure dans le JSON.
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en analyse de données CRM."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        return json.loads(response.choices[0].message.content)

    def create_contact(self, contact_info):
        """Crée un contact dans HubSpot"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            # Journalisation du contenu et du type de contact_info
            logger.info(f"Type de contact_info: {type(contact_info)}")
            logger.info(f"Contenu de contact_info: {contact_info}")
            
            # Vérifier que contact_info est un dictionnaire
            if not isinstance(contact_info, dict):
                logger.error(f"Erreur: contact_info n'est pas un dictionnaire mais {type(contact_info)}")
                return "Erreur de format des données de contact. Veuillez réessayer."
                
            # Vérifier si tous les champs nécessaires sont présents
            required_fields = ['email', 'firstname', 'lastname']
            missing_fields = [field for field in required_fields if field not in contact_info]
            if missing_fields:
                logger.error(f"Champs requis manquants: {missing_fields}")
                return f"Informations incomplètes. Champs manquants: {', '.join(missing_fields)}"
            
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("Intégration HubSpot manquante")
                return "Vous n'avez pas installé cette intégration."
            
            # Récupérer le token HubSpot
            logger.info(f"Configuration de l'utilisateur pour HubSpot: {user_integration.config}")
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("Token d'accès HubSpot manquant")
                return "Le token d'accès HubSpot est manquant. Veuillez vous connecter à HubSpot dans la section Intégrations de votre compte."

            # Préparer les données pour HubSpot
            properties = {
                "email": contact_info['email'],
                "firstname": contact_info['firstname'],
                "lastname": contact_info['lastname']
            }
            
            # Ajouter le téléphone s'il existe
            if 'phone' in contact_info and contact_info['phone']:
                properties["phone"] = contact_info['phone']
            
            # Créer le contact dans HubSpot
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "properties": properties
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la création du contact HubSpot: {str(e)}")
            raise
    
    def parse_contact_info(self, message):
        """Parse les informations de contact à partir d'un message"""
        try:
            # Essayer d'extraire les informations avec l'IA pour plus de précision
            contact_info = self.extract_contact_info(message)
            if contact_info:
                return contact_info
                
            # Méthode alternative si l'extraction par IA échoue
            # Diviser le message en mots
            words = message.split()
            
            # Initialiser les variables pour stocker les informations
            lastname = firstname = email = phone = None
            
            # Parcourir les mots pour identifier les champs
            for word in words:
                if '@' in word and '.' in word:
                    email = word
                elif word.isdigit() and len(word) >= 10:  # Supposons que le numéro de téléphone a au moins 10 chiffres
                    phone = word
                elif not firstname:
                    firstname = word
                elif not lastname:
                    lastname = word
            
            # Vérifier si nous avons au moins les informations essentielles
            if not (firstname and lastname and email):
                return None
            
            return {
                'lastname': lastname,
                'firstname': firstname,
                'email': email,
                'phone': phone
            }
        except Exception as e:
            logger.error(f"Erreur lors du parsing des informations: {str(e)}")
            return {
                'firstname': 'Non spécifié',
                'lastname': 'Non spécifié',
                'email': 'non@specifie.com',
                'phone': ''
            }  # Retourner un dictionnaire par défaut en cas d'erreur 