import openai
from django.conf import settings

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def get_completion(self, prompt, user_domains=None):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'tokens': response.usage.total_tokens
            }
        except Exception as e:
            return {
                'success': False,
                'response': str(e),
                'tokens': 0
            } 