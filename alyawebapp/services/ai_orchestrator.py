from openai import OpenAI, OpenAIError
from django.conf import settings
import logging
import json
import traceback

logger = logging.getLogger(__name__)

class AIOrchestrator:
    def __init__(self):
        try:
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise ValueError("Clé API OpenAI non configurée")
            logger.info(f"Initialisation avec API key: {api_key[:5]}...")
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Erreur d'initialisation OpenAI: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def process_request(self, user_request, user_domains):
        """
        Traite la requête utilisateur et gère les erreurs
        """
        try:
            logger.info(f"Début du traitement de la requête: {user_request}")
            
            if not user_request:
                raise ValueError("Requête utilisateur vide")

            # Message système pour Alya
            system_message = """Tu es Alya, une assistante IA experte. 
            Réponds de manière claire, précise et détaillée aux questions des utilisateurs."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_request}
            ]

            logger.info(f"Messages envoyés à OpenAI: {json.dumps(messages, indent=2)}")

            try:
                completion = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                logger.info("Réponse OpenAI reçue")
                logger.debug(f"Réponse complète: {completion}")

            except OpenAIError as api_error:
                logger.error(f"Erreur API OpenAI: {str(api_error)}")
                logger.error(traceback.format_exc())
                return {
                    'status': 'error',
                    'message': "Erreur lors de la communication avec l'IA",
                    'error': str(api_error)
                }

            if not hasattr(completion, 'choices') or not completion.choices:
                logger.error("Réponse OpenAI invalide")
                return {
                    'status': 'error',
                    'message': "Réponse invalide de l'API"
                }

            ai_response = completion.choices[0].message.content
            logger.info(f"Réponse extraite: {ai_response}")

            if not ai_response:
                logger.error("Réponse vide reçue")
                return {
                    'status': 'error',
                    'message': "Réponse vide reçue de l'IA"
                }

            response_data = {
                'status': 'success',
                'message': ai_response
            }
            
            logger.info(f"Réponse finale: {json.dumps(response_data, indent=2)}")
            return response_data

        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': "Une erreur inattendue est survenue",
                'error': str(e)
            }
