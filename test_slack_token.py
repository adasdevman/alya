#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester un token Slack et vérifier ses scopes.
Usage: python test_slack_token.py [token]
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(override=True)

def test_slack_token(token=None):
    """Teste un token Slack et affiche les informations associées"""
    
    # Si aucun token n'est fourni en argument, chercher dans les variables d'environnement
    if not token:
        config = {}
        try:
            # Chercher dans la base de données ou les variables d'environnement
            token = os.getenv('SLACK_ACCESS_TOKEN')
            
            # Si toujours pas de token, demander à l'utilisateur
            if not token:
                token = input("Veuillez entrer votre token Slack: ")
                
        except Exception as e:
            print(f"Erreur lors de la récupération du token: {str(e)}")
            token = input("Veuillez entrer votre token Slack: ")
    
    # Afficher le début du token pour vérification
    print(f"Test du token: {token[:15]}...")
    
    # Configurer les en-têtes pour l'API Slack
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    print("\n1. Vérification de l'authentification...")
    try:
        # Tester l'authentification
        auth_response = requests.get('https://slack.com/api/auth.test', headers=headers)
        auth_result = auth_response.json()
        
        print("Résultat du test d'authentification:")
        for key, value in auth_result.items():
            print(f"  {key}: {value}")
        
        if auth_result.get('ok'):
            print("\n✅ Le token est VALIDE!")
            print(f"  → Équipe: {auth_result.get('team')}")
            print(f"  → Utilisateur: {auth_result.get('user')}")
            print(f"  → ID utilisateur: {auth_result.get('user_id')}")
            print(f"  → ID équipe: {auth_result.get('team_id')}")
            
            # Tester les scopes
            print("\n2. Vérification des scopes...")
            try:
                # Récupérer les informations sur les scopes
                scope_response = requests.get('https://slack.com/api/apps.auth.info', headers=headers)
                scope_result = scope_response.json()
                
                if scope_result.get('ok'):
                    scopes = scope_result.get('info', {}).get('scopes', [])
                    
                    print(f"Scopes associés au token ({len(scopes)}):")
                    for i, scope in enumerate(scopes, 1):
                        print(f"  {i}. {scope}")
                    
                    # Vérifier les scopes critiques
                    critical_scopes = {
                        'chat:write': "Envoyer des messages",
                        'chat:write.public': "Envoyer des messages dans les canaux publics",
                        'channels:read': "Lire les canaux",
                        'users:read': "Lire les informations des utilisateurs"
                    }
                    
                    print("\nVérification des scopes critiques:")
                    missing_scopes = []
                    for scope, description in critical_scopes.items():
                        if scope in scopes:
                            print(f"  ✓ {scope}: {description}")
                        else:
                            print(f"  ✗ {scope}: {description} - MANQUANT")
                            missing_scopes.append(scope)
                    
                    if missing_scopes:
                        print("\n⚠️ Certains scopes critiques sont manquants!")
                        print("  → Vous devriez réautoriser l'application avec les scopes manquants.")
                    else:
                        print("\n✅ Tous les scopes critiques sont présents!")
                else:
                    print(f"❌ Impossible de récupérer les scopes: {scope_result.get('error')}")
                    
                    # Test alternatif des permissions par API
                    print("\nTest alternatif des permissions par API:")
                    test_apis(headers)
            
            except Exception as e:
                print(f"❌ Erreur lors de la vérification des scopes: {str(e)}")
                # Test alternatif des permissions par API
                test_apis(headers)
            
            # Tester les canaux
            print("\n3. Liste des canaux disponibles...")
            try:
                channels_response = requests.get('https://slack.com/api/conversations.list', headers=headers)
                channels_result = channels_response.json()
                
                if channels_result.get('ok'):
                    channels = channels_result.get('channels', [])
                    print(f"✅ {len(channels)} canaux trouvés")
                    
                    if channels:
                        print("\nListe des 5 premiers canaux:")
                        for i, channel in enumerate(channels[:5], 1):
                            print(f"  {i}. #{channel.get('name')} (ID: {channel.get('id')})")
                else:
                    print(f"❌ Impossible de lister les canaux: {channels_result.get('error')}")
            except Exception as e:
                print(f"❌ Erreur lors de la récupération des canaux: {str(e)}")
        else:
            print("\n❌ Le token est INVALIDE!")
            error = auth_result.get('error')
            print(f"  → Erreur: {error}")
            
            if error == 'invalid_auth':
                print("  → Le token est invalide ou a expiré. Vous devez réautoriser l'application.")
            elif error == 'not_authed':
                print("  → Aucun token d'authentification fourni.")
            elif error == 'token_expired':
                print("  → Le token a expiré et ne peut plus être utilisé.")
            elif error == 'token_revoked':
                print("  → Le token a été révoqué.")
    
    except Exception as e:
        print(f"❌ Erreur lors du test du token: {str(e)}")
    
    return auth_result if 'auth_result' in locals() else {'ok': False, 'error': 'request_failed'}

def test_apis(headers):
    """Teste différentes API pour déterminer les permissions"""
    
    # Test 1: Conversations List (channels:read)
    test_response = requests.get('https://slack.com/api/conversations.list', headers=headers)
    result = test_response.json()
    if result.get('ok'):
        print("  ✓ conversations.list (channels:read): OK")
    else:
        print(f"  ✗ conversations.list (channels:read): {result.get('error')}")
    
    # Test 2: Users List (users:read)
    test_response = requests.get('https://slack.com/api/users.list', headers=headers)
    result = test_response.json()
    if result.get('ok'):
        print("  ✓ users.list (users:read): OK")
    else:
        print(f"  ✗ users.list (users:read): {result.get('error')}")
    
    # Test 3: Post Message (chat:write)
    test_response = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers=headers,
        json={
            'channel': 'general',
            'text': 'Test de permission - Ce message ne sera pas envoyé'
        }
    )
    result = test_response.json()
    if result.get('ok'):
        print("  ✓ chat.postMessage (chat:write): OK")
    elif result.get('error') == 'channel_not_found':
        print("  ✓ chat.postMessage (chat:write): Permission OK (canal non trouvé)")
    elif result.get('error') == 'missing_scope':
        print("  ✗ chat.postMessage (chat:write): Permission manquante")
    else:
        print(f"  ? chat.postMessage (chat:write): {result.get('error')}")

if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else None
    test_slack_token(token) 