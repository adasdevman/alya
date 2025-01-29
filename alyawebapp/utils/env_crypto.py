from cryptography.fernet import Fernet
import os
import base64
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class EnvCrypto:
    def __init__(self, key_file='.env.key'):
        self.key_file = key_file
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self):
        """Charge ou génère une clé de chiffrement."""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key

    def encrypt_env(self, env_file='.env', output_file='.env.encrypted'):
        """Chiffre le fichier .env"""
        try:
            # Lire le contenu du fichier .env
            if not os.path.exists(env_file):
                raise FileNotFoundError(f"Le fichier {env_file} n'existe pas")

            with open(env_file, 'rb') as f:
                data = f.read()

            # Chiffrer les données
            encrypted_data = self.fernet.encrypt(data)

            # Sauvegarder les données chiffrées
            with open(output_file, 'wb') as f:
                f.write(encrypted_data)

            logger.info(f"Fichier {env_file} chiffré avec succès dans {output_file}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du chiffrement: {str(e)}")
            return False

    def decrypt_env(self, encrypted_file='.env.encrypted', output_file='.env.decrypted'):
        """Déchiffre le fichier .env chiffré"""
        try:
            # Lire le contenu du fichier chiffré
            if not os.path.exists(encrypted_file):
                raise FileNotFoundError(f"Le fichier {encrypted_file} n'existe pas")

            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()

            # Déchiffrer les données
            decrypted_data = self.fernet.decrypt(encrypted_data)

            # Sauvegarder les données déchiffrées
            with open(output_file, 'wb') as f:
                f.write(decrypted_data)

            logger.info(f"Fichier {encrypted_file} déchiffré avec succès dans {output_file}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement: {str(e)}")
            return False 