import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io

logger = logging.getLogger(__name__)

class GoogleDriveManager:
    @classmethod
    def share_file(cls, user_integration, file_id, email, role='reader'):
        """Partage un fichier avec un utilisateur"""
        try:
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/drive.file']
            )
            
            service = build('drive', 'v3', credentials=creds)
            
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            result = service.permissions().create(
                fileId=file_id,
                body=user_permission,
                sendNotificationEmail=True
            ).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur partage fichier Drive: {str(e)}")
            raise

    @classmethod
    def get_file_permissions(cls, user_integration, file_id):
        """Récupère les permissions d'un fichier"""
        try:
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/drive.file']
            )
            
            service = build('drive', 'v3', credentials=creds)
            
            permissions = service.permissions().list(
                fileId=file_id,
                fields='permissions(id, emailAddress, role)'
            ).execute()
            
            return permissions.get('permissions', [])
            
        except Exception as e:
            logger.error(f"Erreur récupération permissions Drive: {str(e)}")
            raise

    @classmethod
    def update_permission(cls, user_integration, file_id, permission_id, role):
        """Modifie une permission existante"""
        try:
            creds = Credentials.from_authorized_user_info(
                user_integration.config,
                ['https://www.googleapis.com/auth/drive.file']
            )
            
            service = build('drive', 'v3', credentials=creds)
            
            permission = {'role': role}
            
            result = service.permissions().update(
                fileId=file_id,
                permissionId=permission_id,
                body=permission
            ).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur modification permission Drive: {str(e)}")
            raise 