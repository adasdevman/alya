#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier et rafraîchir automatiquement les tokens Slack.
Conçu pour être exécuté régulièrement via une tâche planifiée.

Ce script :
1. Se connecte à la base de données
2. Récupère toutes les intégrations Slack
3. Vérifie l'état de chaque token
4. Rafraîchit les tokens si nécessaire ou demandé

Usage: python check_and_refresh_slack_tokens.py [--force]
"""

import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime, timedelta
import psycopg2

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slack_token_refresh.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("slack_token_refresh")

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

def verify_token(token):
    """Vérifie si un token Slack est valide"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            "https://slack.com/api/auth.test",
            headers=headers
        )
        result = response.json()
        
        if not result.get('ok', False):
            error = result.get('error', 'unknown_error')
            logger.error(f"Token invalide: {error}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du token: {str(e)}")
        return False

def refresh_token(client_id, client_secret, refresh_token):
    """Rafraîchit un token Slack"""
    url = "https://slack.com/api/oauth.v2.access"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    
    try:
        logger.info("Envoi de la requête de rafraîchissement du token à Slack...")
        
        response = requests.post(url, data=data)
        
        # Vérifier le code de statut HTTP
        if response.status_code != 200:
            logger.error(f"Échec du rafraîchissement du token. Code de statut HTTP: {response.status_code}")
            try:
                result = response.json()
                error_info = result.get('error', 'unknown_error')
                error_desc = result.get('error_description', 'Pas de description disponible')
                logger.error(f"Erreur Slack: {error_info} - {error_desc}")
            except Exception as json_error:
                logger.error(f"Impossible de parser la réponse JSON: {str(json_error)}")
                logger.error(f"Contenu de la réponse: {response.text[:200]}")
            return None
        
        # Parser la réponse JSON
        try:
            result = response.json()
        except Exception as json_error:
            logger.error(f"Impossible de parser la réponse JSON: {str(json_error)}")
            logger.error(f"Contenu de la réponse: {response.text[:200]}")
            return None
        
        # Vérifier si l'opération a réussi
        if not result.get('ok', False):
            error_info = result.get('error', 'unknown_error')
            error_desc = result.get('error_description', 'Pas de description disponible')
            logger.error(f"Échec du rafraîchissement du token: {error_info} - {error_desc}")
            return None
            
        # Récupérer les nouveaux tokens
        new_access_token = result.get('access_token')
        new_refresh_token = result.get('refresh_token')
        
        if not new_access_token:
            logger.error("Le nouveau access_token est manquant dans la réponse")
            return None
            
        # Vérifier le format du nouveau token (pour le débogage)
        if new_access_token.startswith('xoxe.'):
            logger.info("Nouveau token au format xoxe (format attendu)")
        elif new_access_token.startswith(('xoxb-', 'xoxp-')):
            logger.info("Nouveau token au format xoxb/xoxp (format traditionnel)")
        else:
            logger.warning(f"Format de token inattendu: {new_access_token[:10]}...")
        
        # Préparer les données de retour
        token_data = {
            'access_token': new_access_token
        }
        
        if new_refresh_token:
            token_data['refresh_token'] = new_refresh_token
        
        logger.info("Token rafraîchi avec succès")
        return token_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur réseau lors du rafraîchissement du token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue lors du rafraîchissement du token: {str(e)}")
        return None

def check_and_refresh_tokens(force=False):
    """Vérifie et rafraîchit les tokens Slack dans la base de données"""
    conn = None
    
    try:
        # Connexion à la base de données
        logger.info("Connexion à la base de données PostgreSQL...")
        logger.info(f"URL de connexion: {DATABASE_URL[:20]}...{DATABASE_URL[-20:] if len(DATABASE_URL) > 40 else '(masquée)'}")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("Connexion établie")
        
        # Trouver l'intégration Slack
        cursor.execute("SELECT id, name FROM alyawebapp_integration WHERE name ILIKE '%slack%'")
        integrations = cursor.fetchall()
        
        if not integrations:
            logger.error("Aucune intégration Slack trouvée")
            return 0
        
        logger.info(f"Intégrations Slack trouvées: {[i[1] for i in integrations]}")
        
        # Pour chaque intégration Slack
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
                    
                    # Si nous avons une date d'expiration, vérifier si le token expire bientôt (moins de 1 heure)
                    if token_expiry and token_expiry - timedelta(hours=1) <= datetime.now():
                        logger.info(f"Token expirant bientôt pour UserIntegration {ui_id} (User {user_id})")
                        needs_refresh = True
                    
                    # Pour plus de sécurité, vérifier l'état réel du token
                    if not needs_refresh:
                        needs_refresh = not verify_token(access_token)
                    
                    if needs_refresh:
                        logger.info(f"Rafraîchissement du token pour UserIntegration {ui_id} (User {user_id})")
                        
                        # Tentative de rafraîchissement
                        token_data = refresh_token(client_id, client_secret, refresh_token_value)
                        
                        if token_data:
                            # Mise à jour de la base de données
                            new_access_token = token_data['access_token']
                            new_refresh_token = token_data.get('refresh_token')
                            
                            # Mettre à jour la configuration
                            if new_refresh_token:
                                config['refresh_token'] = new_refresh_token
                            
                            # Selon la documentation Slack, les tokens expirent après 12 heures (43200 secondes)
                            expiry_time = datetime.now() + timedelta(hours=12)
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
        
        return refreshed_count
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des tokens: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()
            logger.info("Connexion à la base de données fermée")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Vérifie et rafraîchit les tokens Slack")
    parser.add_argument('--force', action='store_true', help="Force le rafraîchissement de tous les tokens")
    args = parser.parse_args()
    
    if args.force:
        logger.info("Mode force activé: tous les tokens seront rafraîchis")
    
    # Vérifier et rafraîchir les tokens
    count = check_and_refresh_tokens(force=args.force)
    
    if count > 0:
        logger.info(f"{count} token(s) rafraîchi(s) avec succès")
    else:
        logger.info("Aucun token n'a été rafraîchi")

if __name__ == "__main__":
    main() 