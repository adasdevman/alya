from django.core.management.base import BaseCommand
from alyawebapp.models import Domain, BusinessObjective, CompanySize

class Command(BaseCommand):
    help = 'Initialize default data'

    def handle(self, *args, **kwargs):
        # Objectifs métier
        objectives = [
            {'name': 'Augmenter les ventes', 'description': 'Accroître le chiffre d\'affaires', 'icon': 'fas fa-chart-line'},
            {'name': 'Optimiser les processus', 'description': 'Améliorer l\'efficacité opérationnelle', 'icon': 'fas fa-cogs'},
            {'name': 'Développer l\'équipe', 'description': 'Formation et recrutement', 'icon': 'fas fa-users'},
            {'name': 'Innovation produit', 'description': 'Développer de nouvelles solutions', 'icon': 'fas fa-lightbulb'},
        ]

        for obj in objectives:
            BusinessObjective.objects.get_or_create(
                name=obj['name'],
                defaults={
                    'description': obj['description'],
                    'icon': obj['icon']
                }
            )

        # Tailles d'entreprise
        sizes = [
            {'label': '1-10 employés', 'value': '1-10'},
            {'label': '11-50 employés', 'value': '11-50'},
            {'label': '51-200 employés', 'value': '51-200'},
            {'label': '201-500 employés', 'value': '201-500'},
            {'label': '500+ employés', 'value': '500+'},
        ]

        for size in sizes:
            CompanySize.objects.get_or_create(
                value=size['value'],
                defaults={'label': size['label']}
            )

        self.stdout.write(self.style.SUCCESS('Successfully initialized data')) 