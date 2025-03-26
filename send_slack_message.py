#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour envoyer un message test à Slack.
Récupère automatiquement le token depuis la configuration utilisateur.

Usage: python send_slack_message.py [channel] [message]
"""

import os
import sys
import json
import psycopg2
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(override=True)

def get_token_from_user_config():
    """
    Récupère le token Slack depuis la configuration utilisateur dans la base de données.
    """
    conn = None
    try:
        # Récupérer l'URL de la base de données depuis les variables d'environnement
        DATABASE_URL = os.environ.get('DATABASE_URL')
        
        if not DATABASE_URL:
            # Essayer avec les composants individuels
            DB_NAME = os.environ.get('DB_NAME')
            DB_USER = os.environ.get('DB_USER')
            DB_PASSWORD = os.environ.get('DB_PASSWORD')
            DB_HOST = os.environ.get('DB_HOST', 'localhost')
            DB_PORT = os.environ.get('DB_PORT', '5432')
            
            if DB_NAME and DB_USER and DB_PASSWORD:
                DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
                print(f"URL de connexion construite à partir des composants individuels")
            else:
                print("Impossible de construire l'URL de connexion à la base de données")
                return None
        
        print(f"Connexion à la base de données...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Récupérer l'intégration Slack
        cursor.execute("""
            SELECT i.id FROM alyawebapp_integration i 
            WHERE i.name ILIKE '%slack%'
        """)
        integration_result = cursor.fetchone()
        
        if not integration_result:
            print("Aucune intégration Slack trouvée dans la base de données")
            return None
        
        integration_id = integration_result[0]
        print(f"Intégration Slack trouvée avec ID: {integration_id}")
        
        # Lister les utilisateurs avec des intégrations Slack
        cursor.execute("""
            SELECT ui.id, ui.user_id, u.username 
            FROM alyawebapp_userintegration ui
            JOIN alyawebapp_customuser u ON ui.user_id = u.id
            WHERE ui.integration_id = %s AND ui.enabled = TRUE
        """, (integration_id,))
        
        users = cursor.fetchall()
        
        if not users:
            print("Aucun utilisateur avec intégration Slack activée n'a été trouvé")
            return None
        
        print("\nUtilisateurs disponibles:")
        for i, (ui_id, user_id, username) in enumerate(users, 1):
            print(f"{i}. {username} (ID: {user_id}, UI ID: {ui_id})")
        
        # Sélectionner un utilisateur
        try:
            selection = int(input("\nSélectionnez un utilisateur par son numéro: ").strip())
            selected_ui_id = users[selection-1][0]
        except (ValueError, IndexError):
            print("Sélection invalide. Utilisation du premier utilisateur.")
            selected_ui_id = users[0][0]
            
        # Récupérer la configuration pour l'utilisateur sélectionné
        cursor.execute("""
            SELECT ui.config FROM alyawebapp_userintegration ui
            WHERE ui.id = %s
        """, (selected_ui_id,))
        
        user_integration = cursor.fetchone()
        
        if not user_integration:
            print(f"Aucune configuration trouvée pour l'intégration utilisateur ID {selected_ui_id}")
            return None
        
        # Analyser la configuration
        config = user_integration[0]
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                print(f"Format JSON invalide pour la configuration")
                return None
        
        # Récupérer le token
        access_token = config.get('access_token')
        if access_token:
            print(f"Token trouvé: {access_token[:10]}...")
            return access_token
        else:
            print(f"Aucun token d'accès trouvé dans la configuration")
            return None
            
    except Exception as e:
        print(f"Erreur lors de la récupération du token: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None
    
    finally:
        if conn:
            conn.close()
            print("Connexion à la base de données fermée")

def send_slack_message(token, channel="#general", message="Message test depuis le script Python"):
    """Envoie un message à un canal Slack spécifié"""
    print(f"\nEnvoi d'un message à {channel} avec le token: {token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    payload = {
        'channel': channel,
        'text': message
    }
    
    try:
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload
        )
        
        result = response.json()
        
        print("\nRésultat de l'envoi du message:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        if result.get('ok'):
            print("\n✅ Message envoyé avec succès!")
            return True
        else:
            print("\n❌ Échec de l'envoi du message!")
            
            error = result.get('error')
            if error == 'channel_not_found':
                print(f"  → Le canal {channel} n'existe pas ou n'est pas accessible.")
            elif error == 'not_in_channel':
                print(f"  → Le bot n'est pas membre du canal {channel}. Invitez-le d'abord.")
            elif error == 'missing_scope':
                print("  → Les permissions nécessaires ne sont pas accordées.")
                print("  → Ajoutez le scope 'chat:write' et 'chat:write.public' dans les paramètres OAuth de votre app Slack.")
            elif error == 'invalid_auth':
                print("  → Le token est invalide ou a expiré.")
            else:
                print(f"  → Erreur: {error}")
            
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur lors de l'envoi du message: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== ENVOI DE MESSAGE SLACK ===\n")
    
    # Récupérer le token depuis la configuration utilisateur
    token = get_token_from_user_config()
    
    if not token:
        print("Impossible de récupérer un token valide. Veuillez vérifier la configuration.")
        sys.exit(1)
    
    # Récupérer le canal et le message des arguments ou demander à l'utilisateur
    channel = sys.argv[1] if len(sys.argv) > 1 else input("Entrez le nom du canal (par défaut: #general): ").strip() or "#general"
    message = sys.argv[2] if len(sys.argv) > 2 else input("Entrez le message à envoyer: ").strip() or "Test d'envoi de message depuis le script Python"
    
    # Envoyer le message
    send_slack_message(token, channel, message)
    
    print("\n=== OPÉRATION TERMINÉE ===") 