from django.core.management.base import BaseCommand
from alyawebapp.utils.env_crypto import EnvCrypto
import os

class Command(BaseCommand):
    help = 'Déchiffre le fichier .env chiffré'

    def add_arguments(self, parser):
        parser.add_argument(
            '--encrypted-file',
            default='.env.encrypted',
            help='Chemin vers le fichier .env chiffré'
        )
        parser.add_argument(
            '--output',
            default='.env.decrypted',
            help='Chemin de sortie pour le fichier déchiffré'
        )
        parser.add_argument(
            '--key-file',
            default='.env.key',
            help='Chemin vers la clé de chiffrement'
        )

    def handle(self, *args, **options):
        encrypted_file = options['encrypted_file']
        output_file = options['output']
        key_file = options['key_file']

        if not os.path.exists(encrypted_file):
            self.stderr.write(self.style.ERROR(f'Le fichier {encrypted_file} n\'existe pas'))
            return

        if not os.path.exists(key_file):
            self.stderr.write(self.style.ERROR(f'Le fichier de clé {key_file} n\'existe pas'))
            return

        crypto = EnvCrypto(key_file=key_file)
        if crypto.decrypt_env(encrypted_file=encrypted_file, output_file=output_file):
            self.stdout.write(self.style.SUCCESS(f'Fichier {encrypted_file} déchiffré avec succès dans {output_file}'))
        else:
            self.stderr.write(self.style.ERROR('Erreur lors du déchiffrement')) 