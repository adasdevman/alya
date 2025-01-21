from django.core.management.base import BaseCommand
from alyawebapp.models import Domain, UserDomain, CustomUser

class Command(BaseCommand):
    help = 'Débogue les domaines et les associations utilisateur-domaine'

    def handle(self, *args, **kwargs):
        self.stdout.write("Domaines existants:")
        for domain in Domain.objects.all():
            self.stdout.write(f"- {domain.id}: {domain.name} (Icon: {domain.icon})")

        self.stdout.write("\nAssociations Utilisateur-Domaine:")
        for ud in UserDomain.objects.all():
            self.stdout.write(f"- Utilisateur: {ud.user.username}, Domaine: {ud.domain.name}") 