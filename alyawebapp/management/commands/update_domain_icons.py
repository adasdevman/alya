from django.core.management.base import BaseCommand
from alyawebapp.models import Domain

class Command(BaseCommand):
    help = 'Met à jour les icônes des domaines'

    def handle(self, *args, **kwargs):
        # Dictionnaire des domaines avec leurs icônes
        domain_icons = {
            'Santé': 'fas fa-heartbeat',
            'Finance': 'fas fa-coins',
            'Éducation': 'fas fa-graduation-cap',
            'Technologie': 'fas fa-laptop-code',
            'Marketing': 'fas fa-bullhorn',
            'Ressources Humaines': 'fas fa-users',
            'Juridique': 'fas fa-balance-scale',
            'Immobilier': 'fas fa-home',
            'E-commerce': 'fas fa-shopping-cart',
            'Communication': 'fas fa-comments',
            'Développement personnel': 'fas fa-brain',
            'Environnement': 'fas fa-leaf'
        }

        for name, icon in domain_icons.items():
            domain, created = Domain.objects.get_or_create(name=name)
            domain.icon = icon
            domain.save()
            self.stdout.write(
                self.style.SUCCESS(f'Domaine "{name}" mis à jour avec l\'icône {icon}')
            ) 