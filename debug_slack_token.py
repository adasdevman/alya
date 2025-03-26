#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnostic pour afficher le token Slack récupéré dans l'initialisation du handler.
Ce script simule l'initialisation du SlackHandler et affiche le token récupéré.

Usage:
    python debug_slack_token.py [user_id]
"""

import os
import sys
import json
import django
import logging
from dotenv import load_dotenv

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('slack_debug')

# Charger les variables d'environnement
load_dotenv()

# Configurer Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def check_slack_token(user_id=None):
    """Vérifie et affiche le token Slack pour un utilisateur donné"""
    from alyawebapp.models import Integration, UserIntegration, CustomUser
    from alyawebapp.services.handlers.slack_handler import SlackHandler
    from alyawebapp.services.ai_orchestrator import AIOrchestrator
    
    try:
        # Si aucun user_id n'est fourni, lister tous les utilisateurs
        if not user_id:
            users = CustomUser.objects.all()
            print(f"\nUtilisateurs disponibles ({users.count()}):")
            for i, user in enumerate(users, 1):
                username = user.username or user.email
                print(f"{i}. ID: {user.id}, Nom: {username}")
            
            user_choice = input("\nEntrez l'ID ou le numéro de l'utilisateur à vérifier (ou 'q' pour quitter): ")
            if user_choice.lower() == 'q':
                return
            
            try:
                # Si l'entrée est un nombre mais pas un ID valide, considérer comme un index
                choice_num = int(user_choice)
                if 1 <= choice_num <= users.count():
                    user = users[choice_num - 1]
                else:
                    user = CustomUser.objects.get(id=choice_num)
            except (ValueError, CustomUser.DoesNotExist):
                print(f"❌ Utilisateur non trouvé avec l'ID/numéro: {user_choice}")
                return
        else:
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                print(f"❌ Utilisateur non trouvé avec l'ID: {user_id}")
                return
        
        print(f"✅ Utilisateur sélectionné: {user.username or user.email} (ID: {user.id})")
        
        # Vérifier si cet utilisateur a une intégration Slack
        try:
            integration = Integration.objects.get(name__iexact='slack')
            print(f"✅ Intégration Slack trouvée: {integration.name} (ID: {integration.id})")
            
            user_integration = UserIntegration.objects.get(
                user=user,
                integration=integration,
                enabled=True
            )
            
            print(f"✅ Intégration utilisateur trouvée (ID: {user_integration.id})")
            
            # Afficher les détails de la configuration
            config = user_integration.config
            if not config:
                print("❌ La configuration est vide")
            elif isinstance(config, str):
                try:
                    config_dict = json.loads(config)
                    print_config(config_dict)
                except json.JSONDecodeError:
                    print(f"❌ Impossible de décoder la configuration JSON: {config[:50]}...")
            elif isinstance(config, dict):
                print_config(config)
            else:
                print(f"❌ Type de configuration inconnu: {type(config)}")
            
            # Simuler l'initialisation du SlackHandler
            print("\n=== Simulation de l'initialisation du SlackHandler ===")
            
            # Créer un orchestrateur (requis pour initialiser le SlackHandler)
            orchestrator = AIOrchestrator(user)
            
            # Créer le SlackHandler avec logging amélioré
            original_info = logging.Logger.info
            
            def patched_info(self, msg, *args, **kwargs):
                """Version patchée de logger.info qui intercepte les messages liés au token"""
                if "Configuration Slack trouvée" in msg and isinstance(args[0], dict):
                    config = args[0]
                    safe_config = config.copy()
                    if 'access_token' in safe_config:
                        token = safe_config['access_token']
                        if token:
                            # Montrer seulement une partie du token pour la sécurité
                            first_part = token[:10] if len(token) > 10 else token[:5]
                            last_part = token[-5:] if len(token) > 10 else ""
                            safe_config['access_token'] = f"{first_part}...{last_part}"
                            print(f"\n🔑 Token Slack trouvé: {first_part}...{last_part}")
                        else:
                            print("\n⚠️ Token Slack vide!")
                    else:
                        print("\n❌ Aucun token Slack dans la configuration!")
                
                # Appeler la fonction originale
                original_info(self, msg, *args, **kwargs)
            
            # Remplacer temporairement la fonction de logging
            logging.Logger.info = patched_info
            
            try:
                slack_handler = SlackHandler(orchestrator)
                print("\n=== SlackHandler initialisé ===")
                
                # Tester l'accès à l'API Slack
                print("\n=== Test de connexion à l'API Slack ===")
                if slack_handler.slack_integration and slack_handler.slack_integration.config:
                    config = slack_handler.slack_integration.config
                    if isinstance(config, dict) and 'access_token' in config:
                        token = config['access_token']
                        token_preview = f"{token[:10]}...{token[-5:]}" if token and len(token) > 15 else token
                        print(f"Token utilisé pour le test: {token_preview}")
                        
                        # Créer un objet de l'intégration Slack pour tester le token
                        from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
                        
                        # Configuration minimale pour l'API
                        minimal_config = {
                            'client_id': config.get('client_id', 'default_id'),
                            'client_secret': config.get('client_secret', 'default_secret'),
                            'redirect_uri': config.get('redirect_uri', 'default_uri'),
                            'access_token': token,
                            'refresh_token': config.get('refresh_token')
                        }
                        
                        slack_api = SlackAPI(minimal_config)
                        if slack_api.verify_token():
                            print("✅ Token valide! Connexion à l'API Slack réussie.")
                        else:
                            print("❌ Token invalide ou expiré. Échec de la connexion à l'API Slack.")
                    else:
                        print("❌ Configuration invalide ou token manquant.")
            finally:
                # Restaurer la fonction de logging originale
                logging.Logger.info = original_info
                
        except Integration.DoesNotExist:
            print("❌ Aucune intégration Slack n'existe dans la base de données.")
        except UserIntegration.DoesNotExist:
            print("❌ Cet utilisateur n'a pas activé l'intégration Slack.")
    
    except Exception as e:
        print(f"❌ Erreur lors de la vérification du token: {str(e)}")
        import traceback
        print(traceback.format_exc())

def print_config(config):
    """Affiche la configuration de manière sécurisée"""
    print("\nConfiguration Slack:")
    safe_config = config.copy()
    
    # Masquer les valeurs sensibles
    sensitive_keys = ['access_token', 'refresh_token', 'client_secret']
    for key in sensitive_keys:
        if key in safe_config and safe_config[key]:
            value = safe_config[key]
            # Montrer seulement une partie des valeurs sensibles
            first_part = value[:10] if len(value) > 10 else value[:5]
            last_part = value[-5:] if len(value) > 10 else ""
            safe_config[key] = f"{first_part}...{last_part}"
    
    # Afficher toutes les clés et valeurs
    for key, value in safe_config.items():
        print(f"  • {key}: {value}")

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    print("=== DIAGNOSTIC DU TOKEN SLACK ===")
    check_slack_token(user_id) 