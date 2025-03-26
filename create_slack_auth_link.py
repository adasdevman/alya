#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un lien d'autorisation OAuth pour Slack.

Ce script génère un lien que vous pouvez ouvrir dans votre navigateur pour réautoriser
votre application Slack avec les scopes nécessaires.

Usage:
    python create_slack_auth_link.py
"""

import os
import urllib.parse
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def create_slack_auth_link():
    """
    Génère un lien d'autorisation OAuth pour Slack avec les scopes nécessaires.
    """
    # Récupérer les informations de configuration depuis .env
    client_id = os.getenv('SLACK_CLIENT_ID')
    redirect_uri = os.getenv('SLACK_REDIRECT_URI')
    
    if not client_id:
        print("❌ SLACK_CLIENT_ID non trouvé dans les variables d'environnement.")
        client_id = input("Veuillez entrer le Client ID de votre application Slack: ")
    
    if not redirect_uri:
        print("❌ SLACK_REDIRECT_URI non trouvé dans les variables d'environnement.")
        redirect_uri = input("Veuillez entrer l'URI de redirection de votre application Slack: ")
    
    # Définir les scopes nécessaires
    scopes = [
        "channels:read",
        "chat:write",
        "chat:write.public",
        "users:read"
    ]
    
    # Construire le lien d'autorisation
    auth_url = "https://slack.com/oauth/v2/authorize"
    params = {
        "client_id": client_id,
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
        "user_scope": ""  # Pas de scopes utilisateur nécessaires pour les bots
    }
    
    full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    print("\n=== LIEN D'AUTORISATION SLACK ===")
    print("\nVoici le lien pour autoriser votre application Slack avec les scopes nécessaires:")
    print(f"\n{full_url}\n")
    print("Instructions:")
    print("1. Copiez ce lien et ouvrez-le dans votre navigateur")
    print("2. Connectez-vous à votre espace de travail Slack si nécessaire")
    print("3. Vérifiez que les scopes demandés sont corrects et autorisez l'application")
    print("4. Vous serez redirigé vers l'URI de redirection spécifié")
    print("5. Récupérez le nouveau token d'accès depuis la réponse ou depuis le dashboard de votre application")
    
    return full_url

if __name__ == "__main__":
    print("Génération d'un lien d'autorisation OAuth pour Slack...")
    create_slack_auth_link() 