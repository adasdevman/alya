import re
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_extraction(text):
    """Test d'extraction des informations de tâche"""
    logger.info(f"\n\n=== ANALYSE DE: '{text}' ===")
    
    # Test extraction du nom de la tâche
    name_match = re.search(r"['']([^'']*)['']|[\"]([^\"]*)[\"]", text)
    if name_match:
        name = next((g for g in name_match.groups() if g is not None), None)
        logger.info(f"Nom de tâche (guillemets): '{name}'")
    else:
        task_patterns = [
            r"tâche\s+(?:intitulée\s+)?['']?([^''.,]+)['']?",
            r"(?:ajoute|créer?)\s+(?:une\s+)?tâche\s+['']?([^''.,]+)['']?",
            r"(?:ajoute|créer?)\s+(?:une\s+)?carte\s+['']?([^''.,]+)['']?"
        ]
        
        for pattern in task_patterns:
            pattern_match = re.search(pattern, text, re.IGNORECASE)
            if pattern_match:
                name = pattern_match.group(1).strip()
                logger.info(f"Nom de tâche (pattern {pattern}): '{name}'")
                break
        else:
            logger.warning("Aucun nom de tâche détecté")
    
    # Test extraction de la colonne
    column_patterns = [
        r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]([^'\".,]+)[''\"]",
        r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.]+)",
        r"colonne\s+[''\"]?([^'\".,]+)[''\"]?",
        r"liste\s+[''\"]?([^'\".,]+)[''\"]?"
    ]
    
    for pattern in column_patterns:
        column_match = re.search(pattern, text, re.IGNORECASE)
        if column_match:
            list_name = column_match.group(1).strip()
            logger.info(f"Liste détectée (pattern {pattern}): '{list_name}'")
            break
    else:
        logger.warning("Aucune liste détectée")
    
    # Test extraction de l'assigné
    assignee_patterns = [
        r"assign[eé][^a-zA-Z]*la\s+[àa]\s+([''\"]?)([^'\".,\s]+)\1",
        r"assign[eé][eé]?\s+[àa]\s+([''\"]?)([^'\".,\s]+)\1",
        r"assign[eé][eé]?\s+[àa]\s+([A-Za-z]+)",
        r"[àa]\s+([A-Za-z]+)"
    ]
    
    for pattern in assignee_patterns:
        assignee_match = re.search(pattern, text, re.IGNORECASE)
        if assignee_match:
            if len(assignee_match.groups()) > 1:
                # Si nous avons deux groupes (guillemets + nom)
                assignee = assignee_match.group(2).strip()
            else:
                assignee = assignee_match.group(1).strip()
            logger.info(f"Assigné détecté (pattern {pattern}): '{assignee}'")
            break
    else:
        # Recherche simple pour "Marie"
        marie_match = re.search(r"[àa]\s+Marie", text, re.IGNORECASE)
        if marie_match or "marie" in text.lower():
            logger.info("Assigné détecté (recherche directe): 'Marie'")
        else:
            logger.warning("Aucun assigné détecté")
    
    # Test extraction de la date d'échéance
    day_patterns = ["vendredi", "lundi", "mardi", "mercredi", "jeudi", "samedi", "dimanche"]
    
    for day in day_patterns:
        if day in text.lower():
            logger.info(f"Date d'échéance détectée: '{day}'")
            break
    else:
        if "demain" in text.lower():
            logger.info("Date d'échéance détectée: 'demain'")
        elif "semaine prochaine" in text.lower():
            logger.info("Date d'échéance détectée: 'semaine prochaine'")
        else:
            logger.warning("Aucune date d'échéance détectée")

# Tester avec différentes phrases
test_extraction("Ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à Marie. L'échéance est vendredi.")
test_extraction("Créer une tâche pour finaliser la présentation client dans la liste En cours, assignée à Marie pour vendredi")
test_extraction("Je voudrais une nouvelle carte sur Trello : Finaliser la présentation client, dans En cours, assignée à Marie, échéance vendredi")
# Test spécifique pour le cas problématique
test_extraction("Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à Marie. L'échéance est vendredi.") 