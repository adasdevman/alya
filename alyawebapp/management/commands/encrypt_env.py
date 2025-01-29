from django.core.management.base import BaseCommand
from alyawebapp.utils.env_crypto import EnvCrypto
import os

class Command(BaseCommand):
    help = 'Chiffre le fichier .env'

    def add_arguments(self, parser):
        parser.add_argument(
            '--env-file',
            default='.env',
            help='Chemin vers le fichier .env à chiffrer'
        )
        parser.add_argument(
            '--output',
            default='.env.encrypted',
            help='Chemin de sortie pour le fichier chiffré'
        )
        parser.add_argument(
            '--key-file',
            default='.env.key',
            help='Chemin pour la clé de chiffrement'
        )

    def handle(self, *args, **options):
        env_file = options['env_file']
        output_file = options['output']
        key_file = options['key_file']

        if not os.path.exists(env_file):
            self.stderr.write(self.style.ERROR(f'Le fichier {env_file} n\'existe pas'))
            return

        crypto = EnvCrypto(key_file=key_file)
        if crypto.encrypt_env(env_file=env_file, output_file=output_file):
            self.stdout.write(self.style.SUCCESS(f'Fichier {env_file} chiffré avec succès dans {output_file}'))
            self.stdout.write(self.style.WARNING('IMPORTANT: Conservez le fichier .env.key en lieu sûr !'))
        else:
            self.stderr.write(self.style.ERROR('Erreur lors du chiffrement')) 