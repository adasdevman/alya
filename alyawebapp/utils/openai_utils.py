import openai
from typing import Dict, Any, List
import json
import os
import logging
from openai import OpenAI
from django.conf import settings

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

def call_openai_api(message):
    """Appelle l'API OpenAI et gère la réponse"""
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Créer le contexte du chat
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": message}
        ]
        
        # Appeler OpenAI avec les fonctions
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            functions=get_function_definitions(),
            function_call="auto"
        )
        
        # Récupérer la réponse de l'assistant
        assistant_message = response.choices[0].message
        
        # Si l'assistant veut appeler une fonction
        if hasattr(assistant_message, 'function_call') and assistant_message.function_call:
            return {
                "response": assistant_message.content,
                "function_call": {
                    "name": assistant_message.function_call.name,
                    "arguments": json.loads(assistant_message.function_call.arguments)
                }
            }
        
        # Sinon, retourner juste la réponse
        return {
            "response": assistant_message.content
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à OpenAI: {str(e)}")
        raise

def get_system_prompt():
    return """Tu es ALYA, un assistant intelligent qui aide à gérer les contacts et les compagnies dans HubSpot.
    
    Tu peux :
    1. Créer des contacts (email et prénom obligatoires)
    2. Créer des compagnies (nom obligatoire)
    
    Pour créer un contact : "créer contact email=test@test.com nom=test"
    Pour créer une compagnie : "créer compagnie nom=WorldPos domain=worldpos.com industry=Technology"
    
    Demande toujours les informations manquantes avant d'exécuter une action.
    """

def get_function_definitions():
    return [{
        "name": "execute_hubspot_action",
        "description": "Exécute une action dans HubSpot",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_contact", "create_company"],
                    "description": "Type d'action à effectuer"
                },
                "params": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email du contact"
                        },
                        "firstname": {
                            "type": "string",
                            "description": "Prénom du contact"
                        },
                        "name": {
                            "type": "string",
                            "description": "Nom de la compagnie"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domaine de la compagnie"
                        },
                        "industry": {
                            "type": "string",
                            "description": "Secteur d'activité"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description de la compagnie"
                        },
                        "employees": {
                            "type": "string",
                            "description": "Nombre d'employés"
                        },
                        "website": {
                            "type": "string",
                            "description": "Site web de la compagnie"
                        }
                    },
                    "required": ["name"]  # Seul le nom est obligatoire pour la compagnie
                }
            },
            "required": ["action", "params"]
        }
    }] 