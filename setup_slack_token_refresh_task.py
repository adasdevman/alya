#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour configurer une tâche planifiée de rafraîchissement des tokens Slack.

Ce script configure une tâche planifiée (cron pour Linux, Task Scheduler pour Windows)
qui exécutera régulièrement le script check_and_refresh_slack_tokens.py pour maintenir
les tokens Slack à jour.

Usage:
    python setup_slack_token_refresh_task.py [options]

Options:
    --interval HOURS     Intervalle de vérification en heures (défaut: 4)
    --test               Exécute une fois le script de rafraîchissement pour vérifier son fonctionnement
    --no-install         Ne configure pas la tâche planifiée, seulement test si demandé
"""

import os
import sys
import argparse
import logging
import subprocess
import platform
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slack_setup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("slack_token_setup")

# Chemins des scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REFRESH_SCRIPT = os.path.join(SCRIPT_DIR, "check_and_refresh_slack_tokens.py")

def setup_windows_task(interval_hours):
    """Configure une tâche planifiée sous Windows"""
    if not os.path.exists(REFRESH_SCRIPT):
        logger.error(f"Le script {REFRESH_SCRIPT} n'existe pas")
        return False
    
    # Obtenir le chemin Python actuel
    python_exe = sys.executable
    if not python_exe:
        logger.error("Impossible de déterminer le chemin de l'exécutable Python")
        return False
    
    # Préparer la commande pour créer la tâche
    task_name = "SlackTokenRefresh"
    start_time = datetime.now().strftime("%H:%M")
    
    # Le chemin complet de la commande à exécuter
    command = f'"{python_exe}" "{REFRESH_SCRIPT}"'
    
    # La commande pour créer la tâche planifiée
    create_task_cmd = [
        "schtasks", "/create", "/f",
        "/tn", task_name,
        "/tr", command,
        "/sc", "hourly",
        "/mo", str(interval_hours),
        "/st", start_time
    ]
    
    try:
        logger.info(f"Création de la tâche planifiée Windows: {' '.join(create_task_cmd)}")
        result = subprocess.run(create_task_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de la création de la tâche: {result.stderr}")
            return False
        
        logger.info(f"Tâche planifiée créée avec succès: {result.stdout}")
        
        # Vérifier que la tâche existe
        check_cmd = ["schtasks", "/query", "/tn", task_name]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0:
            logger.error(f"La tâche a été créée mais n'est pas visible: {check_result.stderr}")
            return False
        
        logger.info("La tâche a été correctement configurée et est visible dans le planificateur de tâches")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de la tâche Windows: {str(e)}")
        return False

def setup_linux_cron(interval_hours):
    """Configure un job cron sous Linux"""
    if not os.path.exists(REFRESH_SCRIPT):
        logger.error(f"Le script {REFRESH_SCRIPT} n'existe pas")
        return False
    
    # Obtenir le chemin Python actuel
    python_exe = sys.executable
    if not python_exe:
        logger.error("Impossible de déterminer le chemin de l'exécutable Python")
        return False
    
    # Préparer la ligne crontab
    cron_schedule = f"0 */{interval_hours} * * *"  # Toutes les X heures
    cron_command = f"{python_exe} {REFRESH_SCRIPT}"
    cron_line = f"{cron_schedule} {cron_command} >> {SCRIPT_DIR}/slack_refresh.log 2>&1"
    
    try:
        # Lire le crontab actuel
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        
        # Si crontab -l renvoie une erreur, cela peut signifier qu'il n'y a pas de crontab
        # Dans ce cas, on démarre avec un crontab vide
        if result.returncode != 0 and "no crontab" not in result.stderr:
            logger.error(f"Erreur lors de la lecture du crontab: {result.stderr}")
            return False
        
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Vérifier si notre tâche est déjà dans le crontab
        if REFRESH_SCRIPT in current_crontab:
            logger.info("Une tâche pour ce script existe déjà dans le crontab. Suppression...")
            # Filtrer les lignes pour enlever celle contenant notre script
            current_crontab = "\n".join([line for line in current_crontab.split("\n") 
                                        if REFRESH_SCRIPT not in line])
        
        # Ajouter notre nouvelle tâche
        new_crontab = current_crontab.strip() + "\n" + cron_line + "\n"
        
        # Écrire le nouveau crontab
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode != 0:
            logger.error("Erreur lors de l'écriture du crontab")
            return False
        
        logger.info(f"Tâche cron configurée avec succès: {cron_line}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du cron: {str(e)}")
        return False

def test_token_refresh():
    """Exécute le script de rafraîchissement des tokens une fois pour le tester"""
    if not os.path.exists(REFRESH_SCRIPT):
        logger.error(f"Le script {REFRESH_SCRIPT} n'existe pas")
        return False
    
    # Obtenir le chemin Python actuel
    python_exe = sys.executable
    if not python_exe:
        logger.error("Impossible de déterminer le chemin de l'exécutable Python")
        return False
    
    try:
        logger.info(f"Exécution du script de rafraîchissement pour test: {python_exe} {REFRESH_SCRIPT}")
        result = subprocess.run([python_exe, REFRESH_SCRIPT], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de l'exécution du test: {result.stderr}")
            logger.error(f"Sortie: {result.stdout}")
            return False
        
        logger.info(f"Test exécuté avec succès: {result.stdout}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
        return False

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Configure une tâche planifiée pour rafraîchir les tokens Slack")
    parser.add_argument("--interval", type=int, default=4, help="Intervalle de vérification en heures (défaut: 4)")
    parser.add_argument("--test", action="store_true", help="Exécute une fois le script pour vérifier son fonctionnement")
    parser.add_argument("--no-install", action="store_true", help="Ne configure pas la tâche planifiée")
    args = parser.parse_args()
    
    logger.info(f"Configuration de la tâche de rafraîchissement des tokens Slack")
    logger.info(f"Intervalle: {args.interval} heures")
    logger.info(f"Système d'exploitation: {platform.system()}")
    
    # Vérifier que le script existe
    if not os.path.exists(REFRESH_SCRIPT):
        logger.error(f"Le script {REFRESH_SCRIPT} n'existe pas. Impossible de continuer.")
        sys.exit(1)
    
    # Exécuter le script pour vérifier qu'il fonctionne si demandé
    if args.test:
        logger.info("Exécution du test demandée")
        if test_token_refresh():
            logger.info("Test réussi! Le script de rafraîchissement fonctionne correctement.")
        else:
            logger.error("Test échoué! Vérifiez les logs pour plus d'informations.")
            # On continue quand même pour configurer la tâche si demandé
    
    # Configuration de la tâche planifiée
    if not args.no_install:
        logger.info(f"Configuration de la tâche planifiée avec un intervalle de {args.interval} heures")
        
        if platform.system() == "Windows":
            if setup_windows_task(args.interval):
                logger.info("Tâche Windows configurée avec succès")
            else:
                logger.error("Échec de la configuration de la tâche Windows")
                sys.exit(1)
        else:  # Linux, macOS, etc.
            if setup_linux_cron(args.interval):
                logger.info("Tâche cron configurée avec succès")
            else:
                logger.error("Échec de la configuration de la tâche cron")
                sys.exit(1)
    else:
        logger.info("Option --no-install spécifiée. Aucune tâche planifiée n'a été configurée.")
    
    logger.info("Configuration terminée")

if __name__ == "__main__":
    main() 