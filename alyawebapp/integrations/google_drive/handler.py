from ..base import BaseIntegration
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)

class GoogleDriveHandler(BaseIntegration):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    API_VERSION = 'v3'
    API_SERVICE_NAME = 'drive'
    
    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        self.credentials = self._build_credentials()
        self.service = self._build_service()

    def _build_credentials(self) -> Credentials:
        """Construit les credentials Google"""
        return Credentials(
            token=self.config.get('access_token'),
            refresh_token=self.config.get('refresh_token'),
            token_uri=self.config.get('token_uri'),
            client_id=self.config.get('client_id'),
            client_secret=self.config.get('client_secret'),
            scopes=self.SCOPES
        )

    def _build_service(self):
        """Construit le service Google Drive"""
        return build(self.API_SERVICE_NAME, self.API_VERSION, credentials=self.credentials)

    def share_file(self, file_id: str, email: str, role: str = 'reader') -> Dict[str, Any]:
        """Partage un fichier avec un utilisateur"""
        try:
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            return self.service.permissions().create(
                fileId=file_id,
                body=user_permission,
                sendNotificationEmail=True
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors du partage du fichier: {str(e)}")
            raise

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un fichier"""
        try:
            return self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,createdTime,modifiedTime,owners,size'
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du fichier: {str(e)}")
            return None

    def find_files_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Recherche des fichiers par nom"""
        try:
            # Créer une requête pour trouver les fichiers correspondant au nom
            query = f"name contains '{name}' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id,name,mimeType,createdTime,modifiedTime)',
                orderBy='modifiedTime desc'
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de fichiers: {str(e)}")
            raise

    def list_recent_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Liste les fichiers récemment modifiés"""
        try:
            results = self.service.files().list(
                orderBy='modifiedTime desc',
                pageSize=limit,
                fields='files(id,name,mimeType,createdTime,modifiedTime)',
                q="trashed=false"
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Erreur lors du listage des fichiers récents: {str(e)}")
            raise

    def get_file_permissions(self, file_id: str) -> List[Dict[str, Any]]:
        """Récupère les permissions d'un fichier"""
        try:
            permissions = self.service.permissions().list(fileId=file_id).execute()
            return permissions.get('permissions', [])
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des permissions: {str(e)}")
            raise

    def update_permission(self, file_id: str, permission_id: str, role: str) -> Dict[str, Any]:
        """Met à jour les permissions d'un utilisateur"""
        try:
            return self.service.permissions().update(
                fileId=file_id,
                permissionId=permission_id,
                body={'role': role}
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des permissions: {str(e)}")
            raise

    def create_folder(self, name: str, parent_id: str = None) -> Dict[str, Any]:
        """Crée un nouveau dossier"""
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            return self.service.files().create(
                body=file_metadata,
                fields='id,name,mimeType,webViewLink'
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier: {str(e)}")
            raise 