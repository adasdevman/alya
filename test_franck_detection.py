import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_list_extraction(text):
    """Test d'extraction de la liste"""
    logger.info(f"\n=== ANALYSE DE: '{text}' ===")
    
    # Test extraction de la colonne - patterns actuels
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
        logger.warning("Aucune liste détectée avec les patterns actuels")
    
    # Test avec des patterns améliorés
    improved_patterns = [
        r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]([^'\"]+)[''\"]",
        r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.]+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
        r"colonne\s+[''\"]?([^'\".,]+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
        r"liste\s+[''\"]?([^'\".,]+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)"
    ]
    
    for pattern in improved_patterns:
        column_match = re.search(pattern, text, re.IGNORECASE)
        if column_match:
            list_name = column_match.group(1).strip()
            logger.info(f"Liste détectée (pattern amélioré {pattern}): '{list_name}'")
            break
    else:
        logger.warning("Aucune liste détectée avec les patterns améliorés")

def test_assignee_extraction(text):
    """Test d'extraction de l'assigné"""
    logger.info("\nExtraction de l'assigné:")
    
    # Patterns actuels pour l'assigné
    assignee_patterns = [
        r"assign[eé][^a-zA-Z]*la\s+[àa]\s+([''\"]?)([^'\".,\s]+)\1",
        r"assign[eé][eé]?\s+[àa]\s+([''\"]?)([^'\".,\s]+)\1",
        r"assign[eé][eé]?\s+[àa]\s+([A-Za-z]+)",
        r"[àa]\s+([A-Za-z]+)"
    ]
    
    for pattern in assignee_patterns:
        assignee_match = re.search(pattern, text, re.IGNORECASE)
        if assignee_match:
            if len(assignee_match.groups()) > 1 and assignee_match.group(2):
                assignee = assignee_match.group(2).strip()
            else:
                assignee = assignee_match.group(1).strip()
            logger.info(f"Assigné détecté (pattern {pattern}): '{assignee}'")
            break
    else:
        logger.warning("Aucun assigné détecté avec les patterns actuels")
    
    # Patterns améliorés pour l'assigné
    improved_patterns = [
        r"assign[eé][^a-zA-Z]*la\s+[àa]\s+(?:[''\"]?)([^'\".,;]+?)(?:[''\"]?)(?:\s+|$|\.|,)",
        r"assign[eé][eé]?\s+[àa]\s+(?:[''\"]?)([^'\".,;]+?)(?:[''\"]?)(?:\s+|$|\.|,)",
        r"[àa]\s+([^.]+?)(?:\s+et|\s+\.|$|\.|,)"
    ]
    
    for pattern in improved_patterns:
        assignee_match = re.search(pattern, text, re.IGNORECASE)
        if assignee_match:
            assignee = assignee_match.group(1).strip()
            logger.info(f"Assigné détecté (pattern amélioré {pattern}): '{assignee}'")
            break
    else:
        logger.warning("Aucun assigné détecté avec les patterns améliorés")

# Tester avec les phrases problématiques
test_list_extraction("Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à Marie. L'échéance est vendredi.")
test_assignee_extraction("Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à Marie. L'échéance est vendredi.")

test_list_extraction("Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à franck adas. L'échéance est vendredi.")
test_assignee_extraction("Alya, ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello et assigne-la à franck adas. L'échéance est vendredi.") 