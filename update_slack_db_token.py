#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour le token Slack dans la base de données.
Ce script permet de résoudre le problème de token manquant ou expiré
sans avoir à reconfigurer complètement l'intégration.

Usage: python update_slack_db_token.py
"""

import os
import sys
import django
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

# Importer les modèles Django nécessaires
from django.db.models import Q
from alyawebapp.models import Integration, UserIntegration, CustomUser

def update_slack_token():
    """Met à jour le token Slack dans la base de données"""
    print("=== MISE À JOUR DU TOKEN SLACK ===")
    
    # Étape 1: Trouver l'intégration Slack
    try:
        slack_integration = Integration.objects.get(name__icontains='slack')
        print(f"✅ Intégration Slack trouvée: {slack_integration.name} (ID: {slack_integration.id})")
    except Integration.DoesNotExist:
        print("❌ Aucune intégration Slack n'existe dans la base de données.")
        return
    except Integration.MultipleObjectsReturned:
        print("⚠️ Plusieurs intégrations Slack trouvées. Utilisation de la première.")
        slack_integration = Integration.objects.filter(name__icontains='slack').first()
    
    # Étape 2: Récupérer tous les utilisateurs avec cette intégration
    user_integrations = UserIntegration.objects.filter(integration=slack_integration)
    
    if not user_integrations.exists():
        print("❌ Aucun utilisateur n'a configuré l'intégration Slack.")
        return
    
    print(f"\nUtilisateurs avec intégration Slack ({user_integrations.count()}):")
    for i, ui in enumerate(user_integrations, 1):
        username = ui.user.username if hasattr(ui.user, 'username') else ui.user.email
        enabled = "✓ Activé" if ui.enabled else "✗ Désactivé"
        config = ui.config if ui.config else {}
        has_token = "✓" if config.get('access_token') else "✗"
        print(f"{i}. {username} - {enabled} - Token: {has_token}")
    
    # Étape 3: Demander à l'utilisateur de choisir quelle intégration mettre à jour
    try:
        choice = input("\nQuelle intégration voulez-vous mettre à jour? (numéro, 'a' pour toutes, 'q' pour quitter): ")
        
        if choice.lower() == 'q':
            print("Opération annulée.")
            return
        
        # Demander le nouveau token
        new_token = input("\nEntrez le nouveau token Slack (commençant par 'xoxb-' ou 'xoxp-'): ").strip()
        if not new_token or not (new_token.startswith('xoxb-') or new_token.startswith('xoxp-')):
            print("❌ Token invalide. Le token doit commencer par 'xoxb-' ou 'xoxp-'.")
            return
        
        updated_count = 0
        
        if choice.lower() == 'a':
            # Mettre à jour toutes les intégrations
            for ui in user_integrations:
                if ui.config is None:
                    ui.config = {}
                ui.config['access_token'] = new_token
                ui.save()
                updated_count += 1
                username = ui.user.username if hasattr(ui.user, 'username') else ui.user.email
                print(f"✅ Token mis à jour pour {username}")
        else:
            try:
                # Mettre à jour une intégration spécifique
                index = int(choice) - 1
                if 0 <= index < len(user_integrations):
                    ui = user_integrations[index]
                    if ui.config is None:
                        ui.config = {}
                    ui.config['access_token'] = new_token
                    ui.save()
                    updated_count += 1
                    username = ui.user.username if hasattr(ui.user, 'username') else ui.user.email
                    print(f"✅ Token mis à jour pour {username}")
                else:
                    print("❌ Choix invalide.")
                    return
            except ValueError:
                print("❌ Veuillez entrer un numéro valide, 'a' pour toutes, ou 'q' pour quitter.")
                return
        
        print(f"\n✅ Opération terminée. {updated_count} intégration(s) mise(s) à jour.")
        
        # Vérifier si le token a été correctement stocké
        print("\nVérification du token mis à jour...")
        for ui in user_integrations:
            if ui.config and ui.config.get('access_token') == new_token:
                username = ui.user.username if hasattr(ui.user, 'username') else ui.user.email
                print(f"✓ Token correctement enregistré pour {username}")
        
        # Suggérer de tester l'intégration mise à jour
        print("\nPour tester si le token fonctionne correctement, exécutez:")
        print("python simple_slack_test.py")
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_slack_token() 