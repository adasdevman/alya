#!/usr/bin/env python
"""
Script pour vérifier et rafraîchir automatiquement les tokens HubSpot.
Ce script est conçu pour être exécuté régulièrement via une tâche planifiée
(cron job, task scheduler, etc.).

Il vérifie les tokens HubSpot dans la base de données et tente de les
rafraîchir automatiquement s'ils sont expirés ou sur le point d'expirer.

Utilisation: python check_and_refresh_hubspot_tokens.py [--force]
Options:
  --force : Force le rafraîchissement de tous les tokens, même s'ils ne sont pas expirés
"""

import os
import sys
import json
import logging
import argparse
import psycopg2
import requests
from datetime import datetime, timedelta

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Ne pas logger ici pour éviter de polluer les logs avec cette information à chaque exécution
except ImportError:
    pass  # Continuer silencieusement si python-dotenv n'est pas installé

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('hubspot_token_refresh.log')
    ]
)
logger = logging.getLogger('hubspot_token_refresh')

# URL de connexion à la base de données (depuis l'environnement)
DATABASE_URL = os.getenv('DATABASE_URL')
# Fallback sur d'autres variables possibles
if not DATABASE_URL:
    DATABASE_URL = os.getenv('POSTGRES_URL') or os.getenv('DB_URL')
# Valeur par défaut comme dernier recours
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dataia_user:bjVMSjlujw45wmfqW23hVI7jexaroBgW@dpg-cufhqdogph6c73845rcg-a.oregon-postgres.render.com/dataia"

def verify_token(access_token):
    """Vérifie la validité du token HubSpot"""
    try:
        logger.info(f"Vérification de la validité du token: {access_token[:10]}... (tronqué)")
        
        # Utiliser un endpoint réel pour vérifier le token
        url = "https://api.hubapi.com/crm/v3/properties/contact"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        logger.info(f"Code de statut de la réponse: {response.status_code}")
        
        # Si nous obtenons 401 ou 403, le token est invalide
        if response.status_code in [401, 403]:
            logger.error(f"Token invalide: {response.status_code}")
            return False
        
        # Si le code est 200, le token est certainement valide
        if response.status_code == 200:
            logger.info(f"Le token est valide (code 200)")
            return True
            
        # Pour les autres codes, on considère le token comme valide mais on log l'anomalie
        logger.info(f"Le token semble valide mais code inhabituel: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du token: {str(e)}")
        return False

