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
                return "Vous n'avez pas installé cette intégration."
            
            # Machine à états pour le partage de fichiers
            if self.conversation_state == 'share_file_start':
                self.sharing_info['file_id'] = text.strip()
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
                    self.conversation_state = None  # Réinitialiser l'état
                    self.sharing_info = {}
                    return "✅ Fichier partagé avec succès !"
                except Exception as e:
                    logger.error(f"Erreur partage fichier: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return "❌ Erreur lors du partage du fichier. Veuillez vérifier que votre intégration Google Drive est correctement configurée."
            
            # Machine à états pour la création de dossier
            if self.conversation_state == 'folder_creation_start':
                self.folder_info['name'] = text.strip()
                self.conversation_state = 'waiting_for_parent'
                return "Dans quel dossier parent voulez-vous le créer ? (laissez vide pour la racine)"
                
            elif self.conversation_state == 'waiting_for_parent':
                parent_id = text.strip()
                if parent_id:
                    self.folder_info['parent_id'] = parent_id
                
                # Créer le dossier
                try:
                    result = self._create_folder(self.folder_info)
                    folder_id = result.get('id', 'inconnu')
                    self.conversation_state = None  # Réinitialiser l'état
                    self.folder_info = {}
                    return f"✅ Dossier créé avec succès ! ID du dossier : {folder_id}"
                except Exception as e:
                    logger.error(f"Erreur création dossier: {str(e)}")
                    self.conversation_state = None  # Réinitialiser l'état
                    return "❌ Erreur lors de la création du dossier. Veuillez vérifier que votre intégration Google Drive est correctement configurée."
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention de partager un fichier
            if any(phrase in text_lower for phrase in ["partager", "partage", "partage de fichier"]):
                # Vérifier si l'utilisateur a déjà fourni un ID de fichier
                file_id_match = re.search(r'\b([a-zA-Z0-9_-]{25,})\b', text)
                if file_id_match:
                    self.sharing_info['file_id'] = file_id_match.group(0)
                    self.conversation_state = 'waiting_for_email'
                    return "À quelle adresse email souhaitez-vous partager ce fichier ?"
                else:
                    self.conversation_state = 'share_file_start'
                    return "Je vais vous aider à partager un fichier. Veuillez fournir l'ID du fichier Google Drive :"
            
            # Intention de créer un dossier
            if any(phrase in text_lower for phrase in ["créer un dossier", "nouveau dossier", "créer dossier"]):
                folder_name_match = re.search(r'(?:appelé|nommé)\s+"([^"]+)"', text)
                if folder_name_match:
                    self.folder_info['name'] = folder_name_match.group(1)
                    self.conversation_state = 'waiting_for_parent'
                    return "Dans quel dossier parent voulez-vous le créer ? (laissez vide pour la racine)"
                else:
                    self.conversation_state = 'folder_creation_start'
                    return "Je vais vous aider à créer un dossier. Quel nom souhaitez-vous donner à ce dossier ?"
            
            return "Je peux vous aider avec Google Drive. Voici ce que je peux faire :\n" + \
                   "- Partager un fichier (dites 'partager un fichier')\n" + \
                   "- Créer un dossier (dites 'créer un dossier')\n" + \
                   "- Gérer les permissions d'un fichier"

        except Exception as e:
            logger.error(f"Erreur Google Drive: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _share_file(self, sharing_info):
        """Partage un fichier Google Drive en utilisant l'intégration existante"""
        from alyawebapp.integrations.google_drive.handler import GoogleDriveHandler as GoogleDriveAPI
        
        # Vérifier que tous les champs nécessaires sont présents
        required_fields = ['file_id', 'email', 'role']
        missing_fields = [field for field in required_fields if field not in sharing_info]
        if missing_fields:
            raise ValueError(f"Informations incomplètes. Champs manquants: {', '.join(missing_fields)}")
        
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
            return gdrive_handler.create_folder(
                name=folder_info['name'],
                parent_id=parent_id
            )
        else:
            return gdrive_handler.create_folder(
                name=folder_info['name']
            ) 