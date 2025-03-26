#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simplifié pour tester l'envoi d'un message à Slack.
Usage: python test_message.py <token> [channel] [message]
"""

import sys
import requests

def send_test_message(token, channel="#general", message="Test message from Python script"):
    """Envoie un message test à Slack"""
    print(f"Envoi d'un message à {channel}")
    print(f"Token utilisé: {token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    data = {
        'channel': channel,
        'text': message
    }
    
    response = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers=headers,
        json=data
    )
    
    result = response.json()
    
    print("\nRésultat:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    if result.get('ok'):
        print("\n✅ Message envoyé avec succès!")
    else:
        print("\n❌ Échec de l'envoi du message!")
        error = result.get('error')
        
        if error == 'missing_scope':
            print("  → Permission manquante. Votre token n'a pas le scope 'chat:write'.")
            print("  → Réautorisez l'application avec les scopes nécessaires.")
        elif error == 'channel_not_found':
            print(f"  → Le canal '{channel}' n'existe pas ou n'est pas accessible.")
        elif error == 'not_in_channel':
            print(f"  → Le bot n'est pas membre du canal '{channel}'.")
            print("  → Invitez-le dans le canal avec /invite @votre_bot")
        elif error == 'invalid_auth':
            print("  → Token invalide ou expiré.")
        else:
            print(f"  → Erreur: {error}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_message.py <token> [channel] [message]")
        sys.exit(1)
    
    token = sys.argv[1]
    channel = sys.argv[2] if len(sys.argv) > 2 else "#general"
    message = sys.argv[3] if len(sys.argv) > 3 else "Message test depuis le script Python"
    
    send_test_message(token, channel, message) 