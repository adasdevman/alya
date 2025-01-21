from typing import Optional, Dict, Any
from ..models import UserIntegration, Integration
from django.contrib.auth import get_user_model
import importlib
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class IntegrationManager:
    @staticmethod
    def get_integration_handler(integration_name: str, user_id: int) -> Optional[Any]:
        """
        Récupère le gestionnaire d'intégration approprié pour un utilisateur donné.
        """
        try:
            # Récupérer l'intégration et sa configuration utilisateur
            integration = Integration.objects.get(name__iexact=integration_name)
            user_integration = UserIntegration.objects.get(
                user_id=user_id,
                integration=integration,
                enabled=True
            )

            if not user_integration.config:
                logger.warning(f"Configuration manquante pour l'intégration {integration_name}")
                return None

            # Construire le chemin du module
            module_path = f"alyawebapp.integrations.{integration_name.lower()}.handler"
            
            try:
                # Importer dynamiquement le module de l'intégration
                module = importlib.import_module(module_path)
                handler_class = getattr(module, f"{integration_name}Handler")
                
                # Instancier le gestionnaire avec la configuration
                return handler_class(user_integration.config)
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Erreur lors du chargement du gestionnaire pour {integration_name}: {str(e)}")
                return None

        except (Integration.DoesNotExist, UserIntegration.DoesNotExist) as e:
            logger.warning(f"Intégration {integration_name} non trouvée ou non activée pour l'utilisateur {user_id}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du gestionnaire {integration_name}: {str(e)}")
            return None

    @staticmethod
    def get_available_integrations(user_id: int) -> Dict[str, Any]:
        """
        Récupère toutes les intégrations disponibles et configurées pour un utilisateur.
        """
        available_integrations = {}
        user_integrations = UserIntegration.objects.filter(
            user_id=user_id,
            enabled=True
        ).select_related('integration')

        for user_integration in user_integrations:
            integration_name = user_integration.integration.name
            handler = IntegrationManager.get_integration_handler(integration_name, user_id)
            if handler:
                available_integrations[integration_name.lower()] = handler

        return available_integrations

    @staticmethod
    def execute_integration_action(integration_name: str, user_id: int, action: str, **kwargs) -> Dict[str, Any]:
        """
        Exécute une action spécifique sur une intégration.
        """
        handler = IntegrationManager.get_integration_handler(integration_name, user_id)
        if not handler:
            return {
                'status': 'error',
                'message': f"Intégration {integration_name} non disponible ou non configurée"
            }

        try:
            # Vérifier si l'action existe
            if not hasattr(handler, action):
                return {
                    'status': 'error',
                    'message': f"Action {action} non supportée par {integration_name}"
                }

            # Exécuter l'action
            method = getattr(handler, action)
            result = method(**kwargs)
            return {
                'status': 'success',
                'data': result
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {action} sur {integration_name}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 