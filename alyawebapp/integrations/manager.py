from .analytics.amplitude import AmplitudeIntegration
from .analytics.google_analytics import GoogleAnalyticsIntegration
from .analytics.mixpanel import MixpanelIntegration
from .marketing.mailchimp import MailchimpIntegration
from .marketing.brevo import BrevoIntegration
from .crm.salesforce import SalesforceIntegration
from .crm.hubspot import HubspotIntegration
from .rh.bamboohr import BambooHRIntegration
from .rh.workday import WorkdayIntegration
from .finance.stripe import StripeIntegration
from .finance.quickbooks import QuickBooksIntegration
from .automation.zapier import ZapierIntegration
from .automation.uipath import UiPathIntegration
from .logistic.freightview import FreightviewIntegration
from .logistic.odoo import OdooIntegration
from .logistic.shipstation import ShipStationIntegration
from .legal.clio import ClioIntegration
from .legal.docusign import DocuSignIntegration
from .legal.lexisnexis import LexisNexisIntegration
# ... autres imports

class IntegrationManager:
    INTEGRATION_CLASSES = {
        'Amplitude': AmplitudeIntegration,
        'Google Analytics': GoogleAnalyticsIntegration,
        'Mixpanel': MixpanelIntegration,
        'Mailchimp': MailchimpIntegration,
        'Brevo': BrevoIntegration,
        'Salesforce': SalesforceIntegration,
        'HubSpot': HubspotIntegration,
        'BambooHR': BambooHRIntegration,
        'Workday': WorkdayIntegration,
        'Stripe': StripeIntegration,
        'QuickBooks': QuickBooksIntegration,
        'Zapier': ZapierIntegration,
        'UiPath': UiPathIntegration,
        'Freightview': FreightviewIntegration,
        'Odoo': OdooIntegration,
        'ShipStation': ShipStationIntegration,
        'Clio': ClioIntegration,
        'DocuSign': DocuSignIntegration,
        'LexisNexis': LexisNexisIntegration,
        # ... autres intégrations
    }

    @classmethod
    def get_integration(cls, integration_name, config):
        """Récupère l'instance d'intégration appropriée"""
        if integration_name not in cls.INTEGRATION_CLASSES:
            raise ValueError(f"Intégration non supportée: {integration_name}")

        integration_class = cls.INTEGRATION_CLASSES[integration_name]
        return integration_class(config)

    @classmethod
    def test_integration(cls, integration_name, config):
        """Teste une intégration"""
        integration = cls.get_integration(integration_name, config)
        return integration.test_connection()

    @classmethod
    def get_available_integrations(cls, user_id):
        """
        Récupère la liste des intégrations disponibles pour un utilisateur.
        """
        from ..models import UserIntegration, Integration
        import logging

        logger = logging.getLogger(__name__)
        
        # Récupérer les intégrations activées pour l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user_id=user_id,
            enabled=True
        ).select_related('integration')
        
        available_integrations = {}
        for user_integration in user_integrations:
            integration_name = user_integration.integration.name
            try:
                if integration_name in cls.INTEGRATION_CLASSES and user_integration.config:
                    available_integrations[integration_name.lower()] = integration_name
            except Exception as e:
                logger.warning(f"Erreur lors du chargement de l'intégration {integration_name}: {str(e)}")
                continue
        
        return available_integrations