from django.core.management.base import BaseCommand
from alyawebapp.models import CustomUser, UserProfile, Domain

class Command(BaseCommand):
    help = 'Débogue les domaines d\'un utilisateur'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = CustomUser.objects.get(username=username)
            profile = user.profile

            self.stdout.write(f"Utilisateur: {username}")
            self.stdout.write("Domaines dans la base de données:")
            for domain in Domain.objects.all():
                self.stdout.write(f"- {domain.id}: {domain.name}")

            self.stdout.write("\nDomaines du profil:")
            for domain in profile.domains.all():
                self.stdout.write(f"- {domain.id}: {domain.name}")

        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Utilisateur {username} non trouvé"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur: {str(e)}")) 