#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simple pour tester l'intégration Slack.
Ce script permet de vérifier si le token Slack a les bonnes permissions
et d'envoyer un message test si le token est valide.

Usage: python simple_slack_test.py
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def prompt_for_token():
    """Demande à l'utilisateur de saisir un token Slack"""
    print("\n=== Saisie du token Slack ===")
    token = input("Veuillez entrer votre token Slack: ").strip()
    return token

def test_token(token):
    """Teste un token Slack pour vérifier sa validité et ses permissions"""
    print(f"\n=== Test du token Slack ===")
    print(f"Utilisation du token: {token[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Vérifier l'authentification
    print("\n1. Test d'authentification...")
    try:
        response = requests.get("https://slack.com/api/auth.test", headers=headers)
        result = response.json()
        
        if result.get("ok"):
            print("✅ Token valide!")
            print(f"  Équipe: {result.get('team')}")
            print(f"  Utilisateur: {result.get('user')}")
            print(f"  ID utilisateur: {result.get('user_id')}")
            valid_token = True
        else:
            print("❌ Token invalide!")
            print(f"  Erreur: {result.get('error')}")
            valid_token = False
            
    except Exception as e:
        print(f"❌ Erreur lors du test d'authentification: {str(e)}")
        valid_token = False
    
    if not valid_token:
        return False
    
    # Test 2: Vérifier les scopes
    print("\n2. Vérification des scopes...")
    critical_scopes = ["chat:write", "channels:read", "users:read"]
    missing_scopes = []
    
    # Test chat:write
    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": "general", "text": "Test de permissions (ce message ne sera pas envoyé)"}
        )
        result = response.json()
        
        if result.get("error") == "missing_scope":
            print("❌ Le scope 'chat:write' est manquant")
            missing_scopes.append("chat:write")
        elif result.get("error") == "channel_not_found":
            print("✅ Scope 'chat:write' présent (mais canal non trouvé)")
        elif result.get("ok"):
            print("✅ Scope 'chat:write' présent")
        else:
            print(f"⚠️ Résultat chat.postMessage: {result.get('error')}")
    except Exception as e:
        print(f"❌ Erreur lors du test chat.postMessage: {str(e)}")
    
    # Test channels:read
    try:
        response = requests.get("https://slack.com/api/conversations.list", headers=headers)
        result = response.json()
        
        if result.get("error") == "missing_scope":
            print("❌ Le scope 'channels:read' est manquant")
            missing_scopes.append("channels:read")
        elif result.get("ok"):
            print(f"✅ Scope 'channels:read' présent ({len(result.get('channels', []))} canaux trouvés)")
        else:
            print(f"⚠️ Résultat conversations.list: {result.get('error')}")
    except Exception as e:
        print(f"❌ Erreur lors du test conversations.list: {str(e)}")
    
    # Test users:read
    try:
        response = requests.get("https://slack.com/api/users.list", headers=headers)
        result = response.json()
        
        if result.get("error") == "missing_scope":
            print("❌ Le scope 'users:read' est manquant")
            missing_scopes.append("users:read")
        elif result.get("ok"):
            print(f"✅ Scope 'users:read' présent ({len(result.get('members', []))} membres trouvés)")
        else:
            print(f"⚠️ Résultat users.list: {result.get('error')}")
    except Exception as e:
        print(f"❌ Erreur lors du test users.list: {str(e)}")
    
    if missing_scopes:
        print(f"\n⚠️ Certains scopes critiques sont manquants: {', '.join(missing_scopes)}")
        print("Veuillez réautoriser l'application avec TOUS les scopes nécessaires.")
        print("Utilisez le script create_slack_auth_link_with_scopes.py pour générer un lien d'autorisation complet.")
        return False
    
    return True

def send_test_message(token):
    """Envoie un message de test à un canal Slack"""
    print("\n=== Envoi d'un message test ===")
    
    # Demander le canal
    channel = input("Entrez le nom du canal (par défaut: #general): ").strip()
    if not channel:
        channel = "#general"
    
    # S'assurer que le canal commence par # s'il ne commence pas par @ (message direct)
    if not channel.startswith('#') and not channel.startswith('@'):
        channel = '#' + channel
    
    # Demander le message
    message = input("Entrez le message à envoyer (par défaut: Test depuis le script Python): ").strip()
    if not message:
        message = "Test depuis le script Python"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "channel": channel,
        "text": message
    }
    
    print(f"\nEnvoi du message au canal {channel}...")
    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=data
        )
        result = response.json()
        
        if result.get("ok"):
            print("✅ Message envoyé avec succès!")
            return True
        else:
            print(f"❌ Échec de l'envoi du message: {result.get('error')}")
            
            if result.get("error") == "channel_not_found":
                print(f"Le canal {channel} n'existe pas ou n'est pas accessible.")
            elif result.get("error") == "not_in_channel":
                print(f"Le bot n'est pas membre du canal {channel}. Ajoutez-le avec /invite @nom_du_bot")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi du message: {str(e)}")
        return False

def main():
    """Fonction principale"""
    print("=== TEST DE L'INTÉGRATION SLACK ===")
    
    # Récupérer le token depuis les variables d'environnement ou demander à l'utilisateur
    token = os.getenv("SLACK_ACCESS_TOKEN")
    
    if not token:
        token = prompt_for_token()
    
    if not token:
        print("❌ Aucun token fourni. Test annulé.")
        return
    
    # Tester le token
    if test_token(token):
        print("\n✅ Le token est valide et possède les permissions nécessaires!")
        
        # Demander si l'utilisateur souhaite envoyer un message test
        if input("\nVoulez-vous envoyer un message test? (o/n): ").lower() == 'o':
            send_test_message(token)
    else:
        print("\n❌ Le token n'est pas valide ou ne possède pas toutes les permissions nécessaires.")
        print("Veuillez utiliser le script create_slack_auth_link_with_scopes.py pour générer un lien d'autorisation complet.")

if __name__ == "__main__":
    main() 