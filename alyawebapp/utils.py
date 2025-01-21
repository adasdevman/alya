import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

def get_ai_response(prompt):
    try:
        # Initialiser le client OpenAI avec la nouvelle syntaxe
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Appel à l'API OpenAI avec la nouvelle interface
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extraction de la réponse avec la nouvelle structure
        ai_response = response.choices[0].message.content
        logger.error(f"AI RESPONSE: {ai_response}")
        
        return ai_response
        
    except Exception as e:
        logger.error(f"OpenAI API Error: {str(e)}")
        return "Désolé, je ne peux pas répondre pour le moment." 