import openai
from typing import Dict, Any, List
import json
import os
import logging

logger = logging.getLogger(__name__)

def format_chat_history(chat_history: List[Dict[str, Any]]) -> str:
    """
    Formate l'historique du chat en un texte lisible.
    """
    formatted_history = []
    for message in chat_history:
        prefix = "Utilisateur:" if message.get('is_user', False) else "Assistant:"
        formatted_history.append(f"{prefix} {message.get('content', '')}")
    return "\n".join(formatted_history)

def call_openai_api(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelle l'API OpenAI avec un prompt et un contexte enrichi.
    """
    try:
        # Construire le message système avec le contexte des intégrations
        system_message = """Tu es un assistant qui peut interagir avec différentes intégrations.
Les intégrations suivantes sont disponibles : {integrations}.

Historique de la conversation :
{chat_history}

Quand un utilisateur demande une action qui nécessite une intégration :
1. Identifie l'intégration appropriée
2. Détermine l'action à effectuer
3. Prépare les paramètres nécessaires
4. Retourne une réponse structurée avec l'action à effectuer

Format de réponse pour une action d'intégration :
{{
    "message": "Votre message à l'utilisateur",
    "integration_action": {{
        "integration": "nom_integration",
        "method": "nom_methode",
        "params": {{
            "param1": "valeur1"
        }}
    }}
}}""".format(
            integrations=", ".join(context['available_integrations']),
            chat_history=format_chat_history(context.get('chat_history', []))
        )

        # Construire les messages pour l'API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        # Appeler l'API OpenAI
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # Extraire la réponse
        assistant_message = response.choices[0].message.content
        logger.info(f"Réponse OpenAI: {assistant_message}")

        try:
            # Tenter de parser la réponse comme JSON
            parsed_response = json.loads(assistant_message)
            return parsed_response
        except json.JSONDecodeError:
            logger.warning(f"Impossible de parser la réponse JSON: {assistant_message}")
            # Si ce n'est pas du JSON, retourner un format standard
            return {
                "message": assistant_message
            }

    except Exception as e:
        logger.error(f"Erreur lors de l'appel à OpenAI: {str(e)}")
        return {
            "message": "Désolé, une erreur est survenue lors du traitement de votre demande."
        } 