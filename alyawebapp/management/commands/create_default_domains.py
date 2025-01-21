from django.core.management.base import BaseCommand
from alyawebapp.models import Domain

class Command(BaseCommand):
    help = 'Crée les domaines par défaut'

    def handle(self, *args, **kwargs):
        domains = [
            {
                'name': 'Analytics',
                'icon': 'fas fa-chart-line',
                'description': 'Analyse de données et insights'
            },
            {
                'name': 'Logistic',
                'icon': 'fas fa-truck',
                'description': 'Gestion de la chaîne logistique'
            },
            {
                'name': 'Legal',
                'icon': 'fas fa-balance-scale',
                'description': 'Conseil et support juridique'
            },
            {
                'name': 'Marketing',
                'icon': 'fas fa-bullhorn',
                'description': 'Stratégie et campagnes marketing'
            },
            {
                'name': 'Automation',
                'icon': 'fas fa-robot',
                'description': 'Automatisation des processus'
            },
            {
                'name': 'Support',
                'icon': 'fas fa-headset',
                'description': 'Assistance et support client'
            },
            {
                'name': 'Finance',
                'icon': 'fas fa-coins',
                'description': 'Gestion financière et comptabilité'
            },
            {
                'name': 'RH',
                'icon': 'fas fa-users',
                'description': 'Ressources humaines et recrutement'
            },
            {
                'name': 'Projet',
                'icon': 'fas fa-tasks',
                'description': 'Gestion et suivi de projets'
            },
            {
                'name': 'CRM',
                'icon': 'fas fa-address-book',
                'description': 'Gestion de la relation client'
            }
        ]

        for domain_data in domains:
            Domain.objects.get_or_create(
                name=domain_data['name'],
                defaults={
                    'description': domain_data['description'],
                    'icon': domain_data['icon']
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f'Domaine créé avec succès : {domain_data["name"]}')
            ) 