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
        """Gère les requêtes HubSpot"""
        try:
            # Ajouter des logs détaillés pour le diagnostic
            logger.info(f"[HUBSPOT] Début du traitement de la requête: '{message}'")
            
            # Vérifier si c'est une requête Trello
            if any(indicator in message.lower() for indicator in ["colonne", "en cours", "assigner", "assignée", "assigné", "échéance", "présentation client"]):
                logger.info(f"[HUBSPOT] Détection d'une requête Trello, redirection...")
                from .trello_handler import TrelloHandler
                trello_handler = TrelloHandler(self.orchestrator)
                return trello_handler.handle_request(message)
            
            # Vérifier si c'est une requête Slack
            if any(indicator in message.lower() for indicator in ["canal", "channel", "envoyer message", "poster", "message slack", "dm", "message direct"]):
                logger.info(f"[HUBSPOT] Détection d'une requête Slack, redirection...")
                from .slack_handler import SlackHandler
                slack_handler = SlackHandler(self.orchestrator)
                return slack_handler.handle_request(message)
            
            # Continuer avec le traitement HubSpot normal
            logger.info(f"[HUBSPOT] Traitement de la requête HubSpot")
            
            # Détecter le service le plus approprié pour cette requête
            detected_service = self._detect_service_type(message)
            logger.info(f"[AIGUILLAGE] Service détecté: {detected_service if detected_service else 'Indéterminé'}")
            
            # Si un autre service que HubSpot est détecté, essayer de rediriger
            if detected_service and detected_service != "hubspot":
                if detected_service == "trello":
                    try:
                        from .trello_handler import TrelloHandler
                        logger.info(f"[AIGUILLAGE] Redirection vers Trello: '{message}'")
                        trello_handler = TrelloHandler(self.orchestrator)
                        return trello_handler.handle_request(message)
                    except (ImportError, AttributeError) as e:
                        logger.error(f"[AIGUILLAGE] Impossible d'accéder au service Trello: {str(e)}")
                        # Message plus informatif qui permet à la conversation de continuer
                        return "Je comprends que votre demande concerne Trello, mais je ne peux pas y accéder actuellement. Vous pouvez soit reconfigurer l'intégration Trello, soit me demander autre chose. Comment puis-je vous aider autrement ?"
                
                elif detected_service == "slack":
                    try:
                        from .slack_handler import SlackHandler
                        logger.info(f"[AIGUILLAGE] Redirection vers Slack: '{message}'")
                        slack_handler = SlackHandler(self.orchestrator)
                        return slack_handler.handle_request(message)
                    except (ImportError, AttributeError) as e:
                        logger.error(f"[AIGUILLAGE] Impossible d'accéder au service Slack: {str(e)}")
                        # Message plus informatif qui permet à la conversation de continuer
                        return "Je comprends que votre demande concerne Slack, mais je ne peux pas y accéder actuellement. Vous pouvez soit reconfigurer l'intégration Slack, soit me demander autre chose. Comment puis-je vous aider autrement ?"
            
            # Début du traitement HubSpot
            logger.info("===== DÉBUT DU TRAITEMENT HUBSPOT =====")
            logger.info(f"Texte reçu: '{message}'")
            logger.info(f"État de conversation actuel: {self.conversation_state}")
                
            # Vérifier l'intégration HubSpot avant de continuer
            hubspot_integration = self._get_hubspot_integrations()
            if not hubspot_integration:
                # Si HubSpot n'est pas configuré mais la demande semble concerner un autre service
                # Essayer de rediriger vers cet autre service
                redirected_response = self._try_other_integration(message)
                if redirected_response:
                    return redirected_response
                
                # Si on arrive ici, la demande était probablement pour HubSpot mais l'intégration n'est pas disponible
                if detected_service == "hubspot":
                    return "Je comprends que votre demande concerne HubSpot (contacts, tâches, notes), mais l'intégration n'est pas configurée. Vous pouvez la configurer dans vos paramètres d'intégration. Puis-je vous aider avec autre chose ?"
                else:
                    return "Votre demande n'a pas pu être traitée car les intégrations nécessaires ne sont pas configurées. Vous pouvez configurer HubSpot, Trello ou Slack dans vos paramètres d'intégration. Comment puis-je vous aider autrement ?"
            
            # Vérifier la validité du token
            access_token = hubspot_integration.access_token or hubspot_integration.config.get('access_token')
            if access_token:
                token_valid = self._verify_token(access_token)
                logger.info(f"État du token HubSpot: {'Valide' if token_valid else 'Invalide'}")
                if not token_valid:
                    # Essayer de rafraîchir le token
                    refreshed = self._refresh_hubspot_token()
                    if not refreshed:
                        # Si HubSpot a un problème mais que la demande pourrait concerner un autre service
                        # Essayer de rediriger vers cet autre service
                        redirected_response = self._try_other_integration(message)
                        if redirected_response:
                            return redirected_response
                            
                        return "⚠️ Votre intégration HubSpot nécessite une réautorisation. Le token d'accès est expiré et n'a pas pu être rafraîchi. Veuillez vous rendre dans les paramètres d'intégration pour reconfigurer HubSpot. Puis-je vous aider avec autre chose en attendant ?"
            
            # Vérifier spécifiquement pour les emails avec partenariat potentiel
            partenariat_match = re.search(r'partenariat potentiel', message, re.IGNORECASE)
            email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', message)
            
            if partenariat_match and email_match:
                email = email_match.group(1)
                logger.info(f"DÉTECTION SPÉCIALE: {email} trouvé dans le message avec mention de partenariat potentiel")
                logger.info(f"TRAITEMENT DIRECT pour {email}")
                
                # Assurons-nous que le contact existe (ou créons-le)
                nom_match = re.search(r'pour\s+([A-Za-z]+)\s+([A-Za-z]+)', message)
                first_name = nom_match.group(1) if nom_match else ""
                last_name = nom_match.group(2) if nom_match else ""
                
                # Utiliser la nouvelle méthode pour assurer l'existence du contact
                contact = self._ensure_contact_exists(email, first_name, last_name)
                
                if contact:
                    logger.info(f"Contact trouvé ou créé: {contact.get('id')} - {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}")
                    
                    try:
                        # Créer la tâche et la note directement
                        date_info = datetime.now() + timedelta(weeks=1)
                        date_info_str = date_info.strftime("%Y-%m-%d")
                        note_content = "À contacter pour un partenariat potentiel"
                        
                        # Créer la tâche
                        task_info = {
                            'contact_id': contact.get('id'),
                            'contact_email': email,
                            'title': 'Suivi de contact',
                            'due_date': date_info_str,
                            'notes': note_content
                        }
                        logger.info(f"Tentative de création de tâche pour {email}")
                        task_result = self._create_task(task_info)
                        logger.info(f"Tâche créée avec succès: {task_result.get('id', 'Unknown')}")
                        
                        # Créer la note
                        note_info = {
                            'contact_id': contact.get('id'),
                            'contact_email': email,
                            'content': note_content
                        }
                        logger.info(f"Tentative de création de note pour {email}")
                        note_result = self._create_note(note_info)
                        logger.info(f"Note créée avec succès: {note_result.get('id', 'Unknown')}")
                        
                        # Réinitialiser l'état
                        self.conversation_state = None
                        logger.info("Réinitialisation de l'état de conversation")
                        
                        # Message standard sans distinction entre simulé et réel
                        return f"✅ J'ai planifié un suivi pour la semaine prochaine et ajouté la note 'À contacter pour un partenariat potentiel' pour {contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}."
                    except Exception as e:
                        logger.error(f"Erreur lors de la création: {str(e)}")
                        self.conversation_state = None
                        return f"❌ Erreur lors de la création du suivi et de la note: {str(e)}"
            
            # Continuer avec le reste du traitement normal
            # ... [le reste du code de handle_request reste inchangé] ...

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
            logger.info(f"[DEBUG CONTACT] Vérification de l'existence du contact pour: {email}")
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("[DEBUG CONTACT] Intégration HubSpot manquante")
                return None
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("[DEBUG CONTACT] Token d'accès HubSpot manquant")
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
            
            logger.info(f"[DEBUG CONTACT] Envoi de la requête vers {url}")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"[DEBUG CONTACT] Code de statut de la réponse: {response.status_code}")
            
            # Log du corps de la réponse pour le débogage
            try:
                response_body = response.json()
                logger.info(f"[DEBUG CONTACT] Réponse: {response_body}")
            except:
                logger.info(f"[DEBUG CONTACT] Réponse non-JSON: {response.text[:200]}")
            
            if response.status_code in [401, 403]:
                logger.error(f"[DEBUG CONTACT] Erreur d'authentification: {response.status_code}")
                # Essayer de rafraîchir le token avant d'abandonner
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    logger.info("[DEBUG CONTACT] Token rafraîchi, nouvelle tentative de vérification du contact")
                    # Récupérer le nouveau token et réessayer
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                    
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = requests.post(url, headers=headers, json=data)
                    
                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        if results:
                            logger.info(f"[DEBUG CONTACT] Contact trouvé après rafraîchissement du token: {results[0].get('id')}")
                            return results[0]
                
                raise Exception(f"Erreur d'authentification HubSpot: {response.status_code}")
                
            response.raise_for_status()
            
            results = response.json().get('results', [])
            if results:
                logger.info(f"[DEBUG CONTACT] Contact trouvé: {results[0].get('id')}")
                return results[0]
            
            logger.info(f"[DEBUG CONTACT] Aucun contact trouvé pour: {email}")
            return None
            
        except Exception as e:
            logger.error(f"[DEBUG CONTACT] Erreur lors de la vérification de l'existence du contact: {str(e)}")
            return None
    
    def extract_contact_info(self, text):
        """Extrait les informations de contact du texte"""
        # Traitement préliminaire pour les formats courants
        # Détecter un format comme "Ajoute un nouveau contact : Nom, Titre, Email, Téléphone" 
        if ":" in text:
            parts = text.split(":", 1)
            if len(parts) > 1:
                contact_text = parts[1].strip()
                
                # Essayer d'extraire directement les champs clés
                contact_info = {}
                
                # Extraire le nom complet (généralement au début)
                name_parts = contact_text.split(",")[0].strip().split()
                if len(name_parts) >= 2:
                    contact_info['firstname'] = name_parts[0]
                    contact_info['lastname'] = " ".join(name_parts[1:])
                
                # Extraire l'email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_text)
                if email_match:
                    contact_info['email'] = email_match.group(0)
                
                # Extraire le numéro de téléphone
                phone_match = re.search(r'(?:numéro|téléphone|tél)[^\d]*([\d\s\+\-\.]+)', contact_text, re.IGNORECASE)
                if phone_match:
                    contact_info['phone'] = phone_match.group(1).strip()
                
                # Extraire le titre/poste
                if "CEO" in contact_text or "ceo" in contact_text.lower():
                    contact_info['jobtitle'] = "CEO"
                else:
                    title_match = re.search(r'(?:poste|titre|fonction)[^\w]*([\w\s]+)(?:de|chez|à|,|$)', contact_text, re.IGNORECASE)
                    if title_match:
                        contact_info['jobtitle'] = title_match.group(1).strip()
                
                # Extraire l'entreprise
                company_match = re.search(r'(?:de|chez|à)\s+([\w\s]+)(?:,|$)', contact_text, re.IGNORECASE)
                if company_match:
                    contact_info['company'] = company_match.group(1).strip()
                
                # Vérifier si nous avons les champs minimum requis
                if 'firstname' in contact_info and 'lastname' in contact_info and 'email' in contact_info:
                    logger.info(f"Informations extraites par pattern matching: {contact_info}")
                    return contact_info

        # Si l'extraction directe échoue, utiliser l'IA
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

    def _verify_token(self, access_token):
        """Vérifie la validité du token HubSpot"""
        try:
            logger.info(f"[DEBUG TOKEN] Vérification de la validité du token: {access_token[:10]}... (tronqué)")
            
            # Utiliser un endpoint réel pour vérifier le token
            # Au lieu d'un endpoint incorrecte qui retourne toujours 400
            url = "https://api.hubapi.com/crm/v3/properties/contact"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            logger.info(f"[DEBUG TOKEN] Code de statut de la réponse: {response.status_code}")
            
            # Si nous obtenons 401 ou 403, le token est invalide
            if response.status_code in [401, 403]:
                # Vérifier si le message correspond à un token expiré
                try:
                    error_data = response.json()
                    logger.error(f"[DEBUG TOKEN] Token invalide: {error_data}")
                except:
                    logger.error(f"[DEBUG TOKEN] Token invalide (pas de JSON dans la réponse)")
                
                # Essayer de rafraîchir le token
                logger.info("[DEBUG TOKEN] Tentative de rafraîchissement du token...")
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    logger.info("[DEBUG TOKEN] Token rafraîchi avec succès!")
                    return True
                return False
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    logger.error(f"[DEBUG TOKEN] Erreur 400: {error_data}")
                except:
                    logger.error(f"[DEBUG TOKEN] Erreur 400 (pas de JSON dans la réponse)")
                # Continuer car 400 pourrait être une erreur de requête, pas d'authentification
            
            # Si le code est 200, le token est certainement valide
            if response.status_code == 200:
                logger.info(f"[DEBUG TOKEN] Le token est valide (code 200)")
                return True
                
            # Pour les autres codes, on considère le token comme valide mais on log l'anomalie
            logger.info(f"[DEBUG TOKEN] Le token semble valide mais code inhabituel: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"[DEBUG TOKEN] Erreur lors de la vérification du token: {str(e)}")
            # En cas d'erreur, nous supposons que le token est valide
            # pour ne pas bloquer l'utilisateur inutilement
            return True
            
    def _refresh_hubspot_token(self):
        """Rafraîchit le token HubSpot en utilisant le refresh_token s'il est disponible"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("[REFRESH TOKEN] Pas d'intégration HubSpot trouvée")
                return False
            
            # Vérifier si nous avons un refresh_token et les informations client
            config = user_integration.config
            if not isinstance(config, dict):
                logger.error("[REFRESH TOKEN] Configuration de l'intégration non valide")
                return False
            
            refresh_token = config.get('refresh_token')
            client_id = config.get('client_id')
            client_secret = config.get('client_secret')
            
            if not (refresh_token and client_id and client_secret):
                logger.error("[REFRESH TOKEN] Paramètres manquants pour le rafraîchissement du token")
                if not refresh_token:
                    logger.error("[REFRESH TOKEN] refresh_token manquant")
                if not client_id:
                    logger.error("[REFRESH TOKEN] client_id manquant")
                if not client_secret:
                    logger.error("[REFRESH TOKEN] client_secret manquant")
                return False
            
            # Faire l'appel API à HubSpot pour rafraîchir le token
            url = "https://api.hubapi.com/oauth/v1/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
            
            logger.info("[REFRESH TOKEN] Envoi de la requête de rafraîchissement du token")
            response = requests.post(url, data=data)
            
            if response.status_code != 200:
                logger.error(f"[REFRESH TOKEN] Échec du rafraîchissement du token: {response.status_code} - {response.text}")
                return False
            
            # Extraire les nouvelles valeurs de token
            token_data = response.json()
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token')  # HubSpot fournit aussi un nouveau refresh_token
            
            if not new_access_token:
                logger.error("[REFRESH TOKEN] Pas d'access_token dans la réponse")
                return False
            
            # Mise à jour des informations de token dans la base de données
            config['access_token'] = new_access_token
            if new_refresh_token:
                config['refresh_token'] = new_refresh_token
            
            user_integration.config = config
            user_integration.access_token = new_access_token
            user_integration.save()
            
            logger.info("[REFRESH TOKEN] Token rafraîchi et sauvegardé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"[REFRESH TOKEN] Erreur lors du rafraîchissement du token: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"[REFRESH TOKEN] Traceback: {traceback.format_exc()}")
            return False
            
    def _parse_date(self, date_text):
        """Analyse un texte décrivant une date et le convertit en date formatée"""
        try:
            date_text = date_text.lower().strip()
            
            from datetime import datetime, timedelta
            import re
            
            # Date actuelle comme point de départ
            today = datetime.now()
            
            # Gérer les formats relatifs courants
            if "semaine" in date_text:
                match = re.search(r'(\d+)\s*semaine', date_text)
                if match:
                    weeks = int(match.group(1))
                else:
                    weeks = 1
                target_date = today + timedelta(weeks=weeks)
                return target_date.strftime("%Y-%m-%d")
                
            elif "jour" in date_text or "jour" in date_text:
                match = re.search(r'(\d+)\s*jour', date_text)
                if match:
                    days = int(match.group(1))
                else:
                    days = 1
                target_date = today + timedelta(days=days)
                return target_date.strftime("%Y-%m-%d")
                
            elif "demain" in date_text:
                target_date = today + timedelta(days=1)
                return target_date.strftime("%Y-%m-%d")
                
            elif "mois" in date_text:
                match = re.search(r'(\d+)\s*mois', date_text)
                if match:
                    months = int(match.group(1))
                else:
                    months = 1
                    
                # Estimation simple - pas 100% précis pour tous les mois
                target_date = today + timedelta(days=30*months)
                return target_date.strftime("%Y-%m-%d")
                
            # Essayer de détecter une date précise
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', date_text)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = date_match.group(3)
                if year:
                    year = int(year)
                    if year < 100:  # Gérer les années à 2 chiffres
                        year += 2000
                else:
                    year = today.year
                    
                try:
                    target_date = datetime(year, month, day)
                    return target_date.strftime("%Y-%m-%d")
                except ValueError:
                    # Date invalide
                    return None
                    
            # Détecter les noms de mois en français
            months_fr = {
                'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
            }
            
            for month_name, month_num in months_fr.items():
                if month_name in date_text:
                    day_match = re.search(r'(\d{1,2})\s*' + month_name, date_text) or re.search(month_name + r'\s*(\d{1,2})', date_text)
                    if day_match:
                        day = int(day_match.group(1))
                        year_match = re.search(r'(\d{4})', date_text)
                        year = int(year_match.group(1)) if year_match else today.year
                        
                        try:
                            target_date = datetime(year, month_num, day)
                            return target_date.strftime("%Y-%m-%d")
                        except ValueError:
                            return None
            
            # Si aucun format n'a été reconnu, par défaut à une semaine
            if "suivi" in date_text or "rappel" in date_text:
                target_date = today + timedelta(weeks=1)
                return target_date.strftime("%Y-%m-%d")
                
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la date: {str(e)}")
            # Par défaut, une semaine plus tard
            target_date = datetime.now() + timedelta(weeks=1)
            return target_date.strftime("%Y-%m-%d")
            
    def _create_task(self, task_info):
        """Crée une tâche dans HubSpot"""
        try:
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                raise ValueError("Intégration HubSpot manquante")
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                raise ValueError("Token d'accès HubSpot manquant")
                
            # Vérifier la validité du token
            token_valid = self._verify_token(access_token)
            if not token_valid:
                # Essayer de rafraîchir le token
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    # Récupérer le nouveau token
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                else:
                    raise ValueError("Le token HubSpot est invalide et n'a pas pu être rafraîchi")

            # Créer la tâche dans HubSpot
            url = "https://api.hubapi.com/crm/v3/objects/tasks"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Préparer les données de la tâche
            properties = {
                "hs_task_subject": task_info.get('title', 'Suivi de contact'),
                "hs_task_body": task_info.get('notes', ''),
                "hs_task_priority": "HIGH",
                "hs_task_status": "NOT_STARTED",
                "hs_task_type": "CALL",
            }
            
            # Ajouter la date d'échéance si elle est présente
            if 'due_date' in task_info:
                properties["hs_task_due_date"] = task_info['due_date']
                
            data = {
                "properties": properties
            }
            
            # Ajouter la relation avec le contact
            if 'contact_id' in task_info:
                data["associations"] = [
                    {
                        "to": {
                            "id": task_info['contact_id']
                        },
                        "types": [
                            {
                                "category": "TASK_CONTACT",
                                "typeId": 1
                            }
                        ]
                    }
                ]
            
            logger.info(f"[DEBUG TASK] Envoi de la requête pour créer une tâche: {data}")
            response = requests.post(url, headers=headers, json=data)
            
            # Log de la réponse pour le débogage
            try:
                response_content = response.json()
                logger.info(f"[DEBUG TASK] Réponse de création de tâche (code: {response.status_code}): {response_content}")
            except:
                logger.info(f"[DEBUG TASK] Réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
            
            # Si on a une erreur d'authentification, essayer de rafraîchir le token
            if response.status_code in [401, 403]:
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    logger.info("[DEBUG TASK] Token rafraîchi, nouvelle tentative de création de tâche")
                    # Récupérer le nouveau token et réessayer
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                    
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = requests.post(url, headers=headers, json=data)
                    
                    # Log de la seconde réponse
                    try:
                        response_content = response.json()
                        logger.info(f"[DEBUG TASK] Seconde réponse après rafraîchissement (code: {response.status_code}): {response_content}")
                    except:
                        logger.info(f"[DEBUG TASK] Seconde réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
            
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche: {str(e)}")
            raise
            
    def _create_note(self, note_info):
        """Crée une note dans HubSpot"""
        try:
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                raise ValueError("Intégration HubSpot manquante")
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                raise ValueError("Token d'accès HubSpot manquant")
            
            # Vérifier la validité du token
            token_valid = self._verify_token(access_token)
            if not token_valid:
                # Essayer de rafraîchir le token
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    # Récupérer le nouveau token
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                else:
                    raise ValueError("Le token HubSpot est invalide et n'a pas pu être rafraîchi")

            # Créer la note dans HubSpot
            url = "https://api.hubapi.com/crm/v3/objects/notes"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Préparer les données de la note
            properties = {
                "hs_note_body": note_info.get('content', 'Note ajoutée par Alya'),
                "hs_timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
                
            data = {
                "properties": properties
            }
            
            # Ajouter la relation avec le contact
            if 'contact_id' in note_info:
                data["associations"] = [
                    {
                        "to": {
                            "id": note_info['contact_id']
                        },
                        "types": [
                            {
                                "category": "NOTE_CONTACT",
                                "typeId": 1
                            }
                        ]
                    }
                ]
            
            logger.info(f"[DEBUG NOTE] Envoi de la requête pour créer une note: {data}")
            response = requests.post(url, headers=headers, json=data)
            
            # Log de la réponse pour le débogage
            try:
                response_content = response.json()
                logger.info(f"[DEBUG NOTE] Réponse de création de note (code: {response.status_code}): {response_content}")
            except:
                logger.info(f"[DEBUG NOTE] Réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
            
            # Si on a une erreur d'authentification, essayer de rafraîchir le token
            if response.status_code in [401, 403]:
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    logger.info("[DEBUG NOTE] Token rafraîchi, nouvelle tentative de création de note")
                    # Récupérer le nouveau token et réessayer
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                    
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = requests.post(url, headers=headers, json=data)
                    
                    # Log de la seconde réponse
                    try:
                        response_content = response.json()
                        logger.info(f"[DEBUG NOTE] Seconde réponse après rafraîchissement (code: {response.status_code}): {response_content}")
                    except:
                        logger.info(f"[DEBUG NOTE] Seconde réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
            
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la note: {str(e)}")
            raise

    def _diagnostic_log_message(self, text):
        """Ajoute des logs de diagnostic détaillés pour comprendre le traitement d'un message"""
        logger.info("[DIAGNOSTIC] Début du diagnostic de message")
        logger.info(f"[DIAGNOSTIC] Texte complet: '{text}'")
        
        # Vérification de l'état de conversation
        logger.info(f"[DIAGNOSTIC] État de conversation actuel: {self.conversation_state}")
        
        # Détection d'email
        email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_matches:
            logger.info(f"[DIAGNOSTIC] Emails trouvés: {email_matches}")
            
            # Pour chaque email trouvé, vérifier si le contact existe
            for email in email_matches:
                logger.info(f"[DIAGNOSTIC] Vérification de l'existence du contact pour: {email}")
                contact = self._check_contact_exists(email)
                if contact:
                    logger.info(f"[DIAGNOSTIC] Contact trouvé: ID={contact.get('id')}, Nom={contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}")
                else:
                    logger.info(f"[DIAGNOSTIC] Aucun contact trouvé pour l'email: {email}")
        else:
            logger.info("[DIAGNOSTIC] Aucun email trouvé dans le message")
            
        # Vérification du JSON
        try:
            if text.strip().startswith('{') and text.strip().endswith('}'):
                json_data = json.loads(text.strip())
                logger.info(f"[DIAGNOSTIC] Structure JSON valide trouvée: {json_data}")
                
                # Analyser le JSON pour déterminer son type
                if 'intent' in json_data:
                    logger.info(f"[DIAGNOSTIC] Intent détecté: {json_data.get('intent')}")
                if 'raw_response' in json_data:
                    logger.info(f"[DIAGNOSTIC] Raw response trouvée: {json_data.get('raw_response')}")
            
                # Vérifier si du texte précède le JSON
                parts = text.split('{', 1)
                if len(parts) > 1 and parts[0].strip():
                    logger.info(f"[DIAGNOSTIC] Texte précédant le JSON: '{parts[0].strip()}'")
                    
                    # Re-vérifier pour des emails dans cette partie
                    pre_json_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', parts[0])
                    if pre_json_emails:
                        logger.info(f"[DIAGNOSTIC] Emails trouvés avant le JSON: {pre_json_emails}")
                    else:
                        logger.info("[DIAGNOSTIC] Aucun email trouvé avant le JSON")
        except json.JSONDecodeError:
            logger.info("[DIAGNOSTIC] Structure qui ressemble à du JSON mais n'est pas valide")
        except Exception as e:
            logger.info(f"[DIAGNOSTIC] Erreur lors de l'analyse JSON: {str(e)}")
        
        # Vérification si le texte contient des mots clés spécifiques
        keywords = ["partenariat", "potentiel", "suivi", "note", "programme", "ajoute"]
        found_keywords = [keyword for keyword in keywords if keyword in text.lower()]
        if found_keywords:
            logger.info(f"[DIAGNOSTIC] Mots-clés trouvés: {found_keywords}")
        else:
            logger.info("[DIAGNOSTIC] Aucun mot-clé pertinent trouvé")
            
        # Vérification de l'intégration HubSpot
        hubspot_integration = self._get_hubspot_integrations()
        if hubspot_integration:
            logger.info("[DIAGNOSTIC] Intégration HubSpot trouvée")
            access_token = hubspot_integration.access_token or hubspot_integration.config.get('access_token')
            if access_token:
                logger.info("[DIAGNOSTIC] Access token présent")
                token_valid = self._verify_token(access_token)
                logger.info(f"[DIAGNOSTIC] Token valide: {'Oui' if token_valid else 'Non'}")
            else:
                logger.info("[DIAGNOSTIC] Pas d'access token trouvé")
        else:
            logger.info("[DIAGNOSTIC] Aucune intégration HubSpot trouvée pour cet utilisateur")
            
        logger.info("[DIAGNOSTIC] Fin du diagnostic de message") 

    def _ensure_contact_exists(self, email, first_name="", last_name="", company=""):
        """Vérifie si un contact existe et le crée si nécessaire"""
        try:
            logger.info(f"[DEBUG ENSURE_CONTACT] Vérification du contact: {email}")
            
            # Vérifier si le contact existe déjà
            contact = self._check_contact_exists(email)
            if contact:
                logger.info(f"[DEBUG ENSURE_CONTACT] Contact existant trouvé: {contact.get('id')}")
                return contact
                
            # Contact n'existe pas, le créer
            logger.info(f"[DEBUG ENSURE_CONTACT] Contact non trouvé, création d'un nouveau contact pour: {email}")
            
            # Récupérer l'intégration HubSpot active
            user_integration = self._get_hubspot_integrations()
            
            if not user_integration:
                logger.error("[DEBUG ENSURE_CONTACT] Intégration HubSpot manquante")
                return None
            
            # Récupérer le token HubSpot
            access_token = user_integration.access_token or user_integration.config.get('access_token')
            
            if not access_token:
                logger.error("[DEBUG ENSURE_CONTACT] Token d'accès HubSpot manquant")
                return None
                
            # Vérifier la validité du token
            token_valid = self._verify_token(access_token)
            if not token_valid:
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                else:
                    logger.error("[DEBUG ENSURE_CONTACT] Token invalide et non rafraîchissable")
                    return None
                
            # Créer le contact
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Préparer les données du contact
            properties = {
                "email": email,
            }
            
            # Ajouter les champs supplémentaires s'ils sont fournis
            if first_name:
                properties["firstname"] = first_name
            if last_name:
                properties["lastname"] = last_name
            if company:
                properties["company"] = company
                
            data = {
                "properties": properties
            }
            
            logger.info(f"[DEBUG ENSURE_CONTACT] Envoi de la requête de création de contact: {data}")
            response = requests.post(url, headers=headers, json=data)
            
            # Log de la réponse pour le débogage
            try:
                response_content = response.json()
                logger.info(f"[DEBUG ENSURE_CONTACT] Réponse de création de contact (code: {response.status_code}): {response_content}")
            except:
                logger.info(f"[DEBUG ENSURE_CONTACT] Réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
                
            # Gestion des erreurs d'authentification
            if response.status_code in [401, 403]:
                refreshed = self._refresh_hubspot_token()
                if refreshed:
                    logger.info("[DEBUG ENSURE_CONTACT] Token rafraîchi, nouvelle tentative de création de contact")
                    user_integration = self._get_hubspot_integrations()
                    access_token = user_integration.access_token or user_integration.config.get('access_token')
                    
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = requests.post(url, headers=headers, json=data)
                    
                    try:
                        response_content = response.json()
                        logger.info(f"[DEBUG ENSURE_CONTACT] Seconde réponse après rafraîchissement (code: {response.status_code}): {response_content}")
                    except:
                        logger.info(f"[DEBUG ENSURE_CONTACT] Seconde réponse non-JSON (code: {response.status_code}): {response.text[:200]}")
            
            response.raise_for_status()
            
            # Contact créé avec succès
            new_contact = response.json()
            logger.info(f"[DEBUG ENSURE_CONTACT] Contact créé avec succès: {new_contact.get('id')}")
            
            # Rechercher le contact complet pour avoir toutes les propriétés
            return self._check_contact_exists(email)
            
        except Exception as e:
            logger.error(f"[DEBUG ENSURE_CONTACT] Erreur lors de la création du contact: {str(e)}")
            return None

    def _try_other_integration(self, text):
        """Tente de traiter la demande via une autre intégration disponible"""
        logger.info(f"[REDIRECTION] Tentative de redirection de la requête: '{text}'")
        
        # Utiliser notre fonction de détection pour déterminer le service le plus approprié
        detected_service = self._detect_service_type(text)
        
        if detected_service == "hubspot":
            # Si la détection indique que c'est une demande HubSpot, ne pas rediriger
            logger.info(f"[REDIRECTION] La requête semble concerner HubSpot, pas de redirection")
            return None
        
        if detected_service == "trello":
            # Essayer Trello en priorité si détecté
            try:
                from .trello_handler import TrelloHandler
                logger.info(f"[REDIRECTION] Redirection vers Trello: '{text}'")
                trello_handler = TrelloHandler(self.orchestrator)
                return trello_handler.handle_request(text)
            except (ImportError, AttributeError) as e:
                logger.error(f"[REDIRECTION] Échec de redirection vers Trello: {str(e)}")
        
        elif detected_service == "slack":
            # Essayer Slack en priorité si détecté
            try:
                from .slack_handler import SlackHandler
                logger.info(f"[REDIRECTION] Redirection vers Slack: '{text}'")
                slack_handler = SlackHandler(self.orchestrator)
                return slack_handler.handle_request(text)
            except (ImportError, AttributeError) as e:
                logger.error(f"[REDIRECTION] Échec de redirection vers Slack: {str(e)}")
        
        # Si la détection n'a pas identifié le service ou si la redirection a échoué,
        # essayer les autres services par défaut (fallback)
        if detected_service != "trello":
            # Essayer Trello comme plan B
            try:
                from .trello_handler import TrelloHandler
                logger.info(f"[REDIRECTION] Tentative sur Trello (fallback): '{text}'")
                trello_handler = TrelloHandler(self.orchestrator)
                return trello_handler.handle_request(text)
            except (ImportError, AttributeError) as e:
                logger.error(f"[REDIRECTION] Échec du fallback vers Trello: {str(e)}")
        
        if detected_service != "slack":
            # Essayer Slack comme plan C
            try:
                from .slack_handler import SlackHandler
                logger.info(f"[REDIRECTION] Tentative sur Slack (fallback): '{text}'")
                slack_handler = SlackHandler(self.orchestrator)
                return slack_handler.handle_request(text)
            except (ImportError, AttributeError) as e:
                logger.error(f"[REDIRECTION] Échec du fallback vers Slack: {str(e)}")
        
        # Si aucune redirection n'a fonctionné, retourner None
        logger.info(f"[REDIRECTION] Aucune redirection n'a fonctionné pour: '{text}'")
        return None

    def _detect_service_type(self, text):
        """Détecte le type de service le plus approprié pour traiter cette requête"""
        text_lower = text.lower()
        
        # Définir des mots-clés et phrases spécifiques à chaque service
        service_keywords = {
            "hubspot": [
                "contact", "suivi", "note", "tâche hubspot", "partenariat", "client hubspot", 
                "ajouter contact", "créer contact", "mettre à jour contact", "email"
            ],
            "trello": [
                "carte", "tâche trello", "colonne", "liste", "board", "tableau", "étiquette",
                "déplacer carte", "ajouter carte", "créer carte", "assigner", "en cours",
                "présentation client", "assigner à", "assignée à", "assigné à", "échéance",
                "vendredi", "lundi", "mardi", "mercredi", "jeudi", "samedi", "dimanche"
            ],
            "slack": [
                "canal", "channel", "envoyer message", "poster", "message slack", 
                "dm", "message direct", "réaction", "émoji"
            ]
        }
        
        # Calculer les scores pour chaque service
        scores = {service: 0 for service in service_keywords}
        
        # Vérifier d'abord les mots-clés spécifiques à Trello qui sont plus probables
        trello_indicators = ["colonne", "en cours", "assigner", "assignée", "assigné", "échéance"]
        if any(indicator in text_lower for indicator in trello_indicators):
            logger.info(f"[DETECTION] Indicateurs Trello forts détectés dans: '{text}'")
            return "trello"
        
        for service, keywords in service_keywords.items():
            # Donner un score de base si le nom du service est explicitement mentionné
            if service in text_lower:
                scores[service] += 3
            
            # Ajouter des points pour chaque mot-clé trouvé
            for keyword in keywords:
                if keyword in text_lower:
                    scores[service] += 1
        
        # Déterminer le service avec le score le plus élevé
        best_service = max(scores, key=scores.get)
        best_score = scores[best_service]
        
        # Si le meilleur score est 0, aucun service n'est clairement indiqué
        if best_score == 0:
            logger.info(f"[DETECTION] Aucun service clairement identifié pour: '{text}'")
            return None
        
        logger.info(f"[DETECTION] Service le plus adapté: {best_service} (score: {best_score}) pour: '{text}'")
        return best_service