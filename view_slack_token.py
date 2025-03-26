#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simple pour afficher les tokens Slack stockés en base de données.
Ce script ne nécessite pas d'initialiser le handler complet.

Usage:
    python view_slack_token.py
"""

import os
import sys
import json
import django
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def view_slack_tokens():
    """Affiche les tokens Slack pour tous les utilisateurs"""
    from alyawebapp.models import Integration, UserIntegration, CustomUser
    
    try:
        # Rechercher l'intégration Slack
        try:
            slack_integrations = Integration.objects.filter(name__icontains='slack')
            if not slack_integrations.exists():
                print("❌ Aucune intégration Slack trouvée dans la base de données.")
                return
            
            print(f"Intégrations Slack trouvées: {slack_integrations.count()}")
            for integration in slack_integrations:
                print(f"- {integration.name} (ID: {integration.id})")
            
            # Pour chaque intégration Slack, trouver les utilisateurs
            total_users = 0
            for integration in slack_integrations:
                user_integrations = UserIntegration.objects.filter(integration=integration)
                total_users += user_integrations.count()
                
                print(f"\n=== Utilisateurs avec l'intégration '{integration.name}' ({user_integrations.count()}) ===")
                
                if not user_integrations.exists():
                    print("Aucun utilisateur n'a activé cette intégration.")
                    continue
                
                for ui in user_integrations:
                    try:
                        username = ui.user.username or ui.user.email
                    except:
                        username = f"User ID: {ui.user_id}"
                    
                    enabled = "✓" if ui.enabled else "✗"
                    print(f"- {username} (Activé: {enabled})")
                    
                    # Afficher les informations de token
                    if not ui.config:
                        print("  ❌ Configuration vide")
                        continue
                    
                    config = ui.config
                    if isinstance(config, str):
                        try:
                            config = json.loads(config)
                        except json.JSONDecodeError:
                            print(f"  ❌ Configuration invalide (JSON non valide): {config[:30]}...")
                            continue
                    
                    if not isinstance(config, dict):
                        print(f"  ❌ Type de configuration non pris en charge: {type(config)}")
                        continue
                    
                    # Afficher l'access_token
                    if 'access_token' in config and config['access_token']:
                        token = config['access_token']
                        first_part = token[:10] if len(token) > 10 else token[:5]
                        last_part = token[-5:] if len(token) > 10 else ""
                        print(f"  🔑 Token: {first_part}...{last_part}")
                        
                        # Vérifier le format du token
                        if token.startswith(('xoxb-', 'xoxp-', 'xoxe.')):
                            token_type = "Bot" if token.startswith(('xoxb-', 'xoxe.xoxb-')) else "User" if token.startswith('xoxp-') else "Unknown"
                            print(f"  ✅ Format de token valide (Type: {token_type})")
                        else:
                            print(f"  ⚠️ Format de token inhabituel: {token[:5]}...")
                    else:
                        print("  ❌ Aucun access_token trouvé")
                    
                    # Vérifier si refresh_token est présent
                    if 'refresh_token' in config and config['refresh_token']:
                        print("  ✅ refresh_token présent")
                    else:
                        print("  ⚠️ Aucun refresh_token trouvé")
                    
                    # Vérifier si client_id et client_secret sont présents
                    missing_fields = []
                    for field in ['client_id', 'client_secret', 'redirect_uri']:
                        if field not in config or not config[field]:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"  ⚠️ Champs manquants: {', '.join(missing_fields)}")
                    else:
                        print("  ✅ Tous les champs requis sont présents")
                    
                    # Afficher les autres champs éventuels
                    other_fields = [key for key in config.keys() if key not in ['access_token', 'refresh_token', 'client_id', 'client_secret', 'redirect_uri']]
                    if other_fields:
                        print(f"  ℹ️ Autres champs: {', '.join(other_fields)}")
                    
                    print("") # Ligne vide pour séparer les utilisateurs
            
            print(f"\n=== Résumé ===")
            print(f"Total des intégrations Slack: {slack_integrations.count()}")
            print(f"Total des utilisateurs avec au moins une intégration: {total_users}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'accès aux intégrations: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    except Exception as e:
        print(f"❌ Erreur globale: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("=== VISUALISATION DES TOKENS SLACK ===")
    view_slack_tokens() 