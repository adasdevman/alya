#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un lien d'autorisation OAuth pour Slack.
Version améliorée avec vérifications supplémentaires.
"""

import os
import urllib.parse
from dotenv import load_dotenv

# Forcer le rechargement des variables d'environnement
load_dotenv(override=True)

# Valeurs d'environnement
CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SLACK_REDIRECT_URI')

# Afficher les valeurs pour vérification
print("=== VARIABLES DÉTECTÉES ===")
print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {CLIENT_SECRET[:5]}...{CLIENT_SECRET[-5:] if CLIENT_SECRET else ''}")
print(f"Redirect URI: {REDIRECT_URI}")

# Vérification et demande interactive si nécessaire
if not CLIENT_ID:
    print("❌ SLACK_CLIENT_ID manquant. Utilisez l'ID mis à jour.")
    CLIENT_ID = input("Entrez le Client ID: ")

if not REDIRECT_URI:
    print("❌ SLACK_REDIRECT_URI manquant.")
    REDIRECT_URI = input("Entrez l'URI de redirection: ")

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
    "client_id": CLIENT_ID,
    "scope": ",".join(scopes),
    "redirect_uri": REDIRECT_URI,
    "user_scope": ""
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