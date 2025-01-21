from django.core.management.base import BaseCommand
from alyawebapp.models import Domain, Integration

class Command(BaseCommand):
    help = 'Initialise les intégrations par défaut'

    def handle(self, *args, **kwargs):
        integrations_by_domain = {
            'Marketing': [
                {'name': 'Mailchimp', 'icon': 'fab fa-mailchimp', 'description': 'Marketing par email et automation'},
                {'name': 'Sendinblue', 'icon': 'fas fa-mail-bulk', 'description': 'Marketing multicanal'},
                {'name': 'HubSpot Marketing', 'icon': 'fas fa-h-square', 'description': 'Marketing automation et CMS'},
                {'name': 'Google Ads', 'icon': 'fab fa-google', 'description': 'Publicité en ligne'},
                {'name': 'Facebook Ads', 'icon': 'fab fa-facebook', 'description': 'Publicité sur les réseaux sociaux'},
                {'name': 'LinkedIn Ads', 'icon': 'fab fa-linkedin', 'description': 'Publicité B2B'},
                {'name': 'Twitter Ads', 'icon': 'fab fa-twitter', 'description': 'Publicité sur Twitter'},
                {'name': 'Klaviyo', 'icon': 'fas fa-shopping-cart', 'description': 'Marketing automation e-commerce'},
                {'name': 'ActiveCampaign', 'icon': 'fas fa-envelope-open-text', 'description': 'Marketing automation et CRM'},
                {'name': 'Buffer', 'icon': 'fas fa-buffer', 'description': 'Gestion des médias sociaux'}
            ],
            'Analytics': [
                {'name': 'Google Analytics', 'icon': 'fab fa-google', 'description': 'Analyse du trafic web'},
                {'name': 'Mixpanel', 'icon': 'fas fa-chart-line', 'description': 'Analyse comportementale'},
                {'name': 'Amplitude', 'icon': 'fas fa-wave-square', 'description': 'Analytics produit'}
            ],
            'Logistic': [
                {'name': 'ShipStation', 'icon': 'fas fa-shipping-fast', 'description': 'Gestion des expéditions'},
                {'name': 'Freightview', 'icon': 'fas fa-truck', 'description': 'Gestion du transport'},
                {'name': 'Odoo', 'icon': 'fas fa-boxes', 'description': 'Gestion des stocks'}
            ],
            'Legal': [
                {'name': 'DocuSign', 'icon': 'fas fa-file-signature', 'description': 'Signature électronique'},
                {'name': 'LexisNexis', 'icon': 'fas fa-balance-scale', 'description': 'Base juridique'},
                {'name': 'Clio', 'icon': 'fas fa-gavel', 'description': 'Gestion juridique'}
            ],
            'Automation': [
                {'name': 'Zapier', 'icon': 'fas fa-robot', 'description': 'Automatisation des tâches'},
                {'name': 'Make', 'icon': 'fas fa-cogs', 'description': 'Workflows avancés'},
                {'name': 'UiPath', 'icon': 'fas fa-random', 'description': 'RPA'}
            ],
            'Support': [
                {'name': 'Zendesk', 'icon': 'fas fa-headset', 'description': 'Service client'},
                {'name': 'Intercom', 'icon': 'far fa-comment-dots', 'description': 'Messagerie client'},
                {'name': 'Freshdesk', 'icon': 'fas fa-ticket-alt', 'description': 'Support client'}
            ],
            'Finance': [
                {'name': 'QuickBooks', 'icon': 'fas fa-calculator', 'description': 'Comptabilité'},
                {'name': 'Xero', 'icon': 'fas fa-file-invoice-dollar', 'description': 'Comptabilité en ligne'},
                {'name': 'Stripe', 'icon': 'fab fa-stripe', 'description': 'Paiements en ligne'}
            ]
        }

        for domain_name, integrations in integrations_by_domain.items():
            try:
                domain = Domain.objects.get(name=domain_name)
                self.stdout.write(f"Traitement du domaine: {domain_name}")
                
                for integration_data in integrations:
                    integration, created = Integration.objects.get_or_create(
                        name=integration_data['name'],
                        domain=domain,
                        defaults={
                            'icon': integration_data['icon'],
                            'description': integration_data['description']
                        }
                    )
                    if created:
                        self.stdout.write(f"Créé: {integration.name}")
                    else:
                        self.stdout.write(f"Existant: {integration.name}")
                        
            except Domain.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Domaine non trouvé: {domain_name}")) 