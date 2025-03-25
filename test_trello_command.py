import logging
import sys
import os
import re
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockTrelloIntegration:
    """Simulation d'une intégration Trello pour les tests"""
    def __init__(self):
        self.access_token = "test_token"
        self.active_board_id = "test_board_id"
    
    def get_active_board_id(self):
        return self.active_board_id

class MockTrelloHandler:
    """Version légère du TrelloHandler pour les tests"""
    def __init__(self):
        self.trello_integration = MockTrelloIntegration()
        self.available_lists = ["À faire", "En cours", "Terminé"]
        self.members_data = [
            {"id": "user1", "username": "franckadas", "fullName": "franck adas"},
            {"id": "user2", "username": "marie", "fullName": "Marie Dupont"}
        ]
        self.task_info = {}
    
    def extract_task_info(self, text):
        """Extrait les informations de tâche du texte"""
        logger.info(f"Extraction des informations de tâche à partir de: '{text}'")
        
        # Extraire le nom de la tâche (entre guillemets)
        name_match = re.search(r"['']([^'']*)['']|[\"]([^\"]*)[\"]", text)
        name = None
        if name_match:
            name = next((g for g in name_match.groups() if g is not None), None)
            logger.info(f"Nom de tâche (guillemets): '{name}'")
        
        # Extraire la liste (colonne)
        list_patterns = [
            # Pattern pour capturer la liste entre guillemets
            r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"](.*?)['\"\s](?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
            r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]([^'\"]+)[''\"]",
            # Pattern sans guillemets
            r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.\"\']+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
            # Autres patterns possibles
            r"(?:dans|sur|colonne)\s+(?:la\s+)?(?:colonne\s+)?['\"]?([^'\".,]+)['\"]?"
        ]
        
        list_name = "À faire"  # Valeur par défaut
        for pattern in list_patterns:
            list_match = re.search(pattern, text, re.IGNORECASE)
            if list_match:
                list_name = list_match.group(1).strip()
                logger.info(f"Liste détectée (pattern {pattern}): '{list_name}'")
                break
        
        # Nettoyer le nom de la liste
        list_name = list_name.strip("'").strip('"').strip()
        if list_name.startswith("'") or list_name.startswith('"'):
            list_name = list_name[1:]
        if list_name.endswith("'") or list_name.endswith('"'):
            list_name = list_name[:-1]
        logger.info(f"Liste après nettoyage: '{list_name}'")
        
        # Extraire l'assigné
        assignee_patterns = [
            r"assign[eé][^a-zA-Z]*(la |le )?[àa]\s+([^\s\.,]+)",
            r"assign[eé][^a-zA-Z]*la\s+[àa]\s+(?:[''\"]?)([^'\".,;]+(?:\s+[^'\".,;]+)?)(?:[''\"]?)(?:\s+|$|\.|,)",
            r"assign[eé][eé]?\s+[àa]\s+(?:[''\"]?)([^'\".,;]+(?:\s+[^'\".,;]+)?)(?:[''\"]?)(?:\s+|$|\.|,)",
            r"assign[eé][eé]?\s+[àa]\s+(.+?)(?:\s+(?:et|pour|avec|ayant)|\.|\,|$)",
            r"[àa]\s+([^\.]+?)(?:\s+(?:et|pour|avec|ayant)|\.|\,|$)"
        ]
        
        assignee = None
        for pattern in assignee_patterns:
            assignee_match = re.search(pattern, text, re.IGNORECASE)
            if assignee_match:
                if len(assignee_match.groups()) > 1 and assignee_match.group(2):
                    assignee = assignee_match.group(2).strip()
                else:
                    assignee = assignee_match.group(1).strip()
                logger.info(f"Assigné détecté (pattern {pattern}): '{assignee}'")
                break
        
        # Si pas d'assigné détecté mais présence de noms spécifiques
        if not assignee:
            for name in ["marie", "franck", "adas"]:
                if name in text.lower():
                    # Chercher un nom composé potentiel
                    name_match = re.search(r"[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
                    if name_match:
                        assignee = name_match.group(1).strip()
                        logger.info(f"Assigné détecté (recherche spécifique): '{assignee}'")
                        break
        
        # Extraire la date d'échéance
        due_date = None
        day_patterns = {
            "vendredi": 4, "lundi": 0, "mardi": 1, "mercredi": 2, 
            "jeudi": 3, "samedi": 5, "dimanche": 6
        }
        
        for day, weekday in day_patterns.items():
            if day in text.lower():
                today = datetime.now()
                days_until = (weekday - today.weekday()) % 7
                next_day = today + timedelta(days=days_until)
                logger.info(f"Date d'échéance détectée: '{day}'")
                due_date = day
                break
                
        # Construire et retourner les informations de la tâche
        task_info = {
            "name": name,
            "list_name": list_name,
            "assignee": assignee,
            "due_date": due_date
        }
        
        logger.info(f"Résultats d'extraction: {task_info}")
        return task_info
    
    def check_list_exists(self, list_name):
        """Vérifie si la liste existe dans les listes disponibles"""
        # Afficher toutes les listes disponibles pour le debug
        logger.info(f"Listes disponibles: {self.available_lists}")
        logger.info(f"Vérification de l'existence de la liste: '{list_name}'")
        
        # 1. Recherche exacte
        if list_name in self.available_lists:
            logger.info(f"Liste '{list_name}' trouvée (correspondance exacte)")
            return True, list_name
        
        # 2. Recherche insensible à la casse
        for available_list in self.available_lists:
            logger.info(f"Comparaison: '{available_list.lower()}' vs '{list_name.lower()}'")
            if available_list.lower() == list_name.lower():
                logger.info(f"Liste '{list_name}' trouvée (correspondance insensible à la casse => '{available_list}')")
                return True, available_list
        
        logger.warning(f"Liste '{list_name}' non trouvée")
        return False, None
    
    def check_member_exists(self, member_name):
        """Vérifie si le membre existe"""
        if not member_name:
            return False, None
            
        logger.info(f"Vérification de l'existence du membre: '{member_name}'")
        member_name_lower = member_name.lower()
        
        # Recherche flexible du membre
        for member in self.members_data:
            member_username = member.get('username', '').lower()
            member_fullname = member.get('fullName', '').lower() if member.get('fullName') else ''
            
            # Vérifier les différentes manières dont le nom peut correspondre
            if (member_username == member_name_lower or 
                member_fullname == member_name_lower or
                member_name_lower in member_fullname or 
                member_username in member_name_lower):
                logger.info(f"Membre trouvé: {member}")
                return True, member
        
        logger.warning(f"Membre '{member_name}' non trouvé")
        return False, None

# Test principal
def test_trello_command(command):
    logger.info(f"\n\n=== TEST DE LA COMMANDE: '{command}' ===")
    
    handler = MockTrelloHandler()
    task_info = handler.extract_task_info(command)
    
    # Vérifier la liste
    list_exists, exact_list_name = handler.check_list_exists(task_info['list_name'])
    if not list_exists:
        logger.error(f"❌ La liste '{task_info['list_name']}' n'existe pas")
        return False
    
    # Vérifier le membre
    member_exists, member_info = handler.check_member_exists(task_info['assignee'])
    if not member_exists:
        logger.error(f"❌ Le membre '{task_info['assignee']}' n'existe pas")
        return False
    
    # Simuler la création de la tâche
    logger.info(f"✅ Création de tâche réussie:")
    logger.info(f"Tâche: '{task_info['name']}'")
    logger.info(f"Liste: '{exact_list_name}'")
    logger.info(f"Assigné à: '{member_info.get('fullName', member_info.get('username'))}'")
    if task_info['due_date']:
        logger.info(f"Échéance: {task_info['due_date']}")
    
    return True

# Exécuter des tests avec les commandes problématiques
test_commands = [
    "Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à Marie. L'échéance est vendredi.",
    "Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne \"En cours\" sur Trello et assigne-la à Marie. L'échéance est vendredi.",
    "Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à franck adas. L'échéance est vendredi."
]

# Test spécifique pour franck adas
command = test_commands[2]
print("\n\n=== TEST SPÉCIFIQUE POUR FRANCK ADAS ===")

# Test avec des patterns spécifiques
patterns = [
    r"[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})",
    r"assign[eé][^a-zA-Z]*la\s+[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})",
    r"assign[eé][^a-zA-Z]*la\s+[àa]\s+(?:[''\"]?)([^'\".,;]+(?:\s+[^'\".,;]+)?)(?:[''\"]?)"
]

for pattern in patterns:
    match = re.search(pattern, command, re.IGNORECASE)
    if match:
        print(f"Pattern: {pattern}")
        print(f"Résultat: '{match.group(1)}'")
    else:
        print(f"Pattern: {pattern} - Pas de correspondance")

# Tester tous les scénarios normaux
for cmd in test_commands:
    test_trello_command(cmd)
    print("\n" + "-"*80 + "\n") 