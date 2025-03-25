#!/usr/bin/env python
"""
Script pour mettre à jour la configuration des intégrations HubSpot
afin d'ajouter les paramètres nécessaires au rafraîchissement automatique.

Ce script ajoute les champs client_id et client_secret dans la configuration
des intégrations HubSpot si le refresh_token existe déjà. Les valeurs sont
récupérées depuis le fichier .env.

Utilisation: python update_hubspot_config.py
"""

import os
import sys
import json
import psycopg2
from datetime import datetime, timedelta

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables d'environnement chargées depuis .env")
except ImportError:
    print("⚠️ Module python-dotenv non trouvé, utilisation des variables d'environnement du système")

# URL de connexion à la base de données (depuis l'environnement)
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://dataia_user:bjVMSjlujw45wmfqW23hVI7jexaroBgW@dpg-cufhqdogph6c73845rcg-a.oregon-postgres.render.com/dataia")

# Récupérer les identifiants HubSpot depuis les variables d'environnement
HUBSPOT_CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')

# Vérifier d'autres noms possibles pour les variables
if not HUBSPOT_CLIENT_ID:
    HUBSPOT_CLIENT_ID = os.getenv('HUBAPI_CLIENT_ID') or os.getenv('HS_CLIENT_ID')
if not HUBSPOT_CLIENT_SECRET:
    HUBSPOT_CLIENT_SECRET = os.getenv('HUBAPI_CLIENT_SECRET') or os.getenv('HS_CLIENT_SECRET')

def update_hubspot_config():
    """Met à jour la configuration des intégrations HubSpot"""
    conn = None
    
    try:
        # Vérifier si les identifiants HubSpot sont disponibles
        if not HUBSPOT_CLIENT_ID or not HUBSPOT_CLIENT_SECRET:
            print("❌ Client ID et/ou Client Secret non trouvés dans les variables d'environnement.")
            print("Les variables attendues sont HUBSPOT_CLIENT_ID et HUBSPOT_CLIENT_SECRET.")
            user_choice = input("Voulez-vous saisir ces informations manuellement? (o/n): ").strip().lower()
            
            if user_choice != 'o':
                print("❌ Opération annulée.")
                return False
            
            client_id = input("Client ID: ").strip()
            client_secret = input("Client Secret: ").strip()
            
            if not client_id or not client_secret:
                print("❌ Client ID et Client Secret sont requis")
                return False
        else:
            client_id = HUBSPOT_CLIENT_ID
            client_secret = HUBSPOT_CLIENT_SECRET
            print(f"✅ Client ID récupéré: {client_id[:5]}...{client_id[-5:] if len(client_id) > 10 else client_id}")
            print(f"✅ Client Secret récupéré: {client_secret[:3]}...{client_secret[-3:] if len(client_secret) > 6 else '*'*len(client_secret)}")
        
        # Connexion à la base de données
        print(f"🔄 Connexion à la base de données PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("✅ Connexion établie")
        
        # Trouver l'intégration HubSpot
        cursor.execute("SELECT id, name FROM alyawebapp_integration WHERE name ILIKE '%hubspot%'")
        integrations = cursor.fetchall()
        
        if not integrations:
            print("❌ Aucune intégration HubSpot trouvée")
            return False
        
        print(f"✅ Intégrations HubSpot trouvées: {[i[1] for i in integrations]}")
        
        # Pour chaque intégration HubSpot
        updated_count = 0
        for integration_id, integration_name in integrations:
            # Trouver toutes les intégrations utilisateur pour cette intégration
            cursor.execute("""
                SELECT ui.id, ui.user_id, ui.config
                FROM alyawebapp_userintegration ui
                WHERE ui.integration_id = %s AND ui.enabled = TRUE
            """, (integration_id,))
            
            user_integrations = cursor.fetchall()
            print(f"Nombre d'intégrations utilisateur trouvées pour {integration_name}: {len(user_integrations)}")
            
            for ui_id, user_id, config in user_integrations:
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
                    
                    # Vérifier si refresh_token existe
                    refresh_token = config.get('refresh_token')
                    if not refresh_token:
                        print(f"⚠️ UserIntegration {ui_id} (User {user_id}) n'a pas de refresh_token. Ignoré.")
                        continue
                    
                    # Ajouter client_id et client_secret
                    config['client_id'] = client_id
                    config['client_secret'] = client_secret
                    
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
                    
                    # Ajouter une date d'expiration valide
                    expiry_time = datetime.now() + timedelta(minutes=30)
                    config['token_expiry'] = expiry_time.isoformat()
                    
                    conn.commit()
                    
                    print(f"✅ Configuration mise à jour pour UserIntegration {ui_id} (User {user_id})")
                    updated_count += 1
                
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de UserIntegration {ui_id}: {str(e)}")
                    conn.rollback()  # Annuler toute transaction en cours
        
        print(f"\n✅ Opération terminée. {updated_count} configurations mises à jour.")
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
    try:
        print("=== MISE À JOUR DE LA CONFIGURATION HUBSPOT ===")
        result = update_hubspot_config()
        if result:
            print("\n✅ Opération terminée avec succès!")
            print("\nVous pouvez maintenant exécuter check_and_refresh_hubspot_tokens.py pour tester le rafraîchissement automatique.")
        else:
            print("\n❌ Opération échouée ou annulée.")
    except KeyboardInterrupt:
        print("\nOpération annulée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {str(e)}")
        import traceback
        print(traceback.format_exc()) 