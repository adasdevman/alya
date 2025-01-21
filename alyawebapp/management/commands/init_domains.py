from django.core.management.base import BaseCommand
from alyawebapp.models import Domain

class Command(BaseCommand):
    help = 'Initialize default domains'

    def handle(self, *args, **kwargs):
        domains = [
            {'name': 'Analytics', 'icon': 'fas fa-chart-line'},
            {'name': 'Logistic', 'icon': 'fas fa-truck'},
            {'name': 'Legal', 'icon': 'fas fa-balance-scale'},
            {'name': 'Marketing', 'icon': 'fas fa-bullhorn'},
            {'name': 'Automation', 'icon': 'fas fa-robot'},
            {'name': 'Support', 'icon': 'fas fa-headset'},
            {'name': 'Finance', 'icon': 'fas fa-coins'},
            {'name': 'RH', 'icon': 'fas fa-users'},
            {'name': 'Projet', 'icon': 'fas fa-tasks'},
            {'name': 'CRM', 'icon': 'fas fa-handshake'}
        ]

        for domain_data in domains:
            Domain.objects.get_or_create(
                name=domain_data['name'],
                defaults={
                    'icon': domain_data['icon'],
                    'description': domain_data['description']
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully initialized domains')) 