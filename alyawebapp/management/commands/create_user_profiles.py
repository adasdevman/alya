from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from alyawebapp.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Crée les profils utilisateurs manquants'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        for user in users:
            UserProfile.objects.get_or_create(user=user)
            self.stdout.write(f'Profil créé pour {user.username}') 