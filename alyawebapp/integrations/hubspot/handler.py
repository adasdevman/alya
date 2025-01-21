import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class HubSpotHandler:
    def __init__(self, config: Dict[str, str]):
        self.api_key = config.get('api_key')
        self.base_url = "https://api.hubapi.com"
        if not self.api_key:
            raise ValueError("Clé API HubSpot manquante")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Effectue une requête à l'API HubSpot.
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête HubSpot: {str(e)}")
            raise Exception(f"Erreur lors de la communication avec HubSpot: {str(e)}")

    def create_contact(self, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Crée un contact dans HubSpot.
        
        Args:
            properties: Dictionnaire des propriétés du contact
                Ex: {
                    "email": "contact@example.com",
                    "firstname": "John",
                    "lastname": "Doe",
                    "phone": "+33123456789"
                }
        """
        endpoint = "crm/v3/objects/contacts"
        data = {"properties": properties}
        return self._make_request("POST", endpoint, data)

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'un contact.
        """
        endpoint = f"crm/v3/objects/contacts/{contact_id}"
        return self._make_request("GET", endpoint)

    def update_contact(self, contact_id: str, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Met à jour un contact existant.
        """
        endpoint = f"crm/v3/objects/contacts/{contact_id}"
        data = {"properties": properties}
        return self._make_request("PATCH", endpoint, data)

    def delete_contact(self, contact_id: str) -> None:
        """
        Supprime un contact.
        """
        endpoint = f"crm/v3/objects/contacts/{contact_id}"
        self._make_request("DELETE", endpoint)

    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche des contacts selon des critères.
        """
        endpoint = "crm/v3/objects/contacts/search"
        data = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "CONTAINS_TOKEN",
                    "value": query
                }]
            }]
        }
        return self._make_request("POST", endpoint, data).get("results", [])

    def create_deal(self, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Crée une opportunité dans HubSpot.
        """
        endpoint = "crm/v3/objects/deals"
        data = {"properties": properties}
        return self._make_request("POST", endpoint, data)

    def get_deal(self, deal_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une opportunité.
        """
        endpoint = f"crm/v3/objects/deals/{deal_id}"
        return self._make_request("GET", endpoint)

    def update_deal(self, deal_id: str, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Met à jour une opportunité existante.
        """
        endpoint = f"crm/v3/objects/deals/{deal_id}"
        data = {"properties": properties}
        return self._make_request("PATCH", endpoint, data)

    def create_company(self, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Crée une entreprise dans HubSpot.
        """
        endpoint = "crm/v3/objects/companies"
        data = {"properties": properties}
        return self._make_request("POST", endpoint, data)

    def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une entreprise.
        """
        endpoint = f"crm/v3/objects/companies/{company_id}"
        return self._make_request("GET", endpoint)

    def update_company(self, company_id: str, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Met à jour une entreprise existante.
        """
        endpoint = f"crm/v3/objects/companies/{company_id}"
        data = {"properties": properties}
        return self._make_request("PATCH", endpoint, data) 