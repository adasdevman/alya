#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour la configuration des intégrations Gmail existantes.

Ce script ajoute les champs nécessaires (client_id, client_secret, redirect_uri, scopes)
aux configurations des intégrations Gmail existantes pour permettre
l'authentification et le rafraîchissement automatique des tokens.

Usage:
    python update_gmail_config.py
"""

import os
import sys
import json
import logging
import psycopg2
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gmail_update_config.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("gmail_config_update")

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables d'environnement chargées depuis .env")
except ImportError:
    print("⚠️ Module python-dotenv non trouvé, utilisation des variables d'environnement du système")

# Récupérer l'URL de la base de données depuis les variables d'environnement
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logger.error("Variable d'environnement DATABASE_URL non définie")
    # Essayer avec les composants individuels
    DB_NAME = os.environ.get('DB_NAME')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    if DB_NAME and DB_USER and DB_PASSWORD:
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        logger.info(f"URL de connexion construite à partir des composants individuels")
    else:
        logger.critical("Impossible de construire l'URL de connexion à la base de données. Vérifiez vos variables d'environnement.")
        sys.exit(1)

# Récupérer les identifiants Gmail depuis les variables d'environnement
GMAIL_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GMAIL_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
GMAIL_SCOPES = os.getenv('GMAIL_SCOPES', 'https://www.googleapis.com/auth/gmail.modify')

def update_gmail_configs():
    """Met à jour la configuration des intégrations Gmail"""
    conn = None
    
    try:
        # Vérifier si les identifiants Gmail sont disponibles
        if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REDIRECT_URI:
            print("❌ Identifiants Gmail non trouvés dans les variables d'environnement.")
            print("Les variables attendues sont GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET et GOOGLE_REDIRECT_URI.")
            print("Veuillez les ajouter dans votre fichier .env ou les définir dans l'environnement.")
            return False
        else:
            print(f"✅ Client ID récupéré: {GMAIL_CLIENT_ID}")
            print(f"✅ Client Secret récupéré: {GMAIL_CLIENT_SECRET[:5]}...{GMAIL_CLIENT_SECRET[-5:]}")
            print(f"✅ Redirect URI récupéré: {GMAIL_REDIRECT_URI}")
            print(f"✅ Scopes récupérés: {GMAIL_SCOPES}")
        
        # Connexion à la base de données
        print(f"🔄 Connexion à la base de données PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("✅ Connexion établie")
        
        # Trouver l'intégration Gmail
        cursor.execute("SELECT id, name FROM alyawebapp_integration WHERE name ILIKE '%gmail%' OR name ILIKE '%google%mail%'")
        integrations = cursor.fetchall()
        
        if not integrations:
            print("❌ Aucune intégration Gmail trouvée")
            return False
        
        print(f"✅ Intégration(s) Gmail trouvée(s): {[i[1] for i in integrations]}")
        
        updated_count = 0
        config_count = 0
        
        # Pour chaque intégration Gmail
        for integration_id, integration_name in integrations:
            # Trouver toutes les intégrations utilisateur pour cette intégration
            cursor.execute("""
                SELECT ui.id, ui.user_id, ui.config
                FROM alyawebapp_userintegration ui
                WHERE ui.integration_id = %s
            """, (integration_id,))
            
            user_integrations = cursor.fetchall()
            print(f"Nombre d'intégrations utilisateur trouvées pour {integration_name}: {len(user_integrations)}")
            
            for ui_id, user_id, config in user_integrations:
                config_count += 1
                try:
                    # Analyser la configuration
                    if not config:
                        config = {}
                    elif isinstance(config, str):
                        try:
                            config = json.loads(config)
                        except json.JSONDecodeError:
                            print(f"❌ Format JSON invalide pour la config de UserIntegration {ui_id}")
                            config = {}
                    
                    # Vérifier si les champs nécessaires sont présents et les ajouter si manquants
                    was_updated = False
                    
                    if 'client_id' not in config or not config['client_id']:
                        config['client_id'] = GMAIL_CLIENT_ID
                        was_updated = True
                        print(f"  ✓ Ajout de client_id à UserIntegration {ui_id}")
                    
                    if 'client_secret' not in config or not config['client_secret']:
                        config['client_secret'] = GMAIL_CLIENT_SECRET
                        was_updated = True
                        print(f"  ✓ Ajout de client_secret à UserIntegration {ui_id}")
                    
                    if 'redirect_uri' not in config or not config['redirect_uri']:
                        config['redirect_uri'] = GMAIL_REDIRECT_URI
                        was_updated = True
                        print(f"  ✓ Ajout de redirect_uri à UserIntegration {ui_id}")
                        
                    if 'scopes' not in config or not config['scopes']:
                        config['scopes'] = GMAIL_SCOPES
                        was_updated = True
                        print(f"  ✓ Ajout de scopes à UserIntegration {ui_id}")
                    
                    # Mise à jour de la base de données si des changements ont été faits
                    if was_updated:
                        # Vérifier si la table a une colonne 'updated_at'
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'alyawebapp_userintegration' 
                            AND column_name = 'updated_at'
                        """)
                        
                        has_updated_at = cursor.fetchone() is not None
                        
                        # Mise à jour de la base de données
                        if has_updated_at:
                            cursor.execute("""
                                UPDATE alyawebapp_userintegration
                                SET config = %s, updated_at = NOW()
                                WHERE id = %s
                            """, (json.dumps(config), ui_id))
                        else:
                            cursor.execute("""
                                UPDATE alyawebapp_userintegration
                                SET config = %s
                                WHERE id = %s
                            """, (json.dumps(config), ui_id))
                            
                        conn.commit()
                        print(f"✅ Configuration de UserIntegration {ui_id} (User {user_id}) mise à jour")
                        updated_count += 1
                    else:
                        print(f"ℹ️ Configuration de UserIntegration {ui_id} (User {user_id}) déjà à jour")
                
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de UserIntegration {ui_id}: {str(e)}")
                    conn.rollback()  # Annuler toute transaction en cours
        
        print(f"\n✅ Opération terminée. {updated_count}/{config_count} configurations mises à jour.")
        return True
        
    except Exception as e:
        print(f"❌ Erreur globale: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        if conn and conn.status != psycopg2.extensions.STATUS_READY:
            conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== MISE À JOUR DES CONFIGURATIONS GMAIL ===")
    result = update_gmail_configs()
    if result:
        print("\n✅ La mise à jour des configurations Gmail s'est terminée avec succès!")
        print("\nVous pouvez maintenant utiliser les intégrations Gmail avec le système d'authentification complet.")
    else:
        print("\n❌ L'opération a échoué. Veuillez vérifier les messages d'erreur.") 