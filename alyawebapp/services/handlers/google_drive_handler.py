import logging
import json
import re
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    """Gestionnaire pour les intégrations Google Drive"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.sharing_info = {}
        self.folder_info = {}
        self.gdrive_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Google Drive si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='google drive')
            self.gdrive_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.gdrive_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à Google Drive"""
        try:
            if not self.gdrive_integration:
                return "Vous n'avez pas installé cette intégration. Veuillez configurer Google Drive dans vos intégrations avant de l'utiliser."
            
            # Machine à états pour le partage de fichiers
            if self.conversation_state == 'share_file_start':
                file_id = text.strip()
                self.sharing_info['file_id'] = file_id
                
                # Vérifier si le fichier existe
                file_exists = self._verify_file_exists(file_id)
                if not file_exists:
                    self.conversation_state = None
                    self.sharing_info = {}
                    return "❌ Le fichier spécifié n'existe pas ou vous n'avez pas les permissions nécessaires pour y accéder. Veuillez vérifier l'ID du fichier."
                
                # Récupérer les infos du fichier pour une confirmation claire
                file_info = self._get_file_info(file_id)
                if file_info:
                    file_name = file_info.get('name', 'Fichier inconnu')
                    file_type = file_info.get('mimeType', '').split('.')[-1]
                    self.sharing_info['file_name'] = file_name
                    
                    self.conversation_state = 'waiting_for_email'
                    return f"Je vais partager le fichier '{file_name}' ({file_type}). À quelle adresse email souhaitez-vous le partager ?"
                else:
                    self.conversation_state = 'waiting_for_email'
                    return "À quelle adresse email souhaitez-vous partager ce fichier ?"
                
            elif self.conversation_state == 'waiting_for_email':
                self.sharing_info['email'] = text.strip()
                self.conversation_state = 'waiting_for_role'
                return "Quel rôle souhaitez-vous attribuer ? (lecteur, commentateur, éditeur)"
                
            elif self.conversation_state == 'waiting_for_role':
                role = text.strip().lower()
                # Convertir le texte en rôle Google Drive
                role_mapping = {
                    'lecteur': 'reader',
                    'commentateur': 'commenter', 
                    'éditeur': 'writer'
                }
                self.sharing_info['role'] = role_mapping.get(role, 'reader')
                
                # Effectuer le partage
                try:
                    result = self._share_file(self.sharing_info)
                    file_name = self.sharing_info.get('file_name', 'Le fichier')
                    email = self.sharing_info.get('email')
                    role_fr = {'reader': 'lecteur', 'commenter': 'commentateur', 'writer': 'éditeur'}.get(self.sharing_info['role'], 'lecteur')
                    
                    self.conversation_state = None  # Réinitialiser l'état
                    self.sharing_info = {}
                    return f"✅ {file_name} a été partagé avec {email} en tant que {role_fr} !"
                except Exception as e:
                    logger.error(f"Erreur partage fichier: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return f"❌ Erreur lors du partage du fichier: {str(e)}"
            
            # Machine à états pour la création de dossier
            if self.conversation_state == 'folder_creation_start':
                self.folder_info['name'] = text.strip()
                self.conversation_state = 'waiting_for_parent'
                return "Dans quel dossier parent voulez-vous le créer ? (laissez vide pour la racine, ou indiquez l'ID du dossier parent)"
                
            elif self.conversation_state == 'waiting_for_parent':
                parent_id = text.strip()
                if parent_id:
                    # Vérifier si le dossier parent existe
                    parent_exists = self._verify_file_exists(parent_id)
                    if not parent_exists:
                        self.conversation_state = None
                        self.folder_info = {}
                        return "❌ Le dossier parent spécifié n'existe pas ou vous n'avez pas les permissions nécessaires. Le dossier n'a pas été créé."
                    
                    self.folder_info['parent_id'] = parent_id
                
                # Créer le dossier
                try:
                    result = self._create_folder(self.folder_info)
                    folder_id = result.get('id', 'inconnu')
                    folder_name = self.folder_info.get('name')
                    self.conversation_state = None  # Réinitialiser l'état
                    self.folder_info = {}
                    return f"✅ Dossier '{folder_name}' créé avec succès ! ID du dossier : {folder_id}"
                except Exception as e:
                    logger.error(f"Erreur création dossier: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return f"❌ Erreur lors de la création du dossier: {str(e)}"
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention de partager un fichier
            if any(phrase in text_lower for phrase in ["partager", "partage", "partage de fichier"]):
                # Vérifier si l'utilisateur a déjà fourni un ID de fichier
                file_id_match = re.search(r'\b([a-zA-Z0-9_-]{25,})\b', text)
                file_name_match = re.search(r'(?:fichier|document)\s+["\']([^"\']+)["\']', text)
                
                if file_id_match:
                    file_id = file_id_match.group(0)
                    # Vérifier si le fichier existe avant de commencer le processus
                    file_exists = self._verify_file_exists(file_id)
                    if not file_exists:
                        return "❌ Le fichier spécifié n'existe pas ou vous n'avez pas les permissions nécessaires. Veuillez vérifier l'ID du fichier."
                    
                    # Vérifier si l'utilisateur a déjà mentionné un email
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    if email_match:
                        email = email_match.group(0)
                        self.sharing_info = {
                            'file_id': file_id,
                            'email': email
                        }
                        
                        # Vérifier si un rôle est spécifié
                        if "lecteur" in text_lower:
                            self.sharing_info['role'] = 'reader'
                            return self._handle_direct_sharing()
                        elif "commentateur" in text_lower or "commenter" in text_lower:
                            self.sharing_info['role'] = 'commenter'
                            return self._handle_direct_sharing()
                        elif "éditeur" in text_lower or "editor" in text_lower or "modif" in text_lower:
                            self.sharing_info['role'] = 'writer'
                            return self._handle_direct_sharing()
                        else:
                            self.conversation_state = 'waiting_for_role'
                            file_info = self._get_file_info(file_id)
                            file_name = file_info.get('name', 'Le fichier') if file_info else 'Le fichier'
                            self.sharing_info['file_name'] = file_name
                            return f"Quel rôle souhaitez-vous attribuer à {email} pour le fichier '{file_name}' ? (lecteur, commentateur, éditeur)"
                    else:
                        self.sharing_info['file_id'] = file_id
                        file_info = self._get_file_info(file_id)
                        if file_info:
                            file_name = file_info.get('name', 'Fichier inconnu')
                            file_type = file_info.get('mimeType', '').split('.')[-1]
                            self.sharing_info['file_name'] = file_name
                            
                            self.conversation_state = 'waiting_for_email'
                            return f"Je vais vous aider à partager le fichier '{file_name}' ({file_type}). À quelle adresse email souhaitez-vous le partager ?"
                        else:
                            self.conversation_state = 'waiting_for_email'
                            return "À quelle adresse email souhaitez-vous partager ce fichier ?"
                
                elif file_name_match:
                    # L'utilisateur a indiqué un nom plutôt qu'un ID
                    file_name = file_name_match.group(1)
                    # Nous devons chercher le fichier par son nom
                    matching_files = self._find_files_by_name(file_name)
                    
                    if not matching_files:
                        return f"❌ Aucun fichier nommé '{file_name}' n'a été trouvé dans votre Google Drive. Veuillez vérifier le nom du fichier."
                    
                    if len(matching_files) == 1:
                        # Un seul fichier trouvé, on le sélectionne automatiquement
                        file = matching_files[0]
                        file_id = file.get('id')
                        file_name = file.get('name')
                        self.sharing_info['file_id'] = file_id
                        self.sharing_info['file_name'] = file_name
                        
                        # Vérifier si l'utilisateur a déjà mentionné un email
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                        if email_match:
                            email = email_match.group(0)
                            self.sharing_info['email'] = email
                            
                            # Vérifier si un rôle est spécifié
                            if "lecteur" in text_lower:
                                self.sharing_info['role'] = 'reader'
                                return self._handle_direct_sharing()
                            elif "commentateur" in text_lower or "commenter" in text_lower:
                                self.sharing_info['role'] = 'commenter'
                                return self._handle_direct_sharing()
                            elif "éditeur" in text_lower or "editor" in text_lower or "modif" in text_lower:
                                self.sharing_info['role'] = 'writer'
                                return self._handle_direct_sharing()
                            else:
                                self.conversation_state = 'waiting_for_role'
                                return f"Quel rôle souhaitez-vous attribuer à {email} pour le fichier '{file_name}' ? (lecteur, commentateur, éditeur)"
                        else:
                            self.conversation_state = 'waiting_for_email'
                            return f"Je vais vous aider à partager le fichier '{file_name}'. À quelle adresse email souhaitez-vous le partager ?"
                    else:
                        # Plusieurs fichiers trouvés, demander à l'utilisateur de choisir
                        response = f"J'ai trouvé plusieurs fichiers nommés '{file_name}':\n\n"
                        for i, file in enumerate(matching_files[:5], 1):  # Limiter à 5 résultats
                            file_type = file.get('mimeType', '').split('.')[-1]
                            response += f"{i}. {file.get('name')} ({file_type}) - ID: {file.get('id')}\n"
                        
                        if len(matching_files) > 5:
                            response += f"\nEt {len(matching_files) - 5} autres fichiers...\n"
                            
                        response += "\nVeuillez préciser l'ID du fichier que vous souhaitez partager."
                        return response
                
                else:
                    self.conversation_state = 'share_file_start'
                    return "Je vais vous aider à partager un fichier. Veuillez fournir l'ID du fichier Google Drive :"
            
            # Intention de créer un dossier
            if any(phrase in text_lower for phrase in ["créer un dossier", "nouveau dossier", "créer dossier"]):
                folder_name_match = re.search(r'(?:appelé|nommé)\s+"([^"]+)"', text)
                if folder_name_match:
                    self.folder_info['name'] = folder_name_match.group(1)
                    self.conversation_state = 'waiting_for_parent'
                    return "Dans quel dossier parent voulez-vous le créer ? (laissez vide pour la racine, ou indiquez l'ID du dossier parent)"
                else:
                    self.conversation_state = 'folder_creation_start'
                    return "Je vais vous aider à créer un dossier. Quel nom souhaitez-vous donner à ce dossier ?"
            
            # Intention de lister les fichiers
            if any(phrase in text_lower for phrase in ["liste mes fichiers", "affiche mes fichiers", "montre mes fichiers"]):
                try:
                    files = self._list_recent_files(10)  # Limiter à 10 fichiers
                    if not files:
                        return "❌ Je n'ai pas pu récupérer vos fichiers récents ou vous n'avez pas de fichiers."
                    
                    response = "📄 Voici vos fichiers Google Drive récents :\n\n"
                    for file in files:
                        file_name = file.get('name', 'Sans nom')
                        file_id = file.get('id', 'ID inconnu')
                        file_type = file.get('mimeType', '').split('.')[-1]
                        response += f"• {file_name} ({file_type})\n  ID: {file_id}\n\n"
                    
                    return response
                except Exception as e:
                    logger.error(f"Erreur lors du listage des fichiers: {str(e)}")
                    return f"❌ Erreur lors de la récupération des fichiers: {str(e)}"
            
            return "Je peux vous aider avec Google Drive. Voici ce que je peux faire :\n" + \
                   "- Partager un fichier (dites 'partager un fichier')\n" + \
                   "- Créer un dossier (dites 'créer un dossier')\n" + \
                   "- Lister vos fichiers récents (dites 'liste mes fichiers')"

        except Exception as e:
            logger.error(f"Erreur Google Drive: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return f"❌ Une erreur est survenue lors de l'exécution de votre demande: {str(e)}. Veuillez réessayer."
    
    def _verify_file_exists(self, file_id):
        """Vérifie si un fichier existe et est accessible"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        try:
            gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
            file_info = gdrive_handler.get_file_info(file_id)
            return file_info is not None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du fichier: {str(e)}")
            return False
    
    def _get_file_info(self, file_id):
        """Récupère les informations d'un fichier Google Drive"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        try:
            gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
            return gdrive_handler.get_file_info(file_id)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations du fichier: {str(e)}")
            return None
    
    def _find_files_by_name(self, file_name):
        """Recherche des fichiers par nom"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        try:
            gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
            return gdrive_handler.find_files_by_name(file_name)
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de fichiers: {str(e)}")
            return []
    
    def _list_recent_files(self, limit=10):
        """Liste les fichiers récents"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        try:
            gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
            return gdrive_handler.list_recent_files(limit)
        except Exception as e:
            logger.error(f"Erreur lors du listage des fichiers récents: {str(e)}")
            return []
    
    def _handle_direct_sharing(self):
        """Gère le partage direct à partir des informations déjà collectées"""
        try:
            result = self._share_file(self.sharing_info)
            file_name = self.sharing_info.get('file_name', 'Le fichier')
            email = self.sharing_info.get('email')
            role_fr = {'reader': 'lecteur', 'commenter': 'commentateur', 'writer': 'éditeur'}.get(self.sharing_info['role'], 'lecteur')
            
            self.conversation_state = None  # Réinitialiser l'état
            self.sharing_info = {}
            return f"✅ {file_name} a été partagé avec {email} en tant que {role_fr} !"
        except Exception as e:
            logger.error(f"Erreur partage fichier: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état
            self.sharing_info = {}
            return f"❌ Erreur lors du partage du fichier: {str(e)}"
    
    def _share_file(self, sharing_info):
        """Partage un fichier Google Drive en utilisant l'intégration existante"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['file_id', 'email', 'role']
        missing_fields = [field for field in required_fields if field not in sharing_info or not sharing_info[field]]
        
        if missing_fields:
            error_messages = {
                'file_id': "L'ID du fichier n'a pas été spécifié. Veuillez indiquer quel fichier partager.",
                'email': "L'adresse email du destinataire n'a pas été spécifiée. Veuillez indiquer avec qui partager le fichier.",
                'role': "Le rôle du destinataire n'a pas été spécifié. Veuillez choisir entre 'lecteur', 'commentateur' ou 'éditeur'."
            }
            error_msg = " ".join([error_messages[field] for field in missing_fields])
            raise ValueError(error_msg)
        
        # Vérifier à nouveau si le fichier existe
        if not self._verify_file_exists(sharing_info['file_id']):
            raise ValueError(f"Le fichier avec l'ID {sharing_info['file_id']} n'existe pas ou vous n'avez pas les permissions nécessaires.")
        
        # Utiliser l'implémentation existante
        gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
        return gdrive_handler.share_file(
            file_id=sharing_info['file_id'],
            email=sharing_info['email'],
            role=sharing_info['role']
        )
    
    def _create_folder(self, folder_info):
        """Crée un dossier Google Drive en utilisant l'intégration existante"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        if 'name' not in folder_info:
            raise ValueError("Le nom du dossier est requis")
        
        # Utiliser l'implémentation existante
        gdrive_handler = GoogleDriveAPI(self.gdrive_integration.config)
        parent_id = folder_info.get('parent_id')
        
        if parent_id:
            # Vérifier à nouveau si le dossier parent existe
            if not self._verify_file_exists(parent_id):
                raise ValueError(f"Le dossier parent avec l'ID {parent_id} n'existe pas ou vous n'avez pas les permissions nécessaires.")
                
            return gdrive_handler.create_folder(
                name=folder_info['name'],
                parent_id=parent_id
            )
        else:
            return gdrive_handler.create_folder(
                name=folder_info['name']
            ) 