def refresh_token(client_id, client_secret, refresh_token):
    """Rafraîchit le token HubSpot en utilisant le refresh_token"""
    try:
        # Faire l'appel API à HubSpot pour rafraîchir le token
        url = "https://api.hubapi.com/oauth/v1/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token
        }
        
        logger.info("Envoi de la requête de rafraîchissement du token")
        response = requests.post(url, data=data)
        
        if response.status_code != 200:
            logger.error(f"Échec du rafraîchissement du token: {response.status_code} - {response.text[:200]}")
            return None
        
        # Extraire les nouvelles valeurs de token
        token_data = response.json()
        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')  # HubSpot fournit aussi un nouveau refresh_token
        expires_in = token_data.get('expires_in', 1800)  # Par défaut 30 minutes si non spécifié
        
        if not new_access_token:
            logger.error("Pas d'access_token dans la réponse")
            return None
        
        logger.info("Token rafraîchi avec succès")
        
        return {
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'expires_in': expires_in
        }
            
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def check_and_refresh_tokens(force=False):
    """Vérifie et rafraîchit les tokens HubSpot dans la base de données"""
    conn = None
    
    try:
        # Connexion à la base de données
        logger.info("Connexion à la base de données PostgreSQL...")
        logger.info(f"URL de connexion: {DATABASE_URL[:20]}...{DATABASE_URL[-20:] if len(DATABASE_URL) > 40 else '(masquée)'}")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("Connexion établie")
        
        # Trouver l'intégration HubSpot
        cursor.execute("SELECT id, name FROM alyawebapp_integration WHERE name ILIKE '%hubspot%'")
        integrations = cursor.fetchall()
        
        if not integrations:
            logger.error("Aucune intégration HubSpot trouvée")
            return 0
        
        logger.info(f"Intégrations HubSpot trouvées: {[i[1] for i in integrations]}")
        
        # Pour chaque intégration HubSpot
        refreshed_count = 0
        for integration_id, integration_name in integrations:
            # Trouver toutes les intégrations utilisateur pour cette intégration
            cursor.execute("""
                SELECT ui.id, ui.user_id, ui.access_token, ui.config, ui.enabled
                FROM alyawebapp_userintegration ui
                WHERE ui.integration_id = %s AND ui.enabled = TRUE
            """, (integration_id,))
            
            user_integrations = cursor.fetchall()
            logger.info(f"Nombre d'intégrations utilisateur trouvées pour {integration_name}: {len(user_integrations)}")
            
            for ui_id, user_id, access_token, config, enabled in user_integrations:
                if access_token is None or not access_token.strip():
                    logger.warning(f"UserIntegration {ui_id} (User {user_id}) n'a pas d'access_token. Ignoré.")
                    continue
                
                try:
                    # Analyser la configuration
                    if not config:
                        config = {}
                    elif isinstance(config, str):
                        try:
                            config = json.loads(config)
                        except json.JSONDecodeError:
                            logger.error(f"Format JSON invalide pour la config de UserIntegration {ui_id}")
                            config = {}
                    
                    token_expiry = None
                    if 'token_expiry' in config:
                        try:
                            token_expiry = datetime.fromisoformat(config['token_expiry'])
                        except (ValueError, TypeError):
                            logger.error(f"Format de date invalide pour token_expiry: {config.get('token_expiry')}")
                    
                    refresh_token_value = config.get('refresh_token')
                    client_id = config.get('client_id')
                    client_secret = config.get('client_secret')
                    
                    # Vérifier si les informations requises sont présentes
                    if not (refresh_token_value and client_id and client_secret):
                        logger.warning(f"UserIntegration {ui_id} (User {user_id}) manque d'informations pour le rafraîchissement (refresh_token, client_id ou client_secret)")
                        continue
                    
                    # Déterminer si le token doit être rafraîchi
                    needs_refresh = force
                    if not needs_refresh:
                        if token_expiry is None:
                            # Si pas de date d'expiration, vérifier le token
                            needs_refresh = not verify_token(access_token)
                        else:
                            # Si date d'expiration, vérifier si c'est dans moins de 30 minutes
                            now = datetime.now()
                            time_to_expiry = token_expiry - now
                            if time_to_expiry < timedelta(minutes=30):
                                logger.info(f"Token expirant bientôt: {time_to_expiry}")
                                needs_refresh = True
                    
                    if needs_refresh:
                        logger.info(f"Rafraîchissement du token pour UserIntegration {ui_id} (User {user_id})")
                        
                        # Tentative de rafraîchissement
                        token_data = refresh_token(client_id, client_secret, refresh_token_value)
                        
                        if token_data:
                            # Mise à jour de la base de données
                            new_access_token = token_data['access_token']
                            new_refresh_token = token_data.get('refresh_token')
                            expires_in = token_data.get('expires_in')
                            
                            # Mettre à jour la configuration
                            if new_refresh_token:
                                config['refresh_token'] = new_refresh_token
                            
                            # Calculer et stocker la date d'expiration avec une marge de sécurité
                            expiry_time = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 minutes de marge
                            config['token_expiry'] = expiry_time.isoformat()
                            
                            # Supprimer les marqueurs d'échec si présents
                            if 'refresh_failure_time' in config:
                                del config['refresh_failure_time']
                            if 'refresh_errors' in config:
                                del config['refresh_errors']
                            
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
                                    SET access_token = %s, config = %s, updated_at = NOW()
                                    WHERE id = %s
                                """, (new_access_token, json.dumps(config), ui_id))
                            else:
                                cursor.execute("""
                                    UPDATE alyawebapp_userintegration
                                    SET access_token = %s, config = %s
                                    WHERE id = %s
                                """, (new_access_token, json.dumps(config), ui_id))
                            
                            conn.commit()
                            
                            logger.info(f"Token mis à jour pour UserIntegration {ui_id} (User {user_id})")
                            refreshed_count += 1
                        else:
                            logger.error(f"Échec du rafraîchissement pour UserIntegration {ui_id} (User {user_id})")
                            
                            # Marquer l'échec dans la config
                            config['refresh_failure_time'] = datetime.now().isoformat()
                            
                            if not config.get('refresh_errors'):
                                config['refresh_errors'] = []
                            
                            config['refresh_errors'].append({
                                'timestamp': datetime.now().isoformat(),
                                'message': "Échec du rafraîchissement automatique"
                            })
                            
                            # Limiter la taille de l'historique des erreurs
                            if len(config['refresh_errors']) > 5:
                                config['refresh_errors'] = config['refresh_errors'][-5:]
                            
                            # Mise à jour de la config seulement
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
                    else:
                        logger.info(f"Aucun rafraîchissement nécessaire pour UserIntegration {ui_id} (User {user_id})")
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de UserIntegration {ui_id}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    conn.rollback()  # Annuler toute transaction en cours
        
        logger.info(f"Opération terminée. {refreshed_count} tokens rafraîchis.")
        return refreshed_count
        
    except Exception as e:
        logger.error(f"Erreur globale: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        if conn and conn.status != psycopg2.extensions.STATUS_READY:
            conn.rollback()
        return 0
    
    finally:
        if conn:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Vérifie et rafraîchit les tokens HubSpot.')
    parser.add_argument('--force', action='store_true', help='Force le rafraîchissement de tous les tokens')
    args = parser.parse_args()
    
    logger.info("=== VÉRIFICATION ET RAFRAÎCHISSEMENT DES TOKENS HUBSPOT ===")
    
    if args.force:
        logger.info("Mode force activé: tous les tokens seront rafraîchis")
    
    count = check_and_refresh_tokens(force=args.force)
    
    if count > 0:
        logger.info(f"{count} tokens ont été rafraîchis avec succès")
    else:
        logger.info("Aucun token n'a été rafraîchi")
    
    logger.info("=== OPÉRATION TERMINÉE ===")

if __name__ == "__main__":
    main() 