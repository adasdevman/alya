import logging
from .handler import HubSpotHandler
from django.conf import settings

logger = logging.getLogger(__name__)

class HubSpotManager:
    @classmethod
    def execute_action(cls, user_integration, method_name, params):
        """
        Exécute une action HubSpot
        """
        try:
            # Récupérer la configuration complète
            config = {
                'access_token': user_integration.access_token,
                'refresh_token': user_integration.refresh_token,
                'client_id': settings.HUBSPOT_CLIENT_ID,
                'client_secret': settings.HUBSPOT_CLIENT_SECRET,
                'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
                **user_integration.config  # Ajouter toute configuration supplémentaire
            }

            # Créer le handler avec les tokens de l'utilisateur
            handler = HubSpotHandler(config)

            # Vérifier que la méthode existe
            if not hasattr(handler, method_name):
                raise Exception(f"Méthode {method_name} non trouvée pour HubSpot")

            # Exécuter la méthode
            method = getattr(handler, method_name)
            if method_name == 'create_contact':
                # Valider les champs requis pour un contact
                if not params.get('email') or not params.get('firstname'):
                    raise ValueError("L'email et le prénom sont requis pour créer un contact")
                try:
                    result = method(properties=params)
                   
                    # Si les tokens ont été rafraîchis, les mettre à jour
                    if handler.access_token != user_integration.access_token:
                        user_integration.access_token = handler.access_token
                        user_integration.refresh_token = handler.refresh_token
                        user_integration.save()
                       
                except Exception as e:
                    logger.error(f"Erreur lors de la création du contact: {str(e)}")
                    raise
            elif method_name == 'create_company':
                # Valider les champs requis pour une compagnie
                if not params.get('name'):
                    raise ValueError("Le nom est requis pour créer une compagnie")
                result = method(properties=params)
            else:
                result = method(**params)

            return {
                'success': True,
                'contact_id': result.get('id') if result else None
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {method_name} sur HubSpot: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 