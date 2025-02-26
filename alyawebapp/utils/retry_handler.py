from functools import wraps
import time
import logging
import random
from requests.exceptions import RequestException, Timeout
import openai

logger = logging.getLogger(__name__)

class RetryHandler:
    def __init__(self, max_retries=3, base_delay=1, max_delay=10):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Configurer les exceptions à réessayer
        self.retriable_exceptions = (
            RequestException,
            Timeout,
            ConnectionError,
            TimeoutError,
            openai.OpenAIError,  # Classe de base pour toutes les erreurs OpenAI
            openai.APIError,
            openai.APIConnectionError,
            openai.RateLimitError
        )

    def exponential_backoff(self, retry_count):
        """Calcule le délai d'attente avec backoff exponentiel"""
        delay = min(self.base_delay * (2 ** retry_count), self.max_delay)
        jitter = random.uniform(0, 0.1 * delay)  # Ajoute 0-10% de jitter
        return delay + jitter

    def should_retry(self, exception):
        """Détermine si l'erreur est retriable"""
        # Vérifier si c'est une exception retriable
        if isinstance(exception, self.retriable_exceptions):
            return True
        
        # Vérifier les messages d'erreur spécifiques
        error_msg = str(exception).lower()
        retriable_messages = [
            'connection reset',
            'timeout',
            'too many requests',
            'service unavailable',
            'internal server error',
            'bad gateway',
            'gateway timeout'
        ]
        return any(msg in error_msg for msg in retriable_messages)

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for retry in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    if not self.should_retry(e):
                        logger.error(f"Erreur non retriable: {str(e)}")
                        raise

                    delay = self.exponential_backoff(retry)
                    # Log plus détaillé
                    logger.warning(
                        f"Tentative {retry + 1}/{self.max_retries} échouée pour {func.__name__}. "
                        f"Nouvelle tentative dans {delay:.1f}s. "
                        f"Type d'erreur: {type(e).__name__}, "
                        f"Message: {str(e)}"
                    )
                    time.sleep(delay)
            
            logger.error(f"Toutes les tentatives ont échoué. Dernière erreur: {str(last_exception)}")
            raise last_exception

        return wrapper 