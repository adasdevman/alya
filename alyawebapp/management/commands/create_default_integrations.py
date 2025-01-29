from django.core.management.base import BaseCommand
from alyawebapp.models import Domain, Integration

class Command(BaseCommand):
    help = 'Crée des intégrations par défaut pour chaque domaine'

    def handle(self, *args, **kwargs):
        default_integrations = {
            'RH': [
                {'name': 'LinkedIn Recruiter', 'icon_class': 'fab fa-linkedin', 'description': 'Recrutement et sourcing de candidats'},
                {'name': 'Workday', 'icon_class': 'fas fa-calendar-check', 'description': 'Gestion des RH et paie'},
                {'name': 'BambooHR', 'icon_class': 'fas fa-users-gear', 'description': 'Gestion des employés et congés'}
            ],
            'Projet': [
                {'name': 'Jira', 'icon_class': 'fab fa-jira', 'description': 'Gestion de projets agiles'},
                {'name': 'Trello', 'icon_class': 'fab fa-trello', 'description': 'Organisation des tâches'},
                {'name': 'Asana', 'icon_class': 'fas fa-tasks', 'description': 'Suivi de projets'}
            ],
            'CRM': [
                {'name': 'Salesforce', 'icon_class': 'fas fa-cloud', 'description': 'Gestion de la relation client'},
                {'name': 'HubSpot CRM', 'icon_class': 'fab fa-hubspot', 'description': 'Gérez vos contacts et vos ventes'},
                {'name': 'Pipedrive', 'icon_class': 'fas fa-funnel-dollar', 'description': 'Pipeline commercial'}
            ]
        }

        for domain_name, integrations in default_integrations.items():
            domain = Domain.objects.filter(name=domain_name).first()
            if domain:
                for integration_data in integrations:
                    Integration.objects.get_or_create(
                        domain=domain,
                        name=integration_data['name'],
                        defaults={
                            'icon_class': integration_data['icon_class'],
                            'description': integration_data['description']
                        }
                    )
                self.stdout.write(
                    self.style.SUCCESS(f'Intégrations créées pour {domain_name}')
                )

        self.stdout.write(self.style.SUCCESS('Intégrations créées avec succès')) 