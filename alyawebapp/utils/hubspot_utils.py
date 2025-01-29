from ..models import UserIntegration
from ..integrations.hubspot.handler import HubSpotHandler

def get_hubspot_handler(user):
    """Récupère un handler HubSpot configuré pour l'utilisateur"""
    try:
        integration = UserIntegration.objects.get(
            user=user,
            integration__name='hubspot',
            enabled=True
        )
        return HubSpotHandler(integration.access_token)
    except UserIntegration.DoesNotExist:
        raise Exception("Intégration HubSpot non configurée")

def execute_hubspot_action(user, action, params=None):
    """
    Exécute une action HubSpot selon les paramètres fournis
    """
    try:
        handler = get_hubspot_handler(user)
        
        if action == "create_contact":
            required_fields = ["email"]
            if not all(field in params for field in required_fields):
                return {
                    "status": "error",
                    "message": "L'email est requis pour créer un contact",
                    "required_fields": required_fields
                }
            return {
                "status": "success",
                "data": handler.create_contact(params)
            }
            
        elif action == "create_deal":
            required_fields = ["dealname"]
            if not all(field in params for field in required_fields):
                return {
                    "status": "error",
                    "message": "Le nom du deal est requis",
                    "required_fields": required_fields
                }
            return {
                "status": "success",
                "data": handler.create_deal(params)
            }
            
        else:
            return {
                "status": "error",
                "message": f"Action {action} non supportée"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }