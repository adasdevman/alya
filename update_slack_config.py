#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour la configuration des intégrations Slack existantes.

Ce script ajoute les champs nécessaires (client_id, client_secret) aux configurations
des intégrations Slack existantes pour permettre le rafraîchissement automatique des tokens.

Usage:
    python update_slack_config.py [options]

Options:
    --dry-run       Affiche les modifications sans les appliquer
    --client-id     Spécifie le Client ID à utiliser (sinon demandé en interactif)
    --client-secret Spécifie le Client Secret à utiliser (sinon demandé en interactif)
"""

import os
import sys
import json
import logging
import argparse
import getpass
import psycopg2
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slack_update_config.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("slack_config_update")

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

def update_slack_configs(client_id, client_secret, dry_run=False):
    """
    Met à jour la configuration des intégrations Slack existantes.
    
    Args:
        client_id (str): L'ID client de l'application Slack
        client_secret (str): Le secret client de l'application Slack
        dry_run (bool): Si True, affiche les modifications sans les appliquer
        
    Returns:
        int: Le nombre d'intégrations mises à jour
    """
    conn = None
    updated_count = 0
    
    try:
        # Connexion à la base de données
        logger.info("Connexion à la base de données PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("Connexion établie")
        
        # Trouver l'intégration Slack
        cursor.execute("SELECT id, name FROM alyawebapp_integration WHERE name ILIKE '%slack%'")
        integrations = cursor.fetchall()
        
        if not integrations:
            logger.error("Aucune intégration Slack trouvée")
            return 0
        
        logger.info(f"Intégrations Slack trouvées: {len(integrations)}")
        
        # Pour chaque intégration Slack
        for integration_id, integration_name in integrations:
            logger.info(f"Mise à jour de l'intégration: {integration_name} (ID: {integration_id})")
            
            # Trouver toutes les intégrations utilisateur pour cette intégration
            cursor.execute("""
                SELECT ui.id, ui.user_id, ui.access_token, ui.config, ui.enabled
                FROM alyawebapp_userintegration ui
                WHERE ui.integration_id = %s
            """, (integration_id,))
            
            user_integrations = cursor.fetchall()
            logger.info(f"Nombre d'intégrations utilisateur trouvées: {len(user_integrations)}")
            
            for ui_id, user_id, access_token, config, enabled in user_integrations:
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
                    
                    # Vérifier si les champs nécessaires sont déjà présents
                    has_client_id = 'client_id' in config and config['client_id']
                    has_client_secret = 'client_secret' in config and config['client_secret']
                    has_refresh_token = 'refresh_token' in config and config['refresh_token']
                    
                    # Préparer le message de statut
                    status = []
                    if has_client_id:
                        status.append("client_id existant")
                    if has_client_secret:
                        status.append("client_secret existant")
                    if has_refresh_token:
                        status.append("refresh_token existant")
                    
                    if not status:
                        status = ["Aucun champ d'authentification trouvé"]
                    
                    logger.info(f"UserIntegration {ui_id} (User {user_id}): {', '.join(status)}")
                    
                    # Mise à jour de la configuration
                    was_updated = False
                    
                    if not has_client_id:
                        config['client_id'] = client_id
                        was_updated = True
                        logger.info(f"Ajout de client_id à UserIntegration {ui_id}")
                    
                    if not has_client_secret:
                        config['client_secret'] = client_secret
                        was_updated = True
                        logger.info(f"Ajout de client_secret à UserIntegration {ui_id}")
                    
                    # Ajouter une date d'expiration artificielle pour forcer une vérification au prochain lancement
                    if 'token_expiry' not in config or not config['token_expiry']:
                        # Expiration dans 1 heure pour forcer la vérification
                        expiry_time = datetime.now() + timedelta(hours=1)
                        config['token_expiry'] = expiry_time.isoformat()
                        was_updated = True
                        logger.info(f"Ajout d'une date d'expiration à UserIntegration {ui_id}")
                    
                    if was_updated:
                        if not dry_run:
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
                            logger.info(f"UserIntegration {ui_id} mise à jour avec succès")
                            updated_count += 1
                        else:
                            logger.info(f"[DRY RUN] UserIntegration {ui_id} serait mise à jour")
                            updated_count += 1
                    else:
                        logger.info(f"UserIntegration {ui_id} n'a pas besoin de mise à jour")
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de UserIntegration {ui_id}: {str(e)}")
                    if not dry_run and conn:
                        conn.rollback()
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des configurations: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()
            logger.info("Connexion à la base de données fermée")

def get_credentials(args):
    """
    Récupère les identifiants client Slack, soit des arguments en ligne de commande, soit interactivement.
    
    Args:
        args (Namespace): Arguments de ligne de commande
        
    Returns:
        tuple: (client_id, client_secret)
    """
    client_id = args.client_id
    client_secret = args.client_secret
    
    if not client_id:
        client_id = input("Entrez le Client ID de votre application Slack: ")
    
    if not client_secret:
        client_secret = getpass.getpass("Entrez le Client Secret de votre application Slack: ")
    
    return client_id, client_secret

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Met à jour la configuration des intégrations Slack existantes")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les modifications sans les appliquer")
    parser.add_argument("--client-id", type=str, help="Client ID de l'application Slack")
    parser.add_argument("--client-secret", type=str, help="Client Secret de l'application Slack")
    args = parser.parse_args()
    
    logger.info("=== MISE À JOUR DES CONFIGURATIONS SLACK ===")
    
    if args.dry_run:
        logger.info("Mode dry-run activé: aucune modification ne sera appliquée")
    
    # Obtenir les identifiants client
    client_id, client_secret = get_credentials(args)
    
    if not client_id or not client_secret:
        logger.error("Client ID et Client Secret sont requis pour continuer")
        sys.exit(1)
    
    # Mise à jour des configurations
    updated_count = update_slack_configs(client_id, client_secret, dry_run=args.dry_run)
    
    if updated_count > 0:
        if args.dry_run:
            logger.info(f"{updated_count} intégration(s) seraient mise(s) à jour")
        else:
            logger.info(f"{updated_count} intégration(s) mise(s) à jour avec succès")
    else:
        logger.info("Aucune intégration n'a été mise à jour")
    
    logger.info("=== OPÉRATION TERMINÉE ===")

if __name__ == "__main__":
    main() 