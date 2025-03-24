import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def get_system_prompt() -> str:
    """
    Retourne le prompt système pour l'analyse d'intentions.
    
    Returns:
        str: Le prompt système pour guider l'IA dans l'analyse d'intentions
    """
    return """
    Tu es un assistant IA expert en analyse d'intentions et classification de texte.
    Ton rôle est de déterminer si la demande de l'utilisateur est :
    
    1. Une simple conversation générale (salutations, remerciements, etc.)
    2. Une demande liée à une intégration spécifique (HubSpot, Trello, Gmail, Google Drive, Salesforce, QuickBooks, Slack)
    3. Une demande qui pourrait être traitée par plusieurs intégrations (ambiguïté)
    
    Réponds au format JSON avec les champs suivants :
    - "intent": "conversation", "integration", "ambiguous", "general_query" ou "error"
    - "integration": le nom de l'intégration concernée (si applicable)
    - "action": l'action demandée (si applicable)
    - "possible_integrations": liste des intégrations possibles en cas d'ambiguïté
    - "detected_actions": actions détectées pour chaque intégration en cas d'ambiguïté
    - "raw_response": une réponse textuelle directe (pour les conversations générales)
    """

def extract_structured_data(prompt: str, model: str = "gpt-3.5-turbo", openai_client=None) -> Dict[str, Any]:
    """
    Utilise OpenAI pour extraire des données structurées à partir d'un prompt.
    
    Args:
        prompt (str): Le prompt à envoyer à OpenAI
        model (str): Le modèle OpenAI à utiliser
        openai_client: Le client OpenAI à utiliser
        
    Returns:
        Dict[str, Any]: Les données structurées extraites
    """
    if not openai_client:
        raise ValueError("Client OpenAI non fourni")
    
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en extraction de données structurées."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de données structurées: {str(e)}")
        return {}

def detect_language(text: str, openai_client=None) -> str:
    """
    Détecte la langue d'un texte.
    
    Args:
        text (str): Le texte dont il faut détecter la langue
        openai_client: Le client OpenAI à utiliser
        
    Returns:
        str: Le code de la langue détectée (fr, en, etc.)
    """
    if not openai_client:
        return "fr"  # Langue par défaut
    
    prompt = f"""
    Quel est le code ISO de la langue principale utilisée dans ce texte ?
    Réponds uniquement par le code sur 2 lettres: fr, en, es, de, it, etc.
    
    Texte : {text[:500]}
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en détection de langues."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=5
        )
        
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        logger.error(f"Erreur lors de la détection de la langue: {str(e)}")
        return "fr"  # Langue par défaut

def summarize_text(text: str, max_length: int = 200, openai_client=None) -> str:
    """
    Résume un texte.
    
    Args:
        text (str): Le texte à résumer
        max_length (int): La longueur maximale du résumé
        openai_client: Le client OpenAI à utiliser
        
    Returns:
        str: Le résumé du texte
    """
    if not openai_client or not text:
        return text[:max_length] + "..." if len(text) > max_length else text
    
    prompt = f"""
    Résume ce texte en {max_length} caractères maximum.
    Conserve les informations essentielles.
    
    Texte : {text[:2000]}
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en résumé de texte."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_length // 4 + 10  # Approximation pour avoir un résumé de la bonne longueur
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur lors du résumé du texte: {str(e)}")
        return text[:max_length] + "..." if len(text) > max_length else text 