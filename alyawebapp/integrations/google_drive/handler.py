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
                fields='id'
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier: {str(e)}")
            raise 