#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un lien d'autorisation OAuth pour Slack avec tous les scopes nécessaires.

Ce script génère un lien que vous pouvez ouvrir dans votre navigateur pour réautoriser
votre application Slack avec TOUS les scopes nécessaires pour le bon fonctionnement.

Usage:
    python create_slack_auth_link_with_scopes.py
"""

import os
import urllib.parse
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def create_slack_auth_link():
    """
    Génère un lien d'autorisation OAuth pour Slack avec TOUS les scopes nécessaires.
    """
    print("Génération d'un lien d'autorisation OAuth complet pour Slack...")
    
    # Récupérer les informations de configuration depuis .env
    client_id = os.getenv('SLACK_CLIENT_ID')
    redirect_uri = os.getenv('SLACK_REDIRECT_URI')
    
    if not client_id:
        print("❌ SLACK_CLIENT_ID non trouvé dans les variables d'environnement.")
        client_id = input("Veuillez entrer le Client ID de votre application Slack: ")
    
    if not redirect_uri:
        print("❌ SLACK_REDIRECT_URI non trouvé dans les variables d'environnement.")
        redirect_uri = input("Veuillez entrer l'URI de redirection de votre application Slack: ")
    
    # Définir TOUS les scopes nécessaires
    scopes = [
        "channels:read",
        "channels:history",
        "chat:write",
        "chat:write.public",
        "users:read",
        "reactions:read",
        "team:read",
        "groups:read"
    ]
    
    # Construire le lien d'autorisation
    auth_url = "https://slack.com/oauth/v2/authorize"
    params = {
        "client_id": client_id,
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
        "user_scope": "",  # Pas de scopes utilisateur nécessaires pour les bots
        "state": "state-Scopes demandés:\n\n      1. " + "\n  2. ".join(scopes)
    }
    
    full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    print(f"\n{full_url}")
    print("\nScopes demandés:")
    for i, scope in enumerate(scopes, 1):
        print(f"  {i}. {scope}")
    
    print("\nInstructions:")
    print("1. Copiez ce lien et ouvrez-le dans votre navigateur")
    print("2. Connectez-vous à votre espace de travail Slack si nécessaire")
    print("3. VÉRIFIEZ que tous les scopes demandés sont listés dans l'écran d'autorisation")
    print("4. Cliquez sur 'Autoriser' pour approuver TOUS ces scopes")
    print("5. Vous serez redirigé vers l'URI de redirection spécifié")
    print("6. Récupérez le nouveau token d'accès depuis la réponse ou depuis le dashboard de votre application")
    print("7. Mettez à jour votre configuration avec le nouveau token qui aura TOUS les scopes nécessaires")
    
    return full_url

if __name__ == "__main__":
    create_slack_auth_link() 