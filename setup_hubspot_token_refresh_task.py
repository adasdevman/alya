#!/usr/bin/env python
"""
Script d'installation pour le rafraîchissement automatique des tokens HubSpot.
Ce script configure une tâche planifiée (cron ou Task Scheduler) qui exécutera
le script check_and_refresh_hubspot_tokens.py à intervalles réguliers.

Utilisation: python setup_hubspot_token_refresh_task.py
"""

import os
import sys
import platform
import subprocess
import argparse
from datetime import datetime

def get_absolute_path(relative_path):
    """Convertit un chemin relatif en chemin absolu"""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path))

def setup_windows_task(interval_minutes=15, task_name="HubSpotTokenRefresh"):
    """Configure une tâche planifiée sous Windows"""
    script_path = get_absolute_path("check_and_refresh_hubspot_tokens.py")
    python_path = sys.executable
    
    # Vérifier que le script existe
    if not os.path.exists(script_path):
        print(f"❌ Le script {script_path} n'existe pas.")
        return False
    
    # Créer une commande powershell pour configurer la tâche
    ps_command = f"""
    $action = New-ScheduledTaskAction -Execute '{python_path}' -Argument '"{script_path}"'
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {interval_minutes})
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    # Supprimer la tâche si elle existe déjà
    Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false -ErrorAction SilentlyContinue
    
    # Créer la nouvelle tâche
    Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName '{task_name}' -Description 'Rafraîchissement automatique des tokens HubSpot'
    """
    
    # Écrire la commande dans un fichier temporaire
    ps_script_path = get_absolute_path("setup_task.ps1")
    with open(ps_script_path, "w") as file:
        file.write(ps_command)
    
    try:
        # Exécuter la commande PowerShell avec les privilèges d'administrateur
        print("🔄 Configuration de la tâche planifiée Windows...")
        result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Tâche planifiée '{task_name}' configurée avec succès.")
            print(f"   La tâche s'exécutera toutes les {interval_minutes} minutes.")
            return True
        else:
            print(f"❌ Erreur lors de la configuration de la tâche: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(ps_script_path):
            os.remove(ps_script_path)

def setup_linux_cron(interval_minutes=15):
    """Configure une tâche cron sous Linux"""
    script_path = get_absolute_path("check_and_refresh_hubspot_tokens.py")
    python_path = sys.executable
    log_path = get_absolute_path("hubspot_token_refresh.log")
    
    # Vérifier que le script existe
    if not os.path.exists(script_path):
        print(f"❌ Le script {script_path} n'existe pas.")
        return False
    
    # Créer l'expression cron
    if interval_minutes < 60:
        # Pour les intervalles inférieurs à une heure
        cron_expression = f"*/{interval_minutes} * * * *"
    else:
        # Pour les intervalles en heures
        hours = interval_minutes // 60
        cron_expression = f"0 */{hours} * * *"
    
    # Commande à ajouter au crontab
    cron_command = f"{cron_expression} {python_path} {script_path} >> {log_path} 2>&1"
    
    try:
        # Obtenir le crontab actuel
        print("🔄 Récupération du crontab actuel...")
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        
        if result.returncode == 0:
            current_crontab = result.stdout
        else:
            current_crontab = ""
        
        # Vérifier si la commande existe déjà
        if script_path in current_crontab:
            print("⚠️ Une tâche pour ce script existe déjà dans le crontab.")
            if input("Voulez-vous la remplacer? (o/n): ").lower() != 'o':
                print("❌ Installation annulée.")
                return False
            
            # Supprimer les lignes contenant le chemin du script
            new_crontab_lines = [line for line in current_crontab.split('\n') if script_path not in line]
            current_crontab = '\n'.join(new_crontab_lines)
        
        # Ajouter la nouvelle commande
        new_crontab = current_crontab.strip() + "\n" + cron_command + "\n"
        
        # Écrire le nouveau crontab
        with open(get_absolute_path("new_crontab"), "w") as file:
            file.write(new_crontab)
        
        # Installer le nouveau crontab
        print("🔄 Installation du nouveau crontab...")
        result = subprocess.run(["crontab", get_absolute_path("new_crontab")], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Tâche cron configurée avec succès.")
            print(f"   La tâche s'exécutera selon l'expression: {cron_expression}")
            # Supprimer le fichier temporaire
            os.remove(get_absolute_path("new_crontab"))
            return True
        else:
            print(f"❌ Erreur lors de l'installation du crontab: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

def test_token_refresh():
    """Teste le rafraîchissement des tokens en exécutant le script une fois"""
    script_path = get_absolute_path("check_and_refresh_hubspot_tokens.py")
    python_path = sys.executable
    
    # Vérifier que le script existe
    if not os.path.exists(script_path):
        print(f"❌ Le script {script_path} n'existe pas.")
        return False
    
    try:
        print("\n🔄 Test du rafraîchissement des tokens...")
        result = subprocess.run([python_path, script_path, "--force"], capture_output=True, text=True)
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("✅ Test terminé avec succès.")
            return True
        else:
            print(f"❌ Erreur lors du test: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Configure une tâche planifiée pour le rafraîchissement automatique des tokens HubSpot.')
    parser.add_argument('--interval', type=int, default=15, help='Intervalle en minutes entre les exécutions (par défaut: 15)')
    parser.add_argument('--test', action='store_true', help='Exécute le script une fois pour tester')
    parser.add_argument('--task-name', type=str, default="HubSpotTokenRefresh", help='Nom de la tâche planifiée (Windows uniquement)')
    args = parser.parse_args()
    
    print("=== CONFIGURATION DU RAFRAÎCHISSEMENT AUTOMATIQUE DES TOKENS HUBSPOT ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Intervalle: {args.interval} minutes")
    print(f"Système d'exploitation: {platform.system()}")
    
    if args.test:
        test_token_refresh()
        return
    
    if platform.system() == "Windows":
        setup_windows_task(args.interval, args.task_name)
    elif platform.system() == "Linux":
        setup_linux_cron(args.interval)
    else:
        print(f"❌ Système d'exploitation non pris en charge: {platform.system()}")
        print("   Veuillez configurer manuellement une tâche planifiée.")
    
    print("\n=== OPÉRATION TERMINÉE ===")

if __name__ == "__main__":
    main() 