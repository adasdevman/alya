#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier les variables d'environnement Slack.
"""

import os
from dotenv import load_dotenv

# Forcer le rechargement des variables d'environnement
load_dotenv(override=True)

print("=== VARIABLES D'ENVIRONNEMENT SLACK ===")
print(f"SLACK_CLIENT_ID: {os.getenv('SLACK_CLIENT_ID')}")
print(f"SLACK_CLIENT_SECRET: {os.getenv('SLACK_CLIENT_SECRET')} (tronqué pour sécurité)")
print(f"SLACK_REDIRECT_URI: {os.getenv('SLACK_REDIRECT_URI')}")

print("\n=== AUTRES VARIABLES D'INTÉRÊT ===")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Non défini')[:30]}... (tronqué)")
print(f"DEBUG: {os.getenv('DEBUG', 'Non défini')}") 