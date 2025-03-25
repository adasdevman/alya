import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_column_detection(text):
    """Test la détection de la colonne avec différents patterns"""
    
    logger.info(f"Texte à analyser: '{text}'")
    
    # Test avec le pattern problématique
    patterns = [
        # Pattern original
        r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]([^'\".,]+)[''\"]",
        
        # Pattern amélioré 1
        r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"](.*?)['\"\s](?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
        
        # Pattern amélioré 2
        r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]?([^'\"]+?)[''\"]?(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
        
        # Pattern amélioré 3
        r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.\"\']+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
    ]
    
    for i, pattern in enumerate(patterns):
        column_match = re.search(pattern, text, re.IGNORECASE)
        if column_match:
            list_name = column_match.group(1).strip()
            logger.info(f"Pattern {i+1}: '{list_name}'")
            
            # Nettoyer le nom de la liste
            cleaned_name = list_name.strip("'").strip('"').strip()
            if cleaned_name.startswith("'") or cleaned_name.startswith('"'):
                cleaned_name = cleaned_name[1:]
            if cleaned_name.endswith("'") or cleaned_name.endswith('"'):
                cleaned_name = cleaned_name[:-1]
            
            logger.info(f"Nom nettoyé: '{cleaned_name}'")
        else:
            logger.info(f"Pattern {i+1}: Aucune correspondance")

# Test avec différentes variantes de la même phrase
test_phrases = [
    "Ajoute une tâche 'Finaliser la présentation client' dans la colonne 'En cours' sur Trello",
    "Ajoute une tâche 'Finaliser la présentation client' dans la colonne \"En cours\" sur Trello",
    "Ajoute une tâche dans la colonne 'En cours' sur Trello",
    "Ajoute une tâche dans la colonne En cours sur Trello",
]

for phrase in test_phrases:
    logger.info("\n" + "="*50)
    test_column_detection(phrase) 