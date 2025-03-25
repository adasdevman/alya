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
        self.existing_contact = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à HubSpot"""
        try:
            # Récupérer les intégrations HubSpot de l'utilisateur
            hubspot_integration = self._get_hubspot_integrations()
            
            if not hubspot_integration:
                return "Vous n'avez pas installé cette intégration. Veuillez configurer HubSpot dans vos intégrations avant de l'utiliser."

            # Vérifier si l'intégration est correctement configurée
            access_token = hubspot_integration.access_token or hubspot_integration.config.get('access_token')
            if not access_token:
                return "❌ Votre intégration HubSpot n'est pas correctement configurée. Veuillez vérifier vos paramètres d'intégration."

            # Détecter si l'utilisateur veut créer un contact
            text_lower = text.lower()
            if ("créer" in text_lower and "contact" in text_lower) or "nouveau contact" in text_lower or "ajoute un nouveau contact" in text_lower:
                # Vérifier si le message contient déjà toutes les informations nécessaires
                contact_info = self.extract_contact_info(text)
                
                if contact_info and 'email' in contact_info and 'firstname' in contact_info and 'lastname' in contact_info:
                    # Le message contient déjà toutes les informations nécessaires, procéder directement à la création
                    logger.info(f"Informations de contact extraites: {contact_info}")
                    
                    try:
                        # Vérifier si le contact existe déjà
                        existing_contact = self._check_contact_exists(contact_info['email'])
                        if existing_contact:
                            contact_id = existing_contact.get('id')
                            self.update_contact(contact_id, contact_info)
                            return f"{contact_info['firstname']} {contact_info['lastname']} a bien été mis à jour dans HubSpot avec son email et numéro de téléphone."
                        else:
                            self.create_contact(contact_info)
                            return f"{contact_info['firstname']} {contact_info['lastname']} a bien été ajouté dans HubSpot avec son email et numéro de téléphone."
                    except Exception as e:
                        logger.error(f"Erreur lors de la création/mise à jour rapide du contact: {str(e)}")
                        return f"❌ Erreur lors de la création du contact: {str(e)}"
                else:
                    # Commencer le processus de création étape par étape
                    self.conversation_state = 'contact_creation_start'
                    return "Je vais vous aider à créer un contact dans HubSpot. Quel est le prénom du contact ?"

            # Détecter si l'utilisateur veut rechercher un contact
            if "recherche" in text_lower and "contact" in text_lower:
                self.conversation_state = 'contact_search_start'
                return "Je vais vous aider à rechercher un contact dans HubSpot. Veuillez m'indiquer l'adresse email du contact."

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
                email = text.strip()
                self.contact_info['email'] = email
                
                # Vérifier si le contact existe déjà avant de continuer
                existing_contact = self._check_contact_exists(email)
                if existing_contact:
                    self.existing_contact = existing_contact
                    self.conversation_state = 'confirm_update'
                    firstname = existing_contact.get('properties', {}).get('firstname', 'Sans prénom')
                    lastname = existing_contact.get('properties', {}).get('lastname', 'Sans nom')
                    return f"⚠️ Un contact avec l'email {email} existe déjà (nom: {firstname} {lastname}). Souhaitez-vous mettre à jour ce contact ? Répondez par 'oui' ou 'non'."
                
                self.conversation_state = 'waiting_for_phone'
                return "Quel est le numéro de téléphone du contact ? (optionnel, appuyez sur Entrée si aucun)"
                
            elif self.conversation_state == 'confirm_update':
                if text.strip().lower() in ['oui', 'o', 'yes', 'y']:
                    # Continuer avec la mise à jour du contact existant
                    self.conversation_state = 'waiting_for_phone'
                    return "Quel est le nouveau numéro de téléphone du contact ? (optionnel, appuyez sur Entrée si inchangé)"
                else:
                    # Annuler la création/mise à jour
                    self.conversation_state = None
                    self.contact_info = {}
                    self.existing_contact = None
                    return "✅ Opération annulée. Le contact n'a pas été modifié."
                
            elif self.conversation_state == 'waiting_for_phone':
                if text.strip():
                    self.contact_info['phone'] = text.strip()
                else:
                    self.contact_info['phone'] = ""
                
                # Créer ou mettre à jour le contact dans HubSpot
                try:
                    if self.existing_contact:
                        # Mise à jour du contact existant
                        contact_id = self.existing_contact.get('id')
                        result = self.update_contact(contact_id, self.contact_info)
                        self.conversation_state = None
                        self.contact_info = {}
                        self.existing_contact = None
                        return "✅ Contact mis à jour avec succès dans HubSpot !"
                    else:
                        # Création d'un nouveau contact
                        result = self.create_contact(self.contact_info)
                        self.conversation_state = None
                        self.contact_info = {}
                        return "✅ Contact créé avec succès dans HubSpot !"
                except Exception as e:
                    logger.error(f"Erreur création/mise à jour contact HubSpot: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état pour éviter de bloquer l'utilisateur
                    self.contact_info = {}
                    self.existing_contact = None
                    return "❌ Erreur lors de la création/mise à jour du contact. Veuillez vérifier que votre intégration HubSpot est correctement configurée."

            # Gérer les étapes de recherche de contact
            if self.conversation_state == 'contact_search_start':
                email = text.strip()
                contact = self._check_contact_exists(email)
                self.conversation_state = None  # Réinitialiser l'état
                
                if not contact:
                    return f"❌ Aucun contact avec l'email {email} n'a été trouvé dans HubSpot."
                
                # Formater les informations du contact pour l'affichage
                properties = contact.get('properties', {})
                response = "👤 Contact trouvé dans HubSpot :\n\n"
                response += f"• Nom : {properties.get('firstname', 'Non spécifié')} {properties.get('lastname', 'Non spécifié')}\n"
                response += f"• Email : {properties.get('email', 'Non spécifié')}\n"
                
                if properties.get('phone'):
                    response += f"• Téléphone : {properties.get('phone')}\n"
                
                if properties.get('company'):
                    response += f"• Entreprise : {properties.get('company')}\n"
                
                if properties.get('jobtitle'):
                    response += f"• Poste : {properties.get('jobtitle')}\n"
                
                if properties.get('createdate'):
                    created_date = properties.get('createdate').split('T')[0]  # Format simple YYYY-MM-DD
                    response += f"• Créé le : {created_date}\n"
                
                return response

            return "Je peux vous aider avec HubSpot. Voici ce que je peux faire :\n" + \
                   "- Créer un nouveau contact (dites 'créer un contact')\n" + \
                   "- Rechercher un contact (dites 'rechercher un contact par email')\n" + \
                   "- Mettre à jour un contact existant"

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
    
    def _check_contact_exists(self, email):
        """Vérifie si un contact existe déjà dans HubSpot par son email"""
        try:
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("Intégration HubSpot manquante")
                return None
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("Token d'accès HubSpot manquant")
                return None
            
            # Rechercher le contact par email
            url = f"https://api.hubapi.com/crm/v3/objects/contacts/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email
                            }
                        ]
                    }
                ],
                "properties": ["email", "firstname", "lastname", "phone", "company", "jobtitle", "createdate"],
                "limit": 1
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            results = response.json().get('results', [])
            if results:
                return results[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'existence du contact: {str(e)}")
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

            # Vérifier si le contact existe déjà
            existing_contact = self._check_contact_exists(contact_info['email'])
            if existing_contact:
                logger.info(f"Contact existant trouvé pour {contact_info['email']}")
                contact_id = existing_contact.get('id')
                return self.update_contact(contact_id, contact_info)

            # Préparer les données pour HubSpot
            properties = {
                "email": contact_info['email'],
                "firstname": contact_info['firstname'],
                "lastname": contact_info['lastname']
            }
            
            # Ajouter le téléphone s'il existe
            if 'phone' in contact_info and contact_info['phone']:
                properties["phone"] = contact_info['phone']
                
            # Ajouter l'entreprise si elle existe
            if 'company' in contact_info and contact_info['company']:
                properties["company"] = contact_info['company']
                
            # Ajouter le poste si il existe
            if 'jobtitle' in contact_info and contact_info['jobtitle']:
                properties["jobtitle"] = contact_info['jobtitle']
            
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
            
            if response.status_code != 201:
                error_message = response.json().get('message', 'Erreur inconnue')
                logger.error(f"Erreur lors de la création du contact: {error_message}")
                raise Exception(f"Erreur lors de la création du contact: {error_message}")
                
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la création du contact HubSpot: {str(e)}")
            raise
    
    def update_contact(self, contact_id, contact_info):
        """Met à jour un contact existant dans HubSpot"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("Intégration HubSpot manquante")
                return "Vous n'avez pas installé cette intégration."
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("Token d'accès HubSpot manquant")
                return "Le token d'accès HubSpot est manquant. Veuillez vous connecter à HubSpot dans la section Intégrations de votre compte."

            # Préparer les données pour HubSpot
            properties = {}
            
            if 'firstname' in contact_info:
                properties["firstname"] = contact_info['firstname']
                
            if 'lastname' in contact_info:
                properties["lastname"] = contact_info['lastname']
            
            if 'phone' in contact_info and contact_info['phone']:
                properties["phone"] = contact_info['phone']
                
            if 'company' in contact_info and contact_info['company']:
                properties["company"] = contact_info['company']
                
            if 'jobtitle' in contact_info and contact_info['jobtitle']:
                properties["jobtitle"] = contact_info['jobtitle']
            
            # Mettre à jour le contact dans HubSpot
            url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "properties": properties
            }
            
            response = requests.patch(url, headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du contact HubSpot: {str(e)}")
